"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Folder, Loader2, FolderOpen, FileText, CheckCircle2, AlertCircle } from "lucide-react";
import { linkedDirectoryApi } from "@/lib/api";
import type { LinkedDirectoryScanResult } from "@/types";

interface LinkDirectoryModalProps {
  caseId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLinkSuccess: () => void;
}

type ModalState = "input" | "scanning" | "confirm" | "linking" | "success" | "error";

export function LinkDirectoryModal({
  caseId,
  open,
  onOpenChange,
  onLinkSuccess,
}: LinkDirectoryModalProps) {
  const [state, setState] = useState<ModalState>("input");
  const [directoryPath, setDirectoryPath] = useState("");
  const [scanResult, setScanResult] = useState<LinkedDirectoryScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkingProgress, setLinkingProgress] = useState({ indexed: 0, total: 0, percentage: 0, currentFile: "" });
  const [autoExtractMarkdown, setAutoExtractMarkdown] = useState(false);
  const [currentLinkId, setCurrentLinkId] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // Reset state when modal closes
  const handleClose = () => {
    if (state !== "linking") {
      setState("input");
      setDirectoryPath("");
      setScanResult(null);
      setError(null);
      setLinkingProgress({ indexed: 0, total: 0, percentage: 0, currentFile: "" });
      setAutoExtractMarkdown(false);
      setCurrentLinkId(null);
      setAbortController(null);
      onOpenChange(false);
    }
  };

  // Scan directory
  const handleScan = async () => {
    if (!directoryPath.trim()) {
      setError("Veuillez entrer un chemin de répertoire");
      return;
    }

    setState("scanning");
    setError(null);

    try {
      // Clean the path: remove quotes and trim whitespace
      const cleanPath = directoryPath.trim().replace(/^['"]|['"]$/g, '');
      const result = await linkedDirectoryApi.scan(cleanPath);
      setScanResult(result);
      setState("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du scan du répertoire");
      setState("error");
    }
  };

  // Cancel linking
  const handleCancel = async () => {
    if (!currentLinkId) {
      return;
    }

    // Abort the SSE stream
    if (abortController) {
      abortController.abort();
    }

    // Call backend to clean up partial data
    try {
      const cleanId = caseId.replace("course:", "").replace("case:", "");
      const response = await fetch(`http://localhost:8000/api/courses/${cleanId}/link-directory/${currentLinkId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Nettoyage effectué:", result);
      }
    } catch (err) {
      console.error("Erreur lors du nettoyage:", err);
    }

    // Reset state
    setState("input");
    setCurrentLinkId(null);
    setAbortController(null);
    setLinkingProgress({ indexed: 0, total: 0, percentage: 0, currentFile: "" });
  };

  // Link directory
  const handleLink = async () => {
    if (!scanResult) return;

    setState("linking");
    setLinkingProgress({ indexed: 0, total: scanResult.total_files, percentage: 0, currentFile: "" });

    // Create abort controller
    const controller = new AbortController();
    setAbortController(controller);

    try {
      // Clean the path: remove quotes and trim whitespace
      const cleanPath = directoryPath.trim().replace(/^['"]|['"]$/g, '');
      await linkedDirectoryApi.link(
        caseId,
        cleanPath,
        autoExtractMarkdown,
        controller.signal,
        (progress) => {
          setLinkingProgress({
            indexed: progress.indexed,
            total: progress.total,
            percentage: progress.percentage,
            currentFile: progress.current_file,
          });
        },
        (complete) => {
          setCurrentLinkId(complete.link_id);
          setState("success");
          setTimeout(() => {
            onLinkSuccess();
            handleClose();
          }, 2000);
        },
        (err) => {
          setError(err);
          setState("error");
        },
        (linkId) => {
          // Callback to capture link_id early
          setCurrentLinkId(linkId);
        }
      );
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        // Linking was cancelled by user
        return;
      }
      setError(err instanceof Error ? err.message : "Erreur lors de la liaison du répertoire");
      setState("error");
    }
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  // Get file type label and color
  const getFileTypeInfo = (ext: string) => {
    const colors: Record<string, string> = {
      pdf: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
      md: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
      mdx: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
      txt: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
      docx: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
      doc: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    };

    return colors[ext] || "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
  };

  return (
    <>
      {/* Main dialog */}
      <Dialog open={open && state !== "confirm"} onOpenChange={handleClose}>
        <DialogContent className={`max-w-2xl ${state === "linking" ? "[&>button]:hidden" : ""}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Folder className="h-5 w-5" />
              Lier un répertoire
            </DialogTitle>
            <DialogDescription>
              Liez un répertoire local pour indexer tous ses fichiers (.md, .mdx, .pdf, .txt, .docx)
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Input state */}
            {state === "input" && (
              <>
                <div className="space-y-2">
                  <label htmlFor="directory-path" className="text-sm font-medium">
                    Chemin du répertoire
                  </label>
                  <Input
                    id="directory-path"
                    placeholder="/Users/username/Documents/mon-projet"
                    value={directoryPath}
                    onChange={(e) => setDirectoryPath(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        handleScan();
                      }
                    }}
                  />
                  <p className="text-xs text-muted-foreground">
                    Entrez le chemin absolu du répertoire à lier
                  </p>
                </div>
              </>
            )}

            {/* Scanning state */}
            {state === "scanning" && (
              <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="h-12 w-12 animate-spin text-blue-500 mb-4" />
                <p className="text-sm text-muted-foreground">Scan du répertoire en cours...</p>
              </div>
            )}

            {/* Linking state */}
            {state === "linking" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Indexation en cours...</p>
                  <Badge variant="secondary">
                    {linkingProgress.indexed} / {linkingProgress.total}
                  </Badge>
                </div>
                <Progress value={linkingProgress.percentage} className="h-2" />
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  <span className="truncate">{linkingProgress.currentFile}</span>
                </div>
                <p className="text-xs text-muted-foreground text-center">
                  {linkingProgress.percentage.toFixed(1)}% complété
                </p>
              </div>
            )}

            {/* Success state */}
            {state === "success" && (
              <div className="flex flex-col items-center justify-center py-8">
                <CheckCircle2 className="h-12 w-12 text-green-500 mb-4" />
                <p className="text-sm font-medium">Répertoire lié avec succès !</p>
                <p className="text-xs text-muted-foreground">
                  {linkingProgress.indexed} fichier{linkingProgress.indexed > 1 ? "s" : ""} indexé{linkingProgress.indexed > 1 ? "s" : ""}
                </p>
              </div>
            )}

            {/* Error state */}
            {state === "error" && error && (
              <div className="flex flex-col items-center justify-center py-8">
                <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
                <p className="text-sm font-medium text-red-600">Erreur</p>
                <p className="text-xs text-muted-foreground text-center">{error}</p>
              </div>
            )}
          </div>

          <DialogFooter>
            {state === "input" && (
              <>
                <Button variant="outline" onClick={handleClose}>
                  Annuler
                </Button>
                <Button onClick={handleScan} disabled={!directoryPath.trim()}>
                  Scanner
                </Button>
              </>
            )}

            {state === "error" && (
              <Button onClick={() => setState("input")}>
                Réessayer
              </Button>
            )}

            {state === "linking" && (
              <Button
                variant="destructive"
                onClick={handleCancel}
                disabled={!currentLinkId}
              >
                Annuler
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation dialog */}
      <AlertDialog open={state === "confirm"}>
        <AlertDialogContent className="max-w-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              Confirmer la liaison du répertoire
            </AlertDialogTitle>
            <AlertDialogDescription>
              Les fichiers suivants seront indexés dans ce dossier :
            </AlertDialogDescription>
          </AlertDialogHeader>

          {scanResult && (
            <div className="space-y-4">
              {/* Statistics */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                <div className="text-center">
                  <p className="text-2xl font-bold">{scanResult.total_files}</p>
                  <p className="text-xs text-muted-foreground">Fichiers</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">{Object.keys(scanResult.folder_structure).length}</p>
                  <p className="text-xs text-muted-foreground">Dossiers</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">{formatFileSize(scanResult.total_size)}</p>
                  <p className="text-xs text-muted-foreground">Taille totale</p>
                </div>
              </div>

              {/* Files by type */}
              <div>
                <p className="text-sm font-medium mb-2">Fichiers par type :</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(scanResult.files_by_type).map(([ext, count]) => (
                    <Badge key={ext} variant="secondary" className={getFileTypeInfo(ext)}>
                      .{ext} ({count})
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Directory path */}
              <div className="p-3 bg-muted rounded text-xs font-mono break-all">
                {scanResult.base_path}
              </div>

              {/* Auto-extract option */}
              {scanResult && (scanResult.files_by_type.pdf || scanResult.files_by_type.docx || scanResult.files_by_type.doc) && (
                <div className="flex items-start space-x-3 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <Checkbox
                    id="auto-extract"
                    checked={autoExtractMarkdown}
                    onCheckedChange={(checked) => setAutoExtractMarkdown(checked === true)}
                  />
                  <div className="space-y-1">
                    <label
                      htmlFor="auto-extract"
                      className="text-sm font-medium leading-none cursor-pointer"
                    >
                      Extraire automatiquement en Markdown
                    </label>
                    <p className="text-xs text-muted-foreground">
                      Les fichiers PDF, Word et audio seront automatiquement convertis en fichiers .md pour une meilleure recherche sémantique
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setState("input")}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleLink}>
              Indexer {scanResult?.total_files} fichier{scanResult && scanResult.total_files > 1 ? "s" : ""}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
