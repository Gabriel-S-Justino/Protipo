"""Ambiente Alembic — usa a conexão DIRETA (database_url indireta reserva NUNCA a pooled).

Aceita, em ordem:
  1) DATABASE_URL_DIRECT   (manual/.env, pipeline, CI)
  2) DATABASE_URL_UNPOOLED (integração Vercel × Neon)
  3) POSTGRES_URL_NON_POOLING (integração legada)

Nunca rodar migrations automaticamente a cada cold start (local/CI/admin apenas)."""

import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.models import Base


def _load_env_file() -> None:
    """Carrega .env simples (KEY=VALUE) quando a variável não está no ambiente."""
    if Path(".env").is_file():
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


config = context.config

db_url = (
    os.environ.get("DATABASE_URL_DIRECT")
    or os.environ.get("DATABASE_URL_UNPOOLED")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
    or os.environ.get("DATABASE_URL")
)
if not db_url:
    _load_env_file()
    db_url = (
        os.environ.get("DATABASE_URL_DIRECT")
        or os.environ.get("DATABASE_URL_UNPOOLED")
        or os.environ.get("POSTGRES_URL_NON_POOLING")
        or os.environ.get("DATABASE_URL")
    )
if not db_url:
    raise RuntimeError(
        "URL direta do banco ausente para migrations. Use DATABASE_URL_DIRECT (manual no .env) "
        "ou a var DATABASE_URL_UNPOOLED injetada pela integração Vercel×Neon."
    )

# Migrations exigem conexão DIRETA: URLs com "-pooler" são rejeitadas aqui por segurança.
if "-pooler." in db_url:
    raise RuntimeError(
        "A URL configurada para MIGRATIONS é pooled (~'-pooler.'). Alembic/pipeline exigem a "
        "URL direta (sem '-pooler': consolidação de DDL/ferramentas de schema). Copie no "
        "console do Neon a.Connection String com 'Pooled' DESLIGADO."
    )
db_url = db_url.replace("postgres://", "postgresql://", 1).replace(
    "postgresql://", "postgresql+psycopg://", 1
)
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
