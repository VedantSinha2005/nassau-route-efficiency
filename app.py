"""Streamlit dashboard: Nassau Candy distributor routing CASE STUDY.

Run: streamlit run app.py
"""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import (DIAGNOSTIC_OFFSETS, SHIP_MODE_ORDER, group_performance,
                      measure_column, possible_bottlenecks, prepare_data, shipping_kpis)
from factory_lookup import FACTORIES
from geo_lookup import US_STATES

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data' / 'public_demo_orders.csv'
INK = '#11243B'
TEAL = '#0E9488'
GOLD = '#F0B85C'
CORAL = '#D36F58'
BG = '#F4F7FB'

st.set_page_config(page_title='Nassau | Shipping Intelligence',page_icon='\U0001f36c',
                   layout='wide',initial_sidebar_state='expanded')
st.markdown(f"""<style>
    .stApp {{background: {BG};}}
    .block-container {{padding-top: 2rem; padding-bottom: 2rem; max-width: 1460px;}}
    h1,h2,h3 {{color:{INK}; letter-spacing:-0.5px;}}
    div[data-testid="stMetric"] {{background:white; border:1px solid #e3eaf3;
        border-radius:16px; padding:15px 20px; box-shadow:0 2px 8px #11243b07;}}
    div[data-testid="stMetricValue"] {{color:{INK};}}
    .eyebrow {{font-size:12px;letter-spacing:2px;font-weight:700;color:{TEAL};}}
    .hero {{background:linear-gradient(110deg,#10263f,#1a4763);border-radius:18px;
      padding:24px 28px;color:#fff;margin:0 0 18px 0;}}
    .hero h1 {{color:#fff;margin:5px 0;font-size:32px;}}
    .hero p {{color:#d4e6f4;font-size:14px;margin:0;}}
    .note {{background:#fff;border-left:4px solid #d39c39;padding:12px 16px;
           border-radius:4px 10px 10px 4px;color:#3d5269;font-size:14px;margin-bottom:10px;}}
    .small-muted {{font-size:13px;color:#687990;}}
</style>""",unsafe_allow_html=True)


@st.cache_data(show_spinner='Validating shipment records...')
def load_default():
    return pd.read_csv(DATA,low_memory=False,encoding='utf-8-sig')


@st.cache_data(show_spinner='Building factory-to-state dispatch records...')
def load_prepared(source_bytes:bytes|None=None):
    if source_bytes is None:
        df=load_default()
    else:
        from io import BytesIO
        df=pd.read_csv(BytesIO(source_bytes),low_memory=False,encoding='utf-8-sig')
    return prepare_data(df,as_of=pd.Timestamp(date.today()))


def chart(fig,height=400):
    fig.update_layout(template='plotly_white',height=height,
                      margin=dict(l=14,r=14,t=45,b=15),font=dict(color=INK),
                      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                      legend_title_text='')
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})


def display_table(df,cols=None,limit=50):
    if cols is not None:
        df=df[cols]
    st.dataframe(df.head(limit),hide_index=True,use_container_width=True)


def table_view(data,columns):
    friendly={'factory':'Factory','State/Province':'Destination state/province',
              'Region':'Region','Country/Region':'Country','shipments':'Dispatches',
              'avg_days':'Avg days','median_days':'Median days','sd_days':'Std. dev. days',
              'p90_days':'P90 days','delay_rate_pct':'Delayed (%)',
              'efficiency_score':'Efficiency (0-100)','sales':'Sales ($)','units':'Units'}
    if data.empty:
        st.info('No eligible records for this selection. Try lowering minimum route volume.')
        return
    work=data[columns].rename(columns=friendly).copy()
    formatters={x:'{:.1f}' for x in ['Avg days','Median days','Std. dev. days','P90 days',
                                   'Delayed (%)','Efficiency (0-100)'] if x in work}
    st.dataframe(work.style.format(formatters),hide_index=True,use_container_width=True)


