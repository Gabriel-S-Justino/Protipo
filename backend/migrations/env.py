"""Ambiente Alembic — usa DATABASE_URL_DIRECT (conexão direta, NUNCA a pooled).
Nunca rodar migrations automaticamente a cada cold start (local/CI apenas)."""

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.models import Base

config = context.config

# URL vinda do ambiente (12-factor)
db_url = os.environ.get("DATABASE_URL_DIRECT") or os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError(
        "DATABASE_URL_DIRECT (ou DATABASE_URL) deve estar definida para rodar migrations."
    )
config.set_main_option("sqlalchemy.url", db_url)

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
