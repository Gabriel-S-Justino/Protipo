"""Resumable national backfill; verified coverage is the durable checkpoint."""

from datetime import date, timedelta, datetime, timezone
import time

from pipeline.firms import fetch_area, _cache_path
from pipeline.ingest import ingest
from pipeline.db import fetch_all
from pipeline.geography import BRAZIL_BBOX
from pipeline.normalization import SOURCES

DEFAULT_BBOX = BRAZIL_BBOX
WINDOW_DAYS = 5


def _window_iter(start, end):
    cursor = start
    while cursor <= end:
        last = min(cursor + timedelta(days=WINDOW_DAYS - 1), end)
        yield cursor, last
        cursor = last + timedelta(days=1)


def _covered_days(source, first, last):
    rows = fetch_all(
        """
        SELECT day FROM acquisition_coverage
        WHERE scope='BR' AND source_code=:source AND day BETWEEN :first AND :last
    """,
        {"source": source, "first": first, "last": last},
    )
    return {row["day"] for row in rows}


def run_backfill(source, start, end, sleep_s=1, limit=0, bbox=DEFAULT_BBOX):
    first = date.fromisoformat(start)
    last = min(
        date.fromisoformat(end), datetime.now(timezone.utc).date() - timedelta(days=1)
    )
    if last < first or sleep_s < 0 or limit < 0:
        raise ValueError("Intervalo, pausa ou limite inválido.")
    if source not in SOURCES or tuple(bbox) != BRAZIL_BBOX:
        raise ValueError("Use uma fonte FIRMS conhecida e o recorte nacional.")
    windows = list(_window_iter(first, last))
    covered = _covered_days(source, first, last)
    pending = [
        (begin, finish)
        for begin, finish in windows
        if not all(
            begin + timedelta(days=i) in covered
            for i in range((finish - begin).days + 1)
        )
    ]
    selected = pending[:limit] if limit else pending
    errors, accepted, completed = [], 0, 0
    for begin, finish in selected:
        days = (finish - begin).days + 1
        try:
            fetch_area(source, bbox, days, begin.isoformat())
            report = ingest(
                [str(_cache_path(source, bbox, days, begin.isoformat()))], source
            )
            records = report["files"]
            accepted += sum(f.get("accepted", 0) for f in records)
            if any(f.get("rejected", 0) for f in records):
                raise ValueError(
                    "Janela contém linhas rejeitadas; cobertura incompleta."
                )
            if sum(f.get("coverage_days", 0) for f in records) < days:
                raise ValueError(
                    "A ingestão não confirmou cobertura nacional de todos os dias."
                )
            completed += 1
        except Exception as exc:
            errors.append({"start": str(begin), "end": str(finish), "error": str(exc)})
        time.sleep(sleep_s)
    remaining = len(pending) - completed
    return {
        "status": "partial" if errors else "in_progress" if remaining else "ok",
        "source": source,
        "start": str(first),
        "end": str(last),
        "windows_total": len(windows),
        "windows_already_covered": len(windows) - len(pending),
        "windows_attempted": len(selected),
        "windows_completed": completed,
        "windows_remaining": remaining,
        "accepted": accepted,
        "errors": errors,
        "next_action": (
            "Execute novamente com os mesmos parâmetros para continuar."
            if remaining
            else None
        ),
    }