st.sidebar.markdown('### \U0001f36c NASSAU / ANALYTICS')
st.sidebar.caption('FACTORY-TO-CUSTOMER CASE STUDY')
st.sidebar.caption('Default: de-identified demonstration data. Original CSV may be uploaded privately.')
page=st.sidebar.radio('Workspace',[
    'Route Overview','Geographic Bottlenecks','Shipping Mode Analysis',
    'Route Drill-Down','Data Quality & Methods'],
    label_visibility='collapsed')
st.sidebar.divider()
upload=st.sidebar.file_uploader('Optional: replace case-study CSV',type=['csv'])
try:
    lines,shipments,audit=load_prepared(upload.getvalue() if upload is not None else None)
except Exception as exc:
    st.error(f'Cannot load dataset: {exc}')
    st.stop()

if shipments.empty:
    st.error('No valid dispatch records remain after validation. Check the CSV.')
    st.stop()

mode_label=st.sidebar.radio('Measurement view',
    ['Exploratory adjusted (UNVERIFIED)','Raw recorded dates'],index=0,
    help='The supplied dates contain large date shifts. The exploratory adjustment subtracts observable 904/1269/1634-day bands; not verified actual shipping performance.')
exploratory=mode_label.startswith('Exploratory')
measure=measure_column(exploratory)
if exploratory and shipments[measure].isna().all():
    st.sidebar.warning('No records match the data-specific offset bands. Reverting to raw dates.')
    exploratory=False
    measure='raw_lead_days'

start=shipments['order_date'].min().date()
end=shipments['order_date'].max().date()
date_selection=st.sidebar.date_input('Order date range',value=(start,end),
                                      min_value=start,max_value=end)
if isinstance(date_selection,(tuple,list)) and len(date_selection)==2:
    start_choice,end_choice=date_selection
elif isinstance(date_selection,(tuple,list)) and len(date_selection)==1:
    start_choice=end_choice=date_selection[0]
else:
    start_choice,end_choice=start,end

country_options=sorted(shipments['Country/Region'].dropna().unique().tolist())
countries=st.sidebar.multiselect('Customer countries',country_options,default=country_options)
region_options=sorted(shipments['Region'].dropna().unique().tolist())
regions=st.sidebar.multiselect('Customer regions',region_options,default=region_options)
state_source=shipments[shipments['Country/Region'].isin(countries) & shipments['Region'].isin(regions)]
state_options=sorted(state_source['State/Province'].dropna().unique().tolist())
states=st.sidebar.multiselect('Destination state/province',state_options,default=state_options)
factory_options=sorted(shipments['factory'].dropna().unique().tolist())
factories=st.sidebar.multiselect('Case-study factory',factory_options,default=factory_options)
ship_mode_options=[v for v in SHIP_MODE_ORDER if v in set(shipments['Ship Mode'])]
ship_mode_options += sorted(set(shipments['Ship Mode'])-set(ship_mode_options))
modes=st.sidebar.multiselect('Ship mode',ship_mode_options,default=ship_mode_options)
if exploratory:
    threshold=st.sidebar.slider('Delayed if days >',0,14,5,1)
else:
    threshold=st.sidebar.slider('Delayed if days >',0,1800,1275,1)
min_volume=st.sidebar.slider('Minimum dispatches per ranked route',1,150,20,1)

selected=(shipments['order_date'].dt.date.between(start_choice,end_choice)&
          shipments['Country/Region'].isin(countries)&
          shipments['Region'].isin(regions)&shipments['State/Province'].isin(states)&
          shipments['factory'].isin(factories)&shipments['Ship Mode'].isin(modes))
subset=shipments.loc[selected].copy()
if exploratory:
    subset=subset[subset['diagnostic_days'].notna()].copy()

st.markdown('''<div class="hero"><div class="eyebrow" style="color:#7de0cf">NASSAU CANDY | ANALYTICS CASE STUDY</div>
    <h1>Factory-to-Customer Route Intelligence</h1>
    <p>Dispatch lead-time benchmarking &nbsp; • &nbsp; State-level hotspots &nbsp; • &nbsp; Mode performance &nbsp; • &nbsp; Drill-down</p></div>''',unsafe_allow_html=True)
