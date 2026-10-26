# รายงานคุณภาพ RAG — rag-required-v2.1

RAG เป็นส่วนบังคับของระบบ ไม่ประเมินเปรียบเทียบกับการปิด RAG
เกณฑ์ผ่านประกาศก่อนทดสอบใน evaluation/quality_gates_v2.json

**ผลรวม: ผ่านเกณฑ์ที่กำหนดของโครงการ**

## ผลวัดชุดใหม่ 20 ข้อ

| ตัววัด | ผลจริง | เกณฑ์ |
|---|---:|---:|
| Retrieval Recall@6 | 97.50% | >=95% |
| MRR@6 | 0.8792 | >=0.85 |
| nDCG@6 | 0.8410 | >=0.80 |
| Retrieval p95 | 13.25 ms | <=50 ms |
| Supplied context coverage | 100.00% | รายงานแยกจาก ranked retrieval |
| ผลคำตอบตรง gold Spark | 19/20 (95%) | >=90% |
| Clarification correctness | 100% | 100% |
| Citation IDs อยู่ใน context จริง | 100% | 100% |
| มี citation ตรงหลักฐานที่ติดป้าย | 100% | >=95% |
| Warm end-to-end p95 | 5.62 s | <=20 s |

Model warm-up/load แยกต่างหาก: 0.17 วินาที
Model calls รวม: 34; เวลาเฉลี่ยต่อคำถาม 3.54 วินาที

p95 ต่อคำถามไม่นับการเปิด Spark application/ลงทะเบียน views; เวลา CLI เต็มจะสูงกว่า

## วิธีและหลักฐาน

- ค้น BM25 + bilingual concepts/Thai n-grams จากนิยามแบบแยกประเด็น พร้อม cached index
- ranked top 6 และ policy context แยกกัน; rank metrics ไม่นับ policy ที่บังคับแนบเพิ่ม
- qrels เป็น evidence IDs ที่กำหนดไว้ล่วงหน้า Gold SQL/labels ไม่ส่งให้ Agent
- Agent สร้าง SQL เอง พร้อม citations และตรวจความสอดคล้องกับหลักฐานก่อนรัน
- ตรวจ citations ที่ไม่มีจริง ปฏิเสธ SQL อันตราย และจำกัดแถว/เวลา
- ผล SQL เทียบกับ gold ที่รันจริงใน Spark บน HDFS ไม่ใช่คะแนนจากการรัน SQL สำเร็จ
- freeze fingerprints ของ code/knowledge/config/model ตรงทั้งรายงาน retrieval และ end-to-end
- ชุด test เดิมเป็น regression แล้ว ผลเปรียบเทียบเก่าอยู่ใน reports/archive/v1 ไม่ใช้รับรองรุ่นนี้

## ข้อผิดพลาดที่ยังพบ

### fresh08
Return customer ID and total completed sales for the top three identified customers in January 2011; descending sales, ties by customer ID ascending.

สถานะ: executed

SQL: SELECT customer_id, SUM(order_amount) AS total_completed_sales FROM orders WHERE order_ts >= '2011-01-01' AND order_ts < '2011-02-01' GROUP BY customer_id ORDER BY total_completed_sales DESC, customer_id ASC LIMIT 3
ข้อความ: 

สาเหตุ: ไม่กรอง customer_id IS NOT NULL ทำให้กลุ่มลูกค้าไม่ระบุตัวตนติดอันดับ ทั้งที่ถาม identified customers

มี retrieval cases ที่ได้หลักฐานไม่ครบ top 6: 1 ข้อ
- fresh20: ขาด policy.availability

## ประวัติและผล regression ที่ยังต้องเปิดเผย

ชุดใหม่รอบแรกไม่ผ่าน Recall@6 (90.83% เทียบเกณฑ์ 95%) แม้คำตอบถูก 19/20
ผลเดิมไม่ถูกลบ: reports/rag-v2-first-holdout-report.md และ summary JSON
หลังแก้ retrieval ใช้ชุดนั้นเป็น regression-v2; ชุดสุดท้ายครั้งนี้เป็น rag_holdout_v3.json

- dev: 10/10; p95 4.79 s
- regression-v2: 18/20; p95 6.94 s
  - ข้อผิดพลาดที่ยังมีใน regression: hold04 — For United Kingdom orders in June 2011, what fraction of identified purchasing customers placed at least two orders? Return a fraction only.
  - ข้อผิดพลาดที่ยังมีใน regression: hold08 — Return customer ID and completed invoice count for the top four identified customers in August 2011; most invoices first, ties by customer ID ascending.

## ข้อจำกัด

คะแนนนี้เป็นผลชุดคำถามขนาดเล็กที่ผู้พัฒนากำหนด ไม่ใช่การรับรองโดยผู้ประเมินภายนอก
Citation validity/relevance ไม่ได้พิสูจน์ entailment ของข้อความทุกประโยค
ชุดคำถามใหม่มีทั้งรูปแบบใกล้เคียงงานเดิมและเงื่อนไขผสมใหม่ จึงไม่ใช่ตัวแทนทุกโจทย์ในโลกจริง
ใช้ข้อมูล UCI ประวัติศาสตร์ 2009–2011 บนเครื่องเดียว ไม่มี HDFS authentication
Spark cancellation เป็น best effort และยังต้องตรวจคำตอบสำคัญก่อนใช้ตัดสินใจ

## ทำซ้ำ

อ่าน README.md และ evaluation/README.md รัน retrieval และ -Split holdout หลัง freeze
build run: c81fa72c3c174a96bf8c03195b9e6f5e
รายงานดิบ: reports/rag-v2-holdout-1196190e8267415283a456265e0be1ab.json / reports/retrieval-v2-holdout-32f7b7331bec458eace94cf339c9ea06.json
freeze: reports/freeze-rag-v2.1.json
สรุป machine-readable: reports/rag-v2-quality-summary.json

## เวลา CLI จริงหนึ่งตัวอย่าง

ask.ps1 รวมเปิด/ปิด Spark application: 15.25 วินาที
เป็นหนึ่งตัวอย่างขณะโมเดลอุ่นอยู่ ไม่ใช่ p95 และไม่นำไปแทน warm query benchmark
