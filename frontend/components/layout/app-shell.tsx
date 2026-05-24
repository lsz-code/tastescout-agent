import { ReactNode } from "react";
import { AppSidebar } from "@/components/layout/app-sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(255,237,213,0.95),transparent_34%),linear-gradient(135deg,#fff8f0_0%,#fffdfa_48%,#fff2e0_100%)] p-3 md:p-4">
      <div className="flex min-h-[calc(100vh-1.5rem)] gap-4 md:min-h-[calc(100vh-2rem)]">
        <AppSidebar />
        <main className="min-w-0 flex-1">
          <div className="mx-auto h-full max-w-[1580px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
