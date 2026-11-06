"""CLI única do pipeline (argparse, sem dependências fora do requirements)."""

from __future__ import annotations

import argparse
import sys

from pipeline.version import PIPELINE_VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description=(
            "Pipeline científico da Fire Intelligence Platform (roda fora da Vercel). "
            "Requer .env com DATABASE_URL_DIRECT e (para fetch/backfill) MAP_KEY."
        ),
    )
    parser.add_argument("--version", action="version", version=PIPELINE_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser(
        "fetch", help="Baixa CSV da FIRMS para o Brasil (requere MAP_KEY)"
    )
    p_fetch.add_argument(
        "--source", required=True, help="ex.: MODIS_NRT, VIIRS_NOAA21_NRT"
    )
    p_fetch.add_argument(
        "--days", type=int, default=1, help="Janela 1..5 (limite real da Area API)"
    )
    p_fetch.add_argument(
        "--date", help="Data inicial AAAA-MM-DD (opcional; sem ela = recentes)"
    )

    p_ingest = sub.add_parser("ingest", help="Ingestão idempotente de arquivo local")
    p_ingest.add_argument("paths", nargs="+", help="Arquivo(s) CSV FIRMS (MODIS/VIIRS)")
    p_ingest.add_argument(
        "--source",
        required=True,
        help="Código da fonte, ex.: MODIS_SP, VIIRS_SNPP_SP (cf. tabela data_sources)",
    )

    p_valid = sub.add_parser(
        "validate", help="Valida arquivo(s) CSV (presumo nada sobre o esquema)"
    )
    p_valid.add_argument("paths", nargs="+")
    p_valid.add_argument("--source", required=True)

    sub.add_parser("harmonize", help="Calibra MODIS→VIIRS e grava harmonized_series")
    sub.add_parser(
        "calendar", help="Calendário probabilístico semanal e mensal (empírico)"
    )
    sub.add_parser("anomalies", help="Anomalias mensais (zscore vs baseline do mês)")

    for sub_an in (
        harmonize_p := sub.choices["harmonize"],
        sub.choices["calendar"],
        sub.choices["anomalies"],
    ):
        sub_an.add_argument(
            "--region",
            type=int,
            default=None,
            help="Compatibilidade; processamento nacional",
        )
    sub.choices["harmonize"].add_argument(
        "--start", help="AAAA-MM-DD início do período (opcional)"
    )
    sub.choices["harmonize"].add_argument("--end", help="AAAA-MM-DD fim (opcional)")

    backfill_p = sub.add_parser(
        "backfill", help="Backfill histórico em janelas de 5 dias (cache + throttle)"
    )
    backfill_p.add_argument(
        "--source", required=True, help="ex.: MODIS_SP, VIIRS_SNPP_SP"
    )
    backfill_p.add_argument("--start", required=True, help="data inicial AAAA-MM-DD")
    backfill_p.add_argument(
        "--end", required=True, help="data final AAAA-MM-DD (inclusiva)"
    )
    backfill_p.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="pausa entre janelas (s) — cortesia à API",
    )
    backfill_p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="máximo de janelas pendentes por execução (0 = todas; retoma pela cobertura)",
    )
    sub.add_parser("report", help="Relatório de ingestões/execuções")

    p_status = sub.add_parser("status", help="Data availability da FIRMS")
    p_status.add_argument(
        "--sensor", required=True, help="ex.: VIIRS_SNPP_SP / MODIS_SP"
    )

    p_seed = sub.add_parser(
        "seed-demo", help="Popula dados sintéticos DEMO (is_demo=true)"
    )
    p_seed.add_argument("--rows", type=int, default=5000)
    p_seed.add_argument("--years", type=int, default=5)

    sub.add_parser("boundaries", help="Importa Brasil e 27 UFs do IBGE")
    sub.add_parser(
        "update",
        help="Coleta os últimos dias completos e reconstrói produtos nacionais",
    )
    sub.add_parser("clear-demo", help="Remove dados DEMO")

    return parser


def main(argv: list[str] | None = None) -> int:
    from pipeline import commands

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return commands.run(args)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 — CLI top-level: reporta erro com precisão
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
