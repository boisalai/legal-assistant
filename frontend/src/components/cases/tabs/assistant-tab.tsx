"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Bot, User, Send, Loader2, Sparkles, AlertCircle, Wifi, WifiOff, Copy, Check } from "lucide-react";
import { Markdown } from "@/components/ui/markdown";
import { chatApi, settingsApi, documentsApi, type ChatMessage as ApiChatMessage, type LLMModel } from "@/lib/api";
import type { Course, Document } from "@/types";
import { TranscriptionProgress, useTranscriptionProgress } from "../transcription-progress";
import { useLLMSettings } from "@/hooks/use-llm-settings";
import { useActivityTracker } from "@/lib/activity-tracker";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  model?: string;
}

interface AssistantTabProps {
  caseData: Course;
}

const SUGGESTED_QUESTIONS = [
  "Quels documents sont manquants pour ce dossier ?",
  "Y a-t-il des incohérences dans les informations extraites ?",
  "Quelles sont les prochaines étapes à effectuer ?",
  "Peux-tu résumer les points importants de ce dossier ?",
  "Calcule les droits de mutation pour cette transaction.",
];

// Default models if API is unavailable
const DEFAULT_MODELS: LLMModel[] = [
  { id: "ollama:qwen2.5:7b", name: "Qwen 2.5 7B (Local)", provider: "Ollama" },
  { id: "ollama:llama3.2", name: "Llama 3.2 (Local)", provider: "Ollama" },
  { id: "anthropic:claude-sonnet-4-5-20250929", name: "Claude Sonnet 4.5", provider: "Claude" },
  { id: "mlx:mlx-community/Ministral-3-14B-Reasoning-2512-4bit", name: "Ministral-3 14B Reasoning (MLX)", provider: "MLX" },
];

// Audio file extensions
const AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"];

function isAudioFile(filename: string): boolean {
  const ext = filename.toLowerCase().slice(filename.lastIndexOf("."));
  return AUDIO_EXTENSIONS.includes(ext);
}

// Detect if user is asking for transcription
function detectTranscriptionRequest(message: string): { isRequest: boolean; filename?: string } {
  const lowerMessage = message.toLowerCase();
  // Added more keywords including "retranscris", "retranscrire", "audio"
  const transcriptionKeywords = [
    "transcrire", "transcris", "transcription", "transcrira",
    "retranscrire", "retranscris", "retranscription",
    "transcrit", "transcrire l'audio", "transcrire le fichier audio"
  ];

  const hasKeyword = transcriptionKeywords.some(kw => lowerMessage.includes(kw));

  if (!hasKeyword) return { isRequest: false };

  // Try to extract filename from message - multiple patterns
  const filenameMatch =
    message.match(/['"«»]([^'"«»]+\.(mp3|wav|m4a|ogg|webm|flac|aac))['"«»]/i) ||
    message.match(/fichier\s+(?:audio\s+)?(\S+\.(mp3|wav|m4a|ogg|webm|flac|aac))/i) ||
    message.match(/audio\s+(\S+\.(mp3|wav|m4a|ogg|webm|flac|aac))/i) ||
    message.match(/(\S+\.(mp3|wav|m4a|ogg|webm|flac|aac))/i);

  console.log("[detectTranscriptionRequest] message:", lowerMessage, "hasKeyword:", hasKeyword, "filename:", filenameMatch?.[1]);

  return {
    isRequest: true,
    filename: filenameMatch ? filenameMatch[1] : undefined
  };
}

