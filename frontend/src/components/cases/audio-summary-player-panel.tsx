"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  X,
  Volume2,
  Download,
  FileText,
  Headphones,
  Loader2,
} from "lucide-react";
import { Markdown } from "@/components/ui/markdown";
import { audioSummaryApi } from "@/lib/api";
import type { AudioSummary } from "@/types";

interface AudioSummaryPlayerPanelProps {
  summary: AudioSummary;
  onClose: () => void;
}

export function AudioSummaryPlayerPanel({
  summary,
  onClose,
}: AudioSummaryPlayerPanelProps) {
  const [scriptContent, setScriptContent] = useState<string | null>(null);
  const [loadingScript, setLoadingScript] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  // Initialize audio URL
  useEffect(() => {
    if (summary.status === "completed") {
      setAudioUrl(audioSummaryApi.getAudioUrl(summary.id));
    }
  }, [summary]);

  // Load script content if available
  useEffect(() => {
    const loadScript = async () => {
      if (!summary.script_path) return;

      setLoadingScript(true);
      try {
        const scriptUrl = audioSummaryApi.getScriptUrl(summary.id);
        const response = await fetch(scriptUrl);
        if (response.ok) {
          const content = await response.text();
          setScriptContent(content);
        }
      } catch (error) {
        console.error("Error loading script:", error);
      } finally {
        setLoadingScript(false);
      }
    };

    loadScript();
  }, [summary.id, summary.script_path]);

  const handleDownloadAudio = () => {
    if (!audioUrl) return;
    const link = document.createElement("a");
    link.href = audioUrl;
    link.download = `${summary.name.replace(/\s+/g, "_")}.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadScript = () => {
    const scriptUrl = audioSummaryApi.getScriptUrl(summary.id);
    const link = document.createElement("a");
    link.href = scriptUrl;
    link.download = `${summary.name.replace(/\s+/g, "_")}_script.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header - same style as document-preview-panel */}
      <div className="p-4 border-b bg-background flex items-center justify-between shrink-0 min-h-[65px]">
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <h2 className="text-xl font-bold truncate">{summary.name}</h2>
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            <Headphones className="h-4 w-4 flex-shrink-0" />
            <span className="text-muted-foreground">
              {summary.section_count} section{summary.section_count > 1 ? "s" : ""} • {summary.source_documents.length} document{summary.source_documents.length > 1 ? "s" : ""}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-4">
          {summary.script_path && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              onClick={handleDownloadScript}
              title="Télécharger le script"
            >
              <FileText className="h-4 w-4 mr-1" />
              <span className="text-xs">Script</span>
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2"
            onClick={handleDownloadAudio}
            title="Télécharger l'audio"
          >
            <Download className="h-4 w-4 mr-1" />
            <span className="text-xs">Audio</span>
          </Button>
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

      {/* Audio Player Bar - same style as TTS player in document-preview-panel */}
      {audioUrl && (
        <div className="px-4 py-3 border-b bg-muted/10">
          <div className="flex items-center gap-3">
            <Volume2 className="h-4 w-4 text-purple-500 flex-shrink-0" />
            <div className="flex-1">
              <audio
                controls
                autoPlay
                className="w-full h-8"
                src={audioUrl}
              >
                Votre navigateur ne supporte pas l&apos;élément audio.
              </audio>
            </div>
          </div>
        </div>
      )}

      {/* Content - Script markdown */}
      <div className="flex-1 overflow-auto">
        {loadingScript ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : scriptContent ? (
          <div className="p-4 prose prose-sm dark:prose-invert max-w-none">
            <Markdown content={scriptContent} />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
            <Headphones className="h-16 w-16 text-purple-500/30" />
            <div>
              <h4 className="font-medium">Résumé audio</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Écoutez le résumé audio de vos documents de cours.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
