"""Auditable shipping interval analysis: line-item -> order/factory dispatch grain.

CRITICAL: Order Date -> Ship Date measures dispatch/fulfillment, NOT delivery transit.
The supplied file has conspicuous multi-year date offsets. A separate, optional
EXPLORATORY correction only illustrates possible relative operating patterns.
It must never be presented as verified historical delivery data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from factory_lookup import PRODUCT_FACTORY
from geo_lookup import US_STATES, CANADA_PROVINCES, get_us_code, standardize_state

REQUIRED_COLUMNS = [
    'Row ID','Order ID','Order Date','Ship Date','Ship Mode','Customer ID',
    'Country/Region','City','State/Province','Postal Code','Division','Region',
    'Product ID','Product Name','Sales','Units','Gross Profit','Cost',
]
# Three visibly disjoint 365-day offset bands in the supplied case-study file.
# These are not documented business rules, ground truth, or validated corrections.
DIAGNOSTIC_OFFSETS = (904,1269,1634)
SHIP_MODE_ORDER = ['Same Day','First Class','Second Class','Standard Class']


def parse_date_column(series: pd.Series) -> pd.Series:
    """Prefer explicit day-month-year for source; accept common unambiguous alternatives."""
    val = series.astype('string').str.strip()
    result = pd.Series(pd.NaT, index=series.index, dtype='datetime64[ns]')
    for fmt in ('%d-%m-%Y','%Y-%m-%d','%d/%m/%Y','%Y/%m/%d'):
        missing = result.isna()
        if not missing.any():
            break
        result.loc[missing] = pd.to_datetime(val.loc[missing],format=fmt,errors='coerce')
    return result


def diagnostic_adjustment(raw_lead: pd.Series) -> tuple[pd.Series,pd.Series]:
    """Illustrate 0-14-day residuals in narrow, dataset-specific offset bands."""
    offset = pd.Series(np.nan, index=raw_lead.index, dtype='float64')
    adjusted = pd.Series(np.nan, index=raw_lead.index, dtype='float64')
    # Leave already plausible values unchanged, to support fresh corrected CSVs.
    regular = raw_lead.between(0,14)
    offset.loc[regular] = 0.0
    adjusted.loc[regular] = raw_lead.loc[regular]
    for base in DIAGNOSTIC_OFFSETS:
        mask = raw_lead.between(base,base+14)
        offset.loc[mask] = float(base)
        adjusted.loc[mask] = raw_lead.loc[mask]-base
    return adjusted,offset


def prepare_data(frame: pd.DataFrame, as_of=None) -> tuple[pd.DataFrame,pd.DataFrame,dict]:
    """Return cleaned SKU lines, dispatch-level records, and a validation audit."""
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError('Missing required CSV columns: '+', '.join(missing))
    if as_of is None:
        as_of = pd.Timestamp.today().normalize()
    as_of = pd.Timestamp(as_of).normalize()
    d = frame[REQUIRED_COLUMNS].copy().drop_duplicates()
    for name in ['Order ID','Ship Mode','Country/Region','City','State/Province',
                 'Division','Region','Product ID','Product Name','Postal Code']:
        d[name] = d[name].astype('string').str.strip()
    d['Country/Region'] = d['Country/Region'].replace({'US':'United States','USA':'United States','CA':'Canada'})
    d['State/Province'] = [standardize_state(s,c) for s,c in zip(d['State/Province'],d['Country/Region'])]
    d['order_date'] = parse_date_column(d['Order Date'])
    d['ship_date'] = parse_date_column(d['Ship Date'])
    d['factory'] = d['Product Name'].map(PRODUCT_FACTORY).astype('string')
    d['raw_lead_days'] = (d['ship_date']-d['order_date']).dt.days
    d['diagnostic_days'],d['offset_band'] = diagnostic_adjustment(d['raw_lead_days'])
    d['us_code'] = d['State/Province'].map({s:v[0] for s,v in US_STATES.items()})
    d['province_code'] = d['State/Province'].map(CANADA_PROVINCES)
    d['valid_route'] = (
        d['order_date'].notna() & d['ship_date'].notna() &
        d['raw_lead_days'].ge(0) & d['factory'].notna() &
        d['State/Province'].notna() & d['State/Province'].ne('') &
        d['Region'].notna() & d['Region'].ne('') &
        d['Order ID'].notna() & d['Order ID'].ne('')
    )
    valid = d.loc[d['valid_route']].copy()
    for c in ['Sales','Cost','Gross Profit','Units']:
        valid[c] = pd.to_numeric(valid[c],errors='coerce').fillna(0)
    grouping = ['Order ID','factory','Country/Region','State/Province','Region',
                'Ship Mode','order_date','ship_date','raw_lead_days',
                'diagnostic_days','offset_band']
    ships = valid.groupby(grouping,dropna=False,as_index=False).agg(
        line_items=('Row ID','size'),
        units=('Units','sum'),
        sales=('Sales','sum'),
        gross_profit=('Gross Profit','sum'),
        manufacture_cost=('Cost','sum'),
        customer_id=('Customer ID','first'),
        city=('City','first'),
    )
    ships['us_code'] = ships['State/Province'].map(get_us_code)
    ships['is_future_ship_date'] = ships['ship_date'].gt(as_of)
    raw_valid = d['raw_lead_days'].notna()
    audit = {
        'source_line_items':int(len(frame)),
        'duplicate_identical_rows':int(frame.duplicated().sum()),
        'line_items_after_exact_dedup':int(len(d)),
        'unique_order_ids':int(frame['Order ID'].nunique()),
        'valid_line_items':int(len(valid)),
        'valid_dispatch_records':int(len(ships)),
        'invalid_or_missing_dates':int((d['order_date'].isna() | d['ship_date'].isna()).sum()),
        'negative_raw_intervals':int(d['raw_lead_days'].lt(0).sum()),
        'unmapped_products':int(d['factory'].isna().sum()),
        'excluded_line_items':int((~d['valid_route']).sum()),
        'dispatches_over_365_raw_days':int(ships['raw_lead_days'].gt(365).sum()),
        'dispatches_with_future_ship_date':int(ships['is_future_ship_date'].sum()),
        'dispatches_in_diagnostic_bands':int(ships['diagnostic_days'].notna().sum()),
        'us_dispatches':int((ships['Country/Region']=='United States').sum()),
        'canada_dispatches':int((ships['Country/Region']=='Canada').sum()),
        'as_of':as_of.strftime('%Y-%m-%d'),
        'order_date_min':d['order_date'].min().strftime('%Y-%m-%d') if d['order_date'].notna().any() else '',
        'order_date_max':d['order_date'].max().strftime('%Y-%m-%d') if d['order_date'].notna().any() else '',
        'ship_date_min':d['ship_date'].min().strftime('%Y-%m-%d') if d['ship_date'].notna().any() else '',
        'ship_date_max':d['ship_date'].max().strftime('%Y-%m-%d') if d['ship_date'].notna().any() else '',
    }
    return d,ships,audit


def measure_column(diagnostic: bool = True) -> str:
    return 'diagnostic_days' if diagnostic else 'raw_lead_days'


def group_performance(ships:pd.DataFrame, group_columns:list[str], *,
                      measure:str='diagnostic_days', threshold:int=5,
                      min_shipments:int=1) -> pd.DataFrame:
    """Relative efficiency score is min-max normalized on the active eligible routes.

    Zero = longest mean lead time, 100 = shortest; tied routes score 100.
    Scores are DESCRIPTIVE, NOT causal proof of actual route efficiency.
    """
    columns = group_columns+['shipments','avg_days','median_days','sd_days',
        'p90_days','delay_rate_pct','sales','units','efficiency_score']
    if ships.empty or measure not in ships or ships[measure].notna().sum()==0:
        return pd.DataFrame(columns=columns)
    tmp = ships.loc[ships[measure].notna()].copy()
    tmp['_delayed'] = (tmp[measure]>threshold).astype(int)
    res = tmp.groupby(group_columns,as_index=False,dropna=False).agg(
        shipments=('Order ID','size'),avg_days=(measure,'mean'),
        median_days=(measure,'median'),sd_days=(measure,'std'),
        p90_days=(measure,lambda v:float(v.quantile(.9))),
        delay_rate_pct=('_delayed','mean'),sales=('sales','sum'),units=('units','sum'),
    )
    res['delay_rate_pct'] *= 100
    res['sd_days'] = res['sd_days'].fillna(0)
    res = res[res['shipments']>=min_shipments].copy()
    if res.empty:
        res['efficiency_score']=pd.Series(dtype='float')
        return res
    low,high = res['avg_days'].min(),res['avg_days'].max()
    res['efficiency_score'] = 100.0 if abs(high-low)<1e-12 else 100*(high-res['avg_days'])/(high-low)
    return res.sort_values(['avg_days','shipments'],ascending=[True,False]).reset_index(drop=True)


def shipping_kpis(ships:pd.DataFrame,measure:str,threshold:int)->dict:
    v = ships[measure].dropna() if measure in ships else pd.Series(dtype=float)
    return {'shipments':int(len(v)),
            'mean_days':float(v.mean()) if len(v) else float('nan'),
            'median_days':float(v.median()) if len(v) else float('nan'),
            'p90_days':float(v.quantile(.9)) if len(v) else float('nan'),
            'delay_rate_pct':float((v>threshold).mean()*100) if len(v) else float('nan'),
            'routes':int(ships[['factory','State/Province']].drop_duplicates().shape[0]) if len(v) else 0,
            'us':int((ships['Country/Region']=='United States').sum()),
            'canada':int((ships['Country/Region']=='Canada').sum())}


def possible_bottlenecks(state_perf:pd.DataFrame,overall_avg:float)->pd.DataFrame:
    """Candidates only: states with >= median state volume AND worse than global mean."""
    if state_perf.empty:
        return state_perf.copy()
    min_volume=state_perf['shipments'].median()
    result=state_perf[(state_perf['shipments']>=min_volume)&
                      (state_perf['avg_days']>overall_avg)].copy()
    return result.sort_values(['delay_rate_pct','shipments'],ascending=False)
