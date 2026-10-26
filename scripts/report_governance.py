"""Summarize completed execution evidence without inventing missing results."""
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=Path(sys.argv[1]) if len(sys.argv)>1 else sorted((root/'reports').glob('acceptance-*.json'),key=lambda p:p.stat().st_mtime)[-1]
r=json.loads(p.read_text(encoding='utf-8'))
if r.get('status')!='completed':raise SystemExit('Refusing to report incomplete execution as completed')
s=r['summary'];a=s['acceptance'];g=s['regression']
failed=[{'id':c['id'],'question':c['question'],'status':c['result'].get('status'),
         'last_error':c['result'].get('attempts',[{}])[-1].get('error') if c['result'].get('attempts') else c['result'].get('error')}
        for c in r['acceptance'] if not c['correct']]
summary={'raw_report':p.name,'source_unchanged':r['source_unchanged'],'quality_passed':r['quality_passed'],
         'acceptance':a,'regression':g,'context':{k:s[k] for k in ('clean','managed','unfiltered')},
         'policy_integration_correct':sum(c['correct'] for c in r['policy_integration']),
         'policy_integration_total':len(r['policy_integration']),
         'incorrect_answers_delivered':sum(c['result'].get('status')=='executed' and not c['correct'] for c in r['acceptance']),
         'failures':failed,'context_protocol':r['context_protocol'],
         'ontology':{'metrics':9,'tables':3,'format':'OWL/RDF','validation':'SHACL + source grain consistency'},
         'caveats':['Developer-authored supported-family parameter combinations, not an external benchmark.',
                    'Pilot exposed 3 replaced cases. First completed 60-case run scored 59/60; its cases became regression after CTE/NaN fixes. This run uses a different 60-case acceptance set.',
                    'Timing excludes Spark startup; gold queries run before corresponding candidate queries.',
                    'Context trials reuse 12 acceptance questions after exposure; no new holdout claim.',
                    'Optional background outside selected evidence only; actual tokens remain well below full context window.',
                    'Passing thresholds does not mean every case passed. See explicit failed cases.']}
