"""Regenerate research PDFs, markdown reports, charts, and analysis exports.

Run from the project root:
    pip install -r requirements-reports.txt
    python scripts/generate_reports.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER,TA_LEFT,TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,
                                Image,PageBreak,KeepTogether,HRFlowable,CondPageBreak)

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from analysis import prepare_data,group_performance,shipping_kpis,possible_bottlenecks

DATA=(BASE/'data'/'nassau_candy_orders.csv') if (BASE/'data'/'nassau_candy_orders.csv').exists() else (BASE/'data'/'public_demo_orders.csv')
REPORTS=BASE/'reports'
CHARTS=BASE/'assets'
TODAY='2026-10-12'  # reproducible report reference date (the assigned project date)
NAVY='#142940'; TEAL='#0E9488'; CORAL='#CB6D58'; MUTED='#687F90'; LIGHT='#EDF4F7'

font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
bold_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
if font_path.exists() and bold_path.exists():
    pdfmetrics.registerFont(TTFont('DejaVu',str(font_path)))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold',str(bold_path)))
    pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold')
    FONT='DejaVu'; FONT_BOLD='DejaVu-Bold'
else:
    FONT='Helvetica'; FONT_BOLD='Helvetica-Bold'

PAGE_W,PAGE_H=A4
MARGIN=50
CONTENT_W=PAGE_W-2*MARGIN
BLUE=colors.HexColor(NAVY)
SEA=colors.HexColor(TEAL)
PALE=colors.HexColor(LIGHT)
GREY=colors.HexColor(MUTED)

ST={
    'overline':ParagraphStyle('overline',fontName=FONT_BOLD,fontSize=8,leading=12,
        textColor=SEA,spaceAfter=12),
    'cover':ParagraphStyle('cover',fontName=FONT_BOLD,fontSize=25,leading=34,
        textColor=BLUE,spaceAfter=12),
    'subtitle':ParagraphStyle('subtitle',fontName=FONT,fontSize=12,leading=19,
        textColor=GREY,spaceAfter=20),
    'h1':ParagraphStyle('h1',fontName=FONT_BOLD,fontSize=16,leading=21,
        textColor=BLUE,spaceBefore=19,spaceAfter=9,keepWithNext=True),
    'h2':ParagraphStyle('h2',fontName=FONT_BOLD,fontSize=10.5,leading=16,
        textColor=BLUE,spaceBefore=13,spaceAfter=5,keepWithNext=True),
    'body':ParagraphStyle('body',fontName=FONT,fontSize=9.1,leading=14.3,
        textColor=BLUE,spaceAfter=9),
    'small':ParagraphStyle('small',fontName=FONT,fontSize=8,leading=12,
        textColor=GREY,spaceAfter=7),
    'table':ParagraphStyle('table',fontName=FONT,fontSize=7.4,leading=10.5,
        textColor=BLUE),
    'tableh':ParagraphStyle('tableh',fontName=FONT_BOLD,fontSize=7.4,leading=11,
        textColor=colors.white),
    'kpi':ParagraphStyle('kpi',fontName=FONT_BOLD,fontSize=17,leading=22,
        textColor=BLUE,alignment=TA_CENTER),
    'kpilabel':ParagraphStyle('kpilabel',fontName=FONT,fontSize=7.1,leading=11,
        textColor=GREY,alignment=TA_CENTER),
    'exec_cover':ParagraphStyle('exec_cover',fontName=FONT_BOLD,fontSize=21,leading=28,
        textColor=BLUE,spaceAfter=5),
    'exec_subtitle':ParagraphStyle('exec_subtitle',fontName=FONT,fontSize=10,leading=14,
        textColor=GREY,spaceAfter=8),
    'exec_h2':ParagraphStyle('exec_h2',fontName=FONT_BOLD,fontSize=9.3,leading=13,
        textColor=BLUE,spaceBefore=6,spaceAfter=2,keepWithNext=True),
    'exec_body':ParagraphStyle('exec_body',fontName=FONT,fontSize=8.4,leading=12.2,
        textColor=BLUE,spaceAfter=6),
    'caption':ParagraphStyle('caption',fontName=FONT,fontSize=7.6,leading=11,
        textColor=GREY,spaceAfter=12,spaceBefore=5),
    'smallcenter':ParagraphStyle('smallcenter',fontName=FONT,fontSize=8.6,
        leading=13,textColor=BLUE,alignment=TA_CENTER),
}


def para(x,style='body'):
    return Paragraph(x,ST[style])


def table(headers,rows,widths=None,aligns=None,font='table',row_pad=6):
    all_data=[[para(escape(str(x)),'tableh') for x in headers]]
    for row in rows:
        all_data.append([para(escape(str(v)),font) for v in row])
    if widths is None:
        widths=[CONTENT_W/len(headers)]*len(headers)
    t=Table(all_data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),BLUE),('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white,colors.HexColor('#F2F6F8')]),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),row_pad),('BOTTOMPADDING',(0,0),(-1,-1),row_pad),
        ('LINEBELOW',(0,-1),(-1,-1),0.4,colors.HexColor('#E6EDF2')),
    ]))
    return t


def figure(path,caption,width=CONTENT_W):
    from PIL import Image as PILImage
    im=PILImage.open(path)
    ratio=im.size[1]/im.size[0]
    return KeepTogether([Image(str(path),width=width,height=width*ratio),
                         para(escape(caption),'caption')])


def quote_panel(title,desc):
    cell=para(f'<b>{escape(title)}</b>  {escape(desc)}','body')
    t=Table([[cell]],colWidths=[CONTENT_W])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#FFF5E7')),
         ('BOX',(0,0),(-1,-1),0.6,colors.HexColor('#F2D7A7')),
         ('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),13),
         ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    return t


def kpi_strip(metrics):
    data=[]
    for value,label in metrics:
        data.append([para(value,'kpi'),para(label,'kpilabel')])
    t=Table([[Table([[v],[lab]],colWidths=[CONTENT_W/len(metrics)-4],
                     style=TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')])) for v,lab in data]],
            colWidths=[CONTENT_W/len(metrics)]*len(metrics))
    t.setStyle(TableStyle([
       ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EDF6F4')),
       ('BOX',(0,0),(-1,-1),0.4,colors.HexColor('#D5E9E5')),
       ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
       ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),
    ]))
    return t


def pdf_page(canvas,doc):
    canvas.saveState()
    w,h=A4
    canvas.setFillColor(BLUE)
    canvas.rect(0,h-8,w,8,stroke=0,fill=1)
    canvas.setStrokeColor(colors.HexColor('#D6E1E8'))
    canvas.line(MARGIN,43,w-MARGIN,43)
    canvas.setFont(FONT,7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN,29,'Nassau Candy Distributor | Educational analytics case study')
    canvas.drawRightString(w-MARGIN,29,f'October 2026  /  {doc.page:02d}')
    canvas.restoreState()


def create_charts(ships,route50,states,mode,regions):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','axes.labelcolor':NAVY,
                         'text.color':NAVY,'axes.grid':False,
                         'figure.facecolor':'white','axes.facecolor':'white'})
    # Figure 1: three distinct 365-day bands.
    fig,axes=plt.subplots(1,3,figsize=(11.8,3.6),sharey=True)
    for ax,offset in zip(axes,[904,1269,1634]):
        part=ships.loc[ships['offset_band']==offset,'raw_lead_days']-offset
        values=part.value_counts().sort_index()
        ax.bar(values.index,values.values,color=TEAL if offset==1269 else '#6B93A9',width=.77)
        ax.set_title(f'Raw lead = {offset} + residual')
        ax.set_xlim(-.7,12)
        ax.set_xticks(range(0,13,2))
        ax.set_xlabel('Residual (days)')
        ax.grid(axis='y',alpha=.18)
        ax.text(.97,.92,f'n = {len(part):,}',transform=ax.transAxes,ha='right',va='top',fontsize=9,color=MUTED)
    axes[0].set_ylabel('Dispatch records')
    fig.suptitle('Three 365-day-spaced date-offset bands in the source data',y=1.02,fontsize=13,fontweight='bold')
    fig.tight_layout(pad=2)
    fig.savefig(CHARTS/'fig01_raw_date_anomaly.png',dpi=190,bbox_inches='tight')
    plt.close(fig)

    # Figure 2: four modes and the unverified adjusted distribution.
    fig,ax=plt.subplots(figsize=(10.6,4))
    modes=['Same Day','First Class','Second Class','Standard Class']
    rows=mode.set_index('Ship Mode').loc[modes]
    x=np.arange(4)
    bars=ax.bar(x,rows['avg_days'],width=.54,color=[TEAL,'#3A91B5','#DBAC60',CORAL])
    for i,(name,r) in enumerate(rows.iterrows()):
        ax.errorbar(i,r['avg_days'],yerr=[[0],[max(0,r['p90_days']-r['avg_days'])]],
                    fmt='none',capsize=4,color=NAVY,lw=1.3)
        ax.text(i,r['avg_days']+.16,f"{r['avg_days']:.2f} d",ha='center',fontsize=10,fontweight='bold')
        ax.text(i,.23,f"n={int(r['shipments']):,}",ha='center',fontsize=8,color='white')
    ax.set_xticks(x,modes)
    ax.set_ylabel('Exploratory adjusted interval (days)')
    ax.set_ylim(0,8)
    ax.set_title('Service tier pattern after UNVERIFIED date-shift adjustment',loc='left')
    ax.grid(axis='y',alpha=.2)
    fig.tight_layout()
    fig.savefig(CHARTS/'fig02_mode_comparison.png',dpi=180,bbox_inches='tight')
    plt.close(fig)

    # Figure 3: volume and relative time hotspots.
    us=states[states['Country/Region']=='United States'].copy()
    fig,ax=plt.subplots(figsize=(11,4.8))
    ax.scatter(us['shipments'],us['avg_days'],s=30+us['shipments']*.27,
               c=us['delay_rate_pct'],cmap='YlOrRd',vmin=0,vmax=55,
               alpha=.77,edgecolors='white',linewidths=.65)
    for name in ['Minnesota','New Jersey','Tennessee','New York','California','Ohio','Illinois']:
        if name in us['State/Province'].values:
            r=us[us['State/Province']==name].iloc[0]
            ax.annotate(name,(r['shipments'],r['avg_days']),xytext=(5,7),
                        textcoords='offset points',fontsize=8,color=NAVY)
    ax.axhline(ships['diagnostic_days'].mean(),color=TEAL,ls='--',lw=1.3,
               label='Overall exploratory mean')
    ax.set_xscale('log')
    ax.set_xlabel('Dispatch volume (log scale)')
    ax.set_ylabel('Exploratory adjusted days')
    ax.set_title('Candidate bottlenecks: high volume and longer intervals',loc='left')
    ax.grid(alpha=.14)
    ax.legend(loc='lower right',frameon=False)
    sm=plt.cm.ScalarMappable(cmap='YlOrRd',norm=plt.Normalize(0,55))
    cbar=fig.colorbar(sm,ax=ax,pad=.02)
    cbar.set_label('Over 5 days (%)')
    fig.tight_layout()
    fig.savefig(CHARTS/'fig03_state_bottlenecks.png',dpi=180,bbox_inches='tight')
    plt.close(fig)

    # Figure 4: regional pattern.
    fig,ax=plt.subplots(figsize=(9.8,3.3))
    ordered=regions.sort_values('avg_days')
    bars=ax.barh(ordered['Region'],ordered['avg_days'],color=[TEAL,'#549CB3','#DBAC60',CORAL])
    for bar,(_,r) in zip(bars,ordered.iterrows()):
        ax.text(r['avg_days']+.02,bar.get_y()+bar.get_height()/2,
                f"{r['avg_days']:.2f} d  |  {int(r['shipments']):,} dispatches",va='center',fontsize=9)
    ax.set_xlim(0,5.7)
    ax.set_xlabel('Exploratory adjusted days')
    ax.set_title('Customer-region comparison',loc='left')
    ax.invert_yaxis()
    ax.grid(axis='x',alpha=.17)
    fig.tight_layout()
    fig.savefig(CHARTS/'fig04_regions.png',dpi=180,bbox_inches='tight')
    plt.close(fig)

    # Figure 5: month-by-month adjusted sensitivity.
    monthly=ships.copy()
    monthly['period']=monthly['order_date'].dt.to_period('M').dt.to_timestamp()
    monthly=monthly.groupby('period',as_index=False).agg(
        avg_days=('diagnostic_days','mean'),shipments=('Order ID','size'))
    fig,ax=plt.subplots(figsize=(10.4,3.4))
    ax.plot(monthly['period'],monthly['avg_days'],marker='o',ms=3.3,lw=1.8,color=TEAL)
    ax.set_ylim(3.6,5.0)
    ax.set_ylabel('Exploratory adjusted days')
    ax.set_xlabel('Order month')
    ax.set_title('Monthly variation in the adjusted residual - NOT verified transit data',loc='left')
    ax.grid(alpha=.18)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(CHARTS/'fig05_monthly_trend.png',dpi=180,bbox_inches='tight')
    plt.close(fig)


def route_rows(r,top=True):
    z=r.nsmallest(10,'avg_days') if top else r.nlargest(10,'avg_days')
    return [[int(i+1),f"{row['factory']} -> {row['State/Province']}",
             int(row['shipments']),f"{row['avg_days']:.2f}",
             f"{row['delay_rate_pct']:.1f}%"] for i,(_,row) in enumerate(z.iterrows())]


def produce_markdown(audit,ships,route50,states,mode,regions,kpi_raw,kpi_adj,bottlenecks):
    mode_txt='\n'.join(f"| {r['Ship Mode']} | {int(r['shipments']):,} | {r['avg_days']:.2f} | {r['delay_rate_pct']:.1f}% |" for _,r in mode.iterrows())
    reg_txt='\n'.join(f"| {r['Region']} | {int(r['shipments']):,} | {r['avg_days']:.2f} | {r['delay_rate_pct']:.1f}% |" for _,r in regions.iterrows())
    def mk_routes(rows):
        return '\n'.join(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |" for row in rows)
    bottleneck_txt='\n'.join(f"| {r['State/Province']} | {int(r['shipments']):,} | {r['avg_days']:.2f} | {r['delay_rate_pct']:.1f}% |" for _,r in bottlenecks.head(10).iterrows())
    paper=f"""# Factory-to-Customer Shipping Route Efficiency Analysis
