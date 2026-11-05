import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { OverviewPage } from "@/pages/OverviewPage";
import { CalendarPage } from "@/pages/CalendarPage";
import { SeriesPage } from "@/pages/SeriesPage";
import { MethodologyPage } from "@/pages/MethodologyPage";
import { DataQualityPage } from "@/pages/DataQualityPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/series" element={<SeriesPage />} />
        <Route path="/data-quality" element={<DataQualityPage />} />
        <Route path="/methodology" element={<MethodologyPage />} />
        {/* Mapas (globo 3D, plano, 3D realista) chegam na fase de mapas —
            placeholder HONESTO, sem dados fictícios. */}
        <Route path="/globe" element={<PlaceholderPage title="Globo 3D" phase="Fase 6 — mapas (Cesium/MapLibre + GIBS)" />} />
        <Route path="/map" element={<PlaceholderPage title="Mapa plano" phase="Fase 6 — mapas (MapLibre + MVT)" />} />
        <Route path="/map3d" element={<PlaceholderPage title="Mapa 3D realista" phase="Fase 6 — mapas (Cesium World Terrain / DEM aberto)" />} />
        <Route path="/anomalies" element={<PlaceholderPage title="Anomalias" phase="Fase 5 — pipeline de anomalias" />} />
        <Route path="/regions" element={<PlaceholderPage title="Regiões" phase="Fase 5 — malha IBGE + regiões" />} />
      </Route>
    </Routes>
  );
}
