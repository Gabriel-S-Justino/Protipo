"""National scope. Official IBGE polygons, never a rectangle as a country mask."""

import json
import requests
from sqlalchemy import text
from pipeline.db import get_engine

BRAZIL_BBOX = (-74.0, -34.0, -28.0, 6.0)
IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3/malhas"


def boundaries():
    headers = {"Accept": "application/vnd.geo+json"}
    states_response = requests.get(
        "https://servicodados.ibge.gov.br/api/v1/localidades/estados", timeout=60
    )
    states_response.raise_for_status()
    places = [("BR", "Brasil", "country")] + [
        (str(s["id"]), s["nome"], "state") for s in states_response.json()
    ]
    # Download all resources before starting a transaction; failure preserves old polygons.
    shapes = []
    for code, name, level in places:
        kind = "paises" if level == "country" else "estados"
        response = requests.get(
            f"{IBGE_BASE}/{kind}/{code}",
            params={"formato": "application/vnd.geo+json", "qualidade": "maxima"},
            headers=headers,
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features", [])
        if not features:
            raise ValueError(f"Malha IBGE vazia: {code}")
        shapes.append((code, name, level, features))
    with get_engine().begin() as conn:
        for code, name, level, features in shapes:
            geometries = [json.dumps(f["geometry"]) for f in features]
            conn.execute(
                text("""
                INSERT INTO regions (level,name,geocode,is_demo,boundary_file,boundary_version)
                VALUES (:level,:name,:code,false,:url,'IBGE API v3')
                ON CONFLICT (level,name) DO UPDATE SET geocode=EXCLUDED.geocode,
                    boundary_file=EXCLUDED.boundary_file, boundary_version=EXCLUDED.boundary_version,
                    is_demo=false
            """),
                {
                    "level": level,
                    "name": name,
                    "code": code,
                    "url": f"{IBGE_BASE}/{'paises' if level=='country' else 'estados'}/{code}",
                },
            )
            conn.execute(
                text("""
                UPDATE regions SET geom=(
                    SELECT ST_Multi(ST_UnaryUnion(ST_Collect(ST_MakeValid(
                        ST_SetSRID(ST_GeomFromGeoJSON(g),4326))))) FROM jsonb_array_elements_text(
                        CAST(:shapes AS jsonb)) AS items(g)
                ) WHERE level=:level AND name=:name
            """),
                {"shapes": json.dumps(geometries), "level": level, "name": name},
            )
        conn.execute(text("""
            UPDATE regions SET bbox_w=ST_XMin(geom),bbox_s=ST_YMin(geom),
              bbox_e=ST_XMax(geom),bbox_n=ST_YMax(geom)
            WHERE geom IS NOT NULL AND is_demo=false
        """))
        conn.execute(text("""
            UPDATE regions SET parent_id=(SELECT id FROM regions WHERE level='country' AND geocode='BR')
            WHERE level='state' AND geom IS NOT NULL AND is_demo=false
        """))
    return {"status": "ok", "regions": len(shapes)}
