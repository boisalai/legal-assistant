"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Play,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  Settings,
  Zap,
  FileSearch,
} from "lucide-react";
import { AnalysisProgress } from "@/components/AnalysisProgress";
import type { Course, Document } from "@/types";
import { analysisApi } from "@/lib/api";
import { useLLMSettings } from "@/hooks/use-llm-settings";

interface AnalysisTabProps {
  caseId: string;
  caseData: Course;
  documents: Document[];
  onAnalysisComplete: () => void;
}

const LLM_MODELS = [
  { id: "ollama:qwen2.5:7b", name: "Qwen 2.5 7B", description: "Recommandé - Bon équilibre qualité/vitesse" },
  { id: "ollama:llama3.2", name: "Llama 3.2", description: "Rapide - Pour tests rapides" },
  { id: "anthropic:claude-sonnet-4-5-20250929", name: "Claude Sonnet 4.5", description: "Meilleure qualité - Nécessite clé API" },
];

const EXTRACTION_METHODS = [
  { id: "pypdf", name: "PyPDF", description: "Standard - Fonctionne avec la plupart des PDFs" },
  { id: "pdfplumber", name: "PDF Plumber", description: "Meilleur pour les tableaux" },
  { id: "ocr", name: "OCR (Surya)", description: "Pour les documents scannés" },
];

export function AnalysisTab({ caseId, caseData, documents, onAnalysisComplete }: AnalysisTabProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // LLM settings hook - persists to localStorage (shared with assistant tab)
  const { modelId: selectedModel, updateSetting: updateLLMSetting } = useLLMSettings();

  // Settings
  const [extractionMethod, setExtractionMethod] = useState(EXTRACTION_METHODS[0].id);
  const [useOcr, setUseOcr] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const canAnalyze = documents.length > 0 && (caseData.status === "nouveau" || caseData.status === "pending");
  const isComplete = caseData.status && ["termine", "summarized", "analyse_complete", "complete", "valide"].includes(caseData.status);
  const isInProgress = caseData.status === "en_analyse" || caseData.status === "analyzing";

  const handleStartAnalysis = async () => {
    setIsAnalyzing(true);
    setError(null);
    setShowProgress(true);

    try {
      await analysisApi.startStream(caseId);
      // The progress component will handle updates
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'analyse");
      setIsAnalyzing(false);
      setShowProgress(false);
    }
  };

  const handleAnalysisComplete = () => {
    setIsAnalyzing(false);
    setShowProgress(false);
    onAnalysisComplete();
  };

  const handleAnalysisError = (msg: string) => {
    setError(msg);
    setIsAnalyzing(false);
    setShowProgress(false);
  };

  const getStatusInfo = () => {
    if (isComplete) {
      return {
        icon: CheckCircle2,
        color: "text-green-600",
        bgColor: "bg-green-100",
        label: "Analyse terminée",
        description: "L'analyse de ce dossier est complète.",
      };
    }
    if (isInProgress || isAnalyzing) {
      return {
        icon: Loader2,
        color: "text-yellow-600",
        bgColor: "bg-yellow-100",
        label: "Analyse en cours",
        description: "Veuillez patienter pendant l'analyse...",
      };
    }
    if (documents.length === 0) {
      return {
        icon: AlertTriangle,
        color: "text-amber-600",
        bgColor: "bg-amber-100",
        label: "Documents requis",
        description: "Ajoutez au moins un document pour lancer l'analyse.",
      };
    }
    return {
      icon: Clock,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
      label: "Prêt à analyser",
      description: `${documents.length} document(s) prêt(s) à être analysé(s).`,
    };
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-full ${statusInfo.bgColor}`}>
              <StatusIcon className={`h-6 w-6 ${statusInfo.color} ${isInProgress || isAnalyzing ? "animate-spin" : ""}`} />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">{statusInfo.label}</h3>
              <p className="text-sm text-muted-foreground">{statusInfo.description}</p>
            </div>
            {isComplete && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                Score: {Math.round((caseData.score_confiance || 0) * 100)}%
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Analysis Progress */}
      {(isInProgress || showProgress) && (
        <AnalysisProgress
          dossierId={caseId}
          onComplete={handleAnalysisComplete}
          onError={handleAnalysisError}
        />
      )}

      {/* Error Display */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              <p className="text-sm">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Settings Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Paramètres d'analyse
              </CardTitle>
              <CardDescription>
                Configurez les options avant de lancer l'analyse
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettings(!showSettings)}
            >
              {showSettings ? "Masquer" : "Afficher"}
            </Button>
          </div>
        </CardHeader>
        {showSettings && (
          <CardContent className="space-y-6">
            {/* Model Selection */}
            <div className="space-y-2">
              <Label>Modèle LLM</Label>
              <Select value={selectedModel} onValueChange={(value) => updateLLMSetting("modelId", value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LLM_MODELS.map(model => (
                    <SelectItem key={model.id} value={model.id}>
                      <div>
                        <div className="font-medium">{model.name}</div>
                        <div className="text-xs text-muted-foreground">{model.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Extraction Method */}
            <div className="space-y-2">
              <Label>Méthode d'extraction</Label>
              <Select value={extractionMethod} onValueChange={setExtractionMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXTRACTION_METHODS.map(method => (
                    <SelectItem key={method.id} value={method.id}>
                      <div>
                        <div className="font-medium">{method.name}</div>
                        <div className="text-xs text-muted-foreground">{method.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* OCR Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="use-ocr">Utiliser l'OCR</Label>
                <p className="text-xs text-muted-foreground">
                  Active la reconnaissance optique pour les documents scannés
                </p>
              </div>
              <Switch
                id="use-ocr"
                checked={useOcr}
                onCheckedChange={setUseOcr}
              />
            </div>
          </CardContent>
        )}
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3">
        {canAnalyze && !isAnalyzing && (
          <Button onClick={handleStartAnalysis} className="flex-1">
            <Play className="h-4 w-4 mr-2" />
            Lancer l'analyse
          </Button>
        )}
        {isComplete && (
          <Button onClick={handleStartAnalysis} variant="outline" className="flex-1">
            <RefreshCw className="h-4 w-4 mr-2" />
            Relancer l'analyse
          </Button>
        )}
        {documents.length === 0 && (
          <Button disabled className="flex-1">
            <FileSearch className="h-4 w-4 mr-2" />
            Ajoutez des documents d'abord
          </Button>
        )}
      </div>

      {/* Analysis Steps Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Étapes de l'analyse
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { step: 1, title: "Extraction", description: "Lecture et extraction du texte des documents" },
              { step: 2, title: "Classification", description: "Identification du type de transaction" },
              { step: 3, title: "Vérification", description: "Contrôle de cohérence des informations" },
              { step: 4, title: "Génération", description: "Création de la checklist et recommandations" },
            ].map((item) => (
              <div key={item.step} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">
                  {item.step}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-muted-foreground">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
