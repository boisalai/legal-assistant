"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  BookOpen,
  Plus,
  Play,
  Trash2,
  Loader2,
  Sparkles,
  GraduationCap,
} from "lucide-react";
import { toast } from "sonner";
import { flashcardsApi } from "@/lib/api";
import type { FlashcardDeck, Document } from "@/types";

interface FlashcardsSectionProps {
  courseId: string;
  documents: Document[];
  onStudyDeck: (deck: FlashcardDeck) => void;
  onCreateDeck: () => void;
}

export function FlashcardsSection({
  courseId,
  documents,
  onStudyDeck,
  onCreateDeck,
}: FlashcardsSectionProps) {
  const t = useTranslations("flashcards");
  const tCommon = useTranslations("common");
  const [decks, setDecks] = useState<FlashcardDeck[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingDeckId, setDeletingDeckId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deckToDelete, setDeckToDelete] = useState<FlashcardDeck | null>(null);

  // Fetch decks on mount
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
  }, [courseId]);

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

  const getStatusBadge = (deck: FlashcardDeck) => {
    if (deck.total_cards === 0) {
      return <Badge variant="outline">{t("status.empty")}</Badge>;
    }
    if (deck.progress_percent === 100) {
      return <Badge className="bg-green-500">{t("status.mastered")}</Badge>;
    }
    if (deck.learning_cards > 0 || deck.mastered_cards > 0) {
      return <Badge className="bg-blue-500">{t("status.inProgress")}</Badge>;
    }
    return <Badge variant="secondary">{t("status.new")}</Badge>;
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
        <div className="flex items-center gap-2">
          <GraduationCap className="h-4 w-4" />
          <h3 className="font-semibold text-sm">{t("title")}</h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GraduationCap className="h-4 w-4" />
          <h3 className="font-semibold text-sm">
            {t("title")} ({decks.length})
          </h3>
        </div>
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

      {/* Decks list */}
      {decks.length === 0 && hasMarkdownDocs ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <BookOpen className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-3">
              {t("noSets")}
            </p>
            <Button size="sm" onClick={onCreateDeck} className="gap-1">
              <Sparkles className="h-3 w-3" />
              {t("createFirst")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {decks.map((deck) => (
            <Card key={deck.id} className="hover:bg-muted/50 transition-colors">
              <CardHeader className="pb-2 pt-3 px-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1 flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium truncate">
                      {deck.name}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {deck.source_documents.length} document
                      {deck.source_documents.length > 1 ? "s" : ""} ·{" "}
                      {deck.total_cards} fiche
                      {deck.total_cards > 1 ? "s" : ""}
                    </CardDescription>
                  </div>
                  {getStatusBadge(deck)}
                </div>
              </CardHeader>
              <CardContent className="pb-3 px-4">
                {/* Progress bar */}
                {deck.total_cards > 0 && (
                  <div className="space-y-1 mb-3">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{t("progress")}</span>
                      <span>{Math.round(deck.progress_percent)}%</span>
                    </div>
                    <Progress value={deck.progress_percent} className="h-1.5" />
                    <div className="flex gap-3 text-xs text-muted-foreground">
                      <span className="text-green-600">
                        {deck.mastered_cards} {t("masteredCards")}
                      </span>
                      <span className="text-blue-600">
                        {deck.learning_cards} {t("learningCards")}
                      </span>
                      <span>{deck.new_cards} {t("newCards")}</span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="default"
                    onClick={() => onStudyDeck(deck)}
                    disabled={deck.total_cards === 0}
                    className="gap-1 flex-1"
                  >
                    <Play className="h-3 w-3" />
                    {deck.total_cards === 0 ? t("generateFirst") : t("study")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setDeckToDelete(deck);
                      setDeleteDialogOpen(true);
                    }}
                    disabled={deletingDeckId === deck.id}
                  >
                    {deletingDeckId === deck.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Trash2 className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

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
    </div>
  );
}
