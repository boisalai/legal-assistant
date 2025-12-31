"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  X,
  RotateCcw,
  Check,
  Zap,
  Volume2,
  Loader2,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { toast } from "sonner";
import { flashcardsApi } from "@/lib/api";
import type { FlashcardDeck, Flashcard, StudySession, ReviewResult } from "@/types";

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
  const [isReviewing, setIsReviewing] = useState(false);
  const [playingAudio, setPlayingAudio] = useState<"front" | "back" | null>(null);
  const [completedCards, setCompletedCards] = useState<Set<string>>(new Set());

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
  const progressPercent =
    totalCards > 0 ? (completedCards.size / totalCards) * 100 : 0;

  const handleFlip = useCallback(() => {
    setIsFlipped((prev) => !prev);
  }, []);

  const handleReview = async (result: ReviewResult) => {
    if (!currentCard || isReviewing) return;

    setIsReviewing(true);
    try {
      await flashcardsApi.reviewCard(currentCard.id, result);
      setCompletedCards((prev) => new Set(prev).add(currentCard.id));

      // Move to next card
      if (currentIndex < totalCards - 1) {
        setCurrentIndex((prev) => prev + 1);
        setIsFlipped(false);
      } else {
        // Session complete
        toast.success(t("sessionComplete"));
        onDeckUpdate();
      }
    } catch (error) {
      toast.error(t("reviewError"));
    } finally {
      setIsReviewing(false);
    }
  };

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
        if (isFlipped) {
          handleReview("correct");
        } else {
          handleNext();
        }
      } else if (e.key === "1" && isFlipped) {
        handleReview("again");
      } else if (e.key === "2" && isFlipped) {
        handleReview("correct");
      } else if (e.key === "3" && isFlipped) {
        handleReview("easy");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFlipped, currentIndex, handleFlip]);

  const getCardTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      definition: "bg-purple-500",
      concept: "bg-blue-500",
      case: "bg-amber-500",
      question: "bg-green-500",
    };
    return (
      <Badge className={colors[type] || "bg-gray-500"}>
        {t(`types.${type}`)}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b bg-background flex items-center justify-between">
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
        <div className="p-4 border-b bg-background flex items-center justify-between">
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

  const isSessionComplete = completedCards.size === totalCards;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-background shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold truncate">{deck.name}</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex items-center gap-4">
          <Progress value={progressPercent} className="flex-1 h-2" />
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            {completedCards.size}/{totalCards}
          </span>
        </div>
      </div>

      {/* Session complete */}
      {isSessionComplete ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 p-6">
          <div className="text-6xl">🎉</div>
          <div className="text-center">
            <h3 className="text-2xl font-bold mb-2">{t("sessionComplete")}</h3>
            <p className="text-muted-foreground">
              {t("cardsReviewed", { count: totalCards })}
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={onClose}>
              {t("backToCourse")}
            </Button>
            <Button
              onClick={() => {
                setCompletedCards(new Set());
                setCurrentIndex(0);
                setIsFlipped(false);
              }}
            >
              {t("restart")}
            </Button>
          </div>
        </div>
      ) : (
        <>
          {/* Card */}
          <div className="flex-1 p-6 overflow-auto">
            <div className="max-w-2xl mx-auto">
              {/* Card type and navigation */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {currentCard && getCardTypeBadge(currentCard.card_type)}
                  <span className="text-sm text-muted-foreground">
                    {t("cardOf", { current: currentIndex + 1, total: totalCards })}
                  </span>
                </div>
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
                    className="bg-card border rounded-xl p-8 min-h-[300px] flex flex-col backface-hidden"
                    style={{ backfaceVisibility: "hidden" }}
                  >
                    <div className="flex-1 flex items-center justify-center">
                      <p className="text-xl text-center leading-relaxed">
                        {currentCard?.front}
                      </p>
                    </div>
                    <div className="flex justify-center pt-4 border-t mt-4">
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
                    </div>
                    <p className="text-center text-xs text-muted-foreground mt-2">
                      {t("clickToFlip")}
                    </p>
                  </div>

                  {/* Back */}
                  <div
                    className="absolute inset-0 bg-card border rounded-xl p-8 min-h-[300px] flex flex-col backface-hidden rotate-y-180"
                    style={{
                      backfaceVisibility: "hidden",
                      transform: "rotateY(180deg)",
                    }}
                  >
                    <div className="flex-1 flex items-center justify-center">
                      <p className="text-lg text-center leading-relaxed whitespace-pre-wrap">
                        {currentCard?.back}
                      </p>
                    </div>
                    {currentCard?.source_location && (
                      <p className="text-xs text-muted-foreground text-center mt-4 pt-4 border-t">
                        {t("source")}: {currentCard.source_location}
                      </p>
                    )}
                    <div className="flex justify-center pt-2">
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

          {/* Review buttons */}
          <div className="p-4 border-t bg-background shrink-0">
            {isFlipped ? (
              <div className="flex items-center justify-center gap-3">
                <Button
                  variant="outline"
                  onClick={() => handleReview("again")}
                  disabled={isReviewing}
                  className="flex-1 max-w-[150px] gap-2 border-red-200 hover:bg-red-50 hover:border-red-300"
                >
                  <RotateCcw className="h-4 w-4 text-red-500" />
                  <span>{t("review.again")}</span>
                  <kbd className="hidden sm:inline-block text-xs bg-muted px-1 rounded">
                    1
                  </kbd>
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleReview("correct")}
                  disabled={isReviewing}
                  className="flex-1 max-w-[150px] gap-2 border-blue-200 hover:bg-blue-50 hover:border-blue-300"
                >
                  <Check className="h-4 w-4 text-blue-500" />
                  <span>{t("review.correct")}</span>
                  <kbd className="hidden sm:inline-block text-xs bg-muted px-1 rounded">
                    2
                  </kbd>
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleReview("easy")}
                  disabled={isReviewing}
                  className="flex-1 max-w-[150px] gap-2 border-green-200 hover:bg-green-50 hover:border-green-300"
                >
                  <Zap className="h-4 w-4 text-green-500" />
                  <span>{t("review.easy")}</span>
                  <kbd className="hidden sm:inline-block text-xs bg-muted px-1 rounded">
                    3
                  </kbd>
                </Button>
              </div>
            ) : (
              <div className="text-center">
                <Button onClick={handleFlip} className="gap-2">
                  {t("showAnswer")}
                  <kbd className="text-xs bg-primary-foreground/20 px-1.5 rounded">
                    ⎵
                  </kbd>
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
