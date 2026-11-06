"""Endpoint de detecções originais (paginado, limitado)."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.core import db
from backend.app.core.config import get_settings
from backend.app.schemas import DetectionOut

router = APIRouter(tags=["detections"])


@router.get("/detections", response_model=list[DetectionOut])
def list_detections(
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    instrument: str | None = Query(None, pattern="^(MODIS|VIIRS)$"),
    include_demo: bool = Query(False),
) -> list[DetectionOut]:
    settings = get_settings()
    limit = min(limit, settings.max_limit)
    sql = """
        SELECT d.detection_id, d.satellite, d.instrument, d.acquired_at, d.lat, d.lon,
               d.daynight, d.confidence_raw, d.confidence_norm, d.frp, d.is_demo
        FROM fire_detections d
        WHERE (CAST(:instrument AS text) IS NULL OR d.instrument = :instrument)
          AND (:include_demo OR d.is_demo = FALSE)
        ORDER BY d.acquired_at DESC, d.detection_id DESC
        LIMIT :limit OFFSET :offset
    """
    params: dict[str, object] = {
        "instrument": instrument,
        "include_demo": include_demo,
        "limit": limit,
        "offset": offset,
    }
    try:
        rows = db.fetch_all(sql, params)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc
    return [DetectionOut(**r) for r in rows]


@router.get("/detections/{detection_id}", response_model=DetectionOut)
def get_detection(detection_id: int) -> DetectionOut:
    row = db.fetch_one(
        """
        SELECT detection_id, satellite, instrument, acquired_at, lat, lon, daynight,
               confidence_raw, confidence_norm, frp, is_demo
        FROM fire_detections WHERE detection_id = :id
        """,
        {"id": detection_id},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Detecção não encontrada.")
    return DetectionOut(**row)
