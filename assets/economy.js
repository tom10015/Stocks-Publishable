'use strict';
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const valid=x=>typeof x==='number'&&Number.isFinite(x);
const formats={cpi:v=>v.toFixed(2),unemployment:v=>v.toFixed(1)+'%',debt:v=>'$'+(v/1e12).toFixed(2)+' trillion'};
const fmt=(id,v)=>valid(v)?(formats[id]||((x)=>x.toLocaleString('en-US')))(v):'Not available';
let series=[],active='';
function graph(items,id){
 const a=items.filter(x=>valid(x.value)&&x.date).slice(-24);if(a.length<2)return '<p class="muted">Not enough dated observations to draw a trend.</p>';
 const w=800,h=245,p=40,vals=a.map(x=>x.value),min=Math.min(...vals),max=Math.max(...vals),span=max-min||1;
 const xy=a.map((x,i)=>[p+(w-2*p)*i/(a.length-1),p+(h-2*p)*(max-x.value)/span]);
 return '<svg viewBox="0 0 800 245" role="img" aria-label="'+esc(id)+' historical observations">'+
 '<line x1="40" y1="205" x2="760" y2="205" stroke="#30455e" stroke-width="1"/>'+
 '<polyline fill="none" stroke="#58d8aa" stroke-width="3" stroke-linejoin="round" points="'+xy.map(a=>a.join(',')).join(' ')+'"/>'+
 xy.map((v,i)=>'<circle cx="'+v[0]+'" cy="'+v[1]+'" r="4" fill="#58d8aa"><title>'+esc(a[i].date)+' · '+esc(fmt(id,a[i].value))+'</title></circle>').join('')+
 '<text x="40" y="238" fill="#a2b5c9" font-size="12">'+esc(a[0].date)+'</text>'+
 '<text x="760" y="238" text-anchor="end" fill="#a2b5c9" font-size="12">'+esc(a.at(-1).date)+'</text></svg>';
}
function render(){
 const all=document.getElementById('ecoGrid');all.innerHTML=series.length?series.map(s=>{const last=s.observations?.at(-1),isSelected=s.id===active;return '<button type="button" class="econ-card'+(isSelected?' active':'')+'" data-series="'+esc(s.id)+'" aria-pressed="'+String(isSelected)+'"><small>'+esc(s.name)+'</small><strong>'+esc(fmt(s.id,last?.value))+'</strong><span>As of '+esc(last?.date||'not yet collected')+'</span></button>';}).join(''):'<div class="panel"><h2>No verified economic observations loaded</h2><p class="muted">The official-source collector must complete successfully before this dashboard can display historical values.</p><a href="https://www.bls.gov/developers/" target="_blank" rel="noopener noreferrer">BLS Public API ↗</a></div>';
 const s=series.find(x=>x.id===active);if(!s){$('ecoDetail').innerHTML='<h2>Historical observations</h2><p class="muted">No official series has been collected yet.</p>';return}
 const a=s.observations||[],last=a.at(-1),prev=a.at(-2),delta=last&&prev&&prev.value!==0?100*(last.value/prev.value-1):null;
 const row=[...a].reverse().slice(0,18).map(x=>'<tr><td>'+esc(x.date)+'</td><td>'+esc(fmt(s.id,x.value))+'</td></tr>').join('');
 $('ecoDetail').innerHTML='<div class="research-title"><div><div class="kicker">OFFICIAL GOVERNMENT DATA</div><h2>'+esc(s.name)+'</h2><p class="muted">'+esc(s.description||'')+'</p></div><div class="score-big">'+esc(fmt(s.id,last?.value))+'<small>'+esc(last?.date||'—')+'</small></div></div>'+
 '<div class="chart-area">'+graph(a,s.id)+'</div><div class="table-scroll"><table class="research-table"><thead><tr><th>Observation period</th><th>Reported value</th></tr></thead><tbody>'+row+'</tbody></table></div>'+
 '<p class="research-note">Observation periods and release delays vary. Values may be revised. '+esc(s.note||'')+'</p>'+
 '<a target="_blank" rel="noopener noreferrer" href="'+esc(s.source_url)+'">Official '+esc(s.agency||'agency')+' source ↗</a>';
}
async function init(){try{const r=await fetch('./data/economy.json',{cache:'no-cache'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();series=(d.series||[]).filter(x=>/^(cpi|unemployment|debt)$/.test(x.id)&&Array.isArray(x.observations)&&x.observations.length).map(x=>({...x,observations:x.observations.filter(p=>valid(p.value)&&typeof p.date==='string').sort((a,b)=>a.date.localeCompare(b.date))}));active=series[0]?.id||'';$('ecoStatus').textContent='Government snapshot '+(d.updated_at||'not yet collected')+' · '+series.length+' indicator series';render();}catch(e){$('ecoStatus').textContent='Economic dataset unavailable: '+e.message;render()}}
$('ecoGrid').addEventListener('click',e=>{const b=e.target.closest('[data-series]');if(!b)return;active=b.dataset.series;render();});
init();