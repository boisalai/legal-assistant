"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold">
            Notary Assistant
          </Link>
          <nav className="flex items-center gap-2">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                Dashboard
              </Button>
            </Link>
            <Link href="/cases/new">
              <Button size="sm">
                Nouveau dossier
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-6 px-4">
          <h1 className="text-2xl font-semibold">
            Analyse de dossiers notariaux
          </h1>
          <p className="text-muted-foreground max-w-md">
            Automatisez les verifications preliminaires de vos dossiers
          </p>
          <div className="flex gap-3 justify-center">
            <Link href="/cases/new">
              <Button>Nouveau dossier</Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="outline">Voir les dossiers</Button>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-4">
        <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
          Notary Assistant
        </div>
      </footer>
    </div>
  );
}
