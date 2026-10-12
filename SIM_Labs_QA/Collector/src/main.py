from __future__ import annotations
import json, shutil, subprocess, tempfile, uuid, zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

APP_VERSION = "0.5.0-integrado"
BASE = Path(__file__).resolve().parent.parent
# Em EXE one-file do PyInstaller, __file__ aponta para uma pasta temporária.
# Persistimos feedbacks/configurações em LOCALAPPDATA para não perder dados ao fechar.
if getattr(__import__("sys"), "frozen", False):
    DATA = Path(__import__("os").environ.get("LOCALAPPDATA", str(Path.home()))) / "NexGranaUpdateCollector"
else:
    DATA = BASE / "data"
STORE = DATA / "collector.json"
SETTINGS = DATA / "settings.json"
DRAFT = DATA / "draft.json"
DEFAULT = {
    "product": "NexGrana",
    "version_under_test": "0.24.0",
    "reporter": "Mafra",
    "source": "internal_qa",
    "max_upload_mb": 450,
    "state_file": "",
    "sim_labs_endpoint": ""
}
KINDS = ["Bug / Feedback", "Melhoria"]
CATEGORIES = ["Bug / Problema","Melhoria do app","Nova funcionalidade","UX/UI","Performance","Banco / Supabase","Nex / IA","Achados","Administração","Segurança","Outro"]
PRIORITIES = ["P0 - Bloqueador","P1 - Crítico","P2 - Relevante","P3 - Refinamento"]
PLATFORMS = ["Windows","Android","iOS","Web","Multiplataforma"]
STATUSES = ["Aberto","Em análise","Resolvido","Descartado"]
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi"}

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def safe_name(s): return "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip().replace(" ", "_") or "arquivo"
def mb(n): return f"{n / (1024*1024):.1f} MB"
def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def ffmpeg_ready():
    return shutil.which("ffmpeg") and shutil.which("ffprobe")

