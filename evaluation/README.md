# วิธีประเมินระบบ

ชุด [bilingual_200.json](bilingual_200.json) มี 100 โจทย์หลักในสองภาษา รวมโจทย์ SQL 160 ข้อ ขอสูตร 24 ข้อ และข้อที่คาดหวังให้ถามกลับ 16 ข้อ

1. เปิด Spark, HDFS, OPA และ Ollama ใช้ manifest ที่ build ผ่าน ก่อนรันบนเครื่องใหม่ตรวจพาธ manifest ใน [ตัวประเมิน](../jobs/evaluate_bilingual.py)
2. รันชุดเต็มจากโฟลเดอร์โปรเจกต์:

```powershell
docker compose --profile jobs run --rm --no-deps --use-aliases analytics-job --master local[2] /app/jobs/evaluate_bilingual.py --output /app/reports/langfuse-full-200-source.json
python scripts/summarize_benchmark.py reports/langfuse-full-200-source.json evaluation/bilingual_200.json
```

**SQL Correctness** เทียบตารางที่ Agent คืนกับผล Gold SQL ซึ่งรันแยกบนข้อมูลเดียวกัน เช็กลำดับแถวเมื่อโจทย์กำหนด และนับกรณีตอบไม่สำเร็จในฐานของชุด **Recall@6** วัดหลักฐานที่ควรเจอในหกอันดับแรก ส่วน **Faithfulness** ตรวจข้ออ้างในคำอธิบายเทียบหลักฐาน SQL และผล Spark

ชุดพัฒนาใช้ตรวจการถดถอย หากใช้โจทย์ใหม่แก้ระบบแล้ว ให้ระบุว่าการรันซ้ำเป็นผลของชุดที่เคยใช้ปรับระบบ เก็บผลรายข้อไว้ในเครื่อง [รายงานผล](../reports/BENCHMARK_FOLLOWUP.md) · [การดูผลใน Langfuse](../docs/LANGFUSE_EVALUATION.md)