export function AssistantTab({ caseData }: AssistantTabProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<LLMModel[]>(DEFAULT_MODELS);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // LLM settings hook - persists to localStorage
  const { modelId: selectedModel, updateSetting: updateLLMSetting, isLoaded: llmSettingsLoaded } = useLLMSettings();

  // Transcription progress hook
  const transcriptionProgress = useTranscriptionProgress();

  // Activity tracking
  const trackActivity = useActivityTracker(caseData.id);

  // Load available models from backend
  const loadModels = useCallback(async () => {
    try {
      const response = await settingsApi.getModels();
      const allModels: LLMModel[] = [];

      // Backend returns providers directly at root level (e.g., { ollama: {...}, anthropic: {...} })
      // Or wrapped in providers property
      const providers = response.providers || response;

      // Flatten providers into a single list
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
        // Use default from settings if available
        // Only set default model from API if no saved preference exists
        if (response.defaults?.model_id && !llmSettingsLoaded) {
          updateLLMSetting("modelId", response.defaults.model_id);
        }
      }
      setApiConnected(true);
    } catch {
      console.log("Settings API not available, using default models");
      setApiConnected(false);
    }
  }, [llmSettingsLoaded, updateLLMSetting]);

  // Load documents for transcription detection
  const loadDocuments = useCallback(async () => {
    try {
      const docs = await documentsApi.list(caseData.id);
      setDocuments(docs);
    } catch {
      console.log("Could not load documents");
    }
  }, [caseData.id]);

  useEffect(() => {
    loadModels();
    loadDocuments();
  }, [loadModels, loadDocuments]);

  // Handle transcription workflow
  const handleTranscription = useCallback(async (filename: string): Promise<string> => {
    // Refresh documents list first to ensure we have the latest
    let currentDocs = documents;
    if (currentDocs.length === 0) {
      try {
        currentDocs = await documentsApi.list(caseData.id);
        setDocuments(currentDocs);
      } catch {
        return "Impossible de charger la liste des documents.";
      }
    }

    console.log("[Transcription] Looking for file:", filename, "in", currentDocs.map(d => d.nom_fichier));

    // Find the document by filename
    let doc: Document | undefined;

    if (filename) {
      // First try exact match
      doc = currentDocs.find(d =>
        d.nom_fichier.toLowerCase() === filename.toLowerCase()
      );

      // Then try includes match
      if (!doc) {
        doc = currentDocs.find(d =>
          d.nom_fichier.toLowerCase().includes(filename.toLowerCase()) ||
          filename.toLowerCase().includes(d.nom_fichier.toLowerCase().replace(/\.[^/.]+$/, ""))
        );
      }
    }

    if (!doc) {
      // Look for any untranscribed audio file if no specific filename found
      const audioDoc = currentDocs.find(d =>
        isAudioFile(d.nom_fichier) && !d.texte_extrait
      );

      if (!audioDoc) {
        // List available audio files
        const audioFiles = currentDocs.filter(d => isAudioFile(d.nom_fichier));
        if (audioFiles.length === 0) {
          return "Je n'ai pas trouvé de fichier audio dans ce dossier.";
        }
        return `Je n'ai pas trouvé de fichier audio non transcrit. Fichiers audio disponibles: ${audioFiles.map(d => d.nom_fichier).join(", ")}`;
      }

      console.log("[Transcription] Using first untranscribed audio:", audioDoc.nom_fichier);
      return await runTranscription(audioDoc);
    }

    if (!isAudioFile(doc.nom_fichier)) {
      return `Le fichier "${doc.nom_fichier}" n'est pas un fichier audio.`;
    }

    console.log("[Transcription] Found document:", doc.nom_fichier);
    return await runTranscription(doc);
  }, [documents, caseData.id]);

  const runTranscription = async (doc: Document): Promise<string> => {
    transcriptionProgress.startTranscription();

    try {
      const result = await documentsApi.transcribeWithWorkflow(
        caseData.id,
        doc.id,
        {
          language: "fr",
          createMarkdown: true,
          onProgress: (progress) => {
            transcriptionProgress.updateProgress(
              progress.step,
              progress.message,
              progress.percentage
            );
          },
          onStepStart: transcriptionProgress.onStepStart,
          onStepComplete: transcriptionProgress.onStepComplete,
        }
      );

      transcriptionProgress.endTranscription(result.success);

      if (result.success) {
        // Refresh documents list
        await loadDocuments();

        const baseName = doc.nom_fichier.replace(/\.[^/.]+$/, "");
        return `J'ai transcrit le fichier audio "${doc.nom_fichier}" et créé un document markdown "${baseName}_transcription.md" avec le contenu formaté.\n\nVoici un aperçu de la transcription:\n\n${result.transcript_text?.slice(0, 500)}${(result.transcript_text?.length || 0) > 500 ? "..." : ""}`;
      } else {
        return `Erreur lors de la transcription: ${result.error || "Erreur inconnue"}`;
      }
    } catch (err) {
      transcriptionProgress.endTranscription(false);
      return `Erreur lors de la transcription: ${err instanceof Error ? err.message : "Erreur inconnue"}`;
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Build conversation history for context
  const buildHistory = (): ApiChatMessage[] => {
    return messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));
  };

  // Simulate a response when API is unavailable
  const simulateResponse = async (userMessage: string): Promise<string> => {
    await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 1000));

    const lowerMessage = userMessage.toLowerCase();

    if (lowerMessage.includes("manquant") || lowerMessage.includes("document")) {
      return `Pour le dossier "${caseData.nom_dossier}" de type ${caseData.type_transaction}, voici les documents généralement requis:\n\n` +
        `• Certificat de localisation (moins de 10 ans)\n` +
        `• Relevé de taxes foncières\n` +
        `• Déclaration du vendeur\n` +
        `• Preuve d'assurance habitation\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    if (lowerMessage.includes("étape") || lowerMessage.includes("prochaine")) {
      return `Prochaines étapes pour ce dossier:\n\n` +
        `1. Vérifier la complétude des documents\n` +
        `2. Valider les informations extraites\n` +
        `3. Contacter les parties si nécessaire\n` +
        `4. Préparer l'acte notarié\n\n` +
        `⚠️ Note: Cette réponse est simulée. Connectez le backend pour des réponses IA réelles.`;
    }

    if (lowerMessage.includes("résume") || lowerMessage.includes("important")) {
      return `Résumé du dossier "${caseData.nom_dossier}":\n\n` +
        `• Type: ${caseData.type_transaction}\n` +
        `• Statut: ${caseData.status}\n` +
        `• Score de confiance: ${caseData.score_confiance || "Non calculé"}%\n\n` +
        `⚠️ Note: Cette réponse est simulée. Lancez le backend pour une analyse complète.`;
    }

    if (lowerMessage.includes("mutation") || lowerMessage.includes("taxe")) {
      return `Pour calculer les droits de mutation (taxe de bienvenue), j'ai besoin du prix de vente.\n\n` +
        `Formule au Québec:\n` +
        `• 0 à 58 900$: 0.5%\n` +
        `• 58 900$ à 294 600$: 1.0%\n` +
        `• Plus de 294 600$: 1.5%\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    return `Je suis l'assistant IA pour le dossier "${caseData.nom_dossier}".\n\n` +
      `Je peux vous aider à:\n` +
      `• Identifier les documents manquants\n` +
      `• Vérifier les incohérences\n` +
      `• Calculer les frais et taxes\n` +
      `• Résumer les informations importantes\n\n` +
      `⚠️ Note: Le backend n'est pas connecté. Les réponses sont simulées. Démarrez le serveur backend pour des réponses IA réelles.`;
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    // Track message activity
    trackActivity("send_message", {
      message: userMessage.content.slice(0, 200), // Limit to 200 chars for privacy
    });

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      let responseContent: string;
      let usedModel = selectedModel;

      // Check if this is a transcription request
      const transcriptionRequest = detectTranscriptionRequest(userMessage.content);

      if (transcriptionRequest.isRequest) {
        // Handle transcription locally (with progress display)
        setLoading(false); // Allow UI to show progress
        responseContent = await handleTranscription(transcriptionRequest.filename || "");
        usedModel = "transcription-workflow";
      } else {
        // Try to call the real API
        try {
          const response = await chatApi.send(userMessage.content, {
            caseId: caseData.id,
            model: selectedModel,
            history: buildHistory(),
          });
          responseContent = response.message;
          usedModel = response.model || selectedModel;
          setApiConnected(true);
        } catch (apiError) {
          // Fallback to simulation if API is unavailable
          console.log("Chat API not available, using simulation", apiError);
          responseContent = await simulateResponse(userMessage.content);
          setApiConnected(false);
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: responseContent,
        timestamp: new Date(),
        model: usedModel,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur s'est produite");
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Désolé, une erreur s'est produite. Veuillez réessayer.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (question: string) => {
    setInput(question);
  };

  const handleCopyMessage = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-280px)] min-h-[500px]">
      {/* Model Selector & Status */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <span className="font-medium">Assistant IA</span>
          {apiConnected !== null && (
            <Badge variant={apiConnected ? "default" : "secondary"} className="gap-1">
              {apiConnected ? (
                <>
                  <Wifi className="h-3 w-3" />
                  Connecté
                </>
              ) : (
                <>
                  <WifiOff className="h-3 w-3" />
                  Mode simulation
                </>
              )}
            </Badge>
          )}
        </div>
        <Select value={selectedModel} onValueChange={(value) => updateLLMSetting("modelId", value)}>
          <SelectTrigger className="w-[220px]">
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
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* API Status Alert */}
      {apiConnected === false && (
        <Alert variant="default" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Backend non connecté. Les réponses sont simulées. Démarrez le serveur backend pour utiliser l'IA.
          </AlertDescription>
        </Alert>
      )}

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Sparkles className="h-12 w-12 text-primary/50 mb-4" />
              <h3 className="text-lg font-medium mb-2">Comment puis-je vous aider ?</h3>
              <p className="text-sm text-muted-foreground mb-6 max-w-md">
                Posez-moi des questions sur ce dossier. Je peux analyser les documents,
                identifier les informations manquantes et vous guider dans vos vérifications.
              </p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {SUGGESTED_QUESTIONS.map((question, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => handleSuggestionClick(question)}
                  >
                    {question}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}
                >
                  {message.role === "assistant" && (
                    <div className="p-2 rounded-lg bg-primary/10 h-fit">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg p-3 relative group ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      <>
                        <Markdown className="text-sm">{message.content}</Markdown>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="absolute top-1 right-1 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => handleCopyMessage(message.content, message.id)}
                          title="Copier le markdown"
                        >
                          {copiedMessageId === message.id ? (
                            <Check className="h-3.5 w-3.5 text-green-600" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      </>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    )}
                    <div
                      className={`flex items-center gap-2 mt-1 text-xs ${
                        message.role === "user"
                          ? "text-primary-foreground/70"
                          : "text-muted-foreground"
                      }`}
                    >
                      <span>
                        {message.timestamp.toLocaleTimeString("fr-CA", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      {message.model && message.role === "assistant" && (
                        <Badge variant="outline" className="text-[10px] px-1 py-0">
                          {message.model.split(":").pop()}
                        </Badge>
                      )}
                    </div>
                  </div>
                  {message.role === "user" && (
                    <div className="p-2 rounded-lg bg-primary h-fit">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="p-2 rounded-lg bg-primary/10 h-fit">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="bg-muted rounded-lg p-3">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                </div>
              )}
              {/* Transcription Progress */}
              <TranscriptionProgress
                isVisible={transcriptionProgress.isTranscribing}
                currentMessage={transcriptionProgress.currentMessage}
                percentage={transcriptionProgress.percentage}
                currentStep={transcriptionProgress.currentStep}
              />
              <div ref={messagesEndRef} />
            </>
          )}
        </CardContent>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Textarea
              placeholder="Posez votre question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              className="min-h-[44px] max-h-[120px] resize-none"
              rows={1}
            />
            <Button onClick={handleSend} disabled={!input.trim() || loading} size="icon">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Appuyez sur Entrée pour envoyer, Maj+Entrée pour un saut de ligne
          </p>
        </div>
      </Card>
    </div>
  );
}
