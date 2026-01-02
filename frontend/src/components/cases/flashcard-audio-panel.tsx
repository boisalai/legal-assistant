"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, Music } from "lucide-react";
import { flashcardsApi } from "@/lib/api";
import { trackActivity } from "@/lib/activity-tracker";
import type { FlashcardDeck } from "@/types";

interface FlashcardAudioPanelProps {
  deck: FlashcardDeck;
  courseId: string;
  onClose: () => void;
}

export function FlashcardAudioPanel({
  deck,
  courseId,
  onClose,
}: FlashcardAudioPanelProps) {
  // Track activity when viewing flashcard audio
  useEffect(() => {
    trackActivity(courseId, "view_flashcard_audio", {
      deck_id: deck.id,
      deck_name: deck.name,
    });
  }, [deck.id, courseId, deck.name]);

  const audioUrl = flashcardsApi.getSummaryAudioUrl(deck.id);

  // Build a readable file path for display
  const cleanCourseId = courseId.replace("course:", "");
  const cleanDeckId = deck.id.replace("flashcard_deck:", "");
  const displayPath = `data/uploads/courses/${cleanCourseId}/flashcards/${cleanDeckId}_revision.mp3`;

  // Create a filename from the deck name
  const filename = `Revision audio - ${deck.name.replace(/\s+/g, "_")}.mp3`;

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="p-4 border-b bg-background flex items-center justify-between shrink-0 min-h-[65px]">
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <h2 className="text-xl font-bold truncate">{filename}</h2>
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            <Music className="h-4 w-4 flex-shrink-0" />
            <span className="truncate" title={displayPath}>
              {displayPath}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-4">
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
        <div className="flex flex-col items-center justify-center h-full gap-6 p-8">
          <Music className="h-24 w-24 text-purple-500/50" />
          <div className="text-center">
            <h4 className="font-medium text-lg">{filename}</h4>
            <p className="text-sm text-muted-foreground mt-1">
              {deck.name}
            </p>
          </div>
          <audio
            controls
            autoPlay
            className="w-full max-w-md"
            src={audioUrl}
          >
            Votre navigateur ne supporte pas l&apos;element audio.
          </audio>
        </div>
      </div>
    </div>
  );
}
