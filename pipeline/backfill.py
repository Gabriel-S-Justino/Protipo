"""Inclusive, non-overlapping acquisition windows. Empty valid windows are ingested too."""

from datetime import date, timedelta, datetime, timezone
import time
from pipeline.firms import fetch_area, _cache_path
from pipeline.ingest import ingest
from pipeline.geography import BRAZIL_BBOX

DEFAULT_BBOX = BRAZIL_BBOX
WINDOW_DAYS = 5


def _window_iter(start, end):
    cursor = start
    while cursor <= end:
        last = min(cursor + timedelta(days=WINDOW_DAYS - 1), end)
        yield cursor, last
        cursor = last + timedelta(days=1)


def run_backfill(source, start, end, sleep_s=1, limit=0, bbox=DEFAULT_BBOX):
    first, last = date.fromisoformat(start), min(
        date.fromisoformat(end), datetime.now(timezone.utc).date() - timedelta(days=1)
    )
    if last < first or sleep_s < 0 or limit < 0:
        raise ValueError("Intervalo, pausa ou limite inválido.")
    windows = list(_window_iter(first, last))
    if limit:
        windows = windows[:limit]
    errors = []
    accepted = 0
    for begin, finish in windows:
        days = (finish - begin).days + 1
        try:
            fetch_area(source, bbox, days, begin.isoformat())
            result = ingest(
                [str(_cache_path(source, bbox, days, begin.isoformat()))], source
            )
            accepted += sum(f.get("accepted", 0) for f in result["files"])
        except Exception as exc:
            errors.append({"start": str(begin), "end": str(finish), "error": str(exc)})
        time.sleep(sleep_s)
    return {
        "status": "partial" if errors else "ok",
        "windows": len(windows),
        "accepted": accepted,
        "errors": errors,
    }
