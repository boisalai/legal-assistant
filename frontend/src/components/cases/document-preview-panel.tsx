"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, FileText, Music, Download, ExternalLink, Loader2, Volume2, Languages } from "lucide-react";
import { Markdown } from "@/components/ui/markdown";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Document } from "@/types";
import { useActivityTracker } from "@/lib/activity-tracker";

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
  const [generatingTTS, setGeneratingTTS] = useState(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null);
  const [ttsError, setTtsError] = useState<string | null>(null);

  const ext = document.nom_fichier?.split(".").pop()?.toLowerCase() || "";
  const isAudio = document.type_mime?.includes("audio") || document.type_fichier?.includes("audio") || ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"].includes(ext);
  const isPdf = document.type_mime?.includes("pdf") || document.type_fichier === "pdf" || ext === "pdf";
  const isMarkdown = document.type_mime?.includes("markdown") || document.type_fichier === "md" || ext === "md" || ext === "markdown";

  // Clean IDs for API calls
  const cleanCaseId = caseId.replace("judgment:", "");
  const cleanDocId = document.id.replace("document:", "");

  // Activity tracking
  const trackActivity = useActivityTracker(caseId);

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
          const baseUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/cases/${cleanCaseId}/documents/${cleanDocId}/download`;
          const url = `${baseUrl}?inline=true`;
          if (isPdf) {
            setPdfUrl(url);
          } else if (isAudio) {
            setAudioUrl(url);
          }
        } else if (isMarkdown) {
          // For markdown files: use texte_extrait (cleaned content) if available
          if (document.texte_extrait && document.texte_extrait.trim()) {
            setMarkdownContent(document.texte_extrait);
          } else {
            // Fallback to downloading the file if texte_extrait is not available
            const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/cases/${cleanCaseId}/documents/${cleanDocId}/download`;
            try {
              const response = await fetch(downloadUrl);
              if (response.ok) {
                const content = await response.text();
                if (content && content.trim()) {
                  setMarkdownContent(content);
                }
              }
            } catch (error) {
              console.error("Error downloading markdown file:", error);
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

    // Track document view
    trackActivity("view_document", {
      document_id: document.id,
      document_name: document.nom_fichier,
    });
  }, [document.id, isPdf, isAudio, isMarkdown, cleanCaseId, cleanDocId, document.texte_extrait, trackActivity, document.nom_fichier]);

  const handleOpenExternal = () => {
    if (document.file_path) {
      // For linked files, we can't directly open them in browser
      // But we can provide a download link
      const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/cases/${cleanCaseId}/documents/${cleanDocId}/download`;
      window.open(url, "_blank");
    }
  };

  const handleGenerateTTS = async (language: string, voice?: string) => {
    setGeneratingTTS(true);
    setTtsError(null);
    setTtsAudioUrl(null);

    // Track TTS generation
    trackActivity("generate_tts", {
      document_id: document.id,
      document_name: document.nom_fichier,
      language,
    });

    try {
      // Get voice from localStorage if not specified
      let selectedVoice = voice;
      if (!selectedVoice) {
        const savedVoice = language === "fr"
          ? localStorage.getItem("tts_voice_fr")
          : localStorage.getItem("tts_voice_en");
        selectedVoice = savedVoice || undefined;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/cases/${cleanCaseId}/documents/${cleanDocId}/tts`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            language,
            voice: selectedVoice,
            gender: "female", // Fallback if no voice specified
            rate: "+0%",
            volume: "+0%",
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Erreur lors de la génération TTS");
      }

      const data = await response.json();
      if (data.success && data.audio_url) {
        const fullUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${data.audio_url}`;
        setTtsAudioUrl(fullUrl);
      } else {
        throw new Error(data.error || "Erreur de génération TTS");
      }
    } catch (error) {
      console.error("TTS error:", error);
      setTtsError(error instanceof Error ? error.message : "Erreur inconnue");
    } finally {
      setGeneratingTTS(false);
    }
  };

  const handleClose = () => {
    // Track document close
    trackActivity("close_document", {
      document_id: document.id,
      document_name: document.nom_fichier,
    });
    onClose();
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
            <p className="text-xs text-muted-foreground truncate" title={document.file_path}>
              {document.file_path}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* TTS Button - Only show if document has extracted text */}
          {document.texte_extrait && !isAudio && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2"
                  disabled={generatingTTS}
                  title="Lire le document"
                >
                  {generatingTTS ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : (
                    <Volume2 className="h-4 w-4 mr-1" />
                  )}
                  <span className="text-xs">Lire</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Choisir la langue</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => handleGenerateTTS("fr")}>
                  <Languages className="h-4 w-4 mr-2" />
                  Français
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleGenerateTTS("en")}>
                  <Languages className="h-4 w-4 mr-2" />
                  English
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={handleClose}
            title="Fermer"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* TTS Audio Player */}
      {ttsAudioUrl && (
        <div className="px-4 py-3 border-b bg-muted/10">
          <div className="flex items-center gap-3">
            <Volume2 className="h-4 w-4 text-purple-500 flex-shrink-0" />
            <div className="flex-1">
              <audio
                controls
                autoPlay
                className="w-full h-8"
                src={ttsAudioUrl}
              >
                Votre navigateur ne supporte pas l&apos;élément audio.
              </audio>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => setTtsAudioUrl(null)}
              title="Fermer le lecteur"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

      {/* TTS Error */}
      {ttsError && (
        <div className="px-4 py-2 border-b bg-destructive/10 text-destructive text-sm">
          <div className="flex items-center justify-between">
            <span>{ttsError}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => setTtsError(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

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
