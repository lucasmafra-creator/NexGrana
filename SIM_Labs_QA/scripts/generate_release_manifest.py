#!/usr/bin/env python3
"""Create a deterministic, secret-excluding manifest for the RC8 QA bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EXCLUDED_PARTS = {".data", "scratch", "backups", ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".runtime", "dist", "build", "target"}
EXCLUDED_SUFFIXES = {".tsbuildinfo", ".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".sqlite-wal", ".sqlite-shm", ".sqlite-journal", ".db-wal", ".db-shm", ".db-journal", ".log", ".exe", ".apk", ".msi", ".msix", ".p12", ".pfx", ".pem", ".key"}
TREES = ("NexGrana", "SIM_Labs", "SIM_Labs_QA", "tools")
ROOT_FILES = ("LEIA_PRIMEIRO.md", "PROJECT_STATE.md", "NEXGRANA_RULES.md", "BUILD_STATUS.md", "QA_REPORT.md", "CHANGELOG.md", "INICIAR.cmd", "REPARAR_E_INICIAR_SIM_LABS_QA.cmd", "REPARAR_E_INICIAR_SIM_LABS_QA.ps1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def excluded(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if path.name.lower() == ".env" or path.name.lower().startswith(".env."):
        return True
    if len(path.parts) > 1 and path.parts[0] == "SIM_Labs_QA" and path.parts[1] == "data":
        return True
    if len(path.parts) > 1 and path.parts[0] == "tools" and path.parts[1] == "inventory-output":
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    output = (args.output or (root / "release_manifest.json")).resolve()
    output.relative_to(root)
    entries = []
    for tree in TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if excluded(path.relative_to(root)):
                continue
            if path.is_symlink():
                raise SystemExit(f"Symlink não permitido dentro do bundle fonte: {path.relative_to(root)}")
            if not path.is_file() or excluded(path.relative_to(root)):
                continue
            entries.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    for name in ROOT_FILES:
        path=root/name
        if path.is_file():
            entries.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    entries.sort(key=lambda item: item["path"])
    if not entries:
        raise SystemExit("Nenhuma fonte foi encontrada; manifesto não será gravado.")
    manifest = {
        "schema": "nexgrana-sim-labs.release-manifest/1.0",
        "bundle_id": "RC8-QA-RESCUE-20261011-HOTFIX-03",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "SOURCE_BUNDLE_UNBUILT",
        "environment_expected": "Windows QA para builds nativos; staging Supabase separado, chamado qa-* ou staging-*; dados sintéticos",
        "components": {
            "NexGrana": {"source_version": "0.24.0", "delivery_patch": "RC8-QA-STABILITY-20261009", "build": "NOT_GENERATED", "scope": "Windows e Android; iOS posterior; Nex Online adiado"},
            "SIM_Labs_official_baseline": {"source_version": "RC8 baseline / pacote 0.4.x", "status": "SNAPSHOT_UNCHANGED; not compared with installed Windows copy"},
            "SIM_Labs_QA": {"source_version": "0.4.1-qa.2", "status": "CLONE_QA_SOURCE; Windows test-fixture, nested-dependency, safe overlay-reconciliation and truncated Nex skin asset repair included; no EXE generated"},
            "Collector": {"source_version": "0.5.0-integrado", "status": "INHERITED_IN_QA_CLONE; no EXE generated"},
            "Engine": {"source_version": "0.4.1-qa.2-engine", "status": "QA_CLONE_PATCHSET; see QA_REPORT.md for executed evidence"},
            "Observer": {"source_version": None, "status": "NO_SEPARATE_VERSIONED_COMPONENT_FOUND; supervisor checks remain part of SIM Labs"},
            "Bridge": {"source_version": "0.5.0-integrado (Collector bridge file; no independent tag found)", "status": "INHERITED_COMPONENT"},
            "Runner": {"source_version": "pipeline/1.0", "status": "LOCAL_QA_ONLY; no arbitrary path or uploaded source execution"},
        },
        "migrations": {
            "NexGrana_latest": "0.25.6; verified in RC8 report with PGlite only; Supabase staging not applied",
            "SIM_Labs_latest": "0007_qa_operations; new QA migration; not applied to any persistent database",
        },
        "dependency_lock_sources": [
            "NexGrana/requirements.txt", "NexGrana/requirements-qa.txt", "NexGrana/gateway/requirements.txt", "NexGrana/pyproject.toml",
            "SIM_Labs_QA/backend/requirements.txt", "SIM_Labs_QA/Collector/requirements.txt",
            "SIM_Labs_QA/frontend/package.json", "SIM_Labs_QA/frontend/package-lock.json",
        ],
        "build_artifacts": {"windows_exe": None, "android_apk": None, "collector_exe": None},
        "assets": {"nex_skin_sets": 36, "nex_skin_pngs": 72, "native_visual_approval": "PENDING"},
        "source_file_count": len(entries),
        "source_files": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"manifest": str(output), "source_file_count": len(entries), "status": manifest["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