if exploratory:
    st.markdown('''<div class="note"><b>Exploratory / unverified measure:</b> All original lead times are implausibly long.
    This view deducts recurring 904 / 1269 / 1634-day offsets from recorded intervals to display a plausible 0-14-day residual.
    <b>These residuals are not validated transit or delivery times.</b> Switch to raw dates to inspect the source.</div>''',
    unsafe_allow_html=True)
else:
    st.error('RAW DATE ANOMALY: These intervals reflect 2024-2025 orders shipped in 2026-2030. Do NOT interpret them as verified logistics performance.')

if subset.empty:
    st.warning('No shipments match the current filters. Broaden the selection in the sidebar.')
    st.stop()

kpis=shipping_kpis(subset,measure,threshold)
k1,k2,k3,k4,k5=st.columns(5)
k1.metric('Dispatch records',f"{kpis['shipments']:,}")
k2.metric('Avg lead time',f"{kpis['mean_days']:.2f} days")
k3.metric('90th percentile',f"{kpis['p90_days']:.1f} days")
k4.metric(f'> {threshold} days',f"{kpis['delay_rate_pct']:.1f}%")
k5.metric('Factory-state pairs',f"{kpis['routes']:,}")
st.caption('Record grain: one distinct order x case-study factory x destination x dispatch. '
           'Date difference is ORDER-to-SHIP, never delivery-transit duration. '
           'Threshold and relative scores are analyst-defined, not contractual SLAs.')

route_cols=['factory','State/Province']
routes=group_performance(subset,route_cols,measure=measure,threshold=threshold,min_shipments=min_volume)
mode_perf=group_performance(subset,['Ship Mode'],measure=measure,threshold=threshold)
state_perf=group_performance(subset,['Country/Region','State/Province'],
                             measure=measure,threshold=threshold)

if page=='Route Overview':
    st.subheader('Route efficiency overview')
    left,right=st.columns([1.15,1])
    with left:
        st.markdown('**Most efficient factory-to-state combinations**')
        if len(routes):
            top=routes.nsmallest(10,'avg_days').copy()
            top['route']=top['factory']+'  \u2192  '+top['State/Province']
            fig=px.bar(top.iloc[::-1],x='avg_days',y='route',orientation='h',
                       color='efficiency_score',color_continuous_scale='Tealgrn',
                       hover_data=['shipments','delay_rate_pct'],
                       labels={'avg_days':'Avg days','route':''})
            chart(fig,410)
        else:
            st.info('No routes meet the current minimum-volume filter.')
    with right:
        st.markdown('**Least efficient eligible combinations**')
        if len(routes):
            bottom=routes.nlargest(10,'avg_days').copy()
            bottom['route']=bottom['factory']+'  \u2192  '+bottom['State/Province']
            fig=px.bar(bottom.iloc[::-1],x='avg_days',y='route',orientation='h',
                       color_discrete_sequence=[CORAL],
                       hover_data=['shipments','delay_rate_pct'],
                       labels={'avg_days':'Avg days','route':''})
            chart(fig,410)
    st.markdown('**Route leaderboard | volume-qualified**')
    table_view(routes,['factory','State/Province','shipments','avg_days','sd_days',
                       'p90_days','delay_rate_pct','efficiency_score'])
    st.divider()
    a,b=st.columns(2)
    with a:
        trend=subset.copy()
        trend['order_month']=trend['order_date'].dt.to_period('M').dt.to_timestamp()
        trend=trend.groupby('order_month',as_index=False).agg(avg_days=(measure,'mean'),dispatches=('Order ID','size'))
        fig=px.line(trend,x='order_month',y='avg_days',markers=True,
                    title='Mean interval by order month',labels={'order_month':'Order month','avg_days':'Days'})
        fig.update_traces(line_color=TEAL)
        chart(fig,340)
    with b:
        fp=group_performance(subset,['factory'],measure=measure,threshold=threshold)
        fig=px.bar(fp.sort_values('shipments',ascending=False),x='factory',y='shipments',
                   color='avg_days',color_continuous_scale='YlOrRd',
                   title='Dispatch volume by assigned factory',
                   labels={'factory':'Factory','shipments':'Dispatches'})
        chart(fig,340)

