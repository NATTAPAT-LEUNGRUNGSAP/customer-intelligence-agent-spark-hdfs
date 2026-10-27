"""Verify publication source and model match the completed live-model run."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from sql_guard import validate_sql
from question_scope import validate_month_comparison
from provenance import fingerprint
root=Path('/app')
run=json.loads((root/'reports/bilingual-development-final.json').read_text(encoding='utf-8'))
assert run['status']=='completed' and run['source_unchanged'] and run['bank_unchanged']
current=fingerprint(root,endpoint='http://host.docker.internal:11434',model='qwen3.5:9b')
old=run['post_run_provenance']
changes=sorted(k for k in set(current['files_sha256'])|set(old['files_sha256']) if current['files_sha256'].get(k)!=old['files_sha256'].get(k))
assert not changes,changes
assert current['model']==old['model']
checks=[];monthly=[];proposals=0
for case in run['cases']:
    result=case['result']
    proposals+=sum(isinstance(a.get('sql'),str) for a in result.get('attempts',[]))
    if result.get('sql'):proposals+=1
    if result['status']=='executed':
        validate_sql(result['sql'])
        checks.append({'id':case['id'],'final_sql_allowed':True})
        if case['family']=='monthly_max':
            validate_month_comparison(result['sql'])
            monthly.append({'id':case['id'],'highest_month_contract_passed':True})
report={'status':'passed','method':'publication fingerprint verification and deterministic final SQL replay; no additional model calls',
        'same_source_as_full_run':True,'same_model_as_full_run':True,'changed_source_files':changes,
        'sql_proposals_recorded':proposals,'executed_sql_checked':len(checks),
        'monthly_semantic_checks':monthly,'current_files_sha256':current['files_sha256'],'checks':checks}
(root/'reports/bilingual-release-guard-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('current_files_sha256','checks')}))
