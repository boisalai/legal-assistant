"use client";

import { useEffect, useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  CheckCircle2,
  Loader2,
  XCircle,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface SyncTask {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "error";
  details?: string[];
  error?: string;
}

export interface SyncResult {
  uploadedDiscovered: number;
  linkedAdded: number;
  linkedUpdated: number;
  linkedRemoved: number;
}

interface SyncProgressModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tasks: SyncTask[];
  result?: SyncResult | null;
  isComplete: boolean;
  hasError: boolean;
}

export function SyncProgressModal({
  open,
  onOpenChange,
  tasks,
  result,
  isComplete,
  hasError,
}: SyncProgressModalProps) {
  const [autoClose, setAutoClose] = useState(false);

  // Auto-close after 3 seconds if successful and no changes
  useEffect(() => {
    if (isComplete && !hasError && result) {
      const hasChanges =
        result.uploadedDiscovered > 0 ||
        result.linkedAdded > 0 ||
        result.linkedUpdated > 0 ||
        result.linkedRemoved > 0;

      if (!hasChanges) {
        setAutoClose(true);
        const timer = setTimeout(() => {
          onOpenChange(false);
        }, 3000);
        return () => clearTimeout(timer);
      }
    }
  }, [isComplete, hasError, result, onOpenChange]);

  const getStatusIcon = (status: SyncTask["status"]) => {
    switch (status) {
      case "pending":
        return <div className="h-5 w-5 rounded-full border-2 border-muted" />;
      case "running":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case "error":
        return <XCircle className="h-5 w-5 text-red-500" />;
    }
  };

  const completedTasks = tasks.filter((t) => t.status === "completed").length;
  const totalTasks = tasks.length;
  const progressPercentage = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <AlertDialog open={open} onOpenChange={isComplete ? onOpenChange : undefined}>
      <AlertDialogContent className="sm:max-w-[600px]">
        <AlertDialogHeader>
          <AlertDialogTitle>
            {!isComplete && "Synchronisation en cours..."}
            {isComplete && !hasError && "Synchronisation terminée"}
            {isComplete && hasError && "Erreur de synchronisation"}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {!isComplete && `${completedTasks} sur ${totalTasks} tâches effectuées`}
            {isComplete && !hasError && result && (
              <>
                {result.uploadedDiscovered === 0 &&
                result.linkedAdded === 0 &&
                result.linkedUpdated === 0 &&
                result.linkedRemoved === 0
                  ? "Tous les documents sont à jour"
                  : `${result.linkedAdded + result.linkedUpdated + result.linkedRemoved + result.uploadedDiscovered} modification(s) détectée(s)`}
              </>
            )}
            {isComplete && hasError && "Certaines tâches ont échoué"}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {/* Progress bar */}
        {!isComplete && (
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full bg-blue-500 transition-all duration-500 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        )}

        {/* Tasks list */}
        <ScrollArea className="max-h-[400px] pr-4">
          <div className="space-y-4">
            {tasks.map((task) => (
              <div key={task.id} className="space-y-2">
                <div className="flex items-start gap-3">
                  {getStatusIcon(task.status)}
                  <div className="flex-1 space-y-1">
                    <p
                      className={cn(
                        "text-sm font-medium leading-none",
                        task.status === "pending" && "text-muted-foreground",
                        task.status === "running" && "text-foreground",
                        task.status === "completed" && "text-foreground",
                        task.status === "error" && "text-red-600"
                      )}
                    >
                      {task.label}
                    </p>
                    {task.error && (
                      <p className="text-sm text-red-600">{task.error}</p>
                    )}
                    {task.details && task.details.length > 0 && (
                      <div className="space-y-1 pl-2 border-l-2 border-muted">
                        {task.details.map((detail, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-xs text-muted-foreground">
                            <FileText className="h-3 w-3 shrink-0" />
                            <span className="truncate">{detail}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>


        {/* Footer */}
        {isComplete && (
          <AlertDialogFooter>
            {autoClose && (
              <p className="text-sm text-muted-foreground mr-auto self-center">
                Fermeture automatique...
              </p>
            )}
            <AlertDialogAction onClick={() => onOpenChange(false)}>
              Fermer
            </AlertDialogAction>
          </AlertDialogFooter>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );
}
