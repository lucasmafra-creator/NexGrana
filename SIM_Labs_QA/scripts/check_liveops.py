from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT/'backend/app/main.py', ROOT/'backend/app/worker.py', ROOT/'backend/app/supervisor.py',
    ROOT/'backend/app/routers/live.py', ROOT/'backend/alembic/versions/0002_liveops.py',
    ROOT/'frontend/src/App.tsx', ROOT/'frontend/src/vite-env.d.ts',
    ROOT/'START_SIM_LABS.bat', ROOT/'STOP_SIM_LABS.bat',
    ROOT/'docs/LIVEOPS_ARCHITECTURE.md', ROOT/'docs/DEPLOY_24X7.md',
    ROOT/'frontend/public/sim-labs-maquete.png'
]
missing=[str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit('Missing: '+', '.join(missing))
print('SIM Labs LiveOps structural check: OK')
