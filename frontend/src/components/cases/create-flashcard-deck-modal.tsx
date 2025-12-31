"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Loader2,
  FileText,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Volume2,
} from "lucide-react";
import { toast } from "sonner";
import { flashcardsApi } from "@/lib/api";
import type { Document, CardType, FlashcardGenerationProgress } from "@/types";

interface CreateFlashcardDeckModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  documents: Document[];
  onSuccess: () => void;
}

const CARD_TYPE_KEYS: CardType[] = ["definition", "concept", "case", "question"];

export function CreateFlashcardDeckModal({
  open,
  onOpenChange,
  courseId,
  documents,
  onSuccess,
}: CreateFlashcardDeckModalProps) {
  const t = useTranslations("flashcards");
  const tCommon = useTranslations("common");

  // Form state
  const [name, setName] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [selectedCardTypes, setSelectedCardTypes] = useState<CardType[]>([
    "definition",
    "concept",
    "case",
    "question",
  ]);
  const [cardCount, setCardCount] = useState(50);
  const [generateAudio, setGenerateAudio] = useState(false);

  // Generation state
  const [isCreating, setIsCreating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] =
    useState<FlashcardGenerationProgress | null>(null);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Filter markdown documents only and sort alphabetically
  const markdownDocs = documents
    .filter(
      (doc) =>
        doc.filename?.endsWith(".md") ||
        doc.filename?.endsWith(".markdown") ||
        doc.filename?.endsWith(".txt")
    )
    .sort((a, b) => {
      const nameA = a.linked_source?.relative_path || a.filename || "";
      const nameB = b.linked_source?.relative_path || b.filename || "";
      return nameA.localeCompare(nameB, "fr", { sensitivity: "base" });
    });

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setName("");
      setSelectedDocIds([]);
      setSelectedCardTypes(["definition", "concept", "case", "question"]);
      setCardCount(50);
      setGenerateAudio(false);
      setIsCreating(false);
      setIsGenerating(false);
      setGenerationProgress(null);
      setGenerationComplete(false);
      setGenerationError(null);
    }
  }, [open]);

  const handleDocumentToggle = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  const handleCardTypeToggle = (type: CardType) => {
    setSelectedCardTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSelectAllDocs = () => {
    if (selectedDocIds.length === markdownDocs.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(markdownDocs.map((d) => d.id));
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error(t("setNameRequired"));
      return;
    }
    if (selectedDocIds.length === 0) {
      toast.error(t("selectDocument"));
      return;
    }
    if (selectedCardTypes.length === 0) {
      toast.error(t("selectCardType"));
      return;
    }

    setIsCreating(true);
    setGenerationError(null);

    try {
      // Step 1: Create the deck
      const deck = await flashcardsApi.createDeck(courseId, {
        name: name.trim(),
        source_document_ids: selectedDocIds,
        card_types: selectedCardTypes,
        card_count: cardCount,
        generate_audio: generateAudio,
      });

      toast.success(t("created"));

      // Step 2: Generate flashcards
      setIsCreating(false);
      setIsGenerating(true);

      const result = await flashcardsApi.generate(deck.id, {
        onProgress: (progress) => {
          setGenerationProgress(progress);
        },
      });

      if (result.success) {
        setGenerationComplete(true);
        toast.success(t("generated", { count: result.cards_generated || 0 }));

        // Close modal after short delay
        setTimeout(() => {
          onOpenChange(false);
          onSuccess();
        }, 1500);
      } else {
        setGenerationError(result.error || t("generationError"));
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Erreur inconnue";
      setGenerationError(message);
      toast.error(message);
    } finally {
      setIsCreating(false);
      setIsGenerating(false);
    }
  };

  const isFormValid =
    name.trim() &&
    selectedDocIds.length > 0 &&
    selectedCardTypes.length > 0 &&
    !isCreating &&
    !isGenerating;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] max-h-[85vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {t("createTitle")}
          </DialogTitle>
          <DialogDescription>
            {t("createDescription")}
          </DialogDescription>
        </DialogHeader>

        {/* Generation in progress */}
        {(isCreating || isGenerating) && (
          <div className="py-6 space-y-4">
            <div className="flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
            <div className="text-center space-y-2">
              <p className="font-medium">
                {isCreating
                  ? t("creating")
                  : generationProgress?.message || t("generating")}
              </p>
              {generationProgress && (
                <p className="text-sm text-muted-foreground">
                  {generationProgress.status}
                </p>
              )}
            </div>
            {isGenerating && (
              <Progress value={undefined} className="w-full animate-pulse" />
            )}
          </div>
        )}

        {/* Generation complete */}
        {generationComplete && (
          <div className="py-6 space-y-4">
            <div className="flex items-center justify-center">
              <CheckCircle2 className="h-12 w-12 text-green-500" />
            </div>
            <div className="text-center">
              <p className="font-medium text-green-600">
                {generationProgress?.cards_generated || 0} fiches générées!
              </p>
            </div>
          </div>
        )}

        {/* Generation error */}
        {generationError && (
          <div className="py-6 space-y-4">
            <div className="flex items-center justify-center">
              <AlertCircle className="h-12 w-12 text-destructive" />
            </div>
            <div className="text-center">
              <p className="font-medium text-destructive">{generationError}</p>
            </div>
            <div className="flex justify-center">
              <Button
                variant="outline"
                onClick={() => {
                  setGenerationError(null);
                  setIsGenerating(false);
                }}
              >
                {tCommon("retry")}
              </Button>
            </div>
          </div>
        )}

        {/* Form */}
        {!isCreating && !isGenerating && !generationComplete && !generationError && (
          <div className="space-y-5 py-2 overflow-y-auto flex-1">
            {/* Deck name */}
            <div className="space-y-2">
              <Label htmlFor="deck-name">{t("setName")}</Label>
              <Input
                id="deck-name"
                placeholder={t("setNamePlaceholder")}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {/* Document selection */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{t("sourceDocuments")}</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSelectAllDocs}
                  className="text-xs h-7"
                >
                  {selectedDocIds.length === markdownDocs.length
                    ? t("deselectAll")
                    : t("selectAll")}
                </Button>
              </div>
              <div className="border rounded-lg max-h-[200px] overflow-y-auto">
                {markdownDocs.length === 0 ? (
                  <p className="p-4 text-sm text-muted-foreground text-center">
                    {t("noMarkdownAvailable")}
                  </p>
                ) : (
                  <div className="divide-y">
                    {markdownDocs.map((doc) => (
                      <label
                        key={doc.id}
                        className="flex items-center gap-3 p-3 hover:bg-muted/50 cursor-pointer"
                      >
                        <Checkbox
                          checked={selectedDocIds.includes(doc.id)}
                          onCheckedChange={() => handleDocumentToggle(doc.id)}
                        />
                        <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <span className="text-sm truncate flex-1">
                          {doc.linked_source?.relative_path || doc.filename}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("documentsSelected", { count: selectedDocIds.length })}
              </p>
            </div>

            {/* Card types */}
            <div className="space-y-2">
              <Label>{t("cardTypes")}</Label>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                {CARD_TYPE_KEYS.map((typeKey) => (
                  <label
                    key={typeKey}
                    className="flex items-center gap-2 cursor-pointer hover:text-foreground"
                  >
                    <Checkbox
                      checked={selectedCardTypes.includes(typeKey)}
                      onCheckedChange={() => handleCardTypeToggle(typeKey)}
                    />
                    <span className="text-sm">{t(`types.${typeKey}`)}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Card count */}
            <div className="space-y-2">
              <Label>{t("cardCount")}</Label>
              <Select
                value={cardCount.toString()}
                onValueChange={(v) => setCardCount(parseInt(v, 10))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10 fiches</SelectItem>
                  <SelectItem value="20">20 fiches</SelectItem>
                  <SelectItem value="50">50 fiches</SelectItem>
                  <SelectItem value="100">100 fiches</SelectItem>
                  <SelectItem value="200">200 fiches</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Generate audio option */}
            <div className="space-y-2">
              <label className="flex items-start gap-3 cursor-pointer">
                <Checkbox
                  checked={generateAudio}
                  onCheckedChange={(checked) => setGenerateAudio(checked === true)}
                  className="mt-0.5"
                />
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Volume2 className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{t("generateAudio")}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t("generateAudioDesc")}
                  </p>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Footer */}
        {!isCreating && !isGenerating && !generationComplete && !generationError && (
          <DialogFooter className="shrink-0 pt-4 border-t mt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {tCommon("cancel")}
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!isFormValid}
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              {t("createAndGenerate")}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
