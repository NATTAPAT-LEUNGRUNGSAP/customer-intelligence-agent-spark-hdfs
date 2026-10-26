"""Temporary authenticated HTTPS gateway; credentials remain in ignored .private/."""
import argparse
import base64
import json
import re
import secrets
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.private'
CADDY = 'caddy@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d'
COMPOSE = ['docker','compose','-f','compose.yaml','-f','compose.web.yaml',
           '-f','compose.share.yaml','--profile','web','--profile','share']


def command(args, *, data=None, timeout=120):
    result = subprocess.run(args,cwd=ROOT,input=data,capture_output=True,timeout=timeout)
    if result.returncode:
        # Command arguments never include a plaintext password.
        raise RuntimeError(result.stderr.decode(errors='replace')[-1800:])
    return result.stdout.decode(errors='replace')


def request(url, password=None, *, body=None, origin=None):
    headers={}
    if password:
        headers['Authorization']='Basic '+base64.b64encode(('friend:'+password).encode()).decode()
    if origin is not None:headers['Origin']=origin
    if body is not None:headers['Content-Type']='application/json'
    req=Request(url,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    for attempt in range(8):
        try:
            with urlopen(req,timeout=120 if body else 15) as response:
                return response.status,response.read()
        except HTTPError as error:
            return error.code,error.read()
        except URLError as error:
            # Newly assigned tunnel names can take a moment to propagate. Retry
            # DNS failures only for POST, so a submitted query is never replayed.
            if attempt==7 or body is not None and not isinstance(error.reason,socket.gaierror):
                raise
            time.sleep(2)


def ensure_ready():
    for _ in range(20):
        try:
            status,body=request('http://localhost:8090/api/status')
            if status==200 and json.loads(body).get('ready'):return
        except (OSError,URLError):pass
        time.sleep(2)
    raise RuntimeError('Local web API not ready; tunnel was not opened')


def verify(url, password, *, run_query=False):
    checks={}
    for path in ('/','/api/status','/app.js','/api/query'):
        status,_=request(url+path)
        checks['unauthenticated_'+path]=status==401
    status,_=request(url+'/api/status','incorrect-password')
    checks['wrong_password_rejected']=status==401
    status,body=request(url+'/api/status',password)
    checks['authenticated_status_ready']=status==200 and json.loads(body).get('ready') is True
    status,body=request(url+'/',password)
    checks['authenticated_page']=status==200 and b'question-form' in body
    status,_=request(url+'/.private/friend-access.json',password)
    checks['private_files_not_served']=status==404
    for origin in ('https://untrusted.example',''):
        status,_=request(url+'/api/query',password,body={'question':'hello'},origin=origin)
        checks['bad_origin_'+('missing' if not origin else 'foreign')]=status==403
    status,body=request(url+'/api/query',password,body={'question':'Show total completed sales'},origin=url)
    answer=json.loads(body)
    checks['authenticated_clarification']=status==200 and answer.get('status')=='clarification' and answer.get('model_calls')==0
    if run_query:
        status,body=request(url+'/api/query',password,body={'question':'How many completed invoices in October 2011?'},origin=url)
        result=json.loads(body)
        checks['actual_spark_result']=status==200 and result.get('status')=='executed' and result.get('result',{}).get('rows')==[[2040]]
        checks['opa_pre_post_allowed']=len(result.get('policy_trace',[]))==2 and all(d.get('allow') for d in result.get('policy_trace',[]))
    report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'transport':'actual public HTTPS through password-protected gateway',
            'credentials_included':False,'public_url_included':False}
    (ROOT/'reports/friend-access-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not all(checks.values()):raise RuntimeError('Gateway verification failed: '+str(checks))
    return report


def start(rotate=False):
    PRIVATE.mkdir(exist_ok=True)
    # Remove the external route before touching credentials or the gateway.
    command(COMPOSE+['stop','friend-tunnel'],timeout=30)
    credential_path=PRIVATE/'friend-access.json'
    if credential_path.exists() and not rotate:
        credentials=json.loads(credential_path.read_text(encoding='utf-8'))
        password=credentials['password']
    else:
        password=secrets.token_urlsafe(24)
    digest=command(['docker','run','--rm','-i','--entrypoint','caddy',CADDY,'hash-password'],data=(password+'\n').encode(),timeout=30).strip()
    if not re.fullmatch(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',digest):
        raise RuntimeError('Invalid password hash; tunnel remains stopped')
    (PRIVATE/'friend-auth.caddy').write_text('basic_auth {\n    friend '+digest+'\n}\n',encoding='utf-8')
    credentials={'username':'friend','password':password}
    credential_path.write_text(json.dumps(credentials,indent=2),encoding='utf-8')
    ensure_ready()
    command(COMPOSE+['run','--rm','--no-deps','friend-gateway','caddy','validate','--config','/etc/caddy/Caddyfile','--adapter','caddyfile'])
    command(COMPOSE+['up','-d','--no-deps','--force-recreate','friend-gateway'])
    command(COMPOSE+['up','-d','--no-deps','--force-recreate','friend-tunnel'])
    url=None
    try:
        for _ in range(30):
            logs=command(COMPOSE+['logs','--no-color','friend-tunnel'])
            matches=re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',logs)
            if matches:
                url=matches[-1]
                try:
                    status,_=request(url+'/api/status')
                    if status==401:break
                except (OSError,URLError):pass
            time.sleep(2)
        else:raise RuntimeError('Tunnel did not become ready')
        verify(url,password,run_query=True)
    except Exception:
        command(COMPOSE+['stop','friend-tunnel'],timeout=30)
        raise
    credentials['url']=url
    credential_path.write_text(json.dumps(credentials,indent=2),encoding='utf-8')
    (PRIVATE/'friend-access.txt').write_text(
        'Customer Intelligence temporary friend access\n\nURL: '+url+
        '\nUsername: friend\nPassword: '+password+
        '\n\nOpen the URL and enter these credentials in the browser prompt.\n'
        'The host computer, Ollama and Docker must stay running. One query at a time.\n'
        'Stop sharing: python scripts/friend_access.py stop\n',encoding='utf-8')
    print(json.dumps({'status':'ready','url':url,'credentials_file':'.private/friend-access.txt'}))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['start','stop','verify'])
    parser.add_argument('--rotate',action='store_true')
    args=parser.parse_args()
    if args.action=='stop':
        command(COMPOSE+['stop','friend-tunnel','friend-gateway'],timeout=30)
        print('Friend access stopped. Local application is unchanged.')
    elif args.action=='start':start(args.rotate)
    else:
        saved=json.loads((PRIVATE/'friend-access.json').read_text(encoding='utf-8'))
        print(json.dumps(verify(saved['url'],saved['password'],run_query=True)))


if __name__=='__main__':main()
