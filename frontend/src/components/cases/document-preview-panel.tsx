"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, FileText, Music, Download, ExternalLink, Loader2 } from "lucide-react";
import { Markdown } from "@/components/ui/markdown";
import type { Document } from "@/types";

interface DocumentPreviewPanelProps {
  document: Document;
  caseId: string;
  onClose: () => void;
}

export function DocumentPreviewPanel({
  document,
  caseId,
  onClose,
}: DocumentPreviewPanelProps) {
  const [loading, setLoading] = useState(true);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [markdownContent, setMarkdownContent] = useState<string | null>(null);

  const ext = document.nom_fichier?.split(".").pop()?.toLowerCase() || "";
  const isAudio = document.type_mime?.includes("audio") || document.type_fichier?.includes("audio") || ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"].includes(ext);
  const isPdf = document.type_mime?.includes("pdf") || document.type_fichier === "pdf" || ext === "pdf";
  const isMarkdown = document.type_mime?.includes("markdown") || document.type_fichier === "md" || ext === "md" || ext === "markdown";

  // Clean IDs for API calls
  const cleanCaseId = caseId.replace("judgment:", "");
  const cleanDocId = document.id.replace("document:", "");

  useEffect(() => {
    const loadDocument = async () => {
      setLoading(true);
      // Reset state
      setPdfUrl(null);
      setAudioUrl(null);
      setMarkdownContent(null);

      try {
        if (isPdf || isAudio) {
          // Build the download URL with inline=true for browser display
          const baseUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/judgments/${cleanCaseId}/documents/${cleanDocId}/download`;
          const url = `${baseUrl}?inline=true`;
          if (isPdf) {
            setPdfUrl(url);
          } else if (isAudio) {
            setAudioUrl(url);
          }
        } else if (isMarkdown) {
          // For markdown files: always fetch the file content first, fallback to texte_extrait
          const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/judgments/${cleanCaseId}/documents/${cleanDocId}/download`;
          try {
            const response = await fetch(downloadUrl);
            if (response.ok) {
              const content = await response.text();
              if (content && content.trim()) {
                setMarkdownContent(content);
              } else if (document.texte_extrait) {
                setMarkdownContent(document.texte_extrait);
              }
            } else if (document.texte_extrait) {
              // Fallback to texte_extrait if download fails
              setMarkdownContent(document.texte_extrait);
            }
          } catch {
            // Fallback to texte_extrait on network error
            if (document.texte_extrait) {
              setMarkdownContent(document.texte_extrait);
            }
          }
        }
      } catch (error) {
        console.error("Error loading document:", error);
      } finally {
        setLoading(false);
      }
    };

    loadDocument();
  }, [document.id, isPdf, isAudio, isMarkdown, cleanCaseId, cleanDocId, document.texte_extrait]);

  const handleOpenExternal = () => {
    if (document.file_path) {
      // For linked files, we can't directly open them in browser
      // But we can provide a download link
      const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/judgments/${cleanCaseId}/documents/${cleanDocId}/download`;
      window.open(url, "_blank");
    }
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0">
          {isAudio ? (
            <Music className="h-5 w-5 text-purple-500 flex-shrink-0" />
          ) : (
            <FileText className="h-5 w-5 text-blue-500 flex-shrink-0" />
          )}
          <div className="min-w-0">
            <h3 className="font-semibold text-sm truncate">{document.nom_fichier}</h3>
            <p className="text-xs text-muted-foreground">Visualisation</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={onClose}
            title="Fermer"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* PDF Viewer */}
            {isPdf && pdfUrl && (
              <iframe
                src={pdfUrl}
                className="w-full h-full border-0"
                title={document.nom_fichier}
              />
            )}

            {/* Markdown Viewer */}
            {isMarkdown && markdownContent && (
              <div className="p-4 prose prose-sm dark:prose-invert max-w-none">
                <Markdown content={markdownContent} />
              </div>
            )}

            {/* Audio Player */}
            {isAudio && audioUrl && (
              <div className="flex flex-col items-center justify-center h-full gap-6 p-8">
                <Music className="h-24 w-24 text-purple-500/50" />
                <div className="text-center">
                  <h4 className="font-medium text-lg">{document.nom_fichier}</h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    {document.taille ? `${(document.taille / 1024).toFixed(1)} KB` : ""}
                  </p>
                </div>
                <audio
                  controls
                  className="w-full max-w-md"
                  src={audioUrl}
                >
                  Votre navigateur ne supporte pas l&apos;élément audio.
                </audio>

                {/* Show transcription if available */}
                {document.texte_extrait && (
                  <div className="w-full max-w-2xl mt-4">
                    <h5 className="font-medium text-sm mb-2">Transcription</h5>
                    <div className="p-4 bg-muted rounded-lg text-sm max-h-64 overflow-y-auto">
                      {document.texte_extrait}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Text/Other file with extracted content */}
            {!isPdf && !isMarkdown && !isAudio && document.texte_extrait && (
              <div className="p-4">
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg">
                    {document.texte_extrait}
                  </pre>
                </div>
              </div>
            )}

            {/* No content available */}
            {!isPdf && !isAudio && !markdownContent && !document.texte_extrait && (
              <div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
                <FileText className="h-16 w-16 text-muted-foreground/50" />
                <div>
                  <h4 className="font-medium">Aperçu non disponible</h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    Ce type de fichier ne peut pas être prévisualisé directement.
                  </p>
                </div>
                <Button onClick={handleOpenExternal} variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Télécharger le fichier
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
