"""Actual local deployment smoke; known historical dataset, no credentials."""
import json,math,time
from pathlib import Path
from urllib.request import urlopen,Request,build_opener,HTTPCookieProcessor
from http.cookiejar import CookieJar
origin='http://localhost:8090';opener=build_opener(HTTPCookieProcessor(CookieJar()));checks=[]
root=Path(__file__).resolve().parents[1];output=root/'reports/local-integration-http-verification.json'
def save(status):output.write_text(json.dumps({'status':status,'transport':'actual local HTTP, standalone Spark/HDFS, OPA, model for AI paths','checks':checks},ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def post(path,body):
 request=Request(origin+path,json.dumps(body,ensure_ascii=False).encode(),{'Content-Type':'application/json','Origin':origin})
 with opener.open(request,timeout=180) as response:return json.load(response)
for _ in range(20):
 try:
  if json.load(urlopen(origin+'/api/status',timeout=5))['ready']:break
 except OSError:pass
 time.sleep(1)
else:raise RuntimeError('Web not ready')
with urlopen(origin+'/',timeout=10) as response:assert b'id="refresh-dashboard"' in response.read()
selection={'mode':'custom','start':'2011-10-01','end':'2011-10-31'}
try:
 for label,body,wanted in [('all',{'time_selection':{'mode':'all'}},None),('october',{'time_selection':selection},[1154979.30,2040,566.1663235294,1364]),('germany',{'time_selection':selection,'country':'Germany'},[31638.42,58,545.49,38])]:
  data=post('/api/dashboard',body);assert set(data['sections'])=={'kpis','monthly','countries','products','rfm'}
  values=data['sections']['kpis']['result']['rows'][0]
  if wanted:
   for actual,expected in zip(values,wanted):assert math.isclose(float(actual),expected,rel_tol=1e-6,abs_tol=.01),(label,values,wanted)
  for section in data['sections'].values():assert all(p['allow'] for p in section['policy_trace']) and section['result_contract']['status']=='passed'
  checks.append({'name':'dashboard_'+label,'passed':True,'kpis':values,'sections':list(data['sections'])});save('running');print(label,'dashboard passed',flush=True)
 for label,body,expected in [('october_ai',{'question':'How many completed invoices were recorded in October 2011?','time_selection':{'mode':'all'}},2040),('followup_ai',{'question':'แล้วเดือนก่อนล่ะ','follow_up':True,'time_selection':{'mode':'all'}},1837),('germany_ai',{'question':'มีคำสั่งซื้อสำเร็จกี่ใบ','time_selection':selection,'country':'Germany'},58)]:
  result=post('/api/query',body);good=result['status']=='executed' and result['result']['rows']==[[expected]]
  checks.append({'name':label,'passed':good,'response':result});save('running');assert good,label
  print(label,'passed',flush=True)
 save('passed');print('6/6 deployed-main-web checks passed')
except Exception:
 save('failed');raise
