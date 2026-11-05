"""Implementação dos comandos da CLI (delegação de `python -m pipeline <comando>`)."""

from __future__ import annotations

import argparse
import json


def run(args: argparse.Namespace) -> int:
    cmd = args.command
    if cmd == "fetch":
        from pipeline.firms import fetch_area

        # Bbox padrão: Ceará. Sem --date = últimos --days dias (NRT).
        csv = fetch_area(
            args.source,
            (-39.3, -7.9, -37.2, -2.8),
            day_range=args.days,
            date=args.date,
        )
        # fetch_area grava em data/raw com nome <source>_<hash>.csv (cache).
        from pathlib import Path

        from pipeline.firms import _cache_path  # noqa: PLC0415 — cache determinístico

        path = _cache_path(args.source, (-39.3, -7.9, -37.2, -2.8), args.days, args.date)
        if csv.strip():
            n_rows = max(0, len(csv.strip().splitlines()) - 1)
            print(
                json.dumps(
                    {"source": args.source, "file": str(path), "rows": n_rows,
                     "next_step": f"python -m pipeline ingest {path} --source {args.source}"},
                    indent=2,
                )
            )
        else:
            print(json.dumps({"source": args.source, "file": str(path), "rows": 0,
                              "note": "sem detecções na janela (resposta vazia da FIRMS)"}))
        return 0

    if cmd == "ingest":
        from pipeline.ingest import ingest

        report = ingest(args.paths, args.source)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    if cmd == "validate":
        from pathlib import Path

        from pipeline.normalization import normalize_csv_text

        for p in args.paths:
            text_csv = Path(p).read_text(encoding="utf-8", errors="replace")
            result = normalize_csv_text(text_csv, args.source)
            print(
                json.dumps(
                    {
                        "file": p,
                        "accepted": len(result.records),
                        "rejected": len(result.rejects),
                        "duplicated_in_file": result.duplicates_in_file,
                        "rejects_sample": [r.__dict__ for r in result.rejects[:10]],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0

    if cmd == "backfill":
        print(
            "backfill: implementado na fase 3 (janelas paginadas/Area API + Archive Download "
            "para o histórico em massa). Requer MAP_KEY.\n"
            "Roteiro: docs/DATA_PIPELINE.md"
        )
        return 2

    if cmd in ("harmonize", "calendar", "anomalies"):
        print(
            f"{cmd}: fase de implementação planejada — ver docs/HARMONIZATION.md / "
            "docs/CALENDAR_MODEL.md. Não há dados fakes."
        )
        return 2

    if cmd == "report":
        from pipeline.db import fetch_all

        rows = fetch_all(
            """
            SELECT id, source_code, status, records_total, records_accepted, records_rejected,
                   records_duplicated, created_at
            FROM ingestion_batches ORDER BY id DESC LIMIT 20
            """
        )
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        return 0

    if cmd == "status":
        from pipeline.firms import data_availability

        try:
            print(data_availability(args.sensor))
        except RuntimeError as exc:
            print(f"AVISO: {exc}")
            return 2
        return 0

    if cmd == "seed-demo":
        from pipeline.demo import seed_demo

        print(json.dumps(seed_demo(rows=args.rows, years=args.years), indent=2))
        return 0

    if cmd == "clear-demo":
        from pipeline.demo import clear_demo

        print(json.dumps(clear_demo(), indent=2))
        return 0

    raise AssertionError(f"comando desconhecido: {cmd}")
