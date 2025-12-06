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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Link2, Loader2, AlertCircle } from "lucide-react";
import { documentsApi } from "@/lib/api";
import { toast } from "sonner";

interface LinkFileModalProps {
  open: boolean;
  onClose: () => void;
  caseId: string;
  onLinkComplete: () => void;
}

export function LinkFileModal({
  open,
  onClose,
  caseId,
  onLinkComplete,
}: LinkFileModalProps) {
  const [filePath, setFilePath] = useState("");
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  // Clean the file path by removing surrounding quotes (single or double)
  const cleanPath = (path: string): string => {
    let cleaned = path.trim();
    // Remove surrounding single quotes
    if (cleaned.startsWith("'") && cleaned.endsWith("'")) {
      cleaned = cleaned.slice(1, -1);
    }
    // Remove surrounding double quotes
    if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
      cleaned = cleaned.slice(1, -1);
    }
    return cleaned;
  };

  const handleLink = async () => {
    const cleanedPath = cleanPath(filePath);

    if (!cleanedPath) {
      setError("Veuillez entrer un chemin");
      return;
    }

    // Basic path validation
    if (!cleanedPath.startsWith("/")) {
      setError("Le chemin doit être absolu (commencer par /)");
      return;
    }

    setIsLinking(true);
    setError(null);
    setWarnings([]);

    try {
      const result = await documentsApi.link(caseId, cleanedPath);

      // Display warnings if any
      if (result.warnings && result.warnings.length > 0) {
        setWarnings(result.warnings);
      }

      // Success message
      if (result.linked_count === 1) {
        toast.success("Fichier lié avec succès");
      } else {
        toast.success(`${result.linked_count} fichiers liés avec succès`);
      }

      // Wait for the callback to complete before closing
      await Promise.resolve(onLinkComplete());
      handleClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors de la liaison";
      setError(message);
    } finally {
      setIsLinking(false);
    }
  };

  const handleClose = () => {
    if (!isLinking) {
      setFilePath("");
      setError(null);
      setWarnings([]);
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !isLinking && filePath.trim()) {
      handleLink();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Lier un fichier ou dossier
          </DialogTitle>
          <DialogDescription>
            Entrez le chemin d'un fichier ou d'un dossier. Les fichiers ne seront pas copiés, seulement référencés.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="file-path">Chemin du fichier ou dossier</Label>
            <Input
              id="file-path"
              type="text"
              placeholder="/Users/nom/Documents/mon-dossier"
              value={filePath}
              onChange={(e) => {
                setFilePath(e.target.value);
                setError(null);
                setWarnings([]);
              }}
              onKeyDown={handleKeyDown}
              disabled={isLinking}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Astuce : Dans le Finder, sélectionnez un fichier/dossier et faites <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Cmd</kbd>+<kbd className="px-1 py-0.5 bg-muted rounded text-xs">Option</kbd>+<kbd className="px-1 py-0.5 bg-muted rounded text-xs">C</kbd> pour copier son chemin
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {warnings.length > 0 && (
            <div className="rounded-md bg-orange-50 border border-orange-200 p-3 space-y-1">
              <p className="text-sm font-medium text-orange-800">Avertissements :</p>
              {warnings.map((warning, idx) => (
                <p key={idx} className="text-xs text-orange-700">• {warning}</p>
              ))}
            </div>
          )}

          <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground space-y-2">
            <div>
              <p className="font-medium mb-1">📁 Si vous liez un dossier :</p>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>Seuls les fichiers du dossier direct seront liés (pas les sous-dossiers)</li>
                <li>Types supportés : .md, .mdx, .pdf, .txt, .docx</li>
                <li>Limite : 50 fichiers maximum</li>
              </ul>
            </div>
            <div>
              <p className="font-medium mb-1">⚠️ Note importante :</p>
              <p className="text-xs">
                Les fichiers doivent rester accessibles à leur emplacement d'origine.
                Si vous déplacez ou supprimez les fichiers, ils ne seront plus disponibles dans l'application.
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLinking}>
            Annuler
          </Button>
          <Button onClick={handleLink} disabled={isLinking || !filePath.trim()}>
            {isLinking ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Liaison en cours...
              </>
            ) : (
              <>
                <Link2 className="h-4 w-4 mr-2" />
                Lier
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
