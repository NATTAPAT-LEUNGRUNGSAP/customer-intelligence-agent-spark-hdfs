const $ = id => document.getElementById(id);
let running = false;
async function status() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('ระบบยังไม่พร้อม');
    const data = await response.json(), m = data.metadata;
    $('dataset').textContent = `ข้อมูล ${m.observed_min_timestamp} ถึง ${m.observed_max_timestamp} · snapshot ${m.as_of_date}`;
    $('submit').disabled = false;
  } catch (error) { $('progress').textContent = `เชื่อมต่อไม่ได้: ${error.message} กรุณาโหลดหน้าใหม่`; }
}
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
  if (!running) { $('question').value = button.dataset.question; $('question').focus(); }
}));
$('question-form').addEventListener('submit', async event => {
  event.preventDefault(); if (running) return;
  running = true; $('submit').disabled = true; $('answer').hidden = true;
  $('progress').textContent = 'กำลังค้นหลักฐาน ตรวจ SQL และประมวลผล…';
  try {
    const response = await fetch('/api/query', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('question').value})});
    const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed');
    $('answer').hidden = false;
    $('answer-heading').textContent = {information:'ข้อมูลที่มีและคำถามที่รองรับ',executed:'ผลการวิเคราะห์',clarification:'ต้องการข้อมูลเพิ่มเติม',failed:'ยังตอบคำถามนี้ไม่ได้'}[data.status] || data.status;
    $('message').textContent = data.message || data.error || data.explanation || '';
    $('table').replaceChildren();
    if (data.result) {
      const table=document.createElement('table'), head=document.createElement('tr');
      data.result.columns.forEach(name => { const th=document.createElement('th'); th.textContent=name; head.append(th); });
      table.append(head);
      data.result.rows.forEach(row => { const tr=document.createElement('tr'); row.forEach(value => { const td=document.createElement('td'); td.textContent=value === null ? '—' : String(value); tr.append(td); }); table.append(tr); });
      $('table').append(table);
      if (data.result.truncated) $('message').textContent += ' · แสดงไม่เกิน 200 แถว ผลลัพธ์ยังไม่ครบ';
      if (!data.result.rows.length) $('message').textContent += ' · ไม่พบข้อมูลตามเงื่อนไข';
    }
    $('trace').textContent=`Trace ${data.trace_id} · ${data.elapsed_seconds.toFixed(2)} วินาที · ${data.model}`;
    $('sql').textContent=data.executed_sql || data.sql || (data.status==='information' ? 'คำถามสำรวจชุดข้อมูล: อ่านจาก schema และข้อมูลกำกับที่โหลดไว้ จึงไม่ต้องรัน SQL' : 'ไม่มี SQL ที่รันสำเร็จ');
    $('evidence').replaceChildren();
    (data.references || []).forEach(item => { const p=document.createElement('p'); p.textContent=`${(data.citations || []).includes(item.id) ? '✓ ' : ''}${item.id}: ${item.text}`; $('evidence').append(p); });
    $('diagnostics').textContent=JSON.stringify({attempts:data.attempts,review:data.review,result_contract:data.result_contract,context_plan:data.context_plan,context_blocked:data.context_blocked,context_usage:data.context_usage},null,2);
    $('progress').textContent=['executed','information'].includes(data.status) ? 'แสดงข้อมูลแล้ว' : 'ดูรายละเอียดด้านล่าง';
  } catch (error) { $('progress').textContent=`เกิดข้อผิดพลาด: ${error.message}`; }
  finally { running=false; $('submit').disabled=false; }
});
status();
