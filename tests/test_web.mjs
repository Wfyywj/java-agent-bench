/** Dependency-free unit tests for app.js using a deliberately small DOM stub.
 * These test handlers, generated markup and state, NOT browser rendering, layout,
 * accessibility, actual HTML parsing, download delivery or browser security.
 * Run: node --test tests/test_web.mjs
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../dist/app.js', import.meta.url), 'utf8');
const catalog = [{id:'B01',tier:'bronze',status:'design',title:'Alpha checkout',summary:'Payment'},
 {id:'G01',tier:'gold',status:'design',title:'Beta inventory',summary:'Stock'}];
const runnable = [{id:'R01',tier:'T2',status:'runnable',title:'Gamma runnable',summary:'Payment',environment:{task_version:'1.0.1'}}];
const key='jab-planner-v1';
const validResult = JSON.parse(await readFile(new URL('../harness/results/R01-selfcheck.json', import.meta.url),'utf8')).reference;
const decode = s => s.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
async function app({saved, taskData=catalog, runData=runnable, implData=[], storage=new Map()}={}) {
 if(saved!==undefined)storage.set(key,JSON.stringify(saved));
 const ids=new Map(), groups=new Map(), downloads=[];
 class Element {
  constructor(){this.value='';this.textContent='';this.dataset={};this.checked=false;this.open=false;this.markup='';this.children=[];this.classList={toggle(){}};}
  set innerHTML(html){
   for(const child of this.children){if(child.id)ids.delete('#'+child.id);for(const entries of groups.values()){const i=entries.indexOf(child);if(i>=0)entries.splice(i,1);}}
   this.children=[];this.markup=html;
   // Only controls needed by these unit tests. This is not a browser DOM parser.
   for(const match of html.matchAll(/<(?:input|select|button|p|div)\b([^>]*)>/g)){
    const attrs=match[1], el=new Element();
    for(const a of attrs.matchAll(/([\w-]+)="([^"]*)"/g)){
     const value=decode(a[2]);if(a[1]==='id'){el.id=value;ids.set('#'+value,el)}
     if(a[1]==='value')el.value=value;
     if(a[1].startsWith('data-')){el.dataset[a[1].slice(5)]=value;const sel='['+a[1]+']';if(!groups.has(sel))groups.set(sel,[]);groups.get(sel).push(el)}
    }
    el.checked=/\bchecked\b/.test(attrs);this.children.push(el);
   }
  }
  get innerHTML(){return this.markup}
  addEventListener(){} focus(){} setSelectionRange(){} showModal(){this.open=true} close(){this.open=false}
 }
 for(const id of ['content','detail','detailContent','closeDetail','total','runnable','repoLink'])ids.set('#'+id,new Element());
 const nav=['catalog','planner','results','protocol','roadmap'].map(view=>{const e=new Element();e.dataset.view=view;return e});
 const ctx=vm.createContext({console,Blob,Date,setTimeout:fn=>{fn();return 0},
  URL:{createObjectURL(blob){downloads.push({blob});return 'blob:test'},revokeObjectURL(){}},
  document:{querySelector:s=>ids.get(s),querySelectorAll:s=>s==='nav button'?nav:(groups.get(s)||[]),createElement(){return {click(){downloads.at(-1).name=this.download}}}},
  localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},
  fetch:async name=>({ok:true,json:async()=>name==='tasks.json'?taskData:(name==='runnable.json'?runData:implData)})});
 vm.runInContext(source,ctx,{filename:'dist/app.js'});await new Promise(setImmediate);
 return {ctx,storage,downloads,get:s=>ids.get(s),all:s=>groups.get(s)||[],run:s=>vm.runInContext(s,ctx),
  async exported(){return JSON.parse(await downloads.at(-1).blob.text())},
  async import(value){const text=JSON.stringify(value);await ids.get('#resultFile').onchange({target:{files:[{name:'result.json',size:Buffer.byteLength(text),text:async()=>text}]}})}};
}

test('zero seed survives save, fresh application reopen and exported plan',async()=>{
 const a=await app();a.run("selected.add('R01');renderPlanner()");a.get('#seed').value='0';a.get('#savePlan').onclick();
 assert.equal(JSON.parse(a.storage.get(key)).seed,0);
 const b=await app({storage:a.storage});b.run('renderPlanner()');assert.equal(b.get('#seed').value,'0');
 b.get('#exportPlan').onclick();const plan=await b.exported();assert.equal(plan.seed,0);assert.equal(plan.tasks[0].id,'R01');assert.equal(plan.execution_status,'not_run');
});

test('planner persists fields and filters obsolete IDs, using current task statuses',async()=>{
 const a=await app({saved:{name:'Paired trial',track:'model',control:'A',treatment:'B',model:'fixed-v1',repeats:7,budget:600,seed:17,tasks:[{id:'B01',status:'runnable'},{id:'UNKNOWN',status:'runnable'}]}});
 a.run('renderPlanner()');assert.equal(a.get('#experiment').value,'Paired trial');assert.equal(a.get('#track').value,'model');assert.equal(a.get('#repeats').value,'7');assert.equal(a.all('[data-select]').filter(e=>e.checked).length,1);
 a.get('#exportPlan').onclick();const p=await a.exported();assert.deepEqual(p.tasks,[{id:'B01',status:'design',implementation_id:null,manifest_sha256:null}]);assert.equal(p.model,'fixed-v1');assert.equal(p.seed,17);
});

test('planner rejects noninteger or unsafe seeds and missing task selections',async()=>{
 const a=await app();a.run('renderPlanner()');a.get('#exportPlan').onclick();assert.match(a.get('#planStatus').textContent,/至少选择/);
 a.run("selected.add('R01');renderPlanner()");for(const seed of ['1.5','Infinity','9007199254740992']){a.get('#seed').value=seed;a.get('#exportPlan').onclick();assert.match(a.get('#planStatus').textContent,/安全整数/)}assert.equal(a.downloads.length,0);
});

test('catalog tier and case-insensitive query filters intersect; unknown detail is a no-op',async()=>{
 const a=await app();a.run("tier='gold';query='INVENTORY';renderCatalog()");assert.match(a.get('#content').innerHTML,/Beta inventory/);assert.doesNotMatch(a.get('#content').innerHTML,/Alpha checkout|Gamma runnable/);
 a.run("query='checkout';renderCatalog()");assert.match(a.get('#content').innerHTML,/没有匹配/);
 a.run("detail('UNKNOWN')");assert.equal(a.get('#detail').open,false);
});

test('task titles, descriptions and detail markup are escaped',async()=>{
 const evil='<img src=x onerror="boom()"> & \'quoted\'';const a=await app({taskData:[{...catalog[0],title:evil,summary:evil,brief:evil,deliverables:[evil],acceptance:[evil],risks:[evil]}]});
 assert.doesNotMatch(a.get('#content').innerHTML,/<img/);assert.match(a.get('#content').innerHTML,/&lt;img/);
 a.run("detail('B01')");assert.doesNotMatch(a.get('#detailContent').innerHTML,/<img/);assert.match(a.get('#detailContent').innerHTML,/&quot;boom\(\)&quot;/);
});

test('imported result metadata and raw evidence are HTML-escaped',async()=>{
 const a=await app();a.run('renderResults()');const evil='<img src=x onerror="boom()">';await a.import({...validResult,security:evil,environment:{...validResult.environment,java:evil}});
 assert.equal(a.run('results.length'),1);assert.doesNotMatch(a.get('#content').innerHTML,/<img/);
 a.all('[data-result]')[0].onclick();assert.doesNotMatch(a.get('#detailContent').innerHTML,/<img/);assert.match(a.get('#detailContent').innerHTML,/&lt;img/);
});

test('unknown result task/status, missing versions and inconsistent success are rejected',async()=>{
 const a=await app();a.run('renderResults()');
 for(const change of [{task_id:'UNKNOWN'},{task_id:'B01'},{status:'unrecognized-status'},{task_version:''},{task_version:'0.0.1'},{passed:false},{checks:[]},{run:null}]){
  await a.import({...validResult,...change});assert.equal(a.run('results.length'),0,JSON.stringify(change));assert.notEqual(a.get('#resultError').textContent,'');
 }
});

test('malformed result shape and oversized files are rejected',async()=>{
 const a=await app();a.run('renderResults()');await a.import({task_id:'R01',status:'passed'});assert.equal(a.run('results.length'),0);assert.match(a.get('#resultError').textContent,/不是支持/);
 await a.get('#resultFile').onchange({target:{files:[{name:'huge.json',size:2*1024*1024+1,text:async()=>{throw Error('must not read oversized file')}}]}});assert.match(a.get('#resultError').textContent,/超过 2 MB/);assert.equal(a.run('results.length'),0);
});

test('checkbox handler updates selection used by save/export',async()=>{
 const a=await app();a.run('renderPlanner()');const c=a.all('[data-select]').find(e=>e.dataset.select==='R01');c.checked=true;c.onchange();a.get('#savePlan').onclick();assert.equal(JSON.parse(a.storage.get(key)).tasks[0].id,'R01');c.checked=false;c.onchange();a.get('#exportPlan').onclick();assert.equal(a.downloads.length,0);
});


test('valid JSON nonobjects in saved storage do not crash the planner',async()=>{
 for(const saved of [null,[],42,'unexpected']){const a=await app({saved});assert.doesNotThrow(()=>a.run('renderPlanner()'));assert.equal(a.get('#seed').value,'42')}
});

test('saved numeric fields and task IDs are escaped before interpolation',async()=>{
 const evil='" onfocus="boom()';const a=await app({saved:{seed:evil,repeats:evil,budget:evil},taskData:[{...catalog[0],id:evil}]});a.run('renderPlanner()');
 assert.doesNotMatch(a.get('#content').innerHTML,/value="" onfocus=/);assert.doesNotMatch(a.get('#content').innerHTML,/data-select="" onfocus=/);assert.match(a.get('#content').innerHTML,/&quot; onfocus=&quot;/);
});


test('all 15 shipped baseline/reference/mutation records import with current task metadata',async()=>{
 const runData=JSON.parse(await readFile(new URL('../dist/runnable.json',import.meta.url),'utf8'));
 const a=await app({runData});a.run('renderResults()');let count=0;
 for(const id of ['R01','R02','R03']){
  const packet=JSON.parse(await readFile(new URL(`../harness/results/${id}-selfcheck.json`,import.meta.url),'utf8'));
  for(const record of [packet.baseline,packet.reference,...packet.mutations.map(m=>m.result)]){
   await a.import(record);assert.equal(a.run('results.length'),++count,a.get('#resultError').textContent);
  }
 }
 assert.equal(count,15);
 await a.import({...validResult,checks:validResult.checks.map((c,i)=>i===0?{...c,name:'unknown_check'}:c)});assert.equal(a.run('results.length'),count);assert.match(a.get('#resultError').textContent,/检查名称/);
});

test('all 25 shipped design task details render with real nested data shapes',async()=>{
 const taskData=JSON.parse(await readFile(new URL('../dist/tasks.json',import.meta.url),'utf8'));
 assert.equal(taskData.length,25);const a=await app({taskData});
 for(const task of taskData){assert.doesNotThrow(()=>a.run(`detail(${JSON.stringify(task.id)})`),task.id);assert.equal(a.get('#detail').open,true);assert.ok(a.get('#detailContent').innerHTML.includes(task.id));a.get('#detail').close()}
});


test('engineering slice plan and result use distinct implementation identity',async()=>{
 const implData=[{id:'B01',implementation_id:'B01-slice',status:'runnable_slice',scope:'partial',command:'test',path:'engineering/bronze/B01'}];
 const a=await app({implData});a.run("selected.add('B01');renderPlanner()");a.get('#exportPlan').onclick();const plan=await a.exported();assert.equal(plan.tasks[0].implementation_id,'B01-slice');assert.equal(plan.tasks[0].status,'runnable_slice');
 a.run('renderResults()');const record={schema_version:'engineering-1.0',implementation_id:'B01-slice',design_id:'B01',status:'passed',passed:true,submission_sha256:'a'.repeat(64),manifest_sha256:'b'.repeat(64),elapsed_seconds:1,exit_code:0,timestamp_utc:new Date().toISOString(),candidate_files:{'src/Main.java':'c'.repeat(64)},report:{checks:[]}};await a.import(record);assert.equal(a.run('results.length'),1);
 for(const change of [{implementation_id:'UNKNOWN'},{status:'failed'},{exit_code:1},{manifest_sha256:'bad'},{report:null}]){await a.import({...record,...change});assert.equal(a.run('results.length'),1)}
});
