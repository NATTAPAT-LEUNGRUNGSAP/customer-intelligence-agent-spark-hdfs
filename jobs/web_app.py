"""Local browser interface to the same guarded Spark agent. No shell execution."""
import argparse
import json
import threading
import time
import uuid
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from http.cookies import SimpleCookie, CookieError

from agent import answer
from provenance import fingerprint
from query_runtime import load_views, run_query
from question_scope import validate_time_selection
from input_guard import validate_question
from conversation import Sessions, SessionLimit, followup
from chart_data import chart_data
from question_scope import apply_time_selection
from dashboard import filters, queries, guarded_query, validate_country_scope
from policy_engine import authorize, policy_facts


class Application:
    def __init__(self, spark, schema, manifest, model, endpoint, provenance, reports):
        self.spark, self.schema, self.manifest = spark, schema, manifest
        self.model, self.endpoint, self.provenance = model, endpoint, provenance
        self.reports = Path(reports)
        self.lock = threading.Lock()
        self.sessions = Sessions()
        self.session_lock = threading.Lock()
        self.overview_cache = {}
        self.country_options = None

    def countries(self):
        if self.country_options is None:
            result=guarded_query('SELECT DISTINCT country FROM orders WHERE country IS NOT NULL ORDER BY country',
                                 lambda sql:run_query(self.spark,sql))
            self.country_options=[row[0] for row in result['result']['rows']]
        return self.country_options

    def dashboard(self, selection=None, country=None):
        validate_time_selection(selection)
        if not self.lock.acquire(blocking=False):raise BlockingIOError('Another analysis is running; please wait')
        try:
            scope=filters(selection,country,self.schema['_dataset_metadata'],self.countries())
            key=(scope['start'],scope['end'],scope['country'])
            cached=self.overview_cache.get(key)
            if cached and time.monotonic()-cached[0]<300:
                for section in cached[1]['sections'].values():
                    authorize(policy_facts(section['sql'],1))
                    authorize(policy_facts(section['sql'],1,'post',[]))
                return cached[1]
            snapshot=self.manifest['as_of_date']
            sections={name:guarded_query(sql,lambda text:run_query(self.spark,text))
                      for name,sql in queries(scope,snapshot).items()}
            data={'scope':scope,'snapshot':snapshot,'build_run_id':self.manifest['run_id'],
                  'countries':self.countries(),'sections':sections,
                  'charts':{name:chart_data(value) for name,value in sections.items() if name!='kpis'},
                  'definitions':{'sales':'ยอดขายสำเร็จรวม GBP ก่อนหักคืนสินค้า',
                    'invoices':'จำนวน invoice รวมรายการที่ไม่มีรหัสลูกค้า',
                    'aov':'ยอดขาย / จำนวน invoice','customers':'ลูกค้าที่มีรหัสไม่ซ้ำในช่วงที่เลือก',
                    'rfm':'เฉพาะผู้ซื้อในช่วง/ประเทศที่เลือก ซึ่งมีข้อมูลใน snapshot นี้'}}
            if len(self.overview_cache)>=32:self.overview_cache.pop(next(iter(self.overview_cache)))
            self.overview_cache[key]=(time.monotonic(),data)
            return data
        finally:self.lock.release()

    def query(self, question, time_selection=None, *, session_id=None, follow_up=False, country=None):
        question = validate_question(question)
        validate_time_selection(time_selection)
        if not isinstance(follow_up,bool):raise ValueError('Invalid follow-up selection')
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Another question is running; please wait')
        trace_id, started = uuid.uuid4().hex, time.monotonic()
        try:
            state = None
            if session_id is not None:
                with self.session_lock:
                    _, state = self.sessions.get(session_id)
                    self.sessions.consume(state)
            resolved, conversation_scope = question, None
            if follow_up:
                previous = next((h['resolved_question'] for h in reversed(state['history'])
                                 if h['status']=='executed'),None) if state else None
                resolved, conversation_scope = followup(question, previous)
                resolved = validate_question(resolved)
            if country is not None:
                if not isinstance(country,str) or country not in self.countries():raise ValueError('Unknown country')
                resolved=re.sub(r'\nSelected country:[^\n]*','',resolved)
                resolved=validate_question(resolved+'\nSelected country: '+country)
            def execute(sql):
                if country is not None:validate_country_scope(sql,country)
                return run_query(self.spark,sql)
            try:
                result = answer(resolved,self.schema,
                    execute,self.model,self.endpoint,'/app/knowledge',time_selection=time_selection)
            except Exception as error:
                result = {'status':'failed','error':str(error),'rag':True}
            result['resolved_question'] = resolved
            result['selected_country'] = country
            if conversation_scope:result['conversation_scope'] = conversation_scope
            result['chart_data'] = chart_data(result)
            if state is not None:
                stored_question = apply_time_selection(resolved,self.schema.get('_dataset_metadata',{}),time_selection)[0]
                state['history'] = (state['history'] + [{'question':question,
                    'resolved_question':stored_question,'status':result['status']}])[-8:]
                result['conversation_history'] = state['history']
                result['session_remaining'] = self.sessions.requests-state['requests']
            result.update(trace_id=trace_id,question=question,model=self.model,
                          build_run_id=self.manifest['run_id'],provenance=self.provenance,
                          elapsed_seconds=time.monotonic()-started)
            self.reports.mkdir(parents=True,exist_ok=True)
            (self.reports/f'web-agent-{trace_id}.json').write_text(
                json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
            # Return the trace, not local source fingerprints, to the browser.
            return {key:value for key,value in result.items() if key!='provenance'}
        finally:
            self.lock.release()


def handler(app, static_root):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json; charset=utf-8'):
            data = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False,default=str).encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            if getattr(self,'session_token',None):
                self.send_header('Set-Cookie',f'ci_session={self.session_token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=1800')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/api/status':
                return self.send(200,{'ready':True,'busy':app.lock.locked(),'model':app.model,
                    'metadata':app.schema['_dataset_metadata'],'build_run_id':app.manifest['run_id']})
            files={'/':('index.html','text/html; charset=utf-8'),
                   '/app.js':('app.js','text/javascript; charset=utf-8'),
                   '/style.css':('style.css','text/css; charset=utf-8'),
                   '/charts.js':('charts.js','text/javascript; charset=utf-8'),
                   '/dashboard.js':('dashboard.js','text/javascript; charset=utf-8')}
            if path not in files:
                return self.send(404,{'error':'Not found'})
            name,mime=files[path]
            self.send(200,(Path(static_root)/name).read_bytes(),mime)

        def do_POST(self):
            if self.path not in ('/api/query','/api/dashboard'):
                return self.send(404,{'error':'Not found'})
            origin=self.headers.get('Origin','')
            allowed_origins=os.environ.get('CI_ALLOWED_ORIGINS','http://localhost:8090,http://127.0.0.1:8090').split(',')
            if origin not in allowed_origins:
                return self.send(403,{'error':'Local UI origin required'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send(415,{'error':'JSON required'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=12000:
                    raise ValueError('Invalid request size')
                body=json.loads(self.rfile.read(size))
                if self.path=='/api/dashboard':
                    if not isinstance(body,dict) or set(body)-{'time_selection','country'}:raise ValueError('Invalid overview filters')
                    return self.send(200,app.dashboard(body.get('time_selection'),body.get('country')))
                if not isinstance(body,dict) or 'question' not in body or set(body)-{'question','time_selection','follow_up','country'}:
                    raise ValueError('Only question, time_selection and follow_up fields are accepted')
                cookies=SimpleCookie(self.headers.get('Cookie',''))
                token=cookies.get('ci_session')
                with app.session_lock:
                    self.session_token,_=app.sessions.get(token.value if token else None)
                self.send(200,app.query(body['question'],body.get('time_selection'),
                    session_id=self.session_token,follow_up=body.get('follow_up',False),country=body.get('country')))
            except BlockingIOError as error:
                self.send(409,{'error':str(error)})
            except SessionLimit as error:
                self.send(429,{'error':str(error)})
            except (ValueError,TypeError,CookieError) as error:
                self.send(400,{'error':str(error)})
    return Handler


def main():
    from pyspark.sql import SparkSession
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--model',default='qwen3.5:9b')
    parser.add_argument('--endpoint',default='http://host.docker.internal:11434')
    parser.add_argument('--require-read-only',action='store_true')
    args=parser.parse_args()
    spark=SparkSession.builder.appName('customer-intelligence-web').config('spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        schema,manifest=load_views(spark,args.manifest)
        from query_runtime import require_read_only
        require_read_only(spark,manifest['root'])
        app=Application(spark,schema,manifest,args.model,args.endpoint,
                        fingerprint(endpoint=args.endpoint,model=args.model),'/app/reports')
        server=ThreadingHTTPServer(('0.0.0.0',8090),handler(app,'/app/web'))
        print('Customer Intelligence ready on port 8090',flush=True)
        server.serve_forever()
    finally:
        spark.stop()


if __name__=='__main__':
    main()
