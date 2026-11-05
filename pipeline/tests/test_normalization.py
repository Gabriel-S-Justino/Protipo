"""Testes do pipeline: normalização/validação sem banco."""

import pytest

from pipeline.normalization import (
    NormalizeResult,
    normalize_csv_text,
    parse_confidence,
    _parse_acquired,
)

MODIS_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,daynight
-3.5,-38.9,340.2,1.0,1.0,2023-08-15,1430,T,62,6.1,290.1,-1.2
91.0,-38.9,340.2,1.0,1.0,2023-08-15,1430,T,62,6.1,290.1,D
-3.5,-38.9,340.2,1.0,1.0,carol,1430,T,62,6.1,290.1,D
"""

VIIRS_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,conf,version,bright_ti5,daynight
-4.1,-39.2,350.1,0.8,0.8,2023-09-01,1335,S-NPP,h,2.1,295.5,N
-4.1,-39.2,350.1,0.8,0.8,2023-09-01,1335,S-NPP,h,2.1,295.5,N
"""


def make_result() -> NormalizeResult:
    return NormalizeResult()


def test_modis_normalization_and_rejects() -> None:
    res = normalize_csv_text(MODIS_CSV, "MODIS_SP")
    assert len(res.records) == 1
    assert len(res.rejects) == 2
    rec = res.records[0]
    assert rec.satellite == "Terra"
    assert rec.instrument == "MODIS"
    assert rec.acquired_at is not None
    assert rec.acquired_at.hour == 14 and rec.acquired_at.minute == 30
    assert rec.confidence_raw == "62"
    assert rec.confidence_norm == 62.0
    assert rec.daynight == "D"  # daynight=-1.2 não começa com 'N' → classificado 'D'


def test_modis_confidence_out_of_range_clamped_and_invalid_data_rejected() -> None:
    raw, norm = parse_confidence("150", True)
    assert norm == 100.0  # clampa (documentado)
    raw, norm = parse_confidence("x", True)  # MODIS NRT sem informação
    assert raw == "x" and norm is None


def test_viirs_categorical_confidence() -> None:
    res = normalize_csv_text(VIIRS_CSV, "VIIRS_SNPP_SP")
    assert len(res.records) == 1  # duplicado no arquivo não entra
    assert res.duplicates_in_file == 1
    rec = res.records[0]
    assert rec.confidence_raw == "h"
    assert rec.confidence_norm == 100.0
    assert rec.satellite == "S-NPP"
    assert rec.daynight == "N"


def test_invalid_dates_rejected() -> None:
    assert _parse_acquired("invalid", "1030") is None
    assert _parse_acquired("2023-02-30", "1030") is None
    assert _parse_acquired("2023-08-15", "2400") is None
    ok = _parse_acquired("2023-08-15", "0615")
    assert ok is not None and ok.hour == 6


def test_unknown_source_rejected_early() -> None:
    with pytest.raises(ValueError):
        normalize_csv_text(MODIS_CSV, "FONTE_INVENTADA")
