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
   for(const match of html.matchAll(/<(?:input|select|button|p|div|pre)\b([^>]*)>/g)){
    const attrs=match[1], el=new Element();
    for(const a of attrs.matchAll(/([\w-]+)="([^"]*)"/g)){
     const value=decode(a[2]);if(a[1]==='id'){el.id=value;ids.set('#'+value,el)}
     if(a[1]==='value')el.value=value;
     if(a[1].startsWith('data-')){el.dataset[a[1].slice(5)]=value;el.dataset[a[1].slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=value;const sel='['+a[1]+']';if(!groups.has(sel))groups.set(sel,[]);groups.get(sel).push(el)}
    }
    el.checked=/\bchecked\b/.test(attrs);this.children.push(el);
   }
  }
  get innerHTML(){return this.markup}
  addEventListener(){} focus(){} setSelectionRange(){} showModal(){this.open=true} close(){this.open=false}
 }
 for(const id of ['content','detail','detailContent','closeDetail','total','runnable','repoLink'])ids.set('#'+id,new Element());
 const nav=['start','catalog','planner','results','protocol','roadmap'].map(view=>{const e=new Element();e.dataset.view=view;return e});
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
function fillPlan(a,fields={}){
 const values={experiment:'Paired trial',control:'arm-control',treatment:'arm-treatment',model:'fixed-v1',repeats:'4',budget:'600',seed:'17',...fields};
 for(const [id,value] of Object.entries(values)) a.get('#'+id).value=String(value);
}

test('zero seed survives save, fresh application reopen and exported plan',async()=>{
 const a=await app();a.run("selected.add('R01');renderPlanner()");fillPlan(a,{seed:'0'});a.get('#savePlan').onclick();
 assert.equal(JSON.parse(a.storage.get(key)).seed,0);
 const b=await app({storage:a.storage});b.run('renderPlanner()');assert.equal(b.get('#seed').value,'0');
 b.get('#exportPlan').onclick();const plan=await b.exported();assert.equal(plan.seed,0);assert.equal(plan.tasks[0].id,'R01');assert.equal(plan.execution_status,'not_run');
 assert.equal(plan.cost_usd,null);assert.equal(plan.cost_status,'unknown');assert.equal(plan.execution_supported,false);assert.equal(plan.executable,false);
});

test('planner persists fields and filters obsolete IDs, using current task statuses',async()=>{
 const a=await app({saved:{name:'Paired trial',track:'model',control:'A',treatment:'B',model:'fixed-v1',repeats:7,budget:600,seed:17,tasks:[{id:'B01',status:'runnable'},{id:'UNKNOWN',status:'runnable'}]}});
 a.run('renderPlanner()');assert.equal(a.get('#experiment').value,'Paired trial');assert.equal(a.get('#track').value,'model');assert.equal(a.get('#repeats').value,'7');assert.equal(a.all('[data-select]').filter(e=>e.checked).length,1);
 a.get('#exportPlan').onclick();const p=await a.exported();assert.deepEqual(p.tasks,[{id:'B01',status:'design',implementation_id:null,manifest_sha256:null}]);assert.equal(p.model,'fixed-v1');assert.equal(p.seed,17);
});

test('planner rejects noninteger or unsafe seeds and missing task selections',async()=>{
 const a=await app();a.run('renderPlanner()');a.get('#exportPlan').onclick();assert.match(a.get('#planStatus').textContent,/至少选择/);
 a.run("selected.add('R01');renderPlanner()");fillPlan(a);for(const seed of ['1.5','Infinity','9007199254740992','']){a.get('#seed').value=seed;a.get('#exportPlan').onclick();assert.match(a.get('#planStatus').textContent,seed===''?/尚未填写/:/安全整数/)}assert.equal(a.downloads.length,0);
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
 const a=await app();a.run("view='results';renderResults()");const evil='<img src=x onerror="boom()">';await a.import({...validResult,security:evil,environment:{...validResult.environment,java:evil}});
 assert.equal(a.run('results.length'),1);assert.doesNotMatch(a.get('#content').innerHTML,/<img/);
 a.all('[data-result]')[0].onclick();assert.doesNotMatch(a.get('#detailContent').innerHTML,/<img/);assert.match(a.get('#detailContent').innerHTML,/&lt;img/);
});

test('unknown result task/status, missing versions and inconsistent success are rejected',async()=>{
 const a=await app();a.run("view='results';renderResults()");
 for(const change of [{task_id:'UNKNOWN'},{task_id:'B01'},{status:'unrecognized-status'},{task_version:''},{task_version:'0.0.1'},{passed:false},{checks:[]},{run:null}]){
  await a.import({...validResult,...change});assert.equal(a.run('results.length'),0,JSON.stringify(change));assert.notEqual(a.get('#resultError').textContent,'');
 }
});

test('malformed result shape and oversized files are rejected',async()=>{
 const a=await app();a.run("view='results';renderResults()");await a.import({task_id:'R01',status:'passed'});assert.equal(a.run('results.length'),0);assert.match(a.get('#resultError').textContent,/不是支持/);
 await a.get('#resultFile').onchange({target:{files:[{name:'huge.json',size:8*1024*1024+1,text:async()=>{throw Error('must not read oversized file')}}]}});assert.match(a.get('#resultError').textContent,/超过 8 MB/);assert.equal(a.run('results.length'),0);
});

