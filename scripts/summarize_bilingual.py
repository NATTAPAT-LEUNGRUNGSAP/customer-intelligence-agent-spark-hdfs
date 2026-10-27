"""Build a plain-language report strictly from completed recorded executions."""
import json
import hashlib
import re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
before=json.loads((root/'reports/bilingual-retrieval-before.json').read_text(encoding='utf-8'))
after=json.loads((root/'reports/bilingual-retrieval-final.json').read_text(encoding='utf-8'))
run=json.loads((root/'reports/bilingual-development-final.json').read_text(encoding='utf-8'))
assert run['status']=='completed','Do not summarize an incomplete run as completed'
assert len(run['cases'])==200
assert before['bank_sha256']==after['bank_sha256']==run['bank_sha256']
cases=run['cases']
unit_log=(root/'reports/bilingual-unit-tests.txt').read_text(encoding='utf-8-sig')
unit_count=int(re.search(r'Ran (\d+) tests',unit_log)[1])
assert re.search(r'^OK\s*$',unit_log,re.M) and 'FAILED (' not in unit_log
packets=[]
for c in cases:
    response=c['result'];plan=response.get('context_plan')
    if not plan:continue
    references=response['references']; unique={r['id']:{'id':r['id'],'text':r['text']} for r in references}
    compact=json.dumps(list(unique.values()),ensure_ascii=False,separators=(',',':'))
    legacy=json.dumps(references,ensure_ascii=False)
    packets.append({'id':c['id'],'old_metadata_packet_bytes':len(legacy.encode()),'id_text_packet_bytes':len(compact.encode()),
                    'complete_id_text_hash_matches':hashlib.sha256(compact.encode()).hexdigest()==plan['selected_evidence_sha256']})
context_summary={'scope':'paired serialization audit on identical selected references; evidence bytes, not a tokenizer or general context-rot benchmark',
                 'cases':len(packets),'all_complete_id_text_hashes_match':all(p['complete_id_text_hash_matches'] for p in packets),
                 'old_metadata_packet_bytes_total':sum(p['old_metadata_packet_bytes'] for p in packets),
                 'id_text_packet_bytes_total':sum(p['id_text_packet_bytes'] for p in packets),'details':packets}
context_summary['evidence_byte_reduction_fraction']=1-context_summary['id_text_packet_bytes_total']/context_summary['old_metadata_packet_bytes_total']
(root/'reports/bilingual-context-packet-check.json').write_text(json.dumps(context_summary,indent=2)+'\n',encoding='utf-8')
lines=['# ผลพัฒนาระบบด้วยคำถามไทย–อังกฤษ 200 ข้อ','',
       'ชุดคำถามนี้เปิดเผยและใช้ปรับระบบแล้ว เป็น development benchmark ไม่ใช่ fresh holdout หรือหลักฐานว่ารองรับทุกคำถามวิเคราะห์.', '',
       '## ชุดคำถามและวิธีตรวจ','',
       '- ภาษาไทย 100 ข้อ และอังกฤษ 100 ข้อ เป็นคำถามสองภาษาของ 100 เจตนาวิเคราะห์ร่วมกัน ไม่ใช่ 200 เจตนาที่เป็นอิสระต่อกัน',
       '- 160 โจทย์ทดสอบการสร้าง SQL ด้วย Agent จริง; เฉพาะคำสั่งที่ผ่าน guard จึงรัน Spark แล้วเทียบผลกับ SQL อ้างอิง 80 คำสั่งที่รันจริงแยกจาก Agent',
       '- 24 คำถามขอสูตร: ตรวจสูตร/หลักฐานที่เลือก และตรวจว่าไม่เรียกโมเดลหรือ Spark',
       '- 16 คำถามต้องถามกลับหรือแจ้งว่าข้อมูลไม่รองรับ',
       '- SQL อ้างอิงอยู่ใน evaluation/ เท่านั้น Agent ไม่ได้รับคำตอบหรือ SQL อ้างอิง',
       '- ตรวจจำนวนคอลัมน์ ค่า จำนวนแถวซ้ำ และลำดับเมื่อคำถามกำหนด ไม่ใช้ LLM เป็นผู้ตัดสินความถูกต้อง',
       '- ตัวเลขใช้ tolerance ของ evaluator เดิม; percentile เป็นค่าโดยประมาณ และค่าผูกอันดับตรวจตามเงื่อนไขของแต่ละข้อ', '',
       '## ผลที่รันจริง','',
       '| ภาษา | คำตอบถูกต้อง | ทั้งหมด |','|---|---:|---:|']
for lang,label in [('th','ไทย'),('en','อังกฤษ'),('all','รวม')]:
    s=run['summary'][lang];lines.append(f"| {label} | {s['correct']} | {s['total']} |")
