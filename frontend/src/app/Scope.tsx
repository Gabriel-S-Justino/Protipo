import { createContext, useContext, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Region } from "@/services/api";
export const BRAZIL_BBOX: [number, number, number, number] = [-74, -34, -28, 6];
type Scope = {
  regionId: number | undefined;
  setRegionId: (id: number | undefined) => void;
  regions: Region[];
  name: string;
  bbox: [number, number, number, number];
  error: Error | null;
};
const Context = createContext<Scope | null>(null);
export function ScopeProvider({ children }: { children: ReactNode }) {
  const [regionId, setRegionId] = useState<number>();
  const q = useQuery({ queryKey: ["regions"], queryFn: () => api.regions() });
  const selected = q.data?.find((r) => r.id === regionId);
  const bbox: [number, number, number, number] = selected
    ? [selected.bbox_w, selected.bbox_s, selected.bbox_e, selected.bbox_n]
    : BRAZIL_BBOX;
  return (
    <Context.Provider
      value={{
        regionId,
        setRegionId,
        regions: q.data ?? [],
        name: selected?.name ?? "Brasil",
        bbox,
        error: q.error,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useScope() {
  const value = useContext(Context);
  if (!value) throw new Error("ScopeProvider ausente");
  return value;
}
