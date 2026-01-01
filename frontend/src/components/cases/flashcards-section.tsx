"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  Loader2,
  GraduationCap,
} from "lucide-react";
import { toast } from "sonner";
import { flashcardsApi } from "@/lib/api";
import { FlashcardsDataTable } from "./flashcards-data-table";
import type { FlashcardDeck, Document } from "@/types";

interface FlashcardsSectionProps {
  courseId: string;
  documents: Document[];
  onStudyDeck: (deck: FlashcardDeck) => void;
  onCreateDeck: () => void;
  onListenAudio?: (deck: FlashcardDeck) => void;
  refreshKey?: number;
}

export function FlashcardsSection({
  courseId,
  documents,
  onStudyDeck,
  onCreateDeck,
  onListenAudio,
  refreshKey,
}: FlashcardsSectionProps) {
  const t = useTranslations("flashcards");
  const tCommon = useTranslations("common");
  const [decks, setDecks] = useState<FlashcardDeck[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingDeckId, setDeletingDeckId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deckToDelete, setDeckToDelete] = useState<FlashcardDeck | null>(null);

  // Fetch decks on mount and when refreshKey changes
  useEffect(() => {
    const fetchDecks = async () => {
      try {
        const fetchedDecks = await flashcardsApi.listDecks(courseId);
        setDecks(fetchedDecks);
      } catch (error) {
        console.error("Error fetching flashcard decks:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDecks();
  }, [courseId, refreshKey]);

  const handleDeleteDeck = async () => {
    if (!deckToDelete) return;

    setDeletingDeckId(deckToDelete.id);
    try {
      await flashcardsApi.deleteDeck(deckToDelete.id);
      setDecks((prev) => prev.filter((d) => d.id !== deckToDelete.id));
      toast.success(t("deleted"));
    } catch (error) {
      toast.error(t("deleteError"));
    } finally {
      setDeletingDeckId(null);
      setDeckToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleListenAudio = (deck: FlashcardDeck) => {
    // Use parent handler if provided, otherwise play directly
    if (onListenAudio) {
      onListenAudio(deck);
    } else {
      // Fallback: play audio directly
      const audioUrl = flashcardsApi.getSummaryAudioUrl(deck.id);
      const audio = new Audio(audioUrl);
      audio.play().catch(() => {
        toast.error(t("audioError"));
      });
    }
  };

  const handleDeleteClick = (deck: FlashcardDeck) => {
    setDeckToDelete(deck);
    setDeleteDialogOpen(true);
  };

  // Check if we have markdown documents for flashcard generation
  const markdownDocs = documents.filter(
    (doc) =>
      doc.filename?.endsWith(".md") ||
      doc.filename?.endsWith(".markdown") ||
      doc.filename?.endsWith(".txt")
  );
  const hasMarkdownDocs = markdownDocs.length > 0;

  if (loading) {
    return (
      <div className="space-y-2">
        <h3 className="font-semibold text-base flex items-center gap-2">
          <GraduationCap className="h-4 w-4" />
          {t("title")}
        </h3>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Don't show section if no markdown docs and no existing decks
  if (!hasMarkdownDocs && decks.length === 0) {
    return null;
  }

  return (
    <>
      <div className="space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base flex items-center gap-2">
            <GraduationCap className="h-4 w-4" />
            {t("title")} ({decks.length})
          </h3>
          <Button
            size="sm"
            onClick={onCreateDeck}
            disabled={!hasMarkdownDocs}
            className="gap-1"
          >
            <Plus className="h-3 w-3" />
            {t("newSet")}
          </Button>
        </div>

        {/* No markdown docs warning */}
        {!hasMarkdownDocs && (
          <p className="text-sm text-muted-foreground">
            {t("noMarkdownDocs")}
          </p>
        )}

        {/* DataTable */}
        <FlashcardsDataTable
          decks={decks}
          onStudy={onStudyDeck}
          onListenAudio={handleListenAudio}
          onDelete={handleDeleteClick}
          deletingDeckId={deletingDeckId}
        />
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription", { name: deckToDelete?.name || "" })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeckToDelete(null)}>
              {tCommon("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteDeck}>
              {tCommon("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
