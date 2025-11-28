"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Send,
  Bot,
  User,
  Settings2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { LLMSettingsModal } from "./llm-settings-modal";
import { chatApi, type ChatMessage as ApiChatMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface AssistantPanelProps {
  caseId: string;
  onSendMessage?: (message: string, config: LLMConfig) => Promise<string>;
}

interface LLMConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
}

// Available LLM models (kept for reference, actual list is in LLMSettingsModal)
const LLM_MODELS = [
  {
    value: "ollama:qwen2.5:7b",
    label: "Qwen 2.5 7B (Ollama) - Recommandé",
    provider: "ollama",
  },
  {
    value: "ollama:llama3.2",
    label: "Llama 3.2 3B (Ollama) - Rapide",
    provider: "ollama",
  },
  {
    value: "ollama:mistral",
    label: "Mistral 7B (Ollama)",
    provider: "ollama",
  },
  {
    value: "ollama:llama3.1:8b",
    label: "Llama 3.1 8B (Ollama)",
    provider: "ollama",
  },
  {
    value: "anthropic:claude-sonnet-4-5-20250929",
    label: "Claude Sonnet 4.5 (Anthropic) - Production",
    provider: "anthropic",
  },
  {
    value: "anthropic:claude-sonnet-4-20250514",
    label: "Claude Sonnet 4 (Anthropic)",
    provider: "anthropic",
  },
  {
    value: "anthropic:claude-haiku-3-5-20241022",
    label: "Claude Haiku 3.5 (Anthropic) - Rapide",
    provider: "anthropic",
  },
];

export function AssistantPanel({ caseId, onSendMessage }: AssistantPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Bonjour! Je suis votre assistant IA. Comment puis-je vous aider avec ce dossier?",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [checkingBackend, setCheckingBackend] = useState(true);

  // LLM configuration
  const [config, setConfig] = useState<LLMConfig>({
    model: "ollama:qwen2.5:7b",
    temperature: 0.7,
    maxTokens: 2000,
    topP: 0.9,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Check backend connectivity on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await chatApi.health();
        setBackendConnected(true);
      } catch {
        setBackendConnected(false);
      } finally {
        setCheckingBackend(false);
      }
    };
    checkBackend();
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Format model name for display
  const getModelDisplayName = (modelId: string): string => {
    const model = LLM_MODELS.find((m) => m.value === modelId);
    if (model) {
      // Remove provider prefix and clean up label
      return model.label
        .replace(" (Ollama)", "")
        .replace(" (Anthropic)", "")
        .replace(" - Recommandé", "")
        .replace(" - Rapide", "")
        .replace(" - Production", "");
    }
    return modelId;
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: inputValue,
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentMessage = inputValue;
    setInputValue("");
    setIsLoading(true);

    try {
      let assistantResponse: string;

      if (backendConnected) {
        // Use real backend chat API
        // Build history for context
        const history: ApiChatMessage[] = messages.map((msg) => ({
          role: msg.role as "user" | "assistant",
          content: msg.content,
        }));

        // Call chat API with current model configuration
        const response = await chatApi.send(currentMessage, {
          caseId,
          model: config.model,
          history,
        });

        assistantResponse = response.message;
      } else {
        // Simulated response when backend is not available
        await new Promise((resolve) => setTimeout(resolve, 1000));
        assistantResponse = `Le backend n'est pas disponible. Démarrez le serveur backend pour utiliser l'assistant IA. Votre question était: "${currentMessage}"`;
      }

      const assistantMessage: Message = {
        role: "assistant",
        content: assistantResponse,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Erreur: ${error instanceof Error ? error.message : "Erreur inconnue"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full border-l">
      {/* Header */}
      <div className="p-4 border-b bg-background flex items-center justify-between">
        <div className="flex flex-col">
          <h2 className="text-xl font-bold">Assistant IA</h2>
          <span className="text-xs text-muted-foreground/60">
            {getModelDisplayName(config.model)}
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSettingsModalOpen(true)}
          title="Paramètres LLM"
        >
          <Settings2 className="h-5 w-5" />
        </Button>
      </div>

      {/* Backend status warning */}
      {checkingBackend && (
        <div className="p-4 border-b">
          <Alert>
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertDescription>
              Vérification de la connexion au backend...
            </AlertDescription>
          </Alert>
        </div>
      )}
      {!checkingBackend && !backendConnected && (
        <div className="p-4 border-b">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Backend non connecté. Démarrez le serveur backend et Ollama pour utiliser l'assistant IA.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {message.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <Bot className="h-5 w-5 text-primary-foreground" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
            {message.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                <User className="h-5 w-5" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
              <Bot className="h-5 w-5 text-primary-foreground" />
            </div>
            <div className="bg-muted rounded-lg p-4">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-background">
        <Textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Posez une question... (Enter pour envoyer, Shift+Enter pour nouvelle ligne)"
          className="min-h-[80px] max-h-[200px] resize-none"
          disabled={isLoading}
        />
        <p className="text-xs text-muted-foreground mt-2">
          Enter pour envoyer • Shift+Enter pour nouvelle ligne
        </p>
      </div>

      {/* LLM Settings Modal */}
      <LLMSettingsModal
        open={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        config={config}
        onConfigChange={setConfig}
      />
    </div>
  );
}