## Nassau Candy Distributor | Research Paper / Case Study

**Report date:** 12 October 2026  
**Data:** User-supplied `nassau_candy_orders.csv` plus a user-supplied 15-product / 5-factory mapping.  
**Status:** Exploratory descriptive study, NOT an audit of Nassau Candy operations.

## Abstract

This study builds a reproducible factory-to-destination dispatch analytics system using {audit['source_line_items']:,} SKU-level records, representing {audit['valid_dispatch_records']:,} distinct order-factory dispatch records. It includes validation, a US shipping-efficiency choropleth, four-service-tier comparison, minimum-volume route benchmarking, a route drill-down, and an explicit assessment of whether the available dates support logistics conclusions. The predominant finding is data integrity: source orders occurred during {audit['order_date_min']} to {audit['order_date_max']}, while recorded ship dates range {audit['ship_date_min']} to {audit['ship_date_max']}. All {audit['dispatches_over_365_raw_days']:,} dispatches have a source interval above 365 days and {audit['dispatches_with_future_ship_date']:,} are future-dated as of the report's reference date. Consequently raw durations cannot credibly represent ordinary fulfillment or delivery.

A **clearly unverified sensitivity adjustment** reveals three intervals offset by exactly 365 days: subtracting 904, 1,269, or 1,634 days when the remainder is 0-14. On this assumed residual scale, the mean is {kpi_adj['mean_days']:.2f} days and {kpi_adj['delay_rate_pct']:.1f}% exceed five days. These figures are hypotheses for validation, **not verified customer delivery KPIs**.