elif page=='Geographic Bottlenecks':
    st.subheader('US shipping efficiency heatmap')
    st.caption('Only US state dispatches are shown on the US map. Canadian destinations appear below in a separate breakdown.')
    us=state_perf[state_perf['Country/Region']=='United States'].copy()
    us['state_code']=us['State/Province'].map(lambda x:US_STATES.get(x,(None,None,None))[0])
    us=us.dropna(subset=['state_code'])
    if not us.empty:
        fig=px.choropleth(us,locations='state_code',locationmode='USA-states',scope='usa',
                    color='avg_days',color_continuous_scale='RdYlGn_r',
                    hover_name='State/Province',
                    hover_data={'shipments':True,'avg_days':':.2f',
                                'delay_rate_pct':':.1f','state_code':False},
                    labels={'avg_days':'Avg interval (days)','delay_rate_pct':'Delayed %','shipments':'Dispatches'})
        fig.add_trace(go.Scattergeo(lon=[f['lon'] for f in FACTORIES.values()],
                   lat=[f['lat'] for f in FACTORIES.values()],
                   text=list(FACTORIES.keys()),mode='markers',name='Assumed factories',
                   marker=dict(symbol='star',size=10,color=INK,line=dict(color='white',width=1))))
        fig.update_geos(scope='usa',showland=True,landcolor='#f0f4f7',
                        showlakes=True,lakecolor='white')
        chart(fig,505)
    else:
        st.info('No US states to map with the selected filters.')
    st.markdown('**Candidate bottlenecks**')
    bottlenecks=possible_bottlenecks(state_perf,kpis['mean_days'])
    st.caption('Candidates require at least median destination volume AND a mean above the current overall mean; '
               'they are descriptive patterns, NOT evidence of highway congestion.')
    table_view(bottlenecks,['Country/Region','State/Province','shipments','avg_days',
                            'delay_rate_pct','p90_days'])
    st.divider()
    c1,c2=st.columns([1.2,0.8])
    with c1:
        st.markdown('**Illustrative factory-to-state connections (top-volume US routes)**')
        top_flows=routes.nlargest(20,'shipments') if len(routes) else routes
        fig=go.Figure()
        for _,r in top_flows.iterrows():
            geo=US_STATES.get(r['State/Province'])
            factory=FACTORIES.get(r['factory'])
            if not geo or not factory:continue
            fig.add_trace(go.Scattergeo(lon=[factory['lon'],geo[2]],
                 lat=[factory['lat'],geo[1]],mode='lines',showlegend=False,
                 hoverinfo='text',text=f"{r['factory']} to {r['State/Province']}: {r['shipments']} dispatches",
                 line=dict(width=1+4*r['shipments']/max(top_flows['shipments'].max(),1),color='rgba(10,135,140,0.43)')))
        fig.add_trace(go.Scattergeo(lon=[f['lon'] for f in FACTORIES.values()],
                 lat=[f['lat'] for f in FACTORIES.values()],text=list(FACTORIES.keys()),
                 mode='markers',name='Assumed factories',marker=dict(size=9,color=CORAL)))
        fig.update_geos(scope='usa',showland=True,landcolor='#f1f5fa',
                        showsubunits=True,subunitcolor='#d6e1eb')
        chart(fig,410)
        st.caption('Straight connections terminate at approximate state centers; not road or freight routes.')
    with c2:
        st.markdown('**Region comparison**')
        reg=group_performance(subset,['Region'],measure=measure,threshold=threshold)
        fig=px.bar(reg,x='Region',y='avg_days',color='shipments',
                  color_continuous_scale='Tealgrn',
                  labels={'avg_days':'Avg days'},title='Mean by customer region')
        chart(fig,350)
    canada=state_perf[state_perf['Country/Region']=='Canada']
    if not canada.empty:
        st.markdown('**Canadian province performance (outside US choropleth)**')
        table_view(canada,['State/Province','shipments','avg_days','delay_rate_pct'])

