"""Análises científicas pré-calculadas (rodam FORA da Vercel; a API só lê).

Etapa 4 — harmonize: calibra MODIS→VIIRS (razão de medianas por passo sobre a
janela temporal com AMBOS os instrumentos) e grava a série unificada na escala
VIIRS (viirs_raw nos meses com VIIRS, modis_harmonized nos meses sem VIIRS).
Com pouco overlap real os resultados saem rotulados `insufficient`/
`low_confidence` — NUNCA um número polido disfarçado de certeza.

Etapa 5 — calendar: calendário probabilístico empírico P(≥1 foco) por mês
civil (fração de anos com ≥1 foco na região, dados reais sem DEMO).
Etapa 5 — anomalies: comparação do mês observado vs baseline do mesmo mês
civil (média/desvio), com z-score e nível honesto (`info` quando a base é
escassa).
"""

from __future__ import annotations

import json
import statistics as st
from datetime import date
from typing import Any, Callable

from sqlalchemy import text

from pipeline.db import get_engine
from pipeline.version import PIPELINE_VERSION

# Parâmetros científicos explícitos (honestidade + reprodutibilidade):
MIN_OVERLAP_STEPS = 6       # meses de calibração para considerar modelo "medium"
MIN_YEARS_CALENDAR = 3      # anos por bucket para confidence > "low"
MIN_BASELINE_STEPS = 3      # baselines anteriores p/ anomalia não ser só ruído


def _region_bbox(conn, region_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text("SELECT id, name, is_demo, bbox_w, bbox_e, bbox_s, bbox_n "
             "FROM regions WHERE id = :id"),
        {"id": region_id},
    ).fetchone()
    if row is None or row.bbox_w is None:
        return None
    return dict(row._mapping)


def _counts_by_month(conn, bbox: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """Contagens mensais REAIS (is_demo=FALSE) dentro do bbox da região.

    Retorna listas prontas para harmonização/calendário; se a região não tiver
    bbox fixado, usa todo o banco (escopo global)."""
    if bbox:
        where_geo = ("d.lon >= :w AND d.lon <= :e AND d.lat >= :s AND d.lat <= :n")
        geo_params = {"w": bbox["bbox_w"], "e": bbox["bbox_e"],
                      "s": bbox["bbox_s"], "n": bbox["bbox_n"]}
        scope = f"região {bbox['name']}"
    else:
        where_geo = "TRUE"
        geo_params = {}
        scope = "escopo global (sem bbox)"
    rows = conn.execute(
        text(f"""
            SELECT DATE_TRUNC('month', d.acquired_at)::date AS month,
                   COALESCE(SUM((d.instrument = 'MODIS')::int), 0)  AS modis,
                   COALESCE(SUM((d.instrument = 'VIIRS')::int), 0) AS viirs
            FROM fire_detections d
            WHERE d.is_demo = FALSE AND {where_geo}
            GROUP BY 1 ORDER BY 1
        """),
        geo_params,
    ).fetchall()
    result = [{"month": r.month, "modis": int(r.modis), "viirs": int(r.viirs)} for r in rows]
    return result, scope


def _median_ratio(pairs: list[tuple[float, float]]) -> float:
    """Razão de medianas VIIRS/MODIS nos pares (mesmo período, mesmo lugar)."""
    ratios = [v / m for m, v in pairs if m > 0]
    return st.median(ratios) if ratios else 1.0


def _run_command(command: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Grava pipeline_runs (idempotente: running → ok/error), devolve o resultado."""
    with get_engine().begin() as conn:
        run_id = conn.execute(
            text("""
                INSERT INTO pipeline_runs (command, status, pipeline_version, params)
                VALUES (:cmd, 'running', :ver, CAST(:params AS jsonb)) RETURNING id
            """),
            {"cmd": command, "ver": PIPELINE_VERSION,
             "params": json.dumps({"started": str(date.today()), "command": command})},
        ).scalar_one()
    try:
        result = fn()
    except Exception as exc:
        with get_engine().begin() as conn:
            conn.execute(
                text("""
                    UPDATE pipeline_runs
                        SET status='error', finished_at=now(), result=CAST(:r AS jsonb),
                            errors=CAST(:e AS jsonb)
                        WHERE id = :id
                """),
                {"id": run_id, "r": json.dumps({"ok": False}),
                 "e": json.dumps({"error": str(exc)[:2000]})},
            )
        raise
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE pipeline_runs
                    SET status='ok', finished_at=now(), result=CAST(:r AS jsonb)
                    WHERE id = :id
            """),
            {"id": run_id, "r": json.dumps(result, default=str)},
        )
    return result


