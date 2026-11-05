"""Endpoints que leem resultados pré-calculados no banco.

Princípio central do projeto: a API SERVE E CONSULTA; o pipeline CALCULA.
Nenhum processamento científico dentro da requisição; todas as consultas
parametrizadas (anti-SQL injection), com limites máximos.
"""

from fastapi import APIRouter, HTTPException, Query

from backend.app.core import db
from backend.app.core.config import get_settings
from backend.app.schemas import CalendarCell, CoverageOut, DashboardSummary

router = APIRouter(tags=["dashboard"])


def _require_db() -> None:
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(
            status_code=503,
            detail=(
                "Banco não conectado: crie o banco pela integração da Vercel (Database "
                "Marketplace) ou defina DATABASE_URL no .env (ver docs/SETUP.md). "
                "Nada de dados fictícios em produção."
            ),
        )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary() -> DashboardSummary:
    _require_db()
    try:
        row = db.fetch_one(
            """
            SELECT
              COUNT(*)::int AS total,
              COUNT(*) FILTER (WHERE acquired_at >= now() - interval '30 days')::int AS last_30d
            FROM fire_detections
            WHERE is_demo = FALSE
            """
        )
        avg = db.fetch_one(
            """
            SELECT COALESCE(AVG(c.monthly), 0) AS avg30
            FROM (
              SELECT date_trunc('month', acquired_at) AS m,
                     (COUNT(*)::numeric / 30) AS monthly
              FROM fire_detections
              WHERE is_demo = FALSE
                AND acquired_at < now() - interval '30 days'
                AND acquired_at >= now() - interval '365 days'
              GROUP BY 1
            ) c
            """
        )
    except Exception as exc:  # noqa: BLE001 — falha de banco → erro padronizado
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc

    avg30 = float(avg["avg30"]) if avg and avg.get("avg30") is not None else None
    return DashboardSummary(
        total=row["total"] if row else 0,
        last_30d=row["last_30d"] if row else 0,
        last_30d_avg_hist=avg30,
    )


@router.get("/metadata/coverage", response_model=CoverageOut)
def coverage() -> CoverageOut:
    _require_db()
    try:
        rows = db.fetch_all(
            """
            SELECT MIN(acquired_at) AS period_start, MAX(acquired_at) AS period_end,
                   array_agg(DISTINCT instrument::text) AS instruments
            FROM fire_detections
            WHERE is_demo = FALSE
            """
        )
        harm = db.fetch_one(
            """
            SELECT COALESCE(
              AVG(CASE WHEN value_source = 'modis_harmonized' THEN 1.0 ELSE 0.0 END), NULL
            ) AS harmonized_share
            FROM harmonized_series WHERE is_demo = FALSE
            """
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc

    first = rows[0] if rows else {}
    return CoverageOut(
        period_start=first.get("period_start"),
        period_end=first.get("period_end"),
        instruments=first.get("instruments") or [],
        harmonized_share=harm["harmonized_share"] if harm else None,
    )


@router.get("/calendar/probability", response_model=list[CalendarCell])
def calendar_probability(
    region_id: int | None = Query(None),
    period_type: str = Query("week", pattern="^(day|week|month)$"),
) -> list[CalendarCell]:
    _require_db()
    sql = """
        SELECT period_of_year, probability, ci_low, ci_high, years_used,
               expected_count, harmonized_share, confidence
        FROM calendar_probabilities
        WHERE is_demo = FALSE AND period_type = :period_type
          AND (:region_id IS NULL OR region_id = :region_id)
        ORDER BY period_of_year
        LIMIT 400
    """
    try:
        rows = db.fetch_all(sql, {"period_type": period_type, "region_id": region_id})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc
    return [CalendarCell(**r) for r in rows]
