"""Configuração central da API via variáveis de ambiente (Pydantic Settings).

Suporta, SEM mudanças de código, tanto o setup manual (.env) quanto a integração
Vercel × Neon (Database Marketplace), que injeta automaticamente:
  - DATABASE_URL            (pooled; usada pela API)
  - DATABASE_URL_UNPOOLED   (direta; usada por migrations/pipeline)
  - legacy: POSTGRES_URL / POSTGRES_URL_NON_POOLING (integrações antigas)
"""

import os

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"  # development | preview | production
    app_name: str = "Fire Intelligence Platform"

    # Manual (.env). Na integração Vercel×Neon, DATABASE_URL já é injetada automaticamente.
    database_url: str | None = None
    database_url_direct: str | None = None

    # Habilita POST /api/admin/* (migrations etc.). OFF por padrão (segurança).
    admin_enabled: bool = False
    admin_token: str | None = None
    cron_secret: str | None = None

    # CORS: em produção deve ser o domínio do SPA (vazio = restrito; "*" proibido em prod).
    cors_origins: str = ""

    # Limites defensivos de consulta (nenhum processamento científico em requisição).
    max_limit: int = 1000
    default_limit: int = 100
    query_timeout_ms: int = 5000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_database_url(self) -> str | None:
        """URL pooled para requisições da API (precedência: manual → integração)."""
        return self.database_url or os.getenv("POSTGRES_URL")

    @property
    def direct_database_url(self) -> str | None:
        """URL DIRETA para migrations/pipeline (nunca a pooled, p/ evitar erros de schema)."""
        return (
            self.database_url_direct
            or os.getenv("DATABASE_URL_UNPOOLED")  # integração Vercel×Neon
            or os.getenv("POSTGRES_URL_NON_POOLING")  # integração legada
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
