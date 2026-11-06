/** Sidebar fixa à esquerda (recolhível) — os 10 modos de visualização (§11.2). */
import { useState } from "react";
import { NavLink } from "react-router-dom";

const ITEMS: { label: string; to: string; icon: string }[] = [
  { label: "Visão geral", to: "/", icon: "◧" },
  { label: "Globo 3D", to: "/globe", icon: "◍" },
  { label: "Mapa plano", to: "/map", icon: "▦" },
  { label: "Mapa 3D realista", to: "/map3d", icon: "▲" },
  { label: "Quando e onde", to: "/calendar", icon: "▦" },
  { label: "Séries históricas", to: "/series", icon: "∿" },
  { label: "Anomalias", to: "/anomalies", icon: "⚠" },
  { label: "Regiões", to: "/regions", icon: "☰" },
  { label: "Dados e qualidade", to: "/data-quality", icon: "✓" },
  { label: "Metodologia", to: "/methodology", icon: "i" },
];

export function Sidebar() {
  const [open, setOpen] = useState(() => window.innerWidth >= 1024);

  return (
    <nav
      aria-label="Visualizações"
      className={`flex shrink-0 flex-col gap-1 border-r border-neutral-200 bg-white p-3 transition-all dark:border-neutral-800 dark:bg-neutral-900 ${
        open ? "w-64" : "w-16"
      }`}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="mb-2 self-end rounded px-2 py-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
        aria-label={open ? "Recolher menu" : "Expandir menu"}
      >
        {open ? "«" : "»"}
      </button>

      <div className="mb-4 px-2 font-semibold">
        {open ? (
          <span className="block text-sm leading-4">
            Fire Intelligence
            <span className="block text-xs font-normal text-neutral-500">
              Brasil · escala VIIRS
            </span>
          </span>
        ) : (
          <span aria-hidden>🔥</span>
        )}
      </div>

      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded px-3 py-2 text-sm transition ${
              isActive
                ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900"
                : "text-neutral-700 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
            }`
          }
          title={item.label}
        >
          <span aria-hidden>{item.icon}</span>
          {open && <span className="truncate">{item.label}</span>}
        </NavLink>
      ))}
    </nav>
  );
}
