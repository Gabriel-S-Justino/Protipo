"""Implementação dos comandos da CLI (delegação de `python -m pipeline <comando>`)."""

from __future__ import annotations

import argparse
import json


def run(args: argparse.Namespace) -> int:
    cmd = args.command
    if cmd == "fetch":
        from pipeline.firms import fetch_area

        # Placeholder com bbox do Ceará e janela máxima — para o backfill eficiente
        # usar o Archive Download (fase de backfill), não a Area API.
        csv = fetch_area("MODIS_SP", (-39.3, -7.9, -37.2, -2.8), day_range=1)
        if csv.strip():
            print("CSV recebido (para ingestão use: ingest)")
            print(json.dumps({"preview_chars": len(csv)}))
        else:
            print("Sem detecções na janela/resolução consultada (resposta vazia da FIRMS).")
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
        from pipeline.firms import map_key_status

        try:
            print(map_key_status())
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
