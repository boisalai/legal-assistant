"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Send,
  Bot,
  User,
  Loader2,
  AlertCircle,
  MoreVertical,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Markdown } from "@/components/ui/markdown";
import { chatApi, healthApi, type ChatMessage as ApiChatMessage, type DocumentSource } from "@/lib/api";
import { LLMSettingsModal } from "./llm-settings-modal";

// Import SVG logos as React components
import ClaudeLogo from "@/svg/claude-anthropic.svg";
import OllamaLogo from "@/svg/ollama.svg";
import HuggingFaceLogo from "@/svg/hf-logo-colored.svg";

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: DocumentSource[];
}

interface AssistantPanelProps {
  caseId: string;
  onSendMessage?: (message: string, config: LLMConfig) => Promise<string>;
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
  hasDocuments?: boolean;
  onDocumentCreated?: () => void;  // Called when a new document is created via chat
  messages?: Message[];  // Optional: if provided, messages state is controlled by parent
  setMessages?: React.Dispatch<React.SetStateAction<Message[]>>;  // Optional: if provided, messages state is controlled by parent
}

interface LLMConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
}

const LLM_CONFIG_STORAGE_KEY = "legal-assistant-llm-config";

const DEFAULT_LLM_CONFIG: LLMConfig = {
  model: "ollama:qwen2.5:7b",
  temperature: 0.7,
  maxTokens: 2000,
  topP: 0.9,
};

function loadLLMConfig(): LLMConfig {
  if (typeof window === "undefined") return DEFAULT_LLM_CONFIG;
  try {
    const stored = localStorage.getItem(LLM_CONFIG_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_LLM_CONFIG, ...parsed };
    }
  } catch (e) {
    console.warn("Failed to load LLM config from localStorage:", e);
  }
  return DEFAULT_LLM_CONFIG;
}

function saveLLMConfig(config: LLMConfig): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LLM_CONFIG_STORAGE_KEY, JSON.stringify(config));
    // Dispatch custom event to notify other components
    window.dispatchEvent(new CustomEvent("llm-config-changed", { detail: config }));
  } catch (e) {
    console.warn("Failed to save LLM config to localStorage:", e);
  }
}

// Available LLM models (synced with ModelSelector)
const LLM_MODELS = [
  // Ollama models
  {
    value: "ollama:qwen2.5:7b",
    label: "Ollama Qwen 2.5 7B",
    provider: "ollama",
  },
  {
    value: "ollama:llama3.2",
    label: "Ollama Llama 3.2 3B",
    provider: "ollama",
  },
  {
    value: "ollama:mistral",
    label: "Ollama Mistral 7B",
    provider: "ollama",
  },
  {
    value: "ollama:llama3.1:8b",
    label: "Ollama Llama 3.1 8B",
    provider: "ollama",
  },
  // Anthropic models
  {
    value: "anthropic:claude-sonnet-4-5-20250929",
    label: "Claude Sonnet 4.5",
    provider: "anthropic",
  },
  {
    value: "anthropic:claude-sonnet-4-20250514",
    label: "Claude Sonnet 4",
    provider: "anthropic",
  },
  // MLX models
  {
    value: "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit",
    label: "MLX Qwen2.5-3B-Instruct-4bit",
    provider: "mlx",
  },
  {
    value: "mlx:mlx-community/Llama-3.2-3B-Instruct-4bit",
    label: "MLX Llama-3.2-3B-Instruct-4bit",
    provider: "mlx",
  },
  {
    value: "mlx:mlx-community/Mistral-7B-Instruct-v0.3-4bit",
    label: "MLX Mistral-7B-Instruct-v0.3-4bit",
    provider: "mlx",
  },
  {
    value: "mlx:mlx-community/Ministral-3-14B-Reasoning-2512-4bit",
    label: "MLX Ministral-3 14B Reasoning",
    provider: "mlx",
  },
];

