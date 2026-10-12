const API = import.meta.env.VITE_API_URL || '/api/v1';
export async function api<T=any>(path:string, init?:RequestInit):Promise<T>{
 const headers=new Headers(init?.headers||{});
 const token=sessionStorage.getItem('sim_session');
 if(token)headers.set('Authorization',`Bearer ${token}`);
 if(init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type'))headers.set('Content-Type','application/json');
 const r=await fetch(`${API}${path}`,{...init,headers});
 if(!r.ok){const body=await r.text(); if(r.status===401)window.dispatchEvent(new Event('sim-auth-expired')); throw new Error(body)}
 return r.json();
}
export async function download(path:string,filename:string){
 const r=await fetch(`${API}${path}`,{headers:{Authorization:`Bearer ${sessionStorage.getItem('sim_session')||''}`}});
 if(!r.ok)throw new Error(await r.text());
 const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
