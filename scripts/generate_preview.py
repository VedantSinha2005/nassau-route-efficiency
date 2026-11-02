"""Generate a self-contained offline, read-only Plotly dashboard preview.

This HTML is a convenience preview; the actual submission app is app.py (Streamlit).
"""
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import get_plotlyjs

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from analysis import prepare_data,group_performance,shipping_kpis
from geo_lookup import US_STATES

raw=pd.read_csv(BASE/'data'/'public_demo_orders.csv')
_,ship,audit=prepare_data(raw,as_of='2026-10-12')
measure='diagnostic_days'
k=shipping_kpis(ship,measure,5)
routes=group_performance(ship,['factory','State/Province'],measure=measure,threshold=5,min_shipments=50)
mode=group_performance(ship,['Ship Mode'],measure=measure,threshold=5)
states=group_performance(ship,['Country/Region','State/Province'],measure=measure,threshold=5)
us=states[states['Country/Region']=='United States'].copy()
us['state_code']=us['State/Province'].map(lambda x:US_STATES.get(x,(None,))[0])

fig1=px.bar(routes.head(12).iloc[::-1].assign(
    label=lambda d:d['factory']+' -> '+d['State/Province']),
    x='avg_days',y='label',orientation='h',color='delay_rate_pct',
    color_continuous_scale='Teal',labels={'avg_days':'Scenario avg days','label':'',
                                      'delay_rate_pct':'Over 5 days %'},
    hover_data=['shipments'],title='Lowest-interval routes | 50+ dispatches')
fig2=px.bar(mode,x='Ship Mode',y='avg_days',color='Ship Mode',
            color_discrete_sequence=['#0E9488','#5198b9','#edb75b','#cc705c'],
            title='Shipping class - adjusted scenario only',
            labels={'avg_days':'Diagnostic adjusted days'})
fig2.update_layout(showlegend=False)
fig3=px.scatter(us,x='shipments',y='avg_days',size='shipments',color='delay_rate_pct',
     hover_name='State/Province',size_max=45,
     color_continuous_scale='YlOrRd',log_x=True,
     title='Volume vs mean interval by destination state',
     labels={'shipments':'Unique dispatches (log)','avg_days':'Scenario mean days',
             'delay_rate_pct':'Over 5 days %'})
fig4=px.histogram(ship,x='raw_lead_days',color='Ship Mode',nbins=100,
                  title='Original, implausible 904-1642 day source intervals',
                  labels={'raw_lead_days':'Raw source order-to-ship days'})
monthly=ship.assign(order_month=ship['order_date'].dt.to_period('M').dt.to_timestamp()).groupby('order_month',as_index=False).agg(
   mean_days=(measure,'mean'))
fig5=px.line(monthly,x='order_month',y='mean_days',markers=True,
            title='Scenario trend by order month',labels={'mean_days':'Adjusted days','order_month':'Order month'})
figs=[fig1,fig2,fig3,fig4,fig5]
for fig in figs:
    fig.update_layout(template='plotly_white',paper_bgcolor='white',plot_bgcolor='white',
        height=380,margin=dict(l=12,r=12,t=50,b=25),font=dict(family='Arial',color='#11243B'))

plots='\n'.join(f'<article class="panel">{pio.to_html(f,include_plotlyjs=False,full_html=False,config={"displaylogo":False})}</article>' for f in figs)
js=get_plotlyjs()
page=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Nassau Route Efficiency - Read-only Preview</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#F4F7FB;color:#11243B;font-family:Inter,Segoe UI,Arial,sans-serif}}
main{{max-width:1260px;margin:0 auto;padding:28px 20px 50px}}
header{{border-radius:22px;padding:33px 32px;background:linear-gradient(110deg,#11243B,#20536A);color:white}}
h1{{font-size:32px;letter-spacing:-.4px;margin:6px 0 7px}}header p{{color:#C3D8E5;margin:0;font-size:14px}}
.caps{{font-size:11px;letter-spacing:2px;color:#7DE0CF;font-weight:800}}.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:18px 0}}
.card{{background:white;border:1px solid #E0E8EE;border-radius:14px;padding:18px}}
.value{{font-size:25px;font-weight:800}}.lab{{font-size:12px;color:#687990;margin-top:4px}}
.warning{{border-left:5px solid #E6AA40;background:#FFFAED;border-radius:8px;padding:14px 18px;margin:0 0 18px;font-size:14px;line-height:1.55}}
.graphs{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.panel{{background:white;border:1px solid #E0E8EE;border-radius:14px;padding:5px}}
.panel:last-child{{grid-column:span 2}}.foot{{margin-top:26px;color:#687990;font-size:12px;line-height:1.6}}
@media(max-width:860px){{.cards{{grid-template-columns:repeat(2,1fr)}}.graphs{{grid-template-columns:1fr}}.panel:last-child{{grid-column:span 1}}}}
</style>
<script>{js}</script></head><body><main>
<header><div class="caps">CASE STUDY / SHIPPING INTELLIGENCE</div>
<h1>Factory-to-Customer Route Efficiency</h1><p>Nassau Candy Distributor | Interactive read-only preview - FULL APP: app.py (Streamlit)</p></header>
<section class="cards"><div class="card"><div class="value">{k['shipments']:,}</div><div class="lab">Unique dispatches</div></div>
<div class="card"><div class="value">{k['mean_days']:.2f} d</div><div class="lab">Unverified adjusted mean</div></div>
<div class="card"><div class="value">{k['delay_rate_pct']:.1f}%</div><div class="lab">Scenario over 5 days</div></div>
<div class="card"><div class="value">{k['routes']}</div><div class="lab">Factory-state pairs</div></div>
<div class="card"><div class="value">{audit['dispatches_with_future_ship_date']:,}</div><div class="lab">Future-dated source shipments</div></div></section>
<div class="warning"><b>Data integrity warning:</b> Source order dates are in 2024-2025 and recorded ship dates extend to 2030. Every raw dispatch lead exceeds one year. Scenario metrics subtract unverified 904, 1269 or 1634-day shifts from the corresponding bands. This preview is NOT verified transit/delivery evidence or a claim about real Nassau Candy performance.</div>
<div class="graphs">{plots}</div>
<p class="foot"><b>Method:</b> one row per order-factory-destination-dispatch after SKU de-duplication. Interval = order date to ship date (NOT delivery). Routes shown require at least 50 records. This preview is fixed to the case-study data and is not the deployed app. Download project ZIP and deploy <code>app.py</code> for all 5 modules, date/region/state/mode filters, choropleth and order drill-down. Actual company source: <a href="https://www.nassaucandy.com/">NassauCandy.com</a>; factory/product mapping is assignment-provided only.</p>
</main></body></html>'''
output=BASE/'Dashboard_Preview.html'
output.write_text(page,encoding='utf-8')
print('Created',output,'size MB',round(output.stat().st_size/1e6,2))