## 1. Research problem and questions

A distributor needs to understand which origin-destination corridors have larger dispatch intervals, how modes differ, and which high-volume destinations merit investigation. Questions: (Q1) How do order-to-ship intervals vary by factory/state/region? (Q2) Which routes rank fastest/slowest at sufficient volume? (Q3) Are candidate hotspots associated with greater volumes and longer intervals? (Q4) Which data deficiencies prevent credible route-cost or on-time-delivery decisions?

## 2. Dataset and integrity assessment

- **Original grain:** SKU/order line (`Row ID`); {audit['source_line_items']:,} rows, 18 columns, 15 products.
- **Dispatch grain:** unique `Order ID` x factory x destination x ship mode x original order/ship dates; {audit['valid_dispatch_records']:,} records. This prevents double counting lines from the same order.
- **Geography:** {audit['us_dispatches']:,} US dispatch records; {audit['canada_dispatches']:,} Canadian records. The US map excludes Canada; Canadian results remain in tables.
- **Quality:** {audit['invalid_or_missing_dates']} invalid/missing dates; {audit['negative_raw_intervals']} negative durations; {audit['unmapped_products']} unmapped product lines; {audit['excluded_line_items']} excluded lines.
- **Severe quality issue:** raw lead-time mean {kpi_raw['mean_days']:.2f} days; dates reflect multi-year offsets; all raw intervals exceed 365 days. Future-dated records: {audit['dispatches_with_future_ship_date']:,} / {audit['valid_dispatch_records']:,}.

![Observed source-date offsets](../assets/fig01_raw_date_anomaly.png)

The source shows clusters centered at 904, 1269 and 1634 days. The recurrence and mode-aligned residuals suggest a systematic date transformation or synthetic-data mechanism. This is an **inference**, not documented source truth. The unmodified raw series remains accessible in the dashboard.

## 3. Methods and operational definitions

1. Parse dates as `%d-%m-%Y` (with explicit ISO/slash fallbacks); standardize geography, map 15 product names to five *case-study* factories, check null, negative and unmapped records.
2. Aggregate repeated SKU lines into a unique order/factory/destination/dispatch record, summing units and manufacturing financials.
3. Define route = factory to customer state/province; region summaries group by supplied four geographic categories. No carrier trip itinerary is available.
4. Compute **raw order-to-ship lead time** = Ship Date - Order Date, in calendar days. This is fulfillment processing / date-to-dispatch interval, NOT ship-to-delivery transit time.
5. Exploratory only: for raw intervals in `[904,918]`, `[1269,1283]`, or `[1634,1648]`, subtract respective base; plausible 0-14-day residuals are labeled *diagnostic adjusted days*. This rule is case-specific, not production-ready date repair.
6. Compare mean, median, sample SD, 90th percentile and fraction strictly above analyst-configured threshold. Five adjusted days is used for research; not an official service level.
7. Benchmark eligible routes with >=50 dispatches for these research tables (dashboard defaults to 20, adjustable). Relative score = `100 * (max eligible mean - route mean) / (max eligible mean - min eligible mean)`; ties score 100. Scores reflect only this sample and selected view.
8. Define *candidate bottlenecks* as destinations with at least the median state/province volume and mean above the dataset-level mean. Neither correlation nor straight-line map connections establishes real highway congestion.

