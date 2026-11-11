"""Summarize a completed benchmark against its original question bank."""
import argparse
import hashlib
import json
from pathlib import Path


def summarize(source, bank_path):
    data = bank_path.read_bytes()
    if source['status'] != 'completed' or not source.get('source_unchanged'):
        raise ValueError('Benchmark did not complete against frozen source.')
    if hashlib.sha256(data).hexdigest() != source['bank_sha256']:
        raise ValueError('Question bank does not match the run.')
    bank = {case['id']: case for case in json.loads(data)}
    rows = {case['id']: case for case in source['cases']}
    if bank.keys() != rows.keys() or len(rows) != len(source['cases']):
        raise ValueError('Expected every question exactly once.')
    groups = {}
    for kind, selected in (
        ('sql', [c for c in bank.values() if c.get('gold_sql')]),
        ('formula', [c for c in bank.values() if c.get('formula_id')]),
        ('clarification', [c for c in bank.values() if c.get('clarification_policy')]),
    ):
        groups[kind] = {}
        for lang in ('all', 'th', 'en'):
            subset = [c for c in selected if lang == 'all' or c['language'] == lang]
            if subset:
                groups[kind][lang] = dict(total=len(subset),
                                          correct=sum(rows[c['id']]['correct'] for c in subset))
    if sum(g.get('all', {}).get('total', 0) for g in groups.values()) != len(rows):
        raise ValueError('Questions are missing from, or duplicated across, result categories.')
    return {
        'bank_sha256': source['bank_sha256'], 'total': len(rows),
        'correct': sum(row['correct'] for row in rows.values()),
        'groups': groups, 'failed_ids': [r['id'] for r in rows.values() if not r['correct']],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('bank', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(args.report.read_bytes()), args.bank), indent=2))


if __name__ == '__main__':
    main()
