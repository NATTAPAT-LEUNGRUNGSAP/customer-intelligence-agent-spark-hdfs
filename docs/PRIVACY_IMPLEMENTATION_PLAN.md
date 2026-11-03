> Historical audit/source validation: for the integrated deployed system and current test results, see [CURRENT_STATE.md](CURRENT_STATE.md). Main web is now8090; preview8091 is stopped.

# แผนพัฒนา Privacy ก่อนเชื่อม MCP

ตรวจ source วันที่ 3 พฤศจิกายน 2026 จากข้อเสนอใน
[บทสนทนาที่ผู้ใช้ส่งมา](https://chatgpt.com/s/cx_6ae99ac032e48191907f848443506a83)
และ [audit](AGENTIC_MCP_AUDIT.md). เอกสารนี้เป็นแบบสำหรับตรวจทาน ยังไม่ใช่ระบบ privacy/MCP ที่ติดตั้งแล้ว.

## สิ่งที่จะเปลี่ยนสำหรับผู้ใช้

- ผู้ใช้เว็บวิเคราะห์ยอดขาย/ลูกค้าได้ แต่เห็นรหัสแทนลูกค้าและใบสั่งซื้อ ไม่เห็นรหัสต้นฉบับ.
- รหัสแทนเดิมใช้เชื่อมข้อมูลและนับลูกค้าซื้อซ้ำได้ภายในขอบเขตเดียวกัน.
- คำถามที่ส่งรหัสจริงหรือขอข้อมูลระบุตัวตนถูกปฏิเสธ/ปกปิดก่อนส่งถึงโมเดล.
- ไม่เปิดความสามารถถอดรหัสหรือแสดงข้อมูลจริงผ่านเว็บหรือ MCP.
- แสดงว่าเป็น pseudonymization ไม่ใช่การรับรองว่าข้อมูลไม่สามารถระบุตัวบุคคลได้.

## ข้อมูลและช่องทางที่ต้องคุม

| จุด | สภาพที่ตรวจพบ | งานที่ต้องทำ |
|---|---|---|
| `customer_id` ทั้งสามตาราง | อ่านจาก Parquet และแสดงในผลได้ | ใช้ HMAC token แบบเดียวกันเมื่อเป็นลูกค้าคนเดียวกัน |
| `invoice_id` ใน orders/sales_lines | เชื่อมใบสั่งซื้อกลับต้นทางได้ | ใช้ token แยก domain จาก customer แต่ตรงกันข้ามตาราง |
| product_id | จำเป็นต่อการวิเคราะห์สินค้า | เปิดได้ตามรายการข้อมูลที่อนุญาต |
| description | ข้อความอิสระ ไม่ใช่ taxonomy | จำแนก/ตรวจข้อความก่อนเปิด ไม่ถือว่าไม่มี PII โดยอัตโนมัติ |
| ประเทศ วันเวลา จำนวนเงิน | อาจเชื่อมโยงกลับบุคคลร่วมกับข้อมูลอื่น | จำกัดสิทธิ์และพิจารณากลุ่มเล็ก; ไม่เรียกผลลัพธ์ว่า anonymous |
| คำถาม SQL literals/aliases และ error | อาจมีผู้ใช้ใส่รหัสหรือข้อความอ่อนไหว | ตรวจขาเข้าและขาออก รวมข้อมูลที่ส่งกลับให้โมเดลแก้ SQL |
| UI/API และ JSON trace | `Application.query` เขียน response เกือบทั้งหมด | ส่งออก/บันทึกเฉพาะ payload ที่ผ่าน privacy boundary เดียวกัน |
| trusted ETL/evaluator | ต้องอ่านต้นฉบับเพื่อเตรียมข้อมูลและเทียบคำตอบ | แยกสิทธิ์จากแอปและ MCP; ห้ามเปิด evaluator เป็นเครื่องมือ |

## แบบที่เสนอให้ใช้

1. เริ่มด้วยผู้ใช้เว็บบทบาท `analyst` และวัตถุประสงค์ `customer_analytics`.
   identity มาจาก trusted gateway ไม่รับ role/purpose ที่ผู้ใช้หรือโมเดลกำหนดเอง.
   บัญชี Basic Auth ที่ใช้ร่วมกันพิสูจน์ได้เพียงกลุ่มผู้ใช้ ไม่ใช่ identity รายคน;
   ต้องบันทึกข้อจำกัดนี้และไม่อ้างว่ามี per-user authorization จนกว่าจะเพิ่มจริง.
2. ใช้ HMAC-SHA-256 เต็ม digest พร้อม prefix ระบุชนิดและ key version.
   ป้อน domain/key version/purpose/identifier ด้วย encoding ที่ไม่กำกวม.
   NULL คงเป็น NULL; รหัสต้องใช้ canonicalization เดียวกันทุกตาราง.
   ไม่ใช้ SHA-256 ธรรมดาของรหัสสั้นและไม่เปิด tokenization API สำหรับรหัสใดก็ได้.
3. เก็บ secret นอก Git และนอก prompts/logs โดยอ่านผ่าน secret file ที่จำกัดสิทธิ์.
   หาก key/identity/policy ไม่พร้อม ต้องหยุด ไม่ย้อนกลับไปใช้รหัสจริง.
   การหมุน key เปลี่ยน token; เก็บ metadata ของ key version และขั้นตอนสร้างข้อมูลใหม่.
4. แยก analytics access ออกจาก raw HDFS: การแทนค่าที่หน้าเว็บอย่างเดียวไม่พอ.
   production ต้องอ่านเฉพาะ sanitized views/data ด้วย service identity ที่ไม่มีสิทธิ์อ่าน raw path.
   Docker containers ที่ใช้ HDFS identity เดียวกันยังไม่ถือว่าบรรลุการแยกสิทธิ์นี้.
5. รวม validation, OPA pre/post, timeout, row cap และ privacy checks ไว้ใน execution service.
   Web/CLI/MCP ต้องใช้ขอบเขตเดียวกัน และไม่รับ callback ที่ข้าม service จากภายนอก.
6. เพิ่มการป้องกันผลลัพธ์/ข้อความก่อนส่งให้โมเดล เว็บ และ log.
   ห้ามใช้ regex อย่างเดียวเป็นข้อพิสูจน์ว่าไม่มี PII; ใช้ allowed schema,
   classification, synthetic canaries และทดสอบช่องทางแอบแฝงร่วมกัน.

## ไฟล์และลำดับทำงาน

| ลำดับ | จุดที่แก้/เพิ่ม | ผลที่ต้องได้ |
|---|---|---|
| 1 | `jobs/query_runtime.py`, โมดูล token/privacy ใหม่, Compose/secrets | สร้าง sanitized data path โดยไม่แตะ raw evaluator; ออกแบบ HDFS/service identity ก่อนใช้งานจริง |
| 2 | execution service ใหม่, `jobs/policy_engine.py`, `policies/analytics.rego` | ข้อบังคับกลางสำหรับ identity/purpose/fields และ deny เมื่อข้อมูลไม่ครบ |
| 3 | `jobs/agent.py`, `jobs/context_engine.py`, `jobs/web_app.py` | ทุก entry point และ repair/model feedback ผ่าน privacy/output boundary; trace ไม่มี raw values |
| 4 | `tests/`, privacy integration และ evaluator | พิสูจน์ privacy, bypass resistance และ analytic parity บนข้อมูลควบคุม/จริง |
| 5 | MCP client + analytics server แบบเล็ก | initialization, tools/list, tools/call จริงที่เรียก service เดิม ไม่ทำให้ governance เป็น optional tool |

ไม่จำเป็นต้องแยก Server B/C เป็น services ทันที. Adapter สำหรับ RAG/คำอธิบายนโยบายเพิ่มภายหลังได้เมื่อมีประโยชน์ชัดเจน.
การเพิ่ม MCP ไม่ใช่หลักฐานว่าข้อมูลปลอดภัยหรือว่า agent มีอิสระในการวางแผนมากขึ้น.

## เกณฑ์ตรวจรับก่อนเปิดให้เพื่อนใช้

- synthetic attacks: ไม่พบรหัสจริง/canary ใน model input, tool feedback, API, UI,
  JSON/log/error ที่ตรวจ; รายงานจำนวนกรณีและไม่ขยายข้อสรุปเกินชุดโจมตีที่ทดสอบ.
- missing identity/key/classification, OPA outage, malformed decision และ direct-call bypass
  ต้องถูกปฏิเสธทุกกรณีที่กำหนดไว้ก่อนรัน.
- ผลรวม จำนวน distinct ลูกค้า จำนวนซื้อซ้ำ และสัดส่วนคงเดิมบน fixtures;
  ตรวจ parity บนข้อมูลจริงเพิ่มโดยไม่ส่ง raw gold results เข้าแอป.
- ตรวจการจัดอันดับด้วยค่าคำนวณและสมาชิกในกลุ่มเสมอ; การเรียง token ในอันดับเสมอ
  อาจต่างจากการเรียง raw IDs ต้องกำหนดเกณฑ์ก่อนเทียบ ไม่แก้ gold ให้เข้ากับโมเดล.
- วัด first-pass/final accuracy, repair success, route/tool decisions และ p50/p95 latency.
  ชุด 200 ข้อเดิมเป็น regression ไม่ใช่ holdout ใหม่.
- MCP ต้องมีหลักฐาน client initialization, discovery, call, invalid arguments,
  timeout/cancellation และการเรียกตรงที่ไม่สามารถข้าม policy ได้.

## สถานะรอบนี้

เก็บ [source snapshot](../reports/pre-privacy-source-snapshot.json) ก่อนเริ่มไว้แล้ว.
เครื่องยังไม่พร้อมรันทดสอบ: Docker engine pipe ไม่พบ และ Ollama list timeout.
ไม่ได้รัน Spark/OPA/LLM benchmark ใหม่ และไม่ได้เปลี่ยน runtime, deploy หรือ presentation ในรอบวางแบบนี้.
README/Architecture/audit ที่มีการแก้ใน working tree ก่อนรอบนี้ถูกเก็บไว้ ไม่เขียนทับ.

การแยกสิทธิ์ข้อมูลและเปลี่ยนทุก entry point เป็นการปรับโครงสร้างหลัก.
ข้อกำหนดจากบทสนทนาที่อ้างอิงให้ถามก่อน major architectural refactors;
แผนนี้จึงเตรียมขอบเขตที่ตรวจทานได้ก่อนลงมือเปลี่ยนส่วนนั้น.
