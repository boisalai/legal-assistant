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
  Brain,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { LLMSettingsModal } from "./llm-settings-modal";
import { Markdown } from "@/components/ui/markdown";
import { chatApi, healthApi, type ChatMessage as ApiChatMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface AssistantPanelProps {
  caseId: string;
  onSendMessage?: (message: string, config: LLMConfig) => Promise<string>;
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
  hasDocuments?: boolean;
  onDocumentCreated?: () => void;  // Called when a new document is created via chat
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
  } catch (e) {
    console.warn("Failed to save LLM config to localStorage:", e);
  }
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

export function AssistantPanel({ caseId, onSendMessage, onAnalyze, isAnalyzing, hasDocuments, onDocumentCreated }: AssistantPanelProps) {
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

  // LLM configuration - initialized from localStorage
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_LLM_CONFIG);
  const [configLoaded, setConfigLoaded] = useState(false);

  // Load config from localStorage on mount (client-side only)
  useEffect(() => {
    const savedConfig = loadLLMConfig();
    setConfig(savedConfig);
    setConfigLoaded(true);
  }, []);

  // Save config to localStorage whenever it changes
  const handleConfigChange = (newConfig: LLMConfig) => {
    setConfig(newConfig);
    saveLLMConfig(newConfig);
  };

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
    <div className="flex flex-col h-full border-l">
      {/* Header */}
      <div className="p-4 border-b bg-background flex items-center justify-between">
        <div className="flex flex-col">
          <h2 className="text-xl font-bold">Assistant IA</h2>
          <span className="text-xs text-muted-foreground/60">
            {getModelDisplayName(config.model)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={onAnalyze}
            disabled={isAnalyzing || !hasDocuments}
            title={hasDocuments ? "Analyser le dossier" : "Ajoutez des documents pour analyser"}
          >
            {isAnalyzing ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Brain className="h-5 w-5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSettingsModalOpen(true)}
            title="Paramètres LLM"
          >
            <Settings2 className="h-5 w-5" />
          </Button>
        </div>
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
              className={`max-w-[80%] rounded-lg px-3 py-2 ${
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
          placeholder="Posez une question..."
          className="min-h-[80px] max-h-[200px] resize-none"
          disabled={isLoading}
        />
      </div>

      {/* LLM Settings Modal */}
      <LLMSettingsModal
        open={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        config={config}
        onConfigChange={handleConfigChange}
      />
    </div>
  );
}
