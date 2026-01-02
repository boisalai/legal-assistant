"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  X,
  Volume2,
  Loader2,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Headphones,
  Square,
} from "lucide-react";
import { toast } from "sonner";
import { flashcardsApi } from "@/lib/api";
import { trackActivity } from "@/lib/activity-tracker";
import type { FlashcardDeck, StudySession } from "@/types";

interface FlashcardStudyPanelProps {
  deck: FlashcardDeck;
  onClose: () => void;
  onDeckUpdate: () => void;
}

export function FlashcardStudyPanel({
  deck,
  onClose,
  onDeckUpdate,
}: FlashcardStudyPanelProps) {
  const t = useTranslations("flashcards");
  const tCommon = useTranslations("common");
  const [session, setSession] = useState<StudySession | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [playingAudio, setPlayingAudio] = useState<"front" | "back" | null>(null);
  const [isPlayingSummary, setIsPlayingSummary] = useState(false);
  const summaryAudioRef = useRef<HTMLAudioElement | null>(null);

  // Track activity when viewing flashcard study
  useEffect(() => {
    trackActivity(deck.course_id, "view_flashcard_study", {
      deck_id: deck.id,
      deck_name: deck.name,
    });
  }, [deck.id, deck.course_id, deck.name]);

  // Load study session
  useEffect(() => {
    const loadSession = async () => {
      try {
        const studySession = await flashcardsApi.startStudySession(deck.id);
        setSession(studySession);
      } catch (error) {
        toast.error(t("loadError"));
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadSession();
  }, [deck.id]);

  const currentCard = session?.cards[currentIndex];
  const totalCards = session?.cards.length || 0;

  const handleFlip = useCallback(() => {
    setIsFlipped((prev) => !prev);
  }, []);

  const handlePlayAudio = async (side: "front" | "back") => {
    if (!currentCard || playingAudio) return;

    setPlayingAudio(side);
    try {
      // First, generate the TTS
      await flashcardsApi.generateTTS(currentCard.id, side);

      // Then play the audio
      const audioUrl = flashcardsApi.getAudioUrl(currentCard.id, side);
      const audio = new Audio(audioUrl);
      audio.onended = () => setPlayingAudio(null);
      audio.onerror = () => {
        setPlayingAudio(null);
        toast.error(t("audioError"));
      };
      await audio.play();
    } catch (error) {
      setPlayingAudio(null);
      toast.error(t("ttsError"));
    }
  };

  const handlePlaySummaryAudio = async () => {
    if (!deck.has_summary_audio) {
      toast.error(t("noSummaryAudio"));
      return;
    }

    if (isPlayingSummary && summaryAudioRef.current) {
      // Stop playing
      summaryAudioRef.current.pause();
      summaryAudioRef.current.currentTime = 0;
      setIsPlayingSummary(false);
      return;
    }

    try {
      const audioUrl = flashcardsApi.getSummaryAudioUrl(deck.id);
      const audio = new Audio(audioUrl);
      summaryAudioRef.current = audio;

      audio.onended = () => {
        setIsPlayingSummary(false);
        summaryAudioRef.current = null;
      };
      audio.onerror = () => {
        setIsPlayingSummary(false);
        summaryAudioRef.current = null;
        toast.error(t("audioError"));
      };

      setIsPlayingSummary(true);
      await audio.play();
    } catch (error) {
      setIsPlayingSummary(false);
      toast.error(t("audioError"));
    }
  };

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (summaryAudioRef.current) {
        summaryAudioRef.current.pause();
        summaryAudioRef.current = null;
      }
    };
  }, []);

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
      setIsFlipped(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < totalCards - 1) {
      setCurrentIndex((prev) => prev + 1);
      setIsFlipped(false);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        handleFlip();
      } else if (e.key === "ArrowLeft") {
        handlePrevious();
      } else if (e.key === "ArrowRight") {
        handleNext();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, handleFlip]);

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b bg-background flex items-center justify-between min-h-[65px]">
          <h2 className="text-xl font-bold">{deck.name}</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!session || session.cards.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b bg-background flex items-center justify-between min-h-[65px]">
          <h2 className="text-xl font-bold">{deck.name}</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
          <BookOpen className="h-16 w-16 text-muted-foreground" />
          <p className="text-muted-foreground text-center">
            {t("noCardsInSet")}
          </p>
          <Button onClick={onClose}>{tCommon("back")}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-3 border-b bg-background shrink-0 min-h-[65px]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold truncate">{deck.name}</h2>
          <div className="flex items-center gap-1">
            {deck.has_summary_audio && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handlePlaySummaryAudio}
                title={isPlayingSummary ? t("stopAudio") : t("playAllAudio")}
              >
                {isPlayingSummary ? (
                  <Square className="h-5 w-5 text-red-500" />
                ) : (
                  <Headphones className="h-5 w-5" />
                )}
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Card */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="max-w-2xl mx-auto">
          {/* Card navigation */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-muted-foreground">
              {t("cardOf", { current: currentIndex + 1, total: totalCards })}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={handlePrevious}
                disabled={currentIndex === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleNext}
                disabled={currentIndex === totalCards - 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Flip card */}
          <div
            className="relative cursor-pointer perspective-1000"
            onClick={handleFlip}
            style={{ perspective: "1000px" }}
          >
            <div
              className={`relative transition-transform duration-500 transform-style-preserve-3d ${
                isFlipped ? "rotate-y-180" : ""
              }`}
              style={{
                transformStyle: "preserve-3d",
                transform: isFlipped ? "rotateY(180deg)" : "rotateY(0)",
              }}
            >
              {/* Front */}
              <div
                className="bg-card border rounded-xl p-6 min-h-[300px] max-h-[500px] flex flex-col backface-hidden"
                style={{ backfaceVisibility: "hidden" }}
              >
                <div className="flex-1 flex items-center justify-center overflow-auto py-2">
                  <p className="text-xl text-center leading-relaxed">
                    {currentCard?.front}
                  </p>
                </div>
                <div className="shrink-0 flex flex-col items-center pt-4 border-t mt-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePlayAudio("front");
                    }}
                    disabled={playingAudio !== null}
                  >
                    {playingAudio === "front" ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Volume2 className="h-4 w-4" />
                    )}
                  </Button>
                  <p className="text-center text-xs text-muted-foreground mt-1">
                    {t("clickToFlip")}
                  </p>
                </div>
              </div>

              {/* Back */}
              <div
                className="absolute inset-0 bg-card border rounded-xl p-6 min-h-[300px] max-h-[500px] flex flex-col backface-hidden rotate-y-180"
                style={{
                  backfaceVisibility: "hidden",
                  transform: "rotateY(180deg)",
                }}
              >
                <div className="flex-1 flex items-center justify-center overflow-auto py-2">
                  <p className="text-lg text-center leading-relaxed whitespace-pre-wrap">
                    {currentCard?.back}
                  </p>
                </div>
                <div className="shrink-0 flex flex-col items-center pt-4 border-t mt-2">
                  {currentCard?.source_location && (
                    <p className="text-xs text-muted-foreground text-center mb-2">
                      {t("source")}: {currentCard.source_location}
                    </p>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePlayAudio("back");
                    }}
                    disabled={playingAudio !== null}
                  >
                    {playingAudio === "back" ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Volume2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer with flip button */}
      <div className="p-4 border-t bg-background shrink-0">
        <div className="text-center">
          <Button onClick={handleFlip} className="gap-2">
            {t("showAnswer")}
            <kbd className="text-xs bg-primary-foreground/20 px-1.5 rounded">
              ⎵
            </kbd>
          </Button>
        </div>
      </div>
    </div>
  );
}
