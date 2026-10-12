#!/usr/bin/env python3
"""Runtime validation for the Windows QA clone without printing secrets."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from urllib import request, error

QA_ROOT=Path(__file__).resolve().parents[1]
EXPECTED_SERVICE="sim-labs-control-center-qa"
EXPECTED_PHASE="Engine 0.4.1-qa.2"

def _qa_port() -> int:
    path=QA_ROOT/".runtime"/"qa_port.txt"
    if not path.is_file():
        raise RuntimeError("qa_port.txt ausente; inicializacao ainda nao definiu a porta desta copia QA.")
    try:
        port=int(path.read_text(encoding="ascii").strip())
    except ValueError as exc:
        raise RuntimeError("qa_port.txt invalido") from exc
    if not 1024 <= port <= 65535:
        raise RuntimeError("porta QA fora da faixa permitida")
    return port

def _instance_id() -> str:
    text=QA_ROOT.as_posix().lower().rstrip("/")
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def _first_access_password() -> str:
    path=QA_ROOT/".runtime"/"PRIMEIRO_ACESSO.txt"
    if not path.is_file():
        raise RuntimeError("PRIMEIRO_ACESSO.txt ausente; credencial existente nao sera inventada ou rotacionada.")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("Senha:"):
            value=line.split(":",1)[1].strip()
            if value:
                return value
    raise RuntimeError("PRIMEIRO_ACESSO.txt nao contem uma credencial local reconhecivel.")

def _json_get(url: str) -> dict:
    with request.build_opener(request.ProxyHandler({})).open(url,timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} em endpoint QA")
        return json.load(response)

def main() -> int:
    port=_qa_port(); base=f"http://127.0.0.1:{port}"
    health=_json_get(base+"/api/v1/health")
    expected_id=_instance_id()
    checks={
        "status": health.get("status")=="ok",
        "service": health.get("service")==EXPECTED_SERVICE,
        "phase": health.get("phase")==EXPECTED_PHASE,
        "instance_id": health.get("instance_id")==expected_id,
    }
    if not all(checks.values()):
        print("HEALTH_QA=FAIL "+json.dumps(checks,ensure_ascii=False))
        return 2
    print(f"HEALTH_QA=PASS porta={port} service/phase/instance_id confirmados")

    with request.build_opener(request.ProxyHandler({})).open(base+"/",timeout=5) as response:
        body=response.read(262144).decode("utf-8",errors="replace")
        if response.status!=200 or "<html" not in body.lower():
            print("INTERFACE_QA=FAIL")
            return 3
    print("INTERFACE_QA=PASS")

    password=_first_access_password()
    payload=json.dumps({"password":password}).encode("utf-8")
    req=request.Request(base+"/api/v1/auth/login",data=payload,headers={"Content-Type":"application/json"},method="POST")
    try:
        with request.build_opener(request.ProxyHandler({})).open(req,timeout=5) as response:
            data=json.load(response)
            ok=(response.status==200 and bool(data.get("token")) and data.get("name")=="Mafra" and data.get("mode")=="local-private")
    except error.HTTPError as exc:
        print(f"LOGIN_LOCAL=FAIL HTTP {exc.code}")
        return 4
    if not ok:
        print("LOGIN_LOCAL=FAIL resposta inesperada")
        return 4
    print("LOGIN_LOCAL=PASS credencial armazenada validada sem exibicao de segredo")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("VALIDACAO_QA=FAIL "+type(exc).__name__+": "+str(exc))
        raise SystemExit(10)