elif page=='Shipping Mode Analysis':
    st.subheader('Shipping mode comparison')
    st.caption('Service classes in the source are Same Day, First Class, Second Class, and Standard Class. '
               'These labels are not proof of actual on-time performance.')
    first,second=st.columns(2)
    with first:
        order=[x for x in SHIP_MODE_ORDER if x in mode_perf['Ship Mode'].tolist()]
        fig=px.bar(mode_perf,x='Ship Mode',y='avg_days',color='Ship Mode',
                   category_orders={'Ship Mode':order},
                   color_discrete_sequence=[TEAL,'#589cce',GOLD,CORAL],
                   hover_data=['shipments','delay_rate_pct'],title='Average interval by shipping mode',
                   labels={'avg_days':'Days'})
        fig.update_layout(showlegend=False)
        chart(fig,380)
    with second:
        fig=px.box(subset,x='Ship Mode',y=measure,color='Ship Mode',
                   category_orders={'Ship Mode':SHIP_MODE_ORDER},points=False,
                   color_discrete_sequence=[TEAL,'#589cce',GOLD,CORAL],
                   title='Interval distribution by mode',
                   labels={measure:'Interval (days)'})
        fig.update_layout(showlegend=False)
        chart(fig,380)
    table_view(mode_perf,['Ship Mode','shipments','avg_days','median_days',
                          'sd_days','p90_days','delay_rate_pct'])
    st.info('A valid freight-cost vs transit-time comparison is not possible. '
            'The Cost column is manufacturing cost, not shipment price. '
            'Carrier charges, freight spend, delivery dates and distance are absent.')
    st.markdown('**Sales and manufacturing gross-profit context (not shipping costs)**')
    finance=subset.groupby('Ship Mode',as_index=False).agg(
        sales=('sales','sum'),gross_profit=('gross_profit','sum'),
        manufacture_cost=('manufacture_cost','sum'),shipments=('Order ID','size'))
    st.dataframe(finance.rename(columns={'sales':'Sales ($)','gross_profit':'Gross profit ($)',
        'manufacture_cost':'Manufacturing cost ($)','shipments':'Dispatches'}),
        hide_index=True,use_container_width=True)

elif page=='Route Drill-Down':
    st.subheader('Route drill-down | dispatch-level timeline')
    c1,c2=st.columns(2)
    ff=c1.selectbox('Factory',sorted(subset['factory'].unique().tolist()))
    ff_rows=subset[subset['factory']==ff]
    state_choice=c2.selectbox('Destination',sorted(ff_rows['State/Province'].unique().tolist()))
    chosen=ff_rows[ff_rows['State/Province']==state_choice].copy()
    ck=shipping_kpis(chosen,measure,threshold)
    a,b,c=st.columns(3)
    a.metric('Route dispatches',f"{ck['shipments']:,}")
    b.metric('Average interval',f"{ck['mean_days']:.2f} days")
    c.metric('Over threshold',f"{ck['delay_rate_pct']:.1f}%")
    left,right=st.columns([1.2,1])
    with left:
        fig=px.scatter(chosen.sort_values('order_date'),x='order_date',y='ship_date',
                       color='Ship Mode',category_orders={'Ship Mode':SHIP_MODE_ORDER},
                       hover_data=['Order ID','raw_lead_days','diagnostic_days'],
                       title='Recorded order vs. shipment dates',
                       labels={'order_date':'Order date','ship_date':'Recorded ship date'})
        chart(fig,380)
    with right:
        fig=px.histogram(chosen,x=measure,color='Ship Mode',nbins=22,
                         category_orders={'Ship Mode':SHIP_MODE_ORDER},
                         title='Route dispatch intervals',labels={measure:'Days'})
        fig.add_vline(x=threshold,line_dash='dash',line_color=CORAL)
        chart(fig,380)
    st.markdown('**Individual dispatch records**')
    detail=chosen[['Order ID','factory','city','State/Province','Ship Mode',
                   'order_date','ship_date','raw_lead_days','diagnostic_days','offset_band',
                   'line_items','units','sales','gross_profit']].sort_values('order_date')
    st.dataframe(detail,hide_index=True,use_container_width=True)
    st.download_button('Download this route CSV',detail.to_csv(index=False).encode('utf-8'),
                       file_name='selected_route_dispatches.csv',mime='text/csv')