## 4. Findings: mode, region, route rankings

### 4.1 Shipping class comparison - adjusted scenario only

| Ship mode | Dispatches | Mean residual days | Over 5 days |
|---|---:|---:|---:|
{mode_txt}

![Mode comparison](../assets/fig02_mode_comparison.png)

The adjusted tier ordering is plausible (same-day shortest, standard longest) but this consistency is *not proof* of valid shipping timestamps. Claims about carrier SLA compliance cannot be made.

### 4.2 Region comparison - adjusted scenario only

| Customer region | Dispatches | Mean residual days | Over 5 days |
|---|---:|---:|---:|
{reg_txt}

![Region comparison](../assets/fig04_regions.png)

Differences between region averages are relatively small. Mix of shipping modes, products, customer concentrations, date cohorts and factory assignments may confound these crude means.

### 4.3 Top 10 eligible factory-state routes (>=50 dispatches)

| Rank | Route | Dispatches | Mean days | Over 5 days |
|---:|---|---:|---:|---:|
{mk_routes(route_rows(route50,True))}

### 4.4 Bottom 10 eligible factory-state routes (>=50 dispatches)

| Rank | Route | Dispatches | Mean days | Over 5 days |
|---:|---|---:|---:|---:|
{mk_routes(route_rows(route50,False))}

These ranks are **sensitivity results**, not confirmed supply-chain bottlenecks. They depend on a synthetic-looking date adjustment; low-sample routes are excluded. Rankings are not adjusted for mode mix or seasonal cohorts.

## 5. Geographic bottleneck candidates

State/province candidates are selected by above-median volume and above-overall mean adjusted interval. Highest delay-rate candidates in the selected set include:

| State/province | Dispatches | Mean days | Over 5 days |
|---|---:|---:|---:|
{bottleneck_txt}

![State-volume hotspot scatter](../assets/fig03_state_bottlenecks.png)

## 6. Cost-time tradeoff and limitations

A valid **shipping-cost-to-speed** analysis is NOT possible: `Cost` represents manufacturing cost, `Gross Profit = Sales - manufacturing Cost`, and the file contains no freight charges, distance, carrier, freight weight, actual delivery date, or promised service deadline. The source `Ship Date` marks dispatch, not customer receipt. The assignment's five Wonka-themed factories are not documented operating Nassau Candy facilities. The real company's public delivery page describes distribution facilities in multiple US states, but it does not validate the source factory mapping. Date-shift arithmetic does not restore trustworthy source provenance.

This is descriptive EDA with no causal identification, road-distance optimization, statistical confidence inference, service-level compliance conclusion, or customer complaint data. State-centroid lines are illustrations, not road routes. Canadian destinations are intentionally omitted from the US choropleth and assessed separately.

## 7. Recommendations and validation sequence

1. **Block production decisions** based on this file's current dates; request source-system shipment timestamps and original extract specifications.
2. **Reconcile** a stratified sample of orders across raw shipping records, carrier scans and customer proof-of-delivery. Check the three suspected date shifts before any correction is accepted.
3. **Add required inputs:** true origin facility ID, delivery timestamp, promised date, carrier, freight amount, weight, miles, dispatch status, and reason codes for exception management.
4. **Pilot weekly route/region monitoring** after validation: mode-mix-adjusted order-to-dispatch time, actual ship-to-delivery time, on-time percentage, delay distribution, and freight cost per unit/order.
5. **Investigate candidates** (e.g., state clusters with higher delay rates and meaningful volumes), using controls for service mix and demand periods rather than treating raw rank as operational fault.
6. **Govern US and Canada separately** for maps, crossing rules and realistic carrier service policies.

## 8. Conclusion

The work provides a deployable, transparent Streamlit analytical foundation and reveals a critical date-quality issue. A 4.29-day diagnostic average is consistent with a plausible hypothetical date-shift repair but must not be represented as Nassau Candy's measured delivery performance. After source reconciliation and addition of carrier/delivery fields, the system can support verified lane-level monitoring and operational decisions.

## References and provenance

1. User-provided CSV, `Nassau Candy Distributor (1).csv`, made available for this project; no independent provenance information.
2. User-provided assignment product-to-factory mapping and five geographic coordinates; treated solely as case-study assumptions.
3. Nassau Candy official website, https://www.nassaucandy.com/ (accessed 12 October 2026).
4. Nassau Candy, Delivery Information, https://www.nassaucandy.com/delivery-information (accessed 12 October 2026).
5. Nassau Candy, Contact / Distribution Centers, https://www.nassaucandy.com/contact/ (accessed 12 October 2026).

## Reproducibility

`pip install -r requirements-reports.txt`, then `python scripts/generate_reports.py` to regenerate these documents, export tables, and charts. Run dashboard with `streamlit run app.py`; tests: `python -m pytest -q`.
"""
    (REPORTS/'Research_Paper.md').write_text(paper,encoding='utf-8')
    executive=f"""# Executive Summary | Nassau Candy Shipping Intelligence Case Study
**For government and public-sector stakeholders**  
**12 October 2026 | Evidence status: UNVERIFIED case-study dataset**

## Decision in one sentence
**Do not use the supplied shipment dates for regulatory, procurement, or operational performance claims until independently reconciled.** The project still offers a transparent framework for future verified lane monitoring.

## What the dataset actually contains
- **{audit['source_line_items']:,} line items**, collapsed into **{audit['valid_dispatch_records']:,} dispatch records**, mapped to 5 assumption-based factories and {kpi_adj['routes']} factory-state combinations.
- **{audit['us_dispatches']:,} US** and **{audit['canada_dispatches']:,} Canadian** dispatch records.
- Order dates from 2024-2025 but shipping dates from 2026-2030. **Every raw order-to-ship interval exceeds 365 days**; {audit['dispatches_with_future_ship_date']:,} dates are later than 12 October 2026.
- The official Nassau Candy website documents wholesale distribution and real distribution centers. The assignment's five factory names are not verified corporate origins.

## Why the apparent results cannot be used as actual service KPIs
The recorded dates show three 365-day-spaced bands (904, 1,269 and 1,634 days). Subtracting these offsets produces an **illustrative adjusted average of {kpi_adj['mean_days']:.2f} days**, with **{kpi_adj['delay_rate_pct']:.1f}% >5 days**. This is an exploratory inference only. The dataset also lacks final delivery timestamps and shipping costs. Order-to-ship time is not delivery time.

