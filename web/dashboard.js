let overviewBusy=false;
window.dashboardSelection=()=>({time_selection:document.getElementById('time-mode').value==='all'
  ? {mode:'all'} : {mode:'custom',start:document.getElementById('start-date').value,end:document.getElementById('end-date').value},
  country:document.getElementById('country').value || null});
async function refreshOverview(){
  if(overviewBusy)return;
  const el=id=>document.getElementById(id), button=el('refresh-dashboard');
  overviewBusy=true;button.disabled=true;el('overview-status').textContent='กำลังคำนวณภาพรวมจากข้อมูล…';
  ['time-mode','start-date','end-date','country'].forEach(id=>el(id).disabled=true);
  try{
    const response=await fetch('/api/dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(window.dashboardSelection())});
    const data=await response.json();if(!response.ok)throw new Error(data.error || 'ไม่สามารถโหลดภาพรวมได้');
    const current=el('country').value;el('country').replaceChildren(new Option('ทุกประเทศ',''));
    data.countries.forEach(country=>el('country').append(new Option(country,country)));el('country').value=current;
    const values=data.sections.kpis.result.rows[0];
    ['sales','invoices','aov','customers'].forEach((name,i)=>{
      el('kpi-'+name).textContent=values[i]===null?'—':Number(values[i]).toLocaleString('th-TH',{maximumFractionDigits:i===0||i===2?2:0});
      el('definition-'+name).textContent=data.definitions[name];
    });
    [['monthly','line'],['countries','bar'],['products','bar'],['rfm','bar']].forEach(([name,kind])=>{
      const target=el('overview-'+name), chart=data.charts[name];
      if(chart)window.renderResultChart(chart,kind,0,1,target);
      else{target.replaceChildren();const p=document.createElement('p');p.textContent='ไม่พบข้อมูลในขอบเขตนี้';target.append(p);}
    });
    el('rfm-note').textContent=`snapshot ${data.snapshot} · ${data.definitions.rfm}`;
    el('overview-status').textContent=`${data.scope.start} ถึง ${data.scope.end} · ${data.scope.country || 'ทุกประเทศ'} · ข้อมูลประวัติศาสตร์ GBP`;
    el('overview-details').textContent=JSON.stringify({build:data.build_run_id,scope:data.scope,queries:Object.fromEntries(Object.entries(data.sections).map(([key,value])=>[key,{sql:value.sql,checks:value.result_contract.status,policy:value.policy_trace.map(p=>p.allow)}]))},null,2);
    el('overview').hidden=false;
  }catch(error){el('overview-status').textContent=error.message;el('overview').hidden=true;}
  finally{overviewBusy=false;button.disabled=false;['time-mode','start-date','end-date','country'].forEach(id=>el(id).disabled=false);}
}
document.getElementById('refresh-dashboard').addEventListener('click',refreshOverview);
['time-mode','start-date','end-date','country'].forEach(id=>document.getElementById(id).addEventListener('change',()=>{
  document.getElementById('overview').hidden=true;
  document.getElementById('overview-status').textContent='ตัวกรองเปลี่ยนแล้ว กดอัปเดตภาพรวมเพื่อคำนวณใหม่';
}));
window.refreshOverview=refreshOverview;
