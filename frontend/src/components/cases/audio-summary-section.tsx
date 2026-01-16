"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
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
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  Loader2,
  Headphones,
  Play,
  FileText,
  Trash2,
  Clock,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import { audioSummaryApi } from "@/lib/api";
import type { AudioSummary, Document, Module } from "@/types";

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
    </>
  );
}
