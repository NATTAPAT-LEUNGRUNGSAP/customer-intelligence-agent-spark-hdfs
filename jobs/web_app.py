"""Local browser interface to the same guarded Spark agent. No shell execution."""
import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from agent import answer
from provenance import fingerprint
from query_runtime import load_views, run_query
from question_scope import validate_time_selection


class Application:
    def __init__(self, spark, schema, manifest, model, endpoint, provenance, reports):
        self.spark, self.schema, self.manifest = spark, schema, manifest
        self.model, self.endpoint, self.provenance = model, endpoint, provenance
        self.reports = Path(reports)
        self.lock = threading.Lock()

    def query(self, question, time_selection=None):
        validate_time_selection(time_selection)
        if not isinstance(question,str) or not question.strip() or len(question)>2000:
            raise ValueError('Question must contain 1–2000 characters')
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Another question is running; please wait')
        trace_id, started = uuid.uuid4().hex, time.monotonic()
        try:
            try:
                result = answer(question.strip(),self.schema,
                    lambda sql:run_query(self.spark,sql),self.model,self.endpoint,'/app/knowledge',time_selection=time_selection)
            except Exception as error:
                result = {'status':'failed','error':str(error),'rag':True}
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
                   '/style.css':('style.css','text/css; charset=utf-8')}
            if path not in files:
                return self.send(404,{'error':'Not found'})
            name,mime=files[path]
            self.send(200,(Path(static_root)/name).read_bytes(),mime)

        def do_POST(self):
            if self.path!='/api/query':
                return self.send(404,{'error':'Not found'})
            origin=self.headers.get('Origin','')
            if origin not in ('http://localhost:8090','http://127.0.0.1:8090'):
                return self.send(403,{'error':'Local UI origin required'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send(415,{'error':'JSON required'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=12000:
                    raise ValueError('Invalid request size')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict) or 'question' not in body or set(body)-{'question','time_selection'}:
                    raise ValueError('Only question and time_selection fields are accepted')
                self.send(200,app.query(body['question'],body.get('time_selection')))
            except BlockingIOError as error:
                self.send(409,{'error':str(error)})
            except (ValueError,TypeError) as error:
                self.send(400,{'error':str(error)})
    return Handler


def main():
    from pyspark.sql import SparkSession
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--model',default='qwen3.5:9b')
    parser.add_argument('--endpoint',default='http://host.docker.internal:11434')
    args=parser.parse_args()
    spark=SparkSession.builder.appName('customer-intelligence-web').config('spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        schema,manifest=load_views(spark,args.manifest)
        app=Application(spark,schema,manifest,args.model,args.endpoint,
                        fingerprint(endpoint=args.endpoint,model=args.model),'/app/reports')
        server=ThreadingHTTPServer(('0.0.0.0',8090),handler(app,'/app/web'))
        print('Customer Intelligence ready on port 8090',flush=True)
        server.serve_forever()
    finally:
        spark.stop()


if __name__=='__main__':
    main()
