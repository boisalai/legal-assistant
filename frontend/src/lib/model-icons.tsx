/**
 * Utility functions for displaying model provider logos
 *
 * This module provides consistent icon rendering for AI model providers
 * based on the model name/value, detecting specific models like Llama, Qwen, Mistral, etc.
 */

import AnthropicLogo from "@/svg/anthropic.svg";
import OllamaLogo from "@/svg/ollama.svg";
import OpenAILogo from "@/svg/openai.svg";
import HuggingFaceLogo from "@/svg/hf-logo-colored.svg";
import MetaLogo from "@/svg/meta.svg";
import MistralLogo from "@/svg/mistral.svg";
import QwenLogo from "@/svg/qwen.svg";
import GeminiLogo from "@/svg/gemini.svg";

interface ModelIconProps {
  modelValue: string;
  className?: string;
}

/**
 * Get the appropriate icon component for a model based on its value/name
 *
 * This function intelligently detects the model brand (Qwen, Llama, Mistral)
 * regardless of the provider (Ollama, MLX, etc.) and returns the appropriate logo.
 *
 * @param modelValue - The full model identifier (e.g., "ollama:qwen2.5:7b", "mlx:Llama-3.2-3B-Instruct-4bit")
 * @param className - Optional CSS classes to apply to the icon
 * @returns JSX element with the appropriate logo
 */
export function getModelIcon(modelValue: string, className: string = "h-4 w-4 flex-shrink-0") {
  const modelLower = modelValue.toLowerCase();

  // Check for specific model brands regardless of provider
  if (modelLower.includes('qwen')) {
    return <QwenLogo className={className} />;
  }
  if (modelLower.includes('llama')) {
    return <MetaLogo className={className} />;
  }
  if (modelLower.includes('mistral')) {
    return <MistralLogo className={className} />;
  }

  // Fallback to provider-based icons
  if (modelLower.startsWith('anthropic:') || modelLower.includes('claude')) {
    return <AnthropicLogo className={className} />;
  }
  if (modelLower.startsWith('openai:') || modelLower.includes('gpt')) {
    return <OpenAILogo className={className} />;
  }
  if (modelLower.startsWith('gemini:') || modelLower.includes('gemini')) {
    return <GeminiLogo className={className} />;
  }
  if (modelLower.startsWith('mlx:')) {
    return <HuggingFaceLogo className={className} />;
  }

  // Default to Ollama for unknown models
  return <OllamaLogo className={className} />;
}

/**
 * Get provider icon based on provider name (legacy function for backwards compatibility)
 *
 * @param provider - Provider name (e.g., "anthropic", "ollama", "mlx")
 * @param className - Optional CSS classes to apply to the icon
 * @returns JSX element with the appropriate logo
 */
export function getProviderIcon(provider: string, className: string = "h-4 w-4 flex-shrink-0") {
  const normalizedProvider = provider.toLowerCase();

  switch (normalizedProvider) {
    case "anthropic":
    case "claude":
      return <AnthropicLogo className={className} />;
    case "openai":
      return <OpenAILogo className={className} />;
    case "gemini":
    case "google":
      return <GeminiLogo className={className} />;
    case "ollama":
      return <OllamaLogo className={className} />;
    case "mlx":
      return <HuggingFaceLogo className={className} />;
    default:
      return <OllamaLogo className={className} />;
  }
}
