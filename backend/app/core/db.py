"""Pool de conexões com o banco (SQLAlchemy Core + psycopg 3).

- A API usa SEMPRE a URL pooled (Neon pooler / Supabase pooler).
- Sem estado entre requisições: NullPool evita conexões órfãs em serverless
  (o pool externo do provedor faz o pooling real).
- ⚠ LIMITAÇÃO VALIDADA (deploy real, 2026-11-05): o pooler do Neon REJEITA o
  startup parameter `options: statement_timeout`
  ("unsupported startup parameter in options: statement_timeout").
  Por isso NÃO injetamos statement_timeout via options; a proteção de tempo é
  garantida por: consultas pré-calculadas + LIMIT máximos (settings.max_limit).
- statement_timeout DE SÉSSÃO pode ser aplicado com `SET statement_timeout=...`
  direto no SQL (funciona com o pooler) — usar somente quando necessário.
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
        url = settings.api_database_url
        if not url:
            raise RuntimeError(
                "Banco não configurado: defina DATABASE_URL (manual) ou crie o banco pela "
                "integração da Vercel (Database Marketplace) — ver docs/SETUP.md."
            )
        # NÃO usar connect_args={'options': ...}: Neon pooler rejeita (ver docstring).
        _engine = create_engine(
            url,
            poolclass=__import__("sqlalchemy").pool.NullPool,
            connect_args={"sslmode": "require", "connect_timeout": 10},
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
