"""Regression and edge-case tests for source integrity and dashboard metrics."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis import (REQUIRED_COLUMNS,prepare_data,diagnostic_adjustment,
                      group_performance,shipping_kpis,possible_bottlenecks)

DATA=Path(__file__).resolve().parents[1]/'data'/'public_demo_orders.csv'

@pytest.fixture(scope='module')
def prepared():
    return prepare_data(pd.read_csv(DATA,low_memory=False),as_of='2026-10-12')


def test_source_grain_and_quality(prepared):
    rows,dispatches,audit=prepared
    assert audit['source_line_items']==10194
    assert audit['valid_dispatch_records']==8549
    assert audit['invalid_or_missing_dates']==0
    assert audit['unmapped_products']==0
    assert audit['negative_raw_intervals']==0
    assert audit['dispatches_over_365_raw_days']==8549
    assert audit['dispatches_with_future_ship_date']==8245
    assert audit['canada_dispatches']==160
    assert rows['factory'].nunique()==5
    assert dispatches['Order ID'].nunique()==8549
    assert dispatches['line_items'].sum()==10194


def test_metrics_source(prepared):
    _,ship,audit=prepared
    raw=shipping_kpis(ship,'raw_lead_days',1275)
    estimate=shipping_kpis(ship,'diagnostic_days',5)
    assert raw['mean_days']==pytest.approx(1321.3694,abs=0.001)
    assert estimate['mean_days']==pytest.approx(4.29477,abs=0.001)
    assert estimate['delay_rate_pct']==pytest.approx(24.599,abs=.01)
    assert estimate['routes']==196
    assert len(group_performance(ship,['factory','State/Province'],min_shipments=50))==34


def test_known_shipping_modes(prepared):
    _,ship,_=prepared
    m=group_performance(ship,['Ship Mode'])
    averages=dict(zip(m['Ship Mode'],m['avg_days']))
    assert averages['Same Day']==pytest.approx(.38,abs=.01)
    assert averages['Standard Class']==pytest.approx(5.32,abs=.01)
    assert averages['Same Day']<averages['First Class']<averages['Second Class']<averages['Standard Class']


def test_missing_and_negative_dates_are_removed():
    row=pd.read_csv(DATA,nrows=1)
    invalid=row.copy()
    invalid['Order ID']='NEG-DATE'
    invalid['Order Date']='10-01-2024'
    invalid['Ship Date']='09-01-2024'
    missing=row.copy()
    missing['Order ID']='MISSING-DATE'
    missing['Ship Date']=''
    unknown=row.copy()
    unknown['Order ID']='UNKNOWN-FACTORY'
    unknown['Product Name']='New product not in mapping'
    full=pd.concat([row,invalid,missing,unknown],ignore_index=True)
    _,ships,audit=prepare_data(full,as_of='2026-10-12')
    assert len(ships)==1
    assert audit['negative_raw_intervals']==1
    assert audit['invalid_or_missing_dates']==1
    assert audit['unmapped_products']==1
    assert audit['excluded_line_items']==3


def test_adjustment_bands_do_not_mask_unrecognized_values():
    v=pd.Series([5,904,910,1269,1274,1634,1645,750,1800,-1],dtype=float)
    adjustment,bands=diagnostic_adjustment(v)
    assert adjustment.iloc[:7].tolist()==[5,0,6,0,5,0,11]
    assert adjustment.iloc[7:].isna().all()


def test_efficiency_score_ties_and_delay_threshold():
    ship=pd.DataFrame({'factory':['F','F'],'State/Province':['A','B'],
                       'Order ID':['o1','o2'],'diagnostic_days':[2,2],
                       'sales':[2.,3.],'units':[1,1]})
    r=group_performance(ship,['factory','State/Province'],threshold=2)
    assert (r['efficiency_score']==100).all()
    assert (r['delay_rate_pct']==0).all()  # strictly greater than the threshold
    assert group_performance(ship,['factory','State/Province'],min_shipments=3).empty


def test_unknown_required_column():
    with pytest.raises(ValueError,match='Missing required CSV columns'):
        prepare_data(pd.DataFrame({'Order ID':['X']}))
