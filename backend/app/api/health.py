"""Endpoints de health/infraestrutura."""

from fastapi import APIRouter

from backend.app.core import db
from backend.app.core.config import get_settings
from backend.app.schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
def health() -> Health:
    """Healthcheck: toca no banco DE FORMA LEVE (SELECT 1 + contagem de tabelas)
    apenas para informar status — nunca bloqueia o deploy por banco vazio."""
    settings = get_settings()
    db_state, status = None, "degraded"

    if settings.api_database_url:
        try:
            db.fetch_one("SELECT 1 AS ok")
            tables = db.fetch_one(
                """
                SELECT COUNT(*)::int AS n
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            n_tables = tables["n"] if tables else 0
            db_state = f"up ({n_tables} tabelas)"
            status = "ok"
        except Exception as exc:  # noqa: BLE001 — health precisa reportar, não explodir
            db_state = f"down: {type(exc).__name__}"
            status = "degraded"
    else:
        # Sem variável de banco: aguardando integração Vercel×Neon ou .env manual
        db_state = "aguardando integração Vercel×Neon (ou DATABASE_URL no .env)"

    return Health(
        status=status,
        app=settings.app_name,
        env=settings.app_env,
        database=db_state,
        version="0.1.0",
    )
