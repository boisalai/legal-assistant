"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Youtube, Loader2, Download, Clock, User, AlertCircle, Layers } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { documentsApi } from "@/lib/api";
import type { Module } from "@/types";

interface YouTubeDownloadModalProps {
  open: boolean;
  onClose: () => void;
  caseId: string;
  onDownloadComplete: () => void;
  modules?: Module[];
}

interface VideoInfo {
  title: string;
  duration: number;
  uploader: string;
  thumbnail: string;
}

type ModalState = "input" | "loading-info" | "preview" | "downloading" | "success" | "error";

export function YouTubeDownloadModal({
  open,
  onClose,
  caseId,
  onDownloadComplete,
  modules = [],
}: YouTubeDownloadModalProps) {
  const [url, setUrl] = useState("");
  const [state, setState] = useState<ModalState>("input");
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadedTitle, setDownloadedTitle] = useState<string>("");
  const [autoTranscribe, setAutoTranscribe] = useState(true); // Enabled by default
  const [selectedModuleId, setSelectedModuleId] = useState<string | undefined>(undefined);

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    }
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  const isValidYouTubeUrl = (url: string): boolean => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[\w-]+/i;
    return regex.test(url);
  };

  const handleUrlChange = (value: string) => {
    setUrl(value);
    setError(null);
    // Reset state when URL changes
    if (state !== "input" && state !== "loading-info") {
      setState("input");
      setVideoInfo(null);
    }
  };

  const handleFetchInfo = async () => {
    if (!isValidYouTubeUrl(url)) {
      setError("Veuillez entrer une URL YouTube valide");
      return;
    }

    setState("loading-info");
    setError(null);

    try {
      const info = await documentsApi.getYouTubeInfo(caseId, url);
      setVideoInfo(info);
      setState("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la récupération des informations");
      setState("input");
    }
  };

  const handleDownload = async () => {
    setState("downloading");
    setError(null);

    try {
      const result = await documentsApi.downloadYouTube(caseId, url, autoTranscribe, selectedModuleId);

      if (result.success) {
        setDownloadedTitle(result.title || videoInfo?.title || "Audio");
        setState("success");
        // Auto-close and refresh after success
        setTimeout(() => {
          onDownloadComplete();
          handleClose();
        }, 1500);
      } else {
        setError(result.error || "Erreur de téléchargement");
        setState("error");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du téléchargement");
      setState("error");
    }
  };

  const handleClose = () => {
    setUrl("");
    setState("input");
    setVideoInfo(null);
    setError(null);
    setDownloadedTitle("");
    setAutoTranscribe(true); // Reset to default
    setSelectedModuleId(undefined);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && state === "input" && url) {
      handleFetchInfo();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Youtube className="h-5 w-5 text-red-600" />
            Importer depuis YouTube
          </DialogTitle>
          <DialogDescription>
            Collez l'URL d'une vidéo YouTube pour en extraire l'audio
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* URL Input */}
          <div className="space-y-2">
            <Label htmlFor="youtube-url">URL de la vidéo</Label>
            <div className="flex gap-2">
              <Input
                id="youtube-url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={url}
                onChange={(e) => handleUrlChange(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={state === "loading-info" || state === "downloading"}
              />
              {state === "input" && url && (
                <Button
                  variant="secondary"
                  onClick={handleFetchInfo}
                  disabled={!isValidYouTubeUrl(url)}
                >
                  Charger
                </Button>
              )}
            </div>
            {!isValidYouTubeUrl(url) && url && (
              <p className="text-xs text-muted-foreground">
                Formats acceptés: youtube.com/watch?v=, youtu.be/, youtube.com/shorts/
              </p>
            )}
          </div>

          {/* Loading Info */}
          {state === "loading-info" && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Chargement des informations...</span>
            </div>
          )}

          {/* Video Preview */}
          {state === "preview" && videoInfo && (
            <div className="border rounded-lg p-4 space-y-3">
              {videoInfo.thumbnail && (
                <div className="aspect-video rounded-md overflow-hidden bg-muted">
                  <img
                    src={videoInfo.thumbnail}
                    alt={videoInfo.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="space-y-1">
                <h3 className="font-medium text-sm line-clamp-2">{videoInfo.title}</h3>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {videoInfo.uploader}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDuration(videoInfo.duration)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Auto-transcribe option */}
          {state === "preview" && (
            <div className="flex items-center space-x-2 p-3 rounded-md border bg-muted/30">
              <Checkbox
                id="auto-transcribe"
                checked={autoTranscribe}
                onCheckedChange={(checked) => setAutoTranscribe(checked as boolean)}
              />
              <div className="grid gap-1.5 leading-none">
                <label
                  htmlFor="auto-transcribe"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Transcrire automatiquement
                </label>
                <p className="text-xs text-muted-foreground">
                  Lance la transcription Whisper après téléchargement
                </p>
              </div>
            </div>
          )}

          {/* Module selector */}
          {state === "preview" && modules.length > 0 && (
            <div className="space-y-2">
              <Label htmlFor="module-select" className="flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Assigner à un module (optionnel)
              </Label>
              <Select
                value={selectedModuleId || "none"}
                onValueChange={(value) => setSelectedModuleId(value === "none" ? undefined : value)}
              >
                <SelectTrigger id="module-select">
                  <SelectValue placeholder="Aucun module sélectionné" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucun module</SelectItem>
                  {modules.map((module) => (
                    <SelectItem key={module.id} value={module.id}>
                      {module.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Downloading */}
          {state === "downloading" && (
            <div className="flex flex-col items-center justify-center py-8 space-y-3">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <div className="text-center">
                <p className="font-medium">Téléchargement en cours...</p>
                <p className="text-sm text-muted-foreground">
                  {autoTranscribe
                    ? "Extraction de l'audio et lancement de la transcription Whisper"
                    : "Extraction de l'audio et conversion en MP3"}
                </p>
              </div>
            </div>
          )}

          {/* Success */}
          {state === "success" && (
            <div className="flex flex-col items-center justify-center py-8 space-y-3 text-green-600">
              <Download className="h-10 w-10" />
              <div className="text-center">
                <p className="font-medium">Téléchargement terminé</p>
                <p className="text-sm text-muted-foreground">
                  "{downloadedTitle}" a été ajouté au dossier
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 p-3 rounded-md bg-destructive/10 text-destructive">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <p className="text-sm">{error}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={state === "downloading"}
          >
            {state === "success" ? "Fermer" : "Annuler"}
          </Button>
          {state === "preview" && (
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Télécharger l'audio
            </Button>
          )}
          {state === "error" && (
            <Button onClick={handleFetchInfo} variant="secondary">
              Réessayer
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
