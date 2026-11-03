/* Draw only server-validated result data; no model HTML, script or chart code. */
window.renderResultChart = function (data, kind, x, y, container) {
  container.replaceChildren();
  const message = text => { const p=document.createElement('p');p.textContent=text;container.append(p); };
  if (!data || !data.numeric_indices.includes(y) || x===y) return message('เลือกคอลัมน์แกนที่ต่างกัน โดยแกน Y ต้องเป็นตัวเลข');
  if (kind==='scatter' && !data.numeric_indices.includes(x)) return message('กราฟจุดต้องใช้แกน X และ Y เป็นตัวเลข');
  let rows=data.rows;
  if (kind==='line') {
    if (!rows.every(row=>/^\d{4}-\d{2}(?:-\d{2})?(?:[ T].*)?$/.test(String(row[x])))) return message('กราฟเส้นรองรับแกน X ที่เป็นปี-เดือนหรือวันที่ กรุณาเลือกกราฟแท่งสำหรับหมวดหมู่');
    rows=[...rows].sort((a,b)=>String(a[x]).localeCompare(String(b[x])));
  }
  if (!rows.length) return;
  const ns='http://www.w3.org/2000/svg';
  const node=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;return n;};
  const svg=node('svg',{viewBox:'0 0 840 340',role:'img','aria-label':`${data.columns[y]} แยกตาม ${data.columns[x]}`});
  svg.append(node('title',{},`${data.columns[y]} / ${data.columns[x]}`));
  const abs=Math.max(...rows.map(r=>Math.abs(r[y])),1), values=rows.map(r=>r[y]/abs);
  const low=Math.min(0,...values),high=Math.max(0,...values),span=high-low || 1;
  const py=v=>270-(v-low)/span*230, base=py(0);
  const xs=rows.map(r=>r[x]);
  const xabs=kind==='scatter'?Math.max(...xs.map(v=>Math.abs(v)),1):1;
  const xvalues=kind==='scatter'?xs.map(v=>v/xabs):rows.map((_,i)=>i);
  const xmin=Math.min(...xvalues),xspan=Math.max(...xvalues)-xmin || 1;
  const px=i=>kind==='bar'?75+(i+.5)*720/rows.length:75+(xvalues[i]-xmin)/xspan*720;
  svg.append(node('line',{x1:70,y1:base,x2:805,y2:base,stroke:'#81978e'}));
  svg.append(node('text',{x:70,y:20,fill:'#264d43','font-size':14},data.columns[y]));
  svg.append(node('text',{x:420,y:330,'text-anchor':'middle',fill:'#264d43','font-size':14},data.columns[x]));
  if(kind==='line')svg.append(node('polyline',{points:rows.map((r,i)=>`${px(i)},${py(values[i])}`).join(' '),fill:'none',stroke:'#126453','stroke-width':3}));
  rows.forEach((r,i)=>{
    const mark=kind==='bar'?node('rect',{x:px(i)-Math.min(40,640/rows.length)/2,y:Math.min(base,py(values[i])),width:Math.min(40,640/rows.length),height:Math.max(1,Math.abs(base-py(values[i]))),fill:'#248374'}):node('circle',{cx:px(i),cy:py(values[i]),r:4,fill:'#248374'});
    mark.append(node('title',{},`${r[x]}: ${r[y].toLocaleString()}`));svg.append(mark);
    if(rows.length<=12 || i%Math.ceil(rows.length/8)===0)svg.append(node('text',{x:px(i),y:295,'text-anchor':'middle','font-size':11,fill:'#607571'},String(r[x]).slice(0,16)));
  });
  [low,high].forEach(v=>svg.append(node('text',{x:65,y:py(v)+4,'text-anchor':'end','font-size':11,fill:'#607571'},(v*abs).toLocaleString(undefined,{maximumFractionDigits:2}))));
  container.append(svg);
  if(data.truncated)message('กราฟแสดงเพียงบางส่วน สูงสุด 100 จุด โปรดดูขอบเขตของตารางประกอบ');
};
