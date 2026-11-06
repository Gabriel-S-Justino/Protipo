"""National pipeline command dispatch."""

import json
from datetime import date, timedelta, datetime, timezone
from pathlib import Path


def run(args):
    cmd = args.command
    if cmd == "boundaries":
        from pipeline.geography import boundaries

        result = boundaries()
    elif cmd == "update":
        from pipeline.firms import fetch_area, _cache_path
        from pipeline.geography import BRAZIL_BBOX
        from pipeline.ingest import ingest
        from pipeline.analytics import harmonize, calendar, anomalies

        # Complete UTC days; failures stop publication and are visible to CI.
        begin = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
        for source in ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "MODIS_NRT"):
            fetch_area(source, BRAZIL_BBOX, 2, begin)
            ingest([str(_cache_path(source, BRAZIL_BBOX, 2, begin))], source)
        result = {
            "status": "ok",
            "harmonize": harmonize(),
            "calendar": calendar(),
            "anomalies": anomalies(),
        }
    elif cmd == "fetch":
        from pipeline.firms import fetch_area, _cache_path
        from pipeline.geography import BRAZIL_BBOX

        payload = fetch_area(args.source, BRAZIL_BBOX, args.days, args.date)
        result = {
            "source": args.source,
            "file": str(_cache_path(args.source, BRAZIL_BBOX, args.days, args.date)),
            "rows": max(0, len(payload.strip().splitlines()) - 1),
        }
    elif cmd == "ingest":
        from pipeline.ingest import ingest

        result = ingest(args.paths, args.source)
    elif cmd == "validate":
        from pipeline.normalization import normalize_csv_text

        results = []
        for name in args.paths:
            normalized = normalize_csv_text(
                Path(name).read_text(encoding="utf-8-sig"), args.source
            )
            results.append(
                {
                    "file": name,
                    "accepted": len(normalized.records),
                    "rejected": len(normalized.rejects),
                }
            )
        result = {"files": results}
    elif cmd == "backfill":
        from pipeline.backfill import run_backfill

        result = run_backfill(args.source, args.start, args.end, args.sleep, args.limit)
    elif cmd in ("harmonize", "calendar", "anomalies"):
        from pipeline import analytics

        result = getattr(analytics, cmd)()
    elif cmd == "status":
        from pipeline.firms import data_availability

        print(data_availability(args.sensor))
        return 0
    elif cmd == "report":
        from pipeline.db import fetch_all

        result = {
            "batches": fetch_all(
                "SELECT * FROM ingestion_batches ORDER BY id DESC LIMIT 20"
            )
        }
    elif cmd == "seed-demo":
        from pipeline.demo import seed_demo

        result = seed_demo(args.rows, args.years)
    elif cmd == "clear-demo":
        from pipeline.demo import clear_demo

        result = clear_demo()
    else:
        raise ValueError(f"Comando desconhecido: {cmd}")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return (
        0
        if result.get("status", "ok") in {"ok", "insufficient_data", "in_progress"}
        else 1
    )
