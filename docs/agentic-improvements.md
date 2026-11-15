# เรียก Agent ผ่าน MCP

[เซิร์ฟเวอร์ MCP](../jobs/mcp_server.py) เป็นช่องทางเสริมแบบ stdio มีเครื่องมือ `list_tables`, `describe_table` และ `analyze` เมื่อไคลเอนต์เลือก `analyze` คำถามจะเข้า Agent และผ่านการตรวจชุดเดียวกับช่องถาม AI บนเว็บ

ติดตั้งจาก [requirements-mcp.txt](../requirements-mcp.txt) ใช้ manifest ที่ build ผ่าน และตั้ง `OLLAMA_MODEL` กับ `CUSTOMER_PSEUDONYM_KEY` ใน environment ของ MCP ใน container Spark ใช้ตัวเปิด stdio โดยตรงเพื่อให้ช่อง protocol แยกจาก log

```sh
bash scripts/mcp_stdio.sh --manifest /app/reports/build-<run-id>.json
```

การแทนรหัสในผล MCP ครอบคลุมคอลัมน์ชื่อ `customer_id` โดยตรง ส่วนเว็บและ CLI ใช้ทางออกของตัวเอง [คู่มืออ่านโค้ด](CODE_HANDOFF.md)
