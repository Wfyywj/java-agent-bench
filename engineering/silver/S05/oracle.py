#!/usr/bin/env python3
"""Independent relational-set oracle: Python tuples and sets, no Java/SQL/reference imports."""
import csv,json
from pathlib import Path
r=Path(__file__).parent
orders=[(x[0],x[1],int(x[2])) for x in csv.reader((r/'fixtures/orders.csv').open())]
messages=[(x[0],x[1],int(x[2])) for x in csv.reader((r/'fixtures/conversations.csv').open())]
checked=0
for case in json.loads((r/'fixtures/cases.json').read_text()):
 for step in case['steps']:
  _,tenant,since,limit=step['args'];since=int(since);limit=int(limit)
  if not 1<=limit<=1000:expected='422 invalid_limit'
  else:
   exists={(t,i) for t,i,ts in messages if ts>=since}
   matches=sorted((o for o in orders if o[1]==tenant and (tenant,o[0]) in exists),key=lambda o:(-o[2],o[0]))[:limit]
   expected='200 '+','.join(o[0] for o in matches)+'|queries=1'
  assert step['expected']==expected,case['name'];checked+=1
print(json.dumps({'oracle':'independent Python relational model','checked':checked,'orders':len(orders),'messages':len(messages)}))
