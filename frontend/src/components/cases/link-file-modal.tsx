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
      setError("Veuillez entrer un chemin de fichier");
      return;
    }

    // Basic path validation
    if (!cleanedPath.startsWith("/")) {
      setError("Le chemin doit être absolu (commencer par /)");
      return;
    }

    setIsLinking(true);
    setError(null);

    try {
      await documentsApi.register(caseId, cleanedPath);
      toast.success("Fichier lié avec succès");
      onLinkComplete();
      handleClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors du lien";
      setError(message);
    } finally {
      setIsLinking(false);
    }
  };

  const handleClose = () => {
    if (!isLinking) {
      setFilePath("");
      setError(null);
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
            Lier un fichier
          </DialogTitle>
          <DialogDescription>
            Entrez le chemin du fichier. Il ne sera pas copié, seulement référencé.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="file-path">Chemin du fichier</Label>
            <Input
              id="file-path"
              type="text"
              placeholder="/Users/nom/Documents/fichier.pdf"
              value={filePath}
              onChange={(e) => {
                setFilePath(e.target.value);
                setError(null);
              }}
              onKeyDown={handleKeyDown}
              disabled={isLinking}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Astuce : Dans le Finder, sélectionnez un fichier et faites <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Cmd</kbd>+<kbd className="px-1 py-0.5 bg-muted rounded text-xs">Option</kbd>+<kbd className="px-1 py-0.5 bg-muted rounded text-xs">C</kbd> pour copier son chemin
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
            <p className="font-medium mb-1">Note importante</p>
            <p>
              Le fichier doit rester accessible à son emplacement d'origine.
              Si vous déplacez ou supprimez le fichier, il ne sera plus disponible dans l'application.
            </p>
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
                Lier le fichier
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
