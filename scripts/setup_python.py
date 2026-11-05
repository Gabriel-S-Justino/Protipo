"""Cria o virtualenv e instala backend + pipeline — multiplataforma (stdlib apenas).

Uso: python scripts/setup_python.py     (ou: npm run setup:python)
No Windows: py scripts/setup_python.py
"""

import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"

is_win = sys.platform.startswith("win")
pip = VENV_DIR / ("Scripts" if is_win else "bin") / ("pip.exe" if is_win else "pip")

if not VENV_DIR.exists():
    print(f"[setup] criando virtualenv em {VENV_DIR} …")
    venv.create(str(VENV_DIR), with_pip=True)
else:
    print("[setup] virtualenv existente — reaproveitando")

for req in ("backend/requirements.txt", "pipeline/requirements.txt"):
    print(f"[setup] instalando {req} …")
    subprocess.check_call([str(pip), "install", "-r", str(ROOT / req)])

print("[setup] ok — ativar com:")
print('  Linux/macOS:  source .venv/bin/activate')
print("  Windows:      .venv\\Scripts\\activate")
