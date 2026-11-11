"""Render verified full-bank, holdout, and judge-calibration results."""
import argparse
import json
from pathlib import Path

from summarize_benchmark import summarize


def read(path):
    return json.loads(path.read_bytes())


def runtime(source):
    provenance = source['pre_run_provenance']
    files = {k: v for k, v in provenance['files_sha256'].items()
             if not k.startswith('evaluation/')}
    return source['build_run_id'], provenance['model'], files


def result_label(group):
    result = group['groups']['sql']['all']
    return f"{result['correct']}/{result['total']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('full_report', type=Path)
    parser.add_argument('full_bank', type=Path)
    parser.add_argument('holdout_report', type=Path)
    parser.add_argument('holdout_bank', type=Path)
    parser.add_argument('calibration', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--retest', type=Path)
    parser.add_argument('--fresh', type=Path, nargs=2, metavar=('REPORT', 'BANK'))
    args = parser.parse_args()
    full_source = read(args.full_report)
    held_source = read(args.holdout_report)
    full = summarize(full_source, args.full_bank)
    holdout = summarize(held_source, args.holdout_bank)
    if runtime(full_source) != runtime(held_source):
        raise ValueError('The development and holdout runs used different runtime inputs.')
    calibration = read(args.calibration)
    if calibration['status'] != 'completed':
        raise ValueError('Judge calibration did not complete.')
    judge = calibration['summary']
    rows = []
    for key, title in [('sql', 'เทียบผล SQL'), ('formula', 'ขอสูตร'), ('clarification', 'ควรถามกลับ')]:
        group = full['groups'][key]
        cells = ''.join(
            f"<td>{group[lang]['correct']}/{group[lang]['total']}</td>"
            for lang in ('all', 'th', 'en')
        )
        rows.append(f"<tr><th scope='row'>{title}</th>{cells}</tr>")
    row = holdout['groups']['sql']
    followup = ''
    if args.retest and args.fresh:
        retest_source, fresh_source = read(args.retest), read(args.fresh[0])
        if runtime(retest_source) != runtime(fresh_source):
            raise ValueError('Retest and fresh run used different runtime inputs.')
        retest = summarize(retest_source, args.holdout_bank)
        fresh = summarize(fresh_source, args.fresh[1])
        followup = (
            '<section><h2>ผลหลังแก้การสร้างและตรวจ SQL</h2>'
            f'<p>โจทย์เดิมที่ใช้ตรวจซ้ำ <strong>{result_label(holdout)} → {result_label(retest)}</strong></p>'
            f'<p>โจทย์ใหม่อีกชุด <strong>{result_label(fresh)}</strong> ตรงผลอ้างอิง</p>'
            '<p>ชุดพัฒนา 200 ข้อด้านล่างเป็นผลก่อนแก้</p></section>'
        )
    page = f"""<!doctype html>
<html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ผลประเมิน Customer Intelligence</title>
<style>
body{{margin:0;background:#f1f5f7;color:#152b38;font:16px/1.55 'Segoe UI',Tahoma,sans-serif}}
main{{max-width:840px;margin:auto;padding:28px 20px}}
section{{margin:16px 0;padding:16px 20px;background:#fff;border-radius:12px}}
h1,h2{{margin:0}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;text-align:right;border-bottom:1px solid #d8e4e8}}
th:first-child{{text-align:left}}
</style>
<main><h1>ผลประเมิน Customer Intelligence</h1>{followup}
<section><h2>ชุดพัฒนา {full['total']} ข้อ</h2>
<table><thead><tr><th scope="col">ประเภท</th><th scope="col">รวม</th>
<th scope="col">ไทย</th><th scope="col">อังกฤษ</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p>ตัวเลขแต่ละช่องคือจำนวนข้อที่ผ่านจากจำนวนข้อที่ทดสอบ</p></section>
<section><h2>ชุดคำถาม SQL ใหม่ {holdout['total']} ข้อ</h2>
<p>ตรงผลอ้างอิง <strong>{row['all']['correct']}/{row['all']['total']}</strong>
 · ไทย {row['th']['correct']}/{row['th']['total']}
 · อังกฤษ {row['en']['correct']}/{row['en']['total']}</p>
<p>โจทย์และ SQL อ้างอิงจัดทำก่อนรันโดยทีมโครงการ ใช้ทดสอบกับโค้ดชุดเดิม</p></section>
<section><h2>ทดสอบตัวตรวจคำอธิบาย</h2>
<p>จับข้อความผิดได้ <strong>{judge['tp']}/{judge['tp'] + judge['fn']}</strong>
 · พลาด {judge['fn']} · แจ้งผิด {judge['fp']} · ข้อความที่รองรับและให้ผ่าน {judge['tn']}
 · ตัวอย่างที่ตัดสินไม่ได้ {judge['unscored']}</p>
<p>ชุดควบคุมจัดทำขึ้นเพื่อทดสอบตัวตรวจ ยังรอการตรวจจากคนแยกต่างหาก</p>
</section></main></html>"""
    args.output.write_text(page, encoding='utf-8')


if __name__ == '__main__':
    main()
