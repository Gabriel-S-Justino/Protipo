"""Normalização e validação de linhas FIRMS.

Regras científicas/código:
- Não presumir esquema único: detectar colunas por cabeçalho (sinônimos por sensor).
- Validar coordenadas e datas; registrar rejeitados com motivo; nunca substituir
  ausentes por zero; nunca inventar dados.
- Confiança: MODIS numérica 0-100; VIIRS categórica l/n/h → escala comum ordinal
  DOCUMENTADA (l=0, n=50, h=100) preservando o valor original em `confidence_raw`.
- Idem key: (satellite, acquired_at, lat, lon, daynight, confidence_raw).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# --- Mapeamento de colunas por sinônimo (MODIS C6.1 / VIIRS 375 m, FIRMS CSV) ---
COLUMN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "latitude": ("latitude", "lat", "y"),
    "longitude": ("longitude", "lon", "lng", "x"),
    "acquired_date": ("acq_date", "acquired_date", "date"),
    "acquired_time": ("acq_time", "acquired_time", "time"),
    "satellite": ("satellite", "platform", "sat_name"),
    "instrument": ("instrument", "sensor"),
    "confidence": ("confidence", "conf"),
    "frp": ("frp", "fire_power"),
    "brightness": ("brightness", "bright_ti4"),
    "bright_t31": ("bright_t31", "bright_ti5"),
    "scan": ("scan",),
    "track": ("track",),
    "version": ("version",),
    "daynight": ("daynight", "day", "daynight_flag"),
}

SOURCES: dict[str, dict[str, str]] = {
    "MODIS_SP": {"sensor": "MODIS", "instrument": "MODIS"},
    "MODIS_NRT": {"sensor": "MODIS", "instrument": "MODIS"},
    "VIIRS_SNPP_SP": {"sensor": "VIIRS", "instrument": "VIIRS"},
    "VIIRS_SNPP_NRT": {"sensor": "VIIRS", "instrument": "VIIRS"},
    "VIIRS_NOAA20_SP": {"sensor": "VIIRS", "instrument": "VIIRS"},
    "VIIRS_NOAA20_NRT": {"sensor": "VIIRS", "instrument": "VIIRS"},
    "VIIRS_NOAA21_SP": {"sensor": "VIIRS", "instrument": "VIIRS"},
    "VIIRS_NOAA21_NRT": {"sensor": "VIIRS", "instrument": "VIIRS"},
}

SAT_BY_SOURCE = {
    "VIIRS_SNPP_SP": "Suomi-NPP",
    "VIIRS_SNPP_NRT": "Suomi-NPP",
    "VIIRS_NOAA20_SP": "NOAA-20",
    "VIIRS_NOAA20_NRT": "NOAA-20",
    "VIIRS_NOAA21_SP": "NOAA-21",
    "VIIRS_NOAA21_NRT": "NOAA-21",
}


@dataclass
class NormalizedRecord:
    satellite: str
    instrument: str
    acquired_at: datetime
    lat: float
    lon: float
    daynight: str
    confidence_raw: str | None
    confidence_norm: float | None
    frp: float | None = None
    brightness: float | None = None
    bright_t31: float | None = None
    scan: float | None = None
    track: float | None = None
    version: float | None = None
    raw_attributes: dict[str, Any] = field(default_factory=dict)

    def idem_key(self) -> tuple:
        return (
            self.satellite,
            self.acquired_at,
            round(self.lat, 6),
            round(self.lon, 6),
            self.daynight,
            self.confidence_raw,
        )


@dataclass
class Reject:
    line_no: int
    reason: str


@dataclass
class NormalizeResult:
    records: list[NormalizedRecord] = field(default_factory=list)
    rejects: list[Reject] = field(default_factory=list)
    duplicates_in_file: int = 0


def _pick(header: list[str], row: list[str], field_name: str) -> str | None:
    names = COLUMN_SYNONYMS.get(field_name, ())
    for idx, col in enumerate(header):
        if col.strip().lower() in names:
            if idx < len(row) and row[idx].strip() != "":
                return row[idx].strip()
            return None
    return None


def parse_confidence(value: str | None, is_modis: bool) -> tuple[str | None, float | None]:
    """MODIS 0-100 numérico; VIIRS l/n/h → 0/50/100 (ordinal documentada, aproximação)."""
    if value is None:
        return None, None
    v = value.strip()
    if is_modis:
        try:
            num = float(v)
        except ValueError:
            # 'x' em MODIS NRT = sem informação de confiança — preservar original sem inventar.
            return v[:16], None
        return v, max(0.0, min(100.0, num))
    if v not in ("l", "n", "h"):
        return v[:16], None
    return v, {"l": 0.0, "n": 50.0, "h": 100.0}[v]


def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_acquired(date_s: str, time_s: str | None) -> datetime | None:
    """FIRMS: acq_date AAAA-MM-DD (UTC), acq_time HHMM (UTC)."""
    if len(date_s) != 10:
        return None
    try:
        day = datetime.strptime(date_s, "%Y-%m-%d").date()
    except ValueError:
        return None
    hm = (time_s or "0000").rjust(4, "0")
    if not hm.isdigit():
        return None
    hh, mm = int(hm[:2]), int(hm[2:])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=timezone.utc)


def normalize_row(
    header: list[str],
    row: list[str],
    source_code: str,
    line_no: int,
    result: NormalizeResult,
    seen: set[tuple],
) -> None:
    info = SOURCES[source_code]
    is_modis = info["sensor"] == "MODIS"

    lat = _to_float(_pick(header, row, "latitude"))
    lon = _to_float(_pick(header, row, "longitude"))
    problems: list[str] = []
    if lat is None or lon is None or not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        problems.append("coordenadas ausentes/inválidas")

    date_s = _pick(header, row, "acquired_date")
    time_s = _pick(header, row, "acquired_time")
    acquired_at = _parse_acquired(date_s, time_s) if date_s else None
    if acquired_at is None:
        problems.append("data/hora ausente ou inválida")

    if problems:
        result.rejects.append(Reject(line_no=line_no, reason="; ".join(problems)))
        return

    conf_raw, conf_norm = parse_confidence(_pick(header, row, "confidence"), is_modis)
    dnight = (_pick(header, row, "daynight") or "D").upper()
    daynight = "N" if dnight.startswith("N") else "D"

    sat_s = _pick(header, row, "satellite")
    if sat_s and not is_modis:
        satellite = sat_s
    elif is_modis and sat_s:
        # MODIS: coluna 'satellite' pode ser 'T'/'A' → expande para nome legível.
        satellite = {"T": "Terra", "A": "Aqua"}.get(sat_s, sat_s)
    else:
        satellite = SAT_BY_SOURCE.get(source_code, sat_s or "unknown")

    rec = NormalizedRecord(
        satellite=satellite,
        instrument=info["instrument"],
        acquired_at=acquired_at,
        lat=lat,
        lon=lon,
        daynight=daynight,
        confidence_raw=conf_raw,
        confidence_norm=conf_norm,
        frp=_to_float(_pick(header, row, "frp")),
        brightness=_to_float(_pick(header, row, "brightness")),
        bright_t31=_to_float(_pick(header, row, "bright_t31")),
        scan=_to_float(_pick(header, row, "scan")),
        track=_to_float(_pick(header, row, "track")),
        version=_to_float(_pick(header, row, "version")),
        raw_attributes=dict(zip([h.strip() for h in header], [c.strip() for c in row])),
    )

    key = rec.idem_key()
    if key in seen:
        result.duplicates_in_file += 1
        return
    seen.add(key)
    result.records.append(rec)


def detect_header(line: str) -> list[str]:
    return [c.strip().strip('"') for c in line.strip().split(",")]


def normalize_csv_text(text: str, source_code: str) -> NormalizeResult:
    """Normaliza o CSV completo. Não presume ordem/presença de colunas por sensor."""
    if source_code not in SOURCES:
        raise ValueError(f"Fonte desconhecida: {source_code}")
    result = NormalizeResult()
    seen: set[tuple] = set()
    header: list[str] | None = None
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if header is None:
            header = detect_header(line)
            continue
        row = [c.strip().strip('"') for c in line.split(",")]
        try:
            normalize_row(header, row, source_code, line_no, result, seen)
        except Exception as exc:  # noqa: BLE001 — nunca abortar o arquivo por 1 linha ruim
            result.rejects.append(Reject(line_no=line_no, reason=f"exceção: {exc}"))
    return result
