"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Scale, ArrowLeft, FileText, BookOpen, Loader2, RefreshCw, Building2, Calendar, Users } from "lucide-react";
import type { Judgment, CaseBrief } from "@/types/judgment";
import { getJudgment, getCaseBrief, summarizeJudgment } from "@/lib/api";

export default function JudgmentDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [judgment, setJudgment] = useState<Judgment | null>(null);
  const [caseBrief, setCaseBrief] = useState<CaseBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [judgmentData, caseBriefData] = await Promise.all([
          getJudgment(id),
          getCaseBrief(id),
        ]);
        setJudgment(judgmentData);
        setCaseBrief(caseBriefData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur inconnue");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [id]);

  const handleResummarize = async () => {
    setSummarizing(true);
    try {
      const result = await summarizeJudgment(id);
      setCaseBrief(result.case_brief);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du resume");
    } finally {
      setSummarizing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !judgment) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <p className="text-destructive mb-4">{error || "Jugement non trouve"}</p>
        <Link href="/judgments">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour aux jugements
          </Button>
        </Link>
      </div>
    );
  }

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
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="mb-6">
          <Link href="/judgments" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-4">
            <ArrowLeft className="h-4 w-4" />
            Retour aux jugements
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-semibold">
                {judgment.title || "Jugement sans titre"}
              </h1>
              {judgment.citation && (
                <p className="text-muted-foreground">{judgment.citation}</p>
              )}
            </div>
            <Button variant="outline" onClick={handleResummarize} disabled={summarizing}>
              {summarizing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Regenerer le resume
            </Button>
          </div>
        </div>

        {/* Metadata */}
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          {judgment.tribunal && (
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 text-sm">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Tribunal</span>
                </div>
                <p className="font-medium mt-1">{judgment.tribunal}</p>
              </CardContent>
            </Card>
          )}
          {judgment.date && (
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Date</span>
                </div>
                <p className="font-medium mt-1">{judgment.date}</p>
              </CardContent>
            </Card>
          )}
          {(judgment.plaintiff || judgment.defendant) && (
            <Card className="md:col-span-2">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 text-sm">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Parties</span>
                </div>
                <p className="font-medium mt-1">
                  {judgment.plaintiff} c. {judgment.defendant}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        <Tabs defaultValue="brief" className="space-y-4">
          <TabsList>
            <TabsTrigger value="brief">
              <BookOpen className="h-4 w-4 mr-2" />
              Case Brief
            </TabsTrigger>
            <TabsTrigger value="original">
              <FileText className="h-4 w-4 mr-2" />
              Texte original
            </TabsTrigger>
          </TabsList>

          <TabsContent value="brief">
            {summarizing ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-muted-foreground" />
                  <p>Generation du resume en cours...</p>
                  <Progress value={50} className="max-w-xs mx-auto mt-4" />
                </CardContent>
              </Card>
            ) : caseBrief ? (
              <div className="grid gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Faits pertinents</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap">{caseBrief.facts}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Questions en litige</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc list-inside space-y-2">
                      {caseBrief.issues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Regles de droit applicables</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc list-inside space-y-2">
                      {caseBrief.rules.map((rule, i) => (
                        <li key={i}>{rule}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Ratio Decidendi</CardTitle>
                    <CardDescription>
                      Motif principal de la decision
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap">{caseBrief.ratio_decidendi}</p>
                  </CardContent>
                </Card>

                {caseBrief.obiter_dicta && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Obiter Dicta</CardTitle>
                      <CardDescription>
                        Remarques incidentes du tribunal
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="whitespace-pre-wrap">{caseBrief.obiter_dicta}</p>
                    </CardContent>
                  </Card>
                )}

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Conclusion / Dispositif</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap">{caseBrief.conclusion}</p>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-medium mb-2">Aucun resume disponible</h3>
                  <p className="text-muted-foreground mb-4">
                    Generez un case brief automatique pour ce jugement
                  </p>
                  <Button onClick={handleResummarize}>
                    <Scale className="h-4 w-4 mr-2" />
                    Generer le resume
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="original">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Texte original du jugement</CardTitle>
                <CardDescription>
                  {judgment.original_text.length} caracteres
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-muted p-4 rounded-lg max-h-[600px] overflow-y-auto">
                  <pre className="whitespace-pre-wrap font-mono text-sm">
                    {judgment.original_text}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
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
