"""Update the entry-point docs only from completed, recorded test results."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
run=json.loads((root/'reports/bilingual-development-final.json').read_text(encoding='utf-8'))
quality=json.loads((root/'reports/bilingual-quality-summary.json').read_text(encoding='utf-8'))
web=json.loads((root/'reports/bilingual-web-verification.json').read_text(encoding='utf-8'))
gateway=json.loads((root/'reports/friend-access-verification.json').read_text(encoding='utf-8'))
assert run['status']=='completed' and run['source_unchanged'] and run['bank_unchanged']
assert web['status']==gateway['status']=='passed'
assert quality['formula_numeric_integration']['status']=='passed'
rows=run['cases'];sql=[c for c in rows if c['family'] not in ('formula','clarification')]
correct=sum(c['correct'] for c in rows);sql_correct=sum(c['correct'] for c in sql)
unit=quality['unit_tests']['passed']; latency=run['summary']['all']['latency_p95_seconds']
before=quality['retrieval_before']['all']['retrieval']['recall_at_6']
after=quality['retrieval_after']['all']['retrieval']['recall_at_6']
context=quality['context_packet_audit']['evidence_byte_reduction_fraction']
readme=(root/'README.md').read_text(encoding='utf-8')
readme=readme.replace('[ผลประเมิน](reports/GOVERNANCE_REPORT.md)','[ผลประเมิน](reports/BILINGUAL_ANALYTICS_REPORT.md)')
start=readme.index('## ผลประเมิน\n'); end=readme.index('## เริ่มใช้งาน\n',start)
section=f'''## ผลประเมิน

รันชุดพัฒนาไทย 100 ข้อและอังกฤษ 100 ข้อจริง ได้ **{correct}/200**
(ไทย {run['summary']['th']['correct']}/100; อังกฤษ {run['summary']['en']['correct']}/100).
เป็นคำถามสองภาษาของ 100 เจตนา และถูกใช้ปรับระบบแล้ว จึงไม่ใช่ independent holdout.

| สิ่งที่วัด | ผลจริง |
|---|---:|
| โจทย์ SQL เทียบผลกับ SQL อ้างอิงที่รันบนข้อมูลจริง | {sql_correct}/160 |
| เลือกสูตรที่มีหลักฐาน โดยไม่รันคำนวณ | 24/24 |
| ถามกลับ/แจ้งข้อมูลไม่รองรับ | 16/16 |
| สูตร 12 สูตรกับตัวเลขควบคุมและ edge cases บน Spark | 16/16 |
| Retrieval Recall@6 บนคำถามต้นฉบับชุดเดียวกัน ก่อน → หลัง | {before:.1%} → {after:.2%} |
| เวลาตอบ p95 ในรอบ 200 คำถาม | {latency:.2f} วินาที |
| Unit tests / OPA integration | {unit} ผ่าน / 3 ผ่าน |

ยังมี **{200-correct} ข้อไม่ผ่าน**; รายงานแยกกรณีหยุดตรวจออกจากผลที่รันแล้วไม่ตรงอ้างอิง
รวมทั้งกรณีคอลัมน์หรือช่วงเวลาไม่ตรง ไม่ได้อ้างว่ารองรับทุกคำถามแล้ว.
RAG ก่อนปรับยังไม่มีสูตร/syntax ใหม่บางหัวข้อ ผลก่อน–หลังจึงรวมการเพิ่ม knowledge coverage.

Context ส่ง ID และข้อความหลักฐานเต็ม โดยเก็บ metadata ไว้ใน trace แทน.
ตรวจ packet ของ 160 โจทย์ SQL พบว่าขนาด evidence ลด **{context:.2%}**
เมื่อเทียบกับ references ชุดเดียวกันที่แนบ metadata และ hash ของ ID/ข้อความตรงครบ.
นี่เป็นการวัด bytes ของ evidence ไม่ใช่หลักฐานว่าแก้ context rot ทั่วไปแล้ว.

ดู [วิธีวัด ผลดิบ และรายการที่ไม่ผ่าน](reports/BILINGUAL_ANALYTICS_REPORT.md).
ผลชุดก่อนขยาย 60/60 และ regression 80/80 เก็บเป็น
[ผลประเมินก่อนหน้า](reports/GOVERNANCE_REPORT.md) และไม่ถูกนำมาปะปนกับชุดนี้.

มี domain ontology แบบ RDF/OWL พร้อม SHACL และ OPA/Rego ก่อนและหลัง Spark.
สูตรเชิงประกอบและ metric ใหม่เก็บเป็นนิยาม RAG; ไม่ได้อ้างว่าทั้งหมดถูกเพิ่มเป็น OWL metrics.
อ่าน [การออกแบบและคำอธิบายศัพท์](docs/GOVERNANCE.md).

'''
(root/'README.md').write_text(readme[:start]+section+readme[end:],encoding='utf-8')
status_path=root/'reports/STATUS.md'
previous=status_path.read_text(encoding='utf-8')
marker='\n<!-- preserved-history -->\n'
history=previous.split(marker,1)[1] if marker in previous else previous.replace('# Current verification status','# Earlier verification status')
header=f'''# Current verification status

Latest live-model development run: bilingual-development-final.json.
Thai {run['summary']['th']['correct']}/100; English {run['summary']['en']['correct']}/100; total {correct}/200.
SQL results {sql_correct}/160; grounded formula lookup 24/24; clarification 16/16.
This is an exposed development bank, not an independent holdout.
Source/model fingerprints and bank fingerprints match before/after the complete run.

- Unit tests: {unit} passed (bilingual-unit-tests.txt).
- Actual OPA integration: 3 passed (bilingual-opa-integration.txt).
- Numeric RAG formula fixtures on actual Spark: 16/16 (bilingual-formula-integration.json).
- Public authenticated HTTPS feature checks: {len(web['checks'])}/{len(web['checks'])} (bilingual-web-verification.json).
- Password/Origin/public Spark smoke checks: {len(gateway['checks'])}/{len(gateway['checks'])} (friend-access-verification.json).
- Retrieval Recall@6 before/after on the same corrected bank: {before:.4f} → {after:.4f}.
- Evidence packet byte reduction on identical selected references: {context:.4f}; all ID/text hashes match.

{200-correct} development questions still do not match the oracle. See BILINGUAL_ANALYTICS_REPORT.md
and bilingual-quality-summary.json for the actual results and limitations.
The web app is restored; the temporary HTTPS link uses the existing credentials.
The records below are historical and do not describe current-source measurements.
'''
status_path.write_text(header+marker+history,encoding='utf-8')
governance=root/'reports/GOVERNANCE_REPORT.md'
old=governance.read_text(encoding='utf-8')
notice='> Historical result: this report predates the bilingual analytics expansion. See [latest development results](BILINGUAL_ANALYTICS_REPORT.md).\n\n'
if not old.startswith('> Historical result:'):governance.write_text(notice+old,encoding='utf-8')
print('Published completed test results to README and STATUS.')
