# ผลแก้การตอบ aggregation

วันที่ 3 พฤศจิกายน 2026. เป็น targeted development diagnostic 8 ข้อที่ใช้ตรวจ/ปรับระบบ ไม่ใช่ fresh holdout และไม่ใช่การรันชุด 200 ข้อใหม่.

## สิ่งที่แก้

- รู้จักคำจัดกลุ่มไทย “ตามประเทศ”, “แต่ละสินค้า” และคำที่เกี่ยวข้อง.
- ไม่เดาว่าทุก aggregation ต้องมีหนึ่งหรือสองคอลัมน์; ยังบังคับ projection ที่ผู้ใช้กำหนดชัดและสัดส่วนรวมหนึ่งค่า.
- คงการป้องกันมิติที่ไม่ได้ขอ เช่นถามแยกประเทศแต่เพิ่ม order_ts เป็นมิติ โดยตรวจความหมายแทนจำนวนคอลัมน์.
- post-tool duplicate check ใช้ทุก GROUP BY key รวม DATE_TRUNC, alias และ ordinal. ถ้ามี key ที่ไม่ได้แสดงจะไม่อนุมานว่า partial key ต้อง unique.
- ถ้าขอเรียงรหัสสินค้า ต้องเรียง product_id จริง ไม่เปลี่ยนเป็นจัดอันดับยอดขาย.
- เพิ่มคำสั่งรองรับหลาย dimensions/measures และส่งข้อเท็จจริงว่า citation membership ผ่าน code แล้วให้ reviewer. Reviewer ยังเป็นโมเดลเดิมและยังผิดได้; ไม่ถอด OPA หรือ bypass review.

## ผลที่รันจริง

| ตัวชี้วัด | ก่อน | หลัง |
|---|---:|---:|
| ส่ง SQL ผ่านจนประมวลผลสำเร็จ | 4/8 | 8/8 |
| ตรง SQL อ้างอิงแบบ strict รวมลำดับคอลัมน์/แถว | 3/8 | 6/8 |

อีก 2 ข้อหลังแก้คืนคอลัมน์เดือนก่อนประเทศ แทนประเทศก่อนเดือน แต่ค่าตัวเลข สมาชิกแถว จำนวนแถว และลำดับแถวตรง gold เมื่อจัดสองคอลัมน์ให้ตรงกัน. Supplementary value comparison จึงผ่าน 8/8. ไม่แก้คะแนน strict ในผลดิบ และไม่อ้างว่าตัวตรวจ permutation พิสูจน์ semantics ทั่วไป.

ก่อน/หลังใช้ชุดคำถาม gold SQL ข้อมูลและ model digest เดียวกัน. Evaluator รัน gold ทั้ง 8 คำสั่งแยกก่อนเริ่มถามโมเดล ไม่มี gold ใน agent prompt. baseline นำ agent.py, metric_contracts.py, result_contracts.py จาก commit 76629c4 มาทดสอบกับ dependencies เดียวกัน. source/model ไม่เปลี่ยนระหว่างแต่ละรอบ.

รอบ candidate แรกถูกรักษาไว้ที่ aggregation-live-candidate1.json: เจอ false duplicate-group rejection และการเรียงรหัสผิด ก่อนแก้และรันรอบสุดท้ายใหม่.

- Unit tests: 108 ผ่าน รวมกรณีถูกที่ต้องตอบและ SQL ผิดที่ต้องปฏิเสธ.
- OPA integration กับ service จริง: 3 ผ่าน.
- SQL จากรอบประเมินเดิม 156 คำสั่งผ่านการ replay กับ pre-execution validators; ไม่ได้เรียกโมเดล/Spark ใหม่และไม่ได้ replay numeric result contracts เพราะ Decimal ใน JSON เดิมสูญเสียชนิดข้อมูล.
- เว็บ: ดู aggregation-web-verification.json สำหรับการเรียก HTTP จริง.
- ข้อจำกัด readonly/table/function allowlist, exact period, grain/population, row cap, timeout และ OPA pre/post ยังคงอยู่.

## หลักฐาน

- [Baseline จริง](aggregation-live-before.json)
- [ผลหลังแก้จริง](aggregation-live-after.json)
- [สรุปและ supplementary comparison](aggregation-improvement-summary.json)
- [โจทย์และ gold สำหรับ evaluator](../evaluation/answerability_aggregation.json)
- [การวิเคราะห์ปัญหาก่อนแก้](ANSWERABILITY_DIAGNOSIS.md)

ยังไม่ได้เพิ่ม MCP หรือเปิดใช้ privacy controls ใหม่. คำถามภาษาธรรมชาติที่ซับซ้อน การตีความหลายขั้นและ false reviewer veto ยังต้องวัด/พัฒนาต่อ. ผลชุดเล็กนี้ไม่ยืนยันว่าทุก aggregation หรือคำถามทั่วไปตอบได้แล้ว.
