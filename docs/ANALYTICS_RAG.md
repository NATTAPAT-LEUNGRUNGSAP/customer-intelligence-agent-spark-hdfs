# คำถามวิเคราะห์ สูตร และ syntax ใน RAG

ระบบใช้ Online Retail II ซึ่งมีรายการซื้อขายสินค้าและข้อมูลลูกค้าบางรายการที่ไม่มีรหัส
นิยามธุรกิจของโปรเจกต์แบ่งเป็น `orders` (หนึ่งใบสั่งซื้อสำเร็จ), `sales_lines`
(หนึ่งรายการสินค้าต้นทาง) และ `customer_summary` (หนึ่งลูกค้า ณ snapshot).

## คำถาม 200 ข้อใช้อย่างไร

[QUESTION_BANK.md](QUESTION_BANK.md) มีไทย 100 ข้อและอังกฤษ 100 ข้อ เป็นคู่แปลของ
100 เจตนา ครอบคลุม 22 กลุ่ม ไม่ใช่คำถามอิสระ 200 เจตนา คำถามเรียบเรียงจาก schema
และแนววิเคราะห์ที่รองรับ ไม่ได้คัดลอกจากเว็บไซต์หรืออ้างว่าเป็น benchmark ภายนอก.

| ส่วน | จำนวนคำถาม | สิ่งที่ระบบทำ |
|---|---:|---|
| ถามตัวเลขหรือจัดอันดับ | 160 | โมเดลสร้าง SQL เอง ผ่าน guards/OPA แล้วรัน Spark |
| ขอสูตรโดยไม่คำนวณ | 24 | เลือกหนึ่งใน 12 นิยามสูตรที่มีหลักฐาน ไม่เรียกโมเดลหรือรัน expression |
| ข้อมูลไม่ครบหรือไม่มีในชุดข้อมูล | 16 | ถามช่วงเวลา/snapshot หรืออธิบายข้อมูลที่ขาด |

ชุดนี้ใช้พัฒนาและเปิดเผยแล้ว จึงต้องเรียกว่า development benchmark.
SQL อ้างอิงอยู่เฉพาะ `evaluation/bilingual_200.json` สำหรับ evaluator.
Agent ไม่โหลดไฟล์นั้นและไม่เลือก SQL สำเร็จรูปตาม ID คำถาม.

ก่อนสร้าง SQL ระบบแปลงเงื่อนไขที่ตรวจได้เป็น `request_constraints` เช่น เดือนมกราคม
กลายเป็นวันที่เริ่มรวมและวันที่สิ้นสุดไม่รวม หรือคำถามที่ขอรหัสกับค่ากำหนดจำนวนคอลัมน์เป็น 2.
นี่เป็นข้อมูลข้อกำหนดส่งให้โมเดลและผู้ตรวจ SQL ไม่ใช่ SQL คำตอบที่เลือกจากคลัง.
Metric contracts ตรวจเพิ่มว่าหน่วยสินค้าไม่ใช่ยอดเงิน และ weighted price ต้องมีฐานหารเป็นหน่วย.
Context ส่ง ID และข้อความหลักฐานเต็ม ส่วนคะแนน retrieval และ metadata เก็บใน trace ภายนอก
เพื่อลด input ที่ไม่ช่วยอธิบายสูตร โดยไม่ตัดประโยคนิยามหรือ policy ทิ้ง.

## ความรู้ที่เพิ่ม

`knowledge/formulas.md` มี 12 สูตร: AOV, repeat customer fraction, anonymous invoice
fraction, units per order, product sale revenue, monthly sales growth, country sales
share, cumulative sales, three-month moving average, approximate median order value,
high-value customer fraction และ cancellation line fraction.

ทุกสูตรระบุนิยาม expression ตารางต้นทาง หน่วยหรือข้อจำกัด และกติกาฐานหารเป็นศูนย์.
สูตรเชิงประกอบเหล่านี้เป็นนิยาม RAG; ไม่ได้อ้างว่าทั้งหมดถูกเพิ่มเป็น OWL metrics.

`knowledge/analytics_patterns.md` แบ่ง syntax เป็นหัวข้อย่อย: statistics, basket,
transaction types, ratios, windows, HAVING, highest-month ties, snapshot statistics
และการแยก product-line count/units/revenue/weighted unit price.
Retrieval เลือก metric + schema + operation guide ที่เกี่ยวข้อง แล้วแนบ policy จำเป็น.
ไม่ส่งคำถามทั้งหมดหรือเอกสารทั้งหมดเข้า context ทุกครั้ง.

## ตัวอย่างใช้งาน

