"use client";

import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "./app-sidebar";
import { ModelSelector } from "./model-selector";
import { LanguageSelector } from "@/components/ui/language-selector";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
  noPadding?: boolean;
}

export function AppShell({ children, noPadding = false }: AppShellProps) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="h-screen max-h-screen overflow-hidden">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <div className="flex-1 max-w-sm">
            <ModelSelector variant="header" />
          </div>
          <div className="ml-auto">
            <LanguageSelector />
          </div>
        </header>
        <main className={cn("flex-1 min-h-0 overflow-auto", !noPadding && "p-6")}>
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
