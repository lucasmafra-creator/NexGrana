"""Validação reproduzível da candidata NexGrana 0.24.0.

Uso:
  py validate_release.py          # validações que não exigem UI/network
  py validate_release.py --full   # inclui toda a suíte (requer requirements instalados)
"""
from __future__ import annotations

import argparse
import compileall
import hashlib
import importlib.util
import json
import struct
import tomllib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = [
    ROOT / "src" / "main.py",
    ROOT / "src" / "cloud.py",
    ROOT / "src" / "services" / "finance_engine.py",
    ROOT / "src" / "services" / "investment_engine.py",
    ROOT / "src" / "services" / "nex_engine.py",
    ROOT / "src" / "services" / "nex_gateway.py",
    ROOT / "src" / "services" / "nex_conversation.py",
    ROOT / "src" / "services" / "tutorial.py",
    ROOT / "src" / "screens" / "tutorial.py",
    ROOT / "src" / "assets" / "nex" / "nex_hd.png",
    ROOT / "src" / "assets" / "icon.png",
    ROOT / "MIGRATION_0_18.sql",
    ROOT / "SQL_ATOMIC_0_18.sql",
    ROOT / "MIGRATION_0_18_1.sql",
    ROOT / "MIGRATION_0_19.sql",
    ROOT / "MIGRATION_0_20.sql",
    ROOT / "MIGRATION_0_21.sql",
    ROOT / "MIGRATION_0_22.sql",
    ROOT / "MIGRATION_0_23.sql",
    ROOT / "MIGRATION_0_24.sql",
    ROOT / "MIGRATION_0_24_1.sql",
    ROOT / "MIGRATION_0_24_2.sql",
    ROOT / "src" / "screens" / "investments.py",
    ROOT / "src" / "services" / "analytics.py",
    ROOT / "src" / "services" / "offers.py",
    ROOT / "src" / "services" / "performance.py",
    ROOT / "src" / "build_config.py",
    ROOT / "admin" / "achados_admin.py",
    ROOT / "gateway" / "app.py",
    ROOT / "gateway" / "core.py",
    ROOT / "gateway" / "requirements.txt",
    ROOT / "pyproject.toml",
    ROOT / "AUDITORIA_0_23_0.md",
    ROOT / "ATUALIZACAO_0_23_0.md",
    ROOT / "MATRIZ_REQUISITOS_0_23_0.md",
    ROOT / "VALIDACAO_0_23_0.md",
    ROOT / "SEGURANCA_0_23_0.md",
    ROOT / "PERFORMANCE_0_23_0.md",
    ROOT / "NEX_GATEWAY_0_23_0.md",
    ROOT / "MAPA_TELAS_0_23_0.md",
    ROOT / "LEIA_PRIMEIRO_0_23_0.txt",
    ROOT / "RELATORIO_FINAL_0_23_0.md",
    ROOT / "GOLDEN_NEX_0_23_0.md",
    ROOT / "gateway" / "config.example.txt",
    ROOT / "security_scan.py",
    ROOT / "COMANDOS_0_23_0_WINDOWS_ANDROID_IOS.txt",
]

CORE_TESTS = ["tests.test_finance", "tests.test_investments", "tests.test_services", "tests.test_nex_engine", "tests.test_nex_conversation", "tests.test_nex_vivo", "tests.test_tutorial", "tests.test_product_019", "tests.test_product_experience", "tests.test_admin_offers", "tests.test_gateway_server"]
APPROVED_ICON_SHA256 = "36296882b0715a91fa0c751cdbc741d1efd1d7c054ec4da002959758d0c3284f"


