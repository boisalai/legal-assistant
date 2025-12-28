"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
  Settings,
  FileText,
  FileSearch,
  Palette,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  Wifi,
  WifiOff,
  RefreshCw,
  Volume2,
} from "lucide-react";
import { settingsApi } from "@/lib/api";
import { toast } from "sonner";
import { Slider } from "@/components/ui/slider";
import {
  LLMConfig,
  loadLLMConfig,
  saveLLMConfig,
  getModelDisplayName,
} from "@/lib/llm-models";

// Import SVG logos for embedding providers
import HuggingFaceLogo from "@/svg/hf-logo.svg";
import OpenAILogo from "@/svg/openai.svg";
import AnthropicLogo from "@/svg/anthropic.svg";
import GeminiLogo from "@/svg/gemini.svg";
import OllamaLogo from "@/svg/ollama.svg";

const DEFAULT_EXTRACTION_METHODS = [
  { id: "pypdf", name: "PyPDF (Standard)", description: "Extraction basique, rapide", available: true },
  { id: "docling-standard", name: "Docling Standard", description: "Extraction avancée avec layout", available: false },
  { id: "docling-vlm", name: "Docling VLM", description: "Extraction maximale avec vision", available: false },
];

interface TTSVoice {
  name: string;
  locale: string;
  country: string;
  language: string;
  gender: string;
}

interface EmbeddingModelInfo {
  id: string;
  name: string;
  dimensions?: number;
  description?: string;
  recommended?: boolean;
  multilingual?: boolean;
  languages?: string;
  quality?: string;
  speed?: string;
  cost?: string;
  ram?: string;
  best_for?: string;
}

interface EmbeddingProviderInfo {
  name: string;
  description: string;
  icon: string;
  requires_api_key: boolean;
  cost?: string;
  models: EmbeddingModelInfo[];
  default: string;
}

// Helper function to get embedding provider logo
function getEmbeddingProviderLogo(providerKey: string) {
  const normalizedProvider = providerKey.toLowerCase();

  switch (normalizedProvider) {
    case "openai":
      return <OpenAILogo className="h-4 w-4 flex-shrink-0" />;
    case "anthropic":
    case "claude":
      return <AnthropicLogo className="h-4 w-4 flex-shrink-0" />;
    case "gemini":
    case "google":
      return <GeminiLogo className="h-4 w-4 flex-shrink-0" />;
    case "ollama":
      return <OllamaLogo className="h-4 w-4 flex-shrink-0" />;
    case "local":
    default:
      return <HuggingFaceLogo className="h-4 w-4 flex-shrink-0" />;
  }
}

