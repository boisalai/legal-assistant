"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Scale, FileText, BookOpen } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold flex items-center gap-2">
            <Scale className="h-5 w-5" />
            Legal Assistant
          </Link>
          <nav className="flex items-center gap-2">
            <Link href="/judgments">
              <Button variant="ghost" size="sm">
                Jugements
              </Button>
            </Link>
            <Link href="/judgments/new">
              <Button size="sm">
                Nouveau jugement
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-8 px-4">
          <div className="flex justify-center">
            <Scale className="h-16 w-16 text-primary" />
          </div>
          <h1 className="text-3xl font-semibold">
            Assistant Juridique
          </h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            Resume automatique de jugements pour etudiants en droit.
            Generez des case briefs structures en quelques clics.
          </p>

          <div className="grid gap-4 md:grid-cols-3 max-w-2xl mx-auto mt-8">
            <div className="p-6 border rounded-lg text-left">
              <FileText className="h-8 w-8 mb-3 text-primary" />
              <h3 className="font-medium mb-2">Upload de jugements</h3>
              <p className="text-sm text-muted-foreground">
                Telechargez vos jugements en PDF ou texte
              </p>
            </div>
            <div className="p-6 border rounded-lg text-left">
              <BookOpen className="h-8 w-8 mb-3 text-primary" />
              <h3 className="font-medium mb-2">Analyse IA</h3>
              <p className="text-sm text-muted-foreground">
                Extraction automatique des elements cles
              </p>
            </div>
            <div className="p-6 border rounded-lg text-left">
              <Scale className="h-8 w-8 mb-3 text-primary" />
              <h3 className="font-medium mb-2">Case Brief</h3>
              <p className="text-sm text-muted-foreground">
                Resume structure et organise
              </p>
            </div>
          </div>

          <div className="flex gap-3 justify-center pt-4">
            <Link href="/judgments/new">
              <Button size="lg">Analyser un jugement</Button>
            </Link>
            <Link href="/judgments">
              <Button variant="outline" size="lg">Voir mes jugements</Button>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-4">
        <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
          Legal Assistant - Assistant d'etudes juridiques
        </div>
      </footer>
    </div>
  );
}