def run(cmd: list[str]) -> int:
    print("+", subprocess.list2cmdline(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Executa toda a suíte; requer Flet e Supabase instalados")
    args = parser.parse_args()

    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.exists()]
    if missing:
        print("ARQUIVOS OBRIGATÓRIOS AUSENTES:", ", ".join(missing))
        return 2

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project.get("project", {}).get("version")
    if version != "0.24.0":
        print("VERSÃO INCONSISTENTE NO PYPROJECT")
        return 6
    build_text = (ROOT / "build_multiplataforma.py").read_text(encoding="utf-8")
    if "VERSION = '0.24.0'" not in build_text:
        print("VERSÃO INCONSISTENTE NO SCRIPT DE BUILD")
        return 6
    flet_config = project.get("tool", {}).get("flet", {})
    android_dependencies = set(flet_config.get("android", {}).get("dependencies") or [])
    windows_dependencies = set(flet_config.get("windows", {}).get("dependencies") or [])
    if ("cryptography==43.0.1" not in android_dependencies
            or "pillow==12.2.0" not in android_dependencies
            or "cryptography==48.0.0" not in windows_dependencies
            or "pillow==12.3.0" not in windows_dependencies):
        print("DEPENDÊNCIAS DE BUILD INCONSISTENTES: confira as wheels Android e Windows")
        return 6

    manifest = json.loads((ROOT / "src" / "assets" / "nex" / "manifest.json").read_text(encoding="utf-8"))
    variants = manifest.get("variants") or {}
    for role in ("hero", "card", "avatar", "dock"):
        rel = variants.get(role)
        if not rel or not (ROOT / "src" / "assets" / rel).exists():
            print(f"ASSET NEX AUSENTE: {role}")
            return 7
        if str(rel).lower().endswith(".gif"):
            print(f"GIF LEGADO NÃO PERMITIDO NO NEX: {role}")
            return 7
    icon_bytes = (ROOT / "src" / "assets" / "icon.png").read_bytes()
    if not icon_bytes.startswith(b"\x89PNG\r\n\x1a\n") or len(icon_bytes) < 24:
        print("ÍCONE 0.23 NÃO É PNG VÁLIDO")
        return 7
    width, height = struct.unpack(">II", icon_bytes[16:24])
    icon_digest = hashlib.sha256(icon_bytes).hexdigest()
    if width != height or width < 1024 or icon_digest != APPROVED_ICON_SHA256:
        print(f"ÍCONE 0.23 INCONSISTENTE: {width}x{height} {icon_digest}")
        return 7
    print("versão/manifesto Nex: OK")
    print(f"ícone 0.23: OK ({width}x{height})")

    if not compileall.compile_dir(ROOT / "src", quiet=1):
        print("compileall: FALHOU")
        return 3
    print("compileall: OK")
    if not compileall.compile_dir(ROOT / "admin", quiet=1):
        print("compileall admin: FALHOU")
        return 3
    if not compileall.compile_dir(ROOT / "gateway", quiet=1):
        print("compileall gateway: FALHOU")
        return 3

    migration="\n".join((ROOT/name).read_text(encoding="utf-8") for name in
                        ("MIGRATION_0_21.sql","MIGRATION_0_22.sql","MIGRATION_0_23.sql","MIGRATION_0_24.sql","MIGRATION_0_24_1.sql","MIGRATION_0_24_2.sql"))
    for contract in ("is_app_admin", "affiliate_offer_audit", "reset_qa_workspace", "search_tags", "image_alt", "http2[.]mlstatic"):
        if contract not in migration:
            print("CONTRATO SQL 0.21 AUSENTE:",contract)
            return 8

    tests = [sys.executable, "-m", "unittest"]
    if args.full:
        for dep in ("flet", "supabase"):
            if importlib.util.find_spec(dep) is None:
                print(f"Dependência ausente para --full: {dep}")
                return 4
        tests += ["discover", "-s", "tests", "-v"]
    else:
        tests += [*CORE_TESTS, "-v"]
    if run(tests):
        return 5
    if run([sys.executable, "security_scan.py"]):
        return 9

    digest = hashlib.sha256((ROOT / "src" / "assets" / "nex" / "nex_hd.png").read_bytes()).hexdigest()
    print("Nex HD SHA256:", digest)
    print("VALIDAÇÃO CONCLUÍDA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
