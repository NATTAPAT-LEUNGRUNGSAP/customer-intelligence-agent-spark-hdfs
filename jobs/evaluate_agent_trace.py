"""Summarize saved answers without treating execution as correctness."""
import argparse
import json
from pathlib import Path


def summarize(records):
    total = len(records)
    executed = sum(r.get('status') == 'executed' for r in records)
    return {'answers':total, 'executed':executed,
            'repaired_executions':sum(r.get('status') == 'executed' and bool(r.get('attempts')) for r in records),
            'metadata_tool_observations':sum(len(e.get('observations', [])) for r in records for e in r.get('agent_trace', [])),
            'model_calls':sum(r.get('model_calls',0) for r in records),
            'execution_rate':executed/total if total else None,
            'answer_accuracy':None, 'accuracy_note':'Use expected-result evaluation; execution is not correctness.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('answers', help='JSON array of answer records')
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(Path(args.answers).read_text(encoding='utf-8'))), indent=2))
