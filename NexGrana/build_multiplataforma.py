"""Build Windows, Android e trilha iOS com pastas e logs isolados."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
import platform
from importlib.metadata import version, PackageNotFoundError
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parent
VERSION = '0.24.0'


def build_env(flutter=None):
    env = os.environ.copy()
    root = flutter or env.get('FLUTTER_ROOT')
    if root:
        binary = Path(root).resolve() / 'bin'
        if not binary.is_dir():
            raise ValueError(f'Flutter bin não encontrado: {binary}')
        env['PATH'] = str(binary) + os.pathsep + env.get('PATH', '')
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    return env


def build(target, output, env, timeout):
    log = output / f'build-{target}.log'
    if target == 'windows' and os.name != 'nt':
        result={'target':target,'version':VERSION,'status':'blocked','artifacts':[],
                'error':'Build Windows exige Windows com ferramentas de compilação instaladas'}
        log.write_text(result['error']+'\n',encoding='utf-8')
        print(f'{target}: blocked — {result["error"]}',flush=True)
        return result
    if target == 'ipa' and sys.platform != 'darwin':
        result = {'target': target, 'version': VERSION, 'status': 'blocked', 'artifacts': [],
                  'error': 'Build iOS exige macOS com Xcode, assinatura e conta Apple configurados'}
        log.write_text(result['error'] + '\n', encoding='utf-8')
        print(f'{target}: blocked — {result["error"]}', flush=True)
        return result
    if target in {'apk','aab'} and (not shutil.which('flutter',path=env.get('PATH')) or not (env.get('ANDROID_HOME') or env.get('ANDROID_SDK_ROOT') or shutil.which('adb',path=env.get('PATH')))):
        result={'target':target,'version':VERSION,'status':'blocked','artifacts':[],
                'error':'Flutter e Android SDK precisam estar configurados no host; confirme flutter doctor e adb devices antes de compilar.'}
        log.write_text(result['error']+'\n',encoding='utf-8')
        print(f'{target}: blocked — {result["error"]}',flush=True)
        return result
    command = [sys.executable, '-m', 'flet.cli', 'build', target,
               '--build-version', VERSION, '--output', str(output / target), '--yes']
    print(f'Compilando {target}; log: {log}', flush=True)
    result = {'target': target, 'version': VERSION, 'status': 'failed', 'artifacts': []}
    process=None
    with log.open('w', encoding='utf-8') as stream:
        stream.write('Command: ' + subprocess.list2cmdline(command) + '\n')
        stream.flush()
        try:
            process = subprocess.Popen(
                command,cwd=ROOT,env=env,stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1,
            )
            def tee_output():
                for line in iter(process.stdout.readline,''):
                    stream.write(line);stream.flush()
                    print(line,end='',flush=True)
            reader=threading.Thread(target=tee_output,daemon=True)
            reader.start()
            try:
                result['exit_code'] = process.wait(timeout=timeout)
                reader.join(timeout=5)
            except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=stream, stderr=stream, check=False)
                else:
                    process.kill()
                process.wait()
                result['error'] = ('Build cancelado pelo usuário' if isinstance(exc,KeyboardInterrupt)
                                   else f'Build excedeu {timeout}s')
                result['exit_code'] = 130 if isinstance(exc,KeyboardInterrupt) else 124
                reader.join(timeout=5)
        except OSError as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
            result['exit_code'] = 1
    pattern = {'windows':'*.exe','apk':'*.apk','aab':'*.aab','ipa':'*.ipa'}[target]
    artifacts = sorted((output / target).rglob(pattern))
    if result['exit_code'] == 0 and artifacts:
        result['status'] = 'built'
        result['artifacts'] = [str(p.relative_to(output)) for p in artifacts]
        result['artifact_metadata']=[{'path':str(p.relative_to(output)),'size_bytes':p.stat().st_size,
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in artifacts]
    elif result['exit_code'] == 0:
        result['error'] = 'CLI terminou sem artefato esperado; não considerar build concluído'
    print(f'{target}: {result["status"]}', flush=True)
    return result


def source_provenance():
    exclude={'dist','build','node_modules','.venv','venv','.git','.data','.flet','.dart_tool','.gradle',
             '__pycache__','scratch','.pytest_cache','.mypy_cache','.ruff_cache','coverage'}
    entries=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or any(part in exclude for part in path.relative_to(ROOT).parts):continue
        if (path.name=='.env' or (path.name.startswith('.env.') and path.name!='.env.example')
                or path.name.startswith('generated_')
                or path.suffix.lower() in {'.db','.db-wal','.db-shm','.db-journal','.sqlite','.sqlite3',
                                           '.sqlite-wal','.sqlite-shm','.sqlite-journal','.pyc','.log'}):continue
        entries.append((path.relative_to(ROOT).as_posix(),hashlib.sha256(path.read_bytes()).hexdigest()))
    dependencies={}
    for package in ('flet','flet-camera','flet-secure-storage','supabase','cryptography','pillow'):
        try:dependencies[package]=version(package)
        except PackageNotFoundError:dependencies[package]='MISSING'
    return {'source_manifest_sha256':hashlib.sha256(json.dumps(entries,separators=(',',':')).encode()).hexdigest(),
            'source_file_count':len(entries),'python':platform.python_version(),'host':platform.system(),
            'dependencies':dependencies,'created_at':datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description='NexGrana 0.24.0 — build Windows, Android e iOS')
    parser.add_argument('target', choices=['windows', 'apk', 'aab', 'ipa', 'both', 'android'], nargs='?')
    parser.add_argument('--flutter', help='Pasta raiz do Flutter; alternativamente use FLUTTER_ROOT')
    parser.add_argument('--timeout', type=int, default=3600, help='Limite por build em segundos')
    args = parser.parse_args()
    if not args.target:
        args.target = {'1': 'windows', '2': 'apk', '3': 'both'}.get(input('1 Windows | 2 APK | 3 Ambos: ').strip())
        if not args.target:
            parser.error('Opção inválida')
    if args.timeout < 1:
        parser.error('--timeout deve ser positivo')
    if not shutil.which('git'):
        print('Git precisa estar no PATH para o Flutter.', file=sys.stderr)
        return 1
    if os.name=='nt' and len(str(ROOT))>120:
        print('Caminho longo detectado. Copie o projeto para C:\\NG24 antes do build para evitar falhas do Flutter.',file=sys.stderr)
        return 2
    env = build_env(args.flutter)
    output = ROOT / 'dist' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, exist_ok=False)
    targets = ['windows', 'apk'] if args.target == 'both' else (['apk','aab'] if args.target == 'android' else [args.target])
    results = [build(target, output, env, args.timeout) for target in targets]
    provenance=source_provenance()
    for result in results:result['provenance']=provenance
    (output / 'source-manifest.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    (output / 'build-report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    if all(r['status']=='built' for r in results):
        (ROOT/'dist/latest-successful-build.txt').write_text(str(output/'build-report.json'),encoding='utf-8')
    return 0 if all(r['status'] == 'built' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
