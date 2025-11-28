"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mic, Square, Pause, Play, Trash2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob, name: string, language: string, identifySpeakers: boolean) => void;
  disabled?: boolean;
  className?: string;
}

type RecordingState = "idle" | "recording" | "paused" | "stopped";

export function AudioRecorder({
  onRecordingComplete,
  disabled = false,
  className,
}: AudioRecorderProps) {
  const [state, setState] = useState<RecordingState>("idle");
  const [recordingName, setRecordingName] = useState(() => {
    const now = new Date();
    return `Enregistrement ${now.toLocaleDateString("fr-CA")} - ${now.toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" })}`;
  });
  const [language, setLanguage] = useState("fr");
  const [identifySpeakers, setIdentifySpeakers] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const startTimer = useCallback(() => {
    timerRef.current = setInterval(() => {
      setDuration((d) => d + 1);
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    setAudioLevel(average / 255);

    if (state === "recording") {
      animationRef.current = requestAnimationFrame(updateAudioLevel);
    }
  }, [state]);

  const startRecording = async () => {
    try {
      setError(null);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Set up audio analyser for visualization
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms

      setState("recording");
      setDuration(0);
      startTimer();
      updateAudioLevel();
    } catch (err) {
      console.error("Error starting recording:", err);
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setError("Accès au microphone refusé. Veuillez autoriser l'accès dans les paramètres de votre navigateur.");
      } else {
        setError("Impossible d'accéder au microphone. Vérifiez les permissions du navigateur.");
      }
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && state === "recording") {
      mediaRecorderRef.current.pause();
      setState("paused");
      stopTimer();
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && state === "paused") {
      mediaRecorderRef.current.resume();
      setState("recording");
      startTimer();
      updateAudioLevel();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setState("stopped");
      stopTimer();
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      setAudioLevel(0);
    }
  };

  const resetRecording = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    setState("idle");
    setDuration(0);
    audioChunksRef.current = [];

    // Reset name with current time
    const now = new Date();
    setRecordingName(
      `Enregistrement ${now.toLocaleDateString("fr-CA")} - ${now.toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" })}`
    );
  };

  const saveRecording = () => {
    if (audioChunksRef.current.length === 0) return;

    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    onRecordingComplete(audioBlob, recordingName, language, identifySpeakers);
    resetRecording();
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Warning */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          L&apos;enregistrement en direct n&apos;est pas compatible avec les appels vidéo (Zoom, Google Meet, etc.).
          Pour enregistrer un appel, utilisez l&apos;onglet &quot;Téléverser des fichiers&quot;.
        </AlertDescription>
      </Alert>

      {/* Error message */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Pre-recording form */}
      {(state === "idle" || state === "stopped") && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="recording-name">Nom de l&apos;enregistrement</Label>
            <Input
              id="recording-name"
              value={recordingName}
              onChange={(e) => setRecordingName(e.target.value)}
              placeholder="Ex: Rencontre initiale - Famille Tremblay"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="language">Langue de l&apos;audio</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger id="language">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fr">Français</SelectItem>
                <SelectItem value="en">Anglais</SelectItem>
                <SelectItem value="fr-en">Bilingue (français/anglais)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="identify-speakers"
              checked={identifySpeakers}
              onCheckedChange={(checked) => setIdentifySpeakers(checked === true)}
            />
            <Label htmlFor="identify-speakers" className="text-sm font-normal">
              Identifier les interlocuteurs dans la transcription
            </Label>
          </div>
        </div>
      )}

      {/* Recording visualization */}
      <div className="flex flex-col items-center justify-center py-8 border rounded-lg bg-muted/30">
        {/* Timer */}
        <div
          className={cn(
            "text-4xl font-mono mb-4",
            state === "recording" && "text-red-500",
            state === "paused" && "text-yellow-500"
          )}
        >
          {formatDuration(duration)}
        </div>

        {/* Microphone icon with animation */}
        <div className="relative mb-6">
          <div
            className={cn(
              "p-6 rounded-full transition-all",
              state === "recording" && "bg-red-500/20 animate-pulse",
              state === "paused" && "bg-yellow-500/20",
              state === "idle" && "bg-muted",
              state === "stopped" && "bg-green-500/20"
            )}
          >
            <Mic
              className={cn(
                "h-12 w-12",
                state === "recording" && "text-red-500",
                state === "paused" && "text-yellow-500",
                state === "idle" && "text-muted-foreground",
                state === "stopped" && "text-green-500"
              )}
            />
          </div>

          {/* Audio level indicator */}
          {state === "recording" && (
            <div
              className="absolute inset-0 rounded-full border-4 border-red-500/50 animate-ping"
              style={{
                transform: `scale(${1 + audioLevel * 0.5})`,
                opacity: 0.3 + audioLevel * 0.7,
              }}
            />
          )}
        </div>

        {/* Status text */}
        <p className="text-sm text-muted-foreground mb-4">
          {state === "idle" && "Prêt à enregistrer"}
          {state === "recording" && "Enregistrement en cours..."}
          {state === "paused" && "Enregistrement en pause"}
          {state === "stopped" && "Enregistrement terminé !"}
        </p>

        {/* Audio preview when stopped */}
        {state === "stopped" && audioUrl && (
          <audio controls className="mb-4 w-full max-w-md" src={audioUrl}>
            Votre navigateur ne supporte pas l&apos;élément audio.
          </audio>
        )}

        {/* Controls */}
        <div className="flex items-center gap-3">
          {state === "idle" && (
            <Button
              onClick={startRecording}
              disabled={disabled}
              size="lg"
              className="bg-red-500 hover:bg-red-600"
            >
              <Mic className="h-5 w-5 mr-2" />
              Démarrer l&apos;enregistrement
            </Button>
          )}

          {state === "recording" && (
            <>
              <Button onClick={pauseRecording} variant="outline" size="lg">
                <Pause className="h-5 w-5 mr-2" />
                Pause
              </Button>
              <Button onClick={stopRecording} variant="secondary" size="lg">
                <Square className="h-5 w-5 mr-2" />
                Stop
              </Button>
            </>
          )}

          {state === "paused" && (
            <>
              <Button onClick={resumeRecording} variant="outline" size="lg">
                <Play className="h-5 w-5 mr-2" />
                Reprendre
              </Button>
              <Button onClick={stopRecording} variant="secondary" size="lg">
                <Square className="h-5 w-5 mr-2" />
                Stop
              </Button>
            </>
          )}

          {state === "stopped" && (
            <>
              <Button
                onClick={resetRecording}
                variant="destructive"
                size="lg"
              >
                <Trash2 className="h-5 w-5 mr-2" />
                Supprimer & réenregistrer
              </Button>
              <Button onClick={saveRecording} size="lg">
                Sauvegarder et transcrire
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
