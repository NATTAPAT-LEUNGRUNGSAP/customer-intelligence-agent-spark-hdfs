# Customer Intelligence Agent with Spark & HDFS

รุ่น v2.4: มี local web application ที่ http://localhost:8090
เริ่มด้วย scripts/start-web.ps1 หลัง cluster/Ollama/data พร้อม ดู docs/WEB_APP.md
รันทดสอบจริงล่าสุด: unit 25 ข้อผ่าน; exposed regression 20/20; ชุดใหม่ v6 หลัง freeze 20/20 ถูก
RAG Recall@6 100%, MRR@6 0.892, nDCG@6 0.893; warm-query p95 5.43 วินาที
ผ่านเกณฑ์โครงการบนชุดเล็กที่ผู้พัฒนาสร้าง ไม่ใช่การรับรองว่าถูกทุกคำถามทั่วไป
รายละเอียด ผลรอบที่ไม่ผ่าน และข้อจำกัด: reports/DELIVERY_REPORT.md
Presentation: presentation/customer-intelligence-v2.4.pptx (14 slides)
GitHub public repo ที่ร้องขอ: customer-intelligence-agent-spark-hdfs (ยังรอสร้าง/เผยแพร่)

ระบบ Spark + HDFS + RAG + Agent สร้าง SQL เอง กำหนดส่งภายใน 9 พฤศจิกายน 2026
RAG เป็นส่วนบังคับ ไม่มีโหมดปิด RAG และไม่ใช้การเปรียบเทียบมี/ไม่มี RAG เป็นเกณฑ์ส่งงาน
อ่าน reports/STATUS.md, reports/DELIVERY_REPORT.md และ evaluation/README.md สำหรับผลปัจจุบันและวิธีวัด
ผล frozen v2.1 ก่อนแก้รอบปัจจุบัน: Recall@6 97.5%, MRR@6 0.879, nDCG@6 0.841, คำตอบตรง Spark 19/20
ผ่านเกณฑ์โครงการที่ประกาศก่อนทดสอบ ยังมีคำตอบผิด 1 ข้อ ไม่ถือว่าถูกทุกคำถาม

## เริ่มคลัสเตอร์

เปิด Docker Desktop Linux engine และ Ollama แล้วรันใน PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/start.ps1
```

ใช้ Hadoop 3.4.1: NameNode 1 + DataNodes 2, replication=2 และ Spark 4.1.3: master 1 + workers 2
เป็นหลาย container บนเครื่องเดียว ครั้งแรกดาวน์โหลด images/Hadoop และตรวจ SHA-512
หาก Apache archive ช้า: ใช้ Python ที่ติดตั้งจริงรัน scripts/cache_hadoop.py ก่อน
Docker ควรมี RAM 6–8 GB ขึ้นไป เครื่องพัฒนาจัดสรรประมาณ 16 GB ให้ Docker
NameNode UI http://localhost:9870 / Spark UI http://localhost:8080 bind เฉพาะ localhost
HDFS demo ไม่มี authentication และปิด permissions ห้ามใช้การตั้งค่านี้เป็น public service

start.ps1 ตรวจ DataNodes 2, safe mode OFF และ smoke test ตรวจ Spark workers 2
เขียน/อ่าน Parquet ผ่าน HDFS จริง 3 แถว ยอด C001=1500, C002=2500
รายงาน smoke-*.json เกิดเฉพาะเมื่อผ่านจริง

```powershell
docker compose exec namenode hdfs dfsadmin -report
docker compose exec namenode hdfs fsck /customer_intelligence -files -blocks -locations
docker compose stop
```

stop คง volumes และข้อมูลไว้ ไม่ลบ volumes เพื่อแก้ปัญหา
รัน Spark jobs ทีละงานเพราะใช้ driver DNS spark-job ร่วมกัน; job ใช้ --no-deps เพื่อคง workers 2

## ข้อมูลจริงและตาราง

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/build-data.ps1
```

UCI Online Retail II สอง sheet รวม 1,067,371 แถว เก็บ ZIP ต้นฉบับ, CSV และ SHA-256 manifest
CSV บน host เป็น staging; raw rows และตารางจริงเป็น Parquet บน HDFS ภายใต้ run ID ใหม่
build ตรวจ CSV hash/row count กับ provenance และ reconciliation ก่อนเขียน passed manifest
ไม่ overwrite รอบเก่า ไม่ append ซ้ำ เก็บแถวซ้ำตามนโยบายและรายงานจำนวน
ตัดทั้ง invoice เมื่อ customer/country ในรายการขายขัดกัน; ไม่ถือ missing ID เป็นข้อมูลผิดเสมอ
ตาราง: sales_lines (หนึ่ง product line), orders (หนึ่ง completed-sale invoice),
customer_summary (หนึ่ง identified customer ใน window 180 วัน ณ snapshot 2011-12-01)
ข้อมูลเป็นประวัติศาสตร์ 2009–2011 ไม่ใช่ข้อมูลลูกค้าปัจจุบัน

## ถาม Agent

