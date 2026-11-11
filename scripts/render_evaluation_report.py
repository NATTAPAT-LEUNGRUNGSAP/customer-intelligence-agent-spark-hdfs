"""Render a completed hallucination score report as an offline HTML table."""
import argparse
import json
from html import escape
from pathlib import Path

from evaluate_hallucination import summarize


def display_score(value):
    return '—' if value is None else f'{value:.2f}'


def render(report):
    if report.get('status') != 'completed':
        raise ValueError('Expected a completed score report.')
    cases = report['cases']
    families = sorted({case['family'] for case in cases})
    groups = [('รวม', cases)]
    groups.extend((label, [case for case in cases if case['language'] == language])
                  for language, label in [('th', 'ภาษาไทย'), ('en', 'ภาษาอังกฤษ')])
    groups.extend((family, [case for case in cases if case['family'] == family])
                  for family in families)
    rows = []
    for label, group in groups:
        metrics = summarize(group)
        rows.append(
            f"<tr><th scope='row'>{escape(label)}</th>"
            f"<td>{metrics['sql_cases_correct']}/{metrics['sql_cases']}</td></tr>"
        )
    overall = summarize(cases)
    unscored = [case for case in cases if case['faithfulness'] is None]
    reason_labels = {
        'not_applicable': 'ไม่มีคำอธิบายที่นำมาวัดได้',
        'no_claims': 'ผู้ตรวจไม่พบข้ออ้างในข้อความ',
        'missing_context': 'หลักฐานที่ใช้ตอบไม่ครบ',
        'input_too_large': 'ข้อมูลเกินขนาดที่ผู้ตรวจรับได้',
        'error': 'ผู้ตรวจประมวลผลไม่สำเร็จ',
    }
    reasons = ''.join(
        f"<li>{escape(case['id'])} · "
        f"{escape(reason_labels.get(case['judge_status'], case['judge_status']))} · "
        f"{escape(case['status'])}</li>"
        for case in unscored
    )
    incorrect = [case for case in cases if case['sql_result_correctness'] is False]
    failures = ''.join(
        f"<li>{escape(case['id'])} · {escape(case['family'])} · {escape(case['status'])}</li>"
        for case in incorrect
    )
    return f"""<!doctype html>
<html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Customer Intelligence | ผลประเมิน</title>
<style>
body{{margin:0;background:#f1f5f7;color:#152b38;font:16px/1.55 'Segoe UI',Tahoma,sans-serif}}
main{{max-width:960px;margin:auto;padding:32px 20px}}
h1{{font-size:clamp(1.5rem,4vw,2rem);margin-bottom:0}}
.scroll{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;background:white;font-variant-numeric:tabular-nums}}
th,td{{padding:10px;text-align:center;border-bottom:1px solid #d8e4e8}}
th:first-child{{text-align:left}}
thead,tr:first-child{{background:#deefe9}}
summary{{cursor:pointer}}
</style>
<main><h1>ระบบตอบโจทย์ SQL ถูกกี่ข้อ</h1>
<p><strong>{overall['sql_cases_correct']} จาก {overall['sql_cases']} ข้อ</strong> ให้ผลตรงกับคำตอบอ้างอิงที่รันบน Spark</p>
<div class="scroll"><table><thead><tr><th scope="col">กลุ่มคำถาม</th>
<th scope="col">ข้อที่ตอบตรง / ข้อที่ทดสอบ</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<details><summary>คำตอบที่ไม่ผ่าน Correctness ({len(incorrect)} ข้อ)</summary>
<ul>{failures}</ul></details>
<details><summary>ผลตรวจคำอธิบายสำหรับทีม</summary>
<p>โมเดลผู้ตรวจ {escape(report['judge_model'])} ให้ Faithfulness เฉลี่ย
{display_score(overall['mean_faithfulness'])} ใน {overall['faithfulness_scored']}
จาก {overall['cases']} ข้อที่ประเมินข้อความได้ ค่านี้เป็นผลจากตัวตรวจอัตโนมัติ</p>
<details><summary>คำตอบที่ไม่มีคะแนน Faithfulness ({len(unscored)} ข้อ)</summary>
<ul>{reasons}</ul></details></details>
<p>ชุดคำถามจากชุดพัฒนา · {len(families)} ประเภท</p></main></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.report.resolve() == args.output.resolve():
        parser.error('Choose a separate HTML output path.')
    report = json.loads(args.report.read_text(encoding='utf-8'))
    args.output.write_text(render(report), encoding='utf-8')


if __name__ == '__main__':
    main()
