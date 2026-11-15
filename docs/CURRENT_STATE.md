# ภาพรวมระบบปัจจุบัน

เว็บวิเคราะห์อยู่ที่ [พอร์ต 8090](http://localhost:8090/) ใช้ข้อมูล Parquet บน HDFS ผ่านบทบาทอ่านข้อมูล `ci_analyst` ส่วนงานเตรียมข้อมูลใช้ `spark-job` เว็บใช้ Python เรียก Agent โดยตรง และมี MCP แบบ stdio เป็นช่องทางเสริม

- [วิธีใช้งานเว็บ](WEB_APP.md) และ [เส้นทางในโค้ด](CODE_HANDOFF.md)
- [ผลประเมิน SQL](../reports/BENCHMARK_FOLLOWUP.md) และ [หน้าสรุป Langfuse](LANGFUSE_EVALUATION.md)
- [ผลตรวจเว็บตอนรวมระบบ](../reports/local-integration-http-verification.json) เป็นหลักฐานของรอบนั้น

ผล MCP สามารถแทนค่าคอลัมน์ชื่อ `customer_id` โดยตรงได้ตามการตั้งค่า เว็บและ CLI ยังคืนรหัสจากข้อมูลต้นทางเมื่อคำถามต้องใช้รหัส