test('checkbox handler updates selection used by save/export',async()=>{
 const a=await app();a.run('renderPlanner()');const c=a.all('[data-select]').find(e=>e.dataset.select==='R01');c.checked=true;c.onchange();fillPlan(a);a.get('#savePlan').onclick();assert.equal(JSON.parse(a.storage.get(key)).tasks[0].id,'R01');c.checked=false;c.onchange();a.get('#exportPlan').onclick();assert.equal(a.downloads.length,0);
});


test('valid JSON nonobjects in saved storage do not crash the planner',async()=>{
 for(const saved of [null,[],42,'unexpected']){const a=await app({saved});assert.doesNotThrow(()=>a.run('renderPlanner()'));assert.equal(a.get('#seed').value,'');assert.equal(a.get('#model').value,'');assert.equal(a.get('#control').value,'')}
});

test('saved numeric fields and task IDs are escaped before interpolation',async()=>{
 const evil='" onfocus="boom()';const a=await app({saved:{seed:evil,repeats:evil,budget:evil},taskData:[{...catalog[0],id:evil}]});a.run('renderPlanner()');
 assert.doesNotMatch(a.get('#content').innerHTML,/value="" onfocus=/);assert.doesNotMatch(a.get('#content').innerHTML,/data-select="" onfocus=/);assert.match(a.get('#content').innerHTML,/&quot; onfocus=&quot;/);
});


test('all 15 shipped baseline/reference/mutation records import with current task metadata',async()=>{
 const runData=JSON.parse(await readFile(new URL('../dist/runnable.json',import.meta.url),'utf8'));
 const a=await app({runData});a.run("view='results';renderResults()");let count=0;
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
 const a=await app({implData});a.run("selected.add('B01-slice');renderPlanner()");fillPlan(a);a.get('#exportPlan').onclick();const plan=await a.exported();assert.equal(plan.tasks[0].implementation_id,'B01-slice');assert.equal(plan.tasks[0].status,'runnable_slice');
 a.run("view='results';renderResults()");const record={schema_version:'engineering-1.0',implementation_id:'B01-slice',design_id:'B01',status:'passed',passed:true,submission_sha256:'a'.repeat(64),manifest_sha256:'b'.repeat(64),elapsed_seconds:1,exit_code:0,timestamp_utc:new Date().toISOString(),candidate_files:{'src/Main.java':'c'.repeat(64)},report:{checks:[]}};await a.import(record);assert.equal(a.run('results.length'),1);
 for(const change of [{implementation_id:'UNKNOWN'},{status:'failed'},{exit_code:1},{manifest_sha256:'bad'},{report:null}]){await a.import({...record,...change});assert.equal(a.run('results.length'),1)}
});

const file=(value,name='result.json')=>{const text=typeof value==='string'?value:JSON.stringify(value);return {name,size:Buffer.byteLength(text),text:async()=>text}};
const batch=async(a,files)=>a.get('#resultFile').onchange({target:{files}});
const pick=(a,i)=>{const c=a.all('[data-pick]').find(e=>e.dataset.pick===String(i));c.checked=true;c.onchange()};

test('multi-file import is atomic on malformed second file and supports retry',async()=>{
 const a=await app();a.run("view='results';renderResults()");await batch(a,[file(validResult),file('{','broken.json')]);
 assert.equal(a.run('results.length'),0);assert.match(a.get('#resultError').textContent,/broken.json.*本批未导入/);
 await batch(a,[file(validResult)]);assert.equal(a.run('results.length'),1);assert.match(a.get('#resultError').textContent,/新增 1/);
});

test('canonical deduplication ignores JSON key order across and within batches',async()=>{
 const a=await app();a.run("view='results';renderResults()");const reversed=Object.fromEntries(Object.entries(validResult).reverse());
 await batch(a,[file(validResult),file(reversed)]);assert.equal(a.run('results.length'),1);assert.match(a.get('#resultError').textContent,/跳过 1/);
 await a.import(reversed);assert.equal(a.run('results.length'),1);assert.match(a.get('#resultError').textContent,/新增 0.*跳过 1/);
});

test('evidence save restores after refresh; export backup reimports; selected deletion persists',async()=>{
 const a=await app();a.run("view='results';renderResults()");await a.import(validResult);a.get('#saveResults').onclick();a.get('#exportResults').onclick();const backup=await a.exported();assert.equal(backup.length,1);
 const b=await app({storage:a.storage});b.run("view='results';renderResults()");assert.equal(b.run('results.length'),1);await b.import(backup);assert.equal(b.run('results.length'),1);
 pick(b,0);b.get('#deleteResults').onclick();assert.equal(b.run('results.length'),0);assert.deepEqual(JSON.parse(a.storage.get('jab-results-v1')),[]);
 const c=await app({storage:a.storage});assert.equal(c.run('results.length'),0);
});

test('unsaved evidence does not silently persist',async()=>{
 const a=await app();a.run("view='results';renderResults()");await a.import(validResult);assert.equal(a.storage.has('jab-results-v1'),false);
 const b=await app({storage:a.storage});assert.equal(b.run('results.length'),0);
});

