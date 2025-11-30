"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { AppShell } from "@/components/layout";
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
import {
  Bot,
  User,
  Send,
  Loader2,
  Sparkles,
  AlertCircle,
  Wifi,
  WifiOff,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { chatApi, settingsApi, type ChatMessage as ApiChatMessage, type LLMModel } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  model?: string;
}

const SUGGESTED_QUESTIONS = [
  "Quels documents sont requis pour une vente immobilière au Québec ?",
  "Comment calculer les droits de mutation (taxe de bienvenue) ?",
  "Quelles sont les étapes d'une transaction notariale typique ?",
  "Quels sont les délais habituels pour une transaction immobilière ?",
  "Comment vérifier un certificat de localisation ?",
  "Quelles vérifications effectuer au registre foncier ?",
];

// Default models if API is unavailable
const DEFAULT_MODELS: LLMModel[] = [
  { id: "ollama:qwen2.5:7b", name: "Qwen 2.5 7B (Local)", provider: "Ollama" },
  { id: "ollama:llama3.2", name: "Llama 3.2 (Local)", provider: "Ollama" },
  { id: "anthropic:claude-sonnet-4-5-20250929", name: "Claude Sonnet 4.5", provider: "Claude" },
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<LLMModel[]>(DEFAULT_MODELS);
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODELS[0].id);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
        // Use default from response if available
        if (response.defaults?.model_id) {
          setSelectedModel(response.defaults.model_id);
        }
      }
      setApiConnected(true);
    } catch {
      console.log("Settings API not available, using default models");
      setApiConnected(false);
    }
  }, []);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

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

    if (lowerMessage.includes("document") && lowerMessage.includes("vente")) {
      return `Documents requis pour une vente immobilière au Québec:\n\n` +
        `**Documents du vendeur:**\n` +
        `• Titre de propriété (acte d'achat)\n` +
        `• Certificat de localisation (moins de 10 ans)\n` +
        `• Relevé de taxes foncières\n` +
        `• Déclaration du vendeur\n` +
        `• Factures de travaux majeurs\n\n` +
        `**Documents de l'acheteur:**\n` +
        `• Pièce d'identité valide\n` +
        `• Preuve de financement ou pré-autorisation hypothécaire\n` +
        `• Preuve d'assurance habitation\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    if (lowerMessage.includes("mutation") || lowerMessage.includes("taxe") || lowerMessage.includes("bienvenue")) {
      return `Calcul des droits de mutation (taxe de bienvenue) au Québec:\n\n` +
        `**Formule par tranches:**\n` +
        `• 0$ à 58 900$: **0.5%**\n` +
        `• 58 900$ à 294 600$: **1.0%**\n` +
        `• Plus de 294 600$: **1.5%**\n\n` +
        `**Exemple pour 450 000$:**\n` +
        `• (58 900 × 0.5%) = 294.50$\n` +
        `• ((294 600 - 58 900) × 1%) = 2 357$\n` +
        `• ((450 000 - 294 600) × 1.5%) = 2 331$\n` +
        `• **Total: 4 982.50$**\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    if (lowerMessage.includes("étape") || lowerMessage.includes("transaction")) {
      return `Étapes d'une transaction notariale typique:\n\n` +
        `1. **Offre d'achat acceptée** - Signature par les parties\n` +
        `2. **Inspection** - Vérification de l'état du bien\n` +
        `3. **Financement** - Approbation hypothécaire finale\n` +
        `4. **Recherche de titres** - Vérification au registre foncier\n` +
        `5. **Préparation des actes** - Rédaction par le notaire\n` +
        `6. **Signature** - Signature des actes chez le notaire\n` +
        `7. **Publication** - Enregistrement au registre foncier\n` +
        `8. **Remise des clés** - Transfert de propriété\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    if (lowerMessage.includes("délai") || lowerMessage.includes("temps")) {
      return `Délais habituels pour une transaction immobilière:\n\n` +
        `• **Offre à signature:** 30-60 jours (selon conditions)\n` +
        `• **Inspection:** 7-10 jours après offre\n` +
        `• **Financement:** 14-21 jours\n` +
        `• **Recherche de titres:** 3-5 jours ouvrables\n` +
        `• **Certificat de localisation:** 1-2 semaines si nouveau\n` +
        `• **Préparation des actes:** 2-5 jours\n` +
        `• **Publication au registre:** 24-48 heures\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    if (lowerMessage.includes("localisation") || lowerMessage.includes("certificat")) {
      return `Vérification d'un certificat de localisation:\n\n` +
        `**Points à vérifier:**\n` +
        `• Date (moins de 10 ans, idéalement moins de 5 ans)\n` +
        `• Conformité des dimensions du terrain\n` +
        `• Empiètements éventuels\n` +
        `• Servitudes inscrites\n` +
        `• Conformité aux règlements municipaux\n` +
        `• Droits de passage\n\n` +
        `**Situations nécessitant un nouveau certificat:**\n` +
        `• Travaux majeurs effectués\n` +
        `• Plus de 10 ans d'âge\n` +
        `• Changements sur le terrain voisin\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    if (lowerMessage.includes("registre") || lowerMessage.includes("foncier")) {
      return `Vérifications au registre foncier du Québec:\n\n` +
        `**Éléments à vérifier:**\n` +
        `• Chaîne des titres (historique des propriétaires)\n` +
        `• Hypothèques existantes\n` +
        `• Servitudes enregistrées\n` +
        `• Jugements ou saisies\n` +
        `• Droits miniers ou d'exploitation\n` +
        `• Avis de préavis d'exercice\n\n` +
        `**Accès:**\n` +
        `• En ligne: registrefoncier.gouv.qc.ca\n` +
        `• Coût: environ 1$ par document consulté\n\n` +
        `⚠️ Note: Cette réponse est simulée. Le backend n'est pas connecté.`;
    }

    return `Je suis l'assistant IA de Notary Assistant.\n\n` +
      `Je peux vous aider avec:\n` +
      `• Questions sur les transactions notariales\n` +
      `• Calculs (droits de mutation, frais)\n` +
      `• Documents requis pour différents types de transactions\n` +
      `• Procédures et délais\n` +
      `• Vérifications légales\n\n` +
      `Posez-moi une question spécifique et je ferai de mon mieux pour vous aider!\n\n` +
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

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      let responseContent: string;
      let usedModel = selectedModel;

      // Try to call the real API
      try {
        const response = await chatApi.send(userMessage.content, {
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <AppShell>
      <div className="flex flex-col h-[calc(100vh-100px)]">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <MessageSquare className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Assistant IA</h1>
              <p className="text-muted-foreground">
                Posez vos questions sur les transactions notariales
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button variant="outline" size="sm" onClick={clearChat}>
                <Trash2 className="h-4 w-4 mr-2" />
                Effacer
              </Button>
            )}
          </div>
        </div>

        {/* Model Selector & Status */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <span className="font-medium">Modèle IA</span>
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
          <Select value={selectedModel} onValueChange={setSelectedModel}>
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
              Backend non connecté. Les réponses sont simulées. Démarrez le serveur backend avec{" "}
              <code className="bg-muted px-1 rounded">cd backend && uv run python main.py</code>{" "}
              pour utiliser l'IA.
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
                  Je suis votre assistant spécialisé en transactions notariales au Québec.
                  Posez-moi vos questions sur les procédures, documents requis, calculs de frais, et plus encore.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-w-2xl">
                  {SUGGESTED_QUESTIONS.map((question, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      className="text-xs text-left justify-start h-auto py-2 px-3"
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
                      className={`max-w-[80%] rounded-lg p-3 ${
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
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
                <div ref={messagesEndRef} />
              </>
            )}
          </CardContent>

          {/* Input Area */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Textarea
                placeholder="Posez votre question sur les transactions notariales..."
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
    </AppShell>
  );
}
