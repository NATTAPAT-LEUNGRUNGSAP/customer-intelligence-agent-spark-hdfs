# เรียก Agent ผ่าน MCP

เมื่อกดถาม AI บนเว็บ [MCP Client](../jobs/web_mcp.py) เรียกเครื่องมือ `analyze` ของ [MCP Server](../jobs/mcp_server.py) ผ่าน Streamable HTTP ภายใน Docker container เดียวกัน จากนั้น Agent ค้น RAG สร้างและตรวจ SQL แล้วส่งให้ PySpark รันกับข้อมูลบน HDFS ผลกลับผ่าน MCP ไปแสดงบนเว็บ ใน trace ของเว็บดูได้จาก `analysis_transport: mcp`

MCP ของเว็บฟังเฉพาะ loopback ใน container และเริ่มพร้อมเว็บ ส่วนแดชบอร์ดใช้ชุด SQL ของแดชบอร์ดโดยตรง หากอัปเดตจากอิมเมจเดิม ให้รัน `docker compose -f compose.yaml -f compose.web.yaml --profile web up -d --build web` เพื่อให้มี MCP SDK

แอปภายนอกใช้ MCP แบบ stdio ได้ โดยมีเครื่องมือ `list_tables`, `describe_table` และ `analyze`

ติดตั้งจาก [requirements-mcp.txt](../requirements-mcp.txt) ใช้ manifest ที่ build ผ่าน และตั้ง `OLLAMA_MODEL` กับ `CUSTOMER_PSEUDONYM_KEY` ใน environment ของ MCP ใน container Spark ใช้ตัวเปิด stdio โดยตรงเพื่อให้ช่อง protocol แยกจาก log

```sh
bash scripts/mcp_stdio.sh --manifest /app/reports/build-<run-id>.json
```

การแทนรหัสในผล MCP ครอบคลุมคอลัมน์ชื่อ `customer_id` โดยตรง ส่วนเว็บและ CLI ใช้ทางออกของตัวเอง [คู่มืออ่านโค้ด](CODE_HANDOFF.md)
