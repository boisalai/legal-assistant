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
  Copy,
  Check,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Markdown } from "@/components/ui/markdown";
import { chatApi, healthApi, type ChatMessage as ApiChatMessage, type DocumentSource } from "@/lib/api";
import {
  LLM_MODELS,
  LLMConfig,
  DEFAULT_LLM_CONFIG,
  loadLLMConfig,
  saveLLMConfig,
} from "@/lib/llm-models";
import { useLocale as useCustomLocale } from "@/i18n/client";
import { useTranslations, useLocale } from "next-intl";

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
  // Get current locale - use next-intl's useLocale for translations
  const locale = useLocale();
  const t = useTranslations();
  // Keep custom locale hook for API calls
  const { locale: apiLocale } = useCustomLocale();

  // If messages/setMessages are provided as props, use them (controlled mode)
  // Otherwise, use local state (uncontrolled mode)
  const [internalMessages, internalSetMessages] = useState<Message[]>([]);

  const messages = controlledMessages ?? internalMessages;
  const setMessages = controlledSetMessages ?? internalSetMessages;

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [checkingBackend, setCheckingBackend] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [lastLocale, setLastLocale] = useState<string | null>(null);

  // LLM configuration - initialized from localStorage
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_LLM_CONFIG);
  const [configLoaded, setConfigLoaded] = useState(false);

  // Initialize greeting message on mount and update when locale changes
  useEffect(() => {
    if (!controlledMessages) {
      // Only update greeting if it's the first message and locale changed
      const isFirstMessageGreeting = internalMessages.length <= 1;
      if (isFirstMessageGreeting && locale !== lastLocale) {
        const welcomeMessage = t("assistant.welcome");
        internalSetMessages([{ role: "assistant", content: welcomeMessage }]);
        setLastLocale(locale);
      }
    }
  }, [controlledMessages, locale, lastLocale, t, internalMessages.length]);

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
            language: apiLocale,
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
                          { role: "assistant", content: t("assistant.error", { message: data.error }) },
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
            language: apiLocale,
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
          content: t("assistant.backendUnavailable", { message: currentMessage }),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: t("assistant.error", { message: error instanceof Error ? error.message : "Unknown error" }),
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

  const handleCopyMessage = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div className="flex flex-col h-full border-l overflow-hidden">
      {/* Header */}
      <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
        <h2 className="text-xl font-bold">{t("assistant.title")}</h2>
      </div>

      {/* Backend status warning */}
      {checkingBackend && (
        <div className="p-4 border-b shrink-0">
          <Alert>
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertDescription>
              {t("assistant.checkingBackend")}
            </AlertDescription>
          </Alert>
        </div>
      )}
      {!checkingBackend && !backendConnected && (
        <div className="p-4 border-b shrink-0">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {t("assistant.backendNotConnected")}
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
                className={`rounded-lg px-3 py-2 relative group ${
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
                      onClick={() => handleCopyMessage(message.content, idx)}
                      title={t("assistant.copyMarkdown")}
                    >
                      {copiedIndex === idx ? (
                        <Check className="h-3.5 w-3.5 text-green-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </>
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
            placeholder={t("assistant.placeholder")}
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
    </div>
  );
}
