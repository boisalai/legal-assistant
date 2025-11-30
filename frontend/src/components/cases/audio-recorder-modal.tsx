"use client";

import { useState, useRef, useEffect, useCallback } from "react";
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
import { Progress } from "@/components/ui/progress";
import {
  Mic,
  Square,
  Play,
  Pause,
  Trash2,
  Loader2,
  AlertCircle,
  HardDrive,
  RefreshCw,
} from "lucide-react";
import { documentsApi } from "@/lib/api";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { audioStorage, type RecordingSession } from "@/lib/audio-storage";

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

  // IndexedDB state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chunkIndex, setChunkIndex] = useState(0);
  const [savedSize, setSavedSize] = useState(0);
  const [lastSaveTime, setLastSaveTime] = useState<Date | null>(null);
  const [interruptedSessions, setInterruptedSessions] = useState<RecordingSession[]>([]);
  const [isRecovering, setIsRecovering] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const chunkIndexRef = useRef(0);

  // Check for interrupted sessions on mount
  useEffect(() => {
    if (open) {
      checkInterruptedSessions();
      audioStorage.cleanupOldSessions();
    }
  }, [open]);

  const checkInterruptedSessions = async () => {
    try {
      const sessions = await audioStorage.getInterruptedSessions();
      // Filter sessions for this case that have actual content
      const relevantSessions = sessions.filter(
        (s) => s.chunkCount > 0 && s.totalSize > 0
      );
      setInterruptedSessions(relevantSessions);
    } catch (err) {
      console.error("Error checking interrupted sessions:", err);
    }
  };

  useEffect(() => {
    return () => {
      // Cleanup
      if (timerRef.current) clearInterval(timerRef.current);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  // Handle page unload - mark session as interrupted
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isRecording && sessionId) {
        // Mark session as interrupted
        audioStorage.updateSessionStatus(sessionId, "interrupted");
        e.preventDefault();
        e.returnValue = "Un enregistrement est en cours. Voulez-vous vraiment quitter ?";
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isRecording, sessionId]);

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

      // Create session in IndexedDB
      const defaultName = `Enregistrement ${new Date().toLocaleDateString("fr-CA")}`;
      const newSessionId = await audioStorage.startSession(caseId, defaultName, mimeType);
      setSessionId(newSessionId);
      setChunkIndex(0);
      chunkIndexRef.current = 0;
      setSavedSize(0);

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      // Save chunks to IndexedDB every 5 seconds
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          try {
            const currentIndex = chunkIndexRef.current;
            chunkIndexRef.current += 1;
            await audioStorage.saveChunk(newSessionId, currentIndex, event.data);
            setChunkIndex(chunkIndexRef.current);
            setSavedSize((prev) => prev + event.data.size);
            setLastSaveTime(new Date());
          } catch (err) {
            console.error("Error saving chunk:", err);
          }
        }
      };

      mediaRecorder.onstop = async () => {
        // Assemble final recording from IndexedDB
        try {
          const blob = await audioStorage.assembleRecording(newSessionId);
          if (blob) {
            setAudioBlob(blob);
            const url = URL.createObjectURL(blob);
            setAudioUrl(url);
            await audioStorage.updateSessionStatus(newSessionId, "completed");
          }
        } catch (err) {
          console.error("Error assembling recording:", err);
          setError("Erreur lors de l'assemblage de l'enregistrement");
        }

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      // Request data every 5 seconds for incremental saving
      mediaRecorder.start(5000);
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

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (sessionId) {
        audioStorage.updateSessionStatus(sessionId, "paused");
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
      if (sessionId) {
        audioStorage.updateSessionStatus(sessionId, "recording");
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      // Request final data before stopping
      mediaRecorderRef.current.requestData();
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

  const deleteRecording = async () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    if (sessionId) {
      await audioStorage.deleteSession(sessionId);
    }
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    setIsPlaying(false);
    setFileName("");
    setSessionId(null);
    setChunkIndex(0);
    setSavedSize(0);
    setLastSaveTime(null);
  };

  const recoverSession = async (session: RecordingSession) => {
    setIsRecovering(true);
    setError(null);

    try {
      const blob = await audioStorage.assembleRecording(session.id);
      if (blob) {
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        setSessionId(session.id);
        setFileName(session.name);
        setRecordingTime(Math.floor(session.totalSize / 16000)); // Rough estimate
        setSavedSize(session.totalSize);
        await audioStorage.updateSessionStatus(session.id, "completed");
        setInterruptedSessions((prev) => prev.filter((s) => s.id !== session.id));
      }
    } catch (err) {
      console.error("Error recovering session:", err);
      setError("Erreur lors de la récupération de l'enregistrement");
    } finally {
      setIsRecovering(false);
    }
  };

  const discardInterruptedSession = async (session: RecordingSession) => {
    await audioStorage.deleteSession(session.id);
    setInterruptedSessions((prev) => prev.filter((s) => s.id !== session.id));
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

      // Clean up IndexedDB session
      if (sessionId) {
        await audioStorage.deleteSession(sessionId);
      }

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
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hrs > 0) {
      return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    }
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Enregistrer un audio</DialogTitle>
          <DialogDescription>
            Enregistrez une note vocale ou une réunion (jusqu&apos;à 3+ heures)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Recovery banner for interrupted sessions */}
          {interruptedSessions.length > 0 && !isRecording && !audioBlob && (
            <Alert>
              <RefreshCw className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p className="font-medium">Enregistrement(s) interrompu(s) détecté(s)</p>
                  {interruptedSessions.map((session) => (
                    <div
                      key={session.id}
                      className="flex items-center justify-between gap-2 p-2 bg-muted rounded"
                    >
                      <div className="text-sm">
                        <div className="font-medium">{session.name}</div>
                        <div className="text-muted-foreground">
                          {formatSize(session.totalSize)} -{" "}
                          {new Date(session.startedAt).toLocaleString("fr-CA")}
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => recoverSession(session)}
                          disabled={isRecovering}
                        >
                          {isRecovering ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            "Récupérer"
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => discardInterruptedSession(session)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Recording controls */}
          <div className="flex flex-col items-center gap-4 py-6">
            {/* Timer */}
            <div className="text-4xl font-mono tabular-nums">
              {formatTime(recordingTime)}
            </div>

            {/* Storage indicator during recording */}
            {isRecording && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <HardDrive className="h-4 w-4 text-green-500" />
                <span>Sauvegardé: {formatSize(savedSize)}</span>
                {lastSaveTime && (
                  <span className="text-xs">
                    (dernière: {lastSaveTime.toLocaleTimeString("fr-CA")})
                  </span>
                )}
              </div>
            )}

            {/* Record button */}
            {!audioBlob && !isRecording && (
              <Button
                onClick={startRecording}
                size="lg"
                className="rounded-full h-16 w-16"
              >
                <Mic className="h-6 w-6" />
              </Button>
            )}

            {/* Recording controls */}
            {isRecording && (
              <div className="flex items-center gap-2">
                {!isPaused ? (
                  <Button
                    onClick={pauseRecording}
                    size="lg"
                    variant="outline"
                    className="rounded-full h-12 w-12"
                  >
                    <Pause className="h-5 w-5" />
                  </Button>
                ) : (
                  <Button
                    onClick={resumeRecording}
                    size="lg"
                    variant="outline"
                    className="rounded-full h-12 w-12"
                  >
                    <Play className="h-5 w-5 ml-1" />
                  </Button>
                )}
                <Button
                  onClick={stopRecording}
                  size="lg"
                  variant="destructive"
                  className="rounded-full h-16 w-16"
                >
                  <Square className="h-6 w-6" />
                </Button>
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
                <div className="text-sm text-muted-foreground">
                  Taille: {formatSize(audioBlob.size)}
                </div>
              </>
            )}

            {isRecording && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-red-600 animate-pulse" />
                {isPaused ? "En pause" : "Enregistrement en cours..."}
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
                Le fichier sera sauvegardé avec l&apos;extension audio appropriée
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