test('corrupt or malicious local evidence does not crash or partially restore',async()=>{
 for(const raw of ['{','null','42',JSON.stringify([validResult,{schema_version:'x'}])]){
 const storage=new Map([['jab-results-v1',raw],['jab-planner-v1','{']]);const a=await app({storage});a.run("view='results';renderResults()");assert.equal(a.run('results.length'),0);assert.match(a.get('#resultError').textContent,/无法恢复/);assert.equal(storage.get('jab-results-v1'),raw);
 }
});

test('storage failure keeps evidence in memory and blocks a stale saved deletion',async()=>{
 const a=await app();a.run("view='results';renderResults()");await a.import(validResult);a.get('#saveResults').onclick();
 a.run("localStorage.setItem=()=>{throw Error('quota')}");a.get('#saveResults').onclick();assert.match(a.get('#resultError').textContent,/保存失败/);assert.equal(a.run('results.length'),1);
 pick(a,0);a.get('#deleteResults').onclick();assert.match(a.get('#resultError').textContent,/未删除/);assert.equal(a.run('results.length'),1);
});

test('same task and version comparison stays neutral and disallows cross-version records',async()=>{
 const a=await app();a.run("view='results';renderResults()");await a.import([validResult,{...validResult,timestamp_utc:'2026-10-27T00:00:00Z'}]);pick(a,0);pick(a,1);a.get('#compareResults').onclick();assert.match(a.get('#detailContent').innerHTML,/非模型排名/);assert.match(a.get('#detailContent').innerHTML,/未验证模型/);
 a.run("results[1].task_version='older-version'");a.get('#compareResults').onclick();assert.match(a.get('#resultError').textContent,/不能跨任务或版本/);
 a.get('#resultFilter').onchange({target:{value:a.run('resultGroup(results[0])')}});assert.equal(a.run('resultSelection.size'),0);assert.equal(a.all('[data-pick]').length,1);
});

test('quickstart generates only preparation commands with safe shell quoting and validation',async()=>{
 const a=await app({implData:[{id:'B01',implementation_id:'B01-slice'},{id:'S04',implementation_id:'S04-spring'}]});a.run("view='start';renderStart()");a.get('#generateSetup').onclick();assert.match(a.get('#setupStatus').textContent,/请填写/);
 a.get('#setupModel').value="model'; echo PWNED; #";a.get('#setupVersion').value='1.2.3';a.get('#setupWorkspace').value="/tmp/my space ' run";a.get('#generateSetup').onclick();
 const text=a.get('#setupCommands').textContent;assert.match(text,/experiment_tools doctor --provider codex/);assert.match(text,/--task B01-slice/);assert.match(text,/--model 'model'"'"'; echo PWNED; #'/);assert.doesNotMatch(text,/codex exec|claude -p|trusted-code/);
 a.get('#setupWorkspace').value='relative';a.get('#generateSetup').onclick();assert.match(a.get('#setupStatus').textContent,/绝对路径/);assert.doesNotMatch(a.get('#setupCommands').textContent,/experiment_tools init/);
 a.get('#setupWorkspace').value='/tmp/new';a.get('#setupModel').value='model\nmalicious';a.get('#generateSetup').onclick();assert.match(a.get('#setupStatus').textContent,/控制字符/);
 a.get('#setupModel').value='model';a.get('#setupProvider').value='claude';a.get('#setupTask').value='S04-spring';a.get('#generateSetup').onclick();assert.match(a.get('#setupCommands').textContent,/--task S04-spring --provider claude/);
});

test('design and multiple executable variants keep separate identities in plan and refresh',async()=>{
 const implData=[{id:'B01',implementation_id:'B01-slice',status:'runnable_slice',manifest_sha256:'a'.repeat(64)},{id:'B01',implementation_id:'B01-other',status:'runnable_integration_slice',manifest_sha256:'b'.repeat(64)}];
 const a=await app({implData});a.run("selected=new Set(['B01','B01-slice','B01-other']);renderPlanner()");fillPlan(a);a.get('#savePlan').onclick();const plan=JSON.parse(a.storage.get(key));assert.equal(plan.tasks[0].implementation_id,null);assert.equal(plan.tasks[0].status,'design');assert.equal(plan.tasks[1].implementation_id,'B01-slice');assert.equal(plan.tasks[2].implementation_id,'B01-other');
 const b=await app({implData,storage:a.storage});assert.deepEqual(JSON.parse(b.run('JSON.stringify([...selected])')),['B01','B01-slice','B01-other']);
});

test('import preserves no fabricated agent provenance and HTML escapes prototype payload',async()=>{
 const a=await app();a.run("view='results';renderResults()");const payload=JSON.parse(JSON.stringify(validResult).replace(/}$/,',"__proto__":{"polluted":"<script>alert(1)</script>"}}'));await a.import(payload);
 assert.equal(a.run('results.length'),1);assert.equal(a.run('results[0].run_kind'),undefined);assert.equal(a.run('({}).polluted'),undefined);a.all('[data-result]')[0].onclick();assert.doesNotMatch(a.get('#detailContent').innerHTML,/<script>/);
});

test('import busy flag blocks overlapping batches and navigation does not crash completion',async()=>{
 const a=await app();a.run("view='results';renderResults()");let resolve;const slow={name:'slow.json',size:100,text:()=>new Promise(r=>{resolve=r})};const pending=batch(a,[slow]);await batch(a,[file(validResult)]);assert.equal(a.run('results.length'),0);a.run("view='catalog';renderCatalog()");resolve(JSON.stringify(validResult));await pending;assert.equal(a.run('results.length'),1);a.run("view='results';renderResults()");assert.match(a.get('#resultError').textContent,/新增 1/);
});

