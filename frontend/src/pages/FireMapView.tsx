import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { HeatData } from "@/services/api";
import "maplibre-gl/dist/maplibre-gl.css";

maplibregl.setWorkerUrl(workerUrl);

export type MapMode = "globe" | "flat" | "terrain";
const EMPTY: HeatData = { type: "FeatureCollection", features: [] };
const COLORS: maplibregl.ExpressionSpecification = [
  "interpolate",
  ["linear"],
  ["heatmap-density"],
  0,
  "rgba(255,245,200,0)",
  0.15,
  "rgba(254,224,139,0.5)",
  0.4,
  "#fdae61",
  0.65,
  "#f46d43",
  0.85,
  "#d73027",
  1,
  "#7f0000",
];

export function FireMapView({
  mode,
  regionBbox,
  data = EMPTY,
  probability = false,
  selectedCell,
  onCellSelect,
}: {
  mode: MapMode;
  regionBbox: [number, number, number, number];
  data?: HeatData;
  probability?: boolean;
  selectedCell?: number;
  onCellSelect?: (id: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const latest = useRef(data);
  latest.current = data;
  const selectRef = useRef(onCellSelect);
  selectRef.current = onCellSelect;
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState("");
  const [west, south, east, north] = regionBbox;
  useEffect(() => {
    if (!container.current) return;
    setReady(false);
    setError("");
    setDetail("");
    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: container.current,
        center: [(west + east) / 2, (south + north) / 2],
        zoom: 2,
        pitch: mode === "terrain" ? 55 : 0,
        bearing: mode === "terrain" ? -15 : 0,
        maxPitch: mode === "flat" ? 0 : 85,
        dragRotate: mode !== "flat",
        style: {
          version: 8,
          projection: { type: mode === "globe" ? "globe" : "mercator" },
          sources: {
            base: {
              type: "raster",
              tiles: [
                mode === "globe"
                  ? "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg"
                  : "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
              ],
              tileSize: 256,
              maxzoom: mode === "globe" ? 8 : 19,
              attribution:
                mode === "globe"
                  ? "NASA GIBS Blue Marble"
                  : "© OpenStreetMap contributors",
            },
          },
          layers: [{ id: "base", type: "raster", source: "base" }],
        },
      });
    } catch {
      setError(
        "Não foi possível iniciar o mapa. Verifique o suporte a WebGL do navegador.",
      );
      return;
    }
    mapRef.current = map;
    map.addControl(
      new maplibregl.NavigationControl({ visualizePitch: true }),
      "top-right",
    );
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }));
    map.on("load", () => {
      try {
        if (mode === "terrain") {
          map.addSource("elevation", {
            type: "raster-dem",
            tiles: [
              "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png",
            ],
            encoding: "terrarium",
            tileSize: 256,
            maxzoom: 13,
            attribution: "Elevação © Mapzen/AWS Open Data",
          });
          map.setTerrain({ source: "elevation", exaggeration: 1.5 });
          map.addLayer({
            id: "hillshade",
            type: "hillshade",
            source: "elevation",
            paint: { "hillshade-exaggeration": 0.35 },
          });
        }
        map.addSource("fires", { type: "geojson", data: latest.current });
        map.addLayer({
          id: "fires-heat",
          type: "heatmap",
          source: "fires",
          paint: {
            "heatmap-weight": probability
              ? ["coalesce", ["get", "probability"], 0]
              : [
                  "interpolate",
                  ["linear"],
                  ["coalesce", ["get", "weight"], 0],
                  0,
                  0,
                  1,
                  0.15,
                  10,
                  0.4,
                  100,
                  0.8,
                  1000,
                  1,
                ],
            "heatmap-intensity": probability ? 2 : 2.5,
            "heatmap-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              1,
              9,
              4,
              20,
              8,
              45,
              12,
              90,
            ],
            "heatmap-opacity": 0.85,
            "heatmap-color": COLORS,
          },
        });
        if (mode === "globe" && east - west > 30) {
          map.jumpTo({ center: [-51, -14], zoom: 1.8, pitch: 0 });
        } else {
          map.fitBounds(
            [
              [west, south],
              [east, north],
            ],
            { padding: 50, duration: 0, pitch: mode === "terrain" ? 55 : 0 },
          );
        }
        setReady(true);
      } catch {
        setError("Falha ao carregar as camadas do mapa. Tente novamente.");
      }
    });
    map.on("error", (event) => {
      // Surface tile/DEM failures without replacing a working base map with a spinner.
      if (event.error) {
        console.warn("MapLibre layer error", event.error.message);
        setError(
          "Uma camada não pôde ser carregada. Verifique a conexão; o mapa pode estar incompleto.",
        );
      }
    });
    map.on("click", (event) => {
      const candidates = latest.current.features
        .map((f) => {
          const screen = map.project(
            f.geometry.coordinates as [number, number],
          );
          return {
            feature: f,
            distance: Math.hypot(
              screen.x - event.point.x,
              screen.y - event.point.y,
            ),
          };
        })
        .sort((a, b) => a.distance - b.distance);
      const hit = candidates[0];
      if (!hit || hit.distance > 45) {
        setDetail("");
        return;
      }
      const p = hit.feature.properties;
      const coordinates = hit.feature.geometry.coordinates;
      const place =
        p.state ??
        `${coordinates[1].toFixed(2)}°, ${coordinates[0].toFixed(2)}°`;
      setDetail(
        probability
          ? `${place}: ${((p.probability ?? 0) * 100).toFixed(0)}% de recorrência histórica · ${p.years_used} anos · IC 95% ${((p.ci_low ?? 0) * 100).toFixed(0)}–${((p.ci_high ?? 1) * 100).toFixed(0)}%.`
          : `${place}: ${(p.weight ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} unidades de atividade na escala VIIRS.`,
      );
      if (p.cell_id) selectRef.current?.(p.cell_id);
    });
    const resize = new ResizeObserver(() => map.resize());
    resize.observe(container.current);
    return () => {
      resize.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, [mode, west, south, east, north, probability]);
  useEffect(() => {
    if (ready)
      (
        mapRef.current?.getSource("fires") as
          maplibregl.GeoJSONSource | undefined
      )?.setData(data);
  }, [data, ready]);
  useEffect(() => {
    const feature = data.features.find(
      (f) => f.properties.cell_id === selectedCell,
    );
    if (feature && mapRef.current && ready)
      mapRef.current.easeTo({
        center: feature.geometry.coordinates as [number, number],
        zoom: 6,
        duration: 600,
      });
  }, [selectedCell, data, ready]);
  return (
    <div className="space-y-2">
      <div className="relative h-[62vh] min-h-[380px] overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
        <div
          ref={container}
          className="h-full w-full"
          aria-label={`Mapa ${mode} de atividade de calor`}
        />
        {!ready && !error && (
          <div
            role="status"
            className="absolute inset-0 grid place-items-center bg-neutral-100 dark:bg-neutral-900"
          >
            Carregando mapa…
          </div>
        )}
        {error && (
          <div
            role="alert"
            className="absolute left-3 right-14 top-3 rounded bg-amber-50 p-3 text-xs text-amber-950"
          >
            {error}
          </div>
        )}
        <div className="pointer-events-none absolute bottom-8 left-3 rounded bg-white/95 p-3 text-xs text-neutral-800 shadow">
          <span>
            {probability
              ? "Concentração de áreas com maior recorrência"
              : "Atividade harmonizada · intensidade relativa"}
          </span>
          <div className="my-1 h-2 rounded bg-gradient-to-r from-amber-100 via-orange-500 to-red-950" />
          <div className="flex justify-between">
            <span>Menor</span>
            <span>Maior</span>
          </div>
        </div>
      </div>
      {detail && (
        <p
          aria-live="polite"
          className="rounded bg-orange-50 p-3 text-sm text-orange-950"
        >
          {detail}
        </p>
      )}
      <p className="text-xs text-neutral-500">
        Áreas de análise de 0,5° (aproximadamente 50 km). O calor é suavizado
        para leitura; consulte o valor da área ao clicar. Não representa
        temperatura nem localização exata de um futuro foco.
      </p>
    </div>
  );
}