**ถามสูตร:** `ขอสูตรAOV ไม่ต้องรัน SQL`

คำตอบแสดงนิยามและ `SUM(order_amount) / NULLIF(COUNT(*),0)` พร้อมแหล่งอ้างอิง.
ยังไม่มีคำตอบตัวเลข และไม่ต้องถามเดือนเพื่ออธิบายนิยาม.

**ถามตัวเลข:** `เดือนมกราคม 2011 มูลค่าเฉลี่ยต่อคำสั่งซื้อเท่าไร`

โมเดลต้องประกอบ SQL จากนิยาม AOV กับตาราง `orders` และช่วงเวลาที่ถาม.
จำนวนคำสั่งซื้อกับจำนวนรายการสินค้าคนละหน่วยกัน.

**ถามแนวโน้ม:** `For each month of 2011 show year-to-date cumulative sales, ordered by month.`

ต้องรวมยอดขายเป็นรายปี–เดือนก่อน แล้วใช้ expression แบบนี้:

```sql
SUM(monthly_sales) OVER (
  ORDER BY month
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```

นี่เป็น syntax ที่นำไปประกอบ ไม่ใช่ SQL คำตอบสำหรับทุกกรณี.
การรวมเดือนก่อนใช้ window ป้องกันการสะสมระดับรายการใบสั่งซื้อผิดระดับ.

## ข้อจำกัดที่ต้องบอกผู้ใช้

- ยอดขายสำเร็จเป็น GBP ก่อนนำการคืนสินค้ามาหัก ไม่ใช่กำไร.
- cancellation line fraction มีฐานหารเป็นแถวรายการสินค้าทุกประเภท ไม่ใช่จำนวน invoice.
- First purchase หมายถึงครั้งแรกที่พบในข้อมูล ไม่ใช่ประวัติลูกค้าตลอดชีวิต.
- `PERCENTILE_APPROX` เป็นค่าประมาณ ไม่ใช่ median ที่รับรองว่า exact.
- `LAG` เปรียบเทียบแถวเดือนก่อนที่มีข้อมูล ถ้าเดือนหายต้องสร้าง calendar spine
  และตกลงกติกาเดือนว่างก่อนอ้างการเปรียบเทียบเดือนปฏิทินที่ต่อเนื่อง.
- หน้าต่าง `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` มีได้ไม่ครบสามแถวในช่วงต้น.
- ไม่ควรบังคับอัตราเติบโตให้อยู่ 0–1 เหมือนสัดส่วนประชากร.
- สูตรที่ไม่อยู่ในนิยามยังไม่ถูกประเมินหรือรันอัตโนมัติ; ไม่ใช้ `eval` กับข้อความผู้ใช้.

## วิธีตรวจผล

Evaluator รัน SQL อ้างอิง 80 คำสั่งบนข้อมูลจริงก่อนส่งคำถามให้ Agent.
จากนั้นตรวจแถว คอลัมน์ ค่า ลำดับที่กำหนด และแถวซ้ำของแต่ละภาษา.
คำถามสูตรตรวจ ID หลักฐานและการไม่เรียกโมเดล/Spark; ไม่ใช่การทดสอบความสามารถ
ของโมเดลในการประดิษฐ์สูตรใหม่. ผล RAG แยกจากผล SQL และมี source/model fingerprints.
คำถามตัวเลขส่วนใหญ่ใช้มกราคม 2011 หรือปี 2011 และ snapshot ที่มีเพียงวันเดียว;
ผลจึงยังไม่พิสูจน์ความครอบคลุมทุกช่วงเวลา ทุกการสะกด หรือทุกองค์กร.

คำสั่งรันใน Docker (ใช้ทรัพยากร Spark ร่วมกับเว็บ):

```powershell
docker compose run --rm --no-deps spark-job --master spark://spark-master:7077 --conf spark.driver.host=spark-job --conf spark.driver.bindAddress=0.0.0.0 --conf spark.executor.memory=512m /app/jobs/evaluate_bilingual.py --output /app/reports/bilingual-development-new-run.json
```

ใช้ชื่อรายงานใหม่เพื่อรักษาผลรอบเดิมไว้ ไม่เขียนทับผลที่เผยแพร่แล้ว.

## แหล่งอ้างอิง

- [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii): ฟิลด์ ช่วงข้อมูล และข้อสังเกตเรื่องข้อมูลขาดหาย
- [Spark built-in functions](https://spark.apache.org/docs/4.1.3/sql-ref-functions-builtin.html): aggregate, date/time และ approximate percentile
- [Spark window syntax](https://spark.apache.org/docs/4.1.3/sql-ref-syntax-qry-select-window.html): window ordering, ranking และ frames