test('static header links the real repository before JavaScript runs',async()=>{
 const html=await readFile(new URL('../dist/index.html',import.meta.url),'utf8');
 assert.doesNotMatch(html,/源码仓库待连接/);
 assert.doesNotMatch(html,/href="https:\/\/github\.com"/);
 assert.match(html,/id="repoLink" href="https:\/\/github\.com\/Wfyywj\/java-agent-bench" target="_blank" rel="noopener">GitHub 源码 ↗/);
 assert.match(html,/href="https:\/\/github\.com\/Wfyywj\/java-agent-bench">GitHub 源码</);
});

test('markup has native keyboard file/selection controls, status announcements and responsive CSS',async()=>{
 const a=await app();a.run("view='results';renderResults()");assert.match(a.get('#content').innerHTML,/id="resultFile" type="file"[^>]*multiple/);assert.doesNotMatch(a.get('#content').innerHTML,/id="resultFile"[^>]*hidden/);assert.match(a.get('#content').innerHTML,/aria-live="polite"/);
 const html=await readFile(new URL('../dist/index.html',import.meta.url),'utf8'),css=await readFile(new URL('../dist/style.css',import.meta.url),'utf8');assert.match(html,/class="skiplink" href="#content"/);assert.match(html,/<dialog[^>]*aria-label=/);assert.match(css,/:focus-visible/);assert.match(css,/@media\(max-width:760px\)/);assert.match(css,/prefers-reduced-motion/);assert.match(css,/\.notice\.trust/);
});

test('deletion never silently saves newly imported evidence',async()=>{
 const a=await app();a.run("view='results';renderResults()");await a.import(validResult);a.get('#saveResults').onclick();await a.import({...validResult,timestamp_utc:'2026-10-27T01:00:00Z'});pick(a,0);a.get('#deleteResults').onclick();assert.equal(a.run('results.length'),1);assert.deepEqual(JSON.parse(a.storage.get('jab-results-v1')),[]);
});

test('large site-exported backups can be restored, while single large records are rejected',async()=>{
 const a=await app();a.run("view='results';renderResults()");const big={...validResult,security:'x'.repeat(1100000)};await a.import(big);await a.import({...big,timestamp_utc:'2026-10-27T01:00:00Z'});a.get('#exportResults').onclick();const backup=await a.exported();assert.ok(JSON.stringify(backup).length>2*1024*1024);
 const b=await app();b.run("view='results';renderResults()");await b.import(backup);assert.equal(b.run('results.length'),2);await b.import({...validResult,security:'x'.repeat(2200000)});assert.equal(b.run('results.length'),2);assert.match(b.get('#resultError').textContent,/单次记录文件超过 2 MB/);
});

test('quickstart lists all engineering variants, task detail links preselect, Codex permissions are explicit',async()=>{
 const implData=JSON.parse(await readFile(new URL('../dist/implementations.json',import.meta.url),'utf8'));
 const taskData=JSON.parse(await readFile(new URL('../dist/tasks.json',import.meta.url),'utf8'));
 const a=await app({implData,taskData});a.run("detail('S04')");const button=a.all('[data-prepare]').find(x=>x.dataset.prepare==='S04-slice');button.onclick();assert.equal(a.get('#setupTask').value,'S04-slice');for(const impl of implData)assert.ok(a.get('#content').innerHTML.includes(`value="${impl.implementation_id}"`));
 a.get('#setupModel').value='fixed';a.get('#setupVersion').value='1';a.get('#setupWorkspace').value='/tmp/new';a.get('#generateSetup').onclick();assert.match(a.get('#setupCommands').textContent,/--sandbox 'read-only'/);
 a.get('#setupSandbox').value='workspace-write';a.get('#generateSetup').onclick();assert.match(a.get('#setupCommands').textContent,/--sandbox 'workspace-write'/);
 a.get('#setupProvider').value='claude';a.get('#setupProvider').onchange();assert.equal(a.get('#setupSandbox').disabled,true);a.get('#generateSetup').onclick();assert.doesNotMatch(a.get('#setupCommands').textContent,/--sandbox/);
});

test('loaded app keeps the real repository link',async()=>{
 const a=await app();
 assert.equal(a.get('#repoLink').href,'https://github.com/Wfyywj/java-agent-bench');
 assert.equal(a.get('#repoLink').textContent,'GitHub 源码 ↗');
});

test('quickstart leads with clone and prepare, and warns this is not a sandbox',async()=>{
 const a=await app({implData:[{id:'B01',implementation_id:'B01-slice',security:'not_a_secure_sandbox',model_evaluated:false}]});
 a.run("view='start';renderStart()");
 const html=a.get('#content').innerHTML;
 assert.match(html,/class="notice trust"/);
 assert.match(html,/当前执行器仅适用于可信代码，不是安全沙箱。不得直接运行任意模型或第三方生成的不可信代码/);
 assert.match(html,/隔离运行器尚未实现/);
 assert.match(html,/harness\/INTEGRITY.md/);
 const cloneAt=html.indexOf('git clone https://github.com/Wfyywj/java-agent-bench.git');
 const prepareAt=html.indexOf('python3 scripts/engineering.py prepare B01 /tmp/b01-work');
 const springAt=html.indexOf('python3 scripts/engineering.py prepare S04-spring /tmp/s04-spring-work');
 const r01At=html.indexOf('python3 harness/bench.py prepare R01 /tmp/r01-work');
 const zipNoteAt=html.indexOf('可选 ZIP');
 assert.ok(html.indexOf('notice trust')<cloneAt&&cloneAt<prepareAt&&prepareAt<springAt&&springAt<r01At&&r01At<zipNoteAt);
 assert.match(html,/托管可能失败|被托管拦截/);
 assert.doesNotMatch(html,/class="primary"[^>]*>[^<]*下载/);
 assert.match(html,/没有真实模型实测分数/);
 assert.doesNotMatch(html,/模型得分|模型分数\s*[:=：]\s*\d/);
});

