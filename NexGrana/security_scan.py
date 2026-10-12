"""Verificação estática local de segredos e artefatos indevidos na candidata."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
SKIP={'.git','.venv','node_modules','build','dist','release','__pycache__','.data'}
TEXT_SUFFIXES={'.py','.sql','.md','.txt','.toml','.json','.yml','.yaml'}
PATTERNS={
    'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'openai_secret':re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    'supabase_service_jwt':re.compile(r'\beyJ[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'),
}


def main():
    findings=[]
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel=path.relative_to(ROOT)
        if any(part in SKIP for part in rel.parts):
            continue
        try:
            text=path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for name,pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f'{rel}: {name}')
    # Diretórios locais podem ser recriados durante a validação; o empacotador
    # os exclui. Aqui falhamos somente se houver conteúdo que poderia vazar.
    for name in ('.data',):
        folder=ROOT/name
        if folder.exists() and any(path.is_file() for path in folder.rglob('*')):
            findings.append(f'{name}: runtime data present')
    if findings:
        print('FALHA NA VARREDURA DE SEGURANÇA')
        print('\n'.join(findings))
        return 1
    print('security scan: OK (segredos conhecidos e artefatos locais ausentes)')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
