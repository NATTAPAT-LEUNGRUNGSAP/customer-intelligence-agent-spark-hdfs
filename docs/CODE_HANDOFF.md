# คู่มืออ่านโค้ดและส่งต่องาน Customer Intelligence

ระบบรับคำถามภาษาไทยหรืออังกฤษ ค้นนิยามจาก RAG ให้โมเดลเขียน SQL
แล้วใช้ Spark คำนวณจากข้อมูลบน HDFS เว็บแสดงตารางพร้อม SQL และร่องรอยการตรวจ
ส่วน Dashboard ภาพรวมใช้ SQL ที่ระบบเตรียมไว้ และมีทางเข้าคนละเส้นกับช่องถาม AI

## เริ่มจากคำถามหนึ่งข้อ

ตัวอย่าง “เดือนตุลาคม 2011 มีใบสั่งซื้อกี่ใบ” เหมาะสำหรับเปิดตามโค้ด
ผลอ้างอิงของชุดข้อมูลเดิมคือ 2,040 ใบ จากตาราง `orders` ที่มีหนึ่งแถวต่อใบสั่งซื้อสำเร็จ

| ลำดับ | เปิดไฟล์ไหน | ทำอะไรและส่งอะไรต่อ |
|---|---|---|
| 1 | [web/app.js](../web/app.js) | รับข้อความ ช่วงเวลาและตัวเลือกจากหน้าเว็บ ส่ง JSON ไป `POST /api/query` แล้วใช้คำตอบ JSON แสดงตาราง SQL และ trace |
| 2 | [jobs/web_app.py](../jobs/web_app.py) → `Application.query` | ตรวจ input ประกอบบริบทจากตัวกรองหรือคำถามก่อนหน้า ส่งคำถามและฟังก์ชันรัน SQL ไปให้ `agent.answer` หลังจบเขียน `reports/web-agent-<trace_id>.json` และส่งผลกลับเบราว์เซอร์ |
| 3 | [jobs/retrieval.py](../jobs/retrieval.py) และ [knowledge/](../knowledge/) | ค้นเอกสารเกี่ยวกับการนับใบสั่งซื้อ โครงสร้าง `orders` และเงื่อนไขเวลา ส่งข้อความกับรหัสหลักฐานให้ตัวประกอบบริบท |
| 4 | [jobs/context_engine.py](../jobs/context_engine.py) → `assemble_evidence` | เลือกและจัดข้อความหลักฐานสำหรับ prompt ตัว Agent ส่ง prompt ให้ Ollama ผ่าน `generate` แล้วรับข้อเสนอ SQL และ citations กลับมา |
| 5 | [jobs/agent.py](../jobs/agent.py) → `answer` | ตรวจรหัสหลักฐาน จากนั้นเรียก SQL guard, ตัวตรวจความหมายและสูตร และการทบทวนข้อเสนอด้วยโมเดล ก่อนส่ง SQL ที่ผ่านไปยังจุดเรียก Spark |
| 6 | [jobs/tool_hooks.py](../jobs/tool_hooks.py) และ [jobs/policy_engine.py](../jobs/policy_engine.py) | `before_tool` ขอคำตัดสินจาก OPA ก่อนรัน หากอนุญาตจึงเรียกฟังก์ชันรัน SQL จากข้อ 2 |
| 7 | [jobs/query_runtime.py](../jobs/query_runtime.py) → `run_query` | รัน SQL บน Spark ใช้ view ที่อ่าน Parquet จาก HDFS ส่งกลับ `columns`, `rows`, `truncated` จำกัดเวลาและจำนวนแถว |
| 8 | [jobs/result_contracts.py](../jobs/result_contracts.py) และ [jobs/agent.py](../jobs/agent.py) | `after_tool` ตรวจผลและนโยบายก่อนคืนตาราง ถ้าผ่าน Agent ส่งผลพร้อม SQL หลักฐานและ trace กลับไปที่ข้อ 2 |

### เมื่อไม่ผ่าน การทำงานย้อนกลับไปไหน

ใน `answer` ดูบล็อก `except` ที่บันทึก `stage='repair'` ข้อผิดพลาดจากการ
ตรวจ SQL การรัน Spark หรือการตรวจผล จะถูกส่งพร้อมข้อเสนอเดิมให้
[`repair_messages`](../jobs/context_engine.py) เพื่อจัด prompt รอบถัดไป
ระบบเก็บคำถามและหลักฐานเดิมกับความผิดพลาดล่าสุด แล้วกลับไปให้โมเดลเสนอ SQL ใหม่
โดยมีงบรวมสามรอบของลูป การเรียก metadata ก็นับในงบนี้
ถ้า OPA ติดต่อไม่ได้หรือเกินงบ context ระบบหยุด ส่วนคำถามกำไรที่ไม่มีข้อมูลต้นทุน
หยุดที่การตรวจข้อจำกัดของข้อมูลก่อนสร้าง SQL