export function AssistantPanel({
  caseId,
  onSendMessage,
  onAnalyze,
  isAnalyzing,
  hasDocuments,
  onDocumentCreated,
  messages: controlledMessages,
  setMessages: controlledSetMessages
}: AssistantPanelProps) {
  // If messages/setMessages are provided as props, use them (controlled mode)
  // Otherwise, use local state (uncontrolled mode)
  const [internalMessages, internalSetMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Bonjour! Je suis votre assistant IA. Comment puis-je vous aider avec ce dossier?",
    },
  ]);

  const messages = controlledMessages ?? internalMessages;
  const setMessages = controlledSetMessages ?? internalSetMessages;

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [checkingBackend, setCheckingBackend] = useState(true);

  // LLM configuration - initialized from localStorage
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_LLM_CONFIG);
  const [configLoaded, setConfigLoaded] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Load config from localStorage on mount (client-side only)
  useEffect(() => {
    const savedConfig = loadLLMConfig();
    setConfig(savedConfig);
    setConfigLoaded(true);

    // Listen for config changes from ModelSelector
    const handleConfigChanged = (event: CustomEvent<LLMConfig>) => {
      setConfig(event.detail);
    };

    window.addEventListener("llm-config-changed", handleConfigChanged as EventListener);
    return () => {
      window.removeEventListener("llm-config-changed", handleConfigChanged as EventListener);
    };
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Check backend connectivity on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await healthApi.check();
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

  // Get provider info from model ID
  const getProviderInfo = (modelId: string): { provider: string; icon: React.ReactNode; label: string } => {
    if (modelId.startsWith("anthropic:")) {
      return {
        provider: "anthropic",
        icon: <ClaudeLogo className="h-4 w-4 flex-shrink-0" />,
        label: "Claude"
      };
    } else if (modelId.startsWith("mlx:")) {
      return {
        provider: "mlx",
        icon: <HuggingFaceLogo className="h-4 w-4 flex-shrink-0 text-foreground" />,
        label: "MLX"
      };
    } else {
      return {
        provider: "ollama",
        icon: <OllamaLogo className="h-4 w-4 flex-shrink-0 text-foreground" />,
        label: "Ollama"
      };
    }
  };

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

  // Check if message looks like a transcription request
  const isTranscriptionRequest = (message: string): boolean => {
    const keywords = ["transcri", "audio", "fichier audio", "enregistrement", "dictée", "voix"];
    return keywords.some(kw => message.toLowerCase().includes(kw));
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
      if (backendConnected) {
        // Check if this might be a transcription request - use streaming
        const useStreaming = isTranscriptionRequest(currentMessage);

        if (useStreaming) {
          // Use streaming API for transcription requests
          const history: ApiChatMessage[] = messages.map((msg) => ({
            role: msg.role as "user" | "assistant",
            content: msg.content,
          }));

          const response = await chatApi.stream(currentMessage, {
            caseId,
            model: config.model,
            history,
          });

          // Read SSE stream
          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error("No response body");
          }

          const decoder = new TextDecoder();

          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              const text = decoder.decode(value);
              const lines = text.split("\n");

              let eventType = "";
              for (const line of lines) {
                if (line.startsWith("event: ")) {
                  eventType = line.slice(7).trim();
                } else if (line.startsWith("data: ")) {
                  try {
                    const data = JSON.parse(line.slice(6));

                    switch (eventType) {
                      case "complete_message":
                        // Add each complete message as a separate assistant message
                        setMessages((prev) => [
                          ...prev,
                          { role: "assistant", content: data.content },
                        ]);
                        break;
                      case "document_created":
                        // Notify parent that a document was created
                        if (onDocumentCreated) {
                          onDocumentCreated();
                        }
                        break;
                      case "error":
                        setMessages((prev) => [
                          ...prev,
                          { role: "assistant", content: `Erreur: ${data.error}` },
                        ]);
                        break;
                      case "done":
                        // Streaming complete
                        break;
                    }
                  } catch {
                    // Ignore JSON parse errors for incomplete data
                  }
                }
              }
            }
          } finally {
            reader.releaseLock();
          }
        } else {
          // Use regular chat API for non-transcription requests
          const history: ApiChatMessage[] = messages.map((msg) => ({
            role: msg.role as "user" | "assistant",
            content: msg.content,
          }));

          const response = await chatApi.send(currentMessage, {
            caseId,
            model: config.model,
            history,
          });

          const assistantMessage: Message = {
            role: "assistant",
            content: response.message,
            sources: response.sources || [],
          };

          setMessages((prev) => [...prev, assistantMessage]);

          // If a document was created during the chat (e.g., transcription), notify parent
          if (response.document_created && onDocumentCreated) {
            onDocumentCreated();
          }
        }
      } else {
        // Simulated response when backend is not available
        await new Promise((resolve) => setTimeout(resolve, 1000));
        const assistantMessage: Message = {
          role: "assistant",
          content: `Le backend n'est pas disponible. Démarrez le serveur backend pour utiliser l'assistant IA. Votre question était: "${currentMessage}"`,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
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
    <div className="flex flex-col h-full border-l overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-background flex items-center justify-between shrink-0">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-bold">Assistant IA</h2>
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            {getProviderInfo(config.model).icon}
            <span>
              {getModelDisplayName(config.model)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowSettingsModal(true)}
            title="Paramètres LLM"
          >
            <MoreVertical className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Backend status warning */}
      {checkingBackend && (
        <div className="p-4 border-b shrink-0">
          <Alert>
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertDescription>
              Vérification de la connexion au backend...
            </AlertDescription>
          </Alert>
        </div>
      )}
      {!checkingBackend && !backendConnected && (
        <div className="p-4 border-b shrink-0">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Backend non connecté. Démarrez le serveur backend et Ollama pour utiliser l'assistant IA.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
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
            <div className="flex flex-col gap-2 max-w-[80%]">
              <div
                className={`rounded-lg px-3 py-2 ${
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                {message.role === "assistant" ? (
                  <Markdown className="text-sm">{message.content}</Markdown>
                ) : (
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                )}
              </div>
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
      <div className="p-4 border-t bg-background shrink-0">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Posez une question... (Enter pour envoyer, Shift+Enter pour nouvelle ligne)"
            className="min-h-[60px] max-h-[120px] resize-none flex-1"
            disabled={isLoading}
          />
          <Button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            size="icon"
            className="h-[60px] w-[60px] shrink-0"
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* LLM Settings Modal */}
      <LLMSettingsModal
        open={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        config={config}
        onConfigChange={(newConfig) => {
          setConfig(newConfig);
          saveLLMConfig(newConfig);
        }}
      />
    </div>
  );
}