## What the exploratory comparison suggests (subject to verification)

| Shipping tier | Adjusted scenario mean |
|---|---:|
"""
    for _,r in mode.iterrows():
        executive+=f"| {r['Ship Mode']} | {r['avg_days']:.2f} days |\n"
    executive+="""

The dashboard can identify relative-volume candidates, show a US state heatmap, retain Canadian records in separate tables, and drill into order dates. It cannot validate congestion, on-time delivery, or cost-speed tradeoffs without new source data.

## Recommended phased actions
**0-30 days | Validate source:** Request original shipment events, lineage, date-format documentation, true origin facility identifiers, promised delivery dates, and carrier scans. Reconcile a statistical sample of orders and confirm/reject the three offset hypotheses.

**30-60 days | Build trusted operational measures:** Add actual delivery date, freight cost, lane miles, customer state and state/province normalization, mode, weather/holiday and carrier exception labels. Implement data-quality checks that flag future dates, negative intervals and unrecognized origins.

**60-90 days | Pilot monitoring:** Publish a version-controlled dashboard reporting actual fulfillment interval separately from transit interval, delivery reliability and cost per shipment. Investigate high-volume states only after controlling for service-mode mix, geography and seasonality.

## Safeguards relevant to public decision-making
- Clearly distinguish **scenario analytics** from **validated operational evidence**.
- Maintain US and Canada as distinct jurisdictions on maps and service policy.
- Avoid procurement or performance ratings based on artificial date shifts.
- Keep an audit trail for source validation, route definitions, KPI thresholds and changes.

**Bottom line:** The project is a working decision-support prototype and a documented data-governance warning, not an independently verified assessment of Nassau Candy performance.

**Sources:** User-supplied assignment & CSV; https://www.nassaucandy.com/ ; https://www.nassaucandy.com/delivery-information ; https://www.nassaucandy.com/contact/ (accessed 12 October 2026).
"""
    (REPORTS/'Executive_Summary.md').write_text(executive,encoding='utf-8')
    feedback="""# Feedback Video Script (90-120 seconds) - Record in your own voice

**Important:** This is a suggested script, not your personal testimony. Edit it to match what you genuinely did and learned. The submission form requires a public https:// video URL; this text file alone does not satisfy that field.

**0:00-0:15 | Introduce**
"Hello, my project is Factory-to-Customer Shipping Route Efficiency Analysis for Nassau Candy Distributor. My goal was to create a data-driven logistics dashboard that compares route lead times, geographic patterns and shipping modes."

**0:15-0:40 | Show dashboard**
"The dashboard includes an overview leaderboard, a US state heatmap, regional bottleneck comparisons, shipping-mode charts, and an order-level drill-down. Filters let users select the date range, factory, state, shipping mode and delay threshold."

**0:40-1:10 | Discuss most important learning honestly**
"The biggest finding was data quality. The supplied order dates are from 2024 and 2025, while shipment dates extend to 2030, creating implausible lead times. I kept the original data and added an optional, clearly unverified diagnostic adjustment so the analysis does not hide the problem. I learned to validate data before interpreting dashboards."

**1:10-1:35 | Impact and limitations**
"I built reusable Python analysis logic, a Streamlit web application and a research report. I also learned why shipment date alone does not measure delivery duration, and why manufacturing cost is not the same as shipping cost. In a real organization, carrier scan data and actual delivery records would be required before recommending route changes."

**1:35-1:50 | Close**
"This project strengthened my skills in Python, Pandas, Streamlit, data storytelling and responsible interpretation. Thank you."