ใช้ local Qwen3.5 9B ผ่าน Ollama บน RTX 5070 12 GB / RAM 32 GB
ถ้ายังไม่มีโมเดล: ollama pull qwen3.5:9b (ประมาณ 6.6 GB)
container ต้องเข้าถึง host.docker.internal:11434 ได้ โดยไม่ต้องเปิดบริการสู่ public network

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/ask.ps1 -Manifest /app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json -Question "How many completed invoices were recorded in October 2011?"
```

เลือก manifest status=passed อย่างชัดเจน ไม่เลือกไฟล์ล่าสุดโดยไม่ตรวจ
ถามไทยได้ เช่น เดือนตุลาคม 2011 มีคำสั่งซื้อสำเร็จกี่ใบ

RAG ใช้ BM25 + bilingual concepts/Thai n-grams บน knowledge ที่แยกตามนิยามและมี stable IDs
ดึง schema/syntax ที่เป็น dependency ของ metric มาด้วย เพื่อให้หลักฐานครบโดยไม่ต้องรอให้ติดอันดับเอง
cache ดัชนีและ rebuild เมื่อไฟล์เปลี่ยน ไม่ต้องใช้ embedding server สำหรับ corpus ขนาดเล็กนี้
ค้น ranked top 6 พร้อม policy context ที่จำเป็น บันทึก corpus/chunk hashes และ latency
Agent อ้างอิงหลักฐาน สร้าง SQL เอง ตรวจ citations และตรวจความสอดคล้องกับหลักฐานก่อนรัน Spark
กฎช่วงเวลา/ข้อมูลที่ไม่มี/snapshot บังคับถามกลับหรือแจ้งข้อมูลไม่พร้อมก่อนรัน
ไม่ใช้ gold SQL เป็น query templates และไม่ให้เครื่องมือ shell แก่โมเดล
SQL guard จำกัด SELECT/WITH บน 3 views และ whitelist functions
ผลไม่เกิน 200 แถว พร้อม truncated flag; ส่ง cancel Spark job group หลัง 45 วินาที
cancel เป็น best effort ไม่ใช่ process isolation; รวม attempts ไม่เกิน 3 รอบ
โมเดลใช้ temperature=0, context 8192, generation <=768 / evidence review <=256 tokens
SQL รันได้และมี citations ยังไม่รับประกันความหมายถูก ต้องอ้างผลประเมินด้วย
trace อยู่ใน reports/agent-rag-v2-*.json

## วัดคุณภาพ RAG โดยตรง

```powershell
docker compose run --rm --no-deps --entrypoint python3 spark-job -m unittest discover -s /app/tests -v
docker compose run --rm --no-deps --entrypoint python3 spark-job /app/jobs/evaluate_retrieval.py --split dev
powershell -ExecutionPolicy Bypass -File ./scripts/evaluate.ps1 -Manifest /app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json -Split dev
powershell -ExecutionPolicy Bypass -File ./scripts/evaluate.ps1 -Manifest /app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json -Split regression
```

วัด Recall@6, MRR@6, nDCG@6, context coverage, citation validity/relevance,
ความถูกต้องของผล Spark เทียบ gold SQL, clarification และ latency/cost เป็นจำนวน model calls
เกณฑ์ประกาศไว้ใน evaluation/quality_gates_v2.json ก่อนรัน holdout ใหม่ 20 ข้อ
หลัง freeze ใช้ --split holdout / -Split holdout และตรวจ quality_passed แยกจาก status=completed
freeze ปัจจุบันคือ reports/freeze-rag-v2.4.json ผลรวมอยู่ใน reports/delivery-quality-summary.json
ชุด test เดิมถูกเปิดดูแล้ว จึงใช้เป็น regression ไม่อ้างเป็น holdout ใหม่
ชุดใหม่รอบแรก (rag_holdout_v2.json) ไม่ผ่าน Recall จึงใช้เป็น regression-v2 แล้ว
ชุดปัจจุบันคือ rag_holdout_v6.json; v3/v4/v5 เปิดดูแล้ว เป็น regression-v3/v4/v5
รอบ v2.2/v2.3 ไม่ผ่านทุก gate เก็บ raw reports ไว้ รายละเอียดใน reports/DELIVERY_REPORT.md
ประวัติรอบแรกเดิมอยู่ใน reports/rag-v2-first-holdout-report.md
ผลเปรียบเทียบเก่าเก็บเป็นประวัติใน reports/archive/v1 และ JSON เดิม ไม่ใช้เป็นเกณฑ์รับรองปัจจุบัน
รายละเอียดข้อจำกัดและคะแนนจริงอยู่ในรายงาน ไม่อ้างว่าผ่านหากยังไม่รันจริง

## ขอบเขตสองสัปดาห์

1. Spark/HDFS smoke และ replication evidence
2. UCI provenance, versioned tables และ quality reconciliation
3. RAG ที่ค้นหลักฐานได้ตรงประเด็นและวัด retrieval/grounding/efficiency โดยตรง
4. Single Agent สร้าง SQL พร้อม validation และ deadline
5. Dev/regression และ holdout ใหม่ของระบบ RAG เทียบเกณฑ์ที่ประกาศไว้

ต้องส่ง local web application สำหรับเรียก Agent, presentation และโค้ดบน GitHub ด้วย
ข้อกำหนดและโครงนำเสนออยู่ใน reports/PRESENTATION_BRIEF.md; UI ใช้งานได้แล้ว GitHub ยังรอเผยแพร่
มี heuristic context budget และ context stress เบื้องต้น ยังไม่อ้างว่าแก้ context rot ได้ทั่วไป
ตัด MongoDB Policy Storage และ Churn Prediction/Campaign Recommendation ออกจากขอบเขต
ไม่รวม CLV, multiple agents หรือ production deployment
แผนส่งและ buffer อยู่ใน reports/DELIVERY_PLAN.md
แหล่งข้อมูล: https://archive.ics.uci.edu/dataset/502/online+retail+ii
