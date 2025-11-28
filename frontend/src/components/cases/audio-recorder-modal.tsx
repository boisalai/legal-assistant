"use client";

import { useState, useRef, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Mic,
  Square,
  Play,
  Pause,
  Trash2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { documentsApi } from "@/lib/api";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface AudioRecorderModalProps {
  open: boolean;
  onClose: () => void;
  caseId: string;
  onUploadComplete: () => void;
}

export function AudioRecorderModal({
  open,
  onClose,
  caseId,
  onUploadComplete,
}: AudioRecorderModalProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [fileName, setFileName] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      // Cleanup
      if (timerRef.current) clearInterval(timerRef.current);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/mp4",
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType,
        });
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      setError(
        "Impossible d'accéder au microphone. Vérifiez les permissions."
      );
      console.error("Error accessing microphone:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);

      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const togglePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const deleteRecording = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    setIsPlaying(false);
    setFileName("");
  };

  const uploadAudio = async () => {
    if (!audioBlob) return;

    setIsUploading(true);
    setError(null);

    try {
      // Create a File from Blob
      const fileExtension = audioBlob.type.includes("webm") ? "webm" : "mp4";
      const name = fileName.trim() || `enregistrement_${Date.now()}`;
      const file = new File([audioBlob], `${name}.${fileExtension}`, {
        type: audioBlob.type,
      });

      await documentsApi.upload(caseId, file);

      onUploadComplete();
      handleClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erreur lors de l'upload"
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    if (!isUploading && !isRecording) {
      deleteRecording();
      setError(null);
      onClose();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Enregistrer un audio</DialogTitle>
          <DialogDescription>
            Enregistrez une note vocale pour ce dossier
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Recording controls */}
          <div className="flex flex-col items-center gap-4 py-6">
            {/* Timer */}
            <div className="text-4xl font-mono tabular-nums">
              {formatTime(recordingTime)}
            </div>

            {/* Record button */}
            {!audioBlob && (
              <div className="flex items-center gap-2">
                {!isRecording ? (
                  <Button
                    onClick={startRecording}
                    size="lg"
                    className="rounded-full h-16 w-16"
                  >
                    <Mic className="h-6 w-6" />
                  </Button>
                ) : (
                  <Button
                    onClick={stopRecording}
                    size="lg"
                    variant="destructive"
                    className="rounded-full h-16 w-16"
                  >
                    <Square className="h-6 w-6" />
                  </Button>
                )}
              </div>
            )}

            {/* Playback controls */}
            {audioBlob && (
              <>
                <audio
                  ref={audioRef}
                  src={audioUrl || undefined}
                  onEnded={() => setIsPlaying(false)}
                />
                <div className="flex items-center gap-2">
                  <Button
                    onClick={togglePlayPause}
                    size="lg"
                    className="rounded-full h-12 w-12"
                  >
                    {isPlaying ? (
                      <Pause className="h-5 w-5" />
                    ) : (
                      <Play className="h-5 w-5 ml-1" />
                    )}
                  </Button>
                  <Button
                    onClick={deleteRecording}
                    size="lg"
                    variant="outline"
                    className="rounded-full h-12 w-12"
                  >
                    <Trash2 className="h-5 w-5" />
                  </Button>
                </div>
              </>
            )}

            {isRecording && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-red-600 animate-pulse" />
                Enregistrement en cours...
              </div>
            )}
          </div>

          {/* File name input */}
          {audioBlob && (
            <div className="space-y-2">
              <Label htmlFor="fileName">Nom du fichier (optionnel)</Label>
              <Input
                id="fileName"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                placeholder="enregistrement"
                disabled={isUploading}
              />
              <p className="text-xs text-muted-foreground">
                Le fichier sera sauvegardé avec l'extension audio appropriée
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isUploading || isRecording}
          >
            Annuler
          </Button>
          <Button
            onClick={uploadAudio}
            disabled={!audioBlob || isUploading}
          >
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Upload en cours...
              </>
            ) : (
              "Sauvegarder"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
