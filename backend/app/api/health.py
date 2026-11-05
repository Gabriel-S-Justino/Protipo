"""Endpoints de health/infraestrutura."""

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
def health() -> Health:
    """Healthcheck sem tocar no banco com força (só sinaliza disponibilidade)."""
    settings = get_settings()
    db_state = "up" if settings.database_url else None
    return Health(
        status="ok" if settings.database_url else "degraded",
        app=settings.app_name,
        env=settings.app_env,
        database=db_state,
        version="0.1.0",
    )
