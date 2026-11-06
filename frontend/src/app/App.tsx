import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { OverviewPage } from "@/pages/OverviewPage";
const CalendarPage = lazy(() =>
  import("@/pages/CalendarPage").then((m) => ({ default: m.CalendarPage })),
);
import { SeriesPage } from "@/pages/SeriesPage";
import { MethodologyPage } from "@/pages/MethodologyPage";
import { DataQualityPage } from "@/pages/DataQualityPage";

// MapLibre/Recharts sÃ£o pesados: pÃ¡ginas de mapa carregam em chunk separado.
const MapPage = lazy(() =>
  import("@/pages/MapPage").then((m) => ({ default: m.MapPage })),
);
const RegionsPage = lazy(() =>
  import("@/pages/RegionsPage").then((m) => ({ default: m.RegionsPage })),
);
const AnomaliesPage = lazy(() =>
  import("@/pages/AnomaliesPage").then((m) => ({ default: m.AnomaliesPage })),
);

function Loading() {
  return <p className="text-sm text-neutral-500">Carregando mÃ³duloÃ¢â‚¬Â¦</p>;
}

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<OverviewPage />} />
        <Route
          path="/calendar"
          element={
            <Suspense fallback={<Loading />}>
              <CalendarPage />
            </Suspense>
          }
        />
        <Route path="/series" element={<SeriesPage />} />
        <Route path="/data-quality" element={<DataQualityPage />} />
        <Route path="/methodology" element={<MethodologyPage />} />
        <Route
          path="/globe"
          element={
            <Suspense fallback={<Loading />}>
              <MapPage initialMode="globe" />
            </Suspense>
          }
        />
        <Route
          path="/map"
          element={
            <Suspense fallback={<Loading />}>
              <MapPage initialMode="flat" />
            </Suspense>
          }
        />
        <Route
          path="/map3d"
          element={
            <Suspense fallback={<Loading />}>
              <MapPage initialMode="terrain" />
            </Suspense>
          }
        />
        <Route
          path="/anomalies"
          element={
            <Suspense fallback={<Loading />}>
              <AnomaliesPage />
            </Suspense>
          }
        />
        <Route
          path="/regions"
          element={
            <Suspense fallback={<Loading />}>
              <RegionsPage />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}
