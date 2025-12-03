"use client";

import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Cpu, Cloud, Zap } from "lucide-react";

export interface LLMConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
}

interface ModelInfo {
  value: string;
  label: string;
  provider: "ollama" | "anthropic" | "mlx";
}

const LLM_MODELS: ModelInfo[] = [
  // Ollama models
  {
    value: "ollama:qwen2.5:7b",
    label: "Qwen 2.5 7B",
    provider: "ollama",
  },
  {
    value: "ollama:llama3.2",
    label: "Llama 3.2 3B",
    provider: "ollama",
  },
  {
    value: "ollama:mistral",
    label: "Mistral 7B",
    provider: "ollama",
  },
  {
    value: "ollama:llama3.1:8b",
    label: "Llama 3.1 8B",
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
  {
    value: "anthropic:claude-haiku-3-5-20241022",
    label: "Claude Haiku 3.5",
    provider: "anthropic",
  },
  // MLX models
  {
    value: "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit",
    label: "MLX Qwen 2.5 3B",
    provider: "mlx",
  },
  {
    value: "mlx:mlx-community/Llama-3.2-3B-Instruct-4bit",
    label: "MLX Llama 3.2 3B",
    provider: "mlx",
  },
  {
    value: "mlx:mlx-community/Mistral-7B-Instruct-v0.3-4bit",
    label: "MLX Mistral 7B",
    provider: "mlx",
  },
];

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

function getProviderIcon(provider: string) {
  switch (provider) {
    case "anthropic":
      return <Cloud className="h-3.5 w-3.5" />;
    case "mlx":
      return <Zap className="h-3.5 w-3.5" />;
    case "ollama":
    default:
      return <Cpu className="h-3.5 w-3.5" />;
  }
}

function getProviderLabel(provider: string) {
  switch (provider) {
    case "anthropic":
      return "Claude";
    case "mlx":
      return "MLX";
    case "ollama":
    default:
      return "Ollama";
  }
}

interface ModelSelectorProps {
  collapsed?: boolean;
}

export function ModelSelector({ collapsed = false }: ModelSelectorProps) {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_LLM_CONFIG);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const savedConfig = loadLLMConfig();
    setConfig(savedConfig);
  }, []);

  const handleModelChange = (modelId: string) => {
    const newConfig = { ...config, model: modelId };
    setConfig(newConfig);
    saveLLMConfig(newConfig);
  };

  const currentModel = LLM_MODELS.find((m) => m.value === config.model);

  if (!mounted) {
    return null; // Avoid hydration mismatch
  }

  if (collapsed) {
    return null; // Don't show when sidebar is collapsed
  }

  return (
    <div className="px-2 pb-2">
      <Select value={config.model} onValueChange={handleModelChange}>
        <SelectTrigger className="h-9 bg-sidebar-accent/50 border-sidebar-border text-sidebar-foreground hover:bg-sidebar-accent">
          <SelectValue>
            {currentModel && (
              <div className="flex items-center gap-2">
                {getProviderIcon(currentModel.provider)}
                <span className="text-xs font-medium truncate">
                  {currentModel.label}
                </span>
              </div>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {/* Group by provider */}
          <div className="space-y-1">
            {/* Claude models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
              Claude (API)
            </div>
            {LLM_MODELS.filter((m) => m.provider === "anthropic").map((model) => (
              <SelectItem key={model.value} value={model.value}>
                <div className="flex items-center gap-2">
                  {getProviderIcon(model.provider)}
                  <span>{model.label}</span>
                  <Badge variant="outline" className="text-xs">
                    {getProviderLabel(model.provider)}
                  </Badge>
                </div>
              </SelectItem>
            ))}

            {/* MLX models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
              MLX (Apple Silicon)
            </div>
            {LLM_MODELS.filter((m) => m.provider === "mlx").map((model) => (
              <SelectItem key={model.value} value={model.value}>
                <div className="flex items-center gap-2">
                  {getProviderIcon(model.provider)}
                  <span>{model.label}</span>
                  <Badge variant="outline" className="text-xs">
                    {getProviderLabel(model.provider)}
                  </Badge>
                </div>
              </SelectItem>
            ))}

            {/* Ollama models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
              Ollama (Local)
            </div>
            {LLM_MODELS.filter((m) => m.provider === "ollama").map((model) => (
              <SelectItem key={model.value} value={model.value}>
                <div className="flex items-center gap-2">
                  {getProviderIcon(model.provider)}
                  <span>{model.label}</span>
                  <Badge variant="outline" className="text-xs">
                    {getProviderLabel(model.provider)}
                  </Badge>
                </div>
              </SelectItem>
            ))}
          </div>
        </SelectContent>
      </Select>
    </div>
  );
}
