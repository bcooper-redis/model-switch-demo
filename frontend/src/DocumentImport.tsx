import React, {useState} from 'react';

type Passage={id:string;line:number;text:string};
type Section={id:string;title:string;notes:string[];passages:Passage[];recommended:boolean};
type Preview={filename:string;content_hash:string;sections:Section[]};
const categories=['about_me','family','interests','experiences','current_life'];
export function DocumentImport({generation,existing,onClose,onSaved,api}:{generation:string;existing:{text:string}[];onClose:()=>void;onSaved:()=>Promise<unknown>;api:(path:string,body?:unknown)=>Promise<any>}) {
  const [previewGeneration,setPreviewGeneration]=useState(generation);
  const [file,setFile]=useState<{filename:string;text:string}|null>(null);
  const [preview,setPreview]=useState<Preview|null>(null);
  const [selected,setSelected]=useState<Record<string,boolean>>({});
  const [edits,setEdits]=useState<Record<string,string>>({});
  const [groups,setGroups]=useState<Record<string,string>>({});
  const [confirmed,setConfirmed]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const [result,setResult]=useState<{queued:number;skipped:number}|null>(null);
  async function load(f:File){setBusy(true);setError('');setPreview(null);setResult(null);setConfirmed(false);setFile(null);setPreviewGeneration(generation);
    try{if(!f.name.toLowerCase().endsWith('.txt')||f.size>200000)throw new Error('Choose a UTF-8 .txt file up to 200 KB.');
      const text=new TextDecoder('utf-8',{fatal:true}).decode(await f.arrayBuffer());const payload={filename:f.name,text};
      const p:Preview=await api('/documents/preview',payload);setFile(payload);setPreview(p);
      setSelected(Object.fromEntries(p.sections.flatMap(s=>s.passages.map(p=>[p.id,s.recommended]))));
      setEdits(Object.fromEntries(p.sections.flatMap(s=>s.passages.map(p=>[p.id,p.text]))));
      setGroups(Object.fromEntries(p.sections.flatMap(s=>s.passages.map(p=>[p.id,s.title==='FAMILY'?'family':s.title.includes('INTEREST')?'interests':'about_me']))));
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  const count=Object.values(selected).filter(Boolean).length;
  async function save(){if(!file||!preview)return;setBusy(true);setError('');try{
    const selections=preview.sections.flatMap(s=>s.passages).filter(p=>selected[p.id]).map(p=>({passage_id:p.id,text:edits[p.id],category:groups[p.id]}));
    const r=await api('/documents/approve',{...file,content_hash:preview.content_hash,generation:previewGeneration,selections});setResult(r);setFile(null);setPreview(null);setEdits({});setSelected({});await onSaved();
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <div className="modal-backdrop"><section className="modal document-import" role="dialog" aria-modal="true" aria-labelledby="upload-title">
    <h2 id="upload-title">Bring your context with you</h2><button className="close" aria-label="Close document import" disabled={busy} onClick={onClose}>×</button>
    <p>Preview stays in this page and the local server request. Saving sends approved facts to Redis Cloud Agent Memory and OpenAI embeddings. Retrieved context can later be sent to your selected answering provider. Unselected passages are not saved. No LangCache or Context Retriever connection is needed.</p>
    {!result&&<label>Choose a text profile<input type="file" aria-label="Upload text profile" accept=".txt,text/plain" disabled={busy} onChange={e=>{const f=e.target.files?.[0];if(f)load(f);}}/></label>}
    {error&&<p role="alert">{error}</p>}{busy&&<p role="status">Preparing your document…</p>}
    {result&&<div role="status"><h3>{result.queued} memories queued</h3><p>{result.skipped} previously imported passages skipped. Memories become eligible for recall after sync succeeds. Watch the memory panel for pending status, then start a fresh conversation.</p><button onClick={onClose}>Return to demo</button></div>}
    {preview&&<><p><strong>{preview.filename}</strong> · {count} facts selected. Professional sections and working preferences are selected initially. Review the wording and preserve historical or uncertain qualifications.</p>
      <button type="button" disabled={busy||preview.sections.every(s=>s.passages.every(p=>selected[p.id]))} onClick={()=>{setSelected(Object.fromEntries(preview.sections.flatMap(s=>s.passages.map(p=>[p.id,true]))));setConfirmed(false);}}>Select all memories</button>
      <details><summary>Compare with {existing.length} saved memories</summary><p>Imports add facts; they do not replace existing ones. Exclude conflicting passages and correct the existing memory first.</p>{existing.map((m,i)=><blockquote key={i}>{m.text}</blockquote>)}</details><div className="document-sections">{preview.sections.map(s=><details key={s.id}><summary>{s.title} · {s.passages.filter(p=>selected[p.id]).length}/{s.passages.length} selected</summary>
        <label className="review-check"><input type="checkbox" aria-label={'Select section '+s.title} checked={s.passages.every(p=>selected[p.id])} onChange={e=>{setSelected({...selected,...Object.fromEntries(s.passages.map(p=>[p.id,e.target.checked]))});setConfirmed(false);}}/>Include this section</label>
        {s.notes.map((n,i)=><p className="notice" key={i}>{n}</p>)}
        {s.passages.map(p=><article className="import-passage" key={p.id}><label className="review-check"><input type="checkbox" aria-label={'Include line '+p.line} checked={!!selected[p.id]} onChange={e=>{setSelected({...selected,[p.id]:e.target.checked});setConfirmed(false);}}/>Line {p.line}</label><blockquote>{p.text}</blockquote>
          {selected[p.id]&&<><label>Memory to save<textarea aria-label={'Memory at line '+p.line} maxLength={4000} value={edits[p.id]} onChange={e=>{setEdits({...edits,[p.id]:e.target.value});setConfirmed(false);}}/></label><label>Category<select value={groups[p.id]} onChange={e=>setGroups({...groups,[p.id]:e.target.value})}>{categories.map(c=><option key={c} value={c}>{c.replaceAll('_',' ')}</option>)}</select></label></>}
        </article>)}
      </details>)}</div>
      <label className="review-check"><input type="checkbox" aria-label="Confirm selected document facts" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I reviewed the selected facts and their qualifications. Save these as my approved context.</label>
      <button className="new-chat" disabled={busy||!confirmed||!count||Object.keys(selected).some(id=>selected[id]&&!edits[id]?.trim())} onClick={save}>Save {count} approved memories</button>
    </>}
  </section></div>
}
