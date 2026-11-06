/** Shell principal: sidebar fixa (recolhível) + barra superior + área principal. */
import { ScopeProvider } from "@/app/Scope";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  return (
    <ScopeProvider>
      <div className="flex h-screen w-full bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="min-h-0 flex-1 overflow-y-auto p-3 md:p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </ScopeProvider>
  );
}
