"use client";

import { useState, useEffect, useCallback } from "react";

const LLM_SETTINGS_STORAGE_KEY = "legal-assistant-llm-settings";

export interface LLMSettings {
  modelId: string;
  temperature: number;
  maxTokens: number;
  topP: number;
}

const DEFAULT_SETTINGS: LLMSettings = {
  modelId: "ollama:qwen2.5:7b",
  temperature: 0.7,
  maxTokens: 2000,
  topP: 0.9,
};

function loadSettings(): LLMSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const stored = localStorage.getItem(LLM_SETTINGS_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_SETTINGS, ...parsed };
    }
  } catch (e) {
    console.warn("Failed to load LLM settings from localStorage:", e);
  }
  return DEFAULT_SETTINGS;
}

function saveSettings(settings: LLMSettings): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LLM_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    console.warn("Failed to save LLM settings to localStorage:", e);
  }
}

export function useLLMSettings() {
  const [settings, setSettings] = useState<LLMSettings>(DEFAULT_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage on mount (client-side only)
  useEffect(() => {
    const savedSettings = loadSettings();
    setSettings(savedSettings);
    setIsLoaded(true);
  }, []);

  // Update a single setting and persist
  const updateSetting = useCallback(<K extends keyof LLMSettings>(
    key: K,
    value: LLMSettings[K]
  ) => {
    setSettings((prev) => {
      const newSettings = { ...prev, [key]: value };
      saveSettings(newSettings);
      return newSettings;
    });
  }, []);

  // Update all settings and persist
  const updateSettings = useCallback((newSettings: Partial<LLMSettings>) => {
    setSettings((prev) => {
      const merged = { ...prev, ...newSettings };
      saveSettings(merged);
      return merged;
    });
  }, []);

  // Reset to defaults
  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
  }, []);

  return {
    settings,
    isLoaded,
    updateSetting,
    updateSettings,
    resetSettings,
    // Convenience getters
    modelId: settings.modelId,
    temperature: settings.temperature,
    maxTokens: settings.maxTokens,
    topP: settings.topP,
  };
}
