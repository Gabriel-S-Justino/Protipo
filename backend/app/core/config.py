"""Configuração central da API via variáveis de ambiente (Pydantic Settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"  # development | preview | production
    app_name: str = "Fire Intelligence Platform"

    # Conexão POOLED (Neon/Supabase pooler) — usada pelas functions.
    database_url: str | None = None
    # Conexão DIRETA — usada por migrations/pipeline (nunca pela API em requisição).
    database_url_direct: str | None = None

    # Habilita POST /api/admin/* (recomendado apenas em development).
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
