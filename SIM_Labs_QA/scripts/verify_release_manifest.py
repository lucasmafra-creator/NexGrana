#!/usr/bin/env python3
"""Verify every non-secret source entry in release_manifest.json."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"release_manifest.json"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main()->int:
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries=data.get("source_files") or []
    failures=[]
    for entry in entries:
        rel=entry.get("path","")
        path=(ROOT/rel).resolve()
        try:path.relative_to(ROOT.resolve())
        except ValueError:
            failures.append(rel+":outside-root"); continue
        if not path.is_file():
            failures.append(rel+":missing"); continue
        if path.stat().st_size!=entry.get("size_bytes") or sha256(path)!=entry.get("sha256"):
            failures.append(rel+":mismatch")
    if len(entries)!=data.get("source_file_count"):
        failures.append("source_file_count:mismatch")
    if failures:
        print("MANIFEST_INTEGRITY=FAIL count="+str(len(failures)))
        for item in failures[:20]: print(" - "+item)
        return 1
    print("MANIFEST_INTEGRITY=PASS sources="+str(len(entries)))
    return 0
if __name__=="__main__": raise SystemExit(main())
