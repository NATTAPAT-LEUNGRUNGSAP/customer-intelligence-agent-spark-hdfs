# สถาปัตยกรรม Customer Intelligence

Spark ETL อ่าน Online Retail II แล้วเขียนตาราง Parquet บน HDFS ไฟล์ manifest ระบุชุดข้อมูลที่ผ่านการเตรียม เว็บโหลดตารางจาก manifest ตอนเริ่มงาน

```mermaid
flowchart LR
    UI["เว็บ: คำถาม"] --> MCP["MCP Client → Server: analyze"]
    MCP --> RAG["RAG ค้นนิยาม"]
    RAG --> Q["Qwen สร้าง SQL"]
    Q --> G["ตรวจ SQL และทบทวนด้วยโมเดล"]
    G --> P["OPA ก่อนรัน"]
    P --> S["Spark คำนวณ"]
    H["Parquet บน HDFS"] --> S
    S --> R["ตรวจผลและ OPA หลังรัน"]
    R --> T["คืนตาราง SQL หลักฐาน และ trace"]
```

เมื่อข้อผิดพลาดแก้ได้ Agent ส่ง SQL กับเหตุผลล่าสุดกลับให้โมเดลภายในงบสามรอบ คำถามดู schema ใช้ข้อมูลที่โหลดไว้ ส่วน Dashboard ใช้ SQL ภาพรวมที่เตรียมไว้

ใน Docker เว็บส่งคำถามให้ Agent ผ่าน MCP แบบ Streamable HTTP ภายใน container ส่วน Spark ประมวล SQL ผ่าน PySpark, HDFS เก็บข้อมูล และ OPA ตัดสินนโยบาย Ollama รันโมเดลบนเครื่องหลัก แอปภายนอกสามารถเรียก Agent ผ่าน MCP แบบ stdio ได้

[อ่านโค้ดตามลำดับ](../docs/CODE_HANDOFF.md) · [จุดตรวจก่อนและหลัง Spark](../docs/TOOL_HOOKS.md)
