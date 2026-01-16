/**
 * Shared LLM model configuration
 * Single source of truth for available LLM models across the application
 */

export interface ModelInfo {
  value: string;
  label: string;
  provider: "ollama" | "anthropic" | "mlx" | "google";
}

export const LLM_MODELS: ModelInfo[] = [
  // === Google (Gemini API) ===
  {
    value: "google:gemini-1.5-pro",
    label: "Google Gemini 1.5 Pro",
    provider: "google",
  },
  {
    value: "google:gemini-1.5-flash",
    label: "Google Gemini 1.5 Flash",
    provider: "google",
  },
  {
    value: "google:gemini-2.0-flash-exp",
    label: "Google Gemini 2.0 Flash (Exp)",
    provider: "google",
  },

  // === Claude (Anthropic API) ===
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

  // === MLX (Apple Silicon) ===
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

  // === Ollama (Cross-platform) ===
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
];

export interface LLMConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
}

export const LLM_CONFIG_STORAGE_KEY = "legal-assistant-llm-config";

export const DEFAULT_LLM_CONFIG: LLMConfig = {
  model: "ollama:qwen2.5:7b",
  temperature: 0.7,
  maxTokens: 2000,
  topP: 0.9,
};

export function loadLLMConfig(): LLMConfig {
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

export function saveLLMConfig(config: LLMConfig): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LLM_CONFIG_STORAGE_KEY, JSON.stringify(config));
    // Dispatch custom event to notify other components
    window.dispatchEvent(new CustomEvent("llm-config-changed", { detail: config }));
  } catch (e) {
    console.warn("Failed to save LLM config to localStorage:", e);
  }
}

export function getProviderLabel(provider: string): string {
  switch (provider) {
    case "anthropic":
      return "Claude";
    case "google":
      return "Google";
    case "mlx":
      return "MLX";
    case "ollama":
    default:
      return "Ollama";
  }
}

export function getModelDisplayName(modelId: string): string {
  const model = LLM_MODELS.find((m) => m.value === modelId);
  if (model) {
    return model.label;
  }
  return modelId;
}
