"""Validação reproduzível da candidata NexGrana 0.19.0.

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
import tomllib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = [
    ROOT / "src" / "main.py",
    ROOT / "src" / "cloud.py",
    ROOT / "src" / "services" / "finance_engine.py",
    ROOT / "src" / "services" / "nex_engine.py",
    ROOT / "src" / "assets" / "nex" / "nex_hd.png",
    ROOT / "MIGRATION_0_18.sql",
    ROOT / "SQL_ATOMIC_0_18.sql",
    ROOT / "MIGRATION_0_18_1.sql",
    ROOT / "MIGRATION_0_19.sql",
    ROOT / "src" / "services" / "analytics.py",
    ROOT / "src" / "services" / "offers.py",
    ROOT / "src" / "services" / "performance.py",
    ROOT / "pyproject.toml",
]

CORE_TESTS = ["tests.test_finance", "tests.test_services", "tests.test_nex_engine", "tests.test_product_019"]


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
    if project.get("project", {}).get("version") != "0.19.0":
        print("VERSÃO INCONSISTENTE NO PYPROJECT")
        return 6
    build_text = (ROOT / "build_multiplataforma.py").read_text(encoding="utf-8")
    if "VERSION = '0.19.0'" not in build_text:
        print("VERSÃO INCONSISTENTE NO SCRIPT DE BUILD")
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
    print("versão/manifesto Nex: OK")

    if not compileall.compile_dir(ROOT / "src", quiet=1):
        print("compileall: FALHOU")
        return 3
    print("compileall: OK")

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

    digest = hashlib.sha256((ROOT / "src" / "assets" / "nex" / "nex_hd.png").read_bytes()).hexdigest()
    print("Nex HD SHA256:", digest)
    print("VALIDAÇÃO CONCLUÍDA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
