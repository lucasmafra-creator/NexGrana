"""Validate source ZIP layout, integrity and SHA256 of every file."""
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


def verify(path):
    with zipfile.ZipFile(Path(path)) as archive:
        names=archive.namelist()
        if not names or archive.testzip() is not None:
            raise ValueError("ZIP vazio ou corrompido")
        roots={PurePosixPath(name).parts[0] for name in names}
        if len(roots)!=1 or any(".." in PurePosixPath(name).parts or name.startswith("/") for name in names):
            raise ValueError("Estrutura insegura ou raiz incorreta")
        root=next(iter(roots))
        prefix=f"{root}/project/"
        if any(not name.startswith(prefix) for name in names):
            raise ValueError("Arquivos devem estar dentro de project/")
        manifest_name=prefix+"MANIFEST_RELEASE_0_24_0.json"
        manifest=json.loads(archive.read(manifest_name))
        listed={prefix+row["path"]:row for row in manifest["files"]}
        if set(names)!=(set(listed)|{manifest_name}):
            raise ValueError("Manifesto diverge dos arquivos do ZIP")
        for name,row in listed.items():
            data=archive.read(name)
            if len(data)!=row["bytes"] or sha256(data).hexdigest()!=row["sha256"]:
                raise ValueError(f"Arquivo não confere: {name}")
        if manifest["golden_nex_sha256"]!=listed[prefix+"src/assets/nex/nex_hd.png"]["sha256"]:
            raise ValueError("Golden Nex mudou")
        print(f"Pacote validado: {len(names)} arquivos, {manifest['validation']['python_tests']} testes no empacotamento")
        return manifest


if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Uso: py verificar_pacote.py caminho-do-zip")
    verify(sys.argv[1])
