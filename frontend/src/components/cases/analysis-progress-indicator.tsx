"use client";

import { useEffect, useState, useCallback } from "react";
import { analysisApi } from "@/lib/api";
import {
  FileSearch,
  Brain,
  Sparkles,
  CheckCircle2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AnalysisStep {
  id: string;
  label: string;
  icon: React.ReactNode;
  status: "pending" | "active" | "complete" | "error";
}

interface AnalysisProgressIndicatorProps {
  caseId: string;
  isAnalyzing: boolean;
  onComplete?: () => void;
}

export function AnalysisProgressIndicator({
  caseId,
  isAnalyzing,
  onComplete,
}: AnalysisProgressIndicatorProps) {
  const [steps, setSteps] = useState<AnalysisStep[]>([
    { id: "extract", label: "Extraction du texte", icon: <FileSearch className="h-3.5 w-3.5" />, status: "pending" },
    { id: "embed", label: "Indexation vectorielle", icon: <Sparkles className="h-3.5 w-3.5" />, status: "pending" },
    { id: "analyze", label: "Analyse par l'IA", icon: <Brain className="h-3.5 w-3.5" />, status: "pending" },
    { id: "complete", label: "Finalisation", icon: <CheckCircle2 className="h-3.5 w-3.5" />, status: "pending" },
  ]);
  const [currentMessage, setCurrentMessage] = useState("Initialisation...");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // Simulate step progression based on progress percentage
  const updateStepsFromProgress = useCallback((progressPercent: number, status: string) => {
    setSteps((prev) => {
      const newSteps = [...prev];

      if (status === "error") {
        // Mark current step as error
        const activeIndex = newSteps.findIndex((s) => s.status === "active");
        if (activeIndex >= 0) {
          newSteps[activeIndex].status = "error";
        }
        return newSteps;
      }

      if (status === "complete" || status === "summarized") {
        // All steps complete
        return newSteps.map((s) => ({ ...s, status: "complete" as const }));
      }

      // Progress-based step updates
      if (progressPercent >= 0 && progressPercent < 25) {
        // Extraction phase
        newSteps[0].status = "active";
        setCurrentMessage("Extraction du texte des documents...");
      } else if (progressPercent >= 25 && progressPercent < 50) {
        // Embedding phase
        newSteps[0].status = "complete";
        newSteps[1].status = "active";
        setCurrentMessage("Generation des embeddings vectoriels...");
      } else if (progressPercent >= 50 && progressPercent < 90) {
        // Analysis phase
        newSteps[0].status = "complete";
        newSteps[1].status = "complete";
        newSteps[2].status = "active";
        setCurrentMessage("L'IA analyse le contenu...");
      } else if (progressPercent >= 90) {
        // Finalization phase
        newSteps[0].status = "complete";
        newSteps[1].status = "complete";
        newSteps[2].status = "complete";
        newSteps[3].status = "active";
        setCurrentMessage("Finalisation du resume...");
      }

      return newSteps;
    });
  }, []);

  // Poll for status updates
  useEffect(() => {
    if (!isAnalyzing) {
      // Hide after a delay when not analyzing
      const timer = setTimeout(() => setIsVisible(false), 500);
      return () => clearTimeout(timer);
    }

    setIsVisible(true);
    setError(null);

    // Reset steps when starting
    setSteps((prev) => prev.map((s) => ({ ...s, status: "pending" as const })));
    setProgress(0);
    setCurrentMessage("Demarrage de l'analyse...");

    const pollStatus = async () => {
      try {
        const status = await analysisApi.getStatus(caseId);
        setProgress(status.progress);
        updateStepsFromProgress(status.progress, status.status);

        if (status.status === "complete" || status.status === "summarized") {
          setCurrentMessage("Analyse terminee!");
          setSteps((prev) => prev.map((s) => ({ ...s, status: "complete" as const })));
          onComplete?.();
          return true; // Stop polling
        }

        if (status.status === "error") {
          setError(status.message || "Une erreur est survenue");
          return true; // Stop polling
        }

        return false; // Continue polling
      } catch {
        // Ignore errors during polling
        return false;
      }
    };

    // Initial poll
    pollStatus();

    // Set up polling interval
    const interval = setInterval(async () => {
      const shouldStop = await pollStatus();
      if (shouldStop) {
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [caseId, isAnalyzing, onComplete, updateStepsFromProgress]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="mt-3 p-3 bg-muted/30 rounded-lg border border-border/50 animate-in fade-in slide-in-from-top-2 duration-300">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
        <span className="text-xs font-medium text-foreground">Analyse en cours</span>
        <span className="text-xs text-muted-foreground ml-auto">{Math.round(progress)}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-muted rounded-full overflow-hidden mb-3">
        <div
          className="h-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-1.5">
        {steps.map((step) => (
          <div
            key={step.id}
            className={cn(
              "flex items-center gap-2 text-xs transition-all duration-300",
              step.status === "pending" && "text-muted-foreground/50",
              step.status === "active" && "text-primary font-medium",
              step.status === "complete" && "text-green-600",
              step.status === "error" && "text-destructive"
            )}
          >
            {/* Icon */}
            <span className={cn(
              "flex items-center justify-center w-5 h-5 rounded-full transition-all",
              step.status === "pending" && "bg-muted/50",
              step.status === "active" && "bg-primary/10",
              step.status === "complete" && "bg-green-100 dark:bg-green-900/30",
              step.status === "error" && "bg-destructive/10"
            )}>
              {step.status === "active" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : step.status === "complete" ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : step.status === "error" ? (
                <AlertCircle className="h-3 w-3" />
              ) : (
                step.icon
              )}
            </span>
            <span>{step.label}</span>
          </div>
        ))}
      </div>

      {/* Current message */}
      <p className="text-xs text-muted-foreground mt-2 italic">
        {error || currentMessage}
      </p>
    </div>
  );
}
