const assert = require('node:assert/strict');
const test = require('node:test');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function element(tag) {
  return {tag, attrs:{},children:[],textContent:'',
    setAttribute(k,v){this.attrs[k]=v;},
    append(...nodes){this.children.push(...nodes);},
    replaceChildren(){this.children=[];}};
}
const context={window:{},document:{createElement:element,createElementNS:(_,tag)=>element(tag)}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/charts.js'),'utf8'),context);
function render(data,kind='bar',x=0,y=1){const root=element('div');context.window.renderResultChart(data,kind,x,y,root);return root;}
const data={columns:['country','sales'],numeric_indices:[1],rows:[['A',-2],['B',3]],truncated:false};

test('bar chart handles negative values and uses safe SVG text',()=>{
  const hostile={...data,rows:[['<script>alert(1)</script>',2]]};
  const root=render(hostile),svg=root.children[0];
  assert.equal(svg.tag,'svg');assert.equal(svg.attrs.role,'img');
  assert.ok(svg.children.some(n=>n.tag==='rect'));
  assert.ok(!svg.children.some(n=>n.tag==='script'));
  assert.ok(svg.children.find(n=>n.tag==='rect').children[0].textContent.includes('<script>'));
});
test('line chart requires time axis',()=>{
  assert.equal(render(data,'line').children[0].tag,'p');
  const root=render({...data,columns:['month','sales'],rows:[['2011-02',2],['2011-01',1]]},'line');
  assert.ok(root.children[0].children.some(n=>n.tag==='polyline'));
});
test('scatter rejects categorical x and accepts two numeric columns',()=>{
  assert.equal(render(data,'scatter').children[0].tag,'p');
  const root=render({...data,numeric_indices:[0,1],rows:[[1,2],[2,3]]},'scatter');
  assert.equal(root.children[0].children.filter(n=>n.tag==='circle').length,2);
});
test('truncated chart warns about partial data',()=>{
  const root=render({...data,truncated:true});
  assert.equal(root.children[1].tag,'p');
  assert.match(root.children[1].textContent,/100/);
});
