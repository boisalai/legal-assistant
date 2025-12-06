"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  FileUp,
  Mic,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Edit2,
  Check,
  X,
  Loader2,
  Link2,
  RefreshCw,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { Case, Document, Checklist } from "@/types";
import { AnalysisProgressIndicator } from "./analysis-progress-indicator";
import { DocumentsDataTable } from "./documents-data-table";
import { documentsApi } from "@/lib/api";
import { toast } from "sonner";

interface CaseDetailsPanelProps {
  caseData: Case;
  documents: Document[];
  checklist: Checklist | null;
  onUploadDocuments: () => void;
  onRecordAudio: () => void;
  onLinkFile: () => void;
  onAnalyze: () => void;
  onUpdateCase: (data: { description?: string; type_transaction?: string }) => Promise<void>;
  onDeleteDocument: (docId: string) => Promise<void>;
  onPreviewDocument: (docId: string) => void;
  onDelete: () => void;
  onAnalysisComplete?: () => void;
  onDocumentsChange?: () => Promise<void>;
  deleting: boolean;
  isAnalyzing: boolean;
}

export function CaseDetailsPanel({
  caseData,
  documents,
  checklist,
  onUploadDocuments,
  onRecordAudio,
  onLinkFile,
  onAnalyze,
  onUpdateCase,
  onDeleteDocument,
  onPreviewDocument,
  onDelete,
  onAnalysisComplete,
  onDocumentsChange,
  deleting,
  isAnalyzing,
}: CaseDetailsPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editDescription, setEditDescription] = useState(caseData.description || "");
  const [isSaving, setIsSaving] = useState(false);
  const [extractingDocId, setExtractingDocId] = useState<string | null>(null);
  const [transcribingDocId, setTranscribingDocId] = useState<string | null>(null);
  const [clearingDocId, setClearingDocId] = useState<string | null>(null);
  const [extractingPDFDocId, setExtractingPDFDocId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<Document | null>(null);
  const [syncingDocuments, setSyncingDocuments] = useState(false);
  const [syncResultDialogOpen, setSyncResultDialogOpen] = useState(false);
  const [syncResultMessage, setSyncResultMessage] = useState("");
  const [syncResultTitle, setSyncResultTitle] = useState("");

  // Handle synchronize documents
  const handleSyncDocuments = async () => {
    setSyncingDocuments(true);
    try {
      const result = await documentsApi.sync(caseData.id);
      if (onDocumentsChange) {
        await onDocumentsChange();
      }

      if (result.discovered > 0) {
        setSyncResultTitle("Synchronisation réussie");
        setSyncResultMessage(`${result.discovered} fichier(s) découvert(s) et ajouté(s).`);
      } else {
        setSyncResultTitle("Synchronisation réussie");
        setSyncResultMessage("Aucun nouveau fichier découvert.");
      }
      setSyncResultDialogOpen(true);
    } catch (err) {
      setSyncResultTitle("Erreur de synchronisation");
      setSyncResultMessage(err instanceof Error ? err.message : "Erreur lors de la synchronisation");
      setSyncResultDialogOpen(true);
    } finally {
      setSyncingDocuments(false);
    }
  };

  // Check if document is an audio file
  const isAudioFile = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return audioExtensions.includes(ext) || doc.type_mime?.includes("audio");
  };

  // Check if document is a PDF file
  const isPDFFile = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    return ext === "pdf" || doc.type_mime === "application/pdf";
  };

  // Check if a document can have text extracted (non-audio without texte_extrait)
  const canExtractText = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    // PDF files should use "Extraire en markdown" instead of direct extraction
    const extractableExtensions = ["doc", "docx", "txt", "rtf", "md"];
    return extractableExtensions.includes(ext);
  };

  // Check if a document needs text extraction (non-audio without texte_extrait)
  const needsExtraction = (doc: Document) => {
    return canExtractText(doc) && !doc.texte_extrait;
  };

  const handleExtractText = async (doc: Document) => {
    setExtractingDocId(doc.id);
    try {
      const result = await documentsApi.extract(caseData.id, doc.id);
      if (result.success) {
        toast.success(`Texte extrait avec succes (${result.method})`);
        // Refresh the documents list
        if (onDocumentsChange) {
          await onDocumentsChange();
        }
      } else {
        toast.error(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de l'extraction");
    } finally {
      setExtractingDocId(null);
    }
  };

  // Handle transcription for audio files
  const handleTranscribe = async (doc: Document) => {
    setTranscribingDocId(doc.id);
    try {
      const result = await documentsApi.transcribeWithWorkflow(caseData.id, doc.id, {
        language: "fr",
        createMarkdown: true,
      });

      // Only refresh and show success if transcription actually succeeded
      if (result.success) {
        // Refresh documents list to get updated state
        if (onDocumentsChange) {
          await onDocumentsChange();
        }
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

  // Handle PDF extraction to markdown
  const handleExtractPDF = async (doc: Document) => {
    setExtractingPDFDocId(doc.id);
    try {
      const result = await documentsApi.extractPDFToMarkdown(caseData.id, doc.id);

      // Only refresh and show success if extraction actually succeeded
      if (result.success) {
        // Refresh documents list to get updated state
        if (onDocumentsChange) {
          await onDocumentsChange();
        }
        toast.success("Markdown créé avec succès");
      } else {
        toast.error(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de l'extraction");
    } finally {
      setExtractingPDFDocId(null);
    }
  };

  // Handle clearing extracted text
  const handleClearText = async (doc: Document) => {
    setClearingDocId(doc.id);
    try {
      await documentsApi.clearText(caseData.id, doc.id);
      toast.success("Texte retiré de la base de données");
      if (onDocumentsChange) {
        await onDocumentsChange();
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la suppression du texte");
    } finally {
      setClearingDocId(null);
    }
  };

  // Handle document deletion (also clears extracted text from DB if present)
  const handleConfirmDelete = async () => {
    if (docToDelete) {
      // Only clear text for non-markdown documents with extracted text
      // Markdown files store their content in texte_extrait but don't need clearing
      const isMarkdown = docToDelete.nom_fichier?.endsWith('.md');
      if (docToDelete.texte_extrait && !isMarkdown) {
        try {
          await documentsApi.clearText(caseData.id, docToDelete.id);
        } catch (err) {
          // Continue with deletion even if clearing text fails
          console.warn("Failed to clear text before deletion:", err);
        }
      }
      await onDeleteDocument(docToDelete.id);
      setDocToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdateCase({
        description: editDescription,
      });
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditDescription(caseData.description || "");
    setIsEditing(false);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Case Header */}
      <div className="p-4 border-b bg-background">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-bold">{caseData.title || "Sans titre"}</h2>
          {caseData.description && (
            <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
              <span>{caseData.description}</span>
            </div>
          )}
        </div>
      </div>

      {/* Contenu principal avec padding */}
      <div className="px-6 py-2 space-y-4 flex-1">
        {/* Mode édition */}
        {isEditing && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label> 
              <Textarea
                id="edit-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Description du dossier"
                disabled={isSaving}
                className="text-sm min-h-[80px]"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Enregistrer
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                <X className="h-4 w-4" />
                Annuler
              </Button>
            </div>
          </div>
        )}

        {/* Boutons d'action */}
        <div className="flex items-center py-2 gap-2 flex-wrap">
          <Button
            size="sm"
            onClick={() => setIsEditing(true)}
            disabled={isEditing}
            className="gap-2"
          >
            <Edit2 className="h-4 w-4" />
            <span>Modifier</span>
          </Button>
          <Button
            size="sm"
            onClick={onUploadDocuments}
            className="gap-2"
          >
            <FileUp className="h-4 w-4" />
            <span>Ajouter des documents</span>
          </Button>
          <Button
            size="sm"
            onClick={onLinkFile}
            className="gap-2"
          >
            <Link2 className="h-4 w-4" />
            <span>Lier un fichier</span>
          </Button>
          <Button
            size="sm"
            onClick={onRecordAudio}
            className="gap-2"
          >
            <Mic className="h-4 w-4" />
            <span>Enregistrer un audio</span>
          </Button>
        </div>

      {/* Liste des documents */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-sm">Documents ({documents.length})</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSyncDocuments}
            disabled={syncingDocuments}
            title="Synchroniser - Découvre les fichiers dans le répertoire du dossier"
            className="h-7 text-xs"
          >
            {syncingDocuments ? (
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
            ) : (
              <RefreshCw className="h-3 w-3 mr-1" />
            )}
            Sync
          </Button>
        </div>

        {/* DataTable with filters */}
        <DocumentsDataTable
          documents={documents}
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

        {/* Analysis Progress Indicator */}
        <AnalysisProgressIndicator
          caseId={caseData.id}
          isAnalyzing={isAnalyzing}
          onComplete={onAnalysisComplete}
        />
      </div>

      {/* Points de vérification et d'attention */}
      {checklist && (
        <>
          {/* Points de vérification */}
          {checklist.items && checklist.items.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                Points de vérification
              </h3>
              <ul className="space-y-1.5">
                {checklist.items.slice(0, 5).map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-600 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{item.titre}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Points d'attention */}
          {checklist.points_attention && checklist.points_attention.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                Points d'attention ({checklist.points_attention.length})
              </h3>
              <ul className="space-y-1.5">
                {checklist.points_attention.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      </div>

      {/* Footer avec bouton Supprimer */}
      <div className="p-4 border-t mt-auto flex justify-end items-center">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button disabled={deleting}>
              <Trash2 className="h-4 w-4 mr-2" />
              Supprimer
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
              <AlertDialogDescription>
                Êtes-vous sûr de vouloir supprimer ce dossier ? Cette action
                est irréversible.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction onClick={onDelete}>
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* AlertDialog for document deletion */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {docToDelete?.file_path?.includes('data/uploads/') ? 'Supprimer ce document ?' : 'Retirer ce document ?'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {docToDelete?.file_path?.includes('data/uploads/') ? (
                <>
                  Le document « {docToDelete?.nom_fichier} » sera définitivement supprimé du dossier et du disque.
                </>
              ) : (
                <>
                  Le document « {docToDelete?.nom_fichier} » sera retiré de ce dossier.
                  Le fichier original ne sera pas supprimé de votre disque.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDocToDelete(null)}>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete}>
              {docToDelete?.file_path?.includes('data/uploads/') ? 'Supprimer' : 'Retirer'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Sync Result Dialog */}
      <AlertDialog open={syncResultDialogOpen} onOpenChange={setSyncResultDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{syncResultTitle}</AlertDialogTitle>
            <AlertDialogDescription>
              {syncResultMessage}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setSyncResultDialogOpen(false)}>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
