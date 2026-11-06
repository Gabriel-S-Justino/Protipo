"""Readiness distinguishes a connected database from an initialized national dataset."""

from fastapi import APIRouter
from backend.app.core import db
from backend.app.core.config import get_settings
from backend.app.schemas import Health

router = APIRouter(tags=["health"])
EXPECTED_REVISION = "0004_brazil_science"


def health_snapshot():
    settings = get_settings()
    result = dict(
        status="degraded",
        app=settings.app_name,
        env=settings.app_env,
        database="não configurado",
        version="0.1.1",
        readiness="database_missing",
        schema_revision=None,
        expected_revision=EXPECTED_REVISION,
        checks={},
        next_action="Conecte o banco em DATABASE_URL.",
    )
    if not settings.api_database_url:
        return result
    try:
        db.fetch_one("SELECT 1 AS ok")
        result["database"] = "up"
        result["checks"]["database"] = True
    except Exception:
        result.update(
            database="down",
            readiness="database_unreachable",
            next_action="Verifique a conexão e as credenciais do banco no ambiente de produção.",
        )
        return result
    try:
        schema = db.fetch_one("""
            SELECT to_regclass('public.acquisition_coverage') IS NOT NULL AS coverage_table,
              to_regclass('public.alembic_version') IS NOT NULL AS migrations_table,
              EXISTS(SELECT 1 FROM information_schema.columns
                     WHERE table_schema='public' AND table_name='regions' AND column_name='geom') AS region_geometry
        """) or {}
        if schema.get("migrations_table"):
            revision = db.fetch_one("SELECT version_num FROM alembic_version LIMIT 1")
            result["schema_revision"] = revision["version_num"] if revision else None
        ready = (
            schema.get("coverage_table")
            and schema.get("region_geometry")
            and result["schema_revision"] == EXPECTED_REVISION
        )
        result["checks"]["schema"] = bool(ready)
        if not ready:
            result.update(
                readiness="migration_pending",
                next_action="Banco conectado. Aplique a migração 0004_brazil_science antes de carregar os dados nacionais.",
            )
            return result
        data = db.fetch_one("""
            SELECT EXISTS(SELECT 1 FROM regions WHERE level='country' AND geocode='BR'
                          AND geom IS NOT NULL AND is_demo=false) AS boundaries,
              EXISTS(SELECT 1 FROM acquisition_coverage WHERE scope='BR') AS coverage,
              EXISTS(SELECT 1 FROM harmonized_series h JOIN spatial_cells c ON c.id=h.cell_id
                     WHERE c.resolution='br_05deg' AND h.period_type='day' AND h.is_demo=false) AS unified,
              EXISTS(SELECT 1 FROM calendar_probabilities p JOIN spatial_cells c ON c.id=p.cell_id
                     WHERE c.resolution='br_05deg' AND p.is_demo=false) AS calendar
        """) or {}
        result["checks"].update(
            {
                key: bool(data.get(key))
                for key in ("boundaries", "coverage", "unified", "calendar")
            }
        )
        for key, state, action in [
            (
                "boundaries",
                "boundaries_missing",
                "Importe as malhas do Brasil e das UFs pelo comando boundaries.",
            ),
            (
                "coverage",
                "coverage_missing",
                "Carregue os arquivos FIRMS nacionais com os metadados de cobertura.",
            ),
            (
                "unified",
                "harmonization_pending",
                "Execute harmonize após a ingestão nacional.",
            ),
            (
                "calendar",
                "calendar_pending",
                "Execute calendar após reunir pelo menos três anos de períodos completos.",
            ),
        ]:
            if not data.get(key):
                result.update(readiness=state, next_action=action)
                return result
        result.update(status="ok", readiness="ready", next_action=None)
    except Exception:
        result.update(
            readiness="readiness_check_failed",
            next_action="Banco conectado, mas o diagnóstico da estrutura falhou. Consulte os logs da API.",
        )
    return result


@router.get("/health", response_model=Health)
def health():
    return Health(**health_snapshot())
