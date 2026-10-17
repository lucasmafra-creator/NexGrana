"""CEO-only launcher for the trusted, local QA pipeline in this QA clone."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Principal, get_current_principal
from .integrated import ceo

router = APIRouter()
QA_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = QA_ROOT.parent
RUNNER = QA_ROOT / "scripts" / "run_release_pipeline.py"
STATE_ROOT = QA_ROOT / "data" / "qa_pipeline"
LOCK_PATH = STATE_ROOT / "active.lock"
LATEST_PATH = STATE_ROOT / "latest.json"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _pid_is_running(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # access denied: do not assume dead
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, TypeError, ValueError):
        return False


def _safe_status() -> dict:
    state = _read_json(LATEST_PATH)
    if not state:
        return {"status": "NOT_RUN", "message": "Nenhuma execução do pipeline registrada neste clone QA."}
    pid = state.get("pid")
    process_running = isinstance(pid, int) and _pid_is_running(pid)
    report_path = Path(state.get("report_path", "")) if state.get("report_path") else None
    if report_path:
        try:
            report_path.resolve().relative_to(STATE_ROOT.resolve())
        except (OSError, ValueError):
            report_path = None
    report_finished = False
    if report_path and report_path.is_file():
        report = _read_json(report_path)
        if report and report.get("finished_at"):
            report_finished = True
            state["status"] = report.get("status", "BLOCKED")
            state["summary"] = report.get("summary", {})
            state["tests"] = report.get("tests", [])
            state["builds"] = report.get("builds", [])
            state["blockers"] = report.get("blockers", [])
            state["finished_at"] = report.get("finished_at")
    if report_finished and not process_running:
        lock = _read_json(LOCK_PATH)
        if lock.get("run_id") == state.get("run_id") and lock.get("pid") == pid:
            LOCK_PATH.unlink(missing_ok=True)
    if not report_finished and process_running:
        state["status"] = "RUNNING"
    elif not report_finished:
        if state.get("status") == "RUNNING":
            state["status"] = "BLOCKED"
            state["blockers"] = ["Processo do pipeline encerrou antes de gravar o relatório final."]
            state["finished_at"] = datetime.now(timezone.utc).isoformat()
            state["message"] = "A execução encerrou sem relatório; nenhuma aprovação ou build foi confirmada."
            _write_json(LATEST_PATH, state)
        else:
            state["status"] = state.get("status", "BLOCKED")
        if isinstance(pid, int):
            lock = _read_json(LOCK_PATH)
            if lock.get("run_id") == state.get("run_id") and lock.get("pid") == pid:
                LOCK_PATH.unlink(missing_ok=True)
    return {key: value for key, value in state.items() if key not in {"pid", "report_path", "log_path"}}


@router.get("/qa/pipeline/status")
def pipeline_status(p: Principal = Depends(get_current_principal)):
    ceo(p)
    return _safe_status()


@router.post("/qa/pipeline", status_code=202)
def start_pipeline(p: Principal = Depends(get_current_principal)):
    ceo(p)
    marker = _read_json(QA_ROOT / ".simlabs-qa.json")
    if marker.get("release_channel") != "qa" or not RUNNER.is_file() or not PACKAGE_ROOT.joinpath("NexGrana").is_dir():
        raise HTTPException(503, "Clone QA ou fonte NexGrana não encontrado; nenhum comando foi iniciado.")

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        lock = _read_json(LOCK_PATH)
        lock_pid = lock.get("pid")
        lock_run = lock.get("run_id")
        if isinstance(lock_pid, int) and _pid_is_running(lock_pid):
            raise HTTPException(409, "Uma execução do pipeline já está em andamento.")
        # A well-formed lock whose process ended is stale and may be released.
        # An empty/unknown lock is never deleted automatically.
        if isinstance(lock_run, str) and lock_run and lock_pid is None:
            try:
                created_at = datetime.fromisoformat(lock.get("created_at", ""))
            except (TypeError, ValueError):
                raise HTTPException(409, "Existe uma reserva de pipeline inválida; revise o clone QA.")
            if datetime.now(timezone.utc) - created_at.astimezone(timezone.utc) > timedelta(minutes=10):
                LOCK_PATH.unlink(missing_ok=True)
            else:
                raise HTTPException(409, "O pipeline está sendo reservado; tente novamente em instantes.")
        elif isinstance(lock_pid, int) and lock_pid > 0 and isinstance(lock_run, str) and lock_run:
            LOCK_PATH.unlink(missing_ok=True)
        else:
            raise HTTPException(409, "Existe um lock sem processo verificável. Revise o clone QA antes de liberar outra execução.")

    run_id = uuid.uuid4().hex
    run_dir = STATE_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report_path = run_dir / "pipeline-report.json"
    log_path = run_dir / "pipeline.log"
    created_at = datetime.now(timezone.utc).isoformat()
    reservation = {"run_id": run_id, "pid": None, "created_at": created_at, "starting": True}
    try:
        lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(lock_fd, "w", encoding="utf-8") as stream:
            json.dump(reservation, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise HTTPException(409, "Outra execução está reservando o pipeline; tente novamente em instantes.") from exc
    log_handle = log_path.open("ab")
    log_handle.write(f"SIM Labs QA pipeline aceito; run_id={run_id}; inicio={created_at}\n".encode("utf-8"))
    log_handle.flush()
    command = [sys.executable, "-u", str(RUNNER), "--package-root", str(PACKAGE_ROOT), "--output-dir", str(run_dir), "--prepare-deps", "--run-id", run_id]
    process_options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    try:
        process = subprocess.Popen(
            command,
            cwd=str(PACKAGE_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            shell=False,
            close_fds=True,
            **process_options,
        )
    except OSError as exc:
        log_handle.close()
        LOCK_PATH.unlink(missing_ok=True)
        raise HTTPException(503, "O pipeline não pôde iniciar. Revise as dependências locais do SIM Labs QA.") from exc
    finally:
        if not log_handle.closed:
            log_handle.close()

    state = {
        "run_id": run_id,
        "pid": process.pid,
        "status": "RUNNING",
        "created_at": created_at,
        "report_path": str(report_path),
        "log_path": str(log_path),
        "message": "Pipeline iniciado no clone QA. Nenhum binário será instalado ou publicado automaticamente.",
    }
    _write_json(LOCK_PATH, {"run_id": run_id, "pid": process.pid, "created_at": created_at, "starting": False})
    _write_json(LATEST_PATH, state)
    return {key: value for key, value in state.items() if key not in {"pid", "report_path", "log_path"}}
