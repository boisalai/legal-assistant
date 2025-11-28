"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Scale, Plus, FileText, Calendar, Building2 } from "lucide-react";
import type { Judgment } from "@/types/judgment";
import { getJudgments } from "@/lib/api";

export default function JudgmentsPage() {
  const [judgments, setJudgments] = useState<Judgment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchJudgments() {
      try {
        const data = await getJudgments();
        setJudgments(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur inconnue");
      } finally {
        setLoading(false);
      }
    }
    fetchJudgments();
  }, []);

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
                <Plus className="h-4 w-4 mr-1" />
                Nouveau
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold">Mes jugements</h1>
            <p className="text-muted-foreground">
              Liste de tous vos jugements analyses
            </p>
          </div>
          <Link href="/judgments/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau jugement
            </Button>
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-12 text-muted-foreground">
            Chargement...
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-destructive mb-4">{error}</p>
            <p className="text-sm text-muted-foreground">
              Assurez-vous que le backend est demarre sur le port 8000
            </p>
          </div>
        ) : judgments.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-medium mb-2">Aucun jugement</h3>
              <p className="text-muted-foreground mb-4">
                Commencez par ajouter votre premier jugement a analyser
              </p>
              <Link href="/judgments/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Ajouter un jugement
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {judgments.map((judgment) => (
              <Link key={judgment.id} href={`/judgments/${judgment.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardHeader>
                    <CardTitle className="text-lg line-clamp-2">
                      {judgment.title || "Jugement sans titre"}
                    </CardTitle>
                    {judgment.citation && (
                      <CardDescription>{judgment.citation}</CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {judgment.tribunal && (
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4" />
                          {judgment.tribunal}
                        </div>
                      )}
                      {judgment.date && (
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4" />
                          {judgment.date}
                        </div>
                      )}
                      {judgment.domain && (
                        <div className="inline-block px-2 py-1 bg-secondary rounded text-xs">
                          {judgment.domain}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
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
