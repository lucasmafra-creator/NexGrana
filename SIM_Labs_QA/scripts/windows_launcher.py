"""Windows-only optional EXE launcher. Python/backend remain installed by official startup script."""
import subprocess, sys
from pathlib import Path
import ctypes
root=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
script=root/'START_SIM_LABS_WINDOWS.ps1'
if not script.exists():
    ctypes.windll.user32.MessageBoxW(0,'Coloque SIM_Labs.exe ao lado de START_SIM_LABS_WINDOWS.ps1.','SIM Labs',16)
    raise SystemExit(1)
raise SystemExit(subprocess.call(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)],cwd=root))
