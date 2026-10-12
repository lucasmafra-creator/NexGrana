from __future__ import annotations

import json
import shutil
import sys
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from sim_labs_core import MANUAL_CHECKS, import_feedback_package, inspect_build, render_report_markdown, run_source_tests


MANUAL_STATUSES = ["Não testado", "Passou", "Falhou", "Bloqueado", "Não se aplica"]
FEEDBACK_QA_STATUSES = ["Aguardando teste", "Em validação", "Validado pelo QA", "Falhou no QA", "Aguardando correção", "Resolvido confirmado"]


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


class SimLabsWindow(tk.Toplevel):
    """Private, local-only build intake and verification window."""

    def __init__(self, parent, data_dir: Path, product="NexGrana", release="0.24.0"):
        super().__init__(parent)
        self.title("SIM Labs — Build QA local")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.data_dir = Path(data_dir) / "sim_labs"
        self.build_dir = self.data_dir / "builds"
        self.report_dir = self.data_dir / "reports"
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.builds_path = self.data_dir / "builds.json"
        self.feedbacks_path = self.data_dir / "feedbacks.json"
        self.builds = _load_json(self.builds_path, [])
        self.feedbacks = _load_json(self.feedbacks_path, [])
        self.product = product
        self.release = release
        self.selected_build_id = None
        self.busy = False
        self._build_rows = {}
        self._feedback_rows = {}
        self._manual_rows = {}
        self._make_ui()
        self._refresh_builds()
        self._refresh_feedbacks()

    def _make_ui(self):
        header = ttk.Frame(self, padding=(12, 10, 12, 4))
        header.pack(fill="x")
        ttk.Label(header, text="SIM Labs", font=("Segoe UI", 19, "bold")).pack(side="left")
        ttk.Label(header, text="QA local • dados e builds ficam neste computador", foreground="#555").pack(side="left", padx=12)
        self.status = tk.StringVar(value="Pronto para receber um build.")
        ttk.Label(self, textvariable=self.status, padding=(12, 2)).pack(fill="x")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=8)
        self.build_tab = ttk.Frame(self.tabs, padding=10)
        self.feedback_tab = ttk.Frame(self.tabs, padding=10)
        self.check_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.build_tab, text="Builds e verificações")
        self.tabs.add(self.feedback_tab, text="Feedbacks")
        self.tabs.add(self.check_tab, text="Checklist de dispositivo")
        self._make_build_tab()
        self._make_feedback_tab()
        self._make_check_tab()

    def _make_build_tab(self):
        toolbar = ttk.Frame(self.build_tab)
        toolbar.pack(fill="x", pady=(0, 8))
        self.target = tk.StringVar(value="Detectar")
        ttk.Label(toolbar, text="Alvo:").pack(side="left")
        ttk.Combobox(toolbar, textvariable=self.target, state="readonly", width=18,
                     values=["Detectar", "Windows", "Android", "Multiplataforma"]).pack(side="left", padx=5)
        self.add_build_button = ttk.Button(toolbar, text="Importar build", command=self._choose_build)
        self.add_build_button.pack(side="left", padx=3)
        self.test_button = ttk.Button(toolbar, text="Executar testes do ZIP", command=self._run_tests, state="disabled")
        self.test_button.pack(side="left", padx=3)
        ttk.Button(toolbar, text="Salvar relatório", command=self._save_report).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Abrir pasta local", command=self._open_data_folder).pack(side="right")

        body = ttk.Panedwindow(self.build_tab, orient="horizontal")
        body.pack(fill="both", expand=True)
        left, right = ttk.Frame(body), ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)
        columns = ("target", "type", "version", "result", "sha")
        self.build_tree = ttk.Treeview(left, columns=columns, show="headings", height=18, selectmode="browse")
        for column, label, width in zip(columns, ("Alvo", "Tipo", "Versão", "Resultado", "SHA-256"), (85, 130, 85, 95, 115)):
            self.build_tree.heading(column, text=label)
            self.build_tree.column(column, width=width, anchor="w")
        self.build_tree.pack(fill="both", expand=True)
        self.build_tree.bind("<<TreeviewSelect>>", self._select_build)
        ttk.Label(right, text="Resumo das verificações", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.build_detail = tk.Text(right, wrap="word", height=22, state="disabled")
        self.build_detail.pack(fill="both", expand=True, pady=(4, 0))

        note = ttk.Label(self.build_tab,
                         text="Importar e analisar não abre o app. Testes do código só rodam após confirmação; instalação e navegação no Android/Windows ficam no checklist.",
                         wraplength=1050, foreground="#555")
        note.pack(fill="x", pady=(8, 0))

    def _make_feedback_tab(self):
        toolbar = ttk.Frame(self.feedback_tab)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Importar ZIP(s) do Collector", command=self._import_feedbacks).pack(side="left")
        ttk.Label(toolbar, text="Importações repetidas são mescladas pelo ID original.", foreground="#555").pack(side="left", padx=10)
        columns = ("id", "number", "priority", "title", "collector", "qa")
        self.feedback_tree = ttk.Treeview(self.feedback_tab, columns=columns, show="headings", height=20)
        widths = (245, 45, 115, 280, 100, 150)
        labels = ("ID preservado", "Nº", "Prioridade", "Título", "Collector", "QA SIM Labs")
        for column, label, width in zip(columns, labels, widths):
            self.feedback_tree.heading(column, text=label)
            self.feedback_tree.column(column, width=width, anchor="w")
        self.feedback_tree.pack(fill="both", expand=True)
        self.feedback_tree.bind("<<TreeviewSelect>>", self._select_feedback)
        actions = ttk.Frame(self.feedback_tab)
        actions.pack(fill="x", pady=(8, 0))
        self.feedback_qa_status = tk.StringVar(value=FEEDBACK_QA_STATUSES[0])
        ttk.Label(actions, text="Status de validação:").pack(side="left")
        ttk.Combobox(actions, textvariable=self.feedback_qa_status, state="readonly", width=26,
                     values=FEEDBACK_QA_STATUSES).pack(side="left", padx=5)
        ttk.Button(actions, text="Salvar status QA", command=self._save_feedback_status).pack(side="left")
        ttk.Label(actions, text="Teste aprovado não fecha o feedback automaticamente.", foreground="#555").pack(side="right")

    def _make_check_tab(self):
        ttk.Label(self.check_tab, text="A validação visual depende de um dispositivo/build real. Registre cada resultado por build.",
                  wraplength=980).pack(anchor="w", pady=(0, 8))
        self.manual_tree = ttk.Treeview(self.check_tab, columns=("status",), show="tree headings", height=17)
        self.manual_tree.heading("#0", text="Verificação manual")
        self.manual_tree.heading("status", text="Resultado")
        self.manual_tree.column("#0", width=760, anchor="w")
        self.manual_tree.column("status", width=170, anchor="w")
        self.manual_tree.pack(fill="both", expand=True)
        self.manual_tree.bind("<<TreeviewSelect>>", self._select_manual_check)
        actions = ttk.Frame(self.check_tab)
        actions.pack(fill="x", pady=(8, 0))
        self.manual_status = tk.StringVar(value=MANUAL_STATUSES[0])
        self.manual_notes = tk.StringVar()
        ttk.Label(actions, text="Resultado:").pack(side="left")
        ttk.Combobox(actions, textvariable=self.manual_status, state="readonly", width=18,
                     values=MANUAL_STATUSES).pack(side="left", padx=5)
        ttk.Entry(actions, textvariable=self.manual_notes).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(actions, text="Salvar etapa", command=self._save_manual_check).pack(side="right")

    def _set_detail(self, text):
        self.build_detail.configure(state="normal")
        self.build_detail.delete("1.0", "end")
        self.build_detail.insert("1.0", text)
        self.build_detail.configure(state="disabled")

    def _refresh_builds(self, select_id=None):
        for item in self.build_tree.get_children():
            self.build_tree.delete(item)
        self._build_rows.clear()
        for build in sorted(self.builds, key=lambda x: x.get("added_at", ""), reverse=True):
            build_id = build.get("id")
            report = build.get("inspection") or {}
            target = report.get("target") or build.get("target") or "Detectar"
            values = (target, report.get("artifact_type", "—"), report.get("version") or "—",
                      report.get("overall", "—"), (report.get("sha256") or "")[:12])
            self.build_tree.insert("", "end", iid=build_id, values=values)
            self._build_rows[build_id] = build
        wanted = select_id or self.selected_build_id
        if wanted and wanted in self._build_rows:
            self.build_tree.selection_set(wanted)
            self.build_tree.focus(wanted)
            self._display_build(self._build_rows[wanted])
        elif self.builds:
            row = self.builds[-1]
            self.selected_build_id = row.get("id")
            self._display_build(row)
        else:
            self.selected_build_id = None
            self._set_detail("Importe um .zip de código, .apk, .aab ou executável Windows para iniciar a verificação.")
        self._refresh_manual_checks()

    def _refresh_feedbacks(self):
        for item in self.feedback_tree.get_children():
            self.feedback_tree.delete(item)
        self._feedback_rows.clear()
        for record in sorted(self.feedbacks, key=lambda x: (str(x.get("number") or "0").zfill(6), x.get("title", ""))):
            record_id = record.get("feedback_id")
            self.feedback_tree.insert("", "end", iid=record_id, values=(
                record_id, record.get("number") or "—", record.get("priority") or "—",
                record.get("title") or "", record.get("collector_status") or "Aberto",
                record.get("qa_status") or FEEDBACK_QA_STATUSES[0],
            ))
            self._feedback_rows[record_id] = record

    def _display_build(self, build):
        self.selected_build_id = build.get("id")
        report = build.get("inspection") or {}
        lines = [
            f"Arquivo: {report.get('name', '—')}",
            f"Alvo: {report.get('target', '—')}",
            f"Tipo: {report.get('artifact_type', '—')}",
            f"Versão detectada: {report.get('version') or 'não identificada'}",
            f"Tamanho: {(report.get('size_bytes') or 0) / (1024 * 1024):.2f} MB",
            f"SHA-256: {report.get('sha256') or '—'}",
            f"Resultado estrutural: {report.get('overall', '—')}",
            f"Caminho local: {build.get('path', '—')}",
            "",
            "Verificações estruturais:",
        ]
        for check in report.get("checks", []):
            lines.append(f"[{check.get('status')}] {check.get('label')}: {check.get('detail')}")
        test_run = build.get("test_run")
        if test_run:
            lines += ["", f"Suíte de código: {test_run.get('overall')}"]
            for check in test_run.get("checks", []):
                lines.append(f"[{check.get('status')}] {check.get('label')}: {check.get('detail')}")
        if report.get("feedback_ids"):
            lines += ["", "IDs de feedback encontrados:"] + [f"- {item}" for item in report["feedback_ids"]]
        self._set_detail("\n".join(lines))
        can_test = Path(build.get("path", "")).suffix.lower() == ".zip" and "código-fonte" in report.get("artifact_type", "")
        self.test_button.configure(state="normal" if can_test and not self.busy else "disabled")

    def _select_build(self, _event=None):
        selection = self.build_tree.selection()
        if not selection:
            return
        build = self._build_rows.get(selection[0])
        if build:
            self._display_build(build)
            self._refresh_manual_checks()

    def _choose_build(self):
        selected = filedialog.askopenfilename(parent=self, title="Importar build ou pacote de código",
            filetypes=[("Builds e fontes", "*.zip *.apk *.aab *.exe *.msi *.msix *.appx"), ("Todos os arquivos", "*.*")])
        if not selected:
            return
        self.busy = True
        self.add_build_button.configure(state="disabled")
        self.test_button.configure(state="disabled")
        self.status.set("Copiando e verificando estrutura, hash e conteúdo do pacote…")
        chosen_target = self.target.get()
        threading.Thread(target=self._inspect_worker, args=(Path(selected), chosen_target), daemon=True).start()

    def _inspect_worker(self, source: Path, target: str):
        try:
            report = inspect_build(source, target)
            digest = report.get("sha256") or uuid.uuid4().hex
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in source.name)[:140]
            saved = self.build_dir / f"{digest[:12]}_{safe_name}"
            if not saved.exists():
                shutil.copy2(source, saved)
            report["path"] = str(saved)
            record = {"id": uuid.uuid4().hex, "added_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                      "path": str(saved), "target": target, "inspection": report, "test_run": None,
                      "manual_checks": {key: {"status": MANUAL_STATUSES[0], "notes": ""} for key, _ in MANUAL_CHECKS}}
            self.after(0, lambda: self._finish_inspect(record))
        except Exception as exc:
            message = f"Falha na inspeção: {type(exc).__name__}: {exc}"
            self.after(0, lambda msg=message: self._finish_error(msg))

    def _finish_inspect(self, record):
        digest = (record.get("inspection") or {}).get("sha256")
        existing = next((x for x in self.builds if (x.get("inspection") or {}).get("sha256") == digest), None)
        if existing:
            self.selected_build_id = existing.get("id")
            self.status.set("Esse SHA-256 já estava registrado; selecionei o registro existente.")
        else:
            self.builds.append(record)
            self.selected_build_id = record["id"]
            _save_json(self.builds_path, self.builds)
            self._write_inspection_report(record)
            self.status.set(f"Build registrado: {(record.get('inspection') or {}).get('overall')}.")
        self.busy = False
        self.add_build_button.configure(state="normal")
        self._refresh_builds(self.selected_build_id)

    def _finish_error(self, message):
        self.busy = False
        self.add_build_button.configure(state="normal")
        self.status.set(message)
        selected = self._build_rows.get(self.selected_build_id)
        if selected:
            self._display_build(selected)
        messagebox.showerror("SIM Labs", message, parent=self)

    def _run_tests(self):
        build = self._build_rows.get(self.selected_build_id)
        if not build:
            messagebox.showinfo("Selecione um ZIP", "Selecione um pacote .zip com código-fonte.", parent=self)
            return
        confirmed = messagebox.askyesno(
            "Executar testes do pacote?",
            "A suíte vai executar código do ZIP com as permissões deste usuário. O runner remove variáveis de segredo comuns e aplica tempo limite, mas não isola a rede nem o processo.\n\nExecute somente um pacote em que você confia. Continuar?",
            parent=self,
        )
        if not confirmed:
            return
        self.busy = True
        self.add_build_button.configure(state="disabled")
        self.test_button.configure(state="disabled")
        self.status.set("Executando testes do projeto em pasta temporária…")
        threading.Thread(target=self._test_worker, args=(build.get("path"), build.get("id")), daemon=True).start()

    def _test_worker(self, path, build_id):
        try:
            result = run_source_tests(path)
        except Exception as exc:
            result = {
                "schema": "sim-labs.test-run/1.0",
                "source": str(path),
                "checks": [{
                    "id": "runner_error",
                    "label": "Execução da suíte",
                    "status": "FAIL",
                    "detail": f"{type(exc).__name__}: {str(exc)[:500]}",
                }],
                "overall": "FAIL",
            }
        self.after(0, lambda: self._finish_tests(build_id, result))

    def _finish_tests(self, build_id, result):
        build = next((x for x in self.builds if x.get("id") == build_id), None)
        if build:
            build["test_run"] = result
            _save_json(self.builds_path, self.builds)
            self._write_test_report(build, result)
        self.busy = False
        self.add_build_button.configure(state="normal")
        self.status.set(f"Testes encerrados: {result.get('overall')}.")
        self._refresh_builds(build_id)

    def _write_inspection_report(self, build):
        report = build.get("inspection") or {}
        folder = self.report_dir / str(build.get("id"))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / "inspection.md").write_text(render_report_markdown(report), encoding="utf-8")

    def _write_test_report(self, build, result):
        payload = {"build_id": build.get("id"), "build": build.get("inspection"), "test_run": result,
                   "manual_checks": build.get("manual_checks", {}), "feedback_validation_required": True}
        folder = self.report_dir / str(build.get("id"))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md = [render_report_markdown(build.get("inspection") or {}), "## Testes do projeto", ""]
        for check in result.get("checks", []):
            md.append(f"- **{check.get('status')}** — {check.get('label')}: {check.get('detail')}")
        md += ["", "## Validação manual", ""]
        for key, label in MANUAL_CHECKS:
            value = (build.get("manual_checks") or {}).get(key, {})
            md.append(f"- {value.get('status', 'Não testado')} — {label}. {value.get('notes', '')}".strip())
        (folder / "qa_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    def _save_report(self):
        build = self._build_rows.get(self.selected_build_id)
        if not build:
            messagebox.showinfo("Sem build", "Importe e selecione um build primeiro.", parent=self)
            return
        folder = self.report_dir / str(build.get("id"))
        folder.mkdir(parents=True, exist_ok=True)
        report = {"schema": "sim-labs.qa-report/1.0", "product": self.product, "release": self.release,
                  "build_id": build.get("id"), "inspection": build.get("inspection"), "test_run": build.get("test_run"),
                  "manual_checks": build.get("manual_checks"), "feedbacks": self.feedbacks,
                  "feedbacks_are_not_auto_resolved": True}
        (folder / "qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [render_report_markdown(build.get("inspection") or {}), "## Resultado da suíte", ""]
        for check in (build.get("test_run") or {}).get("checks", []):
            lines.append(f"- **{check.get('status')}** — {check.get('label')}: {check.get('detail')}")
        lines += ["", "## Checklist manual", ""]
        for key, label in MANUAL_CHECKS:
            value = (build.get("manual_checks") or {}).get(key, {})
            lines.append(f"- **{value.get('status', 'Não testado')}** — {label}. {value.get('notes', '')}".strip())
        lines += ["", "Feedbacks permanecem em aberto até alguém validar a correção no produto.", ""]
        md_path = folder / "qa_report.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        self.status.set(f"Relatório salvo em {folder}.")
        messagebox.showinfo("Relatório salvo", f"Relatório local salvo em:\n{folder}", parent=self)

    def _import_feedbacks(self):
        paths = filedialog.askopenfilenames(parent=self, title="Selecione todas as partes do pacote Collector",
                                            filetypes=[("ZIP", "*.zip")])
        if not paths:
            return
        merged = {str(x.get("feedback_id")): x for x in self.feedbacks if x.get("feedback_id")}
        imported = 0
        try:
            for raw in paths:
                payload = import_feedback_package(raw)
                for record in payload["records"]:
                    key = record["feedback_id"]
                    if key in merged:
                        old = merged[key]
                        qa_status = old.get("qa_status", FEEDBACK_QA_STATUSES[0])
                        evidence = list(dict.fromkeys((old.get("evidence") or []) + (record.get("evidence") or [])))
                        old.update(record)
                        old["qa_status"] = qa_status
                        old["evidence"] = evidence
                        old["source_packages"] = list(dict.fromkeys((old.get("source_packages") or []) + [Path(raw).name]))
                    else:
                        record["qa_status"] = FEEDBACK_QA_STATUSES[0]
                        record["source_packages"] = [Path(raw).name]
                        merged[key] = record
                        imported += 1
            self.feedbacks = list(merged.values())
            _save_json(self.feedbacks_path, self.feedbacks)
            self._refresh_feedbacks()
            self.status.set(f"Pacote(s) importado(s); {imported} ID(s) novo(s), repetições mescladas.")
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            messagebox.showerror("Importação de feedback", f"Não consegui importar: {type(exc).__name__}: {exc}", parent=self)

    def _select_feedback(self, _event=None):
        selection = self.feedback_tree.selection()
        if not selection:
            return
        record = self._feedback_rows.get(selection[0])
        if record:
            self.feedback_qa_status.set(record.get("qa_status") or FEEDBACK_QA_STATUSES[0])
            summary = f"ID: {record.get('feedback_id')}\nTítulo: {record.get('title')}\n\n{record.get('description') or record.get('notes') or 'Sem descrição no pacote de ingestão.'}"
            self.status.set(summary.replace("\n", " • ")[:320])

    def _save_feedback_status(self):
        selection = self.feedback_tree.selection()
        if not selection:
            messagebox.showinfo("Selecione um feedback", "Selecione uma linha antes de atualizar o status.", parent=self)
            return
        record = self._feedback_rows.get(selection[0])
        if not record:
            return
        if self.feedback_qa_status.get() == "Resolvido confirmado":
            if not messagebox.askyesno("Confirmar resolução", "Você validou manualmente o comportamento corrigido no build e revisou a evidência?", parent=self):
                return
        record["qa_status"] = self.feedback_qa_status.get()
        record["qa_updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        _save_json(self.feedbacks_path, self.feedbacks)
        self._refresh_feedbacks()
        self.feedback_tree.selection_set(record["feedback_id"])
        self.status.set(f"Status QA atualizado para {record['feedback_id']}.")

    def _refresh_manual_checks(self):
        for item in self.manual_tree.get_children():
            self.manual_tree.delete(item)
        self._manual_rows.clear()
        build = self._build_rows.get(self.selected_build_id)
        if not build:
            return
        data = build.setdefault("manual_checks", {})
        for key, label in MANUAL_CHECKS:
            value = data.setdefault(key, {"status": MANUAL_STATUSES[0], "notes": ""})
            self.manual_tree.insert("", "end", iid=key, text=label, values=(value.get("status", MANUAL_STATUSES[0]),))
            self._manual_rows[key] = value
        _save_json(self.builds_path, self.builds)

    def _select_manual_check(self, _event=None):
        selection = self.manual_tree.selection()
        if not selection:
            return
        value = self._manual_rows.get(selection[0], {})
        self.manual_status.set(value.get("status", MANUAL_STATUSES[0]))
        self.manual_notes.set(value.get("notes", ""))

    def _save_manual_check(self):
        selection = self.manual_tree.selection()
        if not selection:
            messagebox.showinfo("Selecione uma etapa", "Selecione uma verificação manual.", parent=self)
            return
        build = self._build_rows.get(self.selected_build_id)
        if not build:
            return
        key = selection[0]
        build.setdefault("manual_checks", {})[key] = {"status": self.manual_status.get(), "notes": self.manual_notes.get().strip(),
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        _save_json(self.builds_path, self.builds)
        self._refresh_manual_checks()
        self.manual_tree.selection_set(key)
        self.status.set("Resultado manual salvo neste build.")

    def _open_data_folder(self):
        try:
            import os
            if os.name == "nt":
                os.startfile(str(self.data_dir))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(self.data_dir)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(self.data_dir)])
        except Exception as exc:
            messagebox.showerror("Pasta local", f"Não consegui abrir a pasta: {exc}", parent=self)
