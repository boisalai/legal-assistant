"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProgressEvent, AnalysisStep } from "@/types";

interface AnalysisProgressProps {
  dossierId: string;
  onComplete?: (data: Record<string, any>) => void;
  onError?: (message: string) => void;
}

const INITIAL_STEPS: AnalysisStep[] = [
  { number: 1, name: "Extraction des données", status: "pending" },
  { number: 2, name: "Classification", status: "pending" },
  { number: 3, name: "Vérification", status: "pending" },
  { number: 4, name: "Génération liste de vérification", status: "pending" },
];

export function AnalysisProgress({
  dossierId,
  onComplete,
  onError,
}: AnalysisProgressProps) {
  const [steps, setSteps] = useState<AnalysisStep[]>(INITIAL_STEPS);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentMessage, setCurrentMessage] = useState("Initialisation...");
  const [isComplete, setIsComplete] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  // Utiliser des refs pour éviter les reconnexions en boucle
  const isCompleteRef = useRef(false);
  const hasErrorRef = useRef(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleProgressEvent = useCallback(
    (event: ProgressEvent) => {
      // Ignorer les heartbeats (ils servent juste à garder la connexion ouverte)
      if (event.type === "heartbeat") {
        console.log("[SSE] Heartbeat received - connection alive");
        return;
      }

      console.log("[SSE] Event received:", event);

      setCurrentMessage(event.message);
      setProgressPercent(event.progressPercent);

      if (event.type === "step_start" && event.step !== null) {
        setSteps((prev) =>
          prev.map((step) =>
            step.number === event.step
              ? { ...step, status: "in_progress", message: event.message }
              : step
          )
        );
      }

      if (event.type === "step_end" && event.step !== null) {
        setSteps((prev) =>
          prev.map((step) =>
            step.number === event.step
              ? { ...step, status: "completed", message: event.message }
              : step
          )
        );
      }

      if (event.type === "complete") {
        console.log("[SSE] Analysis complete!");
        isCompleteRef.current = true;
        setIsComplete(true);
        setProgressPercent(100);
        setCurrentMessage("Analyse terminée!");
        // Fermer la connexion proprement
        eventSourceRef.current?.close();
        onComplete?.(event.data);
      }

      if (event.type === "error") {
        console.log("[SSE] Analysis error:", event.message);
        hasErrorRef.current = true;
        setHasError(true);
        setCurrentMessage(event.message);
        eventSourceRef.current?.close();
        onError?.(event.message);
      }
    },
    [onComplete, onError]
  );

  useEffect(() => {
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 30; // Max 30 tentatives (1 minute)

    const connectSSE = () => {
      // Ne pas reconnecter si analyse terminée ou en erreur
      if (isCompleteRef.current || hasErrorRef.current) {
        console.log("[SSE] Skipping reconnect - analysis finished");
        return;
      }

      // Limiter le nombre de reconnexions
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.log("[SSE] Max reconnection attempts reached");
        setCurrentMessage("Connexion perdue. Veuillez rafraîchir la page.");
        return;
      }

      // Connexion directe au backend pour éviter les problèmes de buffering du proxy
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      // Note: Ne pas utiliser encodeURIComponent car le dossierId peut déjà contenir des caractères encodés
      // et le double-encodage cause des erreurs 404 (dossier%253A au lieu de dossier%3A)
      const url = `${backendUrl}/api/dossiers/${dossierId}/analyse-stream`;

      console.log(`[SSE] Connecting to: ${url} (attempt ${reconnectAttempts + 1})`);

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log("[SSE] Connection opened");
        setIsConnected(true);
        reconnectAttempts = 0; // Reset on successful connection
      };

      eventSource.onmessage = (event) => {
        try {
          console.log("[SSE] Raw message:", event.data);
          const data = JSON.parse(event.data) as ProgressEvent;
          handleProgressEvent(data);
        } catch (err) {
          console.error("[SSE] Parse error:", err, "Data:", event.data);
        }
      };

      eventSource.onerror = (err) => {
        console.log("[SSE] Connection error/closed", err);
        setIsConnected(false);
        eventSource.close();

        // Si l'analyse n'est pas terminée, tenter de reconnecter
        if (!isCompleteRef.current && !hasErrorRef.current) {
          reconnectAttempts++;
          const delay = Math.min(2000 * reconnectAttempts, 10000); // Backoff: 2s, 4s, 6s... max 10s
          console.log(`[SSE] Will reconnect in ${delay}ms`);

          reconnectTimeoutRef.current = setTimeout(connectSSE, delay);
        }
      };
    };

    connectSSE();

    return () => {
      console.log("[SSE] Cleanup");
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      eventSourceRef.current?.close();
    };
  }, [dossierId, handleProgressEvent]);

  const getStepIcon = (status: AnalysisStep["status"]) => {
    switch (status) {
      case "completed":
        return (
          <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        );
      case "in_progress":
        return (
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          </div>
        );
      case "error":
        return (
          <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
            <span className="text-gray-500 text-sm font-medium">
              {/* Numéro de l'étape */}
            </span>
          </div>
        );
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {isComplete ? (
            <>
              <span className="text-green-500">Analyse terminée</span>
            </>
          ) : hasError ? (
            <>
              <span className="text-red-500">Erreur lors de l'analyse</span>
            </>
          ) : (
            <>
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span>Analyse en cours...</span>
            </>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Barre de progression */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{currentMessage}</span>
            <span className="font-medium">{Math.round(progressPercent)}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ease-out ${
                hasError
                  ? "bg-red-500"
                  : isComplete
                  ? "bg-green-500"
                  : "bg-blue-500"
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Liste des étapes */}
        <div className="space-y-4">
          {steps.map((step, index) => (
            <div key={step.number} className="flex items-start gap-4">
              {/* Ligne verticale connectant les étapes */}
              <div className="flex flex-col items-center">
                {getStepIcon(step.status)}
                {index < steps.length - 1 && (
                  <div
                    className={`w-0.5 h-8 mt-2 ${
                      step.status === "completed" ? "bg-green-500" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>

              {/* Contenu de l'étape */}
              <div className="flex-1 pb-4">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-medium ${
                      step.status === "completed"
                        ? "text-green-600"
                        : step.status === "in_progress"
                        ? "text-blue-600"
                        : step.status === "error"
                        ? "text-red-600"
                        : "text-gray-400"
                    }`}
                  >
                    Étape {step.number}: {step.name}
                  </span>
                </div>
                {step.message && step.status !== "pending" && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {step.message}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

      </CardContent>
    </Card>
  );
}
