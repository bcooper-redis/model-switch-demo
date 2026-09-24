import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowUp, ArrowUpRight, Check, Circle, Database, MessageSquare, Plus, RotateCcw, Sparkles, X, ChevronRight, Layers, LoaderCircle, LockKeyhole, Download} from 'lucide-react';
import './style.css';
import {DocumentImport} from './DocumentImport';

type Memory = {sync_error?:string;source_kind?:string;document_id?:string;source_section?:string;source_line?:number;source_notes?:string[];sync_status?:string;category?:string;people?:string[];revision?:number;id:string;text:string;source_message_id:string;source_text:string;conversation_id:string;saved_at:string;attribution_method:string};
type Candidate = {id:string;text:string;version:string;sources:{message_id:string;text:string}[]};
const categories = ['about_me','family','interests','experiences','current_life'];
type Message = {id:string;request_id:string;role:string;text:string;status:string;local_execution?:{execution:string;model:string;digest:string;size_vram_bytes:number};provider?:string;model?:string;error?:string;memories?:Memory[];recall_bypassed?:boolean;recall_ms?:number;generation_ms?:number};
type Conversation = {id:string;title:string;messages:Message[];created_at:string};
type Job = {id:string;delivery:string;extraction:string;error?:string;saved_memory_ids:string[]};
type Provider = {id:string;label:string;available:boolean;default_model:string;models:string[];reachable?:boolean;installed_models?:string[];status?:string};
type State = {documents:{id:string;filename:string;content_hash:string}[];memory_changes_pending:number;candidates:Candidate[];providers:Provider[];owner_id:string;generation:string;conversations:Conversation[];jobs:Job[];memories:Memory[];model:string;embedding_model:string;worker_at:string|null;reset_cleanup_pending:boolean};

async function api(path:string, body?:unknown) {
  const response = await fetch('/api'+path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Demo-Request':'1'},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The request failed. Please retry.');
  return data;
}