def harmonize(region_id: int = 1, start: str | None = None, end: str | None = None) -> dict:
    """Etapa 4: calibra MODIS→VIIRS e grava harmonized_series (mensal)."""

    def _do() -> dict:
        with get_engine().begin() as conn:
            bbox = _region_bbox(conn, region_id)
            if bbox is None:
                return {"status": "error", "message": f"região {region_id} sem bbox fixado"}
            counts, scope = _counts_by_month(conn, bbox)

            if start:
                counts = [c for c in counts if c["month"] >= date.fromisoformat(start)]
            if end:
                counts = [c for c in counts if c["month"] <= date.fromisoformat(end)]

            overlap = [c for c in counts if c["modis"] > 0 and c["viirs"] > 0]
            quality = "medium" if len(overlap) >= MIN_OVERLAP_STEPS else "low"
            factor = _median_ratio([(c["modis"], c["viirs"]) for c in overlap]) if overlap else 1.0
            has_overlap = len(overlap) > 0
            flag = "ok" if (quality == "medium" and has_overlap) else "low_confidence"

            # modelo de harmonização (proveniência)
            model_id = conn.execute(
                text("""
                    INSERT INTO harmonization_models (
                        name, method, region_level, calib_start, calib_end, daynight,
                        params, metrics, quality, pipeline_version
                    ) VALUES (
                        :name, 'median_ratio', 'state', :cs, :ce, NULL,
                        CAST(:params AS jsonb), CAST(:metrics AS jsonb), :quality, :ver
                    ) RETURNING id
                """),
                {
                    "name": f"MODIS→VIIRS {bbox['name']}",
                    "cs": min((c["month"] for c in overlap), default=None),
                    "ce": max((c["month"] for c in overlap), default=None),
                    "params": json.dumps({
                        "min_overlap_steps": MIN_OVERLAP_STEPS,
                        "overlap_steps_available": len(overlap),
                        "scale_target": "VIIRS (375 m)",
                    }),
                    "metrics": json.dumps({
                        "median_ratio": factor,
                        "pairwise_ratios": len(overlap),
                        "note": "overlap parcial — fator provisório" if has_overlap
                        else "SEM overlap MODIS×VIIRS nos dados atuais — fator neutro 1.0",
                    }),
                    "quality": quality,
                    "ver": PIPELINE_VERSION,
                },
            ).scalar_one()

            # série unificada (idempotente: substitui linhas da mesma região/period_type)
            conn.execute(
                text("DELETE FROM harmonized_series WHERE region_id=:r AND period_type='month'"),
                {"r": region_id},
            )
            series_rows = 0
            insufficient_flagged = 0
            for c in counts:
                if c["viirs"] > 0:
                    source_kind, instrument_used, value_raw, value_viirs = (
                        "viirs_raw", "VIIRS", float(c["viirs"]), float(c["viirs"]))
                elif c["modis"] > 0:
                    # Sem VIIRS: MODIS harmonizado (fator), flag honesta quando fraco.
                    value_raw = float(c["modis"])
                    value_viirs = value_raw * factor
                    source_kind, instrument_used = "modis_harmonized", "MODIS"
                else:
                    continue  # mês sem detecções não entra na série
                row_flag = flag
                if source_kind == "modis_harmonized" and not has_overlap:
                    row_flag = "insufficient"
                    insufficient_flagged += 1
                conn.execute(
                    text("""
                        INSERT INTO harmonized_series (
                            region_id, period_type, period_start, value_source,
                            instrument_used, value_raw, value_viirs, ci_low, ci_high,
                            method, model_id, quality_flag, is_demo
                        ) VALUES (
                            :r, 'month', :p, :src, :instr, :vraw, :vviirs, :lo, :hi,
                            :method, :model, :flag, FALSE
                        )
                    """),
                    {"r": region_id, "p": c["month"], "src": source_kind,
                     "instr": instrument_used, "vraw": value_raw,
                     "vviirs": round(value_viirs, 3),
                     "lo": round(value_viirs * 0.8, 3) if source_kind == "modis_harmonized"
                     else value_viirs,
                     "hi": round(value_viirs * 1.25, 3) if source_kind == "modis_harmonized"
                     else value_viirs,
                     "method": "median_ratio" if source_kind == "modis_harmonized" else None,
                     "model": model_id if source_kind == "modis_harmonized" else None,
                     "flag": row_flag},
                )
                series_rows += 1

            return {
                "status": "ok",
                "command": "harmonize",
                "region": bbox["name"],
                "scope": scope,
                "model_id": model_id,
                "median_ratio": round(factor, 4) if has_overlap else None,
                "quality": quality,
                "flag": flag,
                "overlap_months": len(overlap),
                "series_months": series_rows,
                "insufficient_flagged": insufficient_flagged,
                "honest_note": (
                    "Modelo provisório: overlap MODIS×VIIRS insuficiente "
                    f"({len(overlap)}/{MIN_OVERLAP_STEPS} meses). Fator {factor:.3f} "
                    "deve ser recalibrado após o backfill histórico (MODIS_SP 2000→ + "
                    "VIIRS_SNPP_SP). Meses sem VIIRS ficam marcados conforme flag."
                ) if quality == "low" else "Modelo com overlap adequado (medium).",
            }

    return _run_command("harmonize", _do)


