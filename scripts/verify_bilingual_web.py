"""Authenticated public feature checks; credentials never enter the report."""
import json
import time
from pathlib import Path
from friend_access import request

root=Path(__file__).resolve().parents[1]
saved=json.loads((root/'.private/friend-access.json').read_text(encoding='utf-8'))
for _ in range(15):
    status,_body=request(saved['url']+'/api/status',saved['password'])
    if status==200:break
    time.sleep(1)
else:raise RuntimeError('Shared application did not become ready')
checks=[]
questions=[('formula','ขอสูตรAOV ไม่ต้องรัน SQL'),
           ('formula','Explain the formula for month-over-month sales growth; do not execute SQL.'),
           ('discovery','มีข้อมูลอะไรบ้าง'),
           ('monthly_max','เดือนไหนออเดอร์เยอะสุด'),
           ('monthly_max','Which month had the most orders?')]
for kind,question in questions:
    status,body=request(saved['url']+'/api/query',saved['password'],body={'question':question},origin=saved['url'])
    result=json.loads(body)
    if kind=='formula':correct=result.get('intent')=='formula' and result.get('model_calls')==0
    elif kind=='discovery':correct=result.get('intent')=='dataset_discovery' and result.get('status')=='information'
    else:
        rows=result.get('result',{}).get('rows',[])
        correct=(result.get('status')=='executed' and len(rows)==1 and len(rows[0])==2
                 and str(rows[0][0])[:7]=='2011-11' and rows[0][1]==2769)
    row={'kind':kind,'question':question,'http_status':status,'passed':status==200 and correct,
         **{k:result.get(k) for k in ('status','intent','formula_id','model_calls','result','attempts')}}
    checks.append(row)
    print(kind,status,row['passed'],flush=True)
report={'status':'passed' if all(c['passed'] for c in checks) else 'failed',
        'transport':'actual authenticated public HTTPS','checks':checks,
        'monthly_assertion':'one top month only, year-month 2011-11, invoice count 2769; not all months sorted by count'}
(root/'reports/bilingual-web-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if report['status']!='passed':raise AssertionError('Public feature checks failed; see sanitized report')
