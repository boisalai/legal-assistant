"use client";

import { useState, useEffect } from "react";
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
  Headphones,
  CheckCircle2,
  AlertCircle,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import { audioSummaryApi, modelsApi, type LLMModel } from "@/lib/api";
import type { Document, AudioGenerationProgress, Module, VoiceInfo } from "@/types";

interface CreateAudioSummaryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  documents: Document[];
  modules: Module[];
  onSuccess: () => void;
}

// Default French voices
const DEFAULT_VOICES: VoiceInfo[] = [
  { id: "fr-CA-SylvieNeural", name: "Sylvie", gender: "female", region: "Canada", language: "fr" },
  { id: "fr-CA-AntoineNeural", name: "Antoine", gender: "male", region: "Canada", language: "fr" },
  { id: "fr-CA-JeanNeural", name: "Jean", gender: "male", region: "Canada", language: "fr" },
  { id: "fr-CA-ThierryNeural", name: "Thierry", gender: "male", region: "Canada", language: "fr" },
  { id: "fr-FR-DeniseNeural", name: "Denise", gender: "female", region: "France", language: "fr" },
  { id: "fr-FR-HenriNeural", name: "Henri", gender: "male", region: "France", language: "fr" },
  { id: "fr-FR-EloiseNeural", name: "Éloïse", gender: "female", region: "France", language: "fr" },
];

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins} min ${secs} sec`;
}

export function CreateAudioSummaryModal({
  open,
  onOpenChange,
  courseId,
  documents,
  modules,
  onSuccess,
}: CreateAudioSummaryModalProps) {
  // Form state
  const [name, setName] = useState("");
  const [selectedModuleIds, setSelectedModuleIds] = useState<string[]>([]);
  const [voiceTitles, setVoiceTitles] = useState("fr-CA-SylvieNeural");
  const [generateScriptOnly, setGenerateScriptOnly] = useState(false);

  // Generation state
  const [isCreating, setIsCreating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState<AudioGenerationProgress | null>(null);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Voices
  const [voices, setVoices] = useState<VoiceInfo[]>(DEFAULT_VOICES);

  // Models
  const [models, setModels] = useState<LLMModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("anthropic:claude-sonnet-4-20250514");

  // Filter markdown documents only
  const markdownDocs = documents.filter(
    (doc) =>
      doc.filename?.endsWith(".md") ||
      doc.filename?.endsWith(".markdown") ||
      doc.filename?.endsWith(".txt")
  );

  // Get markdown document count per module
  const getModuleMarkdownCount = (moduleId: string) => {
    return markdownDocs.filter((doc) => doc.module_id === moduleId).length;
  };

  // Get document IDs from selected modules
  const getSelectedDocumentIds = () => {
    return markdownDocs
      .filter((doc) => doc.module_id && selectedModuleIds.includes(doc.module_id))
      .map((doc) => doc.id);
  };

  // Sort modules by order_index
  const sortedModules = [...modules].sort((a, b) => a.order_index - b.order_index);

  // Fetch available voices and models
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const fetchedVoices = await audioSummaryApi.listVoices();
        if (fetchedVoices.length > 0) {
          setVoices(fetchedVoices);
        }
      } catch (error) {
        console.error("Error fetching voices:", error);
      }
    };
    const fetchModels = async () => {
      try {
        const response = await modelsApi.list();
        // Flatten all models from all providers
        const allModels: LLMModel[] = [];
        for (const provider of Object.values(response)) {
          if (provider && typeof provider === "object" && "models" in provider) {
            allModels.push(...(provider as { models: LLMModel[] }).models);
          }
        }
        setModels(allModels);
      } catch (error) {
        console.error("Error fetching models:", error);
      }
    };
    fetchVoices();
    fetchModels();
  }, []);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setName("");
      setSelectedModuleIds([]);
      setVoiceTitles("fr-CA-SylvieNeural");
      setSelectedModelId("anthropic:claude-sonnet-4-20250514");
      setGenerateScriptOnly(false);
      setIsCreating(false);
      setIsGenerating(false);
      setGenerationProgress(null);
      setGenerationComplete(false);
      setGenerationError(null);
    }
  }, [open]);

  const handleModuleToggle = (moduleId: string) => {
    setSelectedModuleIds((prev) =>
      prev.includes(moduleId)
        ? prev.filter((id) => id !== moduleId)
        : [...prev, moduleId]
    );
  };

  const handleSelectAllModules = () => {
    const modulesWithDocs = sortedModules.filter((m) => getModuleMarkdownCount(m.id) > 0);
    if (selectedModuleIds.length === modulesWithDocs.length) {
      setSelectedModuleIds([]);
    } else {
      setSelectedModuleIds(modulesWithDocs.map((m) => m.id));
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Veuillez entrer un nom pour le résumé");
      return;
    }
    if (selectedModuleIds.length === 0) {
      toast.error("Veuillez sélectionner au moins un module");
      return;
    }
    const selectedDocIds = getSelectedDocumentIds();
    if (selectedDocIds.length === 0) {
      toast.error("Aucun document markdown dans les modules sélectionnés");
      return;
    }

    setIsCreating(true);
    setGenerationError(null);

    try {
      // Step 1: Create the audio summary record
      const summary = await audioSummaryApi.create(courseId, {
        name: name.trim(),
        source_document_ids: selectedDocIds,
        voice_titles: voiceTitles,
        generate_script_only: generateScriptOnly,
      });

      toast.success("Résumé audio créé");

      // Step 2: Generate the audio
      setIsCreating(false);
      setIsGenerating(true);

      const result = await audioSummaryApi.generate(summary.id, {
        modelId: selectedModelId,
        onProgress: (progress) => {
          setGenerationProgress(progress);
        },
      });

      if (result.success) {
        setGenerationComplete(true);
        const durationText = result.actual_duration_seconds
          ? formatDuration(result.actual_duration_seconds)
          : `${result.section_count} sections`;
        toast.success(`Résumé audio généré: ${durationText}`);

        // Close modal after short delay
        setTimeout(() => {
          onOpenChange(false);
          onSuccess();
        }, 1500);
      } else {
        setGenerationError(result.error || "Erreur lors de la génération");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erreur inconnue";
      setGenerationError(message);
      toast.error(message);
    } finally {
      setIsCreating(false);
      setIsGenerating(false);
    }
  };

  const selectedDocCount = getSelectedDocumentIds().length;
  const isFormValid =
    name.trim() &&
    selectedModuleIds.length > 0 &&
    selectedDocCount > 0 &&
    !isCreating &&
    !isGenerating;

  // Group voices by region
  const voicesByRegion = voices.reduce((acc, voice) => {
    if (!acc[voice.region]) {
      acc[voice.region] = [];
    }
    acc[voice.region].push(voice);
    return acc;
  }, {} as Record<string, VoiceInfo[]>);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] max-h-[85vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Headphones className="h-5 w-5" />
            Nouveau résumé audio
          </DialogTitle>
          <DialogDescription>
            Convertissez vos notes de cours en fichier audio structuré avec des voix différentes par section.
          </DialogDescription>
        </DialogHeader>

        {/* Generation in progress */}
        {(isGenerating || generationComplete || generationError) && (
          <div className="py-6 px-2 flex-shrink-0">
            {isGenerating && !generationComplete && !generationError && (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
                <div className="text-center">
                  <p className="font-medium">{generationProgress?.message || "Génération en cours..."}</p>
                  {generationProgress?.current_section && generationProgress?.total_sections && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Section {generationProgress.current_section} / {generationProgress.total_sections}
                    </p>
                  )}
                </div>
                {generationProgress?.percentage !== undefined && (
                  <Progress value={generationProgress.percentage} className="h-2" />
                )}
              </div>
            )}

            {generationComplete && (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <CheckCircle2 className="h-12 w-12 text-green-500" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-green-600">Résumé audio généré avec succès</p>
                  {generationProgress?.actual_duration_seconds && (
                    <p className="text-sm text-muted-foreground mt-1 flex items-center justify-center gap-1">
                      <Clock className="h-4 w-4" />
                      Durée: {formatDuration(generationProgress.actual_duration_seconds)}
                    </p>
                  )}
                </div>
              </div>
            )}

            {generationError && (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <AlertCircle className="h-12 w-12 text-destructive" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-destructive">Erreur lors de la génération</p>
                  <p className="text-sm text-muted-foreground mt-1">{generationError}</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    setGenerationError(null);
                    setIsGenerating(false);
                    setGenerationProgress(null);
                  }}
                  className="w-full"
                >
                  Réessayer
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Form (hidden during generation) */}
        {!isGenerating && !generationComplete && !generationError && (
          <>
            <div className="flex-1 overflow-y-auto space-y-4 py-4 px-1">
              {/* Name input */}
              <div className="space-y-2">
                <Label htmlFor="name">Nom du résumé</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ex: Obligations - Module 1"
                />
              </div>

              {/* Module selection */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Modules à inclure</Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAllModules}
                    className="h-auto py-1 px-2 text-xs"
                  >
                    {selectedModuleIds.length === sortedModules.filter((m) => getModuleMarkdownCount(m.id) > 0).length
                      ? "Tout désélectionner"
                      : "Tout sélectionner"}
                  </Button>
                </div>
                <div className="border rounded-lg p-3 max-h-40 overflow-y-auto space-y-2">
                  {sortedModules.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Aucun module disponible</p>
                  ) : (
                    sortedModules.map((module) => {
                      const mdCount = getModuleMarkdownCount(module.id);
                      const isDisabled = mdCount === 0;
                      return (
                        <div key={module.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`module-${module.id}`}
                            checked={selectedModuleIds.includes(module.id)}
                            onCheckedChange={() => handleModuleToggle(module.id)}
                            disabled={isDisabled}
                          />
                          <label
                            htmlFor={`module-${module.id}`}
                            className={`flex-1 text-sm cursor-pointer ${isDisabled ? "text-muted-foreground" : ""}`}
                          >
                            {module.name}
                            <span className="text-muted-foreground ml-2">
                              ({mdCount} doc{mdCount > 1 ? "s" : ""})
                            </span>
                          </label>
                        </div>
                      );
                    })
                  )}
                </div>
                {selectedDocCount > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {selectedDocCount} document{selectedDocCount > 1 ? "s" : ""} sélectionné{selectedDocCount > 1 ? "s" : ""}
                  </p>
                )}
              </div>

              {/* Model selection */}
              <div className="space-y-2">
                <Label htmlFor="model">Modèle LLM</Label>
                <Select value={selectedModelId} onValueChange={setSelectedModelId}>
                  <SelectTrigger id="model">
                    <SelectValue placeholder="Sélectionner un modèle" />
                  </SelectTrigger>
                  <SelectContent>
                    {models.filter(m => m.id.startsWith("anthropic:") || m.id.startsWith("ollama:")).map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Claude recommandé pour un résultat de qualité.
                </p>
              </div>

              {/* Voice selection */}
              <div className="space-y-2">
                <Label htmlFor="voice-titles">Voix pour les titres (H1/H2)</Label>
                <Select value={voiceTitles} onValueChange={setVoiceTitles}>
                  <SelectTrigger id="voice-titles">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(voicesByRegion).map(([region, regionVoices]) => (
                      <div key={region}>
                        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                          {region}
                        </div>
                        {regionVoices.map((voice) => (
                          <SelectItem key={voice.id} value={voice.id}>
                            {voice.name} ({voice.gender === "female" ? "F" : "M"})
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Les sections de contenu utiliseront des voix aléatoires variées.
                </p>
              </div>

              {/* Script only option */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="script-only"
                  checked={generateScriptOnly}
                  onCheckedChange={(checked) => setGenerateScriptOnly(checked === true)}
                />
                <label
                  htmlFor="script-only"
                  className="text-sm cursor-pointer"
                >
                  Générer uniquement le script (sans audio)
                </label>
              </div>
            </div>

            <DialogFooter className="flex-shrink-0">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Annuler
              </Button>
              <Button onClick={handleCreate} disabled={!isFormValid}>
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Création...
                  </>
                ) : (
                  <>
                    <Headphones className="h-4 w-4 mr-2" />
                    Générer le résumé
                  </>
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