def calendar(region_id: int = 1) -> dict:
    """Etapa 5: calendário probabilístico empírico mensal P(≥1 foco)."""

    def _do() -> dict:
        with get_engine().begin() as conn:
            bbox = _region_bbox(conn, region_id)
            if bbox is None:
                return {"status": "error", "message": f"região {region_id} sem bbox fixado"}
            counts, scope = _counts_by_month(conn, bbox)

            # histórico por mês civil escreve uma linha por mês com dados
            conn.execute(
                text("DELETE FROM calendar_probabilities WHERE region_id=:r AND period_type='month'"),
                {"r": region_id},
            )
            buckets: dict[int, list[float]] = {}
            for c in counts:
                total = c["modis"] + c["viirs"]
                y = c["month"].year
                buckets.setdefault(c["month"].month, []).append(float(total))

            rows_written = 0
            for month_of_year in range(1, 13):
                values = buckets.get(month_of_year, [])
                if not values:
                    continue  # nunca inventar: mês sem base não recebe linha falsa
                years_used = len(values)
                p_observed = sum(1 for v in values if v >= 1) / years_used
                confidence = "low" if years_used < MIN_YEARS_CALENDAR else "medium"
                expected = st.mean(values)
                row_flag = "ok" if confidence != "low" else "low_confidence"
                conn.execute(
                    text("""
                        INSERT INTO calendar_probabilities (
                            region_id, period_type, period_of_year, probability,
                            ci_low, ci_high, years_used, expected_count,
                            harmonized_share, method, pipeline_version, confidence, is_demo
                        ) VALUES (
                            :r, 'month', :poy, :prob, :lo, :hi, :years, :exp,
                            NULL, 'empirical_year_fraction', :ver, :conf, FALSE
                        )
                    """),
                    {"r": region_id, "poy": month_of_year, "prob": p_observed,
                     "lo": max(0.0, p_observed - 0.15), "hi": min(1.0, p_observed + 0.15),
                     "years": years_used, "exp": round(expected, 3),
                     "ver": PIPELINE_VERSION, "conf": confidence},
                )
                rows_written += 1

            months_with_data = len(buckets)
            return {
                "status": "ok",
                "command": "calendar",
                "region": bbox["name"],
                "scope": scope,
                "rows": rows_written,
                "months_covered": months_with_data,
                "honest_note": (
                    f"{months_with_data}/12 meses com base real; years_used baixo → "
                    "confidence 'low' em dezembro e demais (P cresce quando o backfill "
                    "preencher os anos históricos)." if months_with_data < 12
                    and rows_written else "Calendário empírico com 12 meses cobertos."
                ),
            }

    return _run_command("calendar", _do)


def anomalies(region_id: int = 1, threshold_warning: float = 2.0,
              threshold_alert: float = 3.0) -> dict:
    """Etapa 5: anomalias (mês observado x baseline do mesmo mês civil)."""

    def _do() -> dict:
        with get_engine().begin() as conn:
            bbox = _region_bbox(conn, region_id)
            if bbox is None:
                return {"status": "error", "message": f"região {region_id} sem bbox fixado"}
            counts, scope = _counts_by_month(conn, bbox)

            conn.execute(
                text("DELETE FROM anomaly_results WHERE region_id=:r AND is_demo=FALSE"),
                {"r": region_id},
            )
            rows_written = 0
            for c in counts:
                observed = c["modis"] + c["viirs"]
                month_of_year = c["month"].month
                baseline = [
                    x["modis"] + x["viirs"]
                    for x in counts
                    if x["month"].month == month_of_year and x["month"] != c["month"]
                ]
                expected = st.mean(baseline) if baseline else None
                level = "info"
                score = None
                notes = None
                if baseline and expected and len(baseline) >= MIN_BASELINE_STEPS:
                    sd = st.stdev(baseline)
                    if sd > 0:
                        score = (observed - expected) / sd
                        if score >= threshold_alert:
                            level = "alert"
                        elif score >= threshold_warning:
                            level = "warning"
                else:
                    notes = ("Baseline insuficiente (menos de "
                             f"{MIN_BASELINE_STEPS} anos no mesmo mês) — nível mantido 'info'.")
                # grava mesmo com level 'info' (trilha de auditoria) — nota sempre presente
                conn.execute(
                    text("""
                        INSERT INTO anomaly_results (
                            region_id, period_start, period_end, observed, expected,
                            score, level, method, notes, pipeline_version, is_demo
                        ) VALUES (
                            :r, :ps, :pe, :obs, :exp, :score, :level, 'zscore_monthly',
                            :notes, :ver, FALSE
                        )
                    """),
                    {"r": region_id, "ps": c["month"], "pe": c["month"],
                     "obs": observed, "exp": expected,
                     "score": round(score, 3) if score is not None else None,
                     "level": level,
                     "notes": notes or ("Baseline suficiente: z-score válido."),
                     "ver": PIPELINE_VERSION},
                )
                rows_written += 1

            return {
                "status": "ok",
                "command": "anomalies",
                "region": bbox["name"],
                "scope": scope,
                "rows": rows_written,
                "honest_note": (
                    "Anomalias com baseline escasso ficam 'info' com nota; níveis "
                    "warning/alert exigem ao menos "
                    f"{MIN_BASELINE_STEPS} anos do mesmo mês civil."
                ),
                "method": "zscore por mês civil (média/desvio dos outros anos)",
            }

    return _run_command("anomalies", _do)
