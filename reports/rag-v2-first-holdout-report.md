# รายงานคุณภาพ RAG — รุ่น v2

RAG เป็นส่วนบังคับของระบบ ไม่ประเมินเปรียบเทียบกับการปิด RAG
เกณฑ์ผ่านประกาศก่อนทดสอบใน evaluation/quality_gates_v2.json

**ผลรวม: ยังมีเกณฑ์ที่ไม่ผ่าน**

## ผลวัดชุดใหม่ 20 ข้อ

| ตัววัด | ผลจริง | เกณฑ์ |
|---|---:|---:|
| Retrieval Recall@6 | 90.83% | >=95% |
| MRR@6 | 0.9500 | >=0.85 |
| nDCG@6 | 0.8543 | >=0.80 |
| Retrieval p95 | 18.38 ms | <=50 ms |
| Supplied context coverage | 90.83% | รายงานแยกจาก ranked retrieval |
| ผลคำตอบตรง gold Spark | 19/20 (95%) | >=90% |
| Clarification correctness | 100% | 100% |
| Citation IDs อยู่ใน context จริง | 100% | 100% |
| มี citation ตรงหลักฐานที่ติดป้าย | 100% | >=95% |
| Warm end-to-end p95 | 9.14 s | <=20 s |

Model warm-up/load แยกต่างหาก: 0.17 วินาที
Model calls รวม: 37; เวลาเฉลี่ยต่อคำถาม 3.74 วินาที

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

### hold12
At snapshot 2011-12-01, count customers who are BOTH Champions and high-value.

สถานะ: clarification

SQL: ไม่มี
ข้อความ: The evidence explicitly states that 'Champions' (rfm_segment = 'Champions') and 'high-value' (is_high_value = true) are distinct definitions and labels; a customer cannot be both simultaneously in this schema. Please clarify if you intended to count customers who are Champions OR high-value, or if there is another specific metric definition you require.


มี retrieval cases ที่ได้หลักฐานไม่ครบ top 6: 4 ข้อ
- hold01: ขาด schema.orders
- hold03: ขาด schema.orders
- hold06: ขาด syntax.ranking
- hold08: ขาด syntax.ranking

## ข้อจำกัด

คะแนนนี้เป็นผลชุดคำถามขนาดเล็กที่ผู้พัฒนากำหนด ไม่ใช่การรับรองโดยผู้ประเมินภายนอก
Citation validity/relevance ไม่ได้พิสูจน์ entailment ของข้อความทุกประโยค
ชุดคำถามใหม่มีทั้งรูปแบบใกล้เคียงงานเดิมและเงื่อนไขผสมใหม่ จึงไม่ใช่ตัวแทนทุกโจทย์ในโลกจริง
ใช้ข้อมูล UCI ประวัติศาสตร์ 2009–2011 บนเครื่องเดียว ไม่มี HDFS authentication
Spark cancellation เป็น best effort และยังต้องตรวจคำตอบสำคัญก่อนใช้ตัดสินใจ

## ทำซ้ำ

อ่าน README.md และ evaluation/README.md รัน retrieval และ -Split holdout หลัง freeze
build run: c81fa72c3c174a96bf8c03195b9e6f5e
รายงานดิบ: reports/rag-v2-holdout-ba55f032adbe47bdb1bc32ee34787f17.json / reports/retrieval-v2-holdout-f9944a7d80eb482d85932d06ddccf4bf.json
freeze: reports/freeze-rag-v2.json
สรุป machine-readable: reports/rag-v2-quality-summary.json