export default function SettingsPage() {
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Settings state
  const [extractionMethods, setExtractionMethods] = useState(DEFAULT_EXTRACTION_METHODS);
  const [selectedExtraction, setSelectedExtraction] = useState("pypdf");
  const [useOcr, setUseOcr] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // TTS Settings
  const [ttsVoices, setTtsVoices] = useState<TTSVoice[]>([]);
  const [selectedVoiceFr, setSelectedVoiceFr] = useState("fr-FR-DeniseNeural");
  const [selectedVoiceEn, setSelectedVoiceEn] = useState("en-CA-ClaraNeural");

  // LLM Advanced Settings
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    model: "ollama:qwen2.5:7b",
    temperature: 0.7,
    maxTokens: 2000,
    topP: 0.9,
  });

  // Embedding Settings
  const [embeddingProviders, setEmbeddingProviders] = useState<Record<string, EmbeddingProviderInfo>>({});
  const [selectedEmbeddingProvider, setSelectedEmbeddingProvider] = useState("local");
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState("BAAI/bge-m3");
  const [embeddingMismatch, setEmbeddingMismatch] = useState<{
    has_mismatch: boolean;
    documents_to_reindex: number;
    existing_models: string[];
    current_model: string;
  } | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexDialogOpen, setReindexDialogOpen] = useState(false);

  // Load settings from backend
  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      // Load TTS voices first (independent of other settings)
      try {
        const voicesRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/courses/tts/voices`);
        if (voicesRes.ok) {
          const voices = await voicesRes.json();
          if (Array.isArray(voices)) {
            setTtsVoices(voices);
          }
        }
      } catch (err) {
        console.log("Could not load TTS voices", err);
      }

      // Load embedding models
      try {
        const embeddingRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/settings/embedding-models`);
        if (embeddingRes.ok) {
          const embeddingData = await embeddingRes.json();
          setEmbeddingProviders(embeddingData.providers || {});
          if (embeddingData.current) {
            setSelectedEmbeddingProvider(embeddingData.current.provider || "local");
            setSelectedEmbeddingModel(embeddingData.current.model || "BAAI/bge-m3");
          }
        }
      } catch (err) {
        console.log("Could not load embedding models", err);
      }

      const currentSettings = await settingsApi.getCurrent();

      // Set current values
      if (currentSettings.analysis) {
        setSelectedExtraction(currentSettings.analysis.extraction_method);
        setUseOcr(currentSettings.analysis.use_ocr);
      }

      // Set embedding values from settings if available
      if (currentSettings.embedding) {
        setSelectedEmbeddingProvider(currentSettings.embedding.provider);
        setSelectedEmbeddingModel(currentSettings.embedding.model);
      }

      // Load TTS voice preferences from localStorage
      const savedVoiceFr = localStorage.getItem("tts_voice_fr");
      const savedVoiceEn = localStorage.getItem("tts_voice_en");
      if (savedVoiceFr) setSelectedVoiceFr(savedVoiceFr);
      if (savedVoiceEn) setSelectedVoiceEn(savedVoiceEn);

      // Load LLM config from localStorage
      const savedLlmConfig = loadLLMConfig();
      setLlmConfig(savedLlmConfig);

      setApiConnected(true);
    } catch (err) {
      console.log("Settings API not available", err);
      setApiConnected(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Check dark mode from localStorage
  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setDarkMode(isDark);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      await settingsApi.update({
        extraction_method: selectedExtraction,
        use_ocr: useOcr,
        embedding_provider: selectedEmbeddingProvider,
        embedding_model: selectedEmbeddingModel,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    if (newDarkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  };

  const saveTTSVoices = () => {
    // Save TTS voice preferences to localStorage
    localStorage.setItem("tts_voice_fr", selectedVoiceFr);
    localStorage.setItem("tts_voice_en", selectedVoiceEn);
  };

  const saveLLMSettings = () => {
    // Save LLM config to localStorage and dispatch event
    saveLLMConfig(llmConfig);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const checkEmbeddingMismatch = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/settings/check-embedding-mismatch`);
      if (response.ok) {
        const data = await response.json();
        setEmbeddingMismatch(data);
      }
    } catch (err) {
      console.log("Could not check embedding mismatch", err);
    }
  }, []);

  // Check embedding model mismatch on load and when model changes
  useEffect(() => {
    if (apiConnected && selectedEmbeddingModel) {
      checkEmbeddingMismatch();
    }
  }, [apiConnected, selectedEmbeddingModel, checkEmbeddingMismatch]);

  const handleReindexAll = async () => {
    setReindexDialogOpen(false);
    setReindexing(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/settings/reindex-all`, {
        method: "POST",
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`Réindexation terminée avec succès!`, {
          description: `${data.documents_processed}/${data.total_documents} documents traités, ${data.chunks_created} chunks créés`,
        });
        // Recheck mismatch
        await checkEmbeddingMismatch();
      } else {
        const error = await response.json();
        toast.error(`Erreur lors de la réindexation`, {
          description: error.detail || "Erreur inconnue",
        });
      }
    } catch (err) {
      toast.error(`Erreur lors de la réindexation`, {
        description: err instanceof Error ? err.message : "Erreur inconnue",
      });
    } finally {
      setReindexing(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-3xl">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Settings className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Paramètres</h1>
              <p className="text-muted-foreground">
                Configurez votre environnement de travail
              </p>
            </div>
          </div>
          <Badge variant={apiConnected ? "default" : "secondary"} className="gap-1">
            {apiConnected ? (
              <>
                <Wifi className="h-3 w-3" />
                Backend connecté
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                Mode local
              </>
            )}
          </Badge>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Success Alert */}
        {saved && (
          <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-600">
              Paramètres sauvegardés avec succès
            </AlertDescription>
          </Alert>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Extraction Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Extraction PDF
                </CardTitle>
                <CardDescription>
                  Configurez la méthode d'extraction de texte des documents
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="extraction">Méthode d'extraction</Label>
                  <Select
                    value={selectedExtraction}
                    onValueChange={setSelectedExtraction}
                  >
                    <SelectTrigger id="extraction">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {extractionMethods.map((method) => (
                        <SelectItem
                          key={method.id}
                          value={method.id}
                          disabled={!method.available}
                        >
                          <div className="flex items-center gap-2">
                            <span>{method.name}</span>
                            {!method.available && (
                              <Badge variant="outline" className="text-xs">
                                Non disponible
                              </Badge>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="ocr">Activer l'OCR</Label>
                    <p className="text-xs text-muted-foreground">
                      Pour les PDFs scannés ou images
                    </p>
                  </div>
                  <Switch
                    id="ocr"
                    checked={useOcr}
                    onCheckedChange={setUseOcr}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Appearance Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  Apparence
                </CardTitle>
                <CardDescription>
                  Personnalisez l'interface de l'application
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="dark-mode">Mode sombre</Label>
                    <p className="text-xs text-muted-foreground">
                      Activer le thème sombre
                    </p>
                  </div>
                  <Switch
                    id="dark-mode"
                    checked={darkMode}
                    onCheckedChange={toggleDarkMode}
                  />
                </div>
              </CardContent>
            </Card>

            {/* LLM Advanced Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Paramètres LLM avancés
                </CardTitle>
                <CardDescription>
                  Ajustez les paramètres de génération du modèle de langage
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Current Model (read-only) */}
                <div className="space-y-2">
                  <Label>Modèle actuel</Label>
                  <div className="flex items-center h-10 px-3 py-2 text-sm rounded-md border border-input bg-muted">
                    {getModelDisplayName(llmConfig.model)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Changez de modèle via le sélecteur dans le header
                  </p>
                </div>

                {/* Temperature */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="llm-temperature">Température</Label>
                    <span className="text-sm text-muted-foreground">
                      {llmConfig.temperature.toFixed(1)}
                    </span>
                  </div>
                  <Slider
                    id="llm-temperature"
                    min={0}
                    max={2}
                    step={0.1}
                    value={[llmConfig.temperature]}
                    onValueChange={(value) =>
                      setLlmConfig({ ...llmConfig, temperature: value[0] })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Plus élevé = plus créatif, plus bas = plus déterministe
                  </p>
                </div>

                {/* Max Tokens */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="llm-maxTokens">Max tokens</Label>
                    <span className="text-sm text-muted-foreground">
                      {llmConfig.maxTokens}
                    </span>
                  </div>
                  <Slider
                    id="llm-maxTokens"
                    min={100}
                    max={4000}
                    step={100}
                    value={[llmConfig.maxTokens]}
                    onValueChange={(value) =>
                      setLlmConfig({ ...llmConfig, maxTokens: value[0] })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Longueur maximale de la réponse
                  </p>
                </div>

                {/* Top P */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="llm-topP">Top P</Label>
                    <span className="text-sm text-muted-foreground">
                      {llmConfig.topP.toFixed(2)}
                    </span>
                  </div>
                  <Slider
                    id="llm-topP"
                    min={0}
                    max={1}
                    step={0.05}
                    value={[llmConfig.topP]}
                    onValueChange={(value) =>
                      setLlmConfig({ ...llmConfig, topP: value[0] })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Diversité des tokens considérés
                  </p>
                </div>

                {/* Save LLM Settings Button */}
                <Button onClick={saveLLMSettings} variant="outline" className="w-full">
                  <Save className="h-4 w-4 mr-2" />
                  Sauvegarder les paramètres LLM
                </Button>
              </CardContent>
            </Card>

            {/* Embedding Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileSearch className="h-5 w-5" />
                  Modèle d'Embedding
                </CardTitle>
                <CardDescription>
                  Pour l'indexation vectorielle et la recherche sémantique dans les documents
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Model Selection */}
                <div className="space-y-2">
                  <Label htmlFor="embedding-model">Modèle d'embedding</Label>
                  <Select
                    value={selectedEmbeddingModel}
                    onValueChange={(modelId) => {
                      setSelectedEmbeddingModel(modelId);
                      // Trouver le provider de ce modèle
                      for (const [providerKey, provider] of Object.entries(embeddingProviders)) {
                        if (provider.models.some(m => m.id === modelId)) {
                          setSelectedEmbeddingProvider(providerKey);
                          break;
                        }
                      }
                    }}
                  >
                    <SelectTrigger id="embedding-model">
                      <SelectValue placeholder="Sélectionner un modèle">
                        {(() => {
                          // Find selected model and its provider
                          for (const [providerKey, provider] of Object.entries(embeddingProviders)) {
                            const model = provider.models.find(m => m.id === selectedEmbeddingModel);
                            if (model) {
                              return (
                                <div className="flex items-center gap-2">
                                  {getEmbeddingProviderLogo(providerKey)}
                                  <span>
                                    {model.name}
                                    {model.recommended && " ⭐"}
                                  </span>
                                </div>
                              );
                            }
                          }
                          return "Sélectionner un modèle";
                        })()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(embeddingProviders).map(([providerKey, provider]) => (
                        <div key={providerKey}>
                          <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                            {provider.name}
                          </div>
                          {provider.models.map((model) => (
                            <SelectItem key={model.id} value={model.id}>
                              <div className="flex items-center gap-2">
                                {getEmbeddingProviderLogo(providerKey)}
                                <span>
                                  {model.name}
                                  {model.recommended && " ⭐"}
                                </span>
                              </div>
                            </SelectItem>
                          ))}
                        </div>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Model Info */}
                {(() => {
                  // Trouver le modèle sélectionné dans tous les providers
                  let selectedModelInfo: EmbeddingModelInfo | undefined;
                  let selectedProviderInfo: EmbeddingProviderInfo | undefined;

                  for (const [providerKey, provider] of Object.entries(embeddingProviders)) {
                    const model = provider.models.find(m => m.id === selectedEmbeddingModel);
                    if (model) {
                      selectedModelInfo = model;
                      selectedProviderInfo = provider;
                      break;
                    }
                  }

                  if (!selectedModelInfo) return null;

                  return (
                    <div className="text-sm text-muted-foreground space-y-1">
                      {selectedModelInfo.description && (
                        <p>{selectedModelInfo.description}</p>
                      )}
                      {selectedModelInfo.languages && (
                        <p>Langues: {selectedModelInfo.languages}</p>
                      )}
                      {selectedModelInfo.speed && (
                        <p>Vitesse: {selectedModelInfo.speed}</p>
                      )}
                      {selectedModelInfo.ram && (
                        <p>RAM: {selectedModelInfo.ram}</p>
                      )}
                      {selectedProviderInfo?.requires_api_key && (
                        <p className="text-amber-600 dark:text-amber-400 pt-2">
                          Nécessite une clé API OpenAI (OPENAI_API_KEY)
                        </p>
                      )}
                    </div>
                  );
                })()}

                {/* Embedding Mismatch Warning */}
                {embeddingMismatch?.has_mismatch && (
                  <Alert className="border-amber-500 bg-amber-50 dark:bg-amber-950">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    <AlertDescription className="text-amber-600 dark:text-amber-400">
                      <p className="font-semibold mb-2">
                        ⚠️ Réindexation requise
                      </p>
                      <p className="text-sm mb-2">
                        {embeddingMismatch.documents_to_reindex} document(s) sont indexés avec un modèle différent ({embeddingMismatch.existing_models.filter(m => m !== embeddingMismatch.current_model).join(", ")}).
                      </p>
                      <p className="text-sm mb-3">
                        Pour utiliser le nouveau modèle "{embeddingMismatch.current_model}", vous devez réindexer tous les documents.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setReindexDialogOpen(true)}
                        disabled={reindexing}
                        className="border-amber-600 text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900"
                      >
                        {reindexing ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Réindexation en cours...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Réindexer tous les documents
                          </>
                        )}
                      </Button>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* TTS Voice Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Volume2 className="h-5 w-5" />
                  Synthèse vocale (TTS)
                </CardTitle>
                <CardDescription>
                  Choisissez les voix par défaut pour la lecture de documents
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* French Voice */}
                <div className="space-y-2">
                  <Label htmlFor="voice-fr">Voix française</Label>
                  <Select value={selectedVoiceFr} onValueChange={(value) => {
                    setSelectedVoiceFr(value);
                    saveTTSVoices();
                  }}>
                    <SelectTrigger id="voice-fr">
                      <SelectValue placeholder="Sélectionner une voix française" />
                    </SelectTrigger>
                    <SelectContent>
                      {ttsVoices
                        .filter((v) => v.language === "French")
                        .map((voice) => (
                          <SelectItem key={voice.name} value={voice.name}>
                            <div className="flex items-center gap-2">
                              <span>{voice.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {voice.country} - {voice.gender}
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Voix utilisée par défaut pour lire les documents en français
                  </p>
                </div>

                {/* English Voice */}
                <div className="space-y-2">
                  <Label htmlFor="voice-en">Voix anglaise</Label>
                  <Select value={selectedVoiceEn} onValueChange={(value) => {
                    setSelectedVoiceEn(value);
                    saveTTSVoices();
                  }}>
                    <SelectTrigger id="voice-en">
                      <SelectValue placeholder="Sélectionner une voix anglaise" />
                    </SelectTrigger>
                    <SelectContent>
                      {ttsVoices
                        .filter((v) => v.language === "English")
                        .map((voice) => (
                          <SelectItem key={voice.name} value={voice.name}>
                            <div className="flex items-center gap-2">
                              <span>{voice.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {voice.country} - {voice.gender}
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Voix utilisée par défaut pour lire les documents en anglais
                  </p>
                </div>

                {ttsVoices.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Chargement des voix disponibles...
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Save Button */}
            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={saving || !apiConnected} className="flex-1">
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sauvegarde...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Sauvegarder les paramètres
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={loadSettings} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>

            {!apiConnected && (
              <p className="text-sm text-muted-foreground text-center">
                Le backend n'est pas connecté. Les paramètres IA ne peuvent pas être sauvegardés.
                Le mode sombre est sauvegardé localement.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Reindex Confirmation Dialog */}
      <AlertDialog open={reindexDialogOpen} onOpenChange={setReindexDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Réindexer tous les documents ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette opération va supprimer tous les anciens embeddings et réindexer tous les documents.
              Cela peut prendre plusieurs minutes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleReindexAll}>
              Continuer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
