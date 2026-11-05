"""Configuração do pipeline (variáveis de ambiente + .env via python-dotenv-like manual)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    """Carrega .env simples (KEY=VALUE) sem dependência dotenv pesada."""
    for candidate in (Path(".env"), Path(".env.local")):
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
            break


_load_env_file()


@dataclass(frozen=True)
class PipelineSettings:
    database_url_direct: str | None
    map_key: str | None
    firms_base: str = "https://firms.modaps.eosdis.nasa.gov/api"
    data_dir: str = "data"


_env = os.environ


def get_settings() -> PipelineSettings:
    return PipelineSettings(
        database_url_direct=_env.get("DATABASE_URL_DIRECT") or _env.get("DATABASE_URL"),
        map_key=_env.get("MAP_KEY"),
        data_dir=_env.get("DATA_DIR", "data"),
    )


class MissingConfigError(RuntimeError):
    """Erro de configuração ausente — mensagem instrui o usuário."""
