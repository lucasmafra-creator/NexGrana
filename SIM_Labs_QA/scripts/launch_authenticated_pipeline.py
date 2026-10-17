#!/usr/bin/env python3
"""Authenticate locally, start the reviewed QA pipeline once, and follow it."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


QA_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = QA_ROOT.parent
RUNTIME = QA_ROOT / ".runtime"
STATE_FILE = RUNTIME / "one_click_qa.json"
EXPECTED_SERVICE = "sim-labs-control-center-qa"
EXPECTED_PHASE = "Engine 0.4.1-qa.2"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class QAStartError(RuntimeError):
    pass


class APIError(QAStartError):
    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _port(root: Path) -> int:
    path = root / ".runtime" / "qa_port.txt"
    try:
        value = int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as exc:
        raise QAStartError("Porta QA ausente ou inválida; execute primeiro o inicializador.") from exc
    if not 1024 <= value <= 65535:
        raise QAStartError("Porta QA fora da faixa permitida.")
    return value


def _password(root: Path) -> str:
    path = root / ".runtime" / "PRIMEIRO_ACESSO.txt"
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise QAStartError("Credencial local salva não encontrada; nenhuma senha será criada ou trocada.") from exc
    for line in lines:
        if line.startswith("Senha:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
    raise QAStartError("Arquivo de primeiro acesso não contém uma credencial reconhecível.")


def _instance_id(root: Path) -> str:
    value = root.resolve().as_posix().lower().rstrip("/")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class LocalAPI:
    def __init__(self, base_url: str, timeout: float = 8):
        if not base_url.startswith("http://127.0.0.1:"):
            raise QAStartError("A central não está vinculada ao loopback local esperado.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = request.build_opener(request.ProxyHandler({}), NoRedirect())

    def call(self, path: str, *, method: str = "GET", payload: dict | None = None,
             token: str | None = None) -> dict:
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        req = request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read(1024 * 1024)
        except error.HTTPError as exc:
            raise APIError(exc.code, f"A central respondeu HTTP {exc.code}.") from None
        except (error.URLError, TimeoutError, OSError) as exc:
            raise APIError(None, f"Central QA temporariamente indisponível ({type(exc).__name__}).") from None
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise APIError(None, "A central retornou uma resposta que não é JSON válido.") from exc
        if not isinstance(value, dict):
            raise APIError(None, "Formato inesperado retornado pela central QA.")
        return value


def _save_state(root: Path, state: dict) -> None:
    path = root / ".runtime" / "one_click_qa.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": state.get("status", "UNKNOWN"),
        "run_id": state.get("run_id"),
        "started_by_this_launcher": bool(state.get("started_by_this_launcher", False)),
        "last_error": state.get("last_error"),
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_dir(root: Path, run_id: str | None) -> Path | None:
    if not run_id or not RUN_ID_RE.fullmatch(run_id):
        return None
    base = (root / "data" / "qa_pipeline" / "runs").resolve()
    candidate = (base / run_id).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


def _report_summary(root: Path, run_id: str | None) -> dict:
    run_dir = _run_dir(root, run_id)
    report_file = run_dir / "pipeline-report.json" if run_dir else None
    if not report_file or not report_file.is_file():
        return {}
    try:
        value = json.loads(report_file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        "summary": value.get("summary", {}),
        "tests": value.get("tests", []),
        "builds": value.get("builds", []),
        "blockers": value.get("blockers", []),
        "report": str(report_file),
    }


def _check_identity(api: LocalAPI, root: Path) -> None:
    health = api.call("/api/v1/health")
    valid = (
        health.get("status") == "ok"
        and health.get("service") == EXPECTED_SERVICE
        and health.get("phase") == EXPECTED_PHASE
        and health.get("instance_id") == _instance_id(root)
    )
    if not valid:
        raise QAStartError("Health/versão/identidade não correspondem a esta cópia do SIM Labs QA.")


def _login(api: LocalAPI, root: Path) -> str:
    result = api.call("/api/v1/auth/login", method="POST", payload={"password": _password(root)})
    token = result.get("token")
    if not isinstance(token, str) or not token:
        raise QAStartError("O login local não foi validado; senha e token não serão exibidos.")
    return token


def _running(state: dict) -> bool:
    return str(state.get("status", "")).upper() == "RUNNING"


def _observe_after_uncertain_post(api: LocalAPI, token: str, previous_id: str | None,
                                  *, seconds: int, poll_seconds: float,
                                  clock=time.monotonic, sleep=time.sleep) -> dict | None:
    deadline = clock() + seconds
    while clock() < deadline:
        try:
            current = api.call("/api/v1/qa/pipeline/status", token=token)
        except APIError:
            sleep(min(poll_seconds, max(0, deadline - clock())))
            continue
        current_id = current.get("run_id")
        if current_id and current_id != previous_id and (_running(current) or current.get("status") not in {"NOT_RUN", "STARTING"}):
            return current
        sleep(min(poll_seconds, max(0, deadline - clock())))
    return None


def _start_or_attach(api: LocalAPI, token: str, *, poll_seconds: float,
                     reconciliation_seconds: int = 45) -> tuple[dict, bool]:
    before = api.call("/api/v1/qa/pipeline/status", token=token)
    if _running(before):
        return before, False
    previous_id = before.get("run_id")
    try:
        started = api.call("/api/v1/qa/pipeline", method="POST", token=token)
        if not started.get("run_id"):
            raise QAStartError("A central aceitou a solicitação sem informar o identificador da execução.")
        return started, True
    except APIError as exc:
        if exc.status == 409:
            deadline = time.monotonic() + reconciliation_seconds
            while time.monotonic() < deadline:
                try:
                    current = api.call("/api/v1/qa/pipeline/status", token=token)
                except APIError:
                    time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))
                    continue
                if _running(current):
                    return current, False
                time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))
            raise QAStartError("O SIM Labs informou uma reserva/execução concorrente, mas não confirmou um pipeline ativo. Não houve segunda tentativa automática.") from None
        if exc.status is not None and exc.status < 500:
            raise
        # A connection drop or server-side 5xx can happen after the server
        # accepted the POST. Query status only; never repeat an ambiguous POST.
        observed = _observe_after_uncertain_post(api, token, previous_id,
                                                seconds=reconciliation_seconds,
                                                poll_seconds=poll_seconds)
        if observed:
            return observed, False
        raise QAStartError("A resposta ao início se perdeu e a execução não pôde ser confirmada. O pedido não foi repetido para evitar duplicidade.") from None


def run_pipeline(root: Path = QA_ROOT, *, max_wait_seconds: int = 10800,
                 poll_seconds: float = 5, output=print, api: LocalAPI | None = None) -> int:
    root = root.resolve()
    port = _port(root)
    api = api or LocalAPI(f"http://127.0.0.1:{port}")
    _check_identity(api, root)
    token = _login(api, root)
    output("Health e identidade QA: PASS")
    output("Login local estável: PASS (segredo oculto)")
    state, started_here = _start_or_attach(api, token, poll_seconds=poll_seconds)
    state = dict(state)
    state["started_by_this_launcher"] = started_here
    if not state.get("run_id"):
        raise QAStartError("A central não informou um run_id; nenhum retry automático será feito.")
    _save_state(root, state)
    output(("Pipeline QA iniciado uma única vez" if started_here else "Pipeline QA já ativo; acompanhando a execução existente") + f" (run {state['run_id']}).")

    deadline = time.monotonic() + max_wait_seconds
    next_notice = 0.0
    while True:
        try:
            current = api.call("/api/v1/qa/pipeline/status", token=token)
        except APIError as exc:
            if time.monotonic() >= deadline:
                state.update(status="CONNECTION_LOST", last_error=str(exc))
                _save_state(root, state)
                raise QAStartError("A conexão local não voltou antes do limite; o pipeline não foi reiniciado. Reabra a central e consulte o mesmo run_id.") from None
            time.sleep(poll_seconds)
            continue
        current_id = current.get("run_id")
        if current_id and current_id != state["run_id"]:
            raise QAStartError("A central passou a informar outro run_id; a automação parou para não misturar duas execuções.")
        current["started_by_this_launcher"] = started_here
        _save_state(root, current)
        status = str(current.get("status", "UNKNOWN")).upper()
        if status not in {"RUNNING", "NOT_RUN", "STARTING"}:
            break
        now = time.monotonic()
        if now >= deadline:
            raise QAStartError(f"A execução continua ativa após {max_wait_seconds // 60} minutos. O run_id foi preservado; não foi iniciado outro pipeline.")
        if now >= next_notice:
            output(f"Pipeline QA: RUNNING — acompanhamento automático ativo ({state['run_id']}).")
            next_notice = now + 30
        time.sleep(min(poll_seconds, max(0, deadline - now)))

    state.update(current)
    state["started_by_this_launcher"] = started_here
    _save_state(root, state)
    details = _report_summary(root, state.get("run_id"))
    summary = details.get("summary") or {}
    if summary:
        output(f"Testes aprovados: {summary.get('tests_passed', 0)}; falhos/bloqueados: {summary.get('tests_blocked_or_failed', 0)}; builds criados: {summary.get('native_builds_generated', 0)}.")
        output(f"Windows build: {summary.get('windows_build_status', 'UNKNOWN')}; Android build: {summary.get('android_build_status', 'UNKNOWN')} (etapa separada).")
    for item in details.get("tests", []):
        output(f"TESTE {item.get('name', 'desconhecido')}: {item.get('status', 'UNKNOWN')}")
    for item in details.get("builds", []):
        output(f"BUILD {item.get('target', 'desconhecido')}: {item.get('status', 'UNKNOWN')}")
    output(f"RESULTADO DO PIPELINE: {state.get('status', 'UNKNOWN')}")
    if details.get("report"):
        output(f"Relatório local: {details['report']}")
    return 0 if state.get("status") == "PRONTA PARA QA REAL" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-wait-minutes", type=int, default=180,
                        help="limite para acompanhar a execução; nunca repete um pedido de início")
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    if args.max_wait_minutes < 1 or args.poll_seconds <= 0:
        parser.error("os limites precisam ser positivos")
    try:
        return run_pipeline(max_wait_seconds=args.max_wait_minutes * 60,
                            poll_seconds=args.poll_seconds)
    except QAStartError as exc:
        print(f"QA AUTOMÁTICO: BLOCKED — {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
