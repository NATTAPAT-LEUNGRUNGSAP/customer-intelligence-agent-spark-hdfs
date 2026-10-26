"""Derive explicit admission populations from immutable context experiment traces."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'jobs'))
from rag_metrics import percentile95


def main():
    reports=ROOT/'reports'
    source=max(reports.glob('context-v2-*.json'),key=lambda p:p.stat().st_mtime)
    run=json.loads(source.read_text(encoding='utf-8'))
    assert run['status']=='completed'
    assert len(run['stress'])==42 and len(run['regression'])==20
    hashes=run['provenance']['files_sha256']
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in hashes.items())
    normalized={}
    for strategy in ('managed','unfiltered'):
        rows=[r for r in run['stress'] if r['strategy']==strategy]
        before=[r for r in rows if r['result'].get('context_blocked') and r['result'].get('model_calls',0)==0]
        during=[r for r in rows if r['result'].get('context_blocked') and r['result'].get('model_calls',0)>0]
        completed=[r for r in rows if not r['result'].get('context_blocked')]
        called=[r for r in rows if r['result'].get('model_calls',0)>0]
        normalized[strategy]={'trials':len(rows),'correct':sum(r['correct'] for r in rows),
            'blocked_before_model':len(before),'blocked_after_model_call':len(during),
            'ever_called_model':len(called),'correct_given_model_called':sum(r['correct'] for r in called),
            'no_budget_block_trials':len(completed),'correct_without_budget_block':sum(r['correct'] for r in completed),
            'non_budget_failures':sum(not r['correct'] for r in completed),
            'wrong_executed_results':sum(not r['correct'] and r['result']['status']=='executed' for r in rows),
            'no_budget_block_p95_seconds':percentile95([r['elapsed_seconds'] for r in completed]),
            'prompt_tokens_min':run['summary'][strategy]['actual_prompt_tokens_min'],
            'prompt_tokens_max':run['summary'][strategy]['actual_prompt_tokens_max'],
            'unique_packet_hashes':run['summary'][strategy]['unique_packet_hashes'],
            'retention':run['summary'][strategy]['selected_evidence_retention']}
        assert len(before)+len(during)+len(completed)==len(rows)
    summary={'status':'completed','component':'Context v2','quality_passed':run['quality_passed'],
             'source_report':source.name,'source_core_hashes_match':True,
             'regression_correct':run['regression_correct'],'regression_total':run['regression_total'],
             'matrix':normalized,
             'population_note':'Raw admitted_count excludes any trial budget-blocked at any stage. This summary separately reports initial model calls and repair-stage blocks.',
             'prior_candidate':{'report':'context-v1-9d66b9e8b1ab45c7bef19fabaf693ae4.json',
                                'regression_correct':18,'regression_total':20,'default_adopted':False},
             'limitations':['exposed questions, not fresh holdout','three unique managed packets repeated21 times',
                            'caller-marked optional noise, not arbitrary noise inside required evidence',
                            'heuristic token preflight; actual observed prompts below 3000 tokens',
                            'not proof of a general solution to model context rot']}
    (reports/'context-quality-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    m,u=normalized['managed'],normalized['unfiltered']
    text=f'''# Context engineering — measured Context v2

Controlled local experiment on Qwen3.5:9b, Spark and HDFS. Protocols were recorded
before their runs. Both arms use mandatory RAG. This is not a fresh holdout or an
independent evaluation of general context-rot prevention.

## Actual results

| Measure | Managed | Unfiltered control |
|---|---:|---:|
| Controlled trials (3 exposed tasks) | {m['trials']} | {u['trials']} |
| Correct result | {m['correct']} | {u['correct']} |
| Budget rejection before any model call | {m['blocked_before_model']} | {u['blocked_before_model']} |
| Budget rejection after model work started | {m['blocked_after_model_call']} | {u['blocked_after_model_call']} |
| Trials that ever called the model | {m['ever_called_model']} | {u['ever_called_model']} |
| Correct among trials that called model | {m['correct_given_model_called']} | {u['correct_given_model_called']} |
| Other unsuccessful trials | {m['non_budget_failures']} | {u['non_budget_failures']} |
| Incorrect executed result delivered | {m['wrong_executed_results']} | {u['wrong_executed_results']} |
| Selected ID/text retained verbatim | {m['retention']:.0%} | {u['retention']:.0%} |
| Actual prompt token range, observed calls | {m['prompt_tokens_min']}–{m['prompt_tokens_max']} | {u['prompt_tokens_min']}–{u['prompt_tokens_max']} |
| Unique evidence packet hashes | {m['unique_packet_hashes']} | {u['unique_packet_hashes']} |

Ordinary exposed regression: **{run['regression_correct']}/{run['regression_total']} correct**.
Actual unit suite: **31 passed** (context-v2-unit-tests.log).
All predeclared Context v2 checks: **{'PASS' if run['quality_passed'] else 'FAIL'}**.

Background lengths were 0/3000/12000 characters. Evidence appeared at front/middle/end
of the packet. A fixed shuffled order produced 42 trials:21 in each arm.

## What changed

- Selected RAG facts and original task constraints remain intact, with packet hashes
  and deduplication/conflict checks. Production uses the validated evidence formatting.
- Caller-marked nonessential background is omitted before inference in managed mode.
- Repairs retain the original task/facts and latest SQL/citations/short error, without
  old explanations or full Spark plans. 50 repairs are a unit simulation, not 50 model turns.
- Oversized required input is stopped rather than silently truncating it or retrying
  the same impossible request. The trace distinguishes a preflight stop from a call
  already made before a postflight violation or later repair budget stop.
- Model token counts, budget margins and evidence assembly are visible in the trace/UI.

## Negative result retained

The first candidate stripped metadata and changed evidence serialization. All selected
fact text was retained, and stress trials passed, but exposed regression fell to 18/20.
That representation was not adopted as the default. After preserving the prior
representation, the repeated regression returned to 20/20. A single small experiment
does not establish which individual formatting change caused the difference.
Raw V1 report: context-v1-9d66b9e8b1ab45c7bef19fabaf693ae4.json.

## Interpretation and remaining weaknesses

These results support a narrow claim: selecting context and bounding repair state
can prevent budget-related failures in this controlled setting while preserving the
tested ordinary task behavior. They do not show that model-internal context rot has
been solved. Optional noise was labeled by the caller; noise inside required facts
was not tested. Managed packet position becomes identical after noise is removed:
the 21 managed trials are repetitions of 3 packets, not21 independent long-context tasks.

The 6000-token preflight estimate remains heuristic and overestimates many observed
requests. Budget rejection therefore does not prove the original text could not fit
the 8192-token model window. Actual served prompts in this run were below 3000 tokens;
this does not test model behavior near the full window. Post-generation counters do
not guarantee detection of server-side truncation. Exact model/template-matched
tokenization, harder retained-noise tests and independent cases remain future work.

Do not present the overall managed/unfiltered success gap as a pure model reasoning
or context-rot improvement: most control losses are application budget policy stops.
Raw report admitted_count means no budget block at any stage; use the separately
reported initial-call and repair-block populations above to avoid selection bias.

## Reproduce

Stop the web service to free Spark worker resources, then run:

```powershell
docker compose run --rm --no-deps --use-aliases spark-job --master spark://spark-master:7077 --conf spark.driver.host=spark-job --conf spark.driver.bindAddress=0.0.0.0 --conf spark.executor.memory=512m /app/jobs/evaluate_context.py
```

The current source and covered pre-run fingerprints match {source.name}.
Hashes cover the files mounted into Spark-job; UI assets are verified separately.
Original frozen v2.4 scores are historical; current source includes this extension.
See [design and limits](../docs/CONTEXT_ENGINEERING.md), context-quality-summary.json,
and evaluation/context_protocol_v2.json. Replay results must retain their own source
fingerprints; a protocol replay with changed code is not the original experiment.
'''
    (reports/'CONTEXT_REPORT.md').write_text(text,encoding='utf-8')
    print(json.dumps({'report':'CONTEXT_REPORT.md','regression':run['regression_correct'],'matrix':normalized}))


if __name__=='__main__':
    main()