elif page=='Data Quality & Methods':
    st.subheader('Data integrity | assumptions | methodology')
    st.error('Data quality is the PRIMARY finding: source shipment dates run from 2026 through 2030 for orders placed in 2024-2025. All original dispatch intervals exceed 365 days.')
    l,r=st.columns(2)
    with l:
        st.markdown('**Input and validation audit**')
        audit_table=pd.DataFrame([{'Check':k.replace('_',' ').capitalize(),'Value':v} for k,v in audit.items()])
        st.dataframe(audit_table,hide_index=True,use_container_width=True)
    with r:
        st.markdown('**Observed 365-day date-offset pattern**')
        raw_plot=shipments.copy()
        raw_plot['cluster']=raw_plot['offset_band'].fillna(-1).astype(int).astype(str)
        fig=px.histogram(raw_plot,x='raw_lead_days',nbins=75,color='cluster',
             labels={'raw_lead_days':'Raw order-to-ship days'},
             title='Raw lead-time distribution by inferred offset band')
        chart(fig,365)
    st.markdown('#### Calculation reference')
    st.markdown('''- **Raw lead time:** recorded `Ship Date - Order Date` in calendar days; NOT delivery duration.
- **Exploratory (unverified) adjustment:** subtract exactly 904, 1269, or 1634 days from intervals in the corresponding 0-14-day residual bands; do not adjust other implausible values. Original raw dates stay unchanged. This is a sensitivity exercise only.
- **Dispatch grain:** unique combination of `Order ID + factory + country + state + region + ship mode + order date + ship date`. Repeated SKU lines are collapsed, with units and financials summed.
- **Route:** assigned factory to customer state/province (or region). Product-to-factory mapping comes only from the assignment.
- **Average and variability:** arithmetic mean and sample standard deviation across dispatches.
- **Delay rate:** percentage of intervals strictly above the user-selected threshold; not a contractually defined SLA.
- **Relative efficiency score:** `100 * (largest eligible route mean - route mean) / (largest - smallest)`, equal ties set to 100. Eligible routes have at least the selected dispatch count. This is a descriptive score, NOT routing distance, fuel cost, or causal efficiency.
- **Bottleneck candidates:** destinations with >= median selected-state volume and above-average selected interval. Patterns alone do not establish congestion.
- **Geography:** US state choropleth uses official state abbreviations; Canada reported in tables. Connections to approximate state centroids do not represent actual roads.
- **Financial fields:** `Cost` is the manufacturing expense, not shipping spend; freight economics cannot be calculated.
''')
    st.markdown('#### Case-study assumptions and official website context')
    st.write('Nassau Candy\'s public site describes warehouses and distribution services. The five Wonka-named factories and their coordinates are provided by the assignment and are NOT independently documented actual Nassau facilities.')
    st.markdown('Official sources: [Nassau Candy home](https://www.nassaucandy.com/)  |  [Delivery information](https://www.nassaucandy.com/delivery-information)  |  [Contact / listed distribution centers](https://www.nassaucandy.com/contact/)')

st.divider()
st.download_button('Download all filtered dispatches',
    subset.to_csv(index=False).encode('utf-8'),file_name='nassau_filtered_dispatches.csv',
    mime='text/csv')
st.caption('Research case study only. No implication of verified Nassau Candy internal data or real-world company performance.')