## Recording checklist
1. Open the deployed app, switch among tabs and demonstrate one route drill-down.
2. Record your own narration or appear on camera; make any personal claims accurate.
3. Upload to YouTube (unlisted), Loom, or Google Drive configured for accessible link viewing.
4. Confirm the HTTPS video link works in an incognito/private browser before submission.
"""
    (REPORTS/'Feedback_Video_Script.md').write_text(feedback,encoding='utf-8')


def write_research_pdf(audit,ships,route50,states,mode,regions,raw,adj,bottlenecks):
    path=REPORTS/'Research_Paper.pdf'
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=MARGIN,leftMargin=MARGIN,
        topMargin=48,bottomMargin=62,title='Factory-to-Customer Shipping Route Efficiency Analysis',
        author='Educational analytics case-study project')
    s=[]
    s += [Spacer(1,36),para('RESEARCH PAPER  /  OCTOBER 2026','overline'),
          para('Factory-to-Customer Shipping Route Efficiency Analysis','cover'),
          para('Nassau Candy Distributor  |  Case-study dataset','subtitle'),
          HRFlowable(width='100%',thickness=1.8,color=SEA,spaceAfter=18),
          kpi_strip([('10,194','SKU line items'),('8,549','Dispatch records'),
                     ('196','Factory-state pairs'),('5','Assumed factories')]),
          Spacer(1,20),quote_panel('Critical evidence warning.',
            'The source ship dates (2026-2030) are inconsistent with 2024-2025 orders. All raw intervals exceed one year. Any adjusted metric presented below is unverified exploratory sensitivity, not measured company delivery performance.'),
          Spacer(1,20),para('Abstract','h1'),
          para(f'This paper implements a reproducible shipping analytics prototype from {audit["source_line_items"]:,} '
               f'order line items and {audit["valid_dispatch_records"]:,} distinct factory-to-destination dispatches. '
               'Modules include order/date validation, case-study product-to-factory assignment, '
               'volume-screened route benchmarking, a US geographic view, mode comparison and '
               'order-level exploration. The primary research finding is that the original dates '
               'are unsuitable for an ordinary logistics-time claim.'),
          para(f'Three disjoint 365-day-spaced interval clusters motivate a clearly unverified diagnostic '
               f'adjustment. Its mean is {adj["mean_days"]:.2f} days, compared with the raw '
               f'{raw["mean_days"]:.2f} days. This difference is an assumed data-repair sensitivity '
               'rather than confirmed shipping performance. Source lineage and actual delivery events '
               'are prerequisites for production decisions.'),
          para('Core research questions','h2'),
          para('Which assumed factory-to-state pairs display relatively longer intervals? '
               'How do supplied shipping service categories compare? Which high-volume states '
               'merit further examination? What additional data are necessary to support verified '
               'transit reliability and freight-cost decisions?'),
          para('Evidence class: student/educational case study. Factory names and coordinates '
               'come from the project brief, not independently verified Nassau Candy facilities.','small'),
          PageBreak()]
    s += [para('1  Source data and integrity audit','h1'),
          para('Each row represents a SKU line; some order IDs repeat across lines. The '
               'analysis consolidates identical order-factory-destination-dispatch combinations. '
               'The source file has 18 columns, 15 product names, four shipping modes '
               'and both US and Canadian destinations.'),
          table(['Validation check','Observed result'],[
              ['SKU-level rows',f"{audit['source_line_items']:,}"],
              ['Distinct dispatch records',f"{audit['valid_dispatch_records']:,}"],
              ['Invalid/missing date rows',f"{audit['invalid_or_missing_dates']:,}"],
              ['Negative lead-time rows',f"{audit['negative_raw_intervals']:,}"],
              ['Unmapped factory product rows',f"{audit['unmapped_products']:,}"],
              ['Dispatches with raw lead over 365 days',f"{audit['dispatches_over_365_raw_days']:,}"],
              ['Future ship dates at 2026-10-12',f"{audit['dispatches_with_future_ship_date']:,}"],
              ['US / Canada dispatch records',f"{audit['us_dispatches']:,} / {audit['canada_dispatches']:,}"],
          ],[CONTENT_W*.67,CONTENT_W*.33]),
          Spacer(1,10),
          para('The dates span orders from 2024-01-02 to 2025-12-31; ship dates from '
               '2026-06-30 to 2030-06-28. Source order-to-ship intervals range '
               'from 904 to 1,642 days. These values cannot credibly be interpreted '
               'as ordinary logistics fulfillment or delivery time.'),
          figure(CHARTS/'fig01_raw_date_anomaly.png',
                 'Figure 1. Three discrete date-offset groups separated by 365 days. The x-axis is the remainder after subtracting each group base; this visual does not validate the proposed correction.'),
          para('Integrity finding','h2'),
          para('Intervals form three distinct groups with bases at 904, 1,269 and 1,634 days. '
               'The second and third bases differ by exactly 365 days. Their existence is '
               'compatible with artificial date shifts, but the source mechanism and correct '
               'timestamps are unknown. Original raw dates are therefore preserved in the app.'),
          Spacer(1,15)]
    s += [para('2  Cleaning and analytical design','h1'),
          para('Date fields are parsed explicitly as day-month-year, geographic labels are trimmed '
               'and standardized, and product names map to the 15 assignment-defined factory '
               'lookups. Rows with missing or invalid timestamps, negative intervals, or '
               'unknown factories are excluded from performance calculations but counted in '
               'the validation audit. Multi-line SKU purchases are consolidated at '
               'order-factory-destination-dispatch grain.'),
          para('KPI definitions','h2'),
          table(['Metric','Operational definition'],[
             ['Raw lead time','Calendar-day difference: Ship Date minus Order Date. This is NOT carrier delivery duration.'],
             ['Diagnostic residual','For raw lead in one of the three 0-14-day offset bands, subtract 904, 1269 or 1634 days. Unverified assumption.'],
             ['Route volume','Number of distinct dispatch records for the assigned factory and customer state/province.'],
             ['Variability','Standard deviation of dispatch intervals, with 90th percentile shown separately.'],
             ['Delay percentage','Fraction of dispatch intervals strictly above an adjustable five-day diagnostic threshold. Not an SLA.'],
             ['Efficiency score','Within eligible routes: 100 x (max mean - route mean) / (max mean - min mean); ties score 100. Relative only.'],
          ],[CONTENT_W*.3,CONTENT_W*.7]),
          Spacer(1,10),
          para('Research screening and bottleneck rule','h2'),
          para('The report requires at least 50 dispatch records per factory-to-state route '
               f'({len(route50)} routes qualify), while the dashboard minimum defaults to 20 '
               'and remains adjustable. The benchmark is a descriptive ranking, not an '
               'estimate of miles driven, fuel use or monetary cost. A state is flagged '
               'as a candidate only when its dispatch volume meets or exceeds the median '
               'state volume AND its average exceeds the overall average.'),
          para('Scenario design / caution','h2'),
          para('The default interactive dashboard opens in an explicitly labeled exploratory '
               'adjusted mode so users can examine residual patterns; raw intervals are available '
               'one click away. The adjustment subtracts suspected artificial offsets only '
               'when the remainder lies between zero and fourteen days. Values outside '
               'that band are not silently repaired. No mode-to-customer service guarantee '
               'can be inferred without verified dates.'),
          para('Geographic treatment','h2'),
          para('The US choropleth uses state codes and excludes Canada, which is summarized '
               'separately. Optional straight connections from supplied factory coordinates '
               'to approximate state centroids are illustrations and are NOT actual '
               'freight or road itineraries. The case-study factories are not documented '
               'actual Nassau Candy origins.'),
          Spacer(1,15)]
    s += [para('3  Service-mode and regional results','h1'),
          quote_panel('Interpretation condition.',
                  'All adjusted results on this page are diagnostic sensitivity values and should NOT be cited as Nassau Candy verified transport or delivery KPIs.'),
          Spacer(1,10),
          figure(CHARTS/'fig02_mode_comparison.png',
                 'Figure 2. Mean diagnostic residuals by service mode; upper whisker reaches each mode\'s 90th percentile.'),
          table(['Ship mode','Dispatches','Mean days','Over 5 days'],
                [[r['Ship Mode'],f"{int(r['shipments']):,}",f"{r['avg_days']:.2f}",
                  f"{r['delay_rate_pct']:.1f}%"] for _,r in mode.iterrows()],
                [CONTENT_W*.36,CONTENT_W*.19,CONTENT_W*.2,CONTENT_W*.25]),
          Spacer(1,10),
          para('All-route diagnostic mean','h2'),
          para(f'Across {adj["shipments"]:,} dispatches, adjusted mean is '
               f'{adj["mean_days"]:.2f} days, median {adj["median_days"]:.1f}, '
               f'90th percentile {adj["p90_days"]:.1f}, and the fraction '
               f'exceeding five days is {adj["delay_rate_pct"]:.1f}%. '
               'The mode ordering resembles expected service tiers but does not certify '
               'the source-date adjustment.'),
          para('Region-level aggregates','h2'),
          table(['Customer region','Dispatches','Avg days','Over 5 days'],
              [[r['Region'],f"{int(r['shipments']):,}",f"{r['avg_days']:.2f}",
                f"{r['delay_rate_pct']:.1f}%"] for _,r in regions.iterrows()],
               [CONTENT_W*.32,CONTENT_W*.2,CONTENT_W*.2,CONTENT_W*.28]),
          para('Regional differences are modest relative to the interval scale, and '
               'uncontrolled differences in mode mix, factory, season or customer mix '
               'may account for apparent variation.','small'),
          Spacer(1,15)]
    s += [para('4  Route benchmarking','h1'),
          para('These two ranked tables use the exploratory residual and exclude routes '
               'with fewer than 50 distinct dispatches. Raw source lead-time ranks '
               'are available through the dashboard but are heavily confounded by '
               'the multi-year date-shift artifact.'),
          para('Top 10 lower-interval eligible routes','h2'),
          table(['#','Factory to destination','N','Mean d','>5 d'],
                route_rows(route50,True),[23,CONTENT_W*.49,45,74,CONTENT_W-23-CONTENT_W*.49-45-74],row_pad=4.5),
          Spacer(1,10),
          para('Bottom 10 higher-interval eligible routes','h2'),
          table(['#','Factory to destination','N','Mean d','>5 d'],
                route_rows(route50,False),[23,CONTENT_W*.49,45,74,CONTENT_W-23-CONTENT_W*.49-45-74],row_pad=4.5),
          para('The lowest and highest eligible routes should be treated as investigation '
               'candidates only. Differences may arise from service mix or date-cohort '
               'composition, not true geographic inefficiency. This is a descriptive '
               'screen, not causal evidence or optimized fleet routing.','small'),
          Spacer(1,15)]
    s += [CondPageBreak(320),para('5  Geographic signals and throughput','h1'),
          figure(CHARTS/'fig03_state_bottlenecks.png',
                 'Figure 3. Each bubble is a US destination state; volume is on the x-axis (log scale), mean diagnostic residual on y-axis, with color showing fraction over five days.'),
          para('Higher-volume, higher-interval candidates','h2'),
          table(['State / province','Dispatches','Avg days','>5 days'],
                [[r['State/Province'],f"{int(r['shipments']):,}",f"{r['avg_days']:.2f}",
                  f"{r['delay_rate_pct']:.1f}%"] for _,r in bottlenecks.head(8).iterrows()],
                [CONTENT_W*.37,CONTENT_W*.2,CONTENT_W*.2,CONTENT_W*.23]),
          Spacer(1,8),
          para('A state appearing in this list is not proof of network congestion. '
               'Before investigating routes or carriers, require real delivery events, '
               'route distances, origin site IDs, mode adjustment and source-date '
               'reconciliation. Canadian province records are kept in separate tables '
               'rather than projected onto US state polygons.'),
          Spacer(1,15)]
    s += [CondPageBreak(270),para('6  Time trends, commercial variables and gaps','h1'),
          figure(CHARTS/'fig05_monthly_trend.png',
                 'Figure 4. Diagnostic scenario mean by original order month; only shows sensitivity to the inferred correction.'),
          para('No validated freight cost / time frontier','h2'),
          para('The dataset financial columns contain Sales, Units, Cost and Gross Profit. '
               'Cost is explicitly manufacturing cost and Gross Profit = Sales - Cost. '
               'Neither field provides carrier charges, transportation cost, fuel, miles, '
               'weight, route path, actual delivery time or promised delivery date. '
               'Consequently comparing these financial columns with adjusted lead '
               'time would NOT estimate the monetary value of expedited delivery.'),
          para('Most important methodological limitations','h2'),
          para('First, shipment dates appear altered or synthetic. Second, the date '
               'difference is order-to-ship, not shipping-to-delivery. Third, factory '
               'labels and coordinates come from the assignment, not corporate '
               'records. Fourth, the sample overweights chocolate products relative '
               'to other categories, and the number of dispatches differs widely '
               'between factories. Fifth, all rankings are unadjusted for product, '
               'service class, calendar cohort, route distance and regional seasonality. '
               'The sample includes Canada, whose geographic representation must be '
               'kept distinct from a US-state map.'),
          para('Company-site fact check','h2'),
          para('Nassau Candy public pages describe a national wholesale distribution '
               'business with warehouses in New York, Michigan, Florida, Texas and '
               'California. The project brief instead specifies five Wonka-named '
               'factories; this paper does not claim those names or geographic '
               'points are actual Nassau Candy facilities.'),
          Spacer(1,15)]
    s += [CondPageBreak(260),para('7  Recommendations, conclusion and sources','h1'),
          para('Priority 1 | Reconcile data before decisions','h2'),
          para('Obtain original ERP/WMS order, fulfillment and shipment event logs; '
               'carrier manifest and proof-of-delivery scans; time-zone and date-format '
               'definitions; and a sample of source transactions. Validate or reject '
               'the 904/1269/1634-day offset inference. Do not publish raw or adjusted '
               'intervals as official performance in the meantime.'),
          para('Priority 2 | Acquire the missing operational attributes','h2'),
          para('Add actual ship-to-delivery dates, scheduled vs actual pickup, promised '
               'delivery deadline, carrier, true origin facility identifier, destination '
               'geocode, mileage, payload and freight spend. Split KPI families into '
               'fulfillment lead time, in-transit lead time, on-time delivery and '
               'freight cost per order / unit.'),
          para('Priority 3 | Pilot accountable monitoring','h2'),
          para('After reconciliation, report weekly distributions with minimum-volume '
               'qualifications, service-mix controls and driver-level exception '
               'labels. Use states with meaningful volumes and repeat anomalies '
               'as candidates for investigation, not automatic site or vendor rankings. '
               'Govern Canadian and US operational jurisdictions separately.'),
          para('Conclusion','h2'),
          para('The project meets the analytical prototyping objective while exposing '
               'a decisive evidence limitation. The exploratory 4.29-day adjusted mean '
               'may be useful as a test scenario but not as an actual performance fact. '
               'A verified carrier/delivery dataset can later unlock trustworthy '
               'geographic bottleneck detection, shipping-cost comparison and route '
               'service optimization.'),
          para('Sources and provenance','h2'),
          para('1. Assignment-supplied Nassau Candy CSV (18 columns), factory-location '
               'coordinates and product-to-factory lookup; provenance not independently verified.','small'),
          para('2. Nassau Candy official home: https://www.nassaucandy.com/ '
               '(accessed 12 October 2026).','small'),
          para('3. Nassau Candy delivery information: '
               'https://www.nassaucandy.com/delivery-information '
               '(accessed 12 October 2026).','small'),
          para('4. Nassau Candy contact / distribution centers: '
               'https://www.nassaucandy.com/contact/ '
               '(accessed 12 October 2026).','small'),
          para('Reproduce analyses: install requirements and run '
               'python scripts/generate_reports.py; tests: python -m pytest -q; '
               'dashboard: streamlit run app.py.','small')]
    doc.build(s,onFirstPage=pdf_page,onLaterPages=pdf_page)
    return path


def write_executive_pdf(audit,ships,mode,adj):
    """One-page stakeholder brief; details live in Executive_Summary.md."""
    path=REPORTS/'Executive_Summary.pdf'
    doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,
                          topMargin=33,bottomMargin=46,
                          title='Executive Summary - Nassau Shipping Case Study')
    s=[para('PUBLIC-SECTOR DECISION BRIEF  /  OCTOBER 2026','overline'),
       para('Shipping Route Intelligence<br/>Executive Summary','exec_cover'),
       para('Nassau Candy Distributor | Educational case study','exec_subtitle'),
       kpi_strip([('8,549','Dispatches'),('8,549','Raw >365 days'),
                  ('8,245','Future dated'),('4.29 d','Exploratory only')]),
       Spacer(1,6),quote_panel('Decision: withhold performance claims.',
             'All original dispatch intervals exceed one year. Neither the source data nor the experimental adjustment validates real shipping or delivery performance.'),
       Spacer(1,5),para('The asset','exec_h2'),
       para('A tested Streamlit dashboard with factory-state route rankings, US state '
            'heatmap, volume-based hotspot candidates, service-tier comparisons, '
            'filters, and order-level timelines. Original timestamps remain inspectable.'),
       para('The central evidence gap','exec_h2'),
       para(f'{audit["source_line_items"]:,} product lines consolidate into '
            f'{audit["valid_dispatch_records"]:,} dispatches; source orders occur in '
            '2024-2025, but ship dates span 2026-2030. There are three 365-day-spaced '
            'offset bands. Removing these on an <b>unverified sensitivity basis</b> gives '
            f'{adj["mean_days"]:.2f} days on average and {adj["delay_rate_pct"]:.1f}% '
            'above five days. These residuals are <b>not actual delivery KPIs</b>.','exec_body'),
       para('Exploratory mode pattern','exec_h2'),
       table(['Service tier','Dispatches','Adjusted average'],
            [[r['Ship Mode'],f"{int(r['shipments']):,}",f"{r['avg_days']:.2f} days"]
             for _,r in mode.iterrows()],[CONTENT_W*.45,CONTENT_W*.22,CONTENT_W*.33],row_pad=4),
       Spacer(1,5),para('Required public-sector safeguards','exec_h2'),
       table(['Timeline','Action required'],[
          ['0-30 days','Reconcile raw ERP shipment events, true facilities, time zones and carrier proof-of-delivery; validate the three hypothesized offsets.'],
          ['30-60 days','Add delivery timestamps, freight cost, promised dates, actual origins, distance and service-mode controls.'],
          ['60-90 days','Pilot governed lane monitoring; report actual fulfillment separately from transit and carrier on-time performance.']
       ],[CONTENT_W*.21,CONTENT_W*.79],row_pad=4.5),
       Spacer(1,4),
       para('Scope note: The five Wonka-named factories are assignment assumptions; '
            'US maps exclude Canadian destinations. Cost in the source means '
            'manufacturing cost, not freight charges.','small'),
       para('Sources: assignment CSV and lookup; https://www.nassaucandy.com/ ; '
            'https://www.nassaucandy.com/delivery-information ; '
            'https://www.nassaucandy.com/contact/ (accessed 12 October 2026).','small')]
    doc.build(s,onFirstPage=pdf_page,onLaterPages=pdf_page)
    return path


def main():
    REPORTS.mkdir(exist_ok=True)
    CHARTS.mkdir(exist_ok=True)
    df=pd.read_csv(DATA,low_memory=False,encoding='utf-8-sig')
    lines,ships,audit=prepare_data(df,as_of=TODAY)
    raw=shipping_kpis(ships,'raw_lead_days',1275)
    adj=shipping_kpis(ships,'diagnostic_days',5)
    route50=group_performance(ships,['factory','State/Province'],measure='diagnostic_days',threshold=5,min_shipments=50)
    route_all=group_performance(ships,['factory','State/Province'],measure='diagnostic_days',threshold=5)
    route_raw=group_performance(ships,['factory','State/Province'],measure='raw_lead_days',threshold=1275)
    states=group_performance(ships,['Country/Region','State/Province'],measure='diagnostic_days',threshold=5)
    mode=group_performance(ships,['Ship Mode'],measure='diagnostic_days',threshold=5)
    regions=group_performance(ships,['Region'],measure='diagnostic_days',threshold=5)
    bottlenecks=possible_bottlenecks(states,adj['mean_days'])
    create_charts(ships,route50,states,mode,regions)
    produce_markdown(audit,ships,route50,states,mode,regions,raw,adj,bottlenecks)
    pd.DataFrame([{'check':key,'value':val} for key,val in audit.items()]).to_csv(REPORTS/'data_quality_audit.csv',index=False)
    route_all.to_csv(REPORTS/'route_scores_exploratory.csv',index=False)
    route_raw.to_csv(REPORTS/'route_scores_raw.csv',index=False)
    states.to_csv(REPORTS/'state_scores_exploratory.csv',index=False)
    mode.to_csv(REPORTS/'ship_mode_scores_exploratory.csv',index=False)
    pd.DataFrame([{'Offset base':int(k),'Dispatches':int(v)}
                  for k,v in ships['offset_band'].value_counts().sort_index().items()]).to_csv(
                      REPORTS/'date_offset_clusters.csv',index=False)
    summary={'as_of':TODAY,'audit':audit,'raw':raw,'exploratory':adj,
             'mode_summary':mode.to_dict(orient='records'),
             'route_min_volume_paper':50,'eligible_routes':len(route50),
             'data_caveat':'Unverified 904/1269/1634-day offset scenario; not delivery-time evidence.'}
    (REPORTS/'eda_insights.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
    r=write_research_pdf(audit,ships,route50,states,mode,regions,raw,adj,bottlenecks)
    e=write_executive_pdf(audit,ships,mode,adj)
    print('Generated',r,e,'and',len(list(REPORTS.iterdir())),'report files')

if __name__=='__main__':
    main()
