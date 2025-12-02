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
  Settings,
  Bot,
  FileText,
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
import { settingsApi, type LLMModel } from "@/lib/api";

// Default models when API is unavailable
const DEFAULT_MODELS: LLMModel[] = [
  { id: "ollama:qwen2.5:7b", name: "Qwen 2.5 7B", provider: "Ollama", recommended: true },
  { id: "ollama:llama3.2", name: "Llama 3.2", provider: "Ollama" },
  { id: "ollama:mistral", name: "Mistral 7B", provider: "Ollama" },
  { id: "anthropic:claude-sonnet-4-5-20250929", name: "Claude Sonnet 4.5", provider: "Claude" },
];

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

export default function SettingsPage() {
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Settings state
  const [models, setModels] = useState<LLMModel[]>(DEFAULT_MODELS);
  const [extractionMethods, setExtractionMethods] = useState(DEFAULT_EXTRACTION_METHODS);
  const [selectedModel, setSelectedModel] = useState("ollama:qwen2.5:7b");
  const [selectedExtraction, setSelectedExtraction] = useState("pypdf");
  const [useOcr, setUseOcr] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // TTS Settings
  const [ttsVoices, setTtsVoices] = useState<TTSVoice[]>([]);
  const [selectedVoiceFr, setSelectedVoiceFr] = useState("fr-FR-DeniseNeural");
  const [selectedVoiceEn, setSelectedVoiceEn] = useState("en-CA-ClaraNeural");

  // Load settings from backend
  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      // Load TTS voices first (independent of other settings)
      try {
        const voicesRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/judgments/tts/voices`);
        if (voicesRes.ok) {
          const voices = await voicesRes.json();
          if (Array.isArray(voices)) {
            setTtsVoices(voices);
          }
        }
      } catch (err) {
        console.log("Could not load TTS voices", err);
      }

      const [modelsResponse, currentSettings] = await Promise.all([
        settingsApi.getModels(),
        settingsApi.getCurrent(),
      ]);

      // Flatten models from providers
      // Backend returns providers directly at root level (e.g., { ollama: {...}, anthropic: {...} })
      // Or wrapped in providers property
      const providers = modelsResponse.providers || modelsResponse;
      const allModels: LLMModel[] = [];
      Object.entries(providers).forEach(([provider, providerData]) => {
        // Skip non-provider keys
        if (provider === 'providers' || provider === 'defaults') return;

        // Handle both formats: array or object with models property
        const data = providerData as { models?: LLMModel[] };
        const models = Array.isArray(providerData)
          ? providerData
          : data.models || [];

        models.forEach((model: LLMModel) => {
          allModels.push({
            ...model,
            provider: provider.charAt(0).toUpperCase() + provider.slice(1),
          });
        });
      });

      if (allModels.length > 0) {
        setModels(allModels);
      }

      // Set current values
      if (currentSettings.analysis) {
        setSelectedModel(currentSettings.analysis.model_id);
        setSelectedExtraction(currentSettings.analysis.extraction_method);
        setUseOcr(currentSettings.analysis.use_ocr);
      }

      // Load TTS voice preferences from localStorage
      const savedVoiceFr = localStorage.getItem("tts_voice_fr");
      const savedVoiceEn = localStorage.getItem("tts_voice_en");
      if (savedVoiceFr) setSelectedVoiceFr(savedVoiceFr);
      if (savedVoiceEn) setSelectedVoiceEn(savedVoiceEn);

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
        model_id: selectedModel,
        extraction_method: selectedExtraction,
        use_ocr: useOcr,
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
            {/* AI Model Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  Modèle IA
                </CardTitle>
                <CardDescription>
                  Choisissez le modèle de langage pour l'analyse de documents
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="model">Modèle par défaut</Label>
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger id="model">
                      <SelectValue placeholder="Sélectionner un modèle" />
                    </SelectTrigger>
                    <SelectContent>
                      {models.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex items-center gap-2">
                            <span>{model.name}</span>
                            <Badge variant="outline" className="text-xs">
                              {model.provider}
                            </Badge>
                            {model.recommended && (
                              <Badge variant="secondary" className="text-xs">
                                Recommandé
                              </Badge>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Ollama: Modèles locaux gratuits. Claude: API payante, meilleure qualité.
                  </p>
                </div>
              </CardContent>
            </Card>

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
    </AppShell>
  );
}