(root/'reports/governance-quality-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
lines=['# ผลทดสอบระบบปัจจุบัน','',f'หลักฐานดิบ: `{p.name}`',
       f'Fingerprint ก่อนและหลังรันตรงกัน: **{r["source_unchanged"]}**',
       f'ผ่านเกณฑ์รวมที่กำหนดก่อนรัน: **{r["quality_passed"]}**','',
       '## สิ่งที่พัฒนา','',
       '- Ontology แบบ RDF/OWL: 9 metrics, 3 ตาราง, ความสัมพันธ์กับสูตร ระดับข้อมูล และ knowledge IDs ตรวจด้วย SHACL',
       '- RAG ใช้ ontology เติมเอกสาร metric/schema ที่เกี่ยวข้อง โดย Agent ยังสร้าง SQL เอง',
       '- OPA/Rego ตัดสินก่อนและหลัง Spark ผ่าน HTTP จริง ติดต่อไม่ได้หรือคำตัดสินไม่ครบให้หยุด',
       '- ตรวจช่วงเวลารายเดือน/ช่วงเดือน วัน snapshot ประเภทสินค้า grain และความเสี่ยง join ทำยอดซ้ำ',
       '- ตรวจโครงสร้างผล แถว/คอลัมน์ ตัวเลข finite จำนวนเต็มไม่ติดลบใน COUNT กลุ่มซ้ำ NULL ID และ fraction 0..1','',
       '## ผลคำถามใหม่กับโจทย์เดิม','',
       '| ชุด | ถูก / ทั้งหมด | ล้มเหลว / error | p95 วินาที |', '|---|---:|---:|---:|',
       f'| ใหม่ ก่อนใช้ผลปรับระบบ | {a["correct"]}/{a["total"]} | {a["failed_or_error"]} | {a["latency_p95_seconds"]:.2f} |',
       f'| โจทย์เดิม ทดสอบการถดถอย | {g["correct"]}/{g["total"]} | {g["failed_or_error"]} | {g["latency_p95_seconds"]:.2f} |','',
       f'คำตอบที่ส่งแล้วผิดในชุดใหม่: {summary["incorrect_answers_delivered"]} กรณี ล้มเหลว/หยุดนับผิดตามเกณฑ์',
       f'OPA integration ผ่าน {summary["policy_integration_correct"]}/{summary["policy_integration_total"]} กรณี เรียก service จริง ไม่มี mock','',
       'เป็น 60 คำถามที่ผู้พัฒนาสร้างในกลุ่มงานที่รองรับ: 48 กรณีธุรกิจ 8 กรณีถามกลับ 4 กรณีไทย/อังกฤษ ใช้ gold SQL ที่แยกจาก prompt/runtime',
       'รอบ pilot พบตัวตรวจช่วงเดือนผิดและเปิดคำถามใหม่ไปแล้ว 3 ข้อก่อนหยุด แยกสามข้อนั้นเป็น exposed และแทนใหม่ รอบแรกที่สมบูรณ์ได้ 59/60 แล้วใช้ผลแก้ CTE/NaN จึงย้าย 60 ข้อนั้นเป็น regression รวมกับเดิมเป็น 80 ข้อ และสร้างอีก 60 คำถามสำหรับรอบนี้ ไม่มีการลดเกณฑ์','',
       '## กรณีที่ไม่ผ่าน','']
for f in failed:lines.extend([f'- `{f["id"]}`: {f["question"]}',f'  สถานะ: {f["status"]}; เหตุผล: {f["last_error"]}'])
if not failed:lines.append('ไม่มีกรณีไม่ผ่านในชุดนี้')
lines.extend(['','## การทดลอง Context ที่อ่านผลได้ตรงไปตรงมา','',
              'คำถามต่างกัน 12 ข้อ แต่ละข้อรัน 3 เงื่อนไข รวม 36 trials ทุกเงื่อนไขใช้ RAG และหลักฐานที่จำเป็นชุดเดียวกัน',
              'เติมบันทึกประกอบที่ไม่เกี่ยวกับงาน 3,000 ตัวอักษร นอกเอกสารหลัก สลับไว้ต้น/กลาง/ท้าย ไม่ใช่ข้อความอันตรายภายในเอกสารอ้างอิง','',
              '| เงื่อนไข | ถูก / ทั้งหมด | หยุดก่อนโมเดล | หยุดระหว่างซ่อม | ไม่ถูกด้วยเหตุอื่น | ช่วง tokens จริง |',
              '|---|---:|---:|---:|---:|---:|'])
for key,label in [('clean','ไม่มีข้อความรบกวน'),('managed','ตัดเฉพาะข้อความประกอบ'),('unfiltered','เก็บข้อความประกอบทั้งหมด')]:
    v=s[key];lines.append(f'| {label} | {v["correct"]}/{v["total"]} | {v["blocked_before_model"]} | {v["blocked_during_repair"]} | {v["other_failed"]} | {v["prompt_tokens_min"]}–{v["prompt_tokens_max"]} |')
lines.extend(['','การหยุดก่อนโมเดลแสดงข้อจำกัด input ของระบบ ไม่ใช่หลักฐานว่าโมเดลตอบผิด การรักษาเอกสารครบไม่ได้รับประกันว่าโมเดลใช้เอกสารถูก',
              '12 คำถามนี้เคยเปิดใน acceptance แล้ว จึงเป็น stress experiment ไม่ใช่ชุดคำถามใหม่อีกชุด บริบทที่วัดยังห่างจาก window เต็มและไม่มีประวัติบทสนทนายาว',
              'จึงสรุปได้เฉพาะพฤติกรรมการจัด input และคำตอบในเงื่อนไขที่ทดสอบ ยังรับรองการแก้ context rot ทั่วไปไม่ได้','',
              '## ศัพท์สำหรับการนำเสนอ','',
              '- หลักฐาน: นิยามธุรกิจและคำอธิบายตารางที่ RAG ค้นเจอ เช่น invoice ต้องนับจาก orders',
              '- SQL: คำสั่งค้นและคำนวณข้อมูลที่ Agent สร้าง',
              '- Grain: หนึ่งแถวแทนอะไร เช่น หนึ่งรายการสินค้า หรือหนึ่ง invoice',
              '- Atomic section: หนึ่งหัวข้อความรู้ที่มี ID ให้อ้างอิงได้ ไม่ใช่เอกสารทั้งไฟล์',
              '- Gold SQL: SQL อ้างอิงที่ผู้พัฒนาเตรียมเพื่อคำนวณเฉลยด้วย Spark ไม่ส่งให้ Agent',
              '- Expected evidence: IDs ของหัวข้อความรู้ที่ควรค้นพบในโจทย์นั้น',
              '- Guard: ตัวตรวจว่าคำสั่งอนุญาตให้รันหรือไม่ ไม่ใช่ตัวเฉลยว่าคำตอบถูก',
              '- ชุดคำถามใหม่: ยังไม่ใช้ผลของโจทย์นั้นปรับ source ที่ล็อกไว้ก่อนรอบวัด ส่วนการรันซ้ำเป็น regression','',
              '## ขอบเขต','',
              'Domain ontology ใช้กับ schema ของโปรเจกต์ ไม่ได้ทำ schema matching ขององค์กรใหม่อัตโนมัติ OPA นี้บังคับกฎ analytics ไม่ได้เพิ่ม authentication หรือ tenant isolation',
              'Semantic checks รองรับรูปแบบ SQL และข้อความช่วงเวลาที่กำหนด ยังมีการปฏิเสธ query ที่อาจถูกต้องได้ ข้อมูลยังเป็น cluster บน host เดียว cancellation เป็น best effort',
              'มาตรฐานที่ใช้: [OPA/Rego](https://www.openpolicyagent.org/docs/policy-language), [W3C SHACL](https://www.w3.org/TR/shacl/).'])
(root/'reports/GOVERNANCE_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
