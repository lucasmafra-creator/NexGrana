#!/usr/bin/env python3
"""Run bounded local QA and native builds for the reviewed SIM Labs QA bundle.

The runner never executes an uploaded ZIP, installs artifacts, applies database
migrations, logs in to external services, or promotes a release. Python package
and npm setup is limited to this QA clone and can be requested with
``--prepare-deps``. Native builds are attempted only on a supported Windows
host after local tests pass.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "nexgrana-sim-labs.pipeline/1.0"
TIMEOUT = 1800
IGNORED_SOURCE_PARTS = {".data", "scratch", "backups", ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".runtime", "dist", "build", "target"}
SOURCE_TREES = ("NexGrana", "SIM_Labs", "SIM_Labs_QA", "tools")
SENSITIVE_NAME = re.compile(r"(?i)(token|secret|password|passwd|api[_-]?key|service[_-]?role|credential)")
NEX_QA_MODULES = ["flet", "flet_charts", "flet_camera", "flet_secure_storage", "supabase", "cryptography", "PIL", "fastapi", "uvicorn"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def requirements_tree_sha256(path: Path) -> str:
    """Hash a requirements file and every file it includes with ``-r``."""
    root = path.parent.resolve()
    digest = hashlib.sha256()
    visited: set[Path] = set()

    def add(requirements_file: Path) -> None:
        resolved = requirements_file.resolve()
        if resolved in visited:
            return
        visited.add(resolved)
        try:
            data = resolved.read_bytes()
        except OSError:
            digest.update(b"MISSING\0" + str(resolved).encode("utf-8", errors="replace"))
            return
        try:
            label = resolved.relative_to(root).as_posix()
        except ValueError:
            label = resolved.as_posix()
        digest.update(label.encode("utf-8") + b"\0" + data + b"\0")
        for raw_line in data.decode("utf-8-sig", errors="replace").splitlines():
            line = raw_line.strip()
            if line.startswith("-r ") or line.startswith("--requirement "):
                included = line.split(None, 1)[1].strip().strip("\"'")
                add(resolved.parent / included)

    add(path)
    return digest.hexdigest()


def log_reference(path: Path) -> str:
    parts = path.resolve().parts
    for index, part in enumerate(parts):
        if part == "qa_pipeline" and index + 1 < len(parts):
            return "SIM_Labs_QA/data/qa_pipeline/" + Path(*parts[index + 1:]).as_posix()
    return path.name


def redact(text: str) -> str:
    for name in ("USERPROFILE", "HOME", "LOCALAPPDATA", "APPDATA"):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "<USER_PATH>").replace(value.replace("\\", "/"), "<USER_PATH>")
    for name, value in os.environ.items():
        if value and (SENSITIVE_NAME.search(name) or value.lower().startswith("sb_secret_")) and len(value) >= 6:
            text = text.replace(value, "<redacted>")
    text = re.sub(r"(?i)([a-z0-9_]*(?:token|secret|password|passwd|api[_-]?key|service[_-]?role)[a-z0-9_]*)\s*[:=]\s*([^\s,;]+)", r"\1=<redacted>", text)
    text = re.sub(r"(https?://)[^/@\s:]+:[^/@\s]+@", r"\1<redacted>@", text)
    return text


def run(command: list[str], cwd: Path, log_path: Path, timeout: int = TIMEOUT) -> dict:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, shell=False)
        out = redact((result.stdout or "") + ("\n" + result.stderr if result.stderr else ""))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(out[-1_000_000:], encoding="utf-8", errors="replace")
        return {"status": "PASS" if result.returncode == 0 else "FAIL", "exit_code": result.returncode,
                "duration_seconds": round(time.monotonic() - started, 3), "log": log_reference(log_path), "tail": out[-1200:]}
    except subprocess.TimeoutExpired as exc:
        out = redact((exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or ""))
        out += "\nTimeout: limite de tempo atingido; nenhum retry infinito será iniciado."
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(out[-1_000_000:], encoding="utf-8", errors="replace")
        return {"status": "BLOCKED", "reason": "TIMEOUT", "duration_seconds": round(time.monotonic() - started, 3), "log": log_reference(log_path), "tail": out[-1200:]}
    except OSError as exc:
        message = redact(f"{type(exc).__name__}: {exc}")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(message, encoding="utf-8")
        return {"status": "BLOCKED", "reason": type(exc).__name__, "duration_seconds": round(time.monotonic() - started, 3), "log": log_reference(log_path), "tail": message}


def python_missing_modules(python: Path | str, modules: list[str], log_path: Path) -> list[str] | None:
    code = "import importlib.util,json; names=" + repr(modules) + "; print(json.dumps([n for n in names if importlib.util.find_spec(n) is None]))"
    result = run([str(python), "-c", code], Path.cwd(), log_path, timeout=30)
    if result["status"] != "PASS":
        return None
    try:
        return json.loads(result["tail"].splitlines()[-1])
    except (ValueError, IndexError):
        return None


def find_base_python() -> list[str] | None:
    candidates = []
    if os.name == "nt" and shutil.which("py"):
        launcher = shutil.which("py") or "py"
        # NexGrana declares requires-python >=3.11. Prefer the newest stable
        # interpreter installed by the Windows launcher, then fall back to the
        # generic launcher selection. Do not hard-fail a machine that only has
        # a newer stable Python allowed by NexGrana's requires-python metadata.
        candidates.extend([launcher, f"-3.{minor}"] for minor in (14, 13, 12, 11))
        candidates.append([launcher, "-3"])
    for command in ("python3.14", "python3.13", "python3.12", "python3.11", "python3", "python"):
        path = shutil.which(command)
        if path:
            candidates.append([path])
    for candidate in candidates:
        try:
            result = subprocess.run(candidate + ["-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.releaselevel}')"], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            try:
                parts = result.stdout.strip().split(".")
                version = (int(parts[0]), int(parts[1]))
                is_stable = len(parts) == 3 and parts[2] == "final"
            except ValueError:
                continue
            if version[0] == 3 and version >= (3, 11) and is_stable:
                return candidate
    return None


def ensure_python(project: Path, requirements: Path, modules: list[str], prepare: bool, logs: Path, label: str) -> tuple[Path | None, dict]:
    venv = project / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    setup = {"status": "READY", "created_venv": False, "dependencies_installed": False}
    if not python.is_file():
        if not prepare:
            current = Path(sys.executable)
            missing = python_missing_modules(current, modules, logs / f"{label}-modules.log")
            if missing == []:
                return current, setup
            return None, {"status": "BLOCKED", "reason": "Venv QA ausente ou dependências não disponíveis", "missing_modules": missing or modules, "log": log_reference(logs / f"{label}-modules.log")}
        base = find_base_python()
        if not base:
            return None, {"status": "BLOCKED", "reason": "Python estável 3.11+ não encontrado; dependências não foram instaladas"}
        created = run(base + ["-m", "venv", str(venv)], project, logs / f"{label}-create-venv.log", timeout=180)
        if created["status"] != "PASS" or not python.is_file():
            return None, {"status": "BLOCKED", "reason": "Não foi possível criar o venv isolado", "step": created}
        setup["created_venv"] = True
    missing = python_missing_modules(python, modules, logs / f"{label}-modules.log")
    if missing is None:
        return None, {"status": "BLOCKED", "reason": "Não foi possível inspecionar dependências", "log": log_reference(logs / f"{label}-modules.log")}
    requirements_digest = requirements_tree_sha256(requirements) if requirements.is_file() else "missing"
    stamp = venv / ".requirements.sha256"
    previous_digest = stamp.read_text().strip() if stamp.is_file() else ""
    if prepare and (missing or previous_digest != requirements_digest):
        if not requirements.is_file():
            return None, {"status": "BLOCKED", "reason": "Arquivo requirements não encontrado", "missing_modules": missing}
        installed = run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)], project, logs / f"{label}-pip-install.log", timeout=TIMEOUT)
        if installed["status"] != "PASS":
            return None, {"status": "BLOCKED", "reason": "Instalação de dependências QA falhou", "step": installed}
        stamp.write_text(requirements_digest)
        setup["dependencies_installed"] = True
        missing = python_missing_modules(python, modules, logs / f"{label}-modules-after-install.log")
    if missing:
        check_name = f"{label}-modules-after-install.log" if prepare else f"{label}-modules.log"
        return None, {"status": "BLOCKED", "reason": "Dependências necessárias ausentes", "missing_modules": missing, "log": log_reference(logs / check_name)}
    return python, setup


def qa_environment_check(sim_qa: Path) -> dict:
    guard_path = sim_qa / "backend" / "app" / "qa_environment.py"
    spec = importlib.util.spec_from_file_location("simlabs_qa_environment_guard", guard_path)
    if not spec or not spec.loader:
        return {"status": "BLOCKED", "reason": "Guard de ambiente QA ausente"}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect_qa_environment()


def verify_manifest(package_root: Path) -> dict:
    path = package_root / "release_manifest.json"
    if not path.is_file():
        return {"status": "BLOCKED", "reason": "release_manifest.json ausente"}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        entries = manifest.get("source_files", [])
    except (OSError, ValueError):
        return {"status": "BLOCKED", "reason": "release_manifest.json inválido"}
    if not entries:
        return {"status": "BLOCKED", "reason": "Manifesto não contém hashes de fonte"}
    mismatches = []
    if manifest.get("source_file_count") != len(entries):
        mismatches.append("contagem_de_fontes_diverge_do_manifesto")
    listed_paths = [item.get("path", "") for item in entries]
    if len(set(listed_paths)) != len(listed_paths):
        mismatches.append("manifesto_com_caminhos_duplicados")
    for item in entries:
        relative = Path(item.get("path", ""))
        try:
            target = (package_root / relative).resolve()
            target.relative_to(package_root.resolve())
        except (ValueError, OSError):
            mismatches.append("caminho_forado")
            continue
        if not target.is_file() or sha256(target) != item.get("sha256"):
            mismatches.append(item.get("path", "arquivo_desconhecido"))
    expected_paths = set()
    for tree in SOURCE_TREES:
        base = package_root / tree
        if not base.is_dir():
            continue
        for target in base.rglob("*"):
            if not target.is_file() or target.is_symlink():
                continue
            relative = target.relative_to(package_root)
            if any(part in IGNORED_SOURCE_PARTS for part in relative.parts):
                continue
            if tree == "SIM_Labs_QA" and len(relative.parts) > 1 and relative.parts[1] == "data":
                continue
            if tree == "tools" and len(relative.parts) > 1 and relative.parts[1] == "inventory-output":
                continue
            if target.suffix.lower() in {".tsbuildinfo", ".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".sqlite-wal", ".sqlite-shm", ".sqlite-journal", ".db-wal", ".db-shm", ".db-journal", ".log", ".exe", ".apk", ".msi", ".msix", ".p12", ".pfx", ".pem", ".key"}:
                continue
            if target.name.lower() == ".env" or target.name.lower().startswith(".env."):
                continue
            expected_paths.add(relative.as_posix())
    # The generator includes the two root Windows launchers explicitly; the
    # verifier must count those same files or every bundle reports them as
    # out-of-scope during pipeline preflight.
    for name in ("LEIA_PRIMEIRO.md", "PROJECT_STATE.md", "NEXGRANA_RULES.md", "BUILD_STATUS.md", "QA_REPORT.md", "CHANGELOG.md", "INICIAR.cmd", "REPARAR_E_INICIAR_SIM_LABS_QA.cmd", "REPARAR_E_INICIAR_SIM_LABS_QA.ps1"):
        if (package_root / name).is_file():
            expected_paths.add(name)
    missing_entries = expected_paths - set(listed_paths)
    extra_entries = set(listed_paths) - expected_paths
    mismatches.extend("sem_hash:" + name for name in sorted(missing_entries)[:50])
    mismatches.extend("fora_do_escopo:" + name for name in sorted(extra_entries)[:50])
    return {"status": "PASS" if not mismatches else "BLOCKED", "verified_files": len(entries) - len(mismatches), "mismatches": mismatches[:50]}


def quarantine_unmanifested_source_files(package_root: Path) -> dict:
    """Reconcile an overlaid update by reversibly moving only untracked source files.

    User data, ignored runtime files, manifest-listed files, and changed tracked
    files are never moved. All moved files are kept under SIM_Labs_QA/.runtime
    so a clean overlay can recover without deleting the previous contents.
    """
    initial = verify_manifest(package_root)
    if initial.get("status") == "PASS":
        return {"status": "PASS", "quarantined_count": 0, "manifest": initial}

    mismatches = initial.get("mismatches", [])
    if not mismatches or any(not item.startswith("sem_hash:") for item in mismatches):
        return {"status": "BLOCKED", "reason": "Há arquivos listados alterados/ausentes ou manifesto divergente; nenhum arquivo foi movido.", "manifest": initial}

    quarantine = package_root / "SIM_Labs_QA" / ".runtime" / "source-quarantine" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    moved: list[tuple[Path, Path]] = []
    try:
        # The verifier reports at most 50 mismatches. Recheck after each batch
        # so even large overlays are reconciled without hiding other failures.
        for _ in range(100):
            current = verify_manifest(package_root)
            if current.get("status") == "PASS":
                return {
                    "status": "PASS",
                    "quarantined_count": len(moved),
                    "quarantine_path": quarantine.as_posix() if moved else None,
                    "manifest": current,
                }
            current_mismatches = current.get("mismatches", [])
            if not current_mismatches or any(not item.startswith("sem_hash:") for item in current_mismatches):
                raise RuntimeError("Após separar arquivos extras, a validação encontrou divergências que exigem revisão.")
            for mismatch in current_mismatches:
                relative = Path(mismatch.removeprefix("sem_hash:"))
                if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] not in SOURCE_TREES:
                    raise RuntimeError("Caminho extra fora das árvores de código permitidas.")
                source = package_root / relative
                tree_root = (package_root / relative.parts[0]).resolve()
                resolved = source.resolve()
                resolved.relative_to(tree_root)
                if source.is_symlink() or not source.is_file():
                    raise RuntimeError("O arquivo extra não é um arquivo regular seguro para quarentena.")
                destination = quarantine / relative
                if destination.exists():
                    raise RuntimeError("Destino de quarentena já existe.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, destination)
                moved.append((source, destination))
        raise RuntimeError("Limite de reconciliação de arquivos excedido.")
    except (OSError, ValueError, RuntimeError) as exc:
        rollback_errors = []
        for source, destination in reversed(moved):
            try:
                source.parent.mkdir(parents=True, exist_ok=True)
                if source.exists():
                    raise FileExistsError("O arquivo de origem reapareceu durante a reversão.")
                os.replace(destination, source)
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        reason = str(exc)
        if rollback_errors:
            reason += " Falha ao restaurar todos os arquivos: " + "; ".join(rollback_errors[:3])
        return {"status": "BLOCKED", "reason": reason, "manifest": verify_manifest(package_root)}


def append_error_knowledge(package_root: Path, event: dict) -> None:
    path = package_root / "build_error_knowledge_base.json"
    try:
        database = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"schema": "nexgrana.build-error-kb/1.0", "entries": []}
    except (OSError, ValueError):
        database = {"schema": "nexgrana.build-error-kb/1.0", "entries": []}
    fingerprint_source = "|".join(str(event.get(key, "")) for key in ("stage", "platform", "status", "reason", "original_error"))
    fingerprint = hashlib.sha256(fingerprint_source.encode()).hexdigest()
    found = next((item for item in database.get("entries", []) if item.get("fingerprint") == fingerprint), None)
    if found:
        found["occurrences"] = int(found.get("occurrences", 0)) + 1
        found["last_occurrence"] = event.get("occurred_at")
        found["last_result"] = event.get("status")
        found["last_error"] = event.get("original_error") or event.get("reason", "")
        found["last_log"] = event.get("log")
        found["result"] = event.get("status")
        found["attempts"] = int(found.get("attempts", 0)) + 1
        found["attempt_number"] = found["attempts"]
        found["time_lost_seconds"] = float(found.get("time_lost_seconds", 0)) + float(event.get("duration_seconds", 0))
    else:
        database.setdefault("entries", []).append({
            "fingerprint": fingerprint,
            "platform": event.get("platform", "unknown"),
            "version": event.get("version", "unknown"),
            "stage": event.get("stage", "unknown"),
            "error": event.get("reason", ""),
            "original_error": event.get("original_error") or event.get("reason", ""),
            "cause": "Não determinada automaticamente; requer evidência.",
            "solution": None,
            "solution_confidence": "unverified",
            "changed_file": None,
            "log": event.get("log"),
            "last_log": event.get("log"),
            "success": None,
            "last_result": event.get("status"),
            "result": event.get("status"),
            "time_lost_seconds": float(event.get("duration_seconds", 0)),
            "attempts": 1,
            "attempt_number": 1,
            "occurrences": 1,
            "first_occurrence": event.get("occurred_at"),
            "last_occurrence": event.get("occurred_at"),
            "source": "pipeline execution; no secret values stored",
        })
    entries = database.get("entries", [])
    occurrence_count = sum(int(item.get("occurrences", 1)) for item in entries)
    lost_seconds = sum(float(item.get("time_lost_seconds", 0)) for item in entries)
    correction_attempts = sum(int(item.get("autocorrection_attempts", 0)) for item in entries)
    correction_successes = sum(int(item.get("autocorrection_successes", 0)) for item in entries)
    database["metrics"] = {
        "occurrences": occurrence_count,
        "time_lost_seconds": round(lost_seconds, 3),
        "average_time_lost_seconds": round(lost_seconds / occurrence_count, 3) if occurrence_count else 0,
        "autocorrection_attempts": correction_attempts,
        "autocorrection_successes": correction_successes,
        "autocorrection_rate": round(correction_successes / correction_attempts, 4) if correction_attempts else None,
        "recurrent_fingerprints": sum(int(item.get("occurrences", 1)) > 1 for item in entries),
        "calculated_at": utc_now(),
    }
    path.write_text(json.dumps(database, ensure_ascii=False, indent=2), encoding="utf-8")


def npm_check(project: Path, prepare: bool, logs: Path, label: str, required_path: Path) -> tuple[bool, dict]:
    npm = shutil.which("npm")
    if not npm:
        return False, {"status": "BLOCKED", "reason": "npm ausente"}
    if not required_path.exists() and prepare:
        install = run([npm, "ci", "--no-audit", "--no-fund"], project, logs / f"{label}-npm-ci.log", timeout=TIMEOUT)
        if install["status"] != "PASS":
            return False, {"status": "BLOCKED", "reason": "npm ci falhou", "step": install}
    if not required_path.exists():
        return False, {"status": "BLOCKED", "reason": "node_modules ausente; rode o pipeline com preparação automática habilitada"}
    return True, {"status": "READY"}


def record_step_error(package_root: Path, name: str, result: dict, platform_name: str, version: str) -> None:
    if result.get("status") in {"BLOCKED", "FAIL"}:
        detail_parts = [str(result.get("reason") or "")]
        missing_modules = result.get("missing_modules")
        if missing_modules:
            detail_parts.append("módulos ausentes: " + ", ".join(map(str, missing_modules)))
        step = result.get("step")
        if isinstance(step, dict):
            detail_parts.append(str(step.get("tail") or step.get("reason") or ""))
        detail_parts.append(str(result.get("tail") or ""))
        original = redact(" | ".join(part for part in detail_parts if part))[:1200]
        log_name = result.get("log") or (step.get("log") if isinstance(step, dict) else None)
        append_error_knowledge(package_root, {
            "stage": name,
            "platform": platform_name,
            "version": version,
            "status": result.get("status"),
            "reason": redact(str(result.get("reason") or "Falha/bloqueio registrado; causa ainda não confirmada"))[:800],
            "original_error": original,
            "log": log_name,
            "duration_seconds": result.get("duration_seconds", 0),
            "occurred_at": utc_now(),
        })


def is_ready_for_windows_qa(tests: list[dict], builds: list[dict]) -> bool:
    """Clear the release gate only with green tests and a real Windows build."""
    tests_ok = bool(tests) and all(item.get("status") == "PASS" for item in tests)
    windows_ok = any(item.get("target") == "windows" and item.get("status") == "BUILD OK" for item in builds)
    return tests_ok and windows_ok


def build_target(package_root: Path, nex: Path, target: str, nex_python: Path | None, logs: Path) -> dict:
    if platform.system() != "Windows":
        return {"target": target, "status": "BLOCKED", "reason": "Build nativo exige host Windows; nenhum binário foi gerado."}
    if nex_python is None:
        return {"target": target, "status": "BLOCKED", "reason": "Ambiente Python QA do NexGrana não está pronto."}
    flutter_command = shutil.which("flutter")
    flutter_root = os.environ.get("NEX_FLUTTER_ROOT", "").strip()
    if not flutter_root and flutter_command:
        flutter_root = str(Path(flutter_command).resolve().parent.parent)
    if flutter_root and not (Path(flutter_root) / "bin" / "flutter.bat").is_file():
        return {"target": target, "status": "BLOCKED", "reason": "NEX_FLUTTER_ROOT/PATH aponta para SDK invalido; corrija o caminho configurado."}
    if target == "apk":
        sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        adb = shutil.which("adb")
        if not sdk or not Path(sdk).is_dir() or not adb:
            return {"target": target, "status": "BLOCKED", "reason": "Android SDK/ADB ausente ou sem ANDROID_SDK_ROOT; APK não gerado."}
    previous_artifacts = {p.resolve() for p in (nex / "dist").rglob("*") if p.is_file()} if (nex / "dist").is_dir() else set()
    command = [str(nex_python), "build_multiplataforma.py", target, "--timeout", "7200"]
    if flutter_root:
        command += ["--flutter", flutter_root]
    # The pinned Flet CLI installs its required SDK automatically with --yes when absent.
    result = run(command, nex, logs / f"build-{target}.log", timeout=7200)
    artifacts = []
    suffixes = {"windows": {".exe", ".msix", ".msi"}, "apk": {".apk"}}[target]
    for path in (nex / "dist").rglob("*") if (nex / "dist").is_dir() else []:
        if path.is_file() and path.resolve() not in previous_artifacts and path.suffix.lower() in suffixes:
            artifacts.append({"path": str(path.relative_to(package_root)), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    if result["status"] == "PASS" and artifacts:
        return {"target": target, "status": "BUILD OK", "artifacts": artifacts, "log": result["log"], "smoke_test": "PENDING_MANUAL; binary not started by the pipeline"}
    return {"target": target, "status": "BLOCKED" if result["status"] == "BLOCKED" else "FAIL", "reason": result.get("reason") or "Comando terminou sem artefato compatível", "step": {key: result.get(key) for key in ("exit_code", "duration_seconds", "log", "tail")}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prepare-deps", action="store_true", help="Cria venvs do clone QA e instala dependências fixadas; nunca toca na instalação oficial.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout", type=int, default=TIMEOUT)
    parser.add_argument("--tests-only", action="store_true")
    parser.add_argument("--android", action="store_true")
    args = parser.parse_args()
    package_root = args.package_root.resolve()
    nex = package_root / "NexGrana"
    official = package_root / "SIM_Labs"
    sim_qa = package_root / "SIM_Labs_QA"
    output = (args.output_dir or (sim_qa / "data" / "qa_pipeline" / "runs" / (args.run_id or uuid.uuid4().hex))).resolve()
    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    print(f"[{utc_now()}] Pipeline QA iniciado; verificando ambiente, clone e manifesto.", flush=True)
    report = {"schema": SCHEMA, "run_id": args.run_id or uuid.uuid4().hex, "created_at": utc_now(), "host": platform.platform(),
              "python": platform.python_version(), "package_root": "<local QA bundle>", "status": "RUNNING", "tests": [], "builds": [], "blockers": [], "summary": {}}

    marker = {}
    try:
        marker = json.loads((sim_qa / ".simlabs-qa.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report["blockers"].append("Marcador .simlabs-qa.json ausente ou inválido.")
    if marker.get("release_channel") != "qa" or not nex.is_dir() or not official.is_dir():
        report["blockers"].append("O pacote não contém as árvores NexGrana, SIM Labs baseline e SIM Labs QA esperadas.")

    environment = qa_environment_check(sim_qa) if sim_qa.is_dir() else {"status": "BLOCKED", "reason": "Clone QA ausente"}
    report["environment_gate"] = environment
    if environment.get("status") != "PASS":
        report["blockers"].extend(environment.get("reasons", [environment.get("reason", "Guard QA bloqueou o ambiente.")]))

    manifest = verify_manifest(package_root)
    report["manifest_gate"] = manifest
    if manifest.get("status") != "PASS":
        report["blockers"].append("Manifesto de fonte ausente, desatualizado ou com hash divergente; revise e regenere após revisão.")

    if report["blockers"]:
        print(f"[{utc_now()}] Preflight bloqueado; gravando relatório sem iniciar testes ou builds.", flush=True)
        report["status"] = "BLOCKED"
        report["finished_at"] = utc_now()
        report["duration_seconds"] = round(time.monotonic() - started, 3)
        _write_report(output, report)
        for blocker in report["blockers"]:
            record_step_error(package_root, "preflight", {"status": "BLOCKED", "reason": blocker}, platform.system(), "0.24.0/0.4.1-qa.2")
        _finish_lock(sim_qa, report["run_id"])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    print(f"[{utc_now()}] Preflight aprovado; iniciando testes isolados do clone QA.", flush=True)
    print(f"[{utc_now()}] Preparando o ambiente QA do backend para a suíte de regressão.", flush=True)
    backend_python, backend_setup = ensure_python(sim_qa / "backend", sim_qa / "backend" / "requirements.txt", ["pytest", "fastapi", "sqlalchemy", "alembic", "dotenv", "PIL", "httpx", "jwt"], args.prepare_deps, logs, "sim-backend")
    report["dependency_setup"] = {"sim_backend": backend_setup}

    print(f"[{utc_now()}] Etapa: consistência do manifesto com arquivos voláteis do SQLite.", flush=True)
    manifest_tests = sim_qa / "scripts" / "tests"
    if backend_python:
        result = run([str(backend_python), "-m", "unittest", "discover", "-s", str(manifest_tests), "-p", "test_*.py", "-q"], package_root, logs / "manifest-consistency-tests.log", timeout=60)
    else:
        result = {"status": "BLOCKED", "reason": "Ambiente QA do backend indisponível para a suíte de regressão.", "setup": backend_setup}
    report["tests"].append({"name": "manifest_consistency", **result})
    record_step_error(package_root, "manifest_consistency", result, platform.system(), "0.4.1-qa.2")

    qa_test = sim_qa / "backend" / "tests" / "test_qa_environment.py"
    print(f"[{utc_now()}] Etapa: guard de ambiente QA.", flush=True)
    quick_guard = run([sys.executable, str(qa_test)], sim_qa / "backend", logs / "qa-guard-tests.log", timeout=60)
    report["tests"].append({"name": "qa_environment_guard", **quick_guard})
    record_step_error(package_root, "qa_environment_guard", quick_guard, platform.system(), "0.4.1-qa.2")

    print(f"[{utc_now()}] Etapa: preparar ambiente isolado do NexGrana e executar testes Python.", flush=True)
    nex_python, nex_setup = ensure_python(nex, nex / "requirements-qa.txt", NEX_QA_MODULES, args.prepare_deps, logs, "nex")
    report["dependency_setup"] = {"nex": nex_setup}
    if nex_python:
        result = run([str(nex_python), "-m", "unittest", "discover", "-s", "tests", "-q"], nex, logs / "nex-tests.log", args.timeout)
        report["tests"].append({"name": "nex_python", **result})
        record_step_error(package_root, "nex_python", result, platform.system(), "0.24.0")
    else:
        result = {"name": "nex_python", "status": "BLOCKED", **nex_setup}
        report["tests"].append(result)
        record_step_error(package_root, "nex_python", result, platform.system(), "0.24.0")

    print(f"[{utc_now()}] Etapa: testes do backend e do Collector.", flush=True)
    collector_python, collector_setup = ensure_python(sim_qa / "Collector", sim_qa / "Collector" / "requirements.txt", ["pytest"], args.prepare_deps, logs, "collector")
    report["dependency_setup"]["collector"] = collector_setup
    if backend_python:
        result = run([str(backend_python), "-m", "pytest", "backend/tests", "-q"], sim_qa, logs / "sim-backend-tests.log", args.timeout)
        report["tests"].append({"name": "sim_backend", **result})
        record_step_error(package_root, "sim_backend", result, platform.system(), "0.4.1-qa.2")
    else:
        result = {"name": "sim_backend", "status": "BLOCKED", **backend_setup}
        report["tests"].append(result)
        record_step_error(package_root, "sim_backend", result, platform.system(), "0.4.1-qa.2")
    if collector_python:
        result = run([str(collector_python), "-m", "pytest", "tests", "-q"], sim_qa / "Collector", logs / "collector-tests.log", args.timeout)
        report["tests"].append({"name": "collector", **result})
        record_step_error(package_root, "collector", result, platform.system(), "0.5.0-integrado")
    else:
        result = {"name": "collector", "status": "BLOCKED", **collector_setup}
        report["tests"].append(result)
        record_step_error(package_root, "collector", result, platform.system(), "0.5.0-integrado")

    print(f"[{utc_now()}] Etapa: teste de estado/conexão da Gestão de hoje.", flush=True)
    node = shutil.which("node")
    if node:
        # Invoke the file directly: Node 24's --test mode treated this CJS
        # suite as a single file test in this environment and did not report
        # its two registered cases. Direct invocation runs both node:test
        # assertions and records their individual results in the pipeline log.
        result = run([node, "tests/gestao-hoje.test.cjs"], sim_qa / "frontend", logs / "sim-ui-state.log", timeout=60)
    else:
        result = {"status": "BLOCKED", "reason": "Node.js ausente; teste de estado/conexão da tela de QA não executado."}
    report["tests"].append({"name": "sim_ui_state", **result})
    record_step_error(package_root, "sim_ui_state", result, platform.system(), "0.4.1-qa.2")

    print(f"[{utc_now()}] Etapa: SQL/PGlite e compilação da interface SIM Labs.", flush=True)
    npm = shutil.which("npm")
    if npm:
        ready, setup = npm_check(nex, args.prepare_deps, logs, "nex-sql", nex / "node_modules" / "@electric-sql" / "pglite")
        if ready:
            result = run([npm, "run", "test:sql"], nex, logs / "nex-sql.log", args.timeout)
        else:
            result = setup
        report["tests"].append({"name": "nex_sql", **result})
        record_step_error(package_root, "nex_sql", result, platform.system(), "0.24.0")
        ready, setup = npm_check(sim_qa / "frontend", args.prepare_deps, logs, "sim-frontend", sim_qa / "frontend" / "node_modules" / ".bin" / "vite")
        if ready:
            result = run([npm, "run", "build"], sim_qa / "frontend", logs / "sim-frontend-build.log", args.timeout)
        else:
            result = setup
        report["tests"].append({"name": "sim_frontend_build", **result})
        record_step_error(package_root, "sim_frontend_build", result, platform.system(), "0.4.1-qa.2")
    else:
        for name in ("nex_sql", "sim_frontend_build"):
            result = {"status": "BLOCKED", "reason": "npm ausente"}
            report["tests"].append({"name": name, **result})
            record_step_error(package_root, name, result, platform.system(), "0.24.0/0.4.1-qa.2")

    tests_ok = bool(report["tests"]) and all(item.get("status") == "PASS" for item in report["tests"])
    report["native_validation"] = {"host_windows": platform.system() == "Windows", "installed": False, "device_smoke": "MANUAL_REQUIRED", "supabase_staging": "MANUAL_REQUIRED"}
    if tests_ok and not args.tests_only:
        print(f"[{utc_now()}] Todas as verificações locais passaram; tentando builds suportados pelo host.", flush=True)
        windows_build = build_target(package_root, nex, "windows", nex_python, logs)
        report["builds"].append(windows_build)
        record_step_error(package_root, "build_windows", windows_build, platform.system(), "0.24.0")
        if windows_build.get("status") == "BUILD OK" and args.android:
            print(f"[{utc_now()}] Windows build aprovado; iniciando a tentativa Android em etapa separada.", flush=True)
            android_build = build_target(package_root, nex, "apk", nex_python, logs)
            report["builds"].append(android_build)
            record_step_error(package_root, "build_apk", android_build, platform.system(), "0.24.0")
        else:
            android_build = {"target": "apk", "status": "BLOCKED", "reason": "Android requer etapa separada explicita (--android) apos Windows BUILD PASS."}
            report["builds"].append(android_build)
            record_step_error(package_root, "build_apk", android_build, platform.system(), "0.24.0")
    else:
        for target in ("windows", "apk"):
            report["builds"].append({"target": target, "status": "NOT_RUN" if args.tests_only else "BLOCKED", "reason": "Modo somente testes." if args.tests_only else "Build suspenso porque uma validação local está bloqueada ou falhou."})

    android_build = next((item for item in report["builds"] if item.get("target") == "apk"), {})
    report["status"] = "PRONTA PARA QA REAL" if is_ready_for_windows_qa(report["tests"], report["builds"]) else "BLOCKED"
    if args.tests_only and tests_ok:
        report["status"] = "TESTS_PASS"
    report["summary"] = {
        "tests_passed": sum(item.get("status") == "PASS" for item in report["tests"]),
        "tests_blocked_or_failed": sum(item.get("status") != "PASS" for item in report["tests"]),
        "native_builds_generated": sum(item.get("status") == "BUILD OK" for item in report["builds"]),
        "windows_build_status": next((item.get("status") for item in report["builds"] if item.get("target") == "windows"), "NOT_RUN"),
        "android_build_status": android_build.get("status", "NOT_RUN"),
        "autocorrection": "Nenhuma alteração de código foi aplicada automaticamente; dependências locais podem ser preparadas apenas no clone QA.",
    }
    report["blockers"].extend(item.get("reason") or item.get("tail") or (item.get("name", "teste") + ": consulte o log") for item in report["tests"] if item.get("status") != "PASS")
    report["blockers"].extend(item.get("reason", "") for item in report["builds"] if item.get("target") == "windows" and item.get("status") not in {"BUILD OK", "NOT_RUN"})
    report["finished_at"] = utc_now()
    report["duration_seconds"] = round(time.monotonic() - started, 3)
    _write_report(output, report)
    _finish_lock(sim_qa, report["run_id"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PRONTA PARA QA REAL", "TESTS_PASS"} else 2


def _write_report(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    report["report_path"] = "pipeline-report.json"
    tmp = output / "pipeline-report.json.tmp"
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, output / "pipeline-report.json")
    lines = ["# Execução do pipeline QA", "", f"- Estado: **{report.get('status')}**", f"- Início: `{report.get('created_at')}`", f"- Fim: `{report.get('finished_at', 'em andamento')}`", "", "## Testes"]
    lines += [f"- `{item.get('name')}` — **{item.get('status')}**" for item in report.get("tests", [])]
    lines += ["", "## Builds nativos"]
    lines += [f"- `{item.get('target')}` — **{item.get('status')}** — {item.get('reason', 'sem smoke test automático')}" for item in report.get("builds", [])]
    lines += ["", "## Bloqueios"]
    lines += [f"- {item}" for item in report.get("blockers", []) if item]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _finish_lock(sim_qa: Path, run_id: str) -> None:
    lock = sim_qa / "data" / "qa_pipeline" / "active.lock"
    try:
        current = json.loads(lock.read_text(encoding="utf-8"))
        if current.get("run_id") == run_id:
            lock.unlink()
    except (OSError, ValueError):
        return


if __name__ == "__main__":
    raise SystemExit(main())