lines+=['','| ประเภท | ถูกต้อง | ทั้งหมด |','|---|---:|---:|']
for name,predicate in [('SQL',lambda c:c['family'] not in ('formula','clarification')),('สูตร',lambda c:c['family']=='formula'),('ถามกลับ/ไม่รองรับ',lambda c:c['family']=='clarification')]:
    selected=[c for c in cases if predicate(c)]
    lines.append(f"| {name} | {sum(c['correct'] for c in selected)} | {len(selected)} |")
lines+=['','## RAG ก่อนและหลังเพิ่มความรู้','',
        '| ตัวชี้วัด | ก่อน | หลัง |','|---|---:|---:|']
for key,label in [('recall_at_6','สัดส่วนหลักฐานที่ต้องใช้ซึ่งพบใน 6 รายการแรก'),('context_coverage','สัดส่วนหลักฐานที่ต้องใช้ซึ่งอยู่ใน context'),('mrr_at_6','MRR@6'),('ndcg_at_6','nDCG@6')]:
    b=before['summary']['all']['retrieval'][key];a=after['summary']['all']['retrieval'][key]
    lines.append(f'| {label} | {b:.4f} | {a:.4f} |')
lines+=['', 'ก่อนปรับยังไม่มีเอกสาร syntax/สูตรใหม่บางหัวข้อ จึงเป็นการวัดการเพิ่ม coverage พร้อมการปรับ retrieval ไม่ใช่การทดลองเปลี่ยน retriever โดยคง corpus เดิม. การค้นหลักฐานครบไม่ได้แปลว่า SQL ทุกข้อถูกต้อง. ตารางนี้เรียก retrieval ด้วยคำถามต้นฉบับเดียวกัน; รอบ end-to-end มีการเติม scope ของคำถามเดือนสูงสุดก่อนค้น จึงมีตัวเลข retrieval ของ input จริงแยกไว้ในผลดิบ.', '',
        '## สิ่งที่ปรับ','',
        '- เพิ่มสูตรที่อ้างอิงได้ 12 สูตร และคู่มือ syntax ย่อย 9 หัวข้อ; เลือกเฉพาะหัวข้อที่เกี่ยวข้อง ไม่ยัดทั้ง 200 คำถามเข้า prompt',
        '- แยกการขอสูตรจากการขอตัวเลข สูตรอ้างอิงไม่ต้องระบุเดือน แต่การรันผลจริงยังต้องมีช่วงเวลาหรือ snapshot',
        '- เพิ่มคำค้นไทยและเลือก metric/schema/operation ร่วมกัน; แยกสูตรอ้างอิงจากการค้นเพื่อตอบตัวเลข',
        '- ตรวจเดือนภาษาไทย ป้องกันตอบมัธยฐานแทนค่าสูงสุด และป้องกันเพิ่ม GROUP BY เมื่อถามยอดรวม',
        '- แยกผล window ที่มีหลายแถวออกจาก scalar aggregate และรองรับชื่อภายใน parser ของ PERCENTILE_APPROX', '',
        f"- ส่ง ID และข้อความหลักฐานเต็มให้โมเดล โดยเก็บคะแนน retrieval และ metadata ไว้ใน trace: ตรวจ packet {len(packets)} ข้อแล้ว hash ของ ID/ข้อความตรงครบ {context_summary['all_complete_id_text_hashes_match']}; ขนาด evidence ลด {context_summary['evidence_byte_reduction_fraction']*100:.2f}% เมื่อเทียบ serialization ของ references ชุดเดียวกันที่แนบ metadata. นี่เป็นการวัด bytes ของ evidence ไม่ใช่จำนวน token ของ prompt ทั้งหมดหรือหลักฐานว่าแก้ context rot ทั่วไปแล้ว.", '',
        'รอบพัฒนาก่อนหน้า (bilingual-development-expanded.json) รันครบ 200 ข้อได้ 167 ข้อถูกต้อง. หลังตรวจพบความคลาดเคลื่อนระหว่างภาษาบางข้อ จึงแก้คำถาม 3 คู่ (4 ข้อความ): คำถามรายปีและคำถามจำนวนลูกค้า 2 ข้ออังกฤษ โดย SQL อ้างอิงทั้ง 80 คำสั่งไม่เปลี่ยน. จึงไม่ตีความผลสองรอบเป็นการทดลอง A/B แบบควบคุมทุกปัจจัย. ส่วน RAG ก่อน/หลังด้านบนรันใหม่บนชุดคำถามที่แก้ตรงกันแล้ว.', '',
        '## รายการที่ยังไม่ผ่าน','']
failed=[c for c in cases if not c['correct']]
if failed:
    lines+=['| ID | ภาษา | สถานะ | คำถาม |','|---|---|---|---|']
    lines += [f"| {c['id']} | {c['language']} | {c['result']['status']} | {c['question']} |" for c in failed]
