"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface LLMConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
}

interface LLMSettingsModalProps {
  open: boolean;
  onClose: () => void;
  config: LLMConfig;
  onConfigChange: (config: LLMConfig) => void;
}

// Available LLM models
const LLM_MODELS = [
  // === MLX (Apple Silicon) ===
  {
    value: "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit",
    label: "🍎 Qwen 2.5 3B (MLX) - Recommandé Apple Silicon",
  },
  {
    value: "mlx:mlx-community/Llama-3.2-3B-Instruct-4bit",
    label: "🍎 Llama 3.2 3B (MLX) - Ultra-rapide",
  },
  {
    value: "mlx:mlx-community/Mistral-7B-Instruct-v0.3-4bit",
    label: "🍎 Mistral 7B (MLX) - Qualité maximale",
  },
  // === Ollama (Cross-platform) ===
  {
    value: "ollama:qwen2.5:7b",
    label: "Qwen 2.5 7B (Ollama)",
  },
  {
    value: "ollama:llama3.2",
    label: "Llama 3.2 3B (Ollama) - Rapide",
  },
  {
    value: "ollama:mistral",
    label: "Mistral 7B (Ollama)",
  },
  {
    value: "ollama:llama3.1:8b",
    label: "Llama 3.1 8B (Ollama)",
  },
  // === Claude (Anthropic API) ===
  {
    value: "anthropic:claude-sonnet-4-5-20250929",
    label: "Claude Sonnet 4.5 (Anthropic) - Production",
  },
  {
    value: "anthropic:claude-sonnet-4-20250514",
    label: "Claude Sonnet 4 (Anthropic)",
  },
  {
    value: "anthropic:claude-haiku-3-5-20241022",
    label: "Claude Haiku 3.5 (Anthropic) - Rapide",
  },
];

export function LLMSettingsModal({
  open,
  onClose,
  config,
  onConfigChange,
}: LLMSettingsModalProps) {
  // Local state to track changes before saving
  const [localConfig, setLocalConfig] = useState<LLMConfig>(config);

  // Reset local config when modal opens with new config
  useEffect(() => {
    if (open) {
      setLocalConfig(config);
    }
  }, [open, config]);

  const handleCancel = () => {
    setLocalConfig(config); // Reset to original
    onClose();
  };

  const handleSave = () => {
    onConfigChange(localConfig);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleCancel}>
      <DialogContent className="max-w-md [&>button]:hidden">
        <DialogHeader>
          <DialogTitle>Paramètres LLM</DialogTitle>
          <DialogDescription>
            Configurez le modèle et les paramètres de génération. 🍎 = MLX (Apple Silicon)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Model selection */}
          <div className="space-y-2">
            <Label htmlFor="model">Modèle</Label>
            <Select
              value={localConfig.model}
              onValueChange={(value) =>
                setLocalConfig({ ...localConfig, model: value })
              }
            >
              <SelectTrigger id="model">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LLM_MODELS.map((model) => (
                  <SelectItem key={model.value} value={model.value}>
                    {model.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="temperature">Température</Label>
              <span className="text-sm text-muted-foreground">
                {localConfig.temperature.toFixed(1)}
              </span>
            </div>
            <Slider
              id="temperature"
              min={0}
              max={2}
              step={0.1}
              value={[localConfig.temperature]}
              onValueChange={(value) =>
                setLocalConfig({ ...localConfig, temperature: value[0] })
              }
            />
            <p className="text-xs text-muted-foreground">
              Plus élevé = plus créatif, plus bas = plus déterministe
            </p>
          </div>

          {/* Max Tokens */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="maxTokens">Max tokens</Label>
              <span className="text-sm text-muted-foreground">
                {localConfig.maxTokens}
              </span>
            </div>
            <Slider
              id="maxTokens"
              min={100}
              max={4000}
              step={100}
              value={[localConfig.maxTokens]}
              onValueChange={(value) =>
                setLocalConfig({ ...localConfig, maxTokens: value[0] })
              }
            />
            <p className="text-xs text-muted-foreground">
              Longueur maximale de la réponse
            </p>
          </div>

          {/* Top P */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="topP">Top P</Label>
              <span className="text-sm text-muted-foreground">
                {localConfig.topP.toFixed(2)}
              </span>
            </div>
            <Slider
              id="topP"
              min={0}
              max={1}
              step={0.05}
              value={[localConfig.topP]}
              onValueChange={(value) =>
                setLocalConfig({ ...localConfig, topP: value[0] })
              }
            />
            <p className="text-xs text-muted-foreground">
              Diversité des tokens considérés
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Annuler
          </Button>
          <Button onClick={handleSave}>
            Sauvegarder
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
