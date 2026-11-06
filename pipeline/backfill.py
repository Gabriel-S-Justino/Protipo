"""Backfill histórico da FIRMS em janelas de 5 dias (limite real da Area API,
validado com HTTP 400 fora de [1..5]).

Cada janela: fetch (cache por checksum → não re-baixa) → ingest idempotente
(ON CONFLICT DO NOTHING). Pausa de cortesia entre janelas para respeitar os
limites de taxa da chave MAP_KEY. Erros pontuais NÃO abortam o backfill: a
janela falha fica registrada no relatório (retry rápido embutido no fetch).
"""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

from pipeline.firms import fetch_area
from pipeline.ingest import ingest

# Bbox padrão: Ceará (igual ao comando fetch — documentado em docs/DATA_PIPELINE.md)
DEFAULT_BBOX = (-39.3, -7.9, -37.2, -2.8)
WINDOW_DAYS = 5


def _window_iter(start: dt.date, end: dt.date):
    """Janelas [d, d+WINDOW_DAYS) do start até o end (inclusivo no fim)."""
    cursor = start
    while cursor < end:
        window_end = min(cursor + dt.timedelta(days=WINDOW_DAYS), end)
        yield cursor, window_end
        cursor = window_end


def run_backfill(
    source: str,
    start: str,
    end: str,
    sleep_s: float = 1.0,
    limit: int = 0,
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX,
) -> dict:
    start_d = dt.date.fromisoformat(start)
    end_d = dt.date.fromisoformat(end)
    if end_d <= start_d:
        raise ValueError("--end deve ser posterior a --start")
    if end_d > dt.date.today():
        end_d = dt.date.today()

    windows = list(_window_iter(start_d, end_d))
    if limit:
        windows = windows[:limit]

    windows_ok = 0
    windows_empty = 0
    windows_error = 0
    accepted = 0
    rejected = 0
    errors: list[dict[str, str]] = []
    t0 = time.monotonic()

    for w_start, w_end in windows:
        date_str = w_start.isoformat()
        try:
            csv_text = fetch_area(source, bbox, day_range=WINDOW_DAYS, date=date_str)
            if not csv_text.strip() or len(csv_text.strip().splitlines()) < 2:
                windows_empty += 1
                time.sleep(sleep_s)
                continue
            cache_path = Path(cache_file_name(source, bbox, date_str))
            report = ingest([str(cache_path)], source)
            for f in report.get("files", []):
                accepted += f.get("accepted", 0)
                rejected += f.get("rejected", 0)
            windows_ok += 1
        except Exception as exc:  # noqa: BLE001 — janela falha não derruba o backfill
            windows_error += 1
            errors.append({"window": date_str, "error": str(exc)[:300]})
        time.sleep(sleep_s)

    return {
        "status": "ok" if windows_error == 0 else "partial",
        "command": "backfill",
        "source": source,
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
        "windows_total": len(windows),
        "windows_ok": windows_ok,
        "windows_empty": windows_empty,
        "windows_error": windows_error,
        "accepted": accepted,
        "rejected": rejected,
        "errors_sample": errors[:10],
        "duration_s": round(time.monotonic() - t0, 1),
        "honest_note": (
            "Janelas vazias são esperadas (não é erro). Reexecutar o backfill é "
            "barato: cache por checksum + ingest idempotente (ON CONFLICT DO NOTHING)."
        ),
    }


def cache_file_name(source: str, bbox: tuple[float, float, float, float], date_str: str) -> Path:
    """Nome do arquivo de cache exactamente como fetch_area grava (mesma chave)."""
    from pipeline.firms import _cache_path

    return _cache_path(source, bbox, WINDOW_DAYS, date_str)
