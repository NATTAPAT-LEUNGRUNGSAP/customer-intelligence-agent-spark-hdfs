# แชร์เว็บให้เพื่อนทดลอง

เปิด Docker, Ollama และ [เว็บหลัก](http://localhost:8090/) ไว้ จากโฟลเดอร์โปรเจกต์ รัน:

```powershell
python scripts/friend_access.py start
```

ถ้า PowerShell หา Python ไม่เจอ ให้ใช้พาธ `python.exe` ของเครื่องโดยตรง เมื่อขึ้น `ready` เปิด `.private/friend-access.txt` แล้วส่งลิงก์ HTTPS ชื่อผู้ใช้ และรหัสผ่านให้เพื่อนทางส่วนตัว

```powershell
python scripts/friend_access.py stop
python scripts/friend_access.py start --rotate
```

`stop` ปิดการแชร์ ส่วน `start --rotate` เปลี่ยนรหัสและอาจได้ลิงก์ใหม่ Caddy ตรวจรหัสผ่านก่อนส่งคำขอผ่าน Cloudflare Tunnel เครื่องต้องเปิดอยู่ตลอดการทดลอง เว็บรองรับทีละคำถามและใช้รหัสผ่านร่วมกัน [ผลตรวจ HTTPS](../reports/friend-access-verification.json)
