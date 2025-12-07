"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileSearch,
  Play,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  FolderOpen,
  ArrowRight,
  RefreshCw,
  Zap,
} from "lucide-react";
import { casesApi, analysisApi } from "@/lib/api";
import type { Case } from "@/types";

// Status configuration - supports both legacy (French) and new (English) statuses
const statusConfig: Record<string, { label: string; color: string }> = {
  // Legacy French statuses
  nouveau: { label: "À résumer", color: "bg-blue-500" },
  en_analyse: { label: "En cours", color: "bg-yellow-500" },
  termine: { label: "Résumé", color: "bg-green-500" },
  en_erreur: { label: "En erreur", color: "bg-red-500" },
  archive: { label: "Archivé", color: "bg-gray-500" },
  // New English statuses for judgments
  pending: { label: "En attente", color: "bg-blue-500" },
  analyzing: { label: "En analyse", color: "bg-yellow-500" },
  summarized: { label: "Résumé", color: "bg-green-500" },
  error: { label: "En erreur", color: "bg-red-500" },
  archived: { label: "Archivé", color: "bg-gray-500" },
};

export default function AnalysisPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const fetchCases = useCallback(async () => {
    setLoading(true);
    try {
      const data = await casesApi.list();
      setCases(data);
    } catch (err) {
      setError("Impossible de charger les dossiers");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const startAnalysis = async (caseId: string) => {
    setAnalyzing(caseId);
    try {
      await analysisApi.start(caseId);
      // Refresh cases to get updated status
      await fetchCases();
    } catch (err) {
      console.error("Analysis failed", err);
    } finally {
      setAnalyzing(null);
    }
  };

  // Filter cases - use status field (statut is deprecated alias)
  const filteredCases = cases.filter((c) => {
    if (filter === "all") return true;
    if (filter === "pending") return c.status === "nouveau" || c.status === "pending";
    if (filter === "in_progress") return c.status === "en_analyse" || c.status === "analyzing";
    if (filter === "completed") return c.status && ["termine", "summarized", "archive", "archived"].includes(c.status);
    return true;
  });

  // Stats
  const stats = {
    total: cases.length,
    pending: cases.filter((c) => c.status === "nouveau" || c.status === "pending").length,
    inProgress: cases.filter((c) => c.status === "en_analyse" || c.status === "analyzing").length,
    completed: cases.filter((c) => c.status && ["termine", "summarized", "archive", "archived"].includes(c.status)).length,
  };

  const completionRate = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <FileSearch className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Analyse</h1>
              <p className="text-muted-foreground">
                Gérez l'analyse de vos dossiers notariaux
              </p>
            </div>
          </div>
          <Button variant="outline" onClick={fetchCases} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
        </div>

        {/* Stats Overview */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total</p>
                  <p className="text-2xl font-bold">{stats.total}</p>
                </div>
                <FolderOpen className="h-8 w-8 text-muted-foreground/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">À analyser</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.pending}</p>
                </div>
                <Clock className="h-8 w-8 text-blue-500/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">En cours</p>
                  <p className="text-2xl font-bold text-yellow-600">{stats.inProgress}</p>
                </div>
                <Loader2 className="h-8 w-8 text-yellow-500/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Analysés</p>
                  <p className="text-2xl font-bold text-green-600">{stats.completed}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-500/50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Progress Bar */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Progression globale</span>
              <span className="text-sm text-muted-foreground">{completionRate}%</span>
            </div>
            <Progress value={completionRate} className="h-2" />
          </CardContent>
        </Card>

        {/* Quick Actions */}
        {stats.pending > 0 && (
          <Card className="border-primary/50 bg-primary/5">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-primary" />
                  <div>
                    <p className="font-medium">
                      {stats.pending} dossier{stats.pending > 1 ? "s" : ""} en attente d'analyse
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Lancez l'analyse pour extraire les informations automatiquement
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Cases List */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Dossiers</CardTitle>
                <CardDescription>
                  Sélectionnez un dossier pour lancer ou voir son analyse
                </CardDescription>
              </div>
              <Select value={filter} onValueChange={setFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filtrer" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous ({stats.total})</SelectItem>
                  <SelectItem value="pending">À analyser ({stats.pending})</SelectItem>
                  <SelectItem value="in_progress">En cours ({stats.inProgress})</SelectItem>
                  <SelectItem value="completed">Analysés ({stats.completed})</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-32 text-destructive">
                <AlertCircle className="h-8 w-8 mb-2" />
                <p>{error}</p>
              </div>
            ) : filteredCases.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                <FolderOpen className="h-8 w-8 mb-2" />
                <p>Aucun dossier trouvé</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredCases.map((caseItem) => {
                  const status = (caseItem.status && statusConfig[caseItem.status]) || statusConfig.nouveau;
                  const urlId = caseItem.id.replace("dossier:", "").replace("judgment:", "");
                  const isAnalyzing = analyzing === caseItem.id;
                  const canAnalyze = caseItem.status === "nouveau" || caseItem.status === "pending";

                  return (
                    <div
                      key={caseItem.id}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${status.color}`} />
                        <div>
                          <Link
                            href={`/cases/${urlId}`}
                            className="font-medium hover:underline"
                          >
                            {caseItem.nom_dossier}
                          </Link>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>{caseItem.type_transaction}</span>
                            <span>•</span>
                            <Badge variant="outline" className="text-xs">
                              {status.label}
                            </Badge>
                            {caseItem.score_confiance !== null && caseItem.score_confiance !== undefined && (
                              <>
                                <span>•</span>
                                <span>{caseItem.score_confiance}%</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {canAnalyze && (
                          <Button
                            size="sm"
                            onClick={() => startAnalysis(caseItem.id)}
                            disabled={isAnalyzing}
                          >
                            {isAnalyzing ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                Analyse...
                              </>
                            ) : (
                              <>
                                <Play className="h-4 w-4 mr-1" />
                                Analyser
                              </>
                            )}
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/cases/${urlId}`}>
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
