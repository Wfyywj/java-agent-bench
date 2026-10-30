'use strict';
const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tiers={bronze:'青铜',silver:'白银',gold:'黄金',diamond:'钻石',king:'王者'};
let tasks=[],runnables=[],implementations=[],view='catalog',tier='all',query='',selected=new Set(),results=[];
const stateKey='jab-planner-v1', resultKey='jab-results-v1';
let resultSelection=new Set(), resultFilter='', resultMessage='', storageMessage='', importing=false, planDraft=null, setupTaskId='B01-slice';
let syntheticDoc=null, syntheticMessage='', syntheticSource='', syntheticError=false, syntheticLoading=false, syntheticAttempted=false, syntheticToken=0;
const MAX_RESULTS=100, MAX_IMPORT_BYTES=8*1024*1024;
const shellQuote=s=>"'"+String(s).replace(/'/g,"'\"'\"'")+"'";
const REPO_URL='https://github.com/Wfyywj/java-agent-bench';
const TRUST_WARNING='当前执行器仅适用于可信代码，不是安全沙箱。不得直接运行任意模型或第三方生成的不可信代码。工作区清理与公开测试不是竞赛隔离，隔离运行器尚未实现。详见仓库 harness/INTEGRITY.md。';
const trustBanner=()=>`<div class="notice trust"><b>执行边界</b><p>${esc(TRUST_WARNING)}</p></div>`;
const gatesGreen=list=>Array.isArray(list)&&list.some(x=>x&&x.status==='gates_green');
function sliceStateLabel(t,impls){if(t.status==='runnable')return '● 可执行 · 非隔离沙箱';if(gatesGreen(impls))return '● 可执行切片 · gates_green · 非完整设计';if(impls.length)return '◐ 原设计 + 可运行切片';return '○ 设计稿 · 尚未实现'}
function designNotice(t,impls){if(t.status==='runnable')return '可执行机制验证，不是生产服务，也不是模型评测。';if(gatesGreen(impls))return '原设计仍是 design_only，不是完整目录就绪（full_catalog_ready 为 false）。下列切片状态为 gates_green：已通过 reference / nop_or_baseline / mutants / repeat 四门，只在声明范围内对可信代码可执行。没有模型实测，也不是生产或完整原设计就绪。';return '这是完整场景设计，不代表所有要求均已实现。下方若有工程切片，只能在其限定范围内、且仅对可信代码做本地验收；没有模型实测成绩。设计稿本身不可执行。'}
function securityMeaning(value, modelEvaluated){
 if(value==null||value==='')return '';
 const known=value==='not_a_secure_sandbox'||value==='非安全沙箱，仅可信代码';
 const meaning=known?'仅可信代码的本地功能验收，不是安全沙箱；不得直接运行不可信模型或第三方代码':String(value);
 const unevaluated=modelEvaluated===false?'没有模型实测':'';
 return `security：${meaning}${unevaluated?'。'+unevaluated+'。':''}`;
}
const PLAN_DRAFT_NOTICE='规划草案，不可执行。不能直接交给 experiment_tools 或 analysis_tools 执行，也不是已预注册的严格 A/B。费用为空表示未知，不是免费或零成本。';
const PLAN_PLACEHOLDERS=new Set(['新 Skill 配对实验','baseline-no-skill','workflow-v2','请填写精确版本']);
function sanitizePlan(saved){
 if(!isObject(saved))return {};
 const next={...saved};
 const identity=['name','control','treatment','model'];
 const tainted=identity.some(key=>PLAN_PLACEHOLDERS.has(String(next[key]??'').trim()));
 for(const key of identity) if(PLAN_PLACEHOLDERS.has(String(next[key]??'').trim())) delete next[key];
 if(tainted){
  if(String(next.repeats)==='3') delete next.repeats;
  if(String(next.budget)==='1800') delete next.budget;
  if(String(next.seed)==='42') delete next.seed;
 }
 return next;
}
function planShown(saved,key){if(!isObject(saved)||!Object.prototype.hasOwnProperty.call(saved,key)||saved[key]==null)return '';const text=String(saved[key]);return PLAN_PLACEHOLDERS.has(text.trim())?'':text;}
function filledPlanText(value){const text=String(value??'').trim();return text&&!PLAN_PLACEHOLDERS.has(text)?text:'';}
const clonePrepare=command=>`git clone ${REPO_URL}.git\ncd java-agent-bench\n${command||''}`.replace(/\s+$/,'');
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':isObject(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
const resultGroup=r=>[r.schema_version,r.task_id||r.implementation_id,r.task_version||r.manifest_sha256].join(' / ');
function restoreResults(){try{const raw=localStorage.getItem(resultKey);if(!raw)return;if(raw.length>MAX_IMPORT_BYTES)throw Error('本地记录超过容量上限');const data=JSON.parse(raw);if(!Array.isArray(data)||data.length>MAX_RESULTS)throw Error('本地记录格式无效');const seen=new Set();const next=[];for(const r of data){validateResult(r);const key=canonical(r);if(!seen.has(key)){seen.add(key);next.push(r)}}results=next;storageMessage=`已从此浏览器恢复 ${results.length} 条未认证证据。`}catch{storageMessage='本地结果无法恢复（损坏、版本不匹配或存储不可用）；未覆盖原记录。可重新导入备份。'}}
// Local storage and imported files are data, never trusted verdicts.
const isObject=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function savedPlan(){try{const p=JSON.parse(localStorage.getItem(stateKey)||'{}');return isObject(p)?p:{}}catch{return {}}}
function validateResult(r){
 if(r?.schema_version==='engineering-1.0')return validateEngineeringResult(r);
 const known=runnables.find(t=>t.id===r?.task_id&&t.status==='runnable');
 const statuses=['build_failed','compile_timeout','run_timeout','verification_failed','passed','compile_output_limit','run_output_limit'];
 if(!isObject(r)||r.schema_version!=='1.0'||!known||!/^R[0-9]{2}$/.test(r.task_id))throw Error('不是支持的单次验收结果：需要已知 R 系列任务与 schema_version 1.0');
 if(typeof r.task_version!=='string'||!r.task_version||r.task_version!==known.environment?.task_version)throw Error('任务版本不匹配；仅支持当前目录中的明确版本');
 const process=p=>isObject(p)&&Array.isArray(p.argv)&&p.argv.every(a=>typeof a==='string')&&Number.isInteger(p.exit_code)&&typeof p.timed_out==='boolean'&&typeof p.output_limited==='boolean'&&Number.isInteger(p.output_limit_bytes)&&p.output_limit_bytes>0&&Number.isFinite(p.duration_seconds)&&p.duration_seconds>=0&&typeof p.stdout==='string'&&typeof p.stderr==='string';
 if(!statuses.includes(r.status)||typeof r.passed!=='boolean'||!Number.isInteger(r.expected_checks)||r.expected_checks<8||!Array.isArray(r.checks)||!r.checks.every(c=>isObject(c)&&typeof c.name==='string'&&typeof c.passed==='boolean'&&typeof c.detail==='string')||typeof r.timestamp_utc!=='string'||!Number.isFinite(Date.parse(r.timestamp_utc))||typeof r.patch_sha256!=='string'||! /^[a-f0-9]{64}$/.test(r.patch_sha256)||!isObject(r.environment)||!['java','python','platform'].every(k=>typeof r.environment[k]==='string')||!['category','tier','security'].every(k=>typeof r[k]==='string')||!process(r.compile)||!(r.run===null||process(r.run)))throw Error('验收结果字段或状态不符合支持的格式');
 if(Array.isArray(known.acceptance)&&(r.expected_checks!==known.acceptance.length||r.checks.some(c=>!known.acceptance.includes(c.name))||new Set(r.checks.map(c=>c.name)).size!==r.checks.length))throw Error('检查名称或数量与当前任务不匹配');
 if(r.passed!==(r.status==='passed'))throw Error('passed 与 status 不一致');
 if(r.passed&&(!r.run||r.run.exit_code!==0||r.run.timed_out||r.run.output_limited||r.compile.exit_code!==0||r.compile.timed_out||r.compile.output_limited||r.checks.length!==r.expected_checks||!r.checks.every(c=>c.passed)||new Set(r.checks.map(c=>c.name)).size!==r.expected_checks))throw Error('成功状态与逐项证据不一致');
 return r;
}

