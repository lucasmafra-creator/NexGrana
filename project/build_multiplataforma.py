"""Build Windows/APK with isolated output folders and diagnostic logs."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VERSION = '0.19.0'


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
    command = [sys.executable, '-m', 'flet.cli', 'build', target,
               '--build-version', VERSION, '--output', str(output / target), '--yes']
    print(f'Compilando {target}; log: {log}', flush=True)
    result = {'target': target, 'version': VERSION, 'status': 'failed', 'artifacts': []}
    with log.open('w', encoding='utf-8') as stream:
        stream.write('Command: ' + subprocess.list2cmdline(command) + '\n')
        stream.flush()
        try:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
            try:
                result['exit_code'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=stream, stderr=stream, check=False)
                else:
                    process.kill()
                process.wait()
                result['error'] = f'Build excedeu {timeout}s'
                result['exit_code'] = 124
        except OSError as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
            result['exit_code'] = 1
    pattern = '*.exe' if target == 'windows' else '*.apk'
    artifacts = sorted((output / target).rglob(pattern))
    if result['exit_code'] == 0 and artifacts:
        result['status'] = 'built'
        result['artifacts'] = [str(p.relative_to(output)) for p in artifacts]
    elif result['exit_code'] == 0:
        result['error'] = 'CLI terminou sem artefato esperado; não considerar build concluído'
    print(f'{target}: {result["status"]}', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description='NexGrana 0.19.0 — build Windows e Android')
    parser.add_argument('target', choices=['windows', 'apk', 'both'], nargs='?')
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
    env = build_env(args.flutter)
    output = ROOT / 'dist' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, exist_ok=False)
    targets = ['windows', 'apk'] if args.target == 'both' else [args.target]
    results = [build(target, output, env, args.timeout) for target in targets]
    (output / 'build-report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if all(r['status'] == 'built' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
