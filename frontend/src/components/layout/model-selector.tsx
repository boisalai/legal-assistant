"use client";

import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Image from "next/image";

// Import SVG logos as React components
import ClaudeLogo from "@/svg/claude-anthropic.svg";
import OllamaLogo from "@/svg/ollama.svg";
import HuggingFaceLogo from "@/svg/hf-logo-colored.svg";

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
    value: "mlx:mlx-community/Qwen2.5-7B-Instruct-4bit",
    label: "MLX Qwen2.5-7B-Instruct-4bit",
    provider: "mlx",
  },
  {
    value: "mlx:mlx-community/Qwen2.5-14B-Instruct-4bit",
    label: "MLX Qwen2.5-14B-Instruct-4bit",
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

function getProviderIcon(provider: string, inDropdown: boolean = false) {
  switch (provider) {
    case "anthropic":
      return <ClaudeLogo className="h-4 w-4 flex-shrink-0" />;
    case "mlx":
      return <HuggingFaceLogo className={`h-4 w-4 flex-shrink-0 ${inDropdown ? 'text-foreground' : 'text-white'}`} />;
    case "ollama":
    default:
      return <OllamaLogo className={`h-4 w-4 flex-shrink-0 ${inDropdown ? 'text-foreground' : 'text-white'}`} />;
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
  variant?: "sidebar" | "header";
}

export function ModelSelector({ collapsed = false, variant = "sidebar" }: ModelSelectorProps) {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_LLM_CONFIG);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const savedConfig = loadLLMConfig();
    setConfig(savedConfig);

    // Listen for config changes from other components
    const handleConfigChange = (event: CustomEvent<LLMConfig>) => {
      setConfig(event.detail);
    };

    window.addEventListener("llm-config-changed", handleConfigChange as EventListener);

    return () => {
      window.removeEventListener("llm-config-changed", handleConfigChange as EventListener);
    };
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

  const triggerClassName = variant === "header"
    ? "h-9 w-auto max-w-[420px] bg-background border-input text-foreground hover:bg-accent hover:text-accent-foreground"
    : "h-auto min-h-[36px] bg-sidebar border-sidebar-border text-sidebar-foreground hover:bg-sidebar-accent";

  const containerClassName = variant === "header" ? "" : "px-2 pb-2";

  return (
    <div className={containerClassName}>
      <Select value={config.model} onValueChange={handleModelChange}>
        <SelectTrigger className={triggerClassName}>
          <SelectValue>
            {currentModel && (
              <div className="flex items-center gap-2 py-1">
                {getProviderIcon(currentModel.provider, variant === "sidebar" ? false : true)}
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
                  {getProviderIcon(model.provider, true)}
                  <span>{model.label}</span>
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
                  {getProviderIcon(model.provider, true)}
                  <span>{model.label}</span>
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
                  {getProviderIcon(model.provider, true)}
                  <span>{model.label}</span>
                </div>
              </SelectItem>
            ))}
          </div>
        </SelectContent>
      </Select>
    </div>
  );
}
