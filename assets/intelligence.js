'use strict';
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=x=>typeof x==='number'&&Number.isFinite(x)?x:null;
const num=x=>n(x)===null?'Not reported':x.toLocaleString('en-US',{maximumFractionDigits:2});
const usd=x=>n(x)===null?'Not reported':(x<0?'−':'')+'$'+Math.abs(x).toLocaleString('en-US',{maximumFractionDigits:2});
const short=x=>n(x)===null?'Not reported':(x<0?'−':'')+'$'+(Math.abs(x)>=1e12?(Math.abs(x)/1e12).toFixed(2)+'T':Math.abs(x)>=1e9?(Math.abs(x)/1e9).toFixed(2)+'B':Math.abs(x)>=1e6?(Math.abs(x)/1e6).toFixed(1)+'M':num(Math.abs(x)));
const pct=x=>n(x)===null?'Not available':x.toFixed(1)+'%';
const secLink=x=>typeof x==='string'&&/^https:\/\/(?:www\.)?sec\.gov\//.test(x)?x:null;
const metric=(c,k)=>{const x=c?.metrics?.[k];return n(x?.value)!==null?x:null};
const same=(a,b)=>Boolean(a&&b&&a.period_start===b.period_start&&a.period_end===b.period_end);
const rawData={companies:[],insiders:{},institutions:{},filings:{}};let ticker='',tab='health',compareTo='';
function co(){return rawData.companies.find(x=>x.ticker===ticker)}
function missing(what,link){return '<div class="research-empty"><strong>No verified '+esc(what)+' data available for this company.</strong><p>The source has not published a matching structured record, or our collector has not successfully imported one. We do not substitute estimated or invented data.</p>'+(link?'<a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">Review official source ↗</a>':'')+'</div>'}
function fact(label,value,period,more){return '<div class="research-fact"><small>'+esc(label)+'</small><strong>'+esc(value)+'</strong><span>'+esc(period||'No comparable fiscal period')+'</span>'+(more?'<div class="research-mini">'+esc(more)+'</div>':'')+'</div>'}
function health(c){
 const rev=metric(c,'revenue'),inc=metric(c,'net_income'),ocf=metric(c,'operating_cash_flow'),cap=metric(c,'capex'),eq=metric(c,'equity'),debt=metric(c,'long_term_debt');
 const fcf=same(ocf,cap)?ocf.value-cap.value:null;
 const margin=same(rev,inc)&&rev.value>0?inc.value/rev.value*100:null;
 const h=(c.shares_history||[]).filter(x=>n(x.shares)!==null&&x.shares>0).sort((a,b)=>a.date.localeCompare(b.date));
 const change=h.length>1?100*(h.at(-1).shares/h[0].shares-1):null;
 const rules=[['Net income positive',n(inc?.value)===null?null:inc.value>0],['Free cash flow positive',fcf===null?null:fcf>0],['Net profit margin at least 10%',margin===null?null:margin>=10],['Reported share change at most 2%',change===null?null:change<=2],['Long-term debt no greater than equity',debt&&eq&&eq.value>0?debt.value<=eq.value:null]];
 const available=rules.filter(x=>x[1]!==null),wins=available.filter(x=>x[1]).length,score=available.length>=3?Math.round(100*wins/available.length):null;
 const row=rules.map(([k,v])=>'<div class="score-row"><span>'+esc(k)+'</span><strong class="'+(v===null?'muted':v?'positive':'negative')+'">'+(v===null?'Unavailable':v?'Pass':'Flag')+'</strong></div>').join('');
 const cards=[fact('Reported revenue',short(rev?.value),rev?.period_end),fact('Net income',short(inc?.value),inc?.period_end),fact('Free cash flow',short(fcf),fcf===null?'Matched annual periods required':ocf.period_end),fact('Net margin',pct(margin),rev?.period_end),fact('Shares outstanding change',pct(change),h.length>1?h[0].date+' → '+h.at(-1).date:'Insufficient observations'),fact('Long-term debt',short(debt?.value),debt?.period_end)].join('');
 return '<div class="research-title"><div><div class="kicker">ORIGINAL FORMULA · SEC DISCLOSURES</div><h2>Financial Health &amp; Risk</h2><p>A transparent checklist, not a credit rating, stock price target, or prediction.</p></div><div class="score-big">'+(score===null?'N/A':score+' / 100')+'<small>'+available.length+' of 5 factors</small></div></div><div class="research-facts">'+cards+'</div><h3>How the model scores this company</h3><div class="score-rows">'+row+'</div><p class="research-note">Each available factor contributes equally. Unavailable factors are excluded from the denominator; fewer than three factors means no score. Scores are not comparable across industries without accounting adjustments. Financial and share-count periods may differ. For banks and insurers, metrics such as margin, cash flow, and debt can have different meanings.</p><a href="'+esc(secLink(c.source_url)||('https://www.sec.gov/edgar/browse/?CIK='+encodeURIComponent(c.cik)))+'" target="_blank" rel="noopener noreferrer">Verify financial facts with the SEC ↗</a>';
}
function insiders(c){
 const x=rawData.insiders.tickers?.[c.ticker];
 const rows=(x?.transactions||[]).filter(v=>v.type==='P'||v.type==='S');
 const purchases=rows.filter(r=>r.type==='P'),sales=rows.filter(r=>r.type==='S');
 const body=rows.slice(0,45).map(v=>'<tr><td>'+esc(v.date)+'</td><td><span class="research-pill '+(v.type==='P'?'buy':'sell')+'">'+(v.type==='P'?'P · Purchase':'S · Sale')+'</span></td><td>'+esc(v.owner)+'</td><td>'+num(v.shares)+'</td><td>'+usd(v.price)+'</td><td><a href="'+esc(secLink(v.source_url)||rawData.insiders.source_url)+'" target="_blank" rel="noopener noreferrer">Form 4 ↗</a></td></tr>').join('');
 return '<div class="kicker">SEC REPORTED NON-DERIVATIVE FORM 4</div><h2>Insider Buying &amp; Selling</h2><p class="muted">Quarterly published dataset '+esc(x?.period||'—')+' · dataset refreshed '+esc(rawData.insiders.updated_at||'not available')+'</p><div class="research-facts">'+fact('Purchase lines (P)',num(purchases.length),'Verified P codes in loaded snapshot')+fact('Sale lines (S)',num(sales.length),'Verified S codes in loaded snapshot')+fact('Latest transaction date',rows[0]?.date||'—','Not a live feed')+'</div>'+(rows.length?'<div class="table-scroll"><table class="research-table"><thead><tr><th>Date</th><th>Code</th><th>Reporting owner</th><th>Shares</th><th>Reported price</th><th>Source</th></tr></thead><tbody>'+body+'</tbody></table></div>':missing('insider transaction',rawData.insiders.source_url))+'<p class="research-note">Only verified P and S codes are displayed. Gifts, equity awards, exercises, derivative positions and unverified filings are excluded. A reported sale does not establish insider sentiment or an exchange-executed trade. The SEC dataset is quarterly and may lag more recent filings.</p>';
}
function institutions(c){
 const x=rawData.institutions.tickers?.[c.ticker],rows=x?.positions||[];
 const body=rows.slice(0,35).map(v=>'<tr><td>'+esc(v.manager||'Unknown')+'</td><td>'+esc(v.period||'—')+'</td><td>'+num(v.shares)+'</td><td>'+short(v.value_usd)+'</td><td>'+esc(v.security_class||'—')+'</td><td><a target="_blank" rel="noopener noreferrer" href="'+esc(secLink(v.source_url)||rawData.institutions.source_url)+'">SEC filing ↗</a></td></tr>').join('');
 return '<div class="kicker">FORM 13F · QUARTERLY MANAGER DISCLOSURES</div><h2>Institutional Holdings</h2><p class="muted">Official SEC 13F dataset · '+esc(rawData.institutions.updated_at||'No validated import yet')+'</p>'+(rows.length?'<div class="table-scroll"><table class="research-table"><thead><tr><th>Reporting manager</th><th>Quarter end</th><th>Reported shares</th><th>Reported value</th><th>Security class</th><th>Source</th></tr></thead><tbody>'+body+'</tbody></table></div>':missing('issuer-matched institutional holdings',rawData.institutions.source_url))+'<p class="research-note">13F positions may be reported 45 days or more after quarter-end, do not cover every holding or institutional investor, and do not establish net buying or beneficial ownership. A security-name match alone is insufficient to assign a holding to a ticker. Only verified issuer matches should appear here.</p><p><a href="https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets" target="_blank" rel="noopener noreferrer">Browse official quarterly 13F datasets ↗</a></p>';
}
function dividend(c){
 const div=metric(c,'dividends_paid'),ocf=metric(c,'operating_cash_flow'),cap=metric(c,'capex'),inc=metric(c,'net_income'),per=metric(c,'dividend_per_share');
 const fcf=same(ocf,cap)?ocf.value-cap.value:null;
 const match=div&&same(div,ocf)&&same(div,cap);
 const payout=match&&fcf!==0?100*div.value/fcf:null;
 const earnings=div&&same(div,inc)&&inc.value>0?100*div.value/inc.value:null;
 let label='Insufficient comparable SEC dividend data';
 if(match&&fcf!==null)label=fcf<=0?'FCF was not positive in the reported period':div.value<=fcf?'FCF covered reported cash dividends':'Cash dividends exceeded reported FCF';
 return '<div class="kicker">SOURCE-DATED DIVIDEND RESEARCH</div><h2>Dividend Safety Analyzer</h2><div class="research-facts">'+
 fact('Cash dividends paid',short(div?.value),div?.period_end)+fact('Matching free cash flow',short(match?fcf:null),match?ocf.period_end:'Matching annual periods required')+fact('Dividends / FCF',pct(payout),match?ocf.period_end:'Matching periods required')+fact('Dividends / earnings',pct(earnings),div&&inc&&same(div,inc)?inc.period_end:'Matching periods required')+fact('Reported dividends per share',per?usd(per.value):'Not reported',per?.period_end)+fact('Coverage observation',label,div?.period_end)+'</div>'+
 '<p class="research-note">These are backward-looking accounting measures, not a dividend guarantee. Missing SEC concepts must not be treated as zero dividends. This calculator is not dividend yield: that requires a licensed or user-supplied market price. REITs, BDCs, banks and other specialized companies need sector-specific analysis.</p><a target="_blank" rel="noopener noreferrer" href="'+esc(secLink(c.source_url)||'https://www.sec.gov/edgar/search/')+'">Verify SEC dividend/cash-flow facts ↗</a>';
}
function comparison(c){
 const other=rawData.companies.find(v=>v.ticker===compareTo&&v.ticker!==c.ticker)||rawData.companies.find(v=>v.ticker!==c.ticker);
 const options=rawData.companies.filter(v=>v.ticker!==c.ticker).map(v=>'<option value="'+esc(v.ticker)+'"'+(other?.ticker===v.ticker?' selected':'')+'>'+esc(v.ticker)+' · '+esc(v.name)+'</option>').join('');
 const fields=[['Revenue','revenue'],['Net income','net_income'],['Diluted EPS','diluted_eps'],['Operating cash flow','operating_cash_flow'],['Capital spending','capex'],['Equity','equity'],['Long-term debt','long_term_debt'],['Cash dividends paid','dividends_paid']];
 const rows=fields.map(([label,key])=>{const a=metric(c,key),b=metric(other,key),formatter=key==='diluted_eps'?usd:short;return '<tr><th scope="row">'+esc(label)+'</th><td>'+esc(formatter(a?.value))+'<small>'+esc(a?.period_end||'Unavailable')+'</small></td><td>'+esc(formatter(b?.value))+'<small>'+esc(b?.period_end||'Unavailable')+'</small></td></tr>';}).join('');
 return '<div class="kicker">COMPARE REPORTED FINANCIALS</div><h2>Financial Comparisons</h2><div class="research-compare-controls"><span>Compare '+esc(c.ticker)+' with</span><select id="compareTicker" aria-label="Comparison company">'+options+'</select></div><div class="table-scroll"><table class="research-table comparison-table"><thead><tr><th>SEC metric</th><th>'+esc(c.ticker)+'</th><th>'+esc(other?.ticker||'—')+'</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="research-note">Reporting periods and accounting classifications may differ. No currency conversions are performed; values are presented from their reported USD tags. A side-by-side number is not a same-period ranking.</p>';
}
function filings(c){
 const rows=rawData.filings.tickers?.[c.ticker]||[];
 const key='stockspub_seen_'+c.ticker;
 let seen='';try{seen=localStorage.getItem(key)||''}catch(_){}
 const unread=rows.filter(v=>v.filed>seen).length;
 const body=rows.slice(0,35).map(v=>'<tr><td>'+esc(v.filed)+'</td><td><span class="research-pill">'+esc(v.form)+'</span></td><td>'+esc(v.description||'SEC company filing')+'</td><td><a target="_blank" rel="noopener noreferrer" href="'+esc(secLink(v.source_url)||'https://www.sec.gov/edgar/search/')+'">View filing ↗</a></td></tr>').join('');
 return '<div class="research-title"><div><div class="kicker">SEC REPORTING EVENTS</div><h2>SEC Filing Alerts</h2><p>On-site filing updates for this browser. Checked '+esc(rawData.filings.updated_at||'not yet')+'.</p></div><div class="score-big">'+unread+'<small>since last marked seen</small></div></div>'+
 '<div class="research-actions"><button class="btn btn-primary" id="markFilingsRead" type="button">Mark current filings as seen</button><a href="'+esc('https://www.sec.gov/edgar/browse/?CIK='+encodeURIComponent(c.cik))+'" target="_blank" rel="noopener noreferrer">Browse SEC company filings ↗</a></div>'+
 (rows.length?'<div class="table-scroll"><table class="research-table"><thead><tr><th>Filed</th><th>Form</th><th>Event</th><th>SEC source</th></tr></thead><tbody>'+body+'</tbody></table></div>':missing('recent SEC filing',rawData.filings.source_url))+
 '<p class="research-note">An alert means the saved SEC filing date is newer than this browser\'s last marked-seen date. This does not send email or push notifications. Filing collection is periodic, and recent amendments or documents might not yet appear.</p>';
}
function render(){
 const c=co();if(!c)return;
 $('companyInfo').textContent=c.name+' · SEC CIK '+c.cik;
 $('secIssuerLink').href='https://www.sec.gov/edgar/browse/?CIK='+encodeURIComponent(c.cik);
 const renderers={health,insiders,institutional:institutions,dividend,comparison,filings};
 $('researchContent').innerHTML=renderers[tab](c);
}
function changeTab(next){tab=next;document.querySelectorAll('[data-tab]').forEach(b=>{const on=b.dataset.tab===next;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});render();}
async function fetchData(path,fallback){try{const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error(String(r.status));return await r.json();}catch(e){console.warn('Dataset unavailable:',path,e);return fallback}}
async function init(){
 const [coData,ins,institutional,fil]=await Promise.all([
 fetchData('./data/companies.json',{companies:[]}),fetchData('./data/insiders.json',{tickers:{}}),
 fetchData('./data/institutions.json',{tickers:{}}),fetchData('./data/filings.json',{tickers:{}})]);
 rawData.companies=(coData.companies||[]).filter(c=>/^[A-Z0-9.-]{1,12}$/.test(c.ticker||'')).sort((a,b)=>a.ticker.localeCompare(b.ticker));
 rawData.insiders=ins;rawData.institutions=institutional;rawData.filings=fil;
 ticker=new URLSearchParams(location.search).get('ticker')?.toUpperCase()||'';
 if(!rawData.companies.some(c=>c.ticker===ticker))ticker=rawData.companies[0]?.ticker||'';
 $('researchTicker').innerHTML=rawData.companies.map(c=>'<option value="'+esc(c.ticker)+'"'+(c.ticker===ticker?' selected':'')+'>'+esc(c.ticker)+' · '+esc(c.name)+'</option>').join('');
 $('researchStatus').textContent=rawData.companies.length+' SEC issuers · snapshots are dated, not live quotes';
 if(!ticker){$('researchContent').innerHTML=missing('SEC company');return}
 const hash=location.hash.replace('#','');if(['health','insiders','institutional','dividend','comparison','filings'].includes(hash))changeTab(hash);else render();
}
$('researchTicker').addEventListener('change',e=>{ticker=e.target.value;compareTo='';render();});
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{changeTab(b.dataset.tab);history.replaceState(null,'','#'+b.dataset.tab);}));
$('researchContent').addEventListener('change',e=>{if(e.target.id==='compareTicker'){compareTo=e.target.value;render();}});
$('researchContent').addEventListener('click',e=>{if(e.target.id==='markFilingsRead'){const entries=rawData.filings.tickers?.[ticker]||[];const latest=entries.map(x=>x.filed).sort().at(-1);if(latest){try{localStorage.setItem('stockspub_seen_'+ticker,latest)}catch(_){}}render();}});
init();