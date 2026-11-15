# ดูผลประเมินใน Langfuse

เริ่มจาก [หน้าสรุป 40 ข้อ](../reports/evaluation-quadrants.html) แล้วกด **เปิดคะแนนทั้งสองใน Langfuse** ลิงก์ตั้งตัวกรองให้แล้ว ต้องเปิดบริการ Langfuse ที่ `localhost:3000` และเข้าสู่ระบบก่อน

| คะแนน | วิธีวัด | ผลชุดทดลอง |
|---|---|---|
| `sql_result_correctness` | เทียบผล Spark กับ Gold SQL ที่รันแยกบนข้อมูลเดียวกัน | 36/40 |
| `faithfulness_pass` | คำอธิบายผ่านเมื่อโมเดลผู้ตรวจให้ว่าทุกข้ออ้างมีหลักฐานรองรับ ข้อที่ไม่มีคะแนนนับเป็นไม่ผ่าน | 32/40 |
| `faithfulness` | คะแนนดิบเฉพาะข้อที่มีคำอธิบายให้ตรวจ | เฉลี่ย 1.00 จาก 32 ข้อ |

Langfuse เก็บและแสดงคะแนน ตัววัด Correctness ใช้โค้ด Python ส่วนตัวตรวจ Faithfulness ใช้ `qwen2.5:7b` ผ่าน Ollama ตัวตรวจจับข้อความผิดได้ 2 จาก 8 ในชุดควบคุม [ผลตรวจโดยละเอียด](../reports/FAITHFULNESS_EVIDENCE_AUDIT.md)

## ส่งคะแนนจากเครื่องที่ตั้งค่าแล้ว

ไฟล์ Compose และคีย์ของบริการในเครื่องอยู่ใน `.private/langfuse/` ใช้ Python ที่ติดตั้ง [Langfuse SDK](../requirements-langfuse.txt) แล้วรันสองคำสั่งตามลำดับ

```powershell
python scripts/local_langfuse.py reports/langfuse-expanded-40-scores.json
python scripts/local_langfuse.py reports/langfuse-expanded-40-scores.json --faithfulness-pass
```

ถ้าติดตั้ง SDK ใน `.private/langfuse/sdk` ให้ตั้ง `$env:PYTHONPATH = (Resolve-Path .private/langfuse/sdk).Path` ก่อนรัน การอ่านกลับจาก API ยืนยันคะแนนเดิม 144 รายการ และคะแนนผ่านเกณฑ์เพิ่มอีก 40 รายการ ข้อมูลที่ส่งมีเฉพาะคะแนนและข้อมูลกำกับการประเมิน ส่วนคำถาม SQL และผลรายลูกค้าเก็บในเครื่อง

หากจะให้คะแนนรอบใหม่ ให้ใช้ `python scripts/evaluate_hallucination.py --report <ผลชุดทดสอบที่รันเสร็จ> --output <ไฟล์คะแนนใหม่>` แล้วส่งไฟล์คะแนนใหม่นั้นเข้า Langfuse

ดู [วิธีรันชุดประเมิน](../evaluation/README.md) และ [ผลชุดเต็ม](../reports/BENCHMARK_FOLLOWUP.md)