test('slice and runnable details lead with clone, keep ZIP secondary, and explain security',async()=>{
 const implData=JSON.parse(await readFile(new URL('../dist/implementations.json',import.meta.url),'utf8'));
 const taskData=JSON.parse(await readFile(new URL('../dist/tasks.json',import.meta.url),'utf8'));
 const runData=JSON.parse(await readFile(new URL('../dist/runnable.json',import.meta.url),'utf8'));
 const a=await app({implData,taskData,runData});
 a.run("detail('B01')");
 let html=a.get('#detailContent').innerHTML;
 assert.match(html,/design_only/);
 assert.match(html,/设计稿本身不可执行/);
 assert.match(html,/class="notice trust"/);
 assert.match(html,/当前执行器仅适用于可信代码，不是安全沙箱/);
 assert.match(html,/security：仅可信代码的本地功能验收，不是安全沙箱；不得直接运行不可信模型或第三方代码。没有模型实测。/);
 assert.match(html,/model_evaluated 为 false，没有模型实测成绩。/);
 assert.match(html,/python3 scripts\/engineering\.py prepare B01 /);
 assert.match(html,/可选 ZIP/);
 assert.match(html,/托管可能失败/);
 for(const part of html.split('可运行工程变体').slice(1)){
  assert.ok(part.indexOf('git clone https://github.com/Wfyywj/java-agent-bench.git')>=0);
  assert.ok(part.indexOf('git clone')<part.indexOf('packages/'));
  assert.match(part,/class="primary" data-prepare="/);
  assert.doesNotMatch(part,/<a[^>]*class="(?:primary|secondary)"/);
 }
 assert.doesNotMatch(html,/模型得分|成功率\s*\d|排行榜第/);
 a.run("detail('S04')");
 html=a.get('#detailContent').innerHTML;
 assert.match(html,/packages\/S04-spring\.zip/);
 assert.match(html,/prepare S04-spring/);
 assert.match(html,/不是安全沙箱/);
 assert.match(html,/没有模型实测/);
 assert.ok(html.indexOf('git clone https://github.com/Wfyywj/java-agent-bench.git')<html.indexOf('packages/S04-spring.zip'));
 a.run("detail('R01')");
 html=a.get('#detailContent').innerHTML;
 assert.match(html,/class="notice trust"/);
 assert.match(html,/security：仅可信代码的本地功能验收，不是安全沙箱/);
 assert.match(html,/python3 harness\/bench\.py prepare R01/);
 assert.match(html,/没有候选 ZIP/);
 assert.doesNotMatch(html,/packages\/R01/);
 assert.doesNotMatch(html,/model_evaluated 为 true|模型得分/);
 a.run('renderCatalog()');
 html=a.get('#content').innerHTML;
 assert.match(html,/可执行 · 非隔离沙箱/);
 assert.match(html,/原设计 \+ 可运行切片/);
 assert.match(html,/切片 security：仅可信代码的本地功能验收，不是安全沙箱/);
 assert.match(html,/没有模型实测。/);
 assert.doesNotMatch(html,/设计稿 · 已完成|可直接评测模型/);
});

test('design-only tasks without a slice stay unrealized, and a true flag invents no score',async()=>{
 const a=await app({taskData:[{id:'G01',tier:'gold',status:'design_only',title:'Beta',summary:'Stock'}]});
 a.run("detail('G01')");
 assert.doesNotMatch(a.get('#detailContent').innerHTML,/执行边界|packages\/|git clone/);
 assert.match(a.get('#detailContent').innerHTML,/设计稿本身不可执行/);
 a.run('renderCatalog()');
 assert.match(a.get('#content').innerHTML,/设计稿 · 尚未实现/);
 assert.doesNotMatch(a.get('#content').innerHTML,/security：/);
 const b=await app({taskData:[{id:'B01',tier:'bronze',status:'design_only',title:'Alpha',summary:'Payment'}],implData:[{id:'B01',implementation_id:'B01-slice',status:'runnable_slice',tier:'bronze',security:'not_a_secure_sandbox',model_evaluated:true,scope:'partial',command:'python3 scripts/engineering.py prepare B01 /tmp/b01-work',path:'engineering/bronze/B01'}]});
 b.run('renderCatalog()');
 assert.match(b.get('#content').innerHTML,/原设计 \+ 可运行切片/);
 assert.match(b.get('#content').innerHTML,/不是安全沙箱/);
 assert.doesNotMatch(b.get('#content').innerHTML,/没有模型实测|模型得分|成功率/);
 b.run("detail('B01')");
 const detail=b.get('#detailContent').innerHTML;
 assert.match(detail,/设计稿本身不可执行/);
 assert.match(detail,/security：仅可信代码的本地功能验收，不是安全沙箱；不得直接运行不可信模型或第三方代码<\/p>/);
 assert.doesNotMatch(detail,/model_evaluated 为 false|模型得分|成功率\s*\d/);
});

test('M1 gates-green slices stay design_only and are not full-catalog ready',async()=>{
 const implData=JSON.parse(await readFile(new URL('../dist/implementations.json',import.meta.url),'utf8'));
 const taskData=JSON.parse(await readFile(new URL('../dist/tasks.json',import.meta.url),'utf8'));
 const m1=['B02','S01','S04','G01','G05'];
 const a=await app({implData,taskData});
 a.run('renderCatalog()');
 const catalog=a.get('#content').innerHTML;
 assert.match(catalog,/可执行切片 · gates_green · 非完整设计/);
 assert.match(catalog,/原设计 \+ 可运行切片/);
 assert.match(catalog,/M1 四门通过的切片标为 gates_green，不是完整目录就绪/);
 assert.doesNotMatch(catalog,/完整设计已就绪|设计稿 · 已完成|可直接评测模型|full_catalog_ready 为 true/);
 for(const id of m1){
  a.run(`detail('${id}')`);
  const html=a.get('#detailContent').innerHTML;
  assert.match(html,/design_only/);
  assert.match(html,/切片 gates_green/);
  assert.match(html,/gates_green/);
  assert.match(html,/full_catalog_ready 为 false/);
  assert.match(html,/没有模型实测/);
  assert.doesNotMatch(html,/设计稿本身不可执行/);
  assert.doesNotMatch(html,/完整设计已就绪|生产就绪|full_catalog_ready 为 true/);
 }
 a.run("detail('S04')");
 const s04=a.get('#detailContent').innerHTML;
 assert.match(s04,/S04-slice · gates_green/);
 assert.match(s04,/S04-spring · gates_green/);
 assert.match(s04,/runnable_integration_slice/);
 assert.match(s04,/不是 PostgreSQL/);
 a.run("detail('B01')");
 const b01=a.get('#detailContent').innerHTML;
 assert.match(b01,/design_only/);
 assert.match(b01,/设计稿本身不可执行/);
 assert.doesNotMatch(b01,/gates_green/);
 const green=implData.filter(x=>x.status==='gates_green').map(x=>x.implementation_id).sort();
 assert.deepEqual(green,['B02-slice','G01-slice','G05-slice','S01-slice','S04-slice','S04-spring']);
 assert.equal(implData.filter(x=>x.full_catalog_ready===true).length,0);
});

test('exported plans explicitly remain non-executable planning drafts',async()=>{
 const a=await app();a.run("selected.add('R01');renderPlanner()");fillPlan(a);a.get('#exportPlan').onclick();const plan=await a.exported();assert.equal(plan.plan_kind,'planning_draft');assert.equal(plan.execution_supported,false);assert.equal(plan.executable,false);assert.equal(plan.execution_status,'not_run');assert.equal(plan.cost_usd,null);assert.equal(plan.cost_status,'unknown');assert.match(plan.notice,/规划草案/);assert.match(plan.notice,/不可执行/);assert.match(plan.notice,/费用为空表示未知/);assert.match(a.get('#content').innerHTML,/不能直接交给 experiment_tools 或 analysis_tools 执行/);assert.match(a.get('#content').innerHTML,/不可执行/);assert.match(a.get('#content').innerHTML,/费用为空表示未知/);assert.doesNotMatch(a.get('#content').innerHTML,/导出配置交给执行器/);
});

test('planner blocks placeholder defaults and does not repeat implementation ids',async()=>{
 const implData=[{id:'B01',implementation_id:'B01-slice',status:'runnable_slice',tier:'bronze',security:'not_a_secure_sandbox',model_evaluated:false}];
 const a=await app({implData});a.run('renderPlanner()');
 const html=a.get('#content').innerHTML;
 for(const id of ['experiment','control','treatment','model','repeats','budget','seed']) assert.equal(a.get('#'+id).value,'',id);
 assert.doesNotMatch(html,/value="(?:新 Skill 配对实验|baseline-no-skill|workflow-v2|请填写精确版本)"/);
 assert.doesNotMatch(html,/placeholder="(?:baseline-no-skill|workflow-v2|请填写精确版本|新 Skill 配对实验)"/);
 assert.doesNotMatch(html,/B01-slice B01-slice/);
 assert.match(html,/data-select="B01-slice"[^>]*> B01-slice B01 的限定范围变体/);
 assert.match(html,/规划草案，不可执行/);
 assert.match(html,/费用为空表示未知/);
 a.run("selected.add('B01-slice');renderPlanner()");a.get('#exportPlan').onclick();
 assert.equal(a.downloads.length,0);assert.match(a.get('#planStatus').textContent,/占位或未填写/);
 fillPlan(a,{control:'baseline-no-skill',treatment:'workflow-v2',model:'请填写精确版本'});a.get('#exportPlan').onclick();
 assert.equal(a.downloads.length,0);assert.match(a.get('#planStatus').textContent,/占位/);
 fillPlan(a,{seed:''});a.get('#exportPlan').onclick();
 assert.equal(a.downloads.length,0);assert.match(a.get('#planStatus').textContent,/尚未填写/);
 fillPlan(a);a.get('#exportPlan').onclick();
 const plan=await a.exported();
 assert.equal(plan.plan_kind,'planning_draft');assert.equal(plan.execution_supported,false);assert.equal(plan.executable,false);
 assert.equal(plan.cost_usd,null);assert.equal(plan.cost_status,'unknown');assert.match(plan.cost_note,/未知/);
 assert.equal(plan.model,'fixed-v1');assert.equal(plan.control,'arm-control');assert.equal(plan.treatment,'arm-treatment');
 assert.equal(plan.tasks[0].implementation_id,'B01-slice');assert.equal(plan.tasks[0].id,'B01');
 assert.doesNotMatch(a.get('#planStatus').textContent,/已预注册|成功率|模型得分/);
});

test('shipped implementation tags show each implementation id once',async()=>{
 const implData=JSON.parse(await readFile(new URL('../dist/implementations.json',import.meta.url),'utf8'));
 const a=await app({implData});a.run('renderPlanner()');
 const html=a.get('#content').innerHTML;
 for(const impl of implData){
  assert.equal(html.split(impl.implementation_id+' '+impl.implementation_id).length-1,0,impl.implementation_id);
  assert.match(html,new RegExp('data-select="'+impl.implementation_id+'"[^>]*> '+impl.implementation_id+' '+impl.id+' 的限定范围变体'));
 }
});

test('saved placeholder identity is cleared and explicit numeric choices still export',async()=>{
 const tainted=await app({saved:{name:'新 Skill 配对实验',control:'baseline-no-skill',treatment:'workflow-v2',model:'请填写精确版本',repeats:3,budget:1800,seed:42,tasks:[{id:'R01'}]}});
 tainted.run('renderPlanner()');
 assert.equal(tainted.get('#experiment').value,'');assert.equal(tainted.get('#control').value,'');assert.equal(tainted.get('#treatment').value,'');assert.equal(tainted.get('#model').value,'');
 assert.equal(tainted.get('#repeats').value,'');assert.equal(tainted.get('#budget').value,'');assert.equal(tainted.get('#seed').value,'');
 assert.equal(tainted.all('[data-select]').find(e=>e.dataset.select==='R01').checked,true);
 tainted.get('#exportPlan').onclick();assert.equal(tainted.downloads.length,0);
 const kept=await app({saved:{name:'Paired trial',track:'skill',control:'arm-control',treatment:'arm-treatment',model:'fixed-v1',repeats:3,budget:1800,seed:42,tasks:[{id:'R01'}]}});
 kept.run('renderPlanner()');
 assert.equal(kept.get('#repeats').value,'3');assert.equal(kept.get('#budget').value,'1800');assert.equal(kept.get('#seed').value,'42');
 kept.get('#exportPlan').onclick();const plan=await kept.exported();
 assert.equal(plan.repeats,3);assert.equal(plan.budget,1800);assert.equal(plan.seed,42);assert.equal(plan.cost_usd,null);assert.equal(plan.execution_supported,false);
});

test('B01 detail lists slice scope and risks in readable labels, and marks duplicated rubric text',async()=>{
 const implData=JSON.parse(await readFile(new URL('../dist/implementations.json',import.meta.url),'utf8'));
 const taskData=JSON.parse(await readFile(new URL('../dist/tasks.json',import.meta.url),'utf8'));
 const runData=JSON.parse(await readFile(new URL('../dist/runnable.json',import.meta.url),'utf8'));
 const a=await app({implData,taskData,runData});
 const schemaHead=/<(?:li|b|h3|h4|summary)[^>]*>\s*(?:failureCases|traps|invariants|criticalFailurePolicy)\b/;
 const rawKeyDump=/&quot;(?:failureCases|traps|invariants|criticalFailurePolicy|runtimeTarget|prerequisiteInfrastructure|plannedAssets|objectiveTestStrategy|skillAxes|networkPolicy|resourceBudget)&quot;/;
 a.run("detail('B01')");
 const html=a.get('#detailContent').innerHTML;
 assert.doesNotMatch(html,schemaHead);
 assert.doesNotMatch(html,/<(?:li|b)[^>]*>[^<]*(?:failureCases|traps|invariants|criticalFailurePolicy)/);
 assert.doesNotMatch(html,/(?:failureCases|traps|invariants|criticalFailurePolicy)[:：]/);
 assert.doesNotMatch(html,rawKeyDump);
 assert.match(html,/<b>失败情形<\/b>/);
 assert.match(html,/<b>容易漏掉的陷阱<\/b>/);
 assert.match(html,/<b>必须守住的不变量<\/b>/);
 assert.match(html,/<b>核心失败判定<\/b>/);
 assert.match(html,/<li>夏令时重叠时段<\/li>/);
 const sliceAt=html.indexOf('<b>切片支持范围</b>');
 const deliverAt=html.indexOf('<h3>交付物</h3>');
 const fullAt=html.indexOf('<h3>完整设计尚未实现</h3>');
 assert.ok(sliceAt>=0&&deliverAt>sliceAt&&fullAt>deliverAt);
 const slicePanel=html.slice(html.indexOf('可运行工程变体'),deliverAt);
 assert.match(slicePanel,/<li>CLI adapter verifies HTTP-compatible error value; does not run a live HTTP listener<\/li>/);
 assert.match(slicePanel,/<li>No model runs, scores or difficulty calibration<\/li>/);
 assert.doesNotMatch(slicePanel,/\[\s*\n\s*&quot;/);
 assert.doesNotMatch(slicePanel,/当前不声称可构建/);
 assert.ok(html.indexOf('当前不声称可构建')>fullAt);
 assert.match(html,/<b>计划运行目标<\/b>/);
 assert.match(html,/固定 Clock 与显式 ZoneId/);
 const boilerplate='提交产物与可复演证据逐项映射验收 ID；定性项按缺失/部分/完整三个锚点评分。';
 assert.equal(html.split(boilerplate).length-1,1);
 assert.match(html,/<b>设计稿占位<\/b>/);
 assert.match(html,/正确性与业务不变量/);
 assert.match(html,/回归测试与边界覆盖<br><small>设计稿占位，说明见下方共用条目。<\/small>/);
 assert.match(html,/定位或澄清证据<br><small>设计稿占位，说明见下方共用条目。<\/small>/);
 assert.match(html,/兼容性与交付清晰度<br><small>设计稿占位，说明见下方共用条目。<\/small>/);
 assert.match(html,/验收断言、独立参考模型或数据库状态；不能仅凭自述得分。/);
 assert.match(html,/不是安全沙箱/);
 assert.match(html,/可信代码/);
 assert.match(html,/没有模型实测/);
 assert.doesNotMatch(html,/模型得分|排行榜|成功率\s*\d/);
 for(const task of taskData){
  a.run(`detail(${JSON.stringify(task.id)})`);
  const page=a.get('#detailContent').innerHTML;
  assert.doesNotMatch(page,schemaHead,task.id);
  assert.doesNotMatch(page,rawKeyDump,task.id);
  assert.match(page,/<h3>完整设计尚未实现<\/h3>/,task.id);
  assert.match(page,/<b>切片支持范围<\/b>/,task.id);
  const panel=page.slice(page.indexOf('可运行工程变体'),page.indexOf('<h3>交付物</h3>'));
  assert.doesNotMatch(panel,/当前不声称可构建/,task.id);
  assert.doesNotMatch(panel,/\[\s*\n\s*&quot;/,task.id);
  for(const impl of implData.filter(x=>x.id===task.id)){
   const items=typeof impl.scope==='string'&&impl.scope.trim().startsWith('[')?JSON.parse(impl.scope):null;
   if(!items)continue;
   for(const item of items)assert.match(panel,new RegExp('<li>'+item.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'</li>'),task.id);
  }
  const counts=new Map();
  for(const r of task.rubric||[])counts.set(r.evidence,(counts.get(r.evidence)||0)+1);
  for(const [ev,n] of counts){
   if(n>1){assert.equal(page.split(ev).length-1,1,task.id);assert.match(page,/<b>设计稿占位<\/b>/,task.id)}
  }
 }
 a.run("detail('R01')");
 const r01=a.get('#detailContent').innerHTML;
 assert.match(r01,/<h3>环境与验证计划<\/h3>/);
 assert.match(r01,/<b>安全边界<\/b>/);
 assert.match(r01,/<b>任务版本<\/b>/);
 assert.match(r01,/1\.0\.1/);
 assert.doesNotMatch(r01,/完整设计尚未实现|&quot;task_version&quot;|&quot;runtime&quot;/);
 assert.match(r01,/不是安全沙箱/);
});

test('an earlier synthetic file read that finishes later does not replace the later selection',async()=>{
 const display=name=>({schema_version:'synthetic-replay-display-1.0',data_class:'SYNTHETIC TEST FIXTURES NOT MODEL RESULTS',website_import_supported:false,freeze_sha256:name==='A'?'a'.repeat(64):'b'.repeat(64),slots:[{slot_id:'slot-'+name,state:'success'}],analysis:{status:'incomplete'}});
 const textOf=doc=>JSON.stringify(doc);
 const docA=display('A'), docB=display('B');
 let releaseA;const gateA=new Promise(resolve=>{releaseA=resolve});
 const file=(name,doc,read)=>({name,size:Buffer.byteLength(textOf(doc)),text:read});
 const a=await app();
 a.run("syntheticAttempted=true;view='synthetic';render()");
 const input=a.get('#syntheticFile');
 const selectA=input.onchange({target:{files:[file('selection-a.json',docA,()=>gateA.then(()=>textOf(docA)))]}});
 const selectB=input.onchange({target:{files:[file('selection-b.json',docB,async()=>textOf(docB))]}});
 await selectB;
 assert.match(a.get('#content').innerHTML,/已只读打开 selection-b\.json/);
 assert.match(a.get('#content').innerHTML,/slot-B/);
 releaseA();
 await selectA;
 const page=a.get('#content').innerHTML;
 assert.match(page,/当前来源：selection-b\.json/);
 assert.match(page,/已只读打开 selection-b\.json/);
 assert.match(page,/slot-B/);
 assert.doesNotMatch(page,/selection-a\.json/);
 assert.doesNotMatch(page,/slot-A/);
 assert.equal(a.run('syntheticSource'),'selection-b.json');
 assert.equal(a.run('syntheticDoc.slots[0].slot_id'),'slot-B');
 assert.equal(a.run('syntheticError'),false);
});