function validateEngineeringResult(r){
 const known=implementations.find(x=>x.implementation_id===r.implementation_id&&x.id===r.design_id);
 const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
 if(!known||!['passed','failed','timeout','output_limit','invalid_report'].includes(r.status)||typeof r.passed!=='boolean'||r.passed!==(r.status==='passed')||!hash(r.submission_sha256)||!hash(r.manifest_sha256)||(known.manifest_sha256&&r.manifest_sha256!==known.manifest_sha256)||!Number.isFinite(r.elapsed_seconds)||r.elapsed_seconds<0||!Number.isInteger(r.exit_code)||typeof r.timestamp_utc!=='string'||!Number.isFinite(Date.parse(r.timestamp_utc))||!isObject(r.candidate_files)||!Object.values(r.candidate_files).every(hash))throw Error('工程切片结果标识、状态或证据格式无效');
 if(r.passed&&(r.exit_code!==0||!isObject(r.report)))throw Error('工程切片成功状态与执行结果不一致');
 return r;
}

const list=a=>`<ul>${(Array.isArray(a)?a:(a&&typeof a==='object'?Object.entries(a).flatMap(([k,v])=>Array.isArray(v)?v.map(x=>k+'：'+(typeof x==='string'?x:JSON.stringify(x))):[k+'：'+String(v)]):a?[String(a)]:[])).map(x=>`<li>${esc(typeof x==='string'?x:x.criterion||x.description||JSON.stringify(x))}</li>`).join('')}</ul>`;
function renderBrief(b){if(typeof b==='string')return `<p style="white-space:pre-line;line-height:1.9">${esc(b)}</p>`;if(!isObject(b))return '';return `<p class="sub">${esc(b.context)}</p><p style="line-height:1.9">${esc(b.mission)}</p><h3>执行约束</h3>${list(b.constraints)}<h3>完整场景所需材料</h3>${list(b.inputPackagePlanned)}`;}
const RISK_LABELS={failureCases:'失败情形',traps:'容易漏掉的陷阱',invariants:'必须守住的不变量',criticalFailurePolicy:'核心失败判定'};
const ENV_LABELS={runtimeTarget:'计划运行目标',prerequisiteInfrastructure:'计划中的基础设施',plannedAssets:'计划提供的材料',objectiveTestStrategy:'客观测试策略',skillAxes:'能力轴',networkPolicy:'网络策略',resourceBudget:'资源预算',runtime:'运行环境',database:'数据存储',network:'网络',security:'安全边界',task_version:'任务版本'};
function plain(v){
 if(v==null)return '';
 if(typeof v==='string'||typeof v==='number'||typeof v==='boolean')return String(v);
 if(Array.isArray(v))return v.map(plain).filter(Boolean).join('、');
 if(!isObject(v))return '';
 return Object.entries(v).map(([k,val])=>{const text=plain(val);if(!text)return '';const label=ENV_LABELS[k]||RISK_LABELS[k];return label?`${label}：${text}`:text}).filter(Boolean).join('；');
}
function textList(items){const rows=(Array.isArray(items)?items:[items]).map(plain).filter(s=>s!=='');if(!rows.length)return '';return `<ul>${rows.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`}
function labeledBlock(data, labels){
 if(Array.isArray(data))return textList(data);
 if(!isObject(data))return data==null||data===''?'':`<p>${esc(plain(data))}</p>`;
 return Object.entries(data).map(([k,v])=>{
  const label=labels[k]||'补充说明';
  if(Array.isArray(v)){const body=textList(v);return body?`<p class="small"><b>${esc(label)}</b></p>${body}`:''}
  const text=plain(v);if(!text)return '';
  return `<p class="small"><b>${esc(label)}</b></p><p>${esc(text)}</p>`;
 }).join('');
}
function scopeItems(scope){
 if(Array.isArray(scope))return scope;
 if(typeof scope!=='string'||!scope.trim().startsWith('['))return null;
 try{const parsed=JSON.parse(scope);return Array.isArray(parsed)?parsed:null}catch{return null}
}
function renderSliceScope(scope, separateDesign){
 const items=scopeItems(scope);
 const body=items?textList(items):(scope==null||scope===''?'':`<p class="sub">${esc(plain(scope))}</p>`);
 if(!body)return '';
 const note=separateDesign?'这个变体可以在这些边界内、对可信代码做本地验收。完整原设计的环境计划在下方单独列出。':'这个变体可以在这些边界内、对可信代码做本地验收。';
 return `<p class="small"><b>切片支持范围</b></p><p class="sub">${note}</p>${body}`;
}
function renderRisks(risks){if(Array.isArray(risks)||!isObject(risks))return list(risks);return labeledBlock(risks, RISK_LABELS)}
function renderRubric(items){
 if(!Array.isArray(items)||!items.length)return '';
 const counts=new Map();
 for(const r of items){const ev=String(r?.evidence??'');counts.set(ev,(counts.get(ev)||0)+1)}
 const shared=new Map();
 const rows=items.map(r=>{
  const ev=String(r?.evidence??'');
  if((counts.get(ev)||0)>1){const names=shared.get(ev)||[];names.push(String(r?.dimension??''));shared.set(ev,names)}
  const evidence=(counts.get(ev)||0)>1?'<br><small>设计稿占位，说明见下方共用条目。</small>':`<br><small>${esc(r?.evidence)}</small>`;
  return `<div class="rubric"><span>${esc(r?.dimension)}${evidence}</span><b>${esc(r?.weight)}%</b></div>`;
 }).join('');
 const notes=[...shared.entries()].map(([ev,names])=>`<p class="sub"><b>设计稿占位</b>：${esc(names.filter(Boolean).join('、'))}共用同一证据说明，尚未按题拆开。${esc(ev)}</p>`).join('');
 return rows+notes;
}
function renderEnvironmentBlock(t, taskImpls, body){
 if(!body)return '';
 if(t.status==='runnable')return `<h3>环境与验证计划</h3>${body}`;
 const unbuilt=typeof t.environment?.runtimeTarget==='string'&&t.environment.runtimeTarget.includes('当前不声称可构建');
 const intro=taskImpls.length?`<p class="sub">以下是完整原设计的环境计划，与上方切片支持范围分层展示。${unbuilt?'计划运行目标里的「当前不声称可构建」说明完整场景仍待实现。':''}已有切片只在声明范围内、对可信代码做本地验收。</p>`:'<p class="sub">以下是完整原设计的环境计划，描述尚未落地的运行目标与材料。</p>';
 return `<h3>完整设计尚未实现</h3>${intro}${body}`;
}
function download(name,data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
// Read-only viewer for synthetic-replay-display-1.0. Never calls validateResult or writes `results`.
const SYNTHETIC_SCHEMA='synthetic-replay-display-1.0', SYNTHETIC_CLASS='SYNTHETIC TEST FIXTURES NOT MODEL RESULTS';
const SYNTHETIC_SAMPLE_URLS=[
 ['../docs/samples/synthetic-replay-display-1.0.example.json','仓库冻结样本 docs/samples/synthetic-replay-display-1.0.example.json'],
 ['samples/synthetic-replay-display-1.0.example.json','站点副本 dist/samples/synthetic-replay-display-1.0.example.json']
];
const SLOT_STATES={
 success:{zh:'成功', note:'夹具断言为成功。这不是模型得分。'},
 failure:{zh:'失败', note:'夹具断言为失败。计入非成功，不从列表移除。'},
 infrastructure_failure:{zh:'基础设施失败', note:'单独的非成功结果。不并入失败，也不丢弃。'},
 missing:{zh:'缺失', note:'预定观测不可用。与执行前取消不是同一状态。'},
 cancelled:{zh:'执行前取消', note:'取消发生在任何 agent 试验之前。账本条目已终结。不是运行中超时，也不是缺失。'}
};
function rejectSynthetic(message){throw Error(message)}
function validateSyntheticDisplay(doc){
 if(Array.isArray(doc))rejectSynthetic('已拒绝：这是 JSON 数组，属于普通结果备份或批量导入。合成演练页只打开一份 synthetic-replay-display-1.0，不会把数组写入「结果与证据」。');
 if(!isObject(doc))rejectSynthetic('已拒绝：文件不是 JSON 对象。请选择 analysis/display.json（schema synthetic-replay-display-1.0）。');
 const schema=doc.schema_version;
 if(schema!==SYNTHETIC_SCHEMA){
  if(schema==='engineering-1.0')rejectSynthetic('已拒绝：这是工程切片验收结果（schema_version engineering-1.0），属于普通网站导入格式。请到「结果与证据」导入。合成演练页只接受 synthetic-replay-display-1.0。');
  if(schema==='0.1')rejectSynthetic('已拒绝：这是实验计划草案（schema_version 0.1），不是合成演练 display.json。');
  if(schema==='recipe-1.0')rejectSynthetic('已拒绝：这是 recipe 配置（schema_version recipe-1.0），不是 analysis/display.json。');
  if(schema==='trial-envelope-1.0')rejectSynthetic('已拒绝：这是单个槽位信封（schema_version trial-envelope-1.0）。请打开整份 display.json，不要把单个 slot 当结果导入。');
  if(schema==='1.0'&&doc.data_class===SYNTHETIC_CLASS)rejectSynthetic('已拒绝：这是嵌套的严格分析报告（schema_version 1.0），不是 synthetic-replay-display-1.0。不要把 analysis 单独送进结果导入。请选择 analysis/display.json。');
  if(schema==='1.0')rejectSynthetic('已拒绝：这是普通网站导入格式（schema_version 1.0 的单次验收结果）。请到「结果与证据」导入。本页只接受 synthetic-replay-display-1.0，该文件没有进入结果列表。');
  rejectSynthetic('已拒绝：schema_version 必须是 synthetic-replay-display-1.0。当前为 '+String(schema??'（缺失）')+'。文件没有进入结果列表。');
 }
 if(doc.data_class!==SYNTHETIC_CLASS)rejectSynthetic('已拒绝：data_class 必须是 SYNTHETIC TEST FIXTURES NOT MODEL RESULTS。');
 if(doc.website_import_supported!==false)rejectSynthetic('已拒绝：website_import_supported 必须为 false。本页不会把该文件送进现有结果导入。');
 if(typeof doc.freeze_sha256!=='string'||!/^[a-f0-9]{64}$/.test(doc.freeze_sha256))rejectSynthetic('已拒绝：缺少有效的 freeze_sha256。');
 if(!Array.isArray(doc.slots))rejectSynthetic('已拒绝：缺少 slots 数组。预定槽位必须来自 slots[]。');
 if(!isObject(doc.analysis))rejectSynthetic('已拒绝：缺少 analysis 对象。');
 return doc;
}
function unknownHtml(){return '<b class="unknown">「未知」</b>'}
function measuredValue(value){return value==null?unknownHtml():esc(value)}
function measuredTotal(block){if(!isObject(block)||block.total==null||block.known_count===0)return unknownHtml();return esc(block.total)}
function pairedDelta(block){if(!isObject(block)||block.mean_delta_B_minus_A==null)return unknownHtml();return esc(block.mean_delta_B_minus_A)}
function boundsText(bounds){if(!Array.isArray(bounds)||bounds.length<2||bounds[0]==null||bounds[1]==null)return unknownHtml();return esc(bounds[0])+' … '+esc(bounds[1])}
function slotKind(state){return Object.prototype.hasOwnProperty.call(SLOT_STATES, state)?state:'unknown'}
function slotMeta(state){if(slotKind(state)==='unknown')return {zh:state?String(state):'未标明', note:'文件给出了名单以外的状态。该槽位仍然保留，不并入缺失或执行前取消。'};return SLOT_STATES[state]}
function statePill(state){const kind=slotKind(state), meta=slotMeta(state), raw=kind==='unknown'?(state||'unknown'):state;return `<span class="statepill state-${kind}">${esc(meta.zh)} · ${esc(raw)}</span>`}
function slotIdentity(slot){const ident=isObject(slot.identity)?slot.identity:{};return `<span class="small">${esc(ident.implementation_id)} · repeat ${esc(ident.repeat)} · arm ${esc(ident.arm)}</span>`}
function evidenceCells(ev){
 if(ev==null)return '<td>无证据引用</td><td>无证据引用</td><td>无证据引用</td><td>无证据引用</td>';
 const cell=item=>!isObject(item)?'<td>引用缺失</td><td>引用缺失</td>':`<td class="mono">${item.path==null?'（无 path）':esc(item.path)}</td><td class="mono">${item.sha256==null?'（无 sha256）':esc(item.sha256)}</td>`;
 return cell(ev.trace)+cell(ev.evaluation);
}
function evidenceBlock(ev){
 if(ev==null)return '<p>无证据引用（evidence 为 null）。没有轨迹或验收文件。</p>';
 const part=(kind,item)=>!isObject(item)?`<p>${esc(kind)}：引用缺失</p>`:`<p class="mono">${esc(kind)} path ${item.path==null?'（无 path）':esc(item.path)}<br>${esc(kind)} sha256 ${item.sha256==null?'（无 sha256）':esc(item.sha256)}</p>`;
 return part('trace', ev.trace)+part('evaluation', ev.evaluation);
}
function hashParagraph(label, value){return `<p class="small"><b>${esc(label)}</b><br><span class="mono">${value==null?'（无）':esc(value)}</span></p>`}
function armNames(arms){const names=['A','B'];if(isObject(arms))for(const key of Object.keys(arms))if(!names.includes(key))names.push(key);return names}
function armRow(name, arm){
 if(!isObject(arm))return `<tr><td>${esc(name)}</td><td colspan="10">无此臂的严格汇总</td></tr>`;
 return `<tr><td>${esc(name)}</td><td>${esc(arm.planned)}</td><td>${esc(arm.observed)}</td><td>${esc(arm.successes)}</td><td>${esc(arm.failures)}</td><td>${esc(arm.infrastructure_failures)}</td><td>${esc(arm.missing)}</td><td>${measuredValue(arm.success_rate)}</td><td>${boundsText(arm.success_rate_bounds)}</td><td>${measuredTotal(arm.elapsed_seconds)}</td><td>${measuredTotal(arm.cost_usd)}</td></tr>`;
}
function matchedSlot(entry, slots){
 if(!isObject(entry)||!Array.isArray(slots))return null;
 return slots.find(s=>{
  if(!isObject(s)||!isObject(s.identity))return false;
  const id=s.identity;
  if(id.arm!==entry.arm||id.repeat!==entry.repeat||id.implementation_id!==entry.implementation_id)return false;
  if(entry.manifest_sha256&&id.manifest_sha256&&entry.manifest_sha256!==id.manifest_sha256)return false;
  return true;
 })||null;
}
function missingItem(entry, slots){
 const slot=matchedSlot(entry, slots);
 const state=slot?slot.state:null;
 const slotId=slot&&slot.slot_id?slot.slot_id:'（slots[] 无对应项）';
 const extra=state==='cancelled'?' <span class="small">分析器把它记在 missing_slots 里，因为没有严格记录。槽位状态仍是执行前取消，不是缺失。</span>':(state==='missing'?' <span class="small">预定观测不可用。</span>':'');
 return `<li><span class="mono">${esc(slotId)}</span> · repeat ${esc(isObject(entry)?entry.repeat:'')} · arm ${esc(isObject(entry)?entry.arm:'')} · ${statePill(state)}${extra}</li>`;
}
function warningList(warnings){if(!Array.isArray(warnings)||!warnings.length)return '';return `<div class="notice">${warnings.map(w=>`<p>${esc(typeof w==='string'?w:JSON.stringify(w))}</p>`).join('')}</div>`}
function fixtureNote(armMeta){
 if(!isObject(armMeta))return '';
 return '<h3>夹具元数据</h3>'+armNames(armMeta).map(name=>{
  const md=armMeta[name];
  if(!isObject(md))return '';
  const budget=isObject(md.budget)?md.budget:{};
  return `<p class="small"><b>臂 ${esc(name)}</b> · 夹具标签，不是实测版本：model ${esc(md.model)} · tool ${esc(md.tool)} · workflow ${esc(md.workflow)} · environment ${esc(md.environment)} · evaluator ${esc(md.evaluator)}。声明上限 wall_seconds ${esc(budget.wall_seconds)} · max_tokens ${esc(budget.max_tokens)} · max_tool_calls ${esc(budget.max_tool_calls)}。这不是已消耗的 token、调用次数或费用。</p>`;
 }).join('');
}
function legendHtml(slots){
 const counts={};for(const key of Object.keys(SLOT_STATES))counts[key]=0;let other=0;
 for(const slot of slots){if(isObject(slot)&&Object.prototype.hasOwnProperty.call(counts, slot.state))counts[slot.state]++;else other++}
 return `<div class="legend" aria-label="槽位状态图例">${Object.keys(SLOT_STATES).map(state=>`<span>${statePill(state)} <span class="small">${counts[state]}</span></span>`).join('')}${other?`<span class="small">其他 ${other}</span>`:''}</div><p class="small">缺失用虚线标出，执行前取消用蓝色双线标出。两者都留在列表里，证据都是 null，但不是同一种状态。</p>`;
}
function syntheticLedgerRow(slot, index){
 if(!isObject(slot))return `<tr class="slotrow slotrow-unknown" data-state="unknown"><td>槽位 ${index+1}</td><td>不是对象</td><td>${unknownHtml()}</td><td>${unknownHtml()}</td><td colspan="4">仍保留该位置</td></tr>`;
 const kind=slotKind(slot.state);
 return `<tr class="slotrow slotrow-${kind}" data-state="${esc(slot.state)}"><td><b class="mono">${esc(slot.slot_id)}</b><br>${slotIdentity(slot)}</td><td>${statePill(slot.state)}</td><td>${measuredValue(slot.elapsed_seconds)}</td><td>${measuredValue(slot.cost_usd)}</td>${evidenceCells(slot.evidence)}</tr>`;
}
function syntheticSlotCard(doc, slot, index){
 if(!isObject(slot))return `<article class="slot slot-unknown" data-state="unknown"><h3>槽位 ${index+1}</h3><p>这条记录不是对象，仍保留在列表中。</p></article>`;
 const kind=slotKind(slot.state), meta=slotMeta(slot.state), ident=isObject(slot.identity)?slot.identity:{}, md=isObject(slot.metadata)?slot.metadata:{}, budget=isObject(md.budget)?md.budget:{};
 const freezeNote=slot.freeze_sha256===doc.freeze_sha256?'此槽位 freeze_sha256 与文档一致。':'此槽位 freeze_sha256 与文档不一致。';
 return `<article class="slot slot-${kind}" data-state="${esc(kind==='unknown'?String(slot.state??'unknown'):slot.state)}"><h3><span class="mono">${esc(slot.slot_id)}</span> ${statePill(slot.state)}</h3><p>${esc(meta.note)}</p><p class="small">${esc(ident.implementation_id)} · repeat ${esc(ident.repeat)} · arm ${esc(ident.arm)}</p><p>耗时 elapsed_seconds：${measuredValue(slot.elapsed_seconds)} · 费用 cost_usd：${measuredValue(slot.cost_usd)}</p>${slot.elapsed_seconds==null||slot.cost_usd==null?`<p class="small">resource_unknown_reason：${esc(slot.resource_unknown_reason||'未提供')}</p>`:''}<div class="small"><b>证据引用</b>${evidenceBlock(slot.evidence)}</div>${hashParagraph('manifest_sha256', ident.manifest_sha256)}${hashParagraph('source_content_sha256', slot.source_content_sha256)}${hashParagraph('workspace_artifact_sha256', slot.workspace_artifact_sha256)}${hashParagraph('run_artifact_sha256', slot.run_artifact_sha256)}${hashParagraph('freeze_sha256', slot.freeze_sha256)}<p class="small">${esc(freezeNote)} 哈希是本地内容核对，不是签名。</p><p class="small">夹具标签，不是实测模型或 CLI 版本：model ${esc(md.model)} · tool ${esc(md.tool)} · workflow ${esc(md.workflow)} · environment ${esc(md.environment)} · evaluator ${esc(md.evaluator)}</p><p class="small">声明上限，不是已消耗：wall_seconds ${esc(budget.wall_seconds)} · max_tokens ${esc(budget.max_tokens)} · max_tool_calls ${esc(budget.max_tool_calls)}</p><p class="small">replayed_at ${esc(slot.replayed_at)} · 回放记账时间，不是 agent 开始时间，也不是耗时。run_kind ${esc(slot.run_kind)} · 槽位 schema ${esc(slot.schema_version)}（信封版本，不是本页的 synthetic-replay-display-1.0）。</p></article>`;
}
function syntheticBody(doc){
 const analysis=isObject(doc.analysis)?doc.analysis:{}, overall=isObject(analysis.overall)?analysis.overall:{}, arms=isObject(overall.arms)?overall.arms:{}, slots=Array.isArray(doc.slots)?doc.slots:[], paired=isObject(overall.paired_resources)?overall.paired_resources:{}, missing=Array.isArray(analysis.missing_slots)?analysis.missing_slots:[];
 return `<div class="panel"><h3>文档</h3><p class="small">schema_version <b>${esc(doc.schema_version)}</b> · website_import_supported <b>${esc(String(doc.website_import_supported))}</b> · 不进入现有单次结果导入。</p><p class="small">data_class ${esc(doc.data_class)}</p><p class="small mono">freeze_sha256 ${esc(doc.freeze_sha256)}</p><p class="small mono">analysis.plan_sha256 ${esc(analysis.plan_sha256)}</p><p class="small">analysis.schema_version ${esc(analysis.schema_version)} 是嵌套严格报告的版本，不是本页 schema。status <b>${esc(analysis.status)}</b>。预定槽位 ${esc(slots.length)}，计划配对 ${esc(overall.planned_pairs)}，完整配对 ${esc(overall.complete_pairs)}。有预定槽位没有严格记录时，status 保持 incomplete，不要显示成完成。</p><p class="small">success_delta_B_minus_A：${measuredValue(overall.success_delta_B_minus_A)} · 耗时差 mean_delta：${pairedDelta(paired.elapsed_seconds)} · 费用差 mean_delta：${pairedDelta(paired.cost_usd)}</p><p class="small">分母政策：${esc(analysis.denominator_policy)}</p></div><h3>预定槽位 · slots[] 共 ${esc(slots.length)} 条</h3><p class="sub">按文件顺序全部列出，包括失败、基础设施失败、缺失和执行前取消。列表不从 analysis 重建。</p>${legendHtml(slots)}<div class="tablewrap"><table class="synthetic-ledger" id="syntheticLedger"><thead><tr><th>槽位</th><th>状态</th><th>耗时</th><th>费用</th><th>trace path</th><th>trace sha256</th><th>evaluation path</th><th>evaluation sha256</th></tr></thead><tbody>${slots.map(syntheticLedgerRow).join('')}</tbody></table></div><div id="syntheticSlots">${slots.map((slot,i)=>syntheticSlotCard(doc, slot, i)).join('')}</div>${warningList(analysis.warnings)}<h3>严格报告摘要 · 不是排行榜</h3><p class="sub">臂上的模型名是 @fixture-v1 夹具标签，不是参与比较的真实模型。success_rate 为 null 时显示「未知」。success_rate_bounds 是缺失试验策略下的界，不是点估计，也不是排行榜单元格。known_count 为 0 时忽略 known_sum，不把空集的和显示成测到的 0。</p><div class="tablewrap"><table><thead><tr><th>臂</th><th>计划</th><th>已观测</th><th>成功</th><th>失败</th><th>基础设施失败</th><th>分析器 missing</th><th>成功率</th><th>成功率界</th><th>耗时合计</th><th>费用合计</th></tr></thead><tbody>${armNames(arms).map(name=>armRow(name, arms[name])).join('')}</tbody></table></div><p class="small">分析器 missing 只表示没有严格记录，执行前取消也会计入。不要把这一列读成缺失。槽位真状态见上方 slots[].state。</p><h3>analysis.missing_slots</h3><ul>${missing.length?missing.map(entry=>missingItem(entry, slots)).join(''):'<li>无</li>'}</ul>${fixtureNote(analysis.arm_metadata)}`;
}
async function loadSyntheticSample(){
 if(syntheticLoading)return;
 const token=++syntheticToken;
 syntheticLoading=true;syntheticError=false;syntheticMessage='正在读取冻结样本…';
 if(view==='synthetic')renderSynthetic();
 let failure='未能读取冻结样本。';
 try{
  for(const [url,label] of SYNTHETIC_SAMPLE_URLS){
   try{
    const res=await fetch(url);
    if(!res.ok){failure=label+' 不可用（HTTP '+res.status+'）。';continue}
    const doc=validateSyntheticDisplay(await res.json());
    if(token!==syntheticToken)return;
    syntheticDoc=doc;syntheticSource=label;syntheticError=false;syntheticMessage='已只读打开冻结样本。夹具断言不是模型分数，也没有进入「结果与证据」。';
    return;
   }catch(err){failure=err.message||failure}
  }
  if(token!==syntheticToken)return;
  syntheticError=true;syntheticMessage=failure+' 请改用文件选择 analysis/display.json。本页只接受 synthetic-replay-display-1.0，普通验收结果会被拒绝。';
 }finally{
  if(token===syntheticToken){syntheticLoading=false;if(view==='synthetic')renderSynthetic()}
 }
}
async function onSyntheticFile(e){
 const input=e.target, file=input.files&&input.files[0];
 if(!file)return;
 const token=++syntheticToken;syntheticLoading=false;
 try{
  if(file.size>2*1024*1024)throw Error('已拒绝：文件超过 2 MB。本页没有把该文件写入「结果与证据」。');
  let parsed;try{parsed=JSON.parse(await file.text())}catch{throw Error('已拒绝：不是合法 JSON。结果列表没有变化。')}
  if(token!==syntheticToken)return;
  syntheticDoc=validateSyntheticDisplay(parsed);syntheticSource=file.name;syntheticError=false;syntheticMessage='已只读打开 '+file.name+'。这不是模型成绩，也没有进入「结果与证据」。';
 }catch(err){if(token!==syntheticToken)return;syntheticError=true;syntheticMessage=err.message||'已拒绝该文件。'}
 finally{input.value='';if(token===syntheticToken&&view==='synthetic')renderSynthetic()}
}
function renderSynthetic(){
 const banner='<div class="synthetic-banner" id="syntheticBanner"><b>SYNTHETIC TEST FIXTURES NOT MODEL RESULTS</b><p>合成演练。这是工具写入的夹具断言，不是模型试点，不是 Java 验收输出，也不是模型分数或已校准的排行榜。</p></div>';
 $('#content').innerHTML=`${banner}<div class="sectionhead"><div><h2>合成演练 · 只读槽位</h2><p class="sub">读取 analysis/display.json（schema synthetic-replay-display-1.0）。website_import_supported 为 false，本页不把文件送进「结果与证据」。</p></div></div><div class="panel"><h3>打开冻结样本或本地文件</h3><p class="sub">本地预览会先读仓库里的 docs/samples/synthetic-replay-display-1.0.example.json。从 dist 目录单独打开站点时，改读同内容的 samples 副本。两者都是冻结样本的字节，不是新的试验结果。</p><div class="actions"><button type="button" class="secondary" id="loadSyntheticSample" ${syntheticLoading?'disabled':''}>重新加载冻结样本</button></div><label for="syntheticFile"><b>或选择 analysis/display.json</b></label><input id="syntheticFile" type="file" accept=".json,application/json" aria-label="选择合成演练 display.json"><p class="small">只接受 synthetic-replay-display-1.0。R 系列验收、工程切片、实验计划和单独的 analysis 报告会被拒绝，并说明原因。</p><p class="small">当前来源：${esc(syntheticSource||'尚未打开')}</p><p id="syntheticStatus" class="${syntheticError?'error':''}" role="status" aria-live="polite">${esc(syntheticMessage)}</p></div>${syntheticDoc?syntheticBody(syntheticDoc):'<p class="empty">尚未打开 display.json。</p>'}`;
 $('#loadSyntheticSample').onclick=()=>{loadSyntheticSample()};
 $('#syntheticFile').onchange=onSyntheticFile;
 if(!syntheticDoc&&!syntheticLoading&&!syntheticAttempted){syntheticAttempted=true;loadSyntheticSample()}
}
function render(){document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));({start:renderStart,catalog:renderCatalog,planner:renderPlanner,results:renderResults,synthetic:renderSynthetic,protocol:renderProtocol,roadmap:renderRoadmap}[view])()}
function card(t){const impls=implementations.filter(x=>x.id===t.id);const secured=impls.find(x=>x.security);const security=t.status==='runnable'?securityMeaning(t.security||t.environment?.security):(secured?`切片 ${securityMeaning(secured.security, impls.length&&impls.every(x=>x.model_evaluated===false)?false:undefined)}`:'');return `<article class="card"><div class="cardtop"><span class="tier ${esc(t.tier)}">${esc(tiers[t.tier]||'机制预实验')} · 暂定</span><span class="id">${esc(t.id)}</span></div><h3>${esc(t.title)}</h3><p>${esc(t.summary)}</p>${security?`<p class="securitynote">${esc(security)}</p>`:''}<div class="cardbottom"><span>${sliceStateLabel(t,impls)}</span><button data-detail="${esc(t.id)}">查看任务 ↗</button></div></article>`}
function renderCatalog(){const filtered=[...runnables,...tasks].filter(t=>(tier==='all'||t.tier===tier)&&(!query||JSON.stringify(t).toLowerCase().includes(query.toLowerCase())));$('#content').innerHTML=`<div class="startbanner"><div><b>第一次使用？从 Codex CLI / Claude Code 开始。</b><p>选变体 → 克隆仓库并 prepare → 仅对可信代码验收 → 导入证据</p></div><button class="primary" id="catalogStart">快速开始 →</button></div><div class="sectionhead"><div><h2>任务实验室</h2><p class="sub">业务边界、跨模块约束与独立验收，让难度来自真实复杂性。</p></div><span class="small">${filtered.length} 个任务</span></div><div class="toolbar"><div class="tiers"><button data-tier="all" class="${tier==='all'?'active':''}">全部</button>${Object.entries(tiers).map(([k,v])=>`<button data-tier="${k}" class="${tier===k?'active':''}">${v}</button>`).join('')}</div><input id="search" aria-label="搜索任务" placeholder="搜索任务、能力或场景…" value="${esc(query)}"></div><div class="grid">${filtered.map(card).join('')||'<p class="empty">没有匹配的任务。试试其他关键词。</p>'}</div><div class="notice">状态说明：25 个分级场景的原设计仍是 design_only，工程切片只覆盖其中声明的部分；R 系列是独立机制预实验。M1 四门通过的切片标为 gates_green，不是完整目录就绪。难度尚未经多模型实测校准，不能据此声称达到任何模型段位。</div>`;$('#catalogStart').onclick=()=>{view='start';render()};$('#search').oninput=e=>{query=e.target.value;const pos=e.target.selectionStart;renderCatalog();$('#search').focus();$('#search').setSelectionRange(pos,pos)};document.querySelectorAll('[data-tier]').forEach(b=>b.onclick=()=>{tier=b.dataset.tier;renderCatalog()});bindDetails()}
function bindDetails(){document.querySelectorAll('[data-detail]').forEach(b=>b.onclick=()=>detail(b.dataset.detail))}
function detail(id){const t=[...runnables,...tasks].find(t=>t.id===id);if(!t)return;const taskImpls=implementations.filter(x=>x.id===id);const impl=taskImpls[0];const envBody=labeledBlock(t.environment,ENV_LABELS);const designPlan=t.status!=='runnable'?envBody:'';$('#detailContent').innerHTML=`<div class="detailmeta"><span class="tier ${esc(t.tier)}">${esc(tiers[t.tier]||'机制预实验')}</span><span class="id">${esc(t.id)} / ${esc(t.status)}${gatesGreen(taskImpls)?' · 切片 gates_green':''}</span></div><h2>${esc(t.title)}</h2><p class="sub">${esc(t.summary)}</p>${t.status==='runnable'||taskImpls.length?trustBanner():''}<div class="notice">${designNotice(t,taskImpls)}</div><h3>任务背景与目标</h3>${renderBrief(t.brief)}${taskImpls.map(x=>`<div class="panel"><h3>可运行工程变体 · ${esc(x.implementation_id)}${x.status==='gates_green'?' · gates_green':''}</h3>${x.status==='gates_green'?`<p class="sub">实现状态 gates_green（${esc(x.slice_kind||'')}）。四门证据 ${esc(x.gates_evidence||'')}。full_catalog_ready 为 false；离线不可复现的依赖未标就绪。</p>`:''}<p class="securitynote">${esc(securityMeaning(x.security, x.model_evaluated===false?false:undefined))}</p>${renderSliceScope(x.scope,!!designPlan)}<h3>主路径：克隆仓库后 prepare</h3><p class="sub">权威入口是完整 git 仓库，不是 ZIP。在仓库根目录执行下列命令（来自该变体清单）。只对已审查的可信代码继续验收。</p><pre>${esc(clonePrepare(x.command))}</pre><div class="actions"><button class="primary" data-prepare="${esc(x.implementation_id)}">用快速开始继续准备 →</button><button class="secondary" data-plan-impl="${esc(x.implementation_id)}">选择此变体加入草案</button></div><p class="small zipnote">可选 ZIP：<a href="packages/${encodeURIComponent(x.implementation_id)}.zip" download>下载候选任务包</a>。仓库不提交生成包，站点能否下载取决于部署；托管可能失败（例如边缘 403 或缓存拦截）。若下载失败，请改用上方 git clone。ZIP 不能代替完整仓库，也不是防泄漏隔离。</p><p class="small">代码路径：${esc(x.path)} · 公开开发集。${x.model_evaluated===false?'model_evaluated 为 false，没有模型实测成绩。':''}</p></div>`).join('')}<h3>交付物</h3>${list(t.deliverables)}<h3>验收标准</h3>${list(t.acceptance)}<h3>风险与容易漏掉的边界</h3>${renderRisks(t.risks)}<h3>评分维度</h3>${renderRubric(t.rubric)}<h3>难度依据</h3><p class="sub">${esc(t.difficultyRationale)}</p>${t.status==='runnable'?`<h3>主路径：克隆仓库后准备</h3><p class="securitynote">${esc(securityMeaning(t.security||t.environment?.security))}</p><p class="sub">R 系列没有候选 ZIP。权威入口是完整仓库；只对已审查的可信代码验收。</p><pre>${esc(clonePrepare(t.command))}</pre>`:(t.command?`<h3>本地验证命令</h3><pre>${esc(t.command)}</pre>`:'')}${renderEnvironmentBlock(t,taskImpls,t.status==='runnable'?envBody:designPlan)}<div class="actions"><button class="primary" id="addPlan">将${t.status==='runnable'?'任务':'设计稿'}加入草案</button><button class="secondary" id="exportTask">导出任务 JSON</button></div>`;$('#addPlan').onclick=()=>{selected.add(id);$('#detail').close();view='planner';render()};document.querySelectorAll('[data-prepare]').forEach(b=>b.onclick=()=>{setupTaskId=b.dataset.prepare;$('#detail').close();view='start';render()});document.querySelectorAll('[data-plan-impl]').forEach(b=>b.onclick=()=>{selected.add(b.dataset.planImpl);$('#detail').close();view='planner';render()});$('#exportTask').onclick=()=>download(`${id}.json`,t);$('#detail').showModal()}
function capturePlanDraft(){if(!$('#experiment'))return;planDraft={name:$('#experiment').value,track:$('#track').value,control:$('#control').value,treatment:$('#treatment').value,model:$('#model').value,repeats:$('#repeats').value,budget:$('#budget').value,seed:$('#seed').value};}
function renderPlanner(){const saved=sanitizePlan(planDraft||savedPlan());$('#content').innerHTML=`<h2>设计对照实验</h2><p class="sub">一次只改变一个因素。此处只生成规划草案，不运行代码，也不是已预注册的严格 A/B 实验。</p><div class="panel"><div class="fields"><label>实验名称<input id="experiment" value="${esc(planShown(saved,'name'))}" placeholder="填写你自己的实验名称" autocomplete="off"></label><label>比较对象<select id="track"><option value="skill">Skill / 工作流消融</option><option value="model">固定工作流的模型对比</option></select></label><label>对照组标识<input id="control" value="${esc(planShown(saved,'control'))}" placeholder="填写对照组标识" autocomplete="off"></label><label>实验组标识<input id="treatment" value="${esc(planShown(saved,'treatment'))}" placeholder="填写实验组标识" autocomplete="off"></label><label>固定模型 / 模型版本<input id="model" value="${esc(planShown(saved,'model'))}" placeholder="填写精确模型 ID" autocomplete="off"></label><label>每题重复次数<input id="repeats" type="number" min="1" max="100" value="${esc(planShown(saved,'repeats'))}" placeholder="由你填写"></label><label>每次时间预算（秒）<input id="budget" type="number" min="1" max="86400" value="${esc(planShown(saved,'budget'))}" placeholder="由你填写"></label><label>随机种子<input id="seed" type="number" value="${esc(planShown(saved,'seed'))}" placeholder="由你填写"></label></div><h3>选择具体可执行变体</h3><p class="small">工程变体有独立身份与验收清单；完整场景设计仅用于规划，不会自动替换成某个切片。</p><div class="tiers">${[...runnables,...implementations.map(x=>({...x,id:x.implementation_id,title:x.id+' 的限定范围变体'+(x.status==='gates_green'?' · gates_green':'')}))].map(t=>`<label class="tag"><input type="checkbox" data-select="${esc(t.id)}" ${selected.has(t.id)?'checked':''}> ${esc(t.id)} ${esc(t.title)}</label>`).join('')}</div><details><summary>完整场景设计（不可执行）</summary><div class="tiers">${tasks.map(t=>`<label class="tag"><input type="checkbox" data-select="${esc(t.id)}" ${selected.has(t.id)?'checked':''}> ${esc(t.id)} ${esc(t.title)} · 设计稿</label>`).join('')}</div></details><div class="notice">${esc(PLAN_DRAFT_NOTICE)} 名称、对照组、实验组、模型、重复次数、预算和种子未填写，或仍是占位文字时，不能导出。占位文字不是模型、对照组或实验组的取值。请用快速开始准备具体变体。设计稿可以进入规划，但不能执行或计分。公开开发集不能保证模型未见过；严格比较应使用隔离运行、固定预算和保留测试集。</div><div class="actions"><button class="primary" id="exportPlan">导出实验计划</button><button class="secondary" id="savePlan">保存到此浏览器</button></div><p id="planStatus" role="status"></p></div>`;$('#track').value=saved.track||'skill';document.querySelectorAll('[data-select]').forEach(c=>c.onchange=()=>{c.checked?selected.add(c.dataset.select):selected.delete(c.dataset.select)});function config(){if(!selected.size)throw Error('请至少选择一个任务。');const name=filledPlanText($('#experiment').value),control=filledPlanText($('#control').value),treatment=filledPlanText($('#treatment').value),model=filledPlanText($('#model').value);if(!name||!control||!treatment||!model)throw Error('名称、对照组、实验组或模型仍是占位或未填写。占位文字不能当作模型、对照组或实验组的取值。');const repeatsRaw=String($('#repeats').value).trim(),budgetRaw=String($('#budget').value).trim(),seedRaw=String($('#seed').value).trim();if(!repeatsRaw||!budgetRaw||!seedRaw)throw Error('重复次数、时间预算和随机种子尚未填写。空着表示未知，不能导出成已决定的计划。');const repeats=Number(repeatsRaw),budget=Number(budgetRaw);if(!Number.isInteger(repeats)||repeats<1||repeats>100||!Number.isFinite(budget)||budget<1||budget>86400)throw Error('重复次数或预算超出允许范围。');if(!/^-?\d+$/.test(seedRaw))throw Error('随机种子必须是安全整数。');const seed=Number(seedRaw);if(!Number.isSafeInteger(seed))throw Error('随机种子必须是安全整数。');return {schema_version:'0.1',plan_kind:'planning_draft',execution_supported:false,executable:false,name,track:$('#track').value,control,treatment,model,repeats,budget,seed,tasks:[...selected].map(id=>{const impl=implementations.find(x=>x.implementation_id===id);return {id:impl?.id||id,status:impl?.status||[...runnables,...tasks].find(t=>t.id===id)?.status||'design',implementation_id:impl?.implementation_id||null,manifest_sha256:impl?.manifest_sha256||null}}),dataset_version:'0.2-public-dev',network_policy:'off_except_controlled_model_proxy',cost_usd:null,cost_status:'unknown',cost_note:'费用为空表示未知，不是免费或零成本。',execution_status:'not_run',notice:PLAN_DRAFT_NOTICE,created_at:new Date().toISOString()}}$('#exportPlan').onclick=()=>{try{download('experiment-plan.json',config());$('#planStatus').textContent='已导出规划草案。不可执行，没有启动任何模型或任务。费用为空表示未知。'}catch(e){$('#planStatus').textContent=e.message}};$('#savePlan').onclick=()=>{try{planDraft=config();localStorage.setItem(stateKey,JSON.stringify(planDraft));$('#planStatus').textContent='仅保存在此浏览器，可导出备份；不跨设备同步。'}catch(e){$('#planStatus').textContent=e.message}}}
function renderResults(){
 const groups=[...new Set(results.map(resultGroup))];if(resultFilter&&!groups.includes(resultFilter))resultFilter='';
 const visible=results.map((r,i)=>({r,i})).filter(({r})=>!resultFilter||resultGroup(r)===resultFilter);
 $('#content').innerHTML=`<h2>结果与证据</h2><p class="sub">本地验收记录，不是模型排行榜。按同一任务、同一版本检查证据，不推断模型能力。</p><div class="panel"><label for="resultFile"><b>导入结果 JSON（可多选）</b></label><input id="resultFile" type="file" accept=".json,application/json" multiple ${importing?'disabled':''}><p class="small">支持当前目录版本的 R 系列 / 工程变体验收结果；单次结果或本站导出的 JSON 数组；单次记录文件最多 2 MB，备份数组文件 / 每批 / 本地保存最多 8 MB，最多 ${MAX_RESULTS} 条。整批通过才导入，重复内容跳过。文件只在浏览器读取，不上传。</p><p id="resultError" role="status" aria-live="polite">${esc(resultMessage||storageMessage)}</p><div class="toolbar"><label for="resultFilter">限定任务与版本</label><select id="resultFilter"><option value="">全部记录（不合并统计）</option>${groups.map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join('')}</select></div><div class="actions"><button class="secondary" id="saveResults" ${!results.length?'disabled':''}>保存全部到此浏览器</button><button class="secondary" id="exportResults" ${!results.length?'disabled':''}>导出全部备份</button><button class="secondary" id="compareResults">对比所选证据</button><button class="secondary" id="deleteResults">删除所选</button></div><p class="small">勾选记录后对比或删除；删除同步更新已保存副本。日志可能包含敏感信息，保存前请检查。浏览器存储不跨设备，清理网站数据会丢失。</p><div id="resultList">${visible.length?visible.map(({r,i})=>`<div class="resultrow"><label class="resultselect"><input type="checkbox" data-pick="${i}" ${resultSelection.has(i)?'checked':''} aria-label="选择记录 ${i+1} ${esc(r.task_id||r.implementation_id)}"><span><b>${esc(r.task_id||r.implementation_id)}</b> <span class="tag">${esc(r.status)} · 未认证</span><span class="small resultmeta">${esc(r.timestamp_utc)}<br>版本 ${esc(r.task_version||r.manifest_sha256)}<br>提交 ${esc(r.patch_sha256||r.submission_sha256)}</span></span></label><button class="secondary" data-result="${i}">查看原始证据</button></div>`).join(''):'<div class="empty"><h3>等第一份真实结果。</h3><p>完成本地验收后导入 result.json。这里不会预填模型名称、成功率或虚构排名。</p><button class="secondary" id="resultsStart">查看快速开始</button></div>'}</div></div><div class="notice">导入仅检查字段与状态一致性，未做签名或来源认证。参考解与故障基线是验收器自检，不是 AI 模型分数；同任务同版本也不保证相同环境、预算或提示词。</div>`;
 $('#resultError').textContent=resultMessage||storageMessage;$('#resultFilter').value=resultFilter;$('#resultFilter').onchange=e=>{resultFilter=e.target.value;resultSelection.clear();renderResults()};
 if($('#resultsStart'))$('#resultsStart').onclick=()=>{view='start';render()};
 $('#resultFile').onchange=async e=>{
  if(importing)return;const input=e.target;const files=Array.from(input.files||[]);if(!files.length)return;
  importing=true;input.disabled=true;$('#resultError').textContent='正在检查整批文件…';let filename='';
  try{if(files.reduce((n,f)=>n+f.size,0)>MAX_IMPORT_BYTES)throw Error('整批文件超过 8 MB');const staged=[];
   for(const f of files){filename=f.name;const parsed=JSON.parse(await f.text());if(f.size>2*1024*1024&&!Array.isArray(parsed))throw Error('单次记录文件超过 2 MB');const records=Array.isArray(parsed)?parsed:[parsed];if(!records.length)throw Error('结果数组为空');if(records.length>MAX_RESULTS)throw Error('结果数量超过上限');for(const r of records){validateResult(r);staged.push(r)}}
   const seen=new Set(results.map(canonical)),next=[...results];let duplicates=0;
   for(const r of staged){const key=canonical(r);if(seen.has(key)){duplicates++;continue}seen.add(key);next.push(r)}
   if(next.length>MAX_RESULTS||new Blob([JSON.stringify(next)]).size>MAX_IMPORT_BYTES)throw Error('结果总量超过 100 条或 8 MB；请先导出并删除部分记录');
   const count=next.length-results.length;results=next;resultMessage=`整批导入完成：新增 ${count} 条，跳过 ${duplicates} 条重复记录。尚未保存的记录刷新后会丢失，请保存或导出。`;
  }catch(err){resultMessage=`${filename?filename+'：':''}${err.message}。本批未导入任何记录，已有结果保持不变。`}
  finally{importing=false;input.value='';if(view==='results')renderResults();else input.disabled=false}
 };
 document.querySelectorAll('[data-pick]').forEach(c=>c.onchange=()=>{const i=Number(c.dataset.pick);c.checked?resultSelection.add(i):resultSelection.delete(i)});
 document.querySelectorAll('[data-result]').forEach(b=>b.onclick=()=>{const r=results[Number(b.dataset.result)];$('#detailContent').innerHTML=`<h2>原始验收证据 · 未认证</h2><pre>${esc(JSON.stringify(r,null,2))}</pre>`;$('#detail').showModal()});
 $('#saveResults').onclick=()=>{try{localStorage.setItem(resultKey,JSON.stringify(results));resultMessage=`已保存 ${results.length} 条到此浏览器；建议导出备份。`}catch{resultMessage='保存失败：浏览器存储不可用或容量不足。记录仍在当前页面，请导出备份。'}$('#resultError').textContent=resultMessage};
 $('#exportResults').onclick=()=>download('jab-evidence-backup.json',results);
 $('#deleteResults').onclick=()=>{if(!resultSelection.size){$('#resultError').textContent='请先勾选要删除的记录。';return}const next=results.filter((_,i)=>!resultSelection.has(i));try{const raw=localStorage.getItem(resultKey);if(raw!==null){const saved=JSON.parse(raw);if(!Array.isArray(saved))throw Error('损坏的本地副本');const removed=new Set([...resultSelection].map(i=>canonical(results[i])));localStorage.setItem(resultKey,JSON.stringify(saved.filter(r=>!removed.has(canonical(r))))) }}catch{$('#resultError').textContent='未删除：无法更新浏览器副本。请先导出备份并检查浏览器存储权限。';return}results=next;resultSelection.clear();resultMessage='所选记录已删除；已保存副本同步更新。';renderResults()};
 $('#compareResults').onclick=()=>{const chosen=[...resultSelection].map(i=>results[i]).filter(Boolean);if(chosen.length<2){$('#resultError').textContent='请至少勾选两条同任务、同版本记录。';return}if(new Set(chosen.map(resultGroup)).size!==1){$('#resultError').textContent='不能跨任务或版本对比。请先用筛选器限定同一组，再勾选。';return}$('#detailContent').innerHTML=`<h2>同版本证据对照 · 非模型排名</h2><p class="sub">${esc(resultGroup(chosen[0]))}</p><div class="notice">全部为未认证的用户记录。未验证模型、预算、环境或提示词一致；耗时仅供排查，不能解释为能力或速度排名。</div><div class="tablewrap"><table><thead><tr><th>记录时间</th><th>状态</th><th>验收耗时（秒）</th><th>提交哈希</th></tr></thead><tbody>${chosen.map(r=>`<tr><td>${esc(r.timestamp_utc)}</td><td>${esc(r.status)}</td><td>${esc(r.elapsed_seconds??((r.compile?.duration_seconds||0)+(r.run?.duration_seconds||0)))}</td><td>${esc(r.submission_sha256||r.patch_sha256)}</td></tr>`).join('')}</tbody></table></div>`;$('#detail').showModal()};
}
function renderStart(){
 $('#content').innerHTML=`${trustBanner()}<div class="sectionhead"><div><h2>从第一轮可复现实验开始</h2><p class="sub">以 Codex CLI / Claude Code 为主。先克隆仓库并 prepare，再由你决定是否运行模型。 <a href="${REPO_URL}/blob/main/docs/QUICKSTART.md" target="_blank" rel="noopener">完整本地指南 ↗</a></p></div><span class="tag">01 → 04</span></div><div class="quicksteps"><div><b>01 克隆并选变体</b><p>不是 ZIP，也不是完整设计稿</p></div><div><b>02 本地准备</b><p>检查环境、生成工作区</p></div><div><b>03 手动运行与验收</b><p>仅限已审查的可信代码</p></div><div><b>04 导入证据</b><p>同任务同版本对照</p></div></div><div class="panel"><h3>01 / 克隆仓库并 prepare</h3><p class="sub">主路径是 git clone，再在仓库根目录 prepare。需要本地 Python 3、对应任务的 Java 环境与已安装的 CLI。首次使用从 B01-slice 开始（prepare 参数是 B01）。S04-spring 还需按其任务说明准备依赖后再 prepare。R01 等机制题没有 ZIP，使用 harness/bench.py prepare。任务包 ZIP 只是可选项，托管可能失败，不能代替完整仓库。</p><pre>git clone ${REPO_URL}.git
cd java-agent-bench
python3 scripts/engineering.py prepare B01 /tmp/b01-work
# S04-spring：先按其说明准备依赖，再
# python3 scripts/engineering.py prepare S04-spring /tmp/s04-spring-work
# R01：没有候选 ZIP
# python3 harness/bench.py prepare R01 /tmp/r01-work</pre><p class="small zipnote">可选 ZIP 在任务详情中提供（例如 B01-slice、S04-spring）。仓库不提交 dist/packages，站点能否下载取决于部署；若下载失败或被托管拦截，请忽略 ZIP，以上方 clone 与 prepare 为准。</p><div class="fields"><label>执行客户端<select id="setupProvider"><option value="codex">Codex CLI</option><option value="claude">Claude Code</option></select></label><label>可执行变体<select id="setupTask">${implementations.map(x=>`<option value="${esc(x.implementation_id)}">${esc(x.implementation_id)} · ${esc(tiers[x.tier]||x.id)}限定范围变体${x.status==='gates_green'?' · gates_green':''}</option>`).join('')}</select></label><label>Codex 文件权限（不适用于 Claude）<select id="setupSandbox"><option value="read-only">read-only · 只读检查，不能修复源码</option><option value="workspace-write">workspace-write · 允许修改候选工作区</option></select></label><label>精确模型 ID（必填）<input id="setupModel" placeholder="填写你将实际使用的模型 ID" autocomplete="off"></label><label>CLI 版本（必填）<input id="setupVersion" placeholder="从 codex --version / claude --version 获取"></label><label>新的工作区绝对路径（必填）<input id="setupWorkspace" placeholder="/tmp/my-first-b01-experiment" autocomplete="off"></label></div><div class="actions"><button class="primary" id="generateSetup">生成离线准备命令</button><button class="secondary" id="startCatalog">浏览全部任务与边界</button></div><p id="setupStatus" role="status" aria-live="polite"></p><pre id="setupCommands" tabindex="0" aria-label="生成的本地准备命令">填写上方信息后生成；不会在网页执行。</pre><h3>02 / 在本地仓库根目录运行准备命令</h3><p class="sub">doctor 只检查环境；init 只生成 baseline/、candidate/、PROMPT.md、command-plan.json、manifest.json 与 GUIDE.md，不调用模型、不登录、不付费。生成命令使用 POSIX shell 引号，适用于 macOS / Linux / WSL。</p><h3>03 / 阅读 GUIDE.md，再决定是否运行</h3><p class="sub">检查 command-plan.json，固定模型、CLI 版本、预算与工作流。模型调用可能收费，必须由你确认后手动执行。当前执行器不是安全沙箱。不得直接运行任意模型或第三方生成的不可信代码；不要为了消除提示而盲目加上 --trusted-code。隔离运行器尚未实现。</p><h3>04 / 独立验收并返回这里</h3><p class="sub">按 GUIDE.md 运行本地验收，保留原始日志和结果 JSON；status 可检查工作区材料，不代表模型通过验收。导入后先检查原始证据，再按同任务同版本对照；请保存或导出以免刷新丢失。</p><button class="secondary" id="startResults">前往导入结果 →</button></div><div class="notice">准备指南覆盖目录中的可执行工程变体，不包含设计稿与 R 系列机制预实验。Codex 默认只读，若要修复代码请在创建工作区前选择 workspace-write；此选项不是 Claude Code 的隔离配置。本站没有真实模型实测分数，不是模型排行榜。</div>`;
 $('#setupProvider').value='codex';$('#setupTask').value=implementations.some(x=>x.implementation_id===setupTaskId)?setupTaskId:(implementations[0]?.implementation_id||'');$('#setupSandbox').value='read-only';$('#setupProvider').onchange=()=>{$('#setupSandbox').disabled=$('#setupProvider').value!=='codex'};
 $('#generateSetup').onclick=()=>{try{const provider=$('#setupProvider').value,task=$('#setupTask').value,model=$('#setupModel').value.trim(),version=$('#setupVersion').value.trim(),workspace=$('#setupWorkspace').value.trim();if(!['codex','claude'].includes(provider)||!implementations.some(x=>x.implementation_id===task))throw Error('请选择支持的客户端与变体');if(provider==='codex'&&!['read-only','workspace-write'].includes($('#setupSandbox').value))throw Error('请选择支持的 Codex 文件权限');if(!model||!version||!workspace)throw Error('请填写模型 ID、CLI 版本与新的工作区绝对路径');if([model,version,workspace].some(x=>/[\x00-\x1f\x7f]/.test(x)))throw Error('输入不能包含换行或控制字符');if(!workspace.startsWith('/')||workspace==='/')throw Error('请使用新的非根目录绝对路径，例如 /tmp/my-first-b01-experiment');$('#setupCommands').textContent=`python3 -m experiment_tools doctor --provider ${provider}
python3 -m experiment_tools init --task ${task} --provider ${provider} --model ${shellQuote(model)} --cli-version ${shellQuote(version)}${provider==='codex'?' --sandbox '+shellQuote($('#setupSandbox').value):''} --workspace ${shellQuote(workspace)}
python3 -m experiment_tools status --workspace ${shellQuote(workspace)}`;$('#setupStatus').textContent='已生成命令。复制到本地仓库根目录执行；未启动任何模型。'}catch(e){$('#setupCommands').textContent='请修正输入后重新生成。';$('#setupStatus').textContent=e.message}};
 $('#startCatalog').onclick=()=>{view='catalog';render()};$('#startResults').onclick=()=>{view='results';render()};
}
function renderProtocol(){$('#content').innerHTML=`<h2>评测协议</h2><p class="sub">先排除“题目有问题”和“测量不公平”，再解释分数。</p><div class="panel">${[['01','任务门禁','参考解全部通过、原始缺陷失败、多个有针对性的错误修复被检出。验收必须来自业务口径，不能由被测模型自行定义。'],['02','公平对照','模型榜固定工具、提示词、预算与工作流；系统榜披露完整系统。Skill 实验固定模型和任务，做配对 A/B，并保留失败尝试。'],['03','独立验收','严肃测评需要隔离 agent 与 verifier，补丁应用到全新基线后重测。当前 Python/Java 内核只是可信代码的本地功能验证，不是安全沙箱。'],['04','证据链','固定题目版本、来源提交、环境版本、补丁哈希与原始日志。区分编译失败、业务失败、超时和基础设施失败。'],['05','报告边界','主指标为严格业务成功率。费用、时间、回归与维护性分列；报告题数、重复次数与不确定性。公开开发集始终存在污染风险。']].map(([n,t,p])=>`<div class="step"><strong>${n}</strong><div><h3>${t}</h3><p>${p}</p></div></div>`).join('')}</div><h3>参考项目 · 设计借鉴，不表示复制其题目</h3><div class="panel"><ul><li><a href="https://www.swebench.com/multilingual" target="_blank" rel="noopener">SWE-bench Multilingual</a>：真实仓库缺陷与补丁验收。</li><li><a href="https://github.com/multi-swe-bench/multi-swe-bench" target="_blank" rel="noopener">Multi-SWE-bench</a>：Java 等多语言构建与评测。</li><li><a href="https://github.com/harbor-framework/harbor" target="_blank" rel="noopener">Harbor</a>：隔离执行、任务规范与轨迹记录。</li><li><a href="https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md" target="_blank" rel="noopener">SWE-bench Pro V2</a>：独立验收与防止环境篡改。</li></ul></div>`}
function renderRoadmap(){$('#content').innerHTML=`<h2>建设进度</h2><p class="sub">把已验证的成果与仍需实现的工作放在同一张清单上。</p><div class="panel">${[['01','当前交付 · 开发预览','五档 25 个完整设计仍是 design_only，另有限定范围的工程切片；R01–R03 机制任务；本地执行入口和结果证据。切片并不等于完整生产场景。M1 六条切片（B02、S01、S04、S04-spring、G01、G05）为 gates_green，不是完整目录就绪。'],['02','下一阶段 · 真实工程化','将设计稿逐题落为 Maven/Spring/数据库工程；补齐契约、回归和故障注入测试，锁定依赖与环境镜像。'],['03','隔离与接入','接入 Harbor 或独立执行器，隔离网络与文件系统、限制资源、采集模型与子 Agent 费用。公开开发集与保留测试集分离。'],['04','实测与校准','在明确模型、调用预算及权限后，执行配对预实验，排查天花板、地板和不稳定题。难度以证据校准，不凭题目长度命名。'],['05','持续发布','版本化扩充题族，发布变更日志与回归证据；历史成绩固定到具体任务版本，不追溯性改榜。']].map(([n,t,p])=>`<div class="step"><strong>${n}</strong><div><h3>${t}</h3><p>${p}</p></div></div>`).join('')}</div>`}
$('#closeDetail').onclick=()=>$('#detail').close();$('#detail').addEventListener('click',e=>{if(e.target===$('#detail'))$('#detail').close()});document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{if(view==='planner')capturePlanDraft();view=b.dataset.view;render();$('#content').focus()});
Promise.all([fetch('tasks.json').then(r=>{if(!r.ok)throw Error('任务目录加载失败');return r.json()}),fetch('runnable.json').then(r=>r.ok?r.json():[]),fetch('implementations.json').then(r=>r.ok?r.json():[]).catch(()=>[])]).then(([t,r,i])=>{tasks=t;runnables=r;implementations=Array.isArray(i)?i:[];$('#total').textContent=String(tasks.length).padStart(2,'0');$('#runnable').textContent=String(r.length+implementations.length).padStart(2,'0');$('#repoLink').href=REPO_URL;$('#repoLink').textContent='GitHub 源码 ↗';try{const p=savedPlan();selected=new Set((Array.isArray(p.tasks)?p.tasks:[]).filter(isObject).map(x=>x.implementation_id||x.id).filter(id=>[...t,...r].some(x=>x.id===id)||implementations.some(x=>x.implementation_id===id)))}catch{}restoreResults();render()}).catch(e=>{$('#content').innerHTML=`<div class="notice error">${esc(e.message)}。请刷新后重试。</div>`});
