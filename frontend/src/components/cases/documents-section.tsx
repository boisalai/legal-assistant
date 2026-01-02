"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { FileUp, Mic, Youtube, FileText } from "lucide-react";
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
import { DocumentsDataTable } from "./documents-data-table";
import { documentsApi } from "@/lib/api";
import { toast } from "sonner";
import type { Document } from "@/types";

interface DocumentsSectionProps {
  courseId: string;
  documents: Document[];
  onUploadDocuments: () => void;
  onRecordAudio: () => void;
  onYouTubeImport: () => void;
  onPreviewDocument: (docId: string) => void;
  onDeleteDocument: (docId: string) => Promise<void>;
  onDocumentsChange?: () => Promise<void>;
}

export function DocumentsSection({
  courseId,
  documents,
  onUploadDocuments,
  onRecordAudio,
  onYouTubeImport,
  onPreviewDocument,
  onDeleteDocument,
  onDocumentsChange,
}: DocumentsSectionProps) {
  const t = useTranslations();

  // Document action states
  const [extractingDocId, setExtractingDocId] = useState<string | null>(null);
  const [transcribingDocId, setTranscribingDocId] = useState<string | null>(null);
  const [clearingDocId, setClearingDocId] = useState<string | null>(null);
  const [extractingPDFDocId, setExtractingPDFDocId] = useState<string | null>(null);

  // Dialog states
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<Document | null>(null);
  const [reextractDialogOpen, setReextractDialogOpen] = useState(false);
  const [docToReextract, setDocToReextract] = useState<Document | null>(null);

  // Filter to show only uploaded documents (not linked)
  const uploadedDocuments = documents.filter((doc) => doc.source_type !== "linked");

  // Helper functions
  const isAudioFile = (doc: Document) => {
    const ext = doc.filename?.split(".").pop()?.toLowerCase() || "";
    const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return audioExtensions.includes(ext) || (doc.mime_type?.includes("audio") ?? false);
  };

  const isPDFFile = (doc: Document) => {
    const ext = doc.filename?.split(".").pop()?.toLowerCase() || "";
    return ext === "pdf" || doc.mime_type === "application/pdf";
  };

  const canExtractText = (doc: Document) => {
    const ext = doc.filename?.split(".").pop()?.toLowerCase() || "";
    const extractableExtensions = ["doc", "docx", "txt", "rtf", "md"];
    return extractableExtensions.includes(ext);
  };

  const needsExtraction = (doc: Document) => {
    return canExtractText(doc) && !doc.extracted_text;
  };

  // Handlers
  const handleExtractText = async (doc: Document) => {
    setExtractingDocId(doc.id);
    try {
      const result = await documentsApi.extract(courseId, doc.id);
      if (result.success) {
        toast.success(`Texte extrait avec succes (${result.method})`);
        if (onDocumentsChange) await onDocumentsChange();
      } else {
        toast.error(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de l'extraction");
    } finally {
      setExtractingDocId(null);
    }
  };

  const handleTranscribe = async (doc: Document) => {
    setTranscribingDocId(doc.id);
    try {
      const result = await documentsApi.transcribeWithWorkflow(courseId, doc.id, {
        language: "fr",
        createMarkdown: true,
      });
      if (result.success) {
        if (onDocumentsChange) await onDocumentsChange();
        toast.success("Transcription terminée");
      } else {
        toast.error(result.error || "Erreur lors de la transcription");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la transcription");
    } finally {
      setTranscribingDocId(null);
    }
  };

  const handleExtractPDF = async (doc: Document, forceReextract: boolean = false) => {
    setExtractingPDFDocId(doc.id);
    try {
      const result = await documentsApi.extractPDFToMarkdown(courseId, doc.id, {
        forceReextract,
      });
      if (result.success) {
        if (onDocumentsChange) await onDocumentsChange();
        toast.success("Markdown créé avec succès");
      } else {
        toast.error(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erreur lors de l'extraction";
      if (errorMessage.includes("existe déjà")) {
        setDocToReextract(doc);
        setReextractDialogOpen(true);
        setExtractingPDFDocId(null);
        return;
      }
      toast.error(errorMessage);
    } finally {
      setExtractingPDFDocId(null);
    }
  };

  const handleConfirmReextract = async () => {
    if (docToReextract) {
      setReextractDialogOpen(false);
      await handleExtractPDF(docToReextract, true);
      setDocToReextract(null);
    }
  };

  const handleClearText = async (doc: Document) => {
    setClearingDocId(doc.id);
    try {
      await documentsApi.clearText(courseId, doc.id);
      toast.success("Texte retiré de la base de données");
      if (onDocumentsChange) await onDocumentsChange();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la suppression du texte");
    } finally {
      setClearingDocId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (docToDelete) {
      const isMarkdown = docToDelete.filename?.endsWith(".md");
      if (docToDelete.extracted_text && !isMarkdown) {
        try {
          await documentsApi.clearText(courseId, docToDelete.id);
        } catch (err) {
          console.warn("Failed to clear text before deletion:", err);
        }
      }
      await onDeleteDocument(docToDelete.id);
      setDocToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  return (
    <>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            {t("documents.title")} ({uploadedDocuments.length})
          </h3>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={onUploadDocuments} className="gap-1">
              <FileUp className="h-3 w-3" />
              {t("documents.addDocuments")}
            </Button>
            <Button size="sm" onClick={onRecordAudio} className="gap-1">
              <Mic className="h-3 w-3" />
              {t("courses.recordAudio")}
            </Button>
            <Button size="sm" onClick={onYouTubeImport} className="gap-1">
              <Youtube className="h-3 w-3" />
              {t("courses.youtube")}
            </Button>
          </div>
        </div>

        <DocumentsDataTable
          documents={uploadedDocuments}
          onPreview={onPreviewDocument}
          onDelete={(doc) => {
            setDocToDelete(doc);
            setDeleteDialogOpen(true);
          }}
          onExtract={handleExtractText}
          onExtractPDF={handleExtractPDF}
          onTranscribe={handleTranscribe}
          onClearText={handleClearText}
          extractingDocId={extractingDocId}
          extractingPDFDocId={extractingPDFDocId}
          transcribingDocId={transcribingDocId}
          clearingDocId={clearingDocId}
          needsExtraction={needsExtraction}
          isPDFFile={isPDFFile}
          isAudioFile={isAudioFile}
        />
      </div>

      {/* Delete Document Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {docToDelete?.file_path?.includes("data/uploads/")
                ? "Supprimer ce document ?"
                : "Retirer ce document ?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {docToDelete?.file_path?.includes("data/uploads/") ? (
                <>
                  Le document « {docToDelete?.filename} » sera définitivement
                  supprimé du dossier et du disque.
                </>
              ) : (
                <>
                  Le document « {docToDelete?.filename} » sera retiré de ce
                  dossier. Le fichier original ne sera pas supprimé de votre
                  disque.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDocToDelete(null)}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className={
                docToDelete?.file_path?.includes("data/uploads/")
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : ""
              }
            >
              {docToDelete?.file_path?.includes("data/uploads/")
                ? "Supprimer"
                : "Retirer"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Re-extract PDF Dialog */}
      <AlertDialog open={reextractDialogOpen} onOpenChange={setReextractDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fichier markdown existant</AlertDialogTitle>
            <AlertDialogDescription>
              Un fichier markdown existe déjà pour ce PDF. Voulez-vous supprimer
              et réextraire le fichier ?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDocToReextract(null)}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmReextract}>
              Supprimer et réextraire
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
