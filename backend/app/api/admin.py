"""Endpoints administrativos (POST, protegidos por token, DESABILITADOS por padrão).

POST /api/admin/migrate — aplica as migrations Alembic (usar UMA VEZ, logo depois
de criar o banco pela integração Vercel × Neon). Usa a conexão DIRETA (nunca a
pooled), conforme as regras do projeto.

Habilitação: ADMIN_ENABLED=true + ADMIN_TOKEN=... nas env da Vercel.

Uso típico (uma única vez, após criar o banco no painel):
    curl -X POST https://SEU-DEPLOY.vercel.app/api/admin/migrate \
      -H "X-Admin-Token: SEU_TOKEN"
Importante NUNCA commitar o token; defini-lo apenas como env da Vercel.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from alembic import command as alembic_command
from alembic import config as alembic_config

from fastapi import APIRouter, Header, HTTPException

from backend.app.core import db
from backend.app.core.config import get_settings

logger = logging.getLogger("api.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


def _guard(token: str) -> None:
    settings = get_settings()
    if not settings.admin_enabled:
        raise HTTPException(
            status_code=403,
            detail="Endpoints admin desabilitados (defina ADMIN_ENABLED=true na env da Vercel).",
        )
    if not settings.admin_token or token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Token admin inválido.")


def _alembic_config() -> alembic_config.Config:
    """Config do Alembic apontando para backend/migrations, INCLUÍDO no bundle da function
    (vercel.json#functions.includeFiles). Migrations usam a conexão DIRETA."""
    from backend.app import __file__ as app_file

    backend_dir = Path(app_file).resolve().parent.parent
    cfg = alembic_config.Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    settings = get_settings()
    direct = settings.direct_database_url
    if not direct:
        raise HTTPException(
            status_code=503,
            detail="URL direta indisponível (DATABASE_URL_DIRECT / DATABASE_URL_UNPOOLED).",
        )
    # env.py (Alembic) lê a URL direta do ambiente (12-factor).
    os.environ["DATABASE_URL_DIRECT"] = direct
    return cfg


def _current_revision() -> Optional[str]:
    try:
        row = db.fetch_one("SELECT version_num FROM alembic_version LIMIT 1")
        return row["version_num"] if row else None
    except Exception:
        return None


@router.post("/migrate")
def run_migrations(X_Admin_Token: str = Header(default="")) -> dict:
    _guard(X_Admin_Token)
    cfg = _alembic_config()
    before = _current_revision()
    try:
        alembic_command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001 — reportar falha de migration com clareza
        logger.exception("Migration falhou")
        raise HTTPException(status_code=500, detail=f"Migration falhou: {exc}") from exc
    after = _current_revision()
    return {
        "status": "ok",
        "revision_before": before,
        "revision_after": after,
        "note": "Migrations aplicadas até head. A importação IBGE e a carga FIRMS são etapas separadas.",
    }
