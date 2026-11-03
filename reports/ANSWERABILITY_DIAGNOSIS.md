# ตรวจสาเหตุที่ตอบคำถาม aggregation ไม่ได้

วันที่ 3 พฤศจิกายน 2026. รอบนี้ตรวจโค้ดและ trace ที่บันทึกไว้ พร้อมรัน Python validators ปัจจุบันจริง.
ไม่ได้รัน Spark, Ollama หรือชุด end-to-end ใหม่ และไม่ได้เปลี่ยน runtime.

## ข้อค้นพบที่ทำซ้ำได้

ดูรายละเอียด SQL/checks ที่ [aggregation-contract-audit.json](aggregation-contract-audit.json).
ทดสอบตัวตรวจด้วย SQL ที่ผู้ตรวจเรียบเรียงตามโจทย์ 7 กรณี; ผ่านทั้งหมด 3 กรณีและถูก semantic/shape checks ปฏิเสธ 4 กรณี.
SQL AST guard และ business-source/time checks ผ่านทั้ง 7 กรณี.
ตัวเลขนี้เป็น diagnostic sample ที่ตั้งใจเจาะจุดอ่อน ไม่ใช่อัตราความผิดพลาดของคำถามทั้งหมด.

| คำถาม | ตัวตรวจที่ขวาง | สาเหตุ |
|---|---|---|
| ยอดขายรวมตามประเทศ | validate_semantics | has_breakdown ไม่รู้จัก “ตามประเทศ” แต่รู้จัก “by country” |
| แต่ละสินค้ามียอดขายเท่าไร | validate_semantics และ metric shape | ไม่รู้จัก “แต่ละสินค้า” จึงบังคับเป็นยอดรวมหนึ่งค่า |
| ยอดขายรวมแยกตามประเทศและเดือน | metric shape | เดาว่าหนึ่ง metric ต้องมีสองคอลัมน์ แต่โจทย์ต้องใช้สอง dimensions + metric = สามคอลัมน์ |
| Show total sales by country and month | metric shape | ข้อจำกัดสองคอลัมน์เหมือนกัน แม้เป็นภาษาอังกฤษ |

นี่เป็นหลักฐานของ false rejection ที่ตัวตรวจ ไม่ใช่หลักฐานว่าโมเดลสร้าง SQL เหล่านี้ได้เองหรือ Spark รันผ่านแล้ว.

## ปัญหาอื่นจาก trace เก่าและ source

- รอบ development 196/200 เคยมี review ปฏิเสธ SQL โดยอ้างว่าขาด metric.sales ทั้งที่ validated_citations มี ID นั้น.
  แสดงว่า same-model review มี false veto ได้; ไม่ได้ยืนยันว่าเกิดกับทุกคำถามปัจจุบัน.
- อีกกรณีคืน literal backslash-n ใน SQL สามครั้ง และอีกกรณีทำ aggregation/window ผิดซ้ำสามครั้ง.
  การมี repair loop ยังไม่พิสูจน์ว่าแก้ได้ดี; ต้องวัด unique proposals, recovery และ repeated failure.
- trace คำถามหลายขั้นเกี่ยวกับสินค้า แสดง clarification อ้างว่าต้องมี category ทั้งที่โจทย์เลือกสินค้าจากราคา/การซื้อซ้ำ.
  เป็นการตีความหรือ grounding ที่ผิด. คำถามนั้นยังต้องตกลง GBP เทียบ “บาท” และนิยาม product-specific AOV;
  ควรถามเฉพาะจุดกำกวมจริง ไม่เพิ่มความต้องการ category เอง.
- การสำรวจข้อมูลใช้ full-match ของข้อความจำนวนน้อย จึงพลาดคำถามใกล้เคียง เช่นขอ schema พร้อมจำนวนแถว.
- ชุด 200 ข้อมีเพียง 100 เจตนาสองภาษาและถูกใช้ปรับระบบแล้ว; ผล 196/200 เป็นของ source เก่า.
  ไม่ได้พิสูจน์คุณภาพคำถามภาษาธรรมชาติทั่วไป การทำหลายขั้น หรือคำถามที่มีหลาย dimensions.

## ข้อจำกัดที่ควรปรับ

1. คง readonly, table/function allowlist, timeout, row cap และ OPA ไว้.
2. บังคับจำนวนคอลัมน์เมื่อผู้ใช้กำหนดชัดเท่านั้น; การเดารูปแบบที่มั่นใจต่ำควรเป็น warning.
   ตรวจ dimensions/metrics ที่ต้องมีแยกจากความพอดีของรูปแบบตาราง ไม่บังคับให้ทุก aggregation มีสองคอลัมน์.
3. แก้การตีความกลุ่ม/metric ให้รองรับไทยและหลาย dimensions พร้อมกรณีที่ตั้งใจไม่จัดกลุ่ม;
   ห้ามแก้โดยยอมรับ GROUP BY ทุกแบบ เพราะจะทำให้ยอดรวมผิดได้.
4. ลดอำนาจ veto ของ review ที่ไม่อ้าง discrepancy ที่ตรวจสอบได้. ปัญหา citation membership ให้ตรวจด้วยโค้ด;
   ยังต้องตรวจ logic/population และไม่ตีความการอนุมัติจากโมเดลว่าเป็น correctness oracle.
5. แยกโจทย์หลายขั้นเป็นแผนย่อยและตรวจผลแต่ละขั้น; จับการแก้ซ้ำเดิมแล้วเปลี่ยนวิธีหรือแจ้งจุดติดจริง.
6. ใช้ข้อสอบภาษาธรรมชาติที่ยังไม่ใช้ปรับระบบ รวม synonyms, compound metrics, multi-dimension,
   HAVING, CTE, window และ source-grain ambiguity. รายงาน valid-answer rate,
   false rejection, wrong-answer rate, clarification usefulness, repair recovery และเวลาที่ผู้ใช้เสีย.

## ลำดับความสำคัญ

แก้ basic answerability และ false rejection ก่อนเพิ่ม services/MCP หรือขยายสไลด์.
ต้องวัดบน source ใหม่หลังแก้ และไม่ลดกฎความถูกต้องของประชากรหรือปล่อยตัวเลขผิดเพื่อเพิ่มเปอร์เซ็นต์การตอบ.
ยังไม่สรุปว่าโมเดลเล็กเป็นสาเหตุหลัก เพราะการทดลองนี้พิสูจน์แล้วว่าบางข้อถูกขวางก่อนถึง Spark.
