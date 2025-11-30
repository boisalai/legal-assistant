"use client";

import { useState, useCallback } from "react";
import { Loader2, Check, FileAudio, FileText, Sparkles } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface TranscriptionStep {
  id: string;
  label: string;
  icon: React.ReactNode;
  status: "pending" | "in_progress" | "completed" | "error";
}

interface TranscriptionProgressProps {
  isVisible: boolean;
  currentMessage?: string;
  percentage?: number;
  currentStep?: string;
}

const STEPS: { id: string; label: string; icon: React.ReactNode }[] = [
  { id: "transcription", label: "Transcription", icon: <FileAudio className="h-3 w-3" /> },
  { id: "formatting", label: "Formatage", icon: <Sparkles className="h-3 w-3" /> },
  { id: "saving", label: "Sauvegarde", icon: <FileText className="h-3 w-3" /> },
];

export function TranscriptionProgress({
  isVisible,
  currentMessage,
  percentage = 0,
  currentStep,
}: TranscriptionProgressProps) {
  if (!isVisible) return null;

  const getStepStatus = (stepId: string): "pending" | "in_progress" | "completed" | "error" => {
    if (!currentStep) return "pending";

    const currentIndex = STEPS.findIndex(s => s.id === currentStep);
    const stepIndex = STEPS.findIndex(s => s.id === stepId);

    if (stepIndex < currentIndex) return "completed";
    if (stepIndex === currentIndex) return "in_progress";
    return "pending";
  };

  return (
    <div className="bg-muted/50 rounded-lg p-3 border border-border/50 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex items-center gap-3 mb-2">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">
          {currentMessage || "Transcription en cours..."}
        </span>
      </div>

      <Progress value={percentage} className="h-1.5 mb-3" />

      <div className="flex items-center justify-between gap-2">
        {STEPS.map((step, index) => {
          const status = getStepStatus(step.id);
          return (
            <div key={step.id} className="flex items-center gap-1.5">
              <div
                className={cn(
                  "flex items-center justify-center w-5 h-5 rounded-full transition-colors",
                  status === "completed" && "bg-green-500/20 text-green-600",
                  status === "in_progress" && "bg-primary/20 text-primary",
                  status === "pending" && "bg-muted text-muted-foreground"
                )}
              >
                {status === "completed" ? (
                  <Check className="h-3 w-3" />
                ) : status === "in_progress" ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  step.icon
                )}
              </div>
              <span
                className={cn(
                  "text-xs transition-colors",
                  status === "completed" && "text-green-600",
                  status === "in_progress" && "text-primary font-medium",
                  status === "pending" && "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <div
                  className={cn(
                    "w-4 h-px mx-1",
                    status === "completed" ? "bg-green-500/50" : "bg-border"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Hook to manage transcription state
export function useTranscriptionProgress() {
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [currentMessage, setCurrentMessage] = useState("");
  const [percentage, setPercentage] = useState(0);
  const [currentStep, setCurrentStep] = useState<string | undefined>();

  const startTranscription = useCallback(() => {
    setIsTranscribing(true);
    setCurrentMessage("Initialisation...");
    setPercentage(0);
    setCurrentStep(undefined);
  }, []);

  const updateProgress = useCallback((step: string, message: string, pct: number) => {
    setCurrentStep(step);
    setCurrentMessage(message);
    setPercentage(pct);
  }, []);

  const onStepStart = useCallback((step: string) => {
    setCurrentStep(step);
  }, []);

  const onStepComplete = useCallback((step: string, success: boolean) => {
    if (!success) {
      setCurrentMessage(`Erreur lors de l'étape: ${step}`);
    }
  }, []);

  const endTranscription = useCallback((success: boolean) => {
    if (success) {
      setCurrentMessage("Transcription terminée!");
      setPercentage(100);
      setCurrentStep("complete");
    }
    // Keep visible briefly then hide
    setTimeout(() => {
      setIsTranscribing(false);
      setCurrentMessage("");
      setPercentage(0);
      setCurrentStep(undefined);
    }, 2000);
  }, []);

  return {
    isTranscribing,
    currentMessage,
    percentage,
    currentStep,
    startTranscription,
    updateProgress,
    onStepStart,
    onStepComplete,
    endTranscription,
  };
}
