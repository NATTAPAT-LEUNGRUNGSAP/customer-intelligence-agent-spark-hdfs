"""Build a version-specific report from completed actual runs; no fabricated scores."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    evaluation_path=max(REPORTS.glob('rag-v2.4-holdout-*.json'),key=lambda p:p.stat().st_mtime)
    retrieval_path=max(REPORTS.glob('retrieval-v2.4-holdout-*.json'),key=lambda p:p.stat().st_mtime)
    evaluation,retrieval=read(evaluation_path),read(retrieval_path)
    freeze=read(REPORTS/'freeze-rag-v2.4.json')
    assert evaluation['status']==retrieval['status']=='completed'
    assert evaluation['benchmark']==retrieval['benchmark']==freeze['benchmark']=='rag_holdout_v6.json'
    assert len(evaluation['cases'])==len(retrieval['cases'])==20
    hashes=freeze['provenance']['files_sha256']
    assert evaluation['provenance']['files_sha256']==retrieval['provenance']['files_sha256']==hashes
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in hashes.items())
    assert evaluation['provenance']['model']['digest']==freeze['provenance']['model']['digest']
    assert evaluation['build_run_id']==freeze['build_run_id']
    e,r=evaluation['summary'],retrieval['summary']
    passed=evaluation['quality_passed'] and retrieval['quality_passed']
    failures=[{'id':c['id'],'question':c['question'],'status':c['result']['status'],
               'sql':c['result'].get('sql'),'actual':c['result'].get('result'),'gold':c.get('gold'),
               'attempts':c['result'].get('attempts',[])} for c in evaluation['cases'] if not c['correct']]
    publication=read(REPORTS/'github-publication.json') if (REPORTS/'github-publication.json').exists() else {'status':'pending'}
    summary={'version':'v2.4','status':'completed','quality_passed':passed,
             'source_reports':{'evaluation':evaluation_path.name,'retrieval':retrieval_path.name,
                               'freeze':'freeze-rag-v2.4.json'},
             'end_to_end':e,'retrieval':r,'failures':failures,
             'checks':{'end_to_end':evaluation['quality_checks'],'retrieval':retrieval['quality_checks']},
             'prior_failed_holdouts':[
                 'rag-v2.2-holdout-c348d44e7954423bbb96cf06274833af.json',
                 'retrieval-v2.3-holdout-526ff78dfbf241c4a6856140962f8152.json',
                 'rag-v2.3-holdout-f3efa4011cdf461697b7dbabee6d6c54.json'],
             'github_publication':publication}
    (REPORTS/'delivery-quality-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Customer Intelligence Agent with Spark & HDFS — v2.4',
           '', 'Date: 26 October 2026 (Asia/Bangkok). Deadline: 9 November 2026.', '',
           f'Current measured project-gate decision: **{"PASS" if passed else "FAIL"}**.',
           'Small developer-authored benchmark on supported families; not external certification.',
           'The 20 v6 country/period/subgroup combinations were authored before freeze and not run',
           'through the agent before the final evaluation. This is not a test of unseen domains.', '',
           '| Metric | Actual | Gate |','|---|---:|---:|',
           f"| Recall@6 | {r['recall_at_6']:.2%} | >=95% |",
           f"| MRR@6 | {r['mrr_at_6']:.4f} | >=0.85 |",
           f"| nDCG@6 | {r['ndcg_at_6']:.4f} | >=0.80 |",
           f"| Retrieval p95 | {r['latency_p95_ms']:.2f} ms | <=50 ms |",
           f"| Spark result accuracy | {e['correct']}/{e['total']} ({e['accuracy']:.0%}) | >=90% |",
           f"| Clarification accuracy | {e['clarification_accuracy']:.0%} | 100% |",
           f"| Citation ID validity across traces | {e['citation_validity']:.0%} | 100% |",
           f"| Relevant evidence citation rate | {e['cited_relevant_evidence_rate']:.0%} | >=95% |",
           f"| Warm query p95 | {e['latency_p95_seconds']:.2f} s | <=20 s |", '',
           f"Executed={e['executed']}; failed/error={e['failed_or_error']}; model calls={e['model_calls']}.",
           'Warm-query timing excludes Spark application/view startup. Citation validity concerns',
           'supplied evidence IDs, including IDs retained on failed attempts; it does not certify',
           'correct answers or entailment. Failed answers always count wrong in accuracy.', '',
           '## Implemented application and harness', '',
           '- Local web UI calls actual RAG/Agent/Spark, with rows, SQL/evidence and trace.',
           '- SQL generation remains dynamic; no gold SQL or query catalog is provided to the agent.',
           '- Identified population AST and limited result contracts; scalar-pair output contract.',
           '- Date-trunc syntax validation with corrective feedback; bounded three-attempt repair.',
           '- Retrieval separates imperative return from refund lines and recognizes repeat phrasing.',
           '- Context selection, latest repair state, heuristic budget and actual Ollama token telemetry.',
           '- Public GitHub source published: https://github.com/NATTAPAT-LEUNGRUNGSAP/customer-intelligence-agent-spark-hdfs .',
           '- Actual GitHub CI unit job passed: actions/runs/40284829764. Local distributed checks are separate.', '',
           '## Actual checks and retained failures', '',
           '- Smoke fcde70a71325433185dbaace442f66c9: 2 workers, 3-row HDFS roundtrip, totals 1500/2500.',
           '- Unit suite: 25 passed in Docker (candidate-v2.4-unit-tests-complete.log).',
           '- v2.4 exposed regression-v5: 20/20 correct; separate from new v6 result above.',
           '- Earlier context stress: 0/400/1200 distractor characters, correct invoice count2040;',
           '  oversized prompt blocked before model/SQL. This does not prove long-context robustness.',
           '- v2.2 new v4: 18/20; overall gate FAIL. Bad date_trunc and an overbroad Inactive rule.',
           '- v2.3 new v5: 18/20; overall gate FAIL. MRR0.825 and citation validity95%.',
           '- All raw reports/freeze records retained. No threshold was lowered.',
           '- An extra-output prompt experiment regressed exposed v4 to18/20; reverted before freeze.', '',
           '## Final-case failures', '',
           ('None in these 20 cases; this is not a claim of general perfect accuracy.' if not failures else
            '\n'.join(f"- {f['id']}: {f['status']} — {f['question']}" for f in failures)), '',
           '## Reproduction and limits', '',
           'See README.md, docs/WEB_APP.md, evaluation/README.md and freeze-rag-v2.4.json.',
           f'Raw current results: {evaluation_path.name}; {retrieval_path.name}.',
           'The source/corpus/config/model hashes match the pre-run freeze; no runtime tuning',
           'after this final run. Historical v2.1 scores remain in FINAL_REPORT.md.',
           'Single physical host; no user authentication; best-effort Spark cancellation.',
           'Context input size is a heuristic, not exact tokenization; post-generation counts cannot',
           'guarantee detection of server-side truncation. No general context-rot solution is claimed.',
           'OPA, formal ontology/cross-organization schema matching remain unimplemented.',
           'MongoDB Policy Storage and Churn/Campaign are excluded from this delivery.',
           'Fresh local Git checkout matched the complete host source inventory and covered frozen core;',
           '25 unit tests passed from that checkout. See git-checkout-verification.json.',
           'Web assets/PowerShell launchers are supplemental post-verification host inventory entries,',
           'because they are not mounted into the Spark-job pre-run freeze. See checkout-unit-tests.txt.',
           'Actual final browser demo: web-v2.4-demo-summary.json, correct identified ranking,12.05s sample.',
           'A fresh full data acquisition/build on a separate machine remains unverified.', '']
    (REPORTS/'DELIVERY_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'quality_passed':passed,'correct':e['correct'],'total':e['total'],'failures':len(failures)}))


if __name__=='__main__':
    main()
