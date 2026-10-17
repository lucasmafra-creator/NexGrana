import {useState} from 'react';
import {api} from './api';

export default function RunnerReportUpload({releaseId,product,onImported}:{releaseId:string,product:string,onImported:()=>Promise<void>}) {
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 async function submit(file:File){
  if(!releaseId){setMessage('Selecione uma candidata antes de importar.');return}
  setBusy(true);setMessage('');
  try {
   if(file.size>3*1024*1024)throw new Error('Escolha um relatório JSON de até 3 MB.');
   const report=JSON.parse(await file.text());
   if(report?.schema!=='sim-labs.trusted-source-run/1.0')throw new Error('Schema do runner não reconhecido.');
   const form=new FormData();form.set('file',file);form.set('release_id',releaseId);form.set('product_slug',product);
   const evidence=await api('/evidence',{method:'POST',body:form});
   const run=await api(`/releases/${releaseId}/runner-reports`,{method:'POST',body:JSON.stringify({evidence_id:evidence.id})});
   setMessage(`Relatório ${run.duplicate?'já registrado':'importado'}: ${run.status}. Resultado de código; a instalação e o teste do EXE continuam pendentes.`);
   await onImported();
  } catch(error){setMessage(error instanceof SyntaxError?'JSON inválido.':error instanceof Error?error.message:'Não consegui importar. Confira a conexão e a autorização.');}
  finally{setBusy(false)}
 }
 return <section className="panel"><h2>Relatório do runner de código</h2>
  <p>Importe o JSON de uma execução manual em fonte confiável. Este resultado não comprova execução do build nem encerra missões.</p>
  <label className="upload">{busy?'Importando…':'Selecionar relatório JSON'}<input type="file" accept=".json,application/json" disabled={busy||!releaseId} onChange={event=>{const file=event.target.files?.[0];event.target.value='';if(file)void submit(file)}}/></label>
  <p role="status">{message||(!releaseId?'Selecione uma candidata em Releases & QA.':'O arquivo será guardado como evidência privada.')}</p>
 </section>
}
