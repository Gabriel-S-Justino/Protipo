"""Pool de conexões com o banco (SQLAlchemy Core + psycopg 3).

- A API usa SEMPRE a URL pooled (Neon pooler / Supabase pooler).
- Sem estado entre requisições: NullPool evita conexões órfãs em serverless
  (o pool externo do provedor faz o pooling real).
- statement_timeout defensivo para respeitar limites de duração da Vercel.
"""

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Cria (uma vez por processo) o engine com a URL pooled."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL não configurada: defina a variável no ambiente "
                "(ver .env.example e docs/SETUP.md)."
            )
        _engine = create_engine(
            settings.database_url,
            poolclass=__import__("sqlalchemy").pool.NullPool,
            connect_args={"options": f"-c statement_timeout={settings.query_timeout_ms}"},
        )
    return _engine


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Executa uma consulta SELECT parametrizada (sem SQL injection) e devolve dicts."""
    with get_engine().connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None
