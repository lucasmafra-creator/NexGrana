from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT/'backend/app/main.py', ROOT/'backend/alembic/versions/0001_phase_a_foundation.py',
    ROOT/'frontend/src/App.tsx', ROOT/'docs/SIM_LABS_ESTADO_ATUAL.md',
    ROOT/'docs/PROMPT_MESTRE_SIM_LABS.md', ROOT/'frontend/public/sim-labs-maquete.png'
]
missing=[str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit('Missing: '+', '.join(missing))
print('Phase A structural check: OK')
