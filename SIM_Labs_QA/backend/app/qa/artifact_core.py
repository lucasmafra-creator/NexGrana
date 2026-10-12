"""Local SIM Labs build intake and QA helpers.

The default path inspects artifacts without executing them. Project tests run
only after an explicit user action in the desktop UI.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_ENTRIES = 50_000
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000
DEFAULT_TEST_TIMEOUT_SECONDS = 900

MANUAL_CHECKS = [
    ("windows_open", "Windows: abrir o app e navegar pelas telas principais"),
    ("android_open", "Android: instalar/abrir o APK em dispositivo de teste"),
    ("login_first_access", "Login: conferir mensagem clara quando o primeiro acesso está offline"),
    ("month_rollover", "Financeiro: conferir saldo transportado e lançamento atrasado na virada do mês"),
    ("qa_reset", "Homologação: testar reset somente na conta/ambiente QA autorizado"),
    ("android_chat_keyboard", "Android: enviar mensagens com teclado aberto sem trocar de tela nem perder foco"),
    ("android_chat_history", "Android: conferir histórico, conversas fixadas e ausência de mensagens duplicadas"),
    ("market_lists", "Mercado: iniciar compra a partir de uma lista e confirmar/editar itens"),
    ("tutorial", "Treinamento: percorrer as atividades e verificar salvamento do progresso"),
    ("nex_skins", "Nex: escolher uma skin, trocar para automático e conferir o retorno à escolha manual"),
    ("privacy", "Privacidade: validar perfil ativo e não expor dados de outros perfis"),
]


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check(check_id: str, label: str, status: str, detail: str) -> dict:
    return {"id": check_id, "label": label, "status": status, "detail": detail}


def _safe_member_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    return not path.is_absolute() and all(part not in ("..", "") for part in path.parts)


def _zip_safety(archive: zipfile.ZipFile) -> tuple[list[dict], list[zipfile.ZipInfo]]:
    checks: list[dict] = []
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        checks.append(_check("zip_entry_count", "Quantidade de arquivos", "FAIL",
                             f"O ZIP tem {len(infos)} entradas; limite local: {MAX_ARCHIVE_ENTRIES}."))
        return checks, infos

    total = 0
    unsafe = []
    encrypted = []
    oversized = []
    for info in infos:
        if info.is_dir():
            continue
        total += info.file_size
        mode = (info.external_attr >> 16) & 0o170000
        if not _safe_member_name(info.filename) or mode == stat.S_IFLNK:
            unsafe.append(info.filename)
        if info.flag_bits & 0x1:
            encrypted.append(info.filename)
        if info.file_size and info.file_size > max(MAX_UNCOMPRESSED_BYTES, 20 * MAX_MEMBER_BYTES):
            oversized.append(info.filename)
        ratio = info.file_size / max(1, info.compress_size)
        if ratio > MAX_COMPRESSION_RATIO and info.file_size > 10 * 1024 * 1024:
            oversized.append(info.filename)

    checks.append(_check("zip_paths", "Caminhos do pacote", "FAIL" if unsafe else "PASS",
                         "Há caminhos inseguros ou links simbólicos." if unsafe else "Sem caminhos fora da pasta do pacote."))
    too_large = total > MAX_UNCOMPRESSED_BYTES or bool(oversized)
    checks.append(_check("zip_size", "Tamanho descompactado", "FAIL" if too_large else "PASS",
                         f"{total / (1024 * 1024):.1f} MB após descompactar." +
                         (" Limite local excedido." if too_large else "")))
    checks.append(_check("zip_encryption", "Acesso às entradas", "BLOCKED" if encrypted else "PASS",
                         "Há arquivos criptografados; não consigo validá-los." if encrypted else "Entradas sem senha."))
    return checks, infos


def _zip_test_crc(archive: zipfile.ZipFile) -> dict:
    try:
        bad_member = archive.testzip()
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        return _check("zip_crc", "Integridade interna do ZIP", "FAIL", f"Falha ao ler o ZIP: {type(exc).__name__}.")
    if bad_member:
        return _check("zip_crc", "Integridade interna do ZIP", "FAIL", f"CRC inválido em {bad_member}.")
    return _check("zip_crc", "Integridade interna do ZIP", "PASS", "Entradas descompactadas e CRC conferido.")


def _read_zip_json(archive: zipfile.ZipFile, infos: list[zipfile.ZipInfo], basename: str) -> tuple[str | None, dict | None]:
    matches = [i for i in infos if PurePosixPath(i.filename.replace("\\", "/")).name.lower() == basename.lower()]
    matches.sort(key=lambda i: (i.filename.count("/"), len(i.filename)))
    for info in matches:
        if info.file_size > MAX_MEMBER_BYTES:
            continue
        try:
            value = json.loads(archive.read(info).decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, RuntimeError):
            continue
        if isinstance(value, dict):
            return info.filename, value
    return None, None


def _version_from_zip(infos: list[zipfile.ZipInfo], archive: zipfile.ZipFile) -> str | None:
    for name in ("manifest.json", "MANIFEST_RELEASE_0_24_0.json", "build_info.json"):
        _, data = _read_zip_json(archive, infos, name)
        if data:
            version = data.get("version_under_test") or data.get("release") or data.get("version")
            if version:
                return str(version)
    for info in infos:
        basename = PurePosixPath(info.filename.replace("\\", "/")).name
        if basename.lower() == "pyproject.toml" and info.file_size <= MAX_MEMBER_BYTES:
            try:
                import re
                text = archive.read(info).decode("utf-8", errors="replace")
                match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)', text)
                if match:
                    return match.group(1)
            except (OSError, RuntimeError):
                pass
    return None


def _tool_check(binary: str, args: list[str], check_id: str, label: str, timeout: int = 25) -> dict:
    executable = shutil.which(binary)
    if not executable:
        return _check(check_id, label, "BLOCKED", f"{binary} não encontrado no PATH.")
    try:
        proc = subprocess.run([executable, *args], capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _check(check_id, label, "BLOCKED", f"Não foi possível executar {binary}: {type(exc).__name__}.")
    output = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = " ".join(output[:3])[:600] or f"{binary} retornou código {proc.returncode}."
    return _check(check_id, label, "PASS" if proc.returncode == 0 else "FAIL", detail)


def inspect_build(path: str | Path, target: str = "Detectar") -> dict:
    """Inspect a build/source archive. Never starts the app binary."""
    source = Path(path).expanduser().resolve()
    checks: list[dict] = []
    if not source.is_file():
        return {"path": str(source), "name": source.name, "target": target, "checks": [
            _check("file_exists", "Arquivo recebido", "FAIL", "O caminho não aponta para um arquivo.")],
            "overall": "FAIL", "sha256": None, "version": None, "artifact_type": "desconhecido"}
    size = source.stat().st_size
    checks.append(_check("file_exists", "Arquivo recebido", "PASS" if size else "FAIL",
                         f"{size / (1024 * 1024):.2f} MB." if size else "Arquivo vazio."))
    digest = sha256_file(source)
    checks.append(_check("sha256", "Identificação SHA-256", "PASS", digest))
    suffix = source.suffix.lower()
    version = None
    feedback_ids: list[str] = []
    artifact_type = "desconhecido"

    if suffix in {".zip", ".apk", ".aab", ".xapk"} or zipfile.is_zipfile(source):
        try:
            with zipfile.ZipFile(source) as archive:
                zip_checks, infos = _zip_safety(archive)
                checks.extend(zip_checks)
                if any(c["status"] == "FAIL" for c in zip_checks):
                    artifact_type = "arquivo ZIP bloqueado"
                else:
                    checks.append(_zip_test_crc(archive))
                    names = {i.filename.replace("\\", "/").lower() for i in infos if not i.is_dir()}
                    if suffix == ".apk":
                        artifact_type = "APK Android"
                        has_manifest = "androidmanifest.xml" in names
                        has_dex = any(PurePosixPath(n).name.startswith("classes") and n.endswith(".dex") for n in names)
                        checks.append(_check("apk_manifest", "Manifesto Android", "PASS" if has_manifest else "FAIL",
                                             "AndroidManifest.xml encontrado." if has_manifest else "AndroidManifest.xml ausente."))
                        checks.append(_check("apk_dex", "Código do aplicativo", "PASS" if has_dex else "WARN",
                                             "Arquivo DEX encontrado." if has_dex else "Nenhum classes*.dex identificado."))
                        checks.append(_tool_check("apksigner", ["verify", "--verbose", str(source)], "apk_signature", "Assinatura APK"))
                        checks.append(_tool_check("aapt", ["dump", "badging", str(source)], "apk_metadata", "Metadados APK"))
                        adb = shutil.which("adb")
                        if adb:
                            checks.append(_tool_check("adb", ["devices"], "android_devices", "Dispositivos Android conectados"))
                        else:
                            checks.append(_check("android_devices", "Dispositivo Android", "BLOCKED", "adb não encontrado; o APK não foi instalado nem testado em dispositivo."))
                    elif suffix == ".aab":
                        artifact_type = "Android App Bundle"
                        bundle_manifest = any(n.endswith("base/manifest/AndroidManifest.xml") for n in names)
                        checks.append(_check("aab_manifest", "Manifesto do App Bundle", "PASS" if bundle_manifest else "WARN",
                                             "Manifesto base encontrado." if bundle_manifest else "Manifesto base não identificado."))
                        checks.append(_tool_check("bundletool", ["validate", f"--bundle={source}"], "aab_validate", "Validação do App Bundle"))
                    else:
                        artifact_type = "pacote ZIP / código-fonte"
                        version = _version_from_zip(infos, archive)
                        _, ingest = _read_zip_json(archive, infos, "SIM_LABS_INGEST.json")
                        _, manifest = _read_zip_json(archive, infos, "manifest.json")
                        if ingest:
                            records = ingest.get("records", [])
                            feedback_ids = [str(r.get("feedback_id")) for r in records if r.get("feedback_id")]
                            checks.append(_check("feedback_contract", "Contrato de feedback SIM Labs", "PASS",
                                                 f"{len(feedback_ids)} registros para vincular ao build."))
                        elif manifest and str(manifest.get("schema", "")).startswith("nexgrana.update_collector"):
                            records = manifest.get("items", [])
                            feedback_ids = [str(r.get("id")) for r in records if r.get("id")]
                            checks.append(_check("feedback_contract", "Pacote do Update Collector", "PASS",
                                                 f"{len(feedback_ids)} registros identificados no manifesto."))
                        source_files = {PurePosixPath(n).name.lower() for n in names}
                        if "pyproject.toml" in source_files or "package.json" in source_files:
                            artifact_type = "código-fonte de app"
                            has_tests = any("/tests/" in f"/{n}" or PurePosixPath(n).parts[0].lower() == "tests" for n in names)
                            checks.append(_check("source_tests", "Suíte de testes", "PASS" if has_tests else "WARN",
                                                 "Arquivos de teste encontrados; execução requer ação explícita." if has_tests else "Não encontrei uma pasta de testes."))
                        else:
                            checks.append(_check("source_tests", "Suíte de testes", "BLOCKED",
                                                 "Este ZIP não parece conter uma base de código testável."))
                        expected_evidence = set()
                        for record in (manifest or {}).get("items", []):
                            expected_evidence.update(record.get("_export_evidence", []))
                        missing_evidence = [p for p in expected_evidence if p.lower() not in names]
                        if expected_evidence:
                            checks.append(_check("feedback_evidence", "Referências de evidência", "WARN" if missing_evidence else "PASS",
                                                 (f"{len(missing_evidence)} referência(s) não aparecem nesta parte do ZIP; selecione todas as partes." if missing_evidence
                                                  else f"{len(expected_evidence)} referência(s) presentes.")))
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            artifact_type = "ZIP inválido"
            checks.append(_check("zip_open", "Estrutura ZIP", "FAIL", f"Não consegui validar: {type(exc).__name__}."))
    elif suffix == ".exe":
        artifact_type = "Executável Windows"
        try:
            with source.open("rb") as stream:
                header = stream.read(64)
                is_pe = len(header) >= 64 and header[:2] == b"MZ"
                offset = int.from_bytes(header[60:64], "little") if is_pe else 0
                stream.seek(offset)
                signature = stream.read(4) if is_pe else b""
            valid = is_pe and signature == b"PE\0\0"
        except OSError:
            valid = False
        checks.append(_check("windows_pe", "Formato executável Windows", "PASS" if valid else "FAIL",
                             "Cabeçalho PE válido." if valid else "O arquivo não tem um cabeçalho PE válido."))
        if os.name == "nt":
            ps = shutil.which("powershell") or shutil.which("pwsh")
            if ps:
                script = "$s=Get-AuthenticodeSignature -LiteralPath $args[0]; Write-Output $s.Status; if($s.Status -ne 'Valid'){exit 1}"
                checks.append(_tool_check(ps, ["-NoProfile", "-Command", script, str(source)], "windows_signature", "Assinatura Authenticode"))
            else:
                checks.append(_check("windows_signature", "Assinatura Authenticode", "BLOCKED", "PowerShell não encontrado."))
        else:
            checks.append(_check("windows_signature", "Assinatura Authenticode", "BLOCKED", "Verificação disponível no Windows; não executei o EXE."))
    elif suffix in {".msi", ".msix", ".appx"}:
        artifact_type = "Instalador Windows"
        checks.append(_check("installer_platform", "Formato do instalador", "WARN",
                             "Registrei o instalador; instalação e abertura não são executadas automaticamente."))
    else:
        checks.append(_check("artifact_type", "Tipo de arquivo", "BLOCKED", f"Extensão {suffix or '(sem extensão)'} não suportada."))

    statuses = [c["status"] for c in checks]
    overall = "FAIL" if "FAIL" in statuses else ("BLOCKED" if "BLOCKED" in statuses else ("WARN" if "WARN" in statuses else "PASS"))
    return {"path": str(source), "name": source.name, "size_bytes": size, "target": target,
            "artifact_type": artifact_type, "sha256": digest, "version": version,
            "feedback_ids": feedback_ids, "checks": checks, "overall": overall,
            "inspected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def _strip_secret_environment() -> dict[str, str]:
    blocked = ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD", "SUPABASE", "DATABASE_URL", "CREDENTIAL")
    env = {key: value for key, value in os.environ.items() if not any(term in key.upper() for term in blocked)}
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1"})
    return env


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination_resolved = destination.resolve()
    for info in archive.infolist():
        if info.is_dir():
            continue
        if not _safe_member_name(info.filename):
            raise ValueError(f"Caminho inseguro no pacote: {info.filename}")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise ValueError(f"Link simbólico não permitido: {info.filename}")
        target = (destination / PurePosixPath(info.filename.replace("\\", "/"))).resolve()
        if destination_resolved not in target.parents:
            raise ValueError(f"Arquivo fora da pasta temporária: {info.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def _find_source_root(extracted: Path) -> Path:
    candidates = [p.parent for p in extracted.rglob("pyproject.toml")]
    candidates += [p.parent for p in extracted.rglob("package.json")]
    candidates += [p.parent for p in extracted.rglob("requirements.txt")]
    for candidate in candidates:
        if (candidate / "tests").is_dir() or (candidate / "test").is_dir():
            return candidate
    for candidate in candidates:
        return candidate
    return extracted


def run_source_tests(path: str | Path, timeout: int = DEFAULT_TEST_TIMEOUT_SECONDS) -> dict:
    """Extract a trusted source ZIP to a temporary folder and run local tests.

    The caller must ask before invoking this function. No package manager is
    allowed to download dependencies. Test code still executes with the current
    user's permissions; the runner removes common secret variables and enforces
    a timeout, but it does not provide an OS/network sandbox.
    """
    source = Path(path).expanduser().resolve()
    report = {"schema": "sim-labs.test-run/1.0", "source": str(source), "checks": [], "overall": "BLOCKED"}
    if source.suffix.lower() != ".zip" or not source.is_file():
        report["checks"].append(_check("source_zip", "Pacote de código", "BLOCKED", "Selecione um ZIP com código-fonte."))
        return report
    try:
        with zipfile.ZipFile(source) as archive:
            safety, infos = _zip_safety(archive)
            report["checks"].extend(safety)
            if any(c["status"] in ("FAIL", "BLOCKED") for c in safety):
                report["overall"] = "FAIL"
                return report
            if _zip_test_crc(archive)["status"] != "PASS":
                report["checks"].append(_zip_test_crc(archive))
                report["overall"] = "FAIL"
                return report
            with tempfile.TemporaryDirectory(prefix="sim_labs_tests_") as temp:
                extracted = Path(temp)
                _safe_extract(archive, extracted)
                root = _find_source_root(extracted)
                py_files = list(root.rglob("*.py"))
                if py_files:
                    compile_cmd = [sys.executable, "-m", "compileall", "-q", str(root)]
                    report["checks"].append(_run_command_check("python_compile", "Compilação sintática Python", compile_cmd,
                                                               root, timeout, _strip_secret_environment()))
                test_dir = next((root / name for name in ("tests", "test") if (root / name).is_dir()), None)
                if test_dir and shutil.which(sys.executable):
                    pytest_available = subprocess.run([sys.executable, "-m", "pytest", "--version"], cwd=root,
                                                      capture_output=True, text=True, timeout=20, check=False).returncode == 0
                    if pytest_available:
                        env = _strip_secret_environment()
                        existing = env.get("PYTHONPATH", "")
                        src_dir = root / "src"
                        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(src_dir if src_dir.is_dir() else root), existing]))
                        report["checks"].append(_run_command_check("python_tests", "Testes Python", [sys.executable, "-m", "pytest", "-q"],
                                                                   root, timeout, env))
                    else:
                        report["checks"].append(_check("python_tests", "Testes Python", "BLOCKED",
                                                       "pytest não está instalado; nenhum pacote foi baixado."))
                elif (root / "package.json").is_file():
                    try:
                        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
                        has_test = "test" in (package.get("scripts") or {})
                    except (OSError, json.JSONDecodeError):
                        has_test = False
                    if has_test and shutil.which("npm"):
                        report["checks"].append(_run_command_check("node_tests", "Testes Node", [shutil.which("npm"), "test", "--", "--runInBand"],
                                                                   root, timeout, _strip_secret_environment()))
                    else:
                        report["checks"].append(_check("node_tests", "Testes Node", "BLOCKED",
                                                       "npm ou script test não disponível; não instalei dependências."))
                else:
                    report["checks"].append(_check("tests_found", "Suíte de testes", "BLOCKED",
                                                   "Não encontrei uma pasta tests/ ou um script Node testável."))
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        report["checks"].append(_check("runner_error", "Execução da suíte", "FAIL",
                                       f"{type(exc).__name__}: {str(exc)[:500]}"))
    statuses = [c["status"] for c in report["checks"]]
    report["overall"] = "FAIL" if "FAIL" in statuses else ("BLOCKED" if "BLOCKED" in statuses else ("WARN" if "WARN" in statuses else "PASS"))
    report["executed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["execution_note"] = "Testes do pacote executam código com as permissões do usuário. O runner não isola rede/processos; execute apenas código confiável."
    return report


def _run_command_check(check_id: str, label: str, command: list[str], cwd: Path,
                       timeout: int, env: dict[str, str]) -> dict:
    try:
        proc = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                              timeout=max(1, int(timeout)), check=False)
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        output = output.strip()
        return _check(check_id, label, "PASS" if proc.returncode == 0 else "FAIL",
                      f"exit={proc.returncode}; " + (output[-5_000:] if output else "sem saída"))
    except subprocess.TimeoutExpired:
        return _check(check_id, label, "FAIL", f"Tempo limite de {timeout}s excedido.")
    except OSError as exc:
        return _check(check_id, label, "BLOCKED", f"Não consegui iniciar o comando: {type(exc).__name__}.")


def import_feedback_package(path: str | Path) -> dict:
    """Read Collector package records while preserving their original IDs."""
    source = Path(path).expanduser().resolve()
    with zipfile.ZipFile(source) as archive:
        safety, infos = _zip_safety(archive)
        if any(c["status"] == "FAIL" for c in safety):
            raise ValueError("O ZIP contém caminhos inseguros ou ultrapassa os limites locais.")
        _, manifest = _read_zip_json(archive, infos, "manifest.json")
        _, ingest = _read_zip_json(archive, infos, "SIM_LABS_INGEST.json")
        if not manifest and not ingest:
            raise ValueError("Não encontrei manifest.json nem SIM_LABS_INGEST.json.")
        records = []
        manifest_items = {str(item.get("id")): item for item in (manifest or {}).get("items", []) if item.get("id")}
        source_records = (ingest or {}).get("records") or (manifest or {}).get("items") or []
        for source_item in source_records:
            item = dict(manifest_items.get(str(source_item.get("feedback_id") or source_item.get("id")), {}))
            item.update(source_item)
            record_id = item.get("feedback_id") or item.get("id")
            if not record_id:
                continue
            records.append({
                "feedback_id": str(record_id),
                "number": item.get("number"),
                "title": item.get("title") or "Feedback sem título",
                "kind": item.get("kind") or "Melhoria",
                "priority": item.get("severity") or item.get("priority") or "P2 - Relevante",
                "category": item.get("category") or "Outro",
                "platform": item.get("platform") or "Multiplataforma",
                "screen": item.get("screen") or "",
                "collector_status": item.get("status") or "Aberto",
                "description": item.get("description") or "",
                "current": item.get("current") or "",
                "expected": item.get("expected") or "",
                "solution": item.get("solution") or "",
                "notes": item.get("notes") or "",
                "evidence": item.get("evidence") or item.get("_export_evidence") or [],
                "release": (ingest or {}).get("release") or (manifest or {}).get("version_under_test"),
            })
        if len({r["feedback_id"] for r in records}) != len(records):
            raise ValueError("O pacote contém IDs de feedback repetidos.")
        return {"source": str(source), "release": (ingest or {}).get("release") or (manifest or {}).get("version_under_test"),
                "records": records, "imported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def render_report_markdown(report: dict) -> str:
    lines = ["# Relatório SIM Labs", "", f"- Artefato: `{report.get('name', 'não informado')}`",
             f"- Alvo: {report.get('target', 'não informado')}",
             f"- Tipo: {report.get('artifact_type', 'não informado')}",
             f"- Versão detectada: {report.get('version') or 'não identificada'}",
             f"- SHA-256: `{report.get('sha256') or 'não disponível'}`",
             f"- Resultado estrutural: **{report.get('overall', 'BLOCKED')}**", "", "## Verificações", ""]
    for check in report.get("checks", []):
        lines.append(f"- **{check.get('status')}** — {check.get('label')}: {check.get('detail')}")
    if report.get("feedback_ids"):
        lines += ["", "## Feedbacks relacionados", ""]
        lines += [f"- `{item}` — requer validação funcional; o resultado de build/teste não fecha o feedback sozinho." for item in report["feedback_ids"]]
    lines += ["", "## Limite da automação", "",
              "A análise estrutural não abre o aplicativo. O teste de código requer ação explícita; a validação visual no Windows/Android e a confirmação do usuário permanecem etapas próprias.", ""]
    return "\n".join(lines)
