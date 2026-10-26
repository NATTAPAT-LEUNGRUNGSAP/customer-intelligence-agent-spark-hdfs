import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from web_app import Application, handler


class WebTests(unittest.TestCase):
    def test_http_contract_and_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(None,{'_dataset_metadata':{}},{'run_id':'fixture'},'fixture','unused',{},directory)
            server=ThreadingHTTPServer(('127.0.0.1',0),handler(app,directory))
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            url=f'http://127.0.0.1:{server.server_port}/api/query'
            def request(body,origin='http://localhost:8090'):
                return Request(url,json.dumps(body).encode(),{'Content-Type':'application/json','Origin':origin})
            try:
                with self.assertRaises(HTTPError) as rejected:
                    urlopen(request({'question':'hello'},'https://untrusted.example'))
                self.assertEqual(rejected.exception.code,403)
                with self.assertRaises(HTTPError) as rejected:
                    urlopen(request({'question':'hello','manifest':'/tmp/other'}))
                self.assertEqual(rejected.exception.code,400)
                app.lock.acquire()
                with self.assertRaises(HTTPError) as busy:
                    urlopen(request({'question':'hello'}))
                app.lock.release()
                self.assertEqual(busy.exception.code,409)
                with patch('web_app.answer',return_value={'status':'clarification','message':'Which period?'}):
                    with urlopen(request({'question':'hello'})) as response:
                        result=json.load(response)
                self.assertEqual(result['status'],'clarification')
                self.assertTrue((Path(directory)/f"web-agent-{result['trace_id']}.json").exists())
                self.assertNotIn('provenance',result)
            finally:
                server.shutdown()
                server.server_close()
