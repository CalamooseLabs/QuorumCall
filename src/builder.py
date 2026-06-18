"""Browser poll builder.

``render_builder_html(settings)`` renders the single-page visual poll builder
served at ``GET /new``. It mirrors ui.py's theming (the ``--p`` accent colour and
optional brand bar are injected the same way) and posts the assembled poll to the
existing ``POST /api/polls`` endpoint as multipart form-data, so no separate
create API is needed. The page carries an optional admin-key field, sent as the
``X-Admin-Key`` header (required only when the server has ``QUORUMCALL_ADMIN_KEY``
set).
"""

from settings import inject_theme

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Create a poll — QuorumCall</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  /*__QC_THEME__*/
  --p-dk:color-mix(in srgb,var(--p) 82%,#000);
  --p-lt:color-mix(in srgb,var(--p) 11%,#fff);
  --p-ring:color-mix(in srgb,var(--p) 28%,transparent);
  --text:#111827;--muted:#6b7280;--border:#e5e7eb;--bg:#f3f4f6;--surface:#fff;
  --r:12px;--rs:8px;--danger:#ef4444;
}
body{
  font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:var(--bg);min-height:100vh;display:flex;flex-direction:column;
  align-items:center;padding:2.5rem 1rem 5rem;color:var(--text);line-height:1.5;
}
.card{
  background:var(--surface);border-radius:var(--r);max-width:760px;flex:1 1 auto;min-width:0;
  box-shadow:0 1px 3px rgba(0,0,0,.07),0 6px 24px rgba(0,0,0,.07);overflow:hidden;
}
/* Layout: builder + presets sidebar */
.layout{display:flex;gap:1.25rem;align-items:flex-start;justify-content:center;width:100%;max-width:1000px}
.side{
  width:212px;flex-shrink:0;position:sticky;top:2.5rem;
  background:var(--surface);border-radius:var(--r);padding:1rem .9rem;
  box-shadow:0 1px 3px rgba(0,0,0,.07),0 6px 24px rgba(0,0,0,.07);
}
.side-title{font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.side-sub{font-size:.78rem;color:var(--muted);margin:.15rem 0 .75rem}
.presets{display:flex;flex-direction:column;gap:.4rem}
.preset{
  width:100%;text-align:left;padding:.5rem .7rem;
  border:1.5px solid var(--border);border-radius:var(--rs);background:var(--surface);
  color:var(--text);font-size:.88rem;font-family:inherit;cursor:pointer;
  transition:border-color .1s,background .1s,color .1s;
}
.preset:hover{border-color:var(--p);background:var(--p-lt);color:var(--p-dk)}
@media(max-width:840px){
  .layout{flex-direction:column;align-items:stretch;max-width:760px}
  .side{position:static;width:auto}
  .presets{flex-direction:row;flex-wrap:wrap}
  .preset{width:auto}
}
.brand-bar{display:flex;align-items:center;gap:.65rem;padding:.85rem 1.75rem;background:var(--bg);border-bottom:1px solid var(--border)}
.brand-icon-img{height:26px;width:auto;object-fit:contain;flex-shrink:0}
.brand-name{font-size:.9rem;font-weight:600;color:var(--text)}
.content{padding:1.75rem 2rem 2rem}
h1.title{font-size:1.4rem;font-weight:700;margin-bottom:.25rem}
.sub{color:var(--muted);font-size:.9rem;margin-bottom:1.5rem}
.fl{display:block;font-size:.8rem;font-weight:600;color:var(--text);margin:.9rem 0 .3rem}
.fl .req{color:var(--danger)}
.hint{font-size:.78rem;color:var(--muted);font-weight:400}
input[type=text],input[type=password],input[type=number],input[type=datetime-local],textarea,select{
  width:100%;padding:.6rem .8rem;border:1.5px solid var(--border);border-radius:var(--rs);
  font-size:.95rem;font-family:inherit;color:var(--text);background:var(--surface);
  transition:border-color .12s,box-shadow .12s;
}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--p);box-shadow:0 0 0 3px var(--p-ring)}
.pollfields{display:grid;grid-template-columns:1fr 1fr;gap:.25rem 1rem}
.pollfields .full{grid-column:1 / -1}
.section-label{font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:1.75rem 0 .5rem}
/* Question card */
.qcard{border:1.5px solid var(--border);border-radius:var(--r);padding:1rem 1.1rem;margin-bottom:.9rem;background:var(--surface)}
.qhead{display:flex;align-items:center;gap:.6rem;margin-bottom:.5rem}
.qnum{font-weight:700;font-size:.85rem;color:var(--p);white-space:nowrap}
.qhead select.qtype{flex:1;max-width:230px}
.qhead .spacer{flex:1}
.ico-btn{
  width:1.9rem;height:1.9rem;flex-shrink:0;border:1.5px solid var(--border);border-radius:var(--rs);
  background:var(--surface);color:var(--muted);cursor:pointer;font-size:.95rem;line-height:1;
  display:inline-flex;align-items:center;justify-content:center;transition:border-color .1s,color .1s,background .1s;
}
.ico-btn:hover{border-color:var(--p);color:var(--p)}
.ico-btn:disabled{opacity:.35;cursor:default}
.ico-btn.del:hover{border-color:var(--danger);color:var(--danger)}
.opts{display:flex;flex-direction:column;gap:.4rem}
.opt-row{display:flex;gap:.4rem;align-items:center}
.add-opt{margin-top:.45rem;background:none;border:none;color:var(--p);font-size:.85rem;font-family:inherit;cursor:pointer;padding:.2rem 0}
.add-opt:hover{text-decoration:underline}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem}
.inline{display:flex;align-items:center;gap:.5rem;margin-top:.7rem;font-size:.9rem;cursor:pointer;user-select:none}
.inline input{width:16px;height:16px;accent-color:var(--p);cursor:pointer}
/* Branching */
.branch{margin-top:.9rem;padding-top:.8rem;border-top:1px dashed var(--border)}
.bmap{display:flex;flex-direction:column;gap:.4rem;margin-top:.5rem}
.brow{display:grid;grid-template-columns:1fr auto 1.4fr;align-items:center;gap:.5rem}
.bopt{font-size:.88rem;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mt{margin-top:.5rem}
/* Buttons */
.btn{padding:.6rem 1.4rem;border:none;border-radius:var(--rs);font-size:.95rem;font-family:inherit;font-weight:500;cursor:pointer;transition:background .12s,opacity .12s}
.btn-p{background:var(--p);color:#fff}
.btn-p:hover{background:var(--p-dk)}
.btn-p:disabled{opacity:.55;cursor:default}
.btn-s{background:var(--bg);color:var(--text);border:1.5px solid var(--border)}
.btn-s:hover{border-color:var(--p);color:var(--p)}
.btn-add{width:100%;border:1.5px dashed var(--border);background:var(--surface);color:var(--p);padding:.7rem;border-radius:var(--rs);font-size:.95rem;font-family:inherit;font-weight:500;cursor:pointer}
.btn-add:hover{border-color:var(--p);background:var(--p-lt)}
.footer{display:flex;justify-content:flex-end;margin-top:1.5rem}
.status{margin-top:1rem;font-size:.88rem;border-radius:var(--rs);padding:0}
.status:empty{display:none}
.err-box{padding:.7rem .9rem;background:color-mix(in srgb,var(--danger) 8%,#fff);border:1px solid color-mix(in srgb,var(--danger) 35%,#fff);color:#b91c1c}
.center{text-align:center;padding:2.5rem 1rem}
.center h2{font-size:1.5rem;font-weight:700;margin-bottom:.5rem}
.center .check{font-size:2.75rem;margin-bottom:.5rem}
.ok{color:#16a34a}
.linkbox{display:flex;gap:.5rem;margin:1.25rem 0;align-items:stretch}
.linkbox input{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85rem}
.muted{color:var(--muted)}
a{color:var(--p)}
</style>
</head>
<body>
<div class="layout">
  <aside class="side">
    <div class="side-title">Quick add</div>
    <p class="side-sub">Drop in a common field</p>
    <div id="presets" class="presets"></div>
  </aside>
  <div class="card">
  <div id="brand" class="brand-bar" style="display:none">
    <img id="brand-icon" src="" alt="" class="brand-icon-img">
    <span id="brand-name" class="brand-name"></span>
  </div>
  <div class="content" id="app">
    <h1 class="title">Create a poll</h1>
    <p class="sub">Build your questions, then publish to get a shareable link.</p>

    <div class="pollfields">
      <div class="full">
        <label class="fl" for="ptitle">Poll title <span class="req">*</span></label>
        <input type="text" id="ptitle" placeholder="e.g. Team satisfaction survey">
      </div>
      <div>
        <label class="fl" for="expires">Expires <span class="hint">(optional)</span></label>
        <input type="datetime-local" id="expires">
      </div>
      <div>
        <label class="fl" for="adminkey">Admin key <span class="hint">(if required)</span></label>
        <input type="password" id="adminkey" placeholder="X-Admin-Key" autocomplete="off">
      </div>
    </div>

    <div class="section-label">Questions</div>
    <div id="qlist"></div>
    <button type="button" class="btn-add" onclick="addQ()">+ Add question</button>

    <div id="status" class="status"></div>
    <div class="footer">
      <button type="button" id="createBtn" class="btn btn-p" onclick="createPoll()">Create poll</button>
    </div>
  </div>
  </div>
</div>
<script>
(function(){
'use strict';
var QC="__QC_SETTINGS__";

(function(){
  if(!QC.brand_name&&!QC.brand_icon)return;
  const bar=document.getElementById('brand');bar.style.display='';
  const ico=document.getElementById('brand-icon');
  if(QC.brand_icon)ico.src=QC.brand_icon;else ico.style.display='none';
  document.getElementById('brand-name').textContent=QC.brand_name||'';
})();

const TYPES=[
  ['short_answer','Short answer'],['long_answer','Long answer'],['number','Number'],
  ['email','Email'],['phone','Phone'],['url','URL'],['date','Date'],['time','Time'],
  ['datetime','Date & time'],['radio','Multiple choice (one)'],['checkbox','Checkboxes (many)'],
  ['dropdown','Dropdown'],['true_false','True / False'],['slider','Slider'],
  ['rating','Rating'],['likert','Likert scale']
];
const OPT_TYPES=['radio','checkbox','dropdown','true_false'];   // edit an options[] list
const OTHER_TYPES=['radio','checkbox'];                          // support include_other
const SINGLE=['radio','dropdown','true_false','likert'];        // can branch by answer
const BRANCH_OPT_TYPES=SINGLE.filter(t=>t!=='likert');          // options[] types that branch by answer
const PRESETS=[
  {label:'Full name',    q:{type:'short_answer', title:'Full name', required:true}},
  {label:'Email',        q:{type:'email',        title:'Email address', required:true}},
  {label:'Phone',        q:{type:'phone',        title:'Phone number'}},
  {label:'Shirt size',   q:{type:'dropdown',     title:'Shirt size', options:['XS','S','M','L','XL','XXL']}},
  {label:'Age',          q:{type:'number',       title:'Age'}},
  {label:'Yes / No',     q:{type:'true_false',   title:'Yes or no?'}},
  {label:'Rating (1–5)', q:{type:'rating',  title:'How would you rate it?', rating_max:5}},
  {label:'Satisfaction', q:{type:'likert',       title:'How satisfied are you?', likert_options:['Very dissatisfied','Dissatisfied','Neutral','Satisfied','Very satisfied']}},
  {label:'Comments',     q:{type:'long_answer',  title:'Additional comments'}},
];

let seq=0;
let qs=[];

function defaults(q,type){
  delete q.options;delete q.likert_options;delete q.include_other;
  delete q.slider_min;delete q.slider_max;delete q.slider_step;delete q.slider_labels;delete q.rating_max;
  if(type==='true_false')q.options=['Yes','No'];
  else if(OPT_TYPES.includes(type))q.options=['Option 1','Option 2'];
  if(type==='likert')q.likert_options=['Strongly Disagree','Disagree','Neutral','Agree','Strongly Agree'];
  if(type==='slider'){q.slider_min=0;q.slider_max=100;q.slider_step=1;q.slider_labels='';}
  if(type==='rating')q.rating_max=5;
}
function newQ(){
  seq++;
  const q={_id:'q'+seq,type:'short_answer',title:'',description:'',required:false,branchMode:'default',branchTarget:'',branchMap:{}};
  defaults(q,'short_answer');
  return q;
}
function qFromPreset(t){
  seq++;
  const q={_id:'q'+seq,type:t.type,title:t.title||'',description:t.description||'',required:!!t.required,branchMode:'default',branchTarget:'',branchMap:{}};
  defaults(q,t.type);
  if(t.options)q.options=t.options.slice();
  if(t.likert_options)q.likert_options=t.likert_options.slice();
  if(t.rating_max!=null)q.rating_max=t.rating_max;
  if(t.slider_min!=null){q.slider_min=t.slider_min;q.slider_max=t.slider_max;q.slider_step=t.slider_step;}
  if(t.include_other!=null)q.include_other=t.include_other;
  return q;
}

window.addQ=function(){qs.push(newQ());render();focusLast();};
window.addPreset=function(i){const p=PRESETS[i];if(!p)return;qs.push(qFromPreset(p.q));render();focusLast();};
window.delQ=function(i){
  const id=qs[i]._id;qs.splice(i,1);
  qs.forEach(q=>{
    if(q.branchTarget===id)q.branchTarget='';
    Object.keys(q.branchMap).forEach(k=>{if(q.branchMap[k]===id)q.branchMap[k]='';});
  });
  render();
};
window.moveQ=function(i,d){const j=i+d;if(j<0||j>=qs.length)return;const t=qs[i];qs[i]=qs[j];qs[j]=t;render();};
window.setType=function(i,t){const q=qs[i];q.type=t;defaults(q,t);q.branchMap={};if(!SINGLE.includes(t))q.branchMode='default';render();};
window.updField=function(i,f,v){qs[i][f]=v;};
window.updNum=function(i,f,v){qs[i][f]=v===''?null:Number(v);};
window.updOpt=function(i,f,oi,v){
  const q=qs[i];const old=(q[f][oi]||'').trim();
  q[f][oi]=v;
  if((f==='options'||f==='likert_options')&&old&&q.branchMap[old]!==undefined){
    const nv=v.trim();
    if(nv)q.branchMap[nv]=q.branchMap[old];
    if(nv!==old)delete q.branchMap[old];
  }
};
window.addOpt=function(i,f){qs[i][f].push('');render();};
window.delOpt=function(i,f,oi){qs[i][f].splice(oi,1);render();};
window.setBranchMode=function(i,m){qs[i].branchMode=m;render();};
window.setBranchTarget=function(i,v){qs[i].branchTarget=v;};
window.setBranchMap=function(i,oi,v){const k=branchOpts(qs[i])[oi];if(k!==undefined)qs[i].branchMap[k]=v;};

function branchOpts(q){
  if(BRANCH_OPT_TYPES.includes(q.type))return(q.options||[]).map(o=>o.trim()).filter(Boolean);
  if(q.type==='likert')return(q.likert_options||[]).map(o=>o.trim()).filter(Boolean);
  return [];
}

function targetOpts(i,sel){
  let h=`<option value=""${sel?'':' selected'}>Continue to next question</option>`;
  qs.forEach((q,j)=>{
    if(j===i)return;
    const label='Question '+(j+1)+(q.title.trim()?': '+q.title.trim().slice(0,40):'');
    h+=`<option value="${x(q._id)}"${sel===q._id?' selected':''}>${x(label)}</option>`;
  });
  return h;
}

function optEditor(i,f){
  let h='<div class="opts">';
  // In "branch based on the answer" mode, refresh the branch-map labels on blur
  // so they don't keep showing the pre-edit option text.
  const rr=qs[i].branchMode==='map'?' onchange="render()"':'';
  qs[i][f].forEach((o,oi)=>{
    h+=`<div class="opt-row"><input type="text" value="${x(o)}" placeholder="Option ${oi+1}" oninput="updOpt(${i},'${f}',${oi},this.value)"${rr}><button type="button" class="ico-btn del" title="Remove option" onclick="delOpt(${i},'${f}',${oi})">✕</button></div>`;
  });
  h+=`</div><button type="button" class="add-opt" onclick="addOpt(${i},'${f}')">+ Add option</button>`;
  return h;
}

function qcard(q,i){
  let h='<div class="qcard">';
  // header
  h+='<div class="qhead">';
  h+=`<span class="qnum">Q${i+1}</span>`;
  h+=`<select class="qtype" onchange="setType(${i},this.value)">`+TYPES.map(([v,l])=>`<option value="${v}"${q.type===v?' selected':''}>${x(l)}</option>`).join('')+'</select>';
  h+='<span class="spacer"></span>';
  h+=`<button type="button" class="ico-btn" title="Move up" onclick="moveQ(${i},-1)"${i===0?' disabled':''}>↑</button>`;
  h+=`<button type="button" class="ico-btn" title="Move down" onclick="moveQ(${i},1)"${i===qs.length-1?' disabled':''}>↓</button>`;
  h+=`<button type="button" class="ico-btn del" title="Delete question" onclick="delQ(${i})">✕</button>`;
  h+='</div>';
  // title + description
  h+=`<label class="fl">Question text <span class="req">*</span></label>`;
  h+=`<input type="text" value="${x(q.title)}" placeholder="What do you want to ask?" oninput="updField(${i},'title',this.value)">`;
  h+=`<label class="fl">Description <span class="hint">(optional)</span></label>`;
  h+=`<input type="text" value="${x(q.description)}" placeholder="Helper text shown under the question" oninput="updField(${i},'description',this.value)">`;
  // type-specific
  if(OPT_TYPES.includes(q.type)){
    h+='<label class="fl">Options</label>'+optEditor(i,'options');
  }
  if(q.type==='likert'){
    h+='<label class="fl">Scale options</label>'+optEditor(i,'likert_options');
  }
  if(q.type==='slider'){
    h+='<div class="grid3">';
    h+=`<div><label class="fl">Min</label><input type="number" value="${q.slider_min??''}" oninput="updNum(${i},'slider_min',this.value)"></div>`;
    h+=`<div><label class="fl">Max</label><input type="number" value="${q.slider_max??''}" oninput="updNum(${i},'slider_max',this.value)"></div>`;
    h+=`<div><label class="fl">Step</label><input type="number" value="${q.slider_step??''}" oninput="updNum(${i},'slider_step',this.value)"></div>`;
    h+='</div>';
    h+='<label class="fl">Labels <span class="hint">(optional, comma-separated)</span></label>';
    h+=`<input type="text" value="${x(q.slider_labels||'')}" placeholder="e.g. Low, Medium, High" oninput="updField(${i},'slider_labels',this.value)">`;
  }
  if(q.type==='rating'){
    h+=`<label class="fl">Maximum rating</label><input type="number" min="1" value="${q.rating_max??''}" oninput="updNum(${i},'rating_max',this.value)">`;
  }
  if(OTHER_TYPES.includes(q.type)){
    h+=`<label class="inline"><input type="checkbox"${q.include_other?' checked':''} onchange="updField(${i},'include_other',this.checked)"> Add a free-text "Other…" option</label>`;
  }
  h+=`<label class="inline"><input type="checkbox"${q.required?' checked':''} onchange="updField(${i},'required',this.checked)"> Required</label>`;
  // branching
  h+='<div class="branch"><label class="fl">After this question</label>';
  h+=`<select onchange="setBranchMode(${i},this.value)">`;
  h+=`<option value="default"${q.branchMode==='default'?' selected':''}>Continue to the next question</option>`;
  h+=`<option value="jump"${q.branchMode==='jump'?' selected':''}>Always jump to a question…</option>`;
  if(SINGLE.includes(q.type))h+=`<option value="map"${q.branchMode==='map'?' selected':''}>Branch based on the answer…</option>`;
  h+='</select>';
  if(q.branchMode==='jump'){
    h+=`<select class="mt" onchange="setBranchTarget(${i},this.value)">`+targetOpts(i,q.branchTarget)+'</select>';
  }
  if(q.branchMode==='map'){
    const opts=branchOpts(q);
    if(opts.length){
      h+='<div class="bmap">';
      opts.forEach((o,oi)=>{
        h+=`<div class="brow"><span class="bopt" title="${x(o)}">${x(o)}</span><span class="muted">→</span><select onchange="setBranchMap(${i},${oi},this.value)">`+targetOpts(i,q.branchMap[o]||'')+'</select></div>';
      });
      h+='</div>';
    }else{
      h+='<p class="hint mt">Add options above to branch on them.</p>';
    }
  }
  h+='</div>';
  h+='</div>';
  return h;
}

function render(){
  document.getElementById('qlist').innerHTML=qs.map((q,i)=>qcard(q,i)).join('');
}
function focusLast(){
  const cards=document.querySelectorAll('#qlist .qcard');
  const last=cards[cards.length-1];
  if(last){const inp=last.querySelector('input[type=text]');if(inp)inp.focus();}
}

function buildQuestions(){
  return qs.map(q=>{
    const o={id:q._id,type:q.type,title:q.title.trim()};
    if(q.description.trim())o.description=q.description.trim();
    if(q.required)o.required=true;
    if(OPT_TYPES.includes(q.type))o.options=q.options.map(s=>s.trim()).filter(Boolean);
    if(q.type==='likert')o.likert_options=q.likert_options.map(s=>s.trim()).filter(Boolean);
    if(OTHER_TYPES.includes(q.type)&&q.include_other)o.include_other=true;
    if(q.type==='slider'){
      o.slider_min=Number(q.slider_min)||0;
      o.slider_max=Number(q.slider_max)||0;
      o.slider_step=Number(q.slider_step)||1;
      const labels=(q.slider_labels||'').split(',').map(s=>s.trim()).filter(Boolean);
      if(labels.length){const lm={};labels.forEach((l,li)=>{lm[li]=l;});o.slider_labels=lm;}
    }
    if(q.type==='rating')o.rating_max=Number(q.rating_max)||5;
    if(q.branchMode==='jump'&&q.branchTarget){o.next=q.branchTarget;}
    else if(q.branchMode==='map'){
      const valid=new Set(branchOpts(q));
      const m={};
      Object.entries(q.branchMap).forEach(([k,t])=>{const tk=k.trim();if(t&&valid.has(tk))m[tk]=t;});
      if(Object.keys(m).length)o.next=m;
    }
    return o;
  });
}

function validateAll(){
  const errs=[];
  if(!document.getElementById('ptitle').value.trim())errs.push('Poll title is required.');
  if(!qs.length)errs.push('Add at least one question.');
  const ids=new Set(qs.map(q=>q._id));
  qs.forEach((q,i)=>{
    const L='Question '+(i+1);
    if(!q.title.trim())errs.push(L+': question text is required.');
    if(OPT_TYPES.includes(q.type)&&q.options.filter(o=>o.trim()).length<1)errs.push(L+': add at least one option.');
    if(q.type==='likert'&&q.likert_options.filter(o=>o.trim()).length<1)errs.push(L+': add at least one scale option.');
    if(q.type==='slider'){
      if([q.slider_min,q.slider_max,q.slider_step].some(v=>v===''||v===null||v===undefined||isNaN(Number(v))))errs.push(L+': slider needs a numeric min, max, and step.');
      else{
        if(!(Number(q.slider_max)>Number(q.slider_min)))errs.push(L+': slider max must be greater than min.');
        if(!(Number(q.slider_step)>0))errs.push(L+': slider step must be greater than 0.');
      }
    }
    if(q.type==='rating'&&!(Number(q.rating_max)>=1))errs.push(L+': maximum rating must be at least 1.');
    if(q.branchMode==='jump'&&q.branchTarget&&!ids.has(q.branchTarget))errs.push(L+': branch target no longer exists.');
    if(q.branchMode==='map')Object.entries(q.branchMap).forEach(([k,t])=>{if(t&&branchOpts(q).includes(k)&&!ids.has(t))errs.push(L+': a branch target no longer exists.');});
  });
  return errs;
}

function setStatus(msg){
  const box=document.getElementById('status');
  if(!msg){box.className='status';box.innerHTML='';return;}
  box.className='status err-box';box.innerHTML=msg;
}

window.createPoll=async function(){
  const errs=validateAll();
  if(errs.length){setStatus(errs.map(e=>'• '+x(e)).join('<br>'));return;}
  setStatus('');
  const btn=document.getElementById('createBtn');btn.disabled=true;btn.textContent='Creating…';
  const fd=new FormData();
  fd.append('title',document.getElementById('ptitle').value.trim());
  const exp=document.getElementById('expires').value;
  if(exp)fd.append('expires_at',exp);
  const json=JSON.stringify({questions:buildQuestions()},null,2);
  fd.append('questions_file',new Blob([json],{type:'application/json'}),'questions.json');
  const headers={};
  const key=document.getElementById('adminkey').value;
  if(key)headers['X-Admin-Key']=key;
  function fail(m){btn.disabled=false;btn.textContent='Create poll';setStatus(x(m));}
  try{
    const r=await fetch('/api/polls',{method:'POST',headers,body:fd});
    if(r.status===403)return fail('Admin key required or incorrect.');
    if(!r.ok){let d={};try{d=await r.json();}catch{}return fail('Could not create poll'+(d.detail?': '+d.detail:'.'));}
    const d=await r.json();
    showSuccess(d);
  }catch{fail('Network error — please try again.');}
};

function showSuccess(d){
  const url=d.poll_url||(location.origin+'/p/'+d.id);
  document.getElementById('app').innerHTML=
    '<div class="center"><div class="check ok">✓</div><h2 class="ok">Poll created</h2>'
    +'<p class="muted">Share this link to collect responses:</p>'
    +'<div class="linkbox"><input type="text" id="su" readonly value="'+x(url)+'">'
    +'<button class="btn btn-s" onclick="copyUrl()">Copy</button></div>'
    +'<p><a href="'+x(url)+'">Open the poll →</a></p>'
    +'<p style="margin-top:1.25rem"><button class="btn btn-p" onclick="location.reload()">Create another</button></p></div>';
}
window.copyUrl=function(){
  const i=document.getElementById('su');i.select();
  try{navigator.clipboard.writeText(i.value);}catch{document.execCommand('copy');}
};

function x(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

document.getElementById('presets').innerHTML=PRESETS.map((p,i)=>`<button type="button" class="preset" onclick="addPreset(${i})">+ ${x(p.label)}</button>`).join('');
addQ();
})();
</script>
</body>
</html>"""


def render_builder_html(settings: dict) -> str:
    """Render the visual poll-builder page, themed from ``settings``."""
    return inject_theme(_TEMPLATE, settings)
