"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  X,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Download,
  FileText,
  Headphones,
} from "lucide-react";
import { audioSummaryApi } from "@/lib/api";
import type { AudioSummary } from "@/types";

interface AudioSummaryPlayerPanelProps {
  summary: AudioSummary;
  onClose: () => void;
}

function formatTime(seconds: number): string {
  if (isNaN(seconds) || !isFinite(seconds)) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function AudioSummaryPlayerPanel({
  summary,
  onClose,
}: AudioSummaryPlayerPanelProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // Initialize audio source
  useEffect(() => {
    if (audioRef.current && summary.status === "completed") {
      const audioUrl = audioSummaryApi.getAudioUrl(summary.id);
      audioRef.current.src = audioUrl;
      audioRef.current.load();
    }
  }, [summary]);

  // Audio event handlers
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleDurationChange = () => setDuration(audio.duration);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("durationchange", handleDurationChange);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("durationchange", handleDurationChange);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("ended", handleEnded);
    };
  }, []);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
  };

  const handleSeek = (value: number[]) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = value[0];
    setCurrentTime(value[0]);
  };

  const handleVolumeChange = (value: number[]) => {
    if (!audioRef.current) return;
    const newVolume = value[0];
    audioRef.current.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    if (isMuted) {
      audioRef.current.volume = volume || 0.5;
      setIsMuted(false);
    } else {
      audioRef.current.volume = 0;
      setIsMuted(true);
    }
  };

  const skipBackward = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
  };

  const skipForward = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
  };

  const handleDownloadAudio = () => {
    const audioUrl = audioSummaryApi.getAudioUrl(summary.id);
    const link = document.createElement("a");
    link.href = audioUrl;
    link.download = `${summary.name.replace(/\s+/g, "_")}.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadScript = () => {
    const scriptUrl = audioSummaryApi.getScriptUrl(summary.id);
    window.open(scriptUrl, "_blank");
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Headphones className="h-4 w-4" />
            {summary.name}
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Hidden audio element */}
        <audio ref={audioRef} preload="metadata" />

        {/* Progress slider */}
        <div className="space-y-2">
          <Slider
            value={[currentTime]}
            max={duration || 100}
            step={0.1}
            onValueChange={handleSeek}
            className="cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Playback controls */}
        <div className="flex items-center justify-center gap-2">
          <Button variant="ghost" size="sm" onClick={skipBackward} title="Reculer 10s">
            <SkipBack className="h-4 w-4" />
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={togglePlay}
            className="h-10 w-10 rounded-full"
          >
            {isPlaying ? (
              <Pause className="h-5 w-5" />
            ) : (
              <Play className="h-5 w-5 ml-0.5" />
            )}
          </Button>
          <Button variant="ghost" size="sm" onClick={skipForward} title="Avancer 10s">
            <SkipForward className="h-4 w-4" />
          </Button>
        </div>

        {/* Volume and download controls */}
        <div className="flex items-center justify-between">
          {/* Volume control */}
          <div className="flex items-center gap-2 w-32">
            <Button variant="ghost" size="sm" onClick={toggleMute}>
              {isMuted ? (
                <VolumeX className="h-4 w-4" />
              ) : (
                <Volume2 className="h-4 w-4" />
              )}
            </Button>
            <Slider
              value={[isMuted ? 0 : volume]}
              max={1}
              step={0.01}
              onValueChange={handleVolumeChange}
              className="w-20"
            />
          </div>

          {/* Download buttons */}
          <div className="flex items-center gap-1">
            {summary.script_path && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDownloadScript}
                title="Télécharger le script"
              >
                <FileText className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownloadAudio}
              title="Télécharger l'audio"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Info */}
        <div className="text-xs text-muted-foreground text-center">
          {summary.section_count} section{summary.section_count > 1 ? "s" : ""} • {summary.source_documents.length} document{summary.source_documents.length > 1 ? "s" : ""}
        </div>
      </CardContent>
    </Card>
  );
}
