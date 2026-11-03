const $ = id => document.getElementById(id);
let running = false;
let chartData = null;
function updateChart() {
  window.renderResultChart(chartData,$('chart-kind').value,Number($('chart-x').value),Number($('chart-y').value),$('chart'));
}
['chart-kind','chart-x','chart-y'].forEach(id=>$(id).addEventListener('change',updateChart));
$('time-mode').addEventListener('change',()=>{
  const custom=$('time-mode').value==='custom';
  $('date-range').hidden=!custom;
  $('start-date').required=custom; $('end-date').required=custom;
});
async function status() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('ระบบยังไม่พร้อม');
    const data = await response.json(), m = data.metadata;
    $('start-date').value=m.observed_min_timestamp.slice(0,10);
    $('end-date').value=m.observed_max_timestamp.slice(0,10);
    $('dataset').textContent = `ข้อมูล ${m.observed_min_timestamp} ถึง ${m.observed_max_timestamp} · snapshot ${m.as_of_date}`;
    $('submit').disabled = false;
    window.refreshOverview();
  } catch (error) { $('progress').textContent = `เชื่อมต่อไม่ได้: ${error.message} กรุณาโหลดหน้าใหม่`; }
}
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
  if (!running) {
    $('question').value = button.dataset.question;
    $('question').focus();
    $('question').scrollIntoView({behavior:'smooth',block:'center'});
    $('progress').textContent='เติมคำถามตัวอย่างแล้ว แก้ไขได้ก่อนกดวิเคราะห์';
  }
}));
$('question-form').addEventListener('submit', async event => {
  event.preventDefault(); if (running) return;
  if(overviewBusy){$('progress').textContent='รอให้ภาพรวมคำนวณเสร็จก่อนถาม AI';return;}
  running = true; $('submit').disabled = true; $('answer').hidden = true;
  $('progress').textContent = 'กำลังค้นหลักฐาน ตรวจ SQL และประมวลผล…';
  try {
    const time_selection=$('time-mode').value==='all' ? {mode:'all'} : {mode:'custom',start:$('start-date').value,end:$('end-date').value};
    const response = await fetch('/api/query', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('question').value,time_selection,country:window.dashboardSelection().country,follow_up:$('follow-up').checked})});
    const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed');
    $('answer').hidden = false;
    $('agent-steps').replaceChildren();
    const stageNames={retrieve:'ค้นหลักฐาน',plan:'วางแผน / ตรวจ metadata',review:'SQL ผ่าน reviewer',observe:'รับผลจาก Spark',repair:'ส่งข้อผิดพลาดกลับเพื่อแก้',stop:'หยุดตามข้อจำกัด'};
    (data.agent_trace || []).forEach(step=>{const li=document.createElement('li');li.textContent=(stageNames[step.stage] || step.stage)+(step.attempt ? ` · รอบ ${step.attempt}`:'')+(step.row_count!==undefined?` · ${step.row_count} แถว`:'');$('agent-steps').append(li);});
    $('answer-heading').textContent = data.intent==='unavailable_product_categories' ? 'ชุดข้อมูลไม่มีหมวดหมู่สินค้า' : data.intent==='formula' && data.status==='information' ? 'สูตรและวิธีคำนวณ' : ({information:'ข้อมูลที่มีและคำถามที่รองรับ',executed:'ผลการวิเคราะห์',clarification:'ต้องการข้อมูลเพิ่มเติม',failed:'ยังตอบคำถามนี้ไม่ได้'}[data.status] || data.status);
    $('message').textContent = data.message || data.error || data.explanation || '';
    if (data.analysis_scope) $('message').textContent += '\n' + data.analysis_scope.note;
    if (data.selected_country) $('message').textContent += '\nประเทศที่เลือก: '+data.selected_country;
    if (data.conversation_scope) $('message').textContent += '\nใช้คำถามต่อเนื่อง: '+data.resolved_question;
    $('history').replaceChildren();
    (data.conversation_history || []).forEach(turn=>{const li=document.createElement('li');li.textContent=turn.question+' · '+turn.status;$('history').append(li);});
    $('follow-up').checked=data.status==='executed';
    chartData=data.chart_data;
    $('chart-panel').hidden=!chartData;
    if(chartData){
      ['chart-x','chart-y'].forEach(id=>{
        $(id).replaceChildren();
        chartData.columns.forEach((column,i)=>{if(id==='chart-y' && !chartData.numeric_indices.includes(i))return;const option=document.createElement('option');option.value=i;option.textContent=column;$(id).append(option);});
      });
      $('chart-y').value=chartData.numeric_indices.find(i=>i!==0) ?? chartData.numeric_indices[0];
      $('chart-kind').value='bar'; updateChart();
    }
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
    $('sql').textContent=data.executed_sql || data.sql || (data.intent==='formula' ? 'แสดงนิยามสูตรและ SQL expression จาก RAG โดยยังไม่ได้รันคำนวณ' : data.status==='information' ? 'คำถามสำรวจชุดข้อมูล: อ่านจาก schema และข้อมูลกำกับที่โหลดไว้ จึงไม่ต้องรัน SQL' : 'ไม่มี SQL ที่รันสำเร็จ');
    $('evidence').replaceChildren();
    (data.references || []).forEach(item => { const p=document.createElement('p'); p.textContent=`${(data.citations || []).includes(item.id) ? '✓ ' : ''}${item.id}: ${item.text}`; $('evidence').append(p); });
    $('diagnostics').textContent=JSON.stringify({attempts:data.attempts,review:data.review,result_contract:data.result_contract,context_plan:data.context_plan,context_blocked:data.context_blocked,context_usage:data.context_usage,agent_trace:data.agent_trace},null,2);
    $('progress').textContent=['executed','information'].includes(data.status) ? 'แสดงข้อมูลแล้ว' : 'ดูรายละเอียดด้านล่าง';
  } catch (error) { $('progress').textContent=`เกิดข้อผิดพลาด: ${error.message}`; }
  finally { running=false; $('submit').disabled=false; }
});
status();
