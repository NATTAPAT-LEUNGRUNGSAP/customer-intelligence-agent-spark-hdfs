"""Upload saved Customer Intelligence scores to the local Langfuse instance."""
import argparse
import base64
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from evaluate_hallucination import export_scores, public_benchmark_questions


def execution_details(case, public_question):
    answer = case['result']
    result = answer.get('result')
    inputs = {
        'รหัสข้อ': case['id'],
        'คำถาม': public_question if public_question == case['question'] else None,
    }
    outputs = {
        'สถานะ': answer['status'],
        'SQL ที่รัน': answer.get('executed_sql'),
        'ข้อความที่ตอบ': answer.get('message') or answer.get('error') or answer.get('explanation'),
    }
    if result is not None:
        columns = result['columns']
        rows = result['rows']
        outputs['ผลจาก Spark'] = {
            'คอลัมน์': columns,
            'แถว': [[('[ปิดรหัสลูกค้า]' if value is not None else None)
                     if column.lower() == 'customer_id' else value
                     for column, value in zip(columns, values, strict=True)] for values in rows],
            'จำนวนแถวที่คืนมา': len(rows),
            'ถูกตัดตามเพดานผลลัพธ์': result['truncated'],
        }
    return inputs, outputs


def backfill_details(report, source, client):
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != report['source_sha256']:
        raise SystemExit('The source report does not match the score report.')
    cases = {case['id']: case for case in json.loads(data)['cases']}
    questions = public_benchmark_questions()
    detail_name = 'คำถาม SQL และผลที่ได้'
    expected = {}
    missing = []

    def observations(trace):
        return client.api.observations.get_many(trace_id=trace, fields='core,basic,io').data

    for row in report['cases']:
        case = cases[row['id']]
        trace = client.create_trace_id(seed=f"{report['run_id']}:{row['id']}")
        saved = observations(trace)
        root = next((item for item in saved if item.name == 'offline-analytics-evaluation'), None)
        if root is None:
            raise SystemExit(f"Original observation missing for {row['id']}.")
        inputs, outputs = execution_details(case, questions.get(row['id']))
        detail = next((item for item in saved if item.name == detail_name
                       and item.parent_observation_id == root.id), None)
        if detail is None:
            missing.append((trace, root.id, inputs, outputs))
        else:
            expected[trace] = (detail.id, root.id, inputs, outputs)

    for trace, parent, inputs, outputs in missing:
        with client.start_as_current_observation(
            name=detail_name, trace_context={'trace_id': trace, 'parent_span_id': parent},
            input=inputs, output=outputs,
        ) as detail:
            expected[trace] = (detail.id, parent, inputs, outputs)
    client.flush()
    total = len(expected)
    deadline = time.monotonic() + 90
    while expected and time.monotonic() < deadline:
        for trace, (ident, parent, inputs, outputs) in list(expected.items()):
            if any(item.id == ident and item.parent_observation_id == parent
                   and decode_payload(item.input) == inputs and decode_payload(item.output) == outputs
                   for item in observations(trace)):
                del expected[trace]
        if expected:
            time.sleep(3)
    if expected:
        raise SystemExit(f'Langfuse confirmed details for {total - len(expected)}/{total} traces.')
    print(f'Langfuse confirmed details for {total} traces ({len(missing)} added).')


def decode_payload(payload):
    return json.loads(payload) if isinstance(payload, str) else payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--env-file', type=Path, default=Path('.private/langfuse/.env'))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--backfill-details', type=Path, metavar='SOURCE_REPORT',
                      help='Add details to existing traces using the original benchmark report.')
    mode.add_argument('--faithfulness-pass', action='store_true',
                        help='Add pass/fail scores to previously uploaded SQL cases.')
    args = parser.parse_args()
    config = dict(line.split('=', 1) for line in args.env_file.read_text().splitlines()
                  if line.strip() and not line.startswith('#'))
    base = 'http://localhost:3000'
    public = config['LANGFUSE_INIT_PROJECT_PUBLIC_KEY']
    secret = config['LANGFUSE_INIT_PROJECT_SECRET_KEY']
    os.environ.update(LANGFUSE_BASE_URL=base, LANGFUSE_HOST=base,
                      LANGFUSE_PUBLIC_KEY=public, LANGFUSE_SECRET_KEY=secret)
    report = json.loads(args.report.read_bytes())
    if report.get('status') != 'completed' or not report.get('cases'):
        parser.error('A completed score report is required.')

    from langfuse import get_client

    client = get_client()
    if args.backfill_details:
        backfill_details(report, args.backfill_details, client)
        return
    if args.faithfulness_pass:
        if not client.auth_check():
            raise SystemExit('Langfuse authentication failed.')
    else:
        export_scores(report)

    wanted = {}
    trace_ids = []
    for row in report['cases']:
        trace = client.create_trace_id(seed=f"{report['run_id']}:{row['id']}")
        if args.faithfulness_pass and row['sql_result_correctness'] is None:
            continue
        trace_ids.append(trace)
        if args.faithfulness_pass:
            name = 'faithfulness_pass'
            ident = f'{trace}-{name}'
            value = float(row['faithfulness'] == 1.0)
            wanted[ident] = value
            client.create_score(name=name, value=value, data_type='NUMERIC',
                                trace_id=trace, score_id=ident,
                                comment=('Unscored explanation counts as a fail under the reporting rule.'
                                         if row['faithfulness'] is None else
                                         'Pass requires full support according to the automated judge.'))
            continue
        for name in ('faithfulness', 'sql_result_correctness', 'case_correctness', 'has_ungrounded_claim'):
            if row[name] is not None:
                wanted[f'{trace}-{name}'] = float(row[name])
    if not wanted:
        raise SystemExit('No eligible scores found.')
    if args.faithfulness_pass:
        client.flush()
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
    if args.faithfulness_pass:
        print(f'Faithfulness pass: {sum(wanted.values()):.0f}/{len(wanted)}.')


if __name__ == '__main__':
    main()