else:lines+=['ไม่มีในชุดพัฒนารอบนี้ แต่ยังต้องใช้ข้อสอบอิสระก่อนอ้างความสามารถทั่วไป.']
lines+=['','## การทำซ้ำและข้อจำกัด','',
        f"- Source/model fingerprint คงเดิมระหว่างรัน: {run['source_unchanged']}",
        f"- Question-bank fingerprint คงเดิมระหว่างรัน: {run['bank_unchanged']}",
        f"- SQL อ้างอิงที่รันจริง: {run['gold_queries_executed']}",
        f"- ผลที่รัน SQL แล้วแต่ไม่ตรงตารางอ้างอิง: {sum(not c['correct'] and c['result']['status']=='executed' for c in cases)} ข้อ (รวมกรณีคอลัมน์/ลำดับไม่ตรง ไม่ได้หมายความว่าตัวเลขทุกกรณีผิด)",
        f"- คำถามที่หยุดด้วย failed/error: {sum(c['result']['status'] in ('failed','error') for c in cases)} ข้อ",
        f"- เวลาตอบ p95 ทั้งชุด: {run['summary']['all']['latency_p95_seconds']:.2f} วินาที (รวม model/review/repair/Spark ไม่ใช่ query latency อย่างเดียว)",
        '- ไม่รองรับกำไร ต้นทุน ผลแคมเปญ หรือทำนายอนาคตจากข้อมูลที่ไม่มี',
        '- เดือนขาดหายต้องกำหนด calendar spine ก่อนอ้างการเทียบเดือนปฏิทิน; moving window ที่มีเป็นหน้าต่างของแถวเดือนที่สังเกตได้',
        '- Ontology เดิมยังครอบคลุม domain metrics เดิม; นิยาม metric และสูตรเชิงประกอบใหม่เก็บใน RAG ไม่ได้อ้างว่าถูกเพิ่มเป็น OWL metrics ทั้งหมดแล้ว',
        '- เก็บรอบนำร่องที่หยุด/ผิดพลาดไว้ ไม่มีการนับเป็นรอบทดสอบครบ', '',
        'ดูคำถามทั้งหมดที่ [QUESTION_BANK.md](../docs/QUESTION_BANK.md) และผลดิบ [bilingual-development-final.json](bilingual-development-final.json).']
(root/'reports/BILINGUAL_ANALYTICS_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
summary={'status':run['status'],'source_unchanged':run['source_unchanged'],'bank_unchanged':run['bank_unchanged'],
         'summary':run['summary'],'failures':[{'id':c['id'],'question':c['question'],'status':c['result']['status']} for c in failed],
         'retrieval_before':before['summary'],'retrieval_after':after['summary']}
summary['context_packet_audit']={k:v for k,v in context_summary.items() if k!='details'}
summary['unit_tests']={'passed':unit_count,'total':unit_count}
formula_path=root/'reports/bilingual-formula-integration.json'
if formula_path.exists():
    formula_test=json.loads(formula_path.read_text(encoding='utf-8'))
    summary['formula_numeric_integration']={k:formula_test.get(k) for k in ('status','correct','total','method')}
    lines.extend(['','## สูตรคำนวณกับตัวเลขควบคุม','',f"รัน Spark จริงกับตัวเลขตัวอย่างที่รู้คำตอบล่วงหน้า: {formula_test.get('correct')}/{formula_test.get('total')} ผ่าน สถานะ {formula_test['status']}. ครอบคลุมสูตร 12 สูตรและกรณีฐานว่าง ฐานเติบโตเป็นศูนย์ และอัตราเติบโตติดลบ. เป็นการทดสอบ expression ใน RAG ไม่ใช่การให้ LLM คิดสูตรใหม่. ดู bilingual-formula-integration.json."])
    (root/'reports/BILINGUAL_ANALYTICS_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
release_path=root/'reports/bilingual-release-guard-check.json'
if release_path.exists():
    release=json.loads(release_path.read_text(encoding='utf-8'))
    summary['release_guard_replay']={k:release[k] for k in ('status','changed_source_files','executed_sql_checked','same_source_as_full_run','same_model_as_full_run','method','monthly_semantic_checks')}
    lines.extend(['','## ตรวจ source ก่อนเผยแพร่','',
                  f"Source และ model fingerprints ตรงกับรอบเต็ม: {release['same_source_as_full_run']} / {release['same_model_as_full_run']}. ตรวจ SQL ที่จบด้วย executed ซ้ำกับ guard {release['executed_sql_checked']} คำสั่ง โดยไม่ได้เรียกโมเดลใหม่. Unit tests ล่าสุด {unit_count} ข้อผ่าน. ดู bilingual-release-guard-check.json และผล HTTPS ที่ bilingual-web-verification.json."])
    (root/'reports/BILINGUAL_ANALYTICS_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(root/'reports/bilingual-quality-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'correct':sum(c['correct'] for c in cases),'total':len(cases),'failed':len(failed)}))
