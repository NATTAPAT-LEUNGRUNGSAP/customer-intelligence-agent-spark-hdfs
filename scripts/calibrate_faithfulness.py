"""Compare the current judge with pre-labeled supported and unsupported statements."""
import argparse
import json
from pathlib import Path

from evaluate_hallucination import judge, score_claims


# Each pair changes one fact. Expected labels are set before the judge runs.
PAIRS = [
    ('count-en', 'pair031-en', 'January 2011 had 34,306 sale lines.',
     'January 2011 had 34,360 sale lines.'),
    ('count-th', 'pair031-th', 'มกราคม 2011 มีรายการขาย 34,306 แถว',
     'มกราคม 2011 มีรายการขาย 34,360 แถว'),
    ('scope-en', 'pair076-en', 'November 2011 had the highest invoice count in the data.',
     'November 2011 had the highest total sales in the data.'),
    ('scope-th', 'pair076-th', 'พฤศจิกายน 2011 มีจำนวนใบสั่งซื้อสูงสุด',
     'ธันวาคม 2011 มีจำนวนใบสั่งซื้อสูงสุด'),
    ('aggregate-en', 'pair006-en', 'The SQL calculates the maximum invoice value.',
     'The SQL calculates the minimum invoice value.'),
    ('aggregate-th', 'pair001-th', 'SQL รวมยอดใบสั่งซื้อของเดือนมกราคม 2011',
     'SQL รวมยอดใบสั่งซื้อของเดือนกุมภาพันธ์ 2011'),
    ('coverage-en', 'pair026-en', 'The result groups the available 2011 data by month.',
     'The source contains a complete December 2011.'),
    ('coverage-th', 'pair026-th', 'ผลแยกยอดขายของปี 2011 ตามเดือน',
     'ข้อมูลครอบคลุมเดือนธันวาคม 2011 ครบทั้งเดือน'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--judge-model', default='qwen2.5:7b')
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding='utf-8'))
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    source_by_id = {case['id']: case for case in source['cases']}
    controls = []
    for pair, source_id, supported, unsupported in PAIRS:
        case = source_by_id[source_id]
        if not case['correct']:
            raise ValueError(f'Control source must match Gold SQL: {source_id}')
        answer = case['result']
        packet = dict(question=case['question'], executed_sql=answer['executed_sql'],
                      returned_result=answer['result'],
                      evidence={ref['id']: ref['text'] for ref in answer['references']})
        if pair.startswith('coverage'):
            packet['evidence']['observed_coverage'] = manifest['observed_max_timestamp']
        controls.extend((f'{pair}-{label}', dict(packet, displayed_answer=text), bool(label))
                        for label, text in [(0, supported), (1, unsupported)])
    report = {'status': 'running', 'judge_model': args.judge_model,
              'labels': 'project-authored synthetic controls, not independent human annotation',
              'cases': []}
    for case_id, packet, expected in controls:
        row = dict(id=case_id, statement=packet['displayed_answer'], expected_ungrounded=expected)
        try:
            row.update(score_claims(judge(packet, 'http://127.0.0.1:11434', args.judge_model)))
        except (OSError, ValueError, KeyError, TypeError) as error:
            row.update(has_ungrounded_claim=None, error_type=type(error).__name__)
        report['cases'].append(row)
        print(case_id, expected, row['has_ungrounded_claim'], flush=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    counts = dict.fromkeys(('tp', 'fp', 'tn', 'fn', 'unscored'), 0)
    for row in report['cases']:
        expected, actual = row['expected_ungrounded'], row['has_ungrounded_claim']
        if actual is None:
            counts['unscored'] += 1
        elif actual:
            counts['tp' if expected else 'fp'] += 1
        else:
            counts['fn' if expected else 'tn'] += 1
    report.update(status='completed', summary=counts)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(counts), flush=True)


if __name__ == '__main__':
    main()
