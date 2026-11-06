/** Componente de mapa MapLibre com três modos do PromptMaster:
 *  - "globe": globo 3D (projection: 'globe') + raster NASA GIBS Blue Marble;
 *  - "flat":  mapa plano escuro + focos MVT da nossa API;
 *  - "terrain": plano com relevo 3D (DEM `terrarium` aberto da AWS).
 * Nada de dados fakes: os pontos vêm do endpoint MVT /api/tiles/grid_points.
 */
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map as MlMap } from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

export type MapMode = "globe" | "flat" | "terrain";

const DEMO_MARK = "cornflower";
const GIBS_BLUEMARBLE: maplibregl.RasterSourceSpecification = {
  type: "raster",
  tiles: [
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/500m/{z}/{y}/{x}.jpeg",
  ],
  tileSize: 256,
  maxzoom: 8,
  attribution: "NASA GIBS Blue Marble (domínio público)",
};
const CARTO_DARK: maplibregl.RasterSourceSpecification = {
  type: "raster",
  tiles: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"],
  tileSize: 256,
  maxzoom: 20,
  attribution: "© OpenStreetMap © CARTO",
};
// DEM aberto (terrarium) — elevação; encoding tratado pelo MapLibre via hillshade/terrain custom.
const TERRARIUM_DEM: maplibregl.RasterDEMSourceSpecification = {
  type: "raster-dem",
  tiles: ["https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"],
  encoding: "terrarium",
  tileSize: 256,
  maxzoom: 13,
  attribution: "Mapzen/DEM (Alembic AWS open data)",
};

function styleForMode(mode: MapMode): maplibregl.StyleSpecification {
  const base: maplibregl.StyleSpecification = {
    version: 8,
    sources: {},
    layers: [],
    glyphs: undefined as unknown as string,
  };
  if (mode === "globe") {
    base.sources.gibs = GIBS_BLUEMARBLE;
    base.layers.push({ id: "gibs", type: "raster", source: "gibs" });
  } else {
    base.sources.carto = CARTO_DARK;
    base.layers.push({ id: "carto", type: "raster", source: "carto" });
  }
  return base;
}

export function FireMapView({ mode, regionBbox }: { mode: MapMode; regionBbox?: [number, number, number, number] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const center: [number, number] = regionBbox
      ? [(regionBbox[0] + regionBbox[2]) / 2, (regionBbox[1] + regionBbox[3]) / 2]
      : [-39.0, -4.9];
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleForMode(mode),
      center,
      zoom: mode === "globe" ? 2.2 : 7,
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    mapRef.current = map;
    map.on("load", () => {
      if (mode === "globe") {
        map.setProjection({ type: "globe" });
      }
      if (mode === "terrain") {
        map.setTerrain({ source: "terrain-dem", exaggeration: 1.2 });
        map.addSource("terrain-dem", TERRARIUM_DEM);
      }
      // Focos: MVT gerado por PostGIS (agregados por célula; nada cru demais por requis.)
      map.addSource("fires", {
        type: "vector",
        tiles: [`${location.origin}/api/tiles/grid_points/{z}/{x}/{y}.mvt`],
        minzoom: 0,
        maxzoom: 12,
        attribution: "NASA FIRMS (MODIS/VIIRS) — plataforma",
      });
      map.addLayer({
        id: "fires-heat",
        type: "circle",
        source: "fires",
        "source-layer": "grid_points",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["coalesce", ["get", "n"], 0],
            1, 4, 10, 10, 50, 18, 200, 26,
          ],
          "circle-color": [
            "case",
            [">", ["coalesce", ["get", "v"], 0], 0],
            ["case", ["==", ["coalesce", ["get", "m"], 0], 0], "#38bdf8", DEMO_MARK],
            "#f59e0b",
          ],
          "circle-opacity": 0.55,
          "circle-stroke-color": "#fff7ed",
          "circle-stroke-width": 0.6,
        },
      });
      if (regionBbox) {
        map.fitBounds(
          [[regionBbox[0], regionBbox[1]], [regionBbox[2], regionBbox[3]]],
          { padding: 40, duration: 0 },
        );
      }
      setReady(true);
    });
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  return (
    <div className="relative h-[70vh] min-h-[420px] w-full overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-800">
      <div ref={containerRef} className="h-full w-full" />
      {!ready && (
        <div className="absolute inset-0 grid place-items-center bg-neutral-100 text-sm dark:bg-neutral-900">
          Carregando mapa ({mode})…
        </div>
      )}
      <div className="pointer-events-none absolute bottom-2 left-2 rounded bg-black/60 px-2 py-1 text-[11px] text-white">
        Azul = só VIIRS · Lilás = VIIRS+MODIS · Âmbar = só MODIS · células MVT da grade (PostGIS)
      </div>
    </div>
  );
}