function App({onPrivate}:{onPrivate:(providers:Provider[])=>void}) {
  const [uploadOpen,setUploadOpen] = useState(false);
  const [documentSource,setDocumentSource] = useState<Memory|null>(null);
  const [editing,setEditing] = useState<Memory|null>(null);
  const [editText,setEditText] = useState('');
  const [deleting,setDeleting] = useState(false);
  const [cacheEnabled,setCacheEnabled] = useState(false);
  const [cacheResult,setCacheResult] = useState<{status:string;text:string;cache_ms?:number;generation_ms?:number}|null>(null);
  const [query,setQuery] = useState('');
  const [category,setCategory] = useState('all');
  const [state,setState] = useState<State|null>(null);
  const [cid,setCid] = useState<string|null>(null);
  const [text,setText] = useState('');
  const [provider,setProvider] = useState('openai');
  const [models,setModels] = useState<Record<string,string>>({});
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [connectionError,setConnectionError] = useState('');
  const [selected,setSelected] = useState<string|null>(null);
  const [source,setSource] = useState<string|null>(null);
  const [resetOpen,setResetOpen] = useState(false);
  const [confirmation,setConfirmation] = useState('');
  const messageArea = useRef<HTMLDivElement>(null);
  const initial = useRef(true);
  const refresh = async () => {
    const data:State = await api('/state'); setState(data); setConnectionError('');
    if (initial.current) {setCid(data.conversations.at(-1)?.id || null); setModels(Object.fromEntries(data.providers.map(p=>[p.id,p.default_model]))); initial.current=false;}
    return data;
  };
  useEffect(()=>{refresh().catch(e=>setConnectionError(e.message)); const id=setInterval(()=>refresh().catch(e=>setConnectionError(e.message)),3000);return()=>clearInterval(id);},[]);
  const conversation = state?.conversations.find(c=>c.id===cid);
  const messages = conversation?.messages || [];
  useEffect(()=>{if (!source && messageArea.current) messageArea.current.scrollTo({top:messageArea.current.scrollHeight,behavior:'smooth'});},[cid,messages.length,busy]);
  useEffect(()=>{if(source) document.getElementById(source)?.scrollIntoView({behavior:'smooth',block:'center'});},[source,cid]);
  const selectedMessage = messages.find(m=>m.id===selected);
  const latest = [...messages].reverse().find(m=>m.role==='ASSISTANT');
  const evidence = selectedMessage || latest;
  const supplied = evidence?.memories || [];
  const unfinished = messages.find(m=>m.role==='USER' && m.status!=='complete');
  useEffect(()=>{if(unfinished?.provider && unfinished.model){setProvider(unfinished.provider);setModels(previous=>({...previous,[unfinished.provider!]:unfinished.model!}));}},[cid,unfinished?.id]);
  const selectedProvider = state?.providers.find(p=>p.id===provider);
  const model = models[provider] || selectedProvider?.default_model || '';
  const providerReady = !!selectedProvider?.available && !!model;
  const workerOffline = !state?.worker_at || Date.now()-new Date(state.worker_at).getTime()>120000;

  async function newConversation() {
    setBusy(true);setError('');
    try {const c=await api('/conversations',{});await refresh();setCid(c.id);setSelected(null);setSource(null);setText('');}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function send(retry?:Message, withoutRecall=false) {
    if(!retry && (!text.trim() || !providerReady))return;
    const content=retry?.text || text.trim();const requestId=retry?.request_id || crypto.randomUUID();
    setBusy(true);setError('');setSource(null);setSelected(null);
    try {
      let id=cid;
      if(!id){const c=await api('/conversations',{});id=c.id;setCid(id);}
      if(!retry)setText('');
      await api(`/conversations/${id}/turns`,{request_id:requestId,text:content,without_recall:withoutRecall,provider:retry?.provider || provider,model:retry?.model || model});
      await refresh();
    }catch(e){setError((e as Error).message);await refresh().catch(()=>{});}
    finally{setBusy(false);}
  }
  async function retryJob(job:Job) {
    try{await api(`/jobs/${job.id}/retry`,{});setError('');await refresh();}catch(e){setError((e as Error).message);}
  }
  async function reset() {
    setBusy(true);
    try{await api('/reset',{generation:state?.generation,confirmation});await refresh();setCid(null);setSelected(null);setSource(null);setResetOpen(false);setConfirmation('');setError('');}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function changeMemory() {if(!editing)return;setBusy(true);try{await api(`/memories/${editing.id}`,{revision:editing.revision || 1,text:editText,delete:deleting});setEditing(null);await refresh();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  async function cacheExample(variant:number){setBusy(true);try{setCacheResult(await api('/examples/cache',{provider,model,variant,enabled:cacheEnabled}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  function openSource(m:Memory){if(m.source_kind==='document'){setDocumentSource(m);return;}setCid(m.conversation_id);setSource(m.source_message_id);setSelected(null);}
  function memoryCard(m:Memory){return <article className="memory-card" key={m.id}>
    <div className="memory-label"><span className="tiny-dot"/> {(m.category || 'about_me').replaceAll('_',' ').toUpperCase()} <span className="verified"><Check size={12}/> {m.attribution_method==='document_confirmed'?'Document approved':m.attribution_method==='user_edited'?'Your correction':m.attribution_method==='user_confirmed'?'User confirmed':'Source verified'}</span></div>
    <p>{m.text}</p><button className="source-link" onClick={()=>openSource(m)}>{m.source_kind==='document'?'View document passage':'View supporting message'} <ArrowUpRight size={14}/></button>
    <div className="source-quote">“{m.source_text}”</div><small>{m.attribution_method==='document_confirmed'?'Approved from your document':m.attribution_method==='user_edited'?'Corrected explicitly by you':m.attribution_method==='user_confirmed'?'Fact and source confirmed by you':'Attribution verified by the application'} · revision {m.revision || 1}{m.people?.length ? ' · '+m.people.join(', ') : ''}</small>
    <div className="memory-actions">{m.sync_status==='pending'?<small>{m.sync_error || 'Saved locally · cloud sync pending; not yet used for recall'}</small>:<><button disabled={busy} onClick={()=>{setEditing(m);setEditText(m.text);setDeleting(false);}}>Edit</button><button disabled={busy} onClick={()=>{setEditing(m);setDeleting(true);}}>Delete</button></>}</div>
  </article>}

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Layers size={23}/></div><div>shared context<span>POWERED BY REDIS</span></div></div>
      <button className="new-chat" onClick={newConversation} disabled={busy}><Plus size={17}/> New conversation</button>
      <button className="new-chat" disabled={busy || !state} aria-label="New private chat" title="New private chat" onClick={()=>state&&onPrivate(state.providers)}><LockKeyhole size={17}/> New private chat</button>
      <button className="new-chat" aria-label="Upload context document" title="Upload context document" disabled={busy||!state} onClick={()=>setUploadOpen(true)}><Plus size={17}/> Upload context</button>
      <div className="section-label">CONVERSATIONS <span>{state?.conversations.length || 0}</span></div>
      <nav aria-label="Conversations">{state?.conversations.slice().reverse().map(c=><button key={c.id} aria-label={c.title} disabled={busy} className={'conversation '+(cid===c.id?'active':'')} onClick={()=>{setCid(c.id);setSelected(null);setSource(null);}}><MessageSquare size={15}/><span>{c.title}</span>{cid===c.id&&<ChevronRight size={13}/>}</button>)}
      {!state?.conversations.length&&<p className="sidebar-empty">Your conversations will appear here.</p>}</nav>
      <div className="sidebar-bottom"><a className="source-link export-link" aria-label="Export conversations and memories" title="Export conversations and memories" href="/api/export" download><Download size={17}/><span>Export conversations & memories</span></a><div className="persistence"><Database size={17}/><div>Context stays with you<small>Saved in Redis Cloud</small></div></div><button className="reset-button" onClick={()=>setResetOpen(true)} disabled={busy || !state}><RotateCcw size={14}/> Reset demo</button></div>
    </aside>
    <main>
      <header><div><span className="eyebrow">PERSONAL MEMORY DEMO</span><h1>A new chat. The same context.</h1></div><div className="model-selectors"><label>Answering provider<select aria-label="Answering provider" value={provider} disabled={busy || !!unfinished || !state} onChange={e=>setProvider(e.target.value)}>{state?.providers.map(p=><option key={p.id} value={p.id} disabled={!p.available}>{p.label}{!p.available?' — not configured':''}</option>)}</select></label><label>Model<select aria-label="Answering model" value={model} disabled={busy || !!unfinished || !providerReady} onChange={e=>setModels({...models,[provider]:e.target.value})}>{selectedProvider?.models.map(m=><option key={m} value={m}>{m}</option>)}</select></label></div></header>
      <div className="workspace">
        <section className="chat" aria-label="Chat">
          <div className="chat-top"><span><MessageSquare size={15}/> {conversation ? 'Conversation' : 'Start a conversation'}</span><span className="badge">Memory enabled</span></div>
          {(error||connectionError)&&<div className="alert" role="alert">{error||connectionError}<button aria-label="Dismiss error" onClick={()=>{setError('');setConnectionError('');}}><X size={14}/></button></div>}
          {provider==='local'&&<div className="notice">{selectedProvider?.status || 'Local runtime not configured'}. Answer generation runs on this machine; memory and embeddings still use cloud services.{selectedProvider?.reachable&&!selectedProvider.installed_models?.includes(model)&&' Selected model is not downloaded.'}</div>}
          {state&&workerOffline&&<div className="notice">Memory worker is starting or unavailable. Saved conversations remain in Redis.</div>}
          {state?.reset_cleanup_pending&&<div className="notice">Demo cleared from recall. Cloud cleanup is still pending.</div>}
          <div className="messages" ref={messageArea}>
            {!messages.length&&<div className="welcome"><div className="welcome-icon"><Sparkles size={25}/></div><span className="eyebrow">LET’S START WITH SOMETHING SIMPLE</span><h2>A little context<br/>goes a long way.</h2><p>Share a fact, then open a fresh conversation.<br/>Your saved memory comes with you.</p><button className="suggestion" onClick={()=>setText("What's my name?")} disabled={busy}>What’s my name? <ArrowUpRight size={15}/></button><div className="start-hint">Ask first to see what the assistant knows.</div></div>}
            {messages.map(m=>{
              const job=state?.jobs.find(j=>j.id===m.id);
              return <div id={m.id} key={m.id} className={`message ${m.role.toLowerCase()} ${source===m.id?'highlight':''}`}>
                <div className="message-label">{m.role==='USER'?'YOU':<><Sparkles size={13}/> {m.provider==='local'?'LOCAL · OLLAMA':m.provider==='anthropic'?'ANTHROPIC':'OPENAI'} · {m.model || state?.model}</>}</div><div className="bubble">{m.text}</div>
                {m.role==='USER'&&job&&<div className={'memory-status '+(job.error?'failed':'')}>
                  {job.extraction==='cancelled'?<>Extraction retired after a memory change</>:job.error?<><Circle size={10}/>{job.error}<button onClick={()=>retryJob(job)}>Retry sync</button></>:job.saved_memory_ids.length?<><Check size={12}/> Saved {job.saved_memory_ids.length} {job.saved_memory_ids.length===1?'memory':'memories'}</>:<><span className="pending-dot"/>{job.delivery==='confirmed'?'Memory processing pending':'Waiting to sync memories'}</>}
                </div>}
                {m.role==='ASSISTANT'&&<div className="answer-meta"><button className={selected===m.id?'chosen':''} onClick={()=>setSelected(m.id)}><Database size={12}/> {m.recall_bypassed?'Recall bypassed':`${m.memories?.length || 0} memories supplied`} <ChevronRight size={12}/></button><span>{((m.generation_ms||0)/1000).toFixed(1)}s generation</span>{m.local_execution&&<span title={`Model digest: ${m.local_execution.digest}`}>Local execution verified</span>}</div>}
                {m.role==='USER'&&m.status!=='complete'&&!busy&&<div className="retry"><p>{m.error || 'This saved turn was interrupted. Retry to finish it.'}</p><button onClick={()=>send(m)}>Retry saved message</button>{m.status==='recall_failed'&&<button onClick={()=>send(m,true)}>Continue without recall</button>}</div>}
              </div>
            })}
            {busy&&<div className="thinking" role="status"><LoaderCircle className="spin" size={16}/> Saving / preparing your answer…</div>}
          </div>
          <form className="composer" onSubmit={e=>{e.preventDefault();send();}}><div className="input-wrap"><textarea aria-label="Message" placeholder="Tell me a little about yourself…" value={text} maxLength={2000} disabled={busy || !!unfinished} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}/><button className="send" aria-label="Send message" disabled={busy||!!unfinished||!text.trim()||!providerReady}><ArrowUp size={19}/></button></div><p>Chats are saved in Redis Cloud. {selectedProvider?.label || 'Selected provider'} answers; OpenAI embeds; Redis-managed AI extracts memories.</p></form>
        </section>
        <aside className="evidence" aria-label="Memory evidence"><div className="evidence-heading"><Database size={18}/><h2>Memory & evidence</h2></div><p className="evidence-intro">See the context supplied to the model, and where it came from.</p>
          {state?.memory_changes_pending ? <div className="notice">{state.memory_changes_pending} memory change(s) waiting for cloud sync.</div> : null}
          {evidence&&<details className="service-inspector"><summary>Services for this answer</summary><p>Answer: {evidence.provider} · {evidence.model}</p><p>RedisVL + OpenAI embeddings: {evidence.recall_bypassed?'bypassed':`${evidence.recall_ms || 0} ms · ${supplied.length} memories`}</p><p>Generation: {evidence.generation_ms || 0} ms</p><p>Agent Memory: see each turn's background sync status.</p><p>LangCache: bypassed — personal chat</p><p>Context Retriever: not integrated</p></details>}
          <div className="section-label">MEMORIES SUPPLIED <span>{supplied.length}</span></div>
          {supplied.length?supplied.map(memoryCard):<div className="empty-memory"><div className="empty-symbol"><Database size={21}/></div><strong>{evidence?.recall_bypassed?'Recall was bypassed':'No memories supplied'}</strong><p>{evidence?'This answer did not receive saved personal memories.':'Send a message to inspect the context for its answer.'}</p></div>}
          <label className="memory-filter">Search memories<input aria-label="Search memories" value={query} onChange={e=>setQuery(e.target.value)}/></label><label className="memory-filter">Category<select aria-label="Memory category filter" value={category} onChange={e=>setCategory(e.target.value)}><option value="all">All categories</option>{categories.map(c=><option key={c} value={c}>{c.replaceAll('_',' ')}</option>)}</select></label>
          <div className="section-label saved-label">SAVED IN REDIS <span>{state?.memories.length || 0}</span></div>
          {state?.memories.length?state.memories.filter(m=>(category==='all'||(m.category||'about_me')===category)&&[m.text,...(m.people||[])].join(' ').toLowerCase().includes(query.toLowerCase())).map(memoryCard):<p className="quiet">Nothing saved yet. Extracted facts appear below for source review when automatic verification is unavailable.</p>}
          {!!supplied.length&&state?.memories.every(m=>supplied.some(x=>x.id===m.id))&&<p className="quiet">All saved memories are shown above.</p>}
          <div className="section-label saved-label">NEEDS SOURCE REVIEW <span>{state?.candidates?.length || 0}</span></div>{state?.candidates?.map(c=><CandidateReview key={c.id+ c.version} candidate={c} onDone={refresh} onError={setError}/>)}
          <div className="how-it-works"><div className="section-label">HOW MEMORY WORKS</div><ol><li><span>1</span> Your conversation is saved.</li><li><span>2</span> Agent Memory extracts a fact.</li><li><span>3</span> RedisVL retrieves it next time.</li></ol><p>Extraction can take around 5 minutes. “Pending” does not mean saved.</p></div>
          <details className="service-inspector"><summary>Non-personal cache example</summary><label className="review-check"><input type="checkbox" role="switch" aria-label="LangCache" checked={cacheEnabled} disabled={busy} onChange={e=>{setCacheEnabled(e.target.checked);setCacheResult(null);}}/>LangCache {cacheEnabled?'on':'off'}</label><p>Fixed public question: the capital of France. No chat content or memories are sent. Off: call the model without reading or writing the cache. On: reuse a matching cached answer or call the model on a miss. Switching off preserves existing entries.</p><button disabled={busy||!providerReady} onClick={()=>cacheExample(0)}>Run example</button> <button disabled={busy||!providerReady} onClick={()=>cacheExample(1)}>Try paraphrase</button>{cacheResult&&<p role="status">{cacheResult.status}: {cacheResult.text} {cacheResult.cache_ms!==undefined&&`Cache ${cacheResult.cache_ms} ms · generation ${cacheResult.generation_ms} ms`}</p>}</details>
          <div className="scope-note">Personal answers bypass LangCache<br/>Context Retriever integration pending</div>
        </aside>
      </div>
    </main>
    {uploadOpen&&state&&<DocumentImport existing={state.memories} generation={state.generation} api={api} onClose={()=>setUploadOpen(false)} onSaved={refresh}/>}
    {documentSource&&<div className="modal-backdrop"><section className="modal document-import" role="dialog" aria-modal="true" aria-labelledby="document-source-title"><button className="close" aria-label="Close document source" onClick={()=>setDocumentSource(null)}>×</button><h2 id="document-source-title">Document source</h2><p>{state?.documents?.find(d=>d.id===documentSource.document_id)?.filename} · {documentSource.source_section} · line {documentSource.source_line}</p><blockquote>{documentSource.source_text}</blockquote>{documentSource.source_notes?.map((n,i)=><p key={i}>{n}</p>)}<p>This citation points to the uploaded profile, not the original conversations it mentions.</p><p>Approved memory: {documentSource.text}</p></section></div>}
    {editing&&<div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="edit-title"><button className="close" aria-label="Close memory editor" onClick={()=>setEditing(null)}><X size={18}/></button><h2 id="edit-title">{deleting?'Delete memory':'Correct memory'}</h2><p>The change applies to future recall immediately. Cloud cleanup runs in the background. Existing transcripts remain visible, but prior chat history is excluded from future answers. Pending extraction and unreviewed candidates are retired; other accepted memories remain available.</p>{deleting?<p>{editing.text}</p>:<label>Corrected fact<textarea aria-label="Corrected fact" value={editText} maxLength={4000} onChange={e=>setEditText(e.target.value)}/></label>}<button disabled={busy||(!deleting&&!editText.trim())} onClick={changeMemory}>{deleting?'Delete this memory':'Save correction'}</button></section></div>}
    {resetOpen&&<div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="reset-title"><button className="close" aria-label="Close reset dialog" onClick={()=>setResetOpen(false)}><X size={18}/></button><RotateCcw size={24}/><h2 id="reset-title">Start with an empty memory</h2><p>This clears this application’s conversations and memories from recall. Cloud cleanup runs in the background and remains visible until verified. Other Redis data and Milestone 0 probes are untouched.</p><label>Type RESET to confirm<input autoFocus value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></label><button className="danger" onClick={reset} disabled={busy||confirmation!=='RESET'}>Reset this demo</button></section></div>}
  </div>
}



function CandidateReview({candidate:c,onDone,onError}:{candidate:Candidate;onDone:()=>Promise<unknown>;onError:(error:string)=>void}) {
  const [source,setSource]=useState(''); const [category,setCategory]=useState('about_me');
  const [people,setPeople]=useState(''); const [confirmed,setConfirmed]=useState(false); const [busy,setBusy]=useState(false);
  async function submit(accept:boolean){setBusy(true);try{await api(`/candidates/${c.id}/review`,{version:c.version,source_id:source,category,people:people.split(',').map(p=>p.trim()).filter(Boolean),accept});await onDone();}catch(e){onError((e as Error).message);}finally{setBusy(false);}}
  return <article className="memory-card review-card"><div className="section-label">NOT USED FOR RECALL</div><p>{c.text}</p>
    <label className="memory-filter">Supporting user message<select aria-label="Supporting user message" value={source} onChange={e=>{setSource(e.target.value);setConfirmed(false);}}><option value="">Select the source…</option>{c.sources.map(s=><option key={s.message_id} value={s.message_id}>{s.text.slice(0,100)}</option>)}</select></label>
    {source&&<blockquote>{c.sources.find(s=>s.message_id===source)?.text}</blockquote>}
    <label className="memory-filter">Category<select value={category} onChange={e=>setCategory(e.target.value)}>{categories.map(x=><option key={x} value={x}>{x.replaceAll('_',' ')}</option>)}</select></label>
    <label className="memory-filter">People (optional, comma separated)<input maxLength={400} value={people} onChange={e=>setPeople(e.target.value)}/></label>
    <label className="review-check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/> I confirm this is a true fact supported by my selected message, not a hypothetical or an assistant's suggestion.</label>
    <button disabled={busy||!source||!confirmed} onClick={()=>submit(true)}>Confirm fact & source</button> <button disabled={busy} onClick={()=>submit(false)}>Dismiss</button>
  </article>
}

function PrivateChat({providers,onExit}:{providers:Provider[];onExit:()=>void}) {
  const [provider,setProvider]=useState(providers.find(p=>p.available)?.id || 'openai');
  const [models,setModels]=useState<Record<string,string>>(Object.fromEntries(providers.map(p=>[p.id,p.default_model])));
  const [messages,setMessages]=useState<{role:string;text:string}[]>([]); const [text,setText]=useState('');
  const [busy,setBusy]=useState(false); const [error,setError]=useState('');
  const request=useRef<AbortController|null>(null);
  useEffect(()=>{const timer=setTimeout(onExit,30*60*1000);return()=>{clearTimeout(timer);request.current?.abort();};},[]);
  async function send(){if(!text.trim()||busy)return;const history=[...messages,{role:'USER',text:text.trim()}];setBusy(true);setError('');
    const controller=new AbortController();request.current=controller;
    try{const response=await fetch('/api/private/turns',{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Request':'1'},body:JSON.stringify({history,provider,model:models[provider]}),signal:controller.signal});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Private request failed.');setMessages([...history,{role:'ASSISTANT',text:data.text}]);setText('');}catch(e){if(!controller.signal.aborted)setError((e as Error).message);}finally{if(!controller.signal.aborted)setBusy(false);}}
  return <main className="private-chat"><header><div><span className="eyebrow">PRIVATE CHAT · NOT SAVED</span><h1>Only this conversation.</h1></div><button onClick={onExit}>Close & discard</button></header>
    <div className="notice">No Redis reads or writes, saved memory, extraction, or cache. Only the selected answering provider receives this conversation; its own processing and retention policies still apply. Closing, reloading, or 30 minutes discards this session. Browser/process memory is not a promise of forensic erasure.</div>
    <div className="model-selectors"><label>Provider<select value={provider} disabled={busy} onChange={e=>setProvider(e.target.value)}>{providers.filter(p=>p.available).map(p=><option value={p.id} key={p.id}>{p.label}</option>)}</select></label><label>Model<select value={models[provider]} disabled={busy} onChange={e=>setModels({...models,[provider]:e.target.value})}>{providers.find(p=>p.id===provider)?.models.map(m=><option key={m}>{m}</option>)}</select></label></div>
    <div className="messages">{messages.map((m,i)=><div className={'message '+m.role.toLowerCase()} key={i}><div className="message-label">{m.role}</div><div className="bubble">{m.text}</div></div>)}</div>
    {error&&<div role="alert" className="alert">{error}</div>}<form className="composer" onSubmit={e=>{e.preventDefault();send();}}><div className="input-wrap"><textarea aria-label="Private message" value={text} maxLength={2000} disabled={busy} onChange={e=>setText(e.target.value)}/><button disabled={busy||!text.trim()}>Send</button></div><p>{busy?'Generating privately…':'History exists only in this active page.'}</p></form>
  </main>
}
function Root(){const [privateProviders,setPrivateProviders]=useState<Provider[]|null>(null);return privateProviders?<PrivateChat providers={privateProviders} onExit={()=>setPrivateProviders(null)}/>:<App onPrivate={setPrivateProviders}/>;}
createRoot(document.getElementById('root')!).render(<Root/>);
