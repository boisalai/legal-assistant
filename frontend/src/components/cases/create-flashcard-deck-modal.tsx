"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
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

const CARD_TYPES: { value: CardType; label: string; description: string }[] = [
  {
    value: "definition",
    label: "Définitions",
    description: "Termes juridiques et leurs définitions",
  },
  {
    value: "concept",
    label: "Concepts",
    description: "Questions conceptuelles (conditions, éléments)",
  },
  {
    value: "case",
    label: "Jurisprudence",
    description: "Arrêts et leurs ratios decidendi",
  },
  {
    value: "question",
    label: "Questions",
    description: "Questions analytiques et mises en situation",
  },
];

export function CreateFlashcardDeckModal({
  open,
  onOpenChange,
  courseId,
  documents,
  onSuccess,
}: CreateFlashcardDeckModalProps) {
  const t = useTranslations();

  // Form state
  const [name, setName] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [selectedCardTypes, setSelectedCardTypes] = useState<CardType[]>([
    "definition",
    "concept",
    "case",
    "question",
  ]);
  const [cardCount, setCardCount] = useState(30);

  // Generation state
  const [isCreating, setIsCreating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] =
    useState<FlashcardGenerationProgress | null>(null);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Filter markdown documents only
  const markdownDocs = documents.filter(
    (doc) =>
      doc.filename?.endsWith(".md") ||
      doc.filename?.endsWith(".markdown") ||
      doc.filename?.endsWith(".txt")
  );

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setName("");
      setSelectedDocIds([]);
      setSelectedCardTypes(["definition", "concept", "case", "question"]);
      setCardCount(30);
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
      toast.error("Veuillez entrer un nom pour le jeu");
      return;
    }
    if (selectedDocIds.length === 0) {
      toast.error("Veuillez sélectionner au moins un document");
      return;
    }
    if (selectedCardTypes.length === 0) {
      toast.error("Veuillez sélectionner au moins un type de fiche");
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
      });

      toast.success("Jeu créé, génération des fiches...");

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
        toast.success(
          `${result.cards_generated} fiches générées avec succès!`
        );

        // Close modal after short delay
        setTimeout(() => {
          onOpenChange(false);
          onSuccess();
        }, 1500);
      } else {
        setGenerationError(result.error || "Erreur lors de la génération");
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
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Créer un jeu de révision
          </DialogTitle>
          <DialogDescription>
            Générez des fiches de révision à partir de vos documents de cours.
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
                  ? "Création du jeu..."
                  : generationProgress?.message || "Génération en cours..."}
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
                Réessayer
              </Button>
            </div>
          </div>
        )}

        {/* Form */}
        {!isCreating && !isGenerating && !generationComplete && !generationError && (
          <div className="space-y-6 py-4">
            {/* Deck name */}
            <div className="space-y-2">
              <Label htmlFor="deck-name">Nom du jeu</Label>
              <Input
                id="deck-name"
                placeholder="Ex: Révision Module 1-4 (Intra)"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {/* Document selection */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Documents sources</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSelectAllDocs}
                  className="text-xs h-7"
                >
                  {selectedDocIds.length === markdownDocs.length
                    ? "Tout désélectionner"
                    : "Tout sélectionner"}
                </Button>
              </div>
              <div className="border rounded-lg max-h-[200px] overflow-y-auto">
                {markdownDocs.length === 0 ? (
                  <p className="p-4 text-sm text-muted-foreground text-center">
                    Aucun document markdown disponible
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
                {selectedDocIds.length} document
                {selectedDocIds.length > 1 ? "s" : ""} sélectionné
                {selectedDocIds.length > 1 ? "s" : ""}
              </p>
            </div>

            {/* Card types */}
            <div className="space-y-2">
              <Label>Types de fiches</Label>
              <div className="grid grid-cols-2 gap-2">
                {CARD_TYPES.map((type) => (
                  <label
                    key={type.value}
                    className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedCardTypes.includes(type.value)
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted/50"
                    }`}
                  >
                    <Checkbox
                      checked={selectedCardTypes.includes(type.value)}
                      onCheckedChange={() => handleCardTypeToggle(type.value)}
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <p className="text-sm font-medium">{type.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {type.description}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Card count */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Nombre de fiches</Label>
                <span className="text-sm font-medium">{cardCount}</span>
              </div>
              <Slider
                value={[cardCount]}
                onValueChange={(v) => setCardCount(v[0])}
                min={10}
                max={100}
                step={5}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>10 (rapide)</span>
                <span>100 (exhaustif)</span>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        {!isCreating && !isGenerating && !generationComplete && !generationError && (
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!isFormValid}
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              Créer et générer
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
