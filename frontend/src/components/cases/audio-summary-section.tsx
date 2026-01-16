"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Plus,
  Loader2,
  Headphones,
  Play,
  FileText,
  Trash2,
  Clock,
  AlertCircle,
  Volume2,
  CheckCircle2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { audioSummaryApi } from "@/lib/api";
import type { AudioSummary, AudioGenerationProgress, Document, Module } from "@/types";

interface AudioSummarySectionProps {
  courseId: string;
  documents: Document[];
  modules: Module[];
  onCreateSummary: () => void;
  onPlayAudio?: (summary: AudioSummary) => void;
  refreshKey?: number;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function getStatusBadge(status: AudioSummary["status"]) {
  switch (status) {
    case "pending":
      return <Badge variant="secondary">En attente</Badge>;
    case "script_ready":
      return <Badge variant="outline">Script prêt</Badge>;
    case "generating":
      return <Badge variant="default">Génération...</Badge>;
    case "completed":
      return <Badge variant="default" className="bg-green-600">Terminé</Badge>;
    case "error":
      return <Badge variant="destructive">Erreur</Badge>;
    default:
      return null;
  }
}

export function AudioSummarySection({
  courseId,
  documents,
  modules,
  onCreateSummary,
  onPlayAudio,
  refreshKey,
}: AudioSummarySectionProps) {
  const [summaries, setSummaries] = useState<AudioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingSummaryId, setDeletingSummaryId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [summaryToDelete, setSummaryToDelete] = useState<AudioSummary | null>(null);

  // Audio generation state
  const [generatingAudioId, setGeneratingAudioId] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState<AudioGenerationProgress | null>(null);
  const [generationDialogOpen, setGenerationDialogOpen] = useState(false);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Script import state
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [summaryToImport, setSummaryToImport] = useState<AudioSummary | null>(null);
  const [importScriptContent, setImportScriptContent] = useState("");
  const [isImporting, setIsImporting] = useState(false);

  // Fetch summaries on mount and when refreshKey changes
  useEffect(() => {
    const fetchSummaries = async () => {
      try {
        const fetchedSummaries = await audioSummaryApi.list(courseId);
        setSummaries(fetchedSummaries);
      } catch (error) {
        console.error("Error fetching audio summaries:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchSummaries();
  }, [courseId, refreshKey]);

  const handleDeleteSummary = async () => {
    if (!summaryToDelete) return;

    setDeletingSummaryId(summaryToDelete.id);
    try {
      await audioSummaryApi.delete(summaryToDelete.id);
      setSummaries((prev) => prev.filter((s) => s.id !== summaryToDelete.id));
      toast.success("Résumé audio supprimé");
    } catch (error) {
      toast.error("Erreur lors de la suppression");
    } finally {
      setDeletingSummaryId(null);
      setSummaryToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handlePlayAudio = (summary: AudioSummary) => {
    if (summary.status !== "completed") {
      toast.error("L'audio n'est pas encore généré");
      return;
    }

    if (onPlayAudio) {
      onPlayAudio(summary);
    } else {
      // Fallback: play audio directly
      const audioUrl = audioSummaryApi.getAudioUrl(summary.id);
      const audio = new Audio(audioUrl);
      audio.play().catch(() => {
        toast.error("Erreur lors de la lecture audio");
      });
    }
  };

  const handleDownloadScript = (summary: AudioSummary) => {
    if (!summary.script_path) {
      toast.error("Script non disponible");
      return;
    }

    const scriptUrl = audioSummaryApi.getScriptUrl(summary.id);
    window.open(scriptUrl, "_blank");
  };

  const handleDeleteClick = (summary: AudioSummary) => {
    setSummaryToDelete(summary);
    setDeleteDialogOpen(true);
  };

  const handleGenerateAudio = async (summary: AudioSummary) => {
    if (summary.status !== "script_ready") {
      toast.error("Le script doit d'abord être généré");
      return;
    }

    setGeneratingAudioId(summary.id);
    setGenerationProgress(null);
    setGenerationComplete(false);
    setGenerationError(null);
    setGenerationDialogOpen(true);

    try {
      const result = await audioSummaryApi.generateAudioOnly(summary.id, {
        onProgress: (progress) => {
          setGenerationProgress(progress);
        },
      });

      if (result.success) {
        setGenerationComplete(true);
        const durationText = result.actual_duration_seconds
          ? formatDuration(result.actual_duration_seconds)
          : `${result.section_count} sections`;
        toast.success(`Audio généré: ${durationText}`);

        // Refresh the list after a short delay
        setTimeout(() => {
          setGenerationDialogOpen(false);
          // Trigger a refresh
          const fetchSummaries = async () => {
            try {
              const fetchedSummaries = await audioSummaryApi.list(courseId);
              setSummaries(fetchedSummaries);
            } catch (error) {
              console.error("Error fetching audio summaries:", error);
            }
          };
          fetchSummaries();
        }, 1500);
      } else {
        setGenerationError(result.error || "Erreur lors de la génération audio");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erreur inconnue";
      setGenerationError(message);
      toast.error(message);
    } finally {
      setGeneratingAudioId(null);
    }
  };

  const handleImportClick = (summary: AudioSummary) => {
    setSummaryToImport(summary);
    setImportScriptContent("");
    setImportDialogOpen(true);
  };

  const handleImportScript = async () => {
    if (!summaryToImport || !importScriptContent.trim()) return;

    setIsImporting(true);
    try {
      const result = await audioSummaryApi.importScript(
        summaryToImport.id,
        importScriptContent.trim()
      );

      if (result.success) {
        toast.success(`Script importé: ${result.section_count} sections`);
        setImportDialogOpen(false);

        // Refresh the list
        const fetchedSummaries = await audioSummaryApi.list(courseId);
        setSummaries(fetchedSummaries);
      } else {
        toast.error(result.error || "Erreur lors de l'import");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erreur inconnue";
      toast.error(message);
    } finally {
      setIsImporting(false);
    }
  };

  // Check if we have markdown documents for audio summary generation
  const markdownDocs = documents.filter(
    (doc) =>
      doc.filename?.endsWith(".md") ||
      doc.filename?.endsWith(".markdown") ||
      doc.filename?.endsWith(".txt")
  );
  const hasMarkdownDocs = markdownDocs.length > 0;

  if (loading) {
    return (
      <div className="space-y-2">
        <h3 className="font-semibold text-base flex items-center gap-2">
          <Headphones className="h-4 w-4" />
          Résumés Audio
        </h3>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Don't show section if no markdown docs and no existing summaries
  if (!hasMarkdownDocs && summaries.length === 0) {
    return null;
  }

  return (
    <>
      <div className="space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base flex items-center gap-2">
            <Headphones className="h-4 w-4" />
            Résumés Audio ({summaries.length})
          </h3>
          <Button
            size="sm"
            onClick={onCreateSummary}
            disabled={!hasMarkdownDocs}
            className="gap-1"
          >
            <Plus className="h-3 w-3" />
            Nouveau résumé
          </Button>
        </div>

        {/* Summary list */}
        {summaries.length === 0 ? (
          <div className="text-sm text-muted-foreground py-4 text-center border rounded-lg">
            Aucun résumé audio. Créez-en un à partir de vos documents markdown.
          </div>
        ) : (
          <div className="space-y-2">
            {summaries.map((summary) => (
              <div
                key={summary.id}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">
                      {summary.name}
                    </span>
                    {getStatusBadge(summary.status)}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span>{summary.source_documents.length} document(s)</span>
                    <span>{summary.section_count} section(s)</span>
                    {summary.actual_duration_seconds ? (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDuration(summary.actual_duration_seconds)}
                      </span>
                    ) : summary.estimated_duration_seconds > 0 ? (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        ~{formatDuration(summary.estimated_duration_seconds)}
                      </span>
                    ) : null}
                  </div>
                  {summary.error_message && (
                    <div className="flex items-center gap-1 mt-1 text-xs text-destructive">
                      <AlertCircle className="h-3 w-3" />
                      {summary.error_message}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1">
                  {/* Import script button (for pending status) */}
                  {summary.status === "pending" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleImportClick(summary)}
                      title="Importer un script existant"
                      className="gap-1"
                    >
                      <Upload className="h-3 w-3" />
                      <span className="text-xs">Script</span>
                    </Button>
                  )}

                  {/* Generate audio button (for script_ready status) */}
                  {summary.status === "script_ready" && (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => handleGenerateAudio(summary)}
                      disabled={generatingAudioId === summary.id}
                      title="Générer l'audio"
                      className="gap-1"
                    >
                      {generatingAudioId === summary.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Volume2 className="h-3 w-3" />
                      )}
                      <span className="text-xs">Audio</span>
                    </Button>
                  )}

                  {/* Play button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handlePlayAudio(summary)}
                    disabled={summary.status !== "completed"}
                    title="Écouter"
                  >
                    <Play className="h-4 w-4" />
                  </Button>

                  {/* Download script button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDownloadScript(summary)}
                    disabled={!summary.script_path}
                    title="Télécharger le script"
                  >
                    <FileText className="h-4 w-4" />
                  </Button>

                  {/* Delete button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteClick(summary)}
                    disabled={deletingSummaryId === summary.id}
                    title="Supprimer"
                  >
                    {deletingSummaryId === summary.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer le résumé audio ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette action supprimera définitivement le résumé audio &quot;{summaryToDelete?.name}&quot;
              ainsi que les fichiers script et audio associés.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteSummary}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Audio generation progress dialog */}
      <Dialog open={generationDialogOpen} onOpenChange={(open) => {
        // Only allow closing if generation is complete or has error
        if (!open && (generationComplete || generationError)) {
          setGenerationDialogOpen(false);
        }
      }}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Volume2 className="h-5 w-5" />
              Génération audio
            </DialogTitle>
            <DialogDescription>
              Conversion du script en fichier audio MP3
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {!generationComplete && !generationError && (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
                <div className="text-center">
                  <p className="font-medium">{generationProgress?.message || "Génération en cours..."}</p>
                  {generationProgress?.current_section && generationProgress?.total_sections && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Section {generationProgress.current_section} / {generationProgress.total_sections}
                    </p>
                  )}
                </div>
                {generationProgress?.percentage !== undefined && (
                  <Progress value={generationProgress.percentage} className="h-2" />
                )}
              </div>
            )}

            {generationComplete && (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <CheckCircle2 className="h-12 w-12 text-green-500" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-green-600">Audio généré avec succès</p>
                  {generationProgress?.actual_duration_seconds && (
                    <p className="text-sm text-muted-foreground mt-1 flex items-center justify-center gap-1">
                      <Clock className="h-4 w-4" />
                      Durée: {formatDuration(generationProgress.actual_duration_seconds)}
                    </p>
                  )}
                </div>
              </div>
            )}

            {generationError && (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <AlertCircle className="h-12 w-12 text-destructive" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-destructive">Erreur lors de la génération</p>
                  <p className="text-sm text-muted-foreground mt-1">{generationError}</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setGenerationDialogOpen(false)}
                  className="w-full"
                >
                  Fermer
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Import script dialog */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="sm:max-w-[450px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Importer un script existant
            </DialogTitle>
            <DialogDescription>
              Sélectionnez un fichier markdown pour &quot;{summaryToImport?.name}&quot;.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="script-file">Fichier script (.md)</Label>
              <input
                id="script-file"
                type="file"
                accept=".md,.markdown,.txt"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    const content = await file.text();
                    setImportScriptContent(content);
                  }
                }}
                className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary file:text-primary-foreground hover:file:bg-primary/90 cursor-pointer"
              />
              {importScriptContent && (
                <p className="text-xs text-green-600">
                  ✓ Fichier chargé ({importScriptContent.length} caractères)
                </p>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              Annuler
            </Button>
            <Button
              onClick={handleImportScript}
              disabled={!importScriptContent.trim() || isImporting}
            >
              {isImporting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Import...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Importer et générer audio
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
