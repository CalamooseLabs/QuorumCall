import json

from .settings import DEFAULTS

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Poll</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  /*__QC_THEME__*/
  --p-dk:color-mix(in srgb,var(--p) 82%,#000);
  --p-lt:color-mix(in srgb,var(--p) 11%,#fff);
  --p-ring:color-mix(in srgb,var(--p) 28%,transparent);
  --text:#111827;
  --muted:#6b7280;
  --border:#e5e7eb;
  --bg:#f3f4f6;
  --surface:#fff;
  --r:12px;
  --rs:8px;
}
body{
  font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:var(--bg);
  min-height:100vh;
  display:flex;
  flex-direction:column;
  align-items:center;
  padding:2.5rem 1rem 5rem;
  color:var(--text);
  line-height:1.5;
}
.card{
  background:var(--surface);
  border-radius:var(--r);
  max-width:680px;
  width:100%;
  box-shadow:0 1px 3px rgba(0,0,0,.07),0 6px 24px rgba(0,0,0,.07);
  overflow:hidden;
}
/* Brand bar */
.brand-bar{
  display:flex;
  align-items:center;
  gap:.65rem;
  padding:.85rem 1.75rem;
  background:var(--bg);
  border-bottom:1px solid var(--border);
}
.brand-icon-img{height:26px;width:auto;object-fit:contain;flex-shrink:0}
.brand-name{font-size:.9rem;font-weight:600;color:var(--text)}
/* Content */
.content{padding:1.75rem 2rem 2rem}
/* Poll header */
.poll-title{font-size:1.3rem;font-weight:700;color:var(--text);line-height:1.3;margin-bottom:.75rem}
/* Progress */
.prog-wrap{margin-bottom:1.6rem}
.prog-track{height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-bottom:.35rem}
.prog-fill{height:100%;background:var(--p);border-radius:2px;transition:width .3s ease}
.prog-label{font-size:.75rem;color:var(--muted)}
/* Question */
.q-block{margin-bottom:.25rem}
.q-title{font-size:1.05rem;font-weight:600;color:var(--text);line-height:1.4;margin-bottom:.2rem}
.q-desc{font-size:.875rem;color:var(--muted);margin-bottom:.85rem;line-height:1.6}
.req{color:#ef4444;margin-left:.1rem}
/* Text inputs */
input[type=text],input[type=email],input[type=tel],input[type=url],
input[type=number],input[type=date],input[type=time],input[type=datetime-local],
textarea,select{
  width:100%;margin-top:.5rem;
  padding:.65rem .85rem;
  border:1.5px solid var(--border);
  border-radius:var(--rs);
  font-size:1rem;font-family:inherit;color:var(--text);background:var(--surface);
  transition:border-color .12s,box-shadow .12s;
}
textarea{resize:vertical;min-height:120px}
input:focus,textarea:focus,select:focus{
  outline:none;border-color:var(--p);box-shadow:0 0 0 3px var(--p-ring);
}
/* Choice list */
.choice-list{display:flex;flex-direction:column;gap:.4rem;margin-top:.5rem}
.choice{
  display:flex;align-items:center;gap:.75rem;
  padding:.7rem 1rem;
  border:1.5px solid var(--border);border-radius:var(--rs);
  cursor:pointer;user-select:none;
  transition:border-color .1s,background .1s;
}
.choice:hover{border-color:var(--p);background:var(--p-lt)}
.choice:has(input:checked){border-color:var(--p);background:var(--p-lt)}
.choice input{width:16px;height:16px;accent-color:var(--p);flex-shrink:0;cursor:pointer;margin:0}
/* Other */
.ow{display:none;margin-top:.4rem}
.ow.show{display:block}
/* Slider */
.slider-wrap{padding:.5rem 0 .2rem;margin-top:.4rem}
input[type=range]{width:100%;cursor:pointer;accent-color:var(--p)}
.slider-labels{display:flex;justify-content:space-between;font-size:.75rem;color:var(--muted);margin-top:.2rem}
.slider-val{text-align:center;font-weight:700;font-size:1.35rem;color:var(--p);margin:.35rem 0 .1rem}
/* Rating */
.rating-list{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.5rem}
.rating-btn{
  width:2.6rem;height:2.6rem;
  border:1.5px solid var(--border);border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:.9rem;font-family:inherit;font-weight:500;
  background:var(--surface);color:var(--text);
  transition:border-color .1s,background .1s,color .1s;
}
.rating-btn:hover{border-color:var(--p);color:var(--p)}
.rating-btn.on{background:var(--p);border-color:var(--p);color:#fff}
/* Likert */
.likert-list{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.5rem}
.likert-btn{
  padding:.45rem .9rem;
  border:1.5px solid var(--border);border-radius:2rem;
  cursor:pointer;font-size:.875rem;font-family:inherit;white-space:nowrap;
  background:var(--surface);color:var(--text);
  transition:border-color .1s,background .1s,color .1s;
}
.likert-btn:hover{border-color:var(--p);color:var(--p)}
.likert-btn.on{background:var(--p);border-color:var(--p);color:#fff}
/* Error */
.err{min-height:1.4em;font-size:.85rem;color:#ef4444;margin-top:.6rem}
/* Nav */
.nav{display:flex;justify-content:space-between;align-items:center;margin-top:1.75rem;gap:.75rem}
.btn{
  padding:.6rem 1.5rem;border:none;border-radius:var(--rs);
  font-size:1rem;font-family:inherit;font-weight:500;cursor:pointer;
  transition:background .12s,opacity .12s;
}
.btn-p{background:var(--p);color:#fff}
.btn-p:hover{background:var(--p-dk)}
.btn-p:disabled{opacity:.55;cursor:default}
.btn-s{background:var(--bg);color:var(--text);border:1.5px solid var(--border)}
.btn-s:hover{border-color:var(--p);color:var(--p)}
/* Review */
.rv-list{margin-top:.75rem}
.rv-item{padding:.75rem 0;border-bottom:1px solid var(--border)}
.rv-item:last-child{border-bottom:none}
.rv-q{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:.2rem}
.rv-a{color:var(--text);font-size:.95rem;word-break:break-word}
/* States */
.center{text-align:center;padding:3rem 1.5rem}
.center h2{font-size:1.5rem;font-weight:700;margin-bottom:.5rem}
.center p{color:var(--muted);line-height:1.6}
.ok{color:#16a34a}
.check{font-size:2.75rem;margin-bottom:.65rem}
</style>
</head>
<body>
<div class="card">
  <div id="brand" class="brand-bar" style="display:none">
    <img id="brand-icon" src="" alt="" class="brand-icon-img">
    <span id="brand-name"></span>
  </div>
  <div class="content" id="app"><p style="color:var(--muted)">Loading…</p></div>
</div>
<script>
(function(){
'use strict';
var QC="__QC_SETTINGS__";
const pollId=location.pathname.split('/').filter(Boolean).pop();
let poll,qMap={},qOrder=[],hist=[],curId,ans={};

(function(){
  if(!QC.brand_name&&!QC.brand_icon)return;
  const bar=document.getElementById('brand');
  bar.style.display='';
  const ico=document.getElementById('brand-icon');
  if(QC.brand_icon)ico.src=QC.brand_icon;
  else ico.style.display='none';
  document.getElementById('brand-name').textContent=QC.brand_name||'';
})();

async function init(){
  let data;
  try{
    const r=await fetch('/api/polls/'+pollId);
    if(!r.ok)throw 0;
    data=await r.json();
  }catch{
    return set('<div class="center"><h2>Poll not found</h2><p>This poll does not exist or the link is invalid.</p></div>');
  }
  if(data.is_expired)return set('<div class="center"><h2>This poll is closed</h2><p>Thank you for your interest.</p></div>');
  poll=data;
  document.title=poll.title+' — QuorumCall';
  poll.questions.forEach(q=>{qMap[q.id]=q;qOrder.push(q.id);});
  if(!qOrder.length)return set('<div class="center"><h2>No questions found</h2></div>');
  curId=qOrder[0];
  showQ();
}

function set(h){document.getElementById('app').innerHTML=h;}

function nextId(q){
  const a=ans[q.id];
  if(q.next==null||q.next===undefined){
    const i=qOrder.indexOf(q.id);return i<qOrder.length-1?qOrder[i+1]:null;
  }
  if(typeof q.next==='string')return q.next||null;
  if(typeof q.next==='object'){
    const k=Array.isArray(a)?(a[0]??''):String(a??'');
    const mapped=q.next[k];
    if(mapped!==undefined)return mapped||null;
    const i=qOrder.indexOf(q.id);return i<qOrder.length-1?qOrder[i+1]:null;
  }
  return null;
}

function showQ(){
  const q=qMap[curId];
  const idx=hist.length,total=qOrder.length;
  const pct=Math.round(idx/total*100);
  let h='';
  h+=`<h1 class="poll-title">${x(poll.title)}</h1>`;
  h+=`<div class="prog-wrap"><div class="prog-track"><div class="prog-fill" style="width:${pct}%"></div></div><div class="prog-label">Question ${idx+1} of ${total}</div></div>`;
  h+=`<div class="q-block"><div class="q-title">${x(q.title)}${q.required?'<span class="req">*</span>':''}</div>`;
  if(q.description)h+=`<div class="q-desc">${x(q.description)}</div>`;
  h+=buildInp(q)+'</div>';
  h+='<div class="err" id="err"></div>';
  h+='<div class="nav">';
  h+=hist.length?'<button class="btn btn-s" onclick="goBack()">← Back</button>':'<span></span>';
  h+='<button class="btn btn-p" onclick="goNext()">Next →</button>';
  h+='</div>';
  set(h);
  restore(q);
}

function buildInp(q){
  switch(q.type){
    case'short_answer':return'<input type="text" id="qi" placeholder="Your answer">';
    case'long_answer':return'<textarea id="qi" placeholder="Your answer"></textarea>';
    case'number':return'<input type="number" id="qi">';
    case'email':return'<input type="email" id="qi" placeholder="email@example.com">';
    case'phone':return'<input type="tel" id="qi">';
    case'url':return'<input type="url" id="qi" placeholder="https://">';
    case'date':return'<input type="date" id="qi">';
    case'time':return'<input type="time" id="qi">';
    case'datetime':return'<input type="datetime-local" id="qi">';
    case'true_false':{
      const opts=q.options||['Yes','No'];
      let h='<div class="choice-list">';
      opts.forEach(o=>{h+=`<label class="choice"><input type="radio" name="qi" value="${x(o)}"><span>${x(o)}</span></label>`;});
      return h+'</div>';
    }
    case'radio':{
      let h='<div class="choice-list">';
      (q.options||[]).forEach(o=>{h+=`<label class="choice"><input type="radio" name="qi" value="${x(o)}"><span>${x(o)}</span></label>`;});
      if(q.include_other){
        h+=`<label class="choice"><input type="radio" name="qi" value="__other__" onchange="tog(this)"><span>Other…</span></label>`;
        h+=`<div class="ow" id="ow"><input type="text" id="oi" placeholder="Please specify"></div>`;
      }
      return h+'</div>';
    }
    case'checkbox':{
      let h='<div class="choice-list">';
      (q.options||[]).forEach(o=>{h+=`<label class="choice"><input type="checkbox" class="cbi" value="${x(o)}"><span>${x(o)}</span></label>`;});
      if(q.include_other){
        h+=`<label class="choice"><input type="checkbox" class="cbi" value="__other__" onchange="tog(this)"><span>Other…</span></label>`;
        h+=`<div class="ow" id="ow"><input type="text" id="oi" placeholder="Please specify"></div>`;
      }
      return h+'</div>';
    }
    case'dropdown':
      return'<select id="qi"><option value="">— Select an option —</option>'
        +(q.options||[]).map(o=>`<option value="${x(o)}">${x(o)}</option>`).join('')+'</select>';
    case'slider':{
      const mn=q.slider_min??0,mx=q.slider_max??100,st=q.slider_step??1;
      let lbls='';
      if(q.slider_labels){
        const ents=Object.entries(q.slider_labels);
        lbls=`<div class="slider-labels">${ents.map(([,l])=>`<span>${x(l)}</span>`).join('')}</div>`;
      }
      return`<div class="slider-wrap"><input type="range" id="qi" min="${mn}" max="${mx}" step="${st}" value="${mn}" oninput="document.getElementById('sv').textContent=this.value"><div class="slider-val" id="sv">${mn}</div>${lbls}</div>`;
    }
    case'rating':{
      const mx=q.rating_max||5;
      let h='<div class="rating-list">';
      for(let i=1;i<=mx;i++)h+=`<button type="button" class="rating-btn" data-v="${i}" onclick="selR(${i})">${i}</button>`;
      return h+'</div><input type="hidden" id="qi">';
    }
    case'likert':{
      const opts=q.likert_options||['Strongly Disagree','Disagree','Neutral','Agree','Strongly Agree'];
      return'<div class="likert-list">'+opts.map(o=>`<button type="button" class="likert-btn" data-v="${x(o)}" onclick="selL(this)">${x(o)}</button>`).join('')+'</div><input type="hidden" id="qi">';
    }
    default:return'<input type="text" id="qi">';
  }
}

window.tog=function(el){
  const ow=document.getElementById('ow');
  if(!ow)return;
  if(el.checked){ow.classList.add('show');document.getElementById('oi')?.focus();}
  else{ow.classList.remove('show');const oi=document.getElementById('oi');if(oi)oi.value='';}
};

window.selR=function(v){
  document.querySelectorAll('.rating-btn').forEach(b=>b.classList.toggle('on',+b.dataset.v<=v));
  document.getElementById('qi').value=v;
};

window.selL=function(btn){
  const v=btn.dataset.v;
  btn.closest('.likert-list').querySelectorAll('.likert-btn').forEach(b=>b.classList.toggle('on',b.dataset.v===v));
  document.getElementById('qi').value=v;
};

function getV(q){
  switch(q.type){
    case'checkbox':{
      const vals=Array.from(document.querySelectorAll('.cbi:checked')).map(c=>c.value);
      const i=vals.indexOf('__other__');
      if(i>=0){const oi=document.getElementById('oi');vals[i]='Other: '+(oi?.value||'');}
      return vals;
    }
    case'radio':case'true_false':{
      const s=document.querySelector('input[name="qi"]:checked');
      if(!s)return null;
      if(s.value==='__other__')return'Other: '+(document.getElementById('oi')?.value||'');
      return s.value;
    }
    case'slider':case'number':{const v=document.getElementById('qi')?.value;return v!==''&&v!=null?+v:null;}
    case'rating':{const v=document.getElementById('qi')?.value;return v?+v:null;}
    default:{const v=document.getElementById('qi')?.value;return(v&&v.trim())||null;}
  }
}

function restore(q){
  const v=ans[q.id];
  if(v===undefined)return;
  switch(q.type){
    case'radio':case'true_false':{
      let rv=v;
      if(typeof v==='string'&&v.startsWith('Other: ')){
        rv='__other__';
        const oi=document.getElementById('oi');
        if(oi){oi.value=v.slice(7);document.getElementById('ow')?.classList.add('show');}
      }
      const el=document.querySelector(`input[name="qi"][value="${CSS.escape(String(rv))}"]`);
      if(el)el.checked=true;
      break;
    }
    case'checkbox':
      (Array.isArray(v)?v:[v]).forEach(item=>{
        let rv=item;
        if(typeof item==='string'&&item.startsWith('Other: ')){
          rv='__other__';
          const oi=document.getElementById('oi');
          if(oi){oi.value=item.slice(7);document.getElementById('ow')?.classList.add('show');}
        }
        const el=document.querySelector(`.cbi[value="${CSS.escape(String(rv))}"]`);
        if(el)el.checked=true;
      });
      break;
    case'slider':{
      const sl=document.getElementById('qi');
      if(sl&&v!=null){sl.value=v;const sv=document.getElementById('sv');if(sv)sv.textContent=v;}
      break;
    }
    case'rating':if(v!=null)selR(v);break;
    case'likert':{
      if(v!=null){
        const btn=document.querySelector(`.likert-btn[data-v="${CSS.escape(String(v))}"]`);
        if(btn)selL(btn);
      }
      break;
    }
    default:{const el=document.getElementById('qi');if(el&&v!=null)el.value=v;}
  }
}

function validate(q,v){
  if(!q.required)return null;
  if(v===null||v===''||v===undefined)return'This field is required.';
  if(Array.isArray(v)&&!v.length)return'Please select at least one option.';
  return null;
}

window.goNext=function(){
  const q=qMap[curId];
  const v=getV(q);
  const e=validate(q,v);
  if(e){document.getElementById('err').textContent=e;return;}
  ans[q.id]=v;
  const n=nextId(q);
  hist.push(curId);
  if(!n){showReview();return;}
  curId=n;
  showQ();
};

window.goBack=function(){
  if(!hist.length)return;
  curId=hist.pop();
  showQ();
};

function showReview(){
  let h=`<h1 class="poll-title">${x(poll.title)}</h1><p style="color:var(--muted);margin-bottom:1.25rem">Review your answers before submitting.</p>`;
  h+='<div class="rv-list">';
  Object.entries(ans).forEach(([qid,v])=>{
    const q=qMap[qid];if(!q)return;
    const d=Array.isArray(v)?v.filter(Boolean).join(', '):(v==null?'—':String(v));
    h+=`<div class="rv-item"><div class="rv-q">${x(q.title)}</div><div class="rv-a">${d?x(d):'<em style="color:var(--muted)">No answer</em>'}</div></div>`;
  });
  h+='</div><div class="err" id="err"></div>';
  h+='<div class="nav"><button class="btn btn-s" onclick="goBack()">← Back</button><button class="btn btn-p" onclick="doSubmit()">Submit</button></div>';
  set(h);
}

window.doSubmit=async function(){
  const btn=document.querySelector('.btn-p');
  if(btn)btn.disabled=true;
  const payload={answers:Object.entries(ans).map(([question_id,value])=>({question_id,value}))};
  try{
    const r=await fetch('/api/polls/'+pollId+'/responses',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)
    });
    if(!r.ok)throw 0;
    set('<div class="center"><div class="check ok">✓</div><h2 class="ok">Thank you!</h2><p>Your response has been recorded.</p></div>');
  }catch{
    if(btn)btn.disabled=false;
    document.getElementById('err').textContent='Submission failed. Please try again.';
  }
};

function x(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

init();
})();
</script>
</body>
</html>"""


def render_html(settings: dict) -> str:
    s = {**DEFAULTS, **settings}
    css_var = f"--p:{s['primary_color']};"
    js_settings = json.dumps({
        "brand_name": s["brand_name"],
        "brand_icon": s["brand_icon"],
    })
    return (
        _TEMPLATE
        .replace("/*__QC_THEME__*/", css_var)
        .replace('"__QC_SETTINGS__"', js_settings)
    )
