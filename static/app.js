'use strict';
const $ = s => document.querySelector(s);
let posts = [], candidates = [], service = {}, verifyTarget = null;
const el = (tag, cls, text) => { const n = document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; };
function toast(message) { $('#toast').textContent=message; $('#toast').style.display='block'; clearTimeout(toast.timer); toast.timer=setTimeout(()=>$('#toast').style.display='none',5500); }
async function api(path, data) {
  const r=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await r.json(); if(!r.ok)throw new Error(result.error||'Anfrage fehlgeschlagen'); return result;
}
async function load() {
  try {
    [posts,candidates,service]=await Promise.all([api('/api/posts'+($('#demo-mode').checked?'?mode=demo':'')),api('/api/candidates'),api('/api/status')]);
    showStatus(); render();
  } catch(e){$('#posts').replaceChildren(el('p','empty',e.message));}
}
function showStatus(){
  $('.status').textContent=$('#demo-mode').checked?'● Demo · keine echte KI':'● Manuelle Prüfung erforderlich';
  $('#ai-status').textContent=service.ai_ready?'OpenAI bereit · Modell: '+service.model+' · nur nach bestätigtem Klick.':'Echte KI nicht eingerichtet. '+(!service.ai_key_present?'OPENAI_API_KEY fehlt. ':'')+(!service.ai_authorized?'Verarbeitung durch OpenAI noch nicht freigegeben. ':'')+'Fiktive Textvorlagen sind ausschließlich im Demo-Modus verfügbar.';
  $('#search-status').textContent=service.search_ready?'Brave-Suche bereit · Treffer bleiben unverifiziert.':'Keine freigegebene Suchquelle eingerichtet. Manuell auf LinkedIn recherchieren und importieren; die App ruft keine LinkedIn-Seiten ab.';
  const u=service.usage,l=service.limits;
  $('#usage-status').textContent=`Heute (UTC): KI ${u.ai_calls}/${l.max_ai_calls} Aufrufe · Suche ${u.search_calls}/${l.max_search_calls} · unterschiedliche KI-Beiträge ${u.posts_processed}/${l.max_posts}. Auch fehlgeschlagene Anbieteranfragen zählen.`;
  const r=service.retention;
  $('#retention-status').textContent=`Aufbewahrung: ${l.retention_days} Tage empfohlen. ${r.expired_posts} Beiträge und ${r.expired_candidates} Kandidaten älter. ${r.legacy_without_date} alte Imports ohne Erfassungsdatum bleiben erhalten. Löschung nur nach Bestätigung.`;
}
function action(text, handler, cls) {const b=el('button',cls,text);b.type='button';b.addEventListener('click',async()=>{b.disabled=true;try{await handler();}catch(e){toast(e.message);}finally{b.disabled=false;}});return b;}
function link(text, url){const a=el('a','',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function dateText(value){const date=new Date(value);return value&&!Number.isNaN(date.getTime())?new Intl.DateTimeFormat('de-DE',{dateStyle:'medium',timeStyle:'short'}).format(date):'Veröffentlichungszeit unbekannt';}
function render(){
  $('#count').textContent=posts.filter(p=>p.assessment.eligible&&!p.review.unsuitable).length;
  const visible=posts.filter(p=>(!$('#topic').value||p.assessment.topics.includes($('#topic').value))&&p.assessment.score>=Number($('#score').value)&&(!$('#source').value||p.source===$('#source').value)&&($('#excluded').checked||p.status==='unverified'||p.assessment.eligible)&&($('#unsuitable').checked||!p.review.unsuitable));
  const pending=$('#demo-mode').checked?[]:candidates.filter(p=>p.status==='candidate'&&(!$('#topic').value||p.topic===$('#topic').value)&&(!$('#source').value||p.source===$('#source').value));
  $('#visible-count').textContent=visible.length+' · '+pending.length+' Kandidaten';
  $('#candidates').replaceChildren(...pending.map(candidateCard));
  $('#posts').replaceChildren(...visible.map(card));
  if(!visible.length)$('#posts').append(el('div','empty',pending.length?'Kandidaten am Original prüfen, um verifizierte Beiträge zu erhalten.':'Keine Beiträge für diese Auswahl. Manuell recherchieren und importieren oder ausdrücklich den Demo-Modus aktivieren.'));
}
function candidateCard(p){
  const article=el('article','card candidate-card'),top=el('div','card-top');
  top.append(el('span','badge','ENTDECKTER KANDIDAT · UNVERIFIZIERT'),el('h3','',p.title||'LinkedIn-Suchtreffer'),el('p','post-text',p.snippet||'Kein Suchausschnitt vorhanden.'),el('p','meta','Suchausschnitt, kein bestätigter Originaltext. Fundzeit: '+dateText(p.discovered_at)),el('p','reasons','Autor und Veröffentlichungszeit unbekannt. Keine Eignung und keine Kommentare vor Verifikation.'),link('Originalbeitrag ↗',p.source_url||p.url),action('Original prüfen & verifizieren',()=>openImport(p,'candidate')));
  article.append(top);return article;
}
function card(p){
  const article=el('article','card'),top=el('div','card-top'),authorLine=el('div','author-line'),authorBlock=el('div');
  authorBlock.append(el('div','author',p.author||'Autor noch nicht bestätigt'));
  const meta=el('div','meta');meta.append(el('span','badge',p.status==='demo'?'FIKTIVES BEISPIEL':p.status==='verified'?'MENSCHLICH VERIFIZIERT':'IMPORT · UNVERIFIZIERT'));
  const time=el('time','',dateText(p.published_at));if(p.published_at)time.dateTime=p.published_at;time.title='Anzeige in deiner lokalen Zeitzone';meta.append(time);authorBlock.append(meta);
  const score=el('div','score',String(p.assessment.score));score.append(el('small','',' / 100'));score.title='Regelbasierte Punktzahl; bestätigt keine Eignung ohne Verifikation.';
  authorLine.append(authorBlock,score);top.append(authorLine);
  const tags=el('div','tags');p.assessment.topics.forEach(t=>tags.append(el('span','tag',t)));if(p.review.unsuitable)tags.append(el('span','tag','Als ungeeignet markiert'));top.append(tags,el('p','post-text',p.text||'Originaltext fehlt.'),el('p','relevance',p.assessment.relevance_reason));
  if(!p.assessment.eligible)top.append(el('p','reasons',p.assessment.reasons.join(' ')));
  if(p.publication_evidence)top.append(el('p','meta','Manueller Zeitbeleg: '+p.publication_evidence));
  if(p.verified_at)top.append(el('p','meta','Am Original geprüft: '+dateText(p.verified_at)+' · keine unabhängige LinkedIn-Bestätigung'));
  const links=el('div','links');if(p.url)links.append(link('Originalbeitrag ↗',p.url));if(p.profile_url)links.append(link('Persönliches Profil ↗',p.profile_url));top.append(links);
  if(p.status==='unverified')top.append(action('Original prüfen & verifizieren',()=>openImport(p,'post')));
  const warnings=el('details','warnings');warnings.append(el('summary','','Bewertung & Hinweise'));warnings.append(el('p','','Relevanz: '+p.assessment.components.relevance+'/40 · Aktualität: '+p.assessment.components.recency+'/25 · Diskussion: '+p.assessment.components.discussion+'/20 · Qualität: '+p.assessment.components.quality+'/15'));p.assessment.warnings.forEach(w=>warnings.append(el('p','',w)));top.append(warnings);article.append(top);
  const area=el('div','comment-area'),head=el('div','comment-header');head.append(el('strong','',p.status==='demo'?'Kommentarwerkstatt · DEMO-TEXTVORLAGEN':p.generation.kind==='ai'?'KI-ENTWÜRFE · '+p.generation.model:'Kommentarwerkstatt · echte KI auf Anfrage'));
  const reviewPath='/api/posts/'+p.id+'/review';
  const generate=async(force)=>{
    const message=p.status==='demo'?'Demo neu formulieren? Die gespeicherte Demo-Bearbeitung wird ersetzt.':'Den Originaltext dieses Beitrags an OpenAI übermitteln? Bestätige, dass diese Verarbeitung autorisiert ist. API-Kosten können entstehen; vorhandene Bearbeitungen bleiben erhalten.';
    if(!confirm(message))return;
    try{await api('/api/posts/'+p.id+(force?'/regenerate':'/generate'),{authorized:true});await load();toast(p.status==='demo'?'Demo neu formuliert.':'KI-Antwort gespeichert. Bitte fachlich prüfen.');}catch(e){toast(e.message);await load();}
  };
  if(p.comments.length){
    head.append(action('↻ Neu formulieren',()=>generate(true)));area.append(head);
    if(p.generation.created_at)area.append(el('p','meta','Generiert: '+dateText(p.generation.created_at)+' · Änderungen durch Menschen werden separat gespeichert.'));
    const options=el('div','options'),draft=el('textarea','draft');draft.maxLength=5000;draft.setAttribute('aria-label','Kommentarentwurf bearbeiten');
    let selected=p.review.selected||'A', baseline=p.review.draft??p.comments.find(c=>c.key===selected).text;
    draft.value=baseline;
    const optionButtons=[];
    p.comments.forEach(c=>{const b=action('',async()=>{if(draft.value!==baseline&&!confirm('Nicht gespeicherte Bearbeitung verwerfen und Option wechseln?'))return;selected=c.key;draft.value=c.text;baseline=c.text;copy.disabled=p.status!=='demo';reviewNote.textContent='Option gewechselt. Erneute menschliche Prüfung erforderlich.';optionButtons.forEach(o=>{o.classList.toggle('active',o.dataset.key===selected);o.setAttribute('aria-pressed',String(o.dataset.key===selected));});});b.className='option'+(selected===c.key?' active':'');b.dataset.key=c.key;b.setAttribute('aria-pressed',String(selected===c.key));b.append(el('b','','Option '+c.key),document.createTextNode(c.label));optionButtons.push(b);options.append(b);});area.append(options,draft);
    const actions=el('div','actions'),left=el('div');
    const save=async(reviewed=false)=>{const result=await api(reviewPath,{selected,draft:draft.value,...(reviewed?{reviewed:true}:{})});p.review=result.review;baseline=draft.value;reviewNote.textContent=p.review.reviewed?'✓ Menschlich geprüft · '+dateText(p.review.reviewed_at):'Noch nicht geprüft. Vor Veröffentlichung Fakten und Ton prüfen.';copy.disabled=p.status!=='demo'&&(!p.assessment.eligible||p.review.unsuitable||!p.review.reviewed);};
    const reviewNote=el('p','manual-note',p.review.reviewed?'✓ Menschlich geprüft · '+dateText(p.review.reviewed_at):'Noch nicht geprüft. Vor Veröffentlichung Fakten und Ton prüfen.');
    const copy=action('Kopieren',async()=>{
      if(p.status!=='demo'&&(!p.assessment.eligible||p.review.unsuitable||!p.review.reviewed||draft.value!==p.review.draft||selected!==p.review.selected))throw new Error('Zuerst den aktuellen Entwurf als geprüft markieren.');
      if(!navigator.clipboard){draft.focus();draft.select();toast('Text markiert – bitte manuell kopieren.');return;}await navigator.clipboard.writeText(draft.value);toast('Kopiert. Ausschließlich manuell veröffentlichen.');
    });copy.disabled=p.status!=='demo'&&(!p.assessment.eligible||p.review.unsuitable||!p.review.reviewed);
    draft.addEventListener('input',()=>{copy.disabled=p.status!=='demo';reviewNote.textContent='Bearbeitung geändert. Erneute menschliche Prüfung erforderlich.';});
    left.append(action('Entwurf speichern',async()=>{await save();toast('Entwurf gespeichert.');}),action('Als geprüft markieren',async()=>{if(!confirm('Originalbezug, Fakten und Ton dieses Entwurfs geprüft?'))return;await save(true);toast('Menschliche Prüfung gespeichert.');}),copy);actions.append(left);area.append(actions,reviewNote);
  }else{
    area.append(head);
    const note=p.generation.note||(p.status==='unverified'?'Zuerst Originaltext, Autorenart und Veröffentlichungszeit prüfen.':!p.assessment.eligible?'Ausgeschlossen: keine Generierung.':!p.assessment.enough_context?'Zu wenig Kontext für fundierte Kommentare.':'Drei deutsche KI-Optionen werden erst nach ausdrücklichem Klick erzeugt.');
    area.append(el('p','manual-note',note));
    if(p.status==='verified'&&p.assessment.eligible&&p.assessment.enough_context&&!p.review.unsuitable)area.append(action(p.generation.note?'Erneut KI-Kommentare erzeugen':'KI-Kommentare erzeugen',()=>generate(Boolean(p.generation.note)),'primary'));
    if(p.review.draft){const old=el('details','warnings');old.append(el('summary','','Vorhandene Bearbeitung (unverändert erhalten)'),el('p','post-text',p.review.draft));area.append(old);}
  }
  area.append(action(p.review.unsuitable?'Wieder aufnehmen':'Als ungeeignet markieren',async()=>{await api(reviewPath,{unsuitable:!p.review.unsuitable,reviewed:false});await load();}),el('p','manual-note','Keine automatische Veröffentlichung, Likes oder Nachrichten. Menschliche Prüfung bleibt erforderlich.'));
  article.append(area);return article;
}
function openImport(p=null,kind=null){
  const form=$('#import-form');form.reset();$('#import-error').textContent='';verifyTarget=p?{id:p.id,kind}:null;
  $('#import-title').textContent=p?'Original prüfen & verifizieren':'Beitrag manuell erfassen';$('#import-submit').textContent=p?'Verifikation speichern':'Unverifiziert importieren';$('#verification-fields').hidden=!p;
  for(const name of ['author','text','published_at','publication_evidence'])form.elements[name].required=Boolean(p);
  for(const name of ['original_checked','author_checked','time_checked'])form.elements[name].required=Boolean(p);
  if(p){
    form.elements.url.value=p.url;form.elements.url.readOnly=true;
    for(const name of ['author','text','profile_url','publication_evidence'])form.elements[name].value=p[name]||'';
    form.elements.author_type.value=p.author_type||'unknown';
    if(p.published_at){const d=new Date(p.published_at);if(!Number.isNaN(d.getTime()))form.elements.published_at.value=new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
  }else form.elements.url.readOnly=false;
  $('#import-dialog').showModal();
}
['topic','score','source','excluded','unsuitable'].forEach(id=>$('#'+id).addEventListener('input',()=>{$('#score-value').textContent=$('#score').value;render();}));
$('#demo-mode').addEventListener('change',()=>{$('#source').value='';load();});
$('#open-import').addEventListener('click',()=>openImport());$('#close-import').addEventListener('click',()=>$('#import-dialog').close());
$('#import-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=$('#import-submit');button.disabled=true;$('#import-error').textContent='';
  try{
    const form=e.target,data=Object.fromEntries(new FormData(form));
    data.published_at=data.published_at?new Date(data.published_at).toISOString():'';
    for(const name of ['original_checked','author_checked','time_checked','import_authorized'])data[name]=form.elements[name].checked;
    const path=verifyTarget?'/api/'+(verifyTarget.kind==='candidate'?'candidates':'posts')+'/'+verifyTarget.id+'/verify':'/api/posts';
    await api(path,data);form.reset();$('#import-dialog').close();$('#demo-mode').checked=false;$('#source').value='';$('#excluded').checked=true;await load();toast(verifyTarget?'Verifikation gespeichert. Eignung anhand der Angaben geprüft.':'Unverifiziert erfasst. Vor KI-Verarbeitung am Original prüfen.');
  }catch(err){$('#import-error').textContent=err.message;}finally{button.disabled=false;}
});
$('#search').addEventListener('click',async()=>{
  if(!service.search_ready){toast('Suchanbieter zuerst serverseitig konfigurieren. Siehe Dienste & Datenschutz und README.');return;}
  if(!confirm('Themenabfrage an Brave senden? Bestätige die zulässige Recherche und Speicherung der Suchergebnisse. Kosten können entstehen.'))return;
  $('#search').disabled=true;
  try{const result=await api('/api/search',{topic:$('#search-topic').value,authorized:true});$('#demo-mode').checked=false;$('#topic').value='';$('#source').value='';$('#score').value='0';await load();toast(result.added+' neue Kandidaten. '+result.note);}catch(e){toast(e.message);await load();}finally{$('#search').disabled=false;}
});
$('#purge').addEventListener('click',async()=>{
  await load();const r=service.retention;
  if(!r.expired_posts&&!r.expired_candidates){toast('Keine datierten Einträge außerhalb der Aufbewahrungsfrist. Undatierte Altbestände bleiben erhalten.');return;}
  if(!confirm(`${r.expired_posts} alte Beiträge mit ihren Entwürfen und ${r.expired_candidates} Kandidaten endgültig löschen? Undatierte Altbestände bleiben erhalten.`))return;
  try{const result=await api('/api/retention/purge',{confirm:true});await load();toast(`${result.posts_removed} Beiträge und ${result.candidates_removed} Kandidaten gelöscht.`);}catch(e){toast(e.message);}
});
load();
