"""Upload saved Customer Intelligence scores to the local Langfuse instance."""
import argparse
import base64
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from evaluate_hallucination import export_scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--env-file', type=Path, default=Path('.private/langfuse/.env'))
    args = parser.parse_args()
    config = dict(line.split('=', 1) for line in args.env_file.read_text().splitlines()
                  if line.strip() and not line.startswith('#'))
    base = 'http://localhost:3000'
    public = config['LANGFUSE_INIT_PROJECT_PUBLIC_KEY']
    secret = config['LANGFUSE_INIT_PROJECT_SECRET_KEY']
    os.environ.update(LANGFUSE_BASE_URL=base, LANGFUSE_HOST=base,
                      LANGFUSE_PUBLIC_KEY=public, LANGFUSE_SECRET_KEY=secret)
    report = json.loads(args.report.read_bytes())
    export_scores(report)

    from langfuse import get_client

    wanted = {}
    trace_ids = []
    for row in report['cases']:
        trace = get_client().create_trace_id(seed=f"{report['run_id']}:{row['id']}")
        trace_ids.append(trace)
        for name in ('faithfulness', 'sql_result_correctness', 'case_correctness', 'has_ungrounded_claim'):
            if row[name] is not None:
                wanted[f'{trace}-{name}'] = float(row[name])
    auth = base64.b64encode(f'{public}:{secret}'.encode()).decode()
    pending = dict(wanted)
    deadline = time.monotonic() + 90
    while pending and time.monotonic() < deadline:
        for i in range(0, len(trace_ids), 20):
            query = urlencode({'traceId': ','.join(trace_ids[i:i + 20]), 'limit': 100})
            request = Request(f'{base}/api/public/v3/scores?{query}',
                              headers={'Authorization': f'Basic {auth}'})
            with urlopen(request, timeout=10) as response:
                for score in json.load(response)['data']:
                    ident = score['id']
                    if ident in pending and score['value'] == pending[ident]:
                        del pending[ident]
        if pending:
            time.sleep(3)
    if pending:
        raise SystemExit(f'Langfuse read-back confirmed {len(wanted)-len(pending)}/{len(wanted)} scores.')
    print(f'Langfuse read-back confirmed {len(wanted)} scores for {len(trace_ids)} cases.')


if __name__ == '__main__':
    main()
