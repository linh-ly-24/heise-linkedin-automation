'use strict';
const $ = s => document.querySelector(s);
let posts = [];
const el = (tag, cls, text) => { const n = document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; };
function toast(message) { $('#toast').textContent=message; $('#toast').style.display='block'; clearTimeout(toast.timer); toast.timer=setTimeout(()=>$('#toast').style.display='none',4000); }
async function api(path, data) {
  const r=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await r.json(); if(!r.ok)throw new Error(result.error||'Anfrage fehlgeschlagen'); return result;
}
async function load() { try { posts=await api('/api/posts'); render(); } catch(e){$('#posts').replaceChildren(el('p','empty',e.message));} }
function action(text, handler, cls) {const b=el('button',cls,text);b.type='button';b.addEventListener('click',async()=>{b.disabled=true;try{await handler();}catch(e){toast(e.message);}finally{b.disabled=false;}});return b;}
function link(text, url){const a=el('a','',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function render(){
  $('#count').textContent=posts.filter(p=>p.assessment.eligible&&!p.review.unsuitable).length;
  const visible=posts.filter(p=>(!$('#topic').value||p.assessment.topics.includes($('#topic').value))&&p.assessment.score>=Number($('#score').value)&&(!$('#source').value||p.source===$('#source').value)&&($('#excluded').checked||p.assessment.eligible)&&($('#unsuitable').checked||!p.review.unsuitable));
  $('#visible-count').textContent=visible.length;
  $('#posts').replaceChildren(...visible.map(card));
  if(!visible.length)$('#posts').append(el('div','empty','Keine Beiträge für diese Auswahl. Filter anpassen oder einen echten Beitrag hinzufügen.'));
}
function card(p){
  const article=el('article','card'); const top=el('div','card-top');
  const authorLine=el('div','author-line');const authorBlock=el('div');authorBlock.append(el('div','author',p.author));
  const meta=el('div','meta');meta.append(el('span','badge',p.source==='demo'?'FIKTIVES BEISPIEL':'MANUELL · UNVERIFIZIERT'));
  const date=new Date(p.published_at);const time=el('time','',new Intl.DateTimeFormat('de-DE',{dateStyle:'medium',timeStyle:'short'}).format(date));time.dateTime=p.published_at;time.title='Anzeige in deiner lokalen Zeitzone';meta.append(time);authorBlock.append(meta);
  const score=el('div','score',String(p.assessment.score));score.append(el('small','',' / 100'));score.title='Relevanz '+p.assessment.components.relevance+' · Aktualität '+p.assessment.components.recency+' · Diskussion '+p.assessment.components.discussion+' · Qualität '+p.assessment.components.quality;
  authorLine.append(authorBlock,score);top.append(authorLine);
  const tags=el('div','tags');p.assessment.topics.forEach(t=>tags.append(el('span','tag',t)));if(p.review.unsuitable)tags.append(el('span','tag','Als ungeeignet markiert'));top.append(tags,el('p','post-text',p.text),el('p','relevance',p.assessment.relevance_reason));
  if(!p.assessment.eligible)top.append(el('p','reasons',p.assessment.reasons.join(' ')));
  const links=el('div','links');if(p.url)links.append(link('Originalbeitrag ↗',p.url));if(p.profile_url)links.append(link('Persönliches Profil ↗',p.profile_url));top.append(links);
  const warnings=el('details','warnings');warnings.append(el('summary','','Bewertung & Hinweise'));const breakdown=el('p','','Relevanz: '+p.assessment.components.relevance+'/40 · Aktualität: '+p.assessment.components.recency+'/25 · Diskussion: '+p.assessment.components.discussion+'/20 · Qualität: '+p.assessment.components.quality+'/15');warnings.append(breakdown);p.assessment.warnings.forEach(w=>warnings.append(el('p','',w)));top.append(warnings);article.append(top);
  const area=el('div','comment-area');const head=el('div','comment-header');head.append(el('strong','','Kommentarwerkstatt · regelbasierte Entwürfe'));
  const reviewPath='/api/posts/'+p.id+'/review';
  if(p.comments.length){
    head.append(action('↻ Neu formulieren',async()=>{if(!confirm('Neue Formulierung erzeugen? Gespeicherte Bearbeitung wird ersetzt.'))return;await api('/api/posts/'+p.id+'/regenerate',{});await load();}));area.append(head);
    const options=el('div','options');const draft=el('textarea','draft');draft.maxLength=5000;draft.setAttribute('aria-label','Kommentarentwurf bearbeiten');
    let selected=p.review.selected||'A';draft.value=p.review.draft??p.comments.find(c=>c.key===selected).text;
    const optionButtons=[];
    p.comments.forEach(c=>{const b=action('',async()=>{if(draft.value!==(p.review.draft??p.comments.find(o=>o.key===selected).text)&&!confirm('Bearbeitung verwerfen und Option wechseln?'))return;selected=c.key;draft.value=c.text;p.review.draft=undefined;optionButtons.forEach(o=>{o.classList.toggle('active',o.dataset.key===selected);o.setAttribute('aria-pressed',String(o.dataset.key===selected));});});b.className='option'+(selected===c.key?' active':'');b.dataset.key=c.key;b.setAttribute('aria-pressed',String(selected===c.key));b.append(el('b','','Option '+c.key),document.createTextNode(c.label));optionButtons.push(b);options.append(b);});
    area.append(options,draft);
    const actions=el('div','actions');const left=el('div');left.append(action('Entwurf speichern',async()=>{await api(reviewPath,{selected,draft:draft.value});p.review.selected=selected;p.review.draft=draft.value;toast('Entwurf gespeichert.');}),action('Kopieren',async()=>{if(!navigator.clipboard){draft.focus();draft.select();toast('Text markiert – bitte manuell kopieren.');return;}await navigator.clipboard.writeText(draft.value);toast('Kopiert. Vor manueller Veröffentlichung prüfen.');}));actions.append(left,action(p.review.unsuitable?'Wieder aufnehmen':'Als ungeeignet markieren',async()=>{await api(reviewPath,{unsuitable:!p.review.unsuitable});await load();}));area.append(actions,el('p','manual-note','Keine automatische Veröffentlichung. Quellen, Aussage und Ton vor dem manuellen Kopieren prüfen.'));
  }else{area.append(head,el('p','manual-note',p.assessment.eligible?'Zu wenig Informationen für einen fundierten Kommentar. Ergänze den vollständigen Inhalt durch einen neuen manuellen Import.':'Für ausgeschlossene Beiträge werden keine Kommentare erzeugt.'),action(p.review.unsuitable?'Wieder aufnehmen':'Als ungeeignet markieren',async()=>{await api(reviewPath,{unsuitable:!p.review.unsuitable});await load();}));}
  article.append(area);return article;
}
['topic','score','source','excluded','unsuitable'].forEach(id=>$('#'+id).addEventListener('input',()=>{$('#score-value').textContent=$('#score').value;render();}));
$('#open-import').addEventListener('click',()=>$('#import-dialog').showModal());$('#close-import').addEventListener('click',()=>$('#import-dialog').close());
$('#import-form').addEventListener('submit',async e=>{e.preventDefault();const button=e.target.querySelector('button[type=submit]');button.disabled=true;$('#import-error').textContent='';try{const data=Object.fromEntries(new FormData(e.target));data.published_at=new Date(data.published_at).toISOString();await api('/api/posts',data);e.target.reset();$('#import-dialog').close();$('#source').value='manual';$('#excluded').checked=true;await load();toast('Erfasst und bewertet. Manuelle Angaben bitte prüfen.');}catch(err){$('#import-error').textContent=err.message;}finally{button.disabled=false;}});
load();
