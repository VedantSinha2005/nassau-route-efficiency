"""Create a de-identified demonstration copy for public app hosting.

This is DATA MINIMIZATION, not a formal guarantee of anonymity. Before public
sharing, obtain authorization for the aggregate operational and commercial data.
The underlying dates, mode classes, amounts and geography are unchanged so
case-study analytical totals and anomalies remain reproducible.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'data'/'nassau_candy_orders.csv'
out=ROOT/'data'/'public_demo_orders.csv'
if not source.exists():
    raise SystemExit('Private raw CSV not found; cannot regenerate demo from public demo.')

original=pd.read_csv(source,low_memory=False,encoding='utf-8-sig')
d=original.copy()
rng=np.random.default_rng(20261012)
for column,prefix in [('Order ID','DEMO-ORDER'),('Customer ID','DEMO-CUST')]:
    uniques=d[column].drop_duplicates().tolist()
    ids=rng.permutation(np.arange(100001,100001+len(uniques)))
    mapping={value:f'{prefix}-{int(ids[i]):06d}' for i,value in enumerate(uniques)}
    if column=='Customer ID':
        # Customer IDs stay numeric for schema compatibility; no original ID retained.
        d[column]=d[column].map({v:int(ids[i])+500000 for i,v in enumerate(uniques)})
    else:
        d[column]=d[column].map(mapping)
d['City']='Withheld in public demo'
d['Postal Code']='Withheld'
d['Row ID']=np.arange(1,len(d)+1)
d.to_csv(out,index=False)
print('Wrote',out,'with',len(d),'redacted rows,',d['Order ID'].nunique(),'pseudo order IDs')
