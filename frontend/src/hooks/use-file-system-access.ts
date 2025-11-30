"use client";

import { useState, useCallback } from "react";
import { toast } from "sonner";
import { documentsApi } from "@/lib/api";

// Extend Window interface for File System Access API
declare global {
  interface Window {
    showOpenFilePicker?: (options?: OpenFilePickerOptions) => Promise<FileSystemFileHandle[]>;
  }
}

interface OpenFilePickerOptions {
  multiple?: boolean;
  excludeAcceptAllOption?: boolean;
  types?: {
    description?: string;
    accept: Record<string, string[]>;
  }[];
}

interface FileSystemFileHandle {
  kind: "file";
  name: string;
  getFile(): Promise<File>;
  // Note: The actual path is not directly available in the API
  // We need to use a workaround or inform the user
}

// Check if File System Access API is supported
export function isFileSystemAccessSupported(): boolean {
  return typeof window !== "undefined" && "showOpenFilePicker" in window;
}

// File types accepted for linking
const ACCEPTED_TYPES: { description: string; accept: Record<string, string[]> }[] = [
  {
    description: "Documents",
    accept: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
      "image/*": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif"],
    },
  },
  {
    description: "Audio",
    accept: {
      "audio/*": [".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac", ".webm"],
      "video/mp4": [".mp4"],
      "video/webm": [".webm"],
    },
  },
];

export interface UseLinkFileOptions {
  caseId: string;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export function useLinkFile({ caseId, onSuccess, onError }: UseLinkFileOptions) {
  const [isLinking, setIsLinking] = useState(false);
  const [isSupported] = useState(isFileSystemAccessSupported);

  const linkFile = useCallback(async () => {
    if (!isFileSystemAccessSupported()) {
      toast.error("Votre navigateur ne supporte pas cette fonctionnalité. Utilisez Chrome ou Edge.");
      return;
    }

    setIsLinking(true);

    try {
      // Open file picker with File System Access API
      const fileHandles = await window.showOpenFilePicker!({
        multiple: true,
        types: ACCEPTED_TYPES,
      });

      if (fileHandles.length === 0) {
        setIsLinking(false);
        return;
      }

      // Unfortunately, the File System Access API doesn't provide the full path directly
      // We need to prompt the user to enter the path manually or use a workaround
      // For now, we'll show a dialog asking for the path

      for (const handle of fileHandles) {
        const file = await handle.getFile();

        // The File System Access API doesn't expose the full path for security reasons
        // We need to ask the user to provide the path manually
        const filePath = prompt(
          `Entrez le chemin complet du fichier "${file.name}":\n\n` +
          `Exemple: /Users/nom/Documents/fichier.pdf\n\n` +
          `(Cette étape est nécessaire car le navigateur ne permet pas d'accéder automatiquement au chemin pour des raisons de sécurité)`
        );

        if (!filePath) {
          toast.info(`Fichier "${file.name}" ignoré (pas de chemin fourni)`);
          continue;
        }

        // Register the file with the backend
        try {
          await documentsApi.register(caseId, filePath);
          toast.success(`Fichier "${file.name}" lié avec succès`);
        } catch (err) {
          toast.error(`Erreur lors du lien de "${file.name}": ${err instanceof Error ? err.message : "Erreur inconnue"}`);
        }
      }

      onSuccess?.();
    } catch (err) {
      // User cancelled the picker
      if (err instanceof Error && err.name === "AbortError") {
        // User cancelled, do nothing
        setIsLinking(false);
        return;
      }

      const error = err instanceof Error ? err : new Error("Erreur inconnue");
      toast.error(error.message);
      onError?.(error);
    } finally {
      setIsLinking(false);
    }
  }, [caseId, onSuccess, onError]);

  // Alternative: link by path directly (for use with a text input)
  const linkByPath = useCallback(async (filePath: string) => {
    if (!filePath.trim()) {
      toast.error("Veuillez entrer un chemin de fichier valide");
      return false;
    }

    setIsLinking(true);

    try {
      await documentsApi.register(caseId, filePath);
      toast.success("Fichier lié avec succès");
      onSuccess?.();
      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Erreur inconnue");
      toast.error(error.message);
      onError?.(error);
      return false;
    } finally {
      setIsLinking(false);
    }
  }, [caseId, onSuccess, onError]);

  return {
    linkFile,
    linkByPath,
    isLinking,
    isSupported,
  };
}
