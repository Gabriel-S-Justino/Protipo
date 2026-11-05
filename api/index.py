"""Entrypoint da Vercel Function (Python runtime).

A runtime Python da Vercel expõe a variável `app` deste módulo como aplicação ASGI.
O código da aplicação vive em `backend/app` (testável e importável fora da Vercel);
aqui apenas ajustamos o path e nomeamos `app` para o padrão da plataforma.
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.app.main import app  # noqa: E402, F401