## ส่วนที่เปิดเมื่อจะแก้งานต่อ

| ต้องการแก้อะไร | อ่านที่ไหนและผลไปที่ไหน |
|---|---|
| เตรียมข้อมูลหรือปรับตาราง | [prepare_data.py](../jobs/prepare_data.py) เตรียมไฟล์ให้ [build_tables.py](../jobs/build_tables.py) สร้าง `sales_lines`, `orders` และ `customer_summary` บน HDFS แล้วเขียน manifest ให้ `load_views` ใช้ตอนเริ่มระบบ |
| คำศัพท์ สูตร หรือโครงสร้างความรู้ | [knowledge/](../knowledge/) ป้อน RAG ส่วน [ontology/](../ontology/) และ [ontology.py](../jobs/ontology.py) ดูแลกราฟนิยามและการตรวจ SHACL |
| วันที่ ประเทศ หรือคำถามต่อเนื่อง | [question_scope.py](../jobs/question_scope.py) จัดช่วงข้อมูลและตัวเลือก ส่วน [conversation.py](../jobs/conversation.py) ใช้บริบทจากประวัติแบบจำกัด ส่งคำถามที่ตีความแล้วเข้า Agent |
| SQL ถูกบล็อกหรือผลผิดรูป | [sql_guard.py](../jobs/sql_guard.py) ตรวจคำสั่งและตาราง [semantic_contracts.py](../jobs/semantic_contracts.py) และ [metric_contracts.py](../jobs/metric_contracts.py) ตรวจเงื่อนไขทางธุรกิจ ดู `attempts`, `policy_trace` และ `hook_trace` ประกอบ |
| Dashboard และกราฟ | [dashboard.py](../jobs/dashboard.py) สร้างคำสั่ง SQL ภาพรวมและส่งผลให้ [dashboard.js](../web/dashboard.js) ส่วน [charts.js](../web/charts.js) วาดกราฟจากค่าที่ได้รับ |
| เรียกจากโปรแกรมอื่น | [mcp_server.py](../jobs/mcp_server.py) เปิดเครื่องมือผ่าน MCP stdio โดย `analyze` เรียก Agent เดียวกัน ผลส่งกลับ MCP client เว็บปกติเรียก Python โดยตรง |
| Correctness และ Faithfulness | [evaluate_bilingual.py](../jobs/evaluate_bilingual.py) รันโจทย์และเทียบผลกับ Gold SQL ใน [evaluation/](../evaluation/) ตัววัด [evaluate_hallucination.py](../scripts/evaluate_hallucination.py) อ่านรายงานที่เสร็จแล้วและประเมินคำอธิบายแยกต่างหาก สรุปผลอยู่ใน [BENCHMARK_FOLLOWUP.md](../reports/BENCHMARK_FOLLOWUP.md) |
| เปิดเว็บและแชร์ให้ทดลอง | [WEB_APP.md](WEB_APP.md) ระบุขั้นตอนเปิด Spark, Ollama และเว็บ ส่วน [FRIEND_ACCESS.md](FRIEND_ACCESS.md) อธิบายการเปิดและปิดลิงก์ชั่วคราว |

## ส่งให้คนอื่นรับช่วง

ส่งลิงก์ GitHub พร้อมชื่อ branch หรือ commit และลิงก์มาที่หน้านี้ ระบุงานที่ต้องทำต่อ
กับคำถามที่ใช้ทำให้เห็นปัญหาซ้ำ ถ้ามี ให้แนบเฉพาะรายงานสรุปที่เผยแพร่ได้
คนรับช่วงสามารถเริ่มจาก README แล้วใช้ `/api/status` ตรวจว่าเว็บพร้อม
ก่อนลองคำถามตัวอย่างและเปิด trace ของรอบที่เพิ่งรัน

ถ้ารับช่วงใน Codex อีกแชท ให้เปิด repo เดียวกันแล้วระบุ commit และงานที่จะทำต่อ
เช่น “เริ่มจาก `docs/CODE_HANDOFF.md` แล้วตรวจกรณียอดขายของใบสั่งซื้อไม่มีรหัสลูกค้าใน United Kingdom
ดูผลเดิมในรายงานและบันทึกว่ารันอะไรจริง” ผลหลังแก้ล่าสุดคือโจทย์เดิม 16/16 และโจทย์ใหม่ 11/12
ส่วนชุด 200 ข้อเป็นผลก่อนแก้ ตัวตรวจ Faithfulness จับข้ออ้างผิดได้ 2/8 บนชุดควบคุม

รหัสผ่าน ลิงก์แชร์ที่ยังเปิดอยู่ API keys และ trace ที่มีข้อมูลรายลูกค้าเก็บไว้ในเครื่อง
ใช้ commit และรายงานสรุปเป็นหลักฐานสำหรับส่งต่อ
