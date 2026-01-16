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

import { getModelIcon } from "@/lib/model-icons";
import {
  LLM_MODELS,
  LLMConfig,
  DEFAULT_LLM_CONFIG,
  loadLLMConfig,
  saveLLMConfig,
} from "@/lib/llm-models";

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
                {getModelIcon(currentModel.value, `h-4 w-4 flex-shrink-0 ${variant === "header" ? "text-foreground" : "text-white"}`)}
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
                  {getModelIcon(model.value, "h-4 w-4 flex-shrink-0 text-foreground")}
                  <span>{model.label}</span>
                </div>
              </SelectItem>
            ))}

            {/* Google models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
              Google (Gemini API)
            </div>
            {LLM_MODELS.filter((m) => m.provider === "google").map((model) => (
              <SelectItem key={model.value} value={model.value}>
                <div className="flex items-center gap-2">
                  {getModelIcon(model.value, "h-4 w-4 flex-shrink-0 text-foreground")}
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
                  {getModelIcon(model.value, "h-4 w-4 flex-shrink-0 text-foreground")}
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
                  {getModelIcon(model.value, "h-4 w-4 flex-shrink-0 text-foreground")}
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