def split_video(src: Path, out_dir: Path, target_bytes: int):
    if src.stat().st_size <= target_bytes:
        return [src]
    if not ffmpeg_ready():
        raise RuntimeError(f"{src.name} tem {mb(src.stat().st_size)}. Instale FFmpeg para dividir vídeos grandes automaticamente.")
    out_dir.mkdir(parents=True, exist_ok=True)
    pr = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(src)], capture_output=True, text=True, check=True)
    duration = max(float(pr.stdout.strip()), 1)
    bps = src.stat().st_size / duration
    seg_seconds = max(8, int((target_bytes * 0.82) / max(bps, 1)))
    pattern = out_dir / f"{src.stem}_part_%03d.mp4"
    subprocess.run(["ffmpeg","-y","-i",str(src),"-map","0","-c","copy","-f","segment","-reset_timestamps","1","-segment_time",str(seg_seconds),str(pattern)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    parts = sorted(out_dir.glob(f"{src.stem}_part_*.mp4"))
    if not parts:
        raise RuntimeError("FFmpeg não gerou as partes do vídeo.")
    return parts

class Collector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NexGrana Update Collector — SIM Labs Bridge")
        self.geometry("1280x820")
        self.minsize(1050, 680)
        DATA.mkdir(exist_ok=True)
        self.items = load_json(STORE, [])
        self.settings = load_json(SETTINGS, DEFAULT.copy())
        for k, v in DEFAULT.items(): self.settings.setdefault(k, v)
        self.editing_id = None
        self.attachments = []
        self._sync_running = False
        self.build_ui()
        self.refresh_tree()
        self.after(2000, self.autosave_draft)

    def build_ui(self):
        top = ttk.Frame(self, padding=8); top.pack(fill="x")
        ttk.Label(top, text="NexGrana Update Collector", font=("Segoe UI",16,"bold")).pack(side="left")
        ttk.Label(top, text=f"SIM Labs local v{APP_VERSION}").pack(side="left", padx=8)
        ttk.Button(top, text="Gerar ZIP para Work", command=self.export_work).pack(side="right")
        ttk.Button(top, text="Abrir último ZIP", command=self.open_last_export).pack(side="right", padx=4)
        ttk.Button(top, text="Abrir SIM Labs QA", command=self.open_sim_labs).pack(side="right", padx=4)
        ttk.Button(top, text="Enviar para a Central", command=self.send_to_central).pack(side="right", padx=4)
        self.last_export_dir = None

        bar = ttk.Frame(self, padding=(8,0,8,6)); bar.pack(fill="x")
        self.bridge_status = tk.StringVar(value="Central: envio pelo botão · anexos e IDs preservados")
        ttk.Label(bar, textvariable=self.bridge_status).pack(side="right")
        self.summary = tk.StringVar(); ttk.Label(bar, textvariable=self.summary).pack(side="left")
        self.version = tk.StringVar(value=self.settings["version_under_test"])
        ttk.Entry(bar, textvariable=self.version, width=16).pack(side="right")
        ttk.Label(bar, text="Versão em teste:").pack(side="right")

        pane = ttk.Panedwindow(self, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left, right = ttk.Frame(pane), ttk.Frame(pane); pane.add(left, weight=2); pane.add(right, weight=3)

        filt = ttk.Frame(left); filt.pack(fill="x", pady=(0,5))
        self.search = tk.StringVar(); ttk.Entry(filt, textvariable=self.search).pack(side="left", fill="x", expand=True)
        self.search.trace_add("write", lambda *a: self.refresh_tree())
        self.filter_status = tk.StringVar(value="Todos")
        ttk.Combobox(filt, textvariable=self.filter_status, values=["Todos"]+STATUSES, state="readonly", width=13).pack(side="left", padx=4)
        self.filter_status.trace_add("write", lambda *a: self.refresh_tree())

        cols = ("n","tipo","prio","tela","titulo","status")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended")
        widths = (55,110,105,100,250,90)
        for c,w in zip(cols,widths): self.tree.heading(c,text=c.upper()); self.tree.column(c,width=w,anchor="w")
        self.tree.pack(fill="both", expand=True); self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        btns = ttk.Frame(left); btns.pack(fill="x", pady=5)
        ttk.Button(btns,text="Editar",command=self.edit_selected).pack(side="left")
        ttk.Button(btns,text="Duplicar",command=self.duplicate_selected).pack(side="left",padx=3)
        ttk.Button(btns,text="Resolvido",command=self.resolve_selected).pack(side="left")
        ttk.Button(btns,text="Selecionar visíveis",command=self.select_visible).pack(side="right", padx=3)
        ttk.Button(btns,text="Excluir selecionados",command=self.delete_selected).pack(side="right")

        form = ttk.Frame(right, padding=(10,0)); form.pack(fill="both", expand=True); form.columnconfigure(1, weight=1)
        self.kind = tk.StringVar(value=KINDS[0]); self.titlev = tk.StringVar(); self.category = tk.StringVar(value=CATEGORIES[0]); self.priority = tk.StringVar(value=PRIORITIES[2]); self.platform = tk.StringVar(value=PLATFORMS[0]); self.screen = tk.StringVar(); self.status = tk.StringVar(value=STATUSES[0])
        rows = [("Tipo",self.kind,KINDS),("Título",self.titlev,None),("Categoria",self.category,CATEGORIES),("Prioridade",self.priority,PRIORITIES),("Plataforma",self.platform,PLATFORMS),("Tela / área",self.screen,None),("Status",self.status,STATUSES)]
        for i,(label,var,vals) in enumerate(rows):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky="w",pady=3)
            w = ttk.Combobox(form,textvariable=var,values=vals,state="readonly") if vals else ttk.Entry(form,textvariable=var)
            w.grid(row=i,column=1,sticky="ew",pady=3)

        self.texts = {}
        for j,(key,label) in enumerate([("description","Descrição / problema"),("current","Comportamento atual"),("expected","Comportamento esperado"),("solution","Ideia de solução"),("notes","Observações")], start=7):
            ttk.Label(form,text=label).grid(row=j,column=0,sticky="nw",pady=3)
            t = tk.Text(form,height=3,wrap="word"); t.grid(row=j,column=1,sticky="nsew",pady=3); self.texts[key]=t

        ar = 12; ttk.Label(form,text="Evidências").grid(row=ar,column=0,sticky="nw")
        aw = ttk.Frame(form); aw.grid(row=ar,column=1,sticky="nsew")
        self.attach_list = tk.Listbox(aw,height=5); self.attach_list.pack(side="left",fill="both",expand=True)
        ab = ttk.Frame(aw); ab.pack(side="right",fill="y")
        ttk.Button(ab,text="Anexar",command=self.add_files).pack(fill="x",pady=1)
        ttk.Button(ab,text="Colar print",command=self.paste_image).pack(fill="x",pady=1)
        ttk.Button(ab,text="Remover",command=self.remove_attachment).pack(fill="x",pady=1)

        acts = ttk.Frame(form); acts.grid(row=13,column=0,columnspan=2,sticky="ew",pady=8)
        ttk.Button(acts,text="Salvar",command=lambda:self.save_item(False)).pack(side="left")
        ttk.Button(acts,text="Salvar e novo",command=lambda:self.save_item(True)).pack(side="left",padx=4)
        ttk.Button(acts,text="Limpar",command=self.clear_form).pack(side="left")
        ttk.Button(acts,text="Configurações / SIM Labs",command=self.open_settings).pack(side="right")

    def form_data(self):
        return {"kind":self.kind.get(),"title":self.titlev.get().strip(),"category":self.category.get(),"priority":self.priority.get(),"platform":self.platform.get(),"screen":self.screen.get().strip(),"status":self.status.get(),"description":self.texts["description"].get("1.0","end").strip(),"current":self.texts["current"].get("1.0","end").strip(),"expected":self.texts["expected"].get("1.0","end").strip(),"solution":self.texts["solution"].get("1.0","end").strip(),"notes":self.texts["notes"].get("1.0","end").strip(),"attachments":list(self.attachments)}

    def autosave_draft(self):
        try:
            d = self.form_data()
            if any([d["title"],d["description"],d["current"],d["expected"],d["attachments"]]): save_json(DRAFT,d)
        finally:
            self.after(2000,self.autosave_draft)

    def clear_form(self):
        self.editing_id=None; self.kind.set(KINDS[0]); self.titlev.set(""); self.category.set(CATEGORIES[0]); self.priority.set(PRIORITIES[2]); self.platform.set(PLATFORMS[0]); self.screen.set(""); self.status.set(STATUSES[0])
        for t in self.texts.values(): t.delete("1.0","end")
        self.attachments=[]; self.refresh_attachments()

    def load_form(self, item):
        self.kind.set(item.get("kind",KINDS[0])); self.titlev.set(item.get("title","")); self.category.set(item.get("category",CATEGORIES[0])); self.priority.set(item.get("priority",PRIORITIES[2])); self.platform.set(item.get("platform",PLATFORMS[0])); self.screen.set(item.get("screen","")); self.status.set(item.get("status",STATUSES[0]))
        for k,t in self.texts.items(): t.delete("1.0","end"); t.insert("1.0",item.get(k,""))
        self.attachments=list(item.get("attachments",[])); self.refresh_attachments()

    def next_number(self): return max([int(x.get("number",0)) for x in self.items]+[0])+1

    def save_item(self, new_after):
        d=self.form_data()
        if not d["title"]: messagebox.showwarning("Título","Informe um título."); return
        if self.editing_id:
            for x in self.items:
                if x["id"]==self.editing_id: x.update(d); x["updated_at"]=now(); break
        else:
            d.update({"id":str(uuid.uuid4()),"number":self.next_number(),"created_at":now(),"updated_at":now(),"source":self.settings.get("source"),"reporter":self.settings.get("reporter"),"product":self.settings.get("product"),"version":self.version.get().strip()}); self.items.append(d)
        self.settings["version_under_test"] = self.version.get().strip(); save_json(SETTINGS,self.settings); save_json(STORE,self.items); self.refresh_tree(); old=d["kind"]; self.clear_form(); self.kind.set(old if new_after else KINDS[0])

    def selected(self):
        s=self.tree.selection(); return next((x for x in self.items if s and x["id"]==s[0]),None)
    def edit_selected(self):
        x=self.selected();
        if x: self.editing_id=x["id"]; self.load_form(x)
    def duplicate_selected(self):
        x=self.selected();
        if not x:return
        y=dict(x); y["id"]=str(uuid.uuid4()); y["number"]=self.next_number(); y["title"]=y.get("title","")+" (cópia)"; y["status"]="Aberto"; y["created_at"]=y["updated_at"]=now(); self.items.append(y); save_json(STORE,self.items); self.refresh_tree()
    def resolve_selected(self):
        x=self.selected();
        if x: x["status"]="Resolvido"; x["updated_at"]=now(); save_json(STORE,self.items); self.refresh_tree()
    def select_visible(self):
        visible=self.tree.get_children()
        if visible:
            self.tree.selection_set(visible)
    def delete_selected(self):
        selected=set(self.tree.selection())
        rows=[item for item in self.items if item.get("id") in selected]
        if not rows:
            messagebox.showinfo("Selecione itens", "Selecione um ou mais itens na lista. Você pode filtrar antes e usar 'Selecionar visíveis'.")
            return
        preview="\n".join(f"#{item.get('number')} — {item.get('title')}" for item in rows[:5])
        if len(rows)>5:
            preview+=f"\n… e mais {len(rows)-5} item(ns)"
        if not messagebox.askyesno("Excluir selecionados", f"Excluir {len(rows)} item(ns)?\n\n{preview}"):
            return
        self.items=[item for item in self.items if item.get("id") not in selected]
        if self.editing_id in selected:
            self.clear_form()
        save_json(STORE,self.items)
        self.refresh_tree()

    def refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        q=self.search.get().lower().strip(); fs=self.filter_status.get()
        for x in sorted(self.items,key=lambda z:-int(z.get("number",0))):
            blob=" ".join(str(x.get(k,"")) for k in ["title","category","screen","description","priority"]).lower()
            if q and q not in blob: continue
            if fs!="Todos" and x.get("status")!=fs: continue
            self.tree.insert("","end",iid=x["id"],values=(f"#{x.get('number')}",x.get("kind"),x.get("priority"),x.get("screen"),x.get("title"),x.get("status")))
        bugs=sum(x.get("kind")=="Bug / Feedback" for x in self.items); imps=sum(x.get("kind")=="Melhoria" for x in self.items); opened=sum(x.get("status") not in ("Resolvido","Descartado") for x in self.items)
        self.summary.set(f"{len(self.items)} itens • {bugs} bugs/feedbacks • {imps} melhorias • {opened} abertos")

    def add_files(self):
        files=filedialog.askopenfilenames(title="Selecionar evidências",filetypes=[("Evidências","*.png *.jpg *.jpeg *.webp *.gif *.mp4 *.mov *.mkv *.avi *.txt *.log *.pdf"),("Todos","*.*")])
        for p in files:
            if p not in self.attachments:self.attachments.append(p)
        self.refresh_attachments()
    def paste_image(self):
        if ImageGrab is None: messagebox.showerror("Clipboard","Instale Pillow."); return
        d=ImageGrab.grabclipboard()
        if d is None: messagebox.showinfo("Clipboard","Nenhuma imagem no clipboard."); return
        if isinstance(d,list):
            for p in d:
                if p not in self.attachments:self.attachments.append(p)
        else:
            out=DATA/"clipboard"/f"clipboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"; out.parent.mkdir(exist_ok=True); d.save(out); self.attachments.append(str(out))
        self.refresh_attachments()
    def remove_attachment(self):
        s=self.attach_list.curselection()
        if s:self.attachments.pop(s[0]); self.refresh_attachments()
    def refresh_attachments(self):
        self.attach_list.delete(0,"end")
        for p in self.attachments:
            q=Path(p); self.attach_list.insert("end",q.name+(f" ({mb(q.stat().st_size)})" if q.exists() else " [ausente]"))

    def open_settings(self):
        w=tk.Toplevel(self); w.title("Configurações / SIM Labs"); w.geometry("760x390")
        f=ttk.Frame(w,padding=12); f.pack(fill="both",expand=True); f.columnconfigure(1,weight=1); vars_={}
        rows=[("Produto","product"),("Versão em teste","version_under_test"),("Responsável","reporter"),("Origem","source"),("Máx. por arquivo Work (MB)","max_upload_mb"),("NEXGRANA_ESTADO_ATUAL.md","state_file"),("Endpoint SIM Labs (consulta)","sim_labs_endpoint")]
        for r,(label,key) in enumerate(rows):
            ttk.Label(f,text=label).grid(row=r,column=0,sticky="w",pady=4); v=tk.StringVar(value=str(self.settings.get(key,""))); vars_[key]=v; ttk.Entry(f,textvariable=v).grid(row=r,column=1,sticky="ew",pady=4)
            if key=="state_file": ttk.Button(f,text="Selecionar",command=lambda vv=v:vv.set(filedialog.askopenfilename(filetypes=[("Markdown","*.md"),("Todos","*.*")]))).grid(row=r,column=2,padx=4)
        ttk.Label(f,text="Use Enviar para a Central. Neste pacote a conexão local é configurada ao iniciar o SIM Labs; nenhuma credencial é embutida.",wraplength=680).grid(row=len(rows),column=0,columnspan=3,sticky="w",pady=14)
        def save_settings():
            for k,v in vars_.items():
                val=v.get().strip()
                if k=="max_upload_mb":
                    try: val=max(50,min(490,int(val)))
                    except Exception: val=450
                self.settings[k]=val
            self.version.set(str(self.settings["version_under_test"])); save_json(SETTINGS,self.settings); w.destroy()
        ttk.Button(f,text="Salvar",command=save_settings).grid(row=len(rows)+1,column=2,sticky="e")

    def send_to_central(self):
        if self._sync_running:
            return
        if not self.items:
            messagebox.showinfo("Central", "Salve pelo menos um feedback antes de enviar.")
            return
        import threading, queue
        from sim_labs_bridge import send_snapshot
        snapshot = json.loads(json.dumps(self.items, ensure_ascii=False))
        release = self.version.get()
        self._sync_running = True
        self.bridge_status.set("Central: enviando feedbacks e evidências…")
        result_queue = queue.Queue()
        def work():
            try:
                result_queue.put((True, send_snapshot(snapshot, release)))
            except Exception as exc:
                result_queue.put((False, type(exc).__name__ + ": " + str(exc)))
        def check_result():
            try:
                ok, result = result_queue.get_nowait()
            except queue.Empty:
                self.after(150, check_result)
                return
            self._sync_running = False
            if ok:
                self.bridge_status.set(f"Central: {result['created']} novos · {result['updated']} atualizados · {result['duplicates']} reenvios")
                text = f"Envio concluído.\nNovos: {result['created']}\nAtualizados: {result['updated']}\nReenvios reconhecidos: {result['duplicates']}\nEvidências: {result['attachments']}"
                if result.get('omitted'):
                    text += "\n\nAnexos não enviados:\n" + "\n".join(result['omitted'])
                messagebox.showinfo("SIM Labs integrado", text)
            else:
                self.bridge_status.set("Central: envio pendente; dados locais preservados")
                messagebox.showerror("Envio para a central", result + "\nSe a central estiver desligada, inicie-a e envie novamente. Seus dados continuam salvos.")
        threading.Thread(target=work, daemon=True).start()
        self.after(150, check_result)

    def render_md(self, items, title):
        L=[f"# {title}","",f"Versão em teste: **{self.version.get()}**",""]
        for x in items:
            L += [f"## #{x.get('number')} — {x.get('title','')}","",f"- ID: `{x.get('id')}`",f"- Tipo: {x.get('kind')}",f"- Categoria: {x.get('category')}",f"- Prioridade: {x.get('priority')}",f"- Plataforma: {x.get('platform')}",f"- Tela/área: {x.get('screen') or 'não informada'}",f"- Status: {x.get('status')}","","### Descrição",x.get("description") or "_não informada_","","### Comportamento atual",x.get("current") or "_não informado_","","### Comportamento esperado",x.get("expected") or "_não informado_","","### Ideia de solução",x.get("solution") or "_não informada_","","### Observações",x.get("notes") or "_nenhuma_","","### Evidências"]
            L += [f"- `{p}`" for p in x.get("_export_evidence",[])] or ["- nenhuma"]
            L += ["","---",""]
        return "\n".join(L)

    def open_last_export(self):
        if not self.last_export_dir:
            messagebox.showinfo("Último ZIP", "Ainda não houve exportação nesta sessão.")
            return
        try:
            __import__("os").startfile(str(self.last_export_dir))
        except Exception as exc:
            messagebox.showerror("Abrir pasta", f"Não foi possível abrir a pasta:\n{exc}")

    def open_sim_labs(self):
        current = getattr(self, "sim_labs_window", None)
        if current is not None:
            try:
                if current.winfo_exists():
                    current.deiconify(); current.lift(); current.focus_force()
                    return
            except Exception:
                pass
        try:
            from sim_labs_ui import SimLabsWindow
            self.sim_labs_window = SimLabsWindow(
                self,
                DATA,
                product=self.settings.get("product", "NexGrana"),
                release=self.version.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("SIM Labs", f"Não foi possível abrir o console local:\n{type(exc).__name__}: {exc}")

    def export_work(self):
        if not self.items:
            messagebox.showwarning("Sem itens", "Cadastre e SALVE pelo menos um feedback ou melhoria antes de exportar.")
            return
        out_dir = filedialog.askdirectory(title="Escolha a pasta onde salvar os ZIPs para o Work", mustexist=True)
        if not out_dir:
            return
        staging = None
        try:
            try:
                max_mb = int(self.settings.get("max_upload_mb", 450))
            except Exception:
                max_mb = 450
            max_bytes = max_mb * 1024 * 1024
            video_target = int(max_bytes * 0.72)
            safe_limit = int(max_bytes * 0.92)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"NexGrana_Feedback_{safe_name(self.version.get())}_{stamp}"
            staging = Path(tempfile.mkdtemp(prefix="nexcollector_"))
            package = staging / base_name
            evdir = package / "evidencias"
            evdir.mkdir(parents=True)
            items = json.loads(json.dumps(self.items, ensure_ascii=False))
            missing, omitted_large = [], []

            for x in items:
                x["_export_evidence"] = []
                for j, raw in enumerate(x.get("attachments", []), 1):
                    src = Path(raw)
                    if not src.exists():
                        missing.append(str(src)); continue
                    prefix = f"{int(x.get('number',0)):03d}_{j:02d}_"
                    if src.suffix.lower() in VIDEO_EXTS and src.stat().st_size > video_target:
                        if not ffmpeg_ready():
                            omitted_large.append({"file": str(src), "reason": "video grande; FFmpeg não instalado"})
                            continue
                        parts = split_video(src, evdir / f"video_{int(x.get('number',0)):03d}_{j:02d}", video_target)
                    else:
                        parts = [src]
                    for part in parts:
                        if part.stat().st_size > safe_limit:
                            omitted_large.append({"file": str(part), "reason": f"arquivo individual maior que {max_mb} MB"})
                            continue
                        dst = evdir / (prefix + safe_name(part.name))
                        shutil.copy2(part, dst)
                        x["_export_evidence"].append(dst.relative_to(package).as_posix())

            bugs = [x for x in items if x.get("kind") == "Bug / Feedback"]
            improvements = [x for x in items if x.get("kind") == "Melhoria"]
            manifest = {
                "schema":"nexgrana.update_collector/0.3.1", "generated_at":now(),
                "collector_version":APP_VERSION, "product":self.settings.get("product"),
                "version_under_test":self.version.get(), "reporter":self.settings.get("reporter"),
                "source":self.settings.get("source"),
                "counts":{"total":len(items),"bugs_feedbacks":len(bugs),"improvements":len(improvements),
                          "open":sum(x.get("status") not in ("Resolvido","Descartado") for x in items)},
                "missing_attachments":missing, "omitted_large_attachments":omitted_large, "items":items
            }
            ingest = {
                "schema":"sim-labs.feedback-ingest/1.0", "generated_at":now(),
                "product":self.settings.get("product"), "release":self.version.get(),
                "source":"collector_internal",
                "records":[{"feedback_id":x.get("id"),"number":x.get("number"),"kind":x.get("kind"),
                            "severity":x.get("priority"),"category":x.get("category"),"platform":x.get("platform"),
                            "screen":x.get("screen"),"status":x.get("status"),"title":x.get("title"),
                            "evidence":x.get("_export_evidence",[]),"created_at":x.get("created_at"),
                            "updated_at":x.get("updated_at")} for x in items]
            }
            prompt = f"""# PROMPT_WORK — NexGrana Update Collector\n\nUse este pacote como entrada estruturada da rodada de QA do NexGrana {self.version.get()}.\n\n1. Leia manifest.json, SIM_LABS_INGEST.json, FEEDBACKS_E_BUGS.md, MELHORIAS_DO_APP.md e todas as evidências.\n2. Se houver NEXGRANA_ESTADO_ATUAL.md, trate-o como estado canônico.\n3. Analise imagens e vídeos, não só o texto.\n4. Preserve IDs dos itens.\n5. Diferencie bug, melhoria, duplicata, limitação externa e item resolvido.\n6. Para cada item: evidência → causa provável → módulo → risco → correção → teste → status.\n7. Não invente teste/build.\n8. Ao final liste tudo que melhorou, corrigiu, implementou, tudo que ainda falta e próximos passos.\n9. Gere saída compatível com ingestão posterior pelo SIM Labs.\n"""
            (package/"PROMPT_WORK.md").write_text(prompt, encoding="utf-8")
            (package/"FEEDBACKS_E_BUGS.md").write_text(self.render_md(bugs,"Feedbacks e Bugs"), encoding="utf-8")
            (package/"MELHORIAS_DO_APP.md").write_text(self.render_md(improvements,"Melhorias do App"), encoding="utf-8")
            (package/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2), encoding="utf-8")
            (package/"SIM_LABS_INGEST.json").write_text(json.dumps(ingest,ensure_ascii=False,indent=2), encoding="utf-8")
            if omitted_large:
                (package/"EVIDENCIAS_NAO_INCLUIDAS.md").write_text(
                    "# Evidências não incluídas\n\n" + "\n".join(f"- {x['file']} — {x['reason']}" for x in omitted_large),
                    encoding="utf-8")
            state = Path(str(self.settings.get("state_file","")).strip())
            if str(state) and state.exists():
                shutil.copy2(state, package/"NEXGRANA_ESTADO_ATUAL.md")
            else:
                (package/"NEXGRANA_ESTADO_ATUAL.md").write_text(
                    f"# NEXGRANA_ESTADO_ATUAL\n\nVersão em teste: {self.version.get()}\n\n> Estado canônico não selecionado no Collector.\n",
                    encoding="utf-8")

            metadata = [p for p in package.iterdir() if p.is_file()]
            evidence = [p for p in evdir.rglob("*") if p.is_file()]
            meta_size = sum(p.stat().st_size for p in metadata)
            groups, current, size = [], [], meta_size
            for p in sorted(evidence):
                if current and size + p.stat().st_size > safe_limit:
                    groups.append(current); current=[]; size=meta_size
                current.append(p); size += p.stat().st_size
            groups.append(current)

            outputs=[]
            for n, group in enumerate(groups, 1):
                suffix = "" if len(groups)==1 else f"_part{n:02d}"
                out = Path(out_dir) / f"{base_name}{suffix}.zip"
                with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                    for p in metadata: z.write(p,p.relative_to(package))
                    for p in group: z.write(p,p.relative_to(package))
                if not out.exists() or out.stat().st_size == 0:
                    raise RuntimeError(f"ZIP não foi criado corretamente: {out}")
                outputs.append(out)

            self.last_export_dir = Path(out_dir)
            shutil.rmtree(staging, ignore_errors=True); staging=None
            msg = "ZIP criado com sucesso em:\n\n" + str(self.last_export_dir) + "\n\n" +                   "\n".join(f"- {p.name} ({mb(p.stat().st_size)})" for p in outputs)
            if len(outputs)>1: msg += "\n\nEnvie TODAS as partes no mesmo chat do Work."
            if missing: msg += f"\n\nAtenção: {len(missing)} evidência(s) não encontrada(s)."
            if omitted_large: msg += f"\n\nAtenção: {len(omitted_large)} evidência(s) grande(s) não incluída(s). Veja EVIDENCIAS_NAO_INCLUIDAS.md dentro do ZIP."
            messagebox.showinfo("Exportação concluída", msg)
            try:
                __import__("os").startfile(str(self.last_export_dir))
            except Exception:
                pass
        except Exception as exc:
            try:
                log = DATA / "export_errors.log"
                with log.open("a", encoding="utf-8") as f:
                    f.write(f"[{now()}] {type(exc).__name__}: {exc}\n")
            except Exception:
                log = None
            messagebox.showerror(
                "Falha ao gerar ZIP",
                f"O ZIP não foi gerado.\n\nErro: {type(exc).__name__}: {exc}\n\n"
                + (f"Log: {log}" if log else "")
            )
        finally:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)

if __name__ == "__main__":
    Collector().mainloop()
