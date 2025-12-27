"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SessionSelector } from "@/components/cases/session-selector";
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
  Folder,
  RefreshCw,
  FileText,
  Youtube,
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
import type { Course, Document, Checklist } from "@/types";
import type { LinkedDirectory } from "./linked-directories-data-table";
import { DocumentsDataTable } from "./documents-data-table";
import { LinkedDirectoriesSection } from "./linked-directories-section";
import { SyncProgressModal, SyncTask, SyncResult } from "./sync-progress-modal";
import { documentsApi } from "@/lib/api";
import { toast } from "sonner";

interface CaseDetailsPanelProps {
  caseData: Course;
  documents: Document[];
  checklist: Checklist | null;
  onUploadDocuments: () => void;
  onRecordAudio: () => void;
  onLinkFile: () => void;
  onYouTubeImport: () => void;
  onAnalyze?: () => void;
  onUpdateCase: (data: {
    description?: string;
    type_transaction?: string;
    session_id?: string;
    course_code?: string;
    professor?: string;
    credits?: number;
    color?: string;
  }) => Promise<void>;
  onDeleteDocument: (docId: string) => Promise<void>;
  onPreviewDocument: (docId: string) => void;
  onPreviewDirectory: (directory: LinkedDirectory) => void;
  onDelete: () => void;
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
  onYouTubeImport,
  onUpdateCase,
  onDeleteDocument,
  onPreviewDocument,
  onPreviewDirectory,
  onDelete,
  onDocumentsChange,
  deleting,
  isAnalyzing,
}: CaseDetailsPanelProps) {
  const t = useTranslations();
  const [isEditing, setIsEditing] = useState(false);
  const [editDescription, setEditDescription] = useState(caseData.description || "");
  const [isSaving, setIsSaving] = useState(false);

  // Academic fields for editing
  const [editSessionId, setEditSessionId] = useState(caseData.session_id || "");
  const [editCourseCode, setEditCourseCode] = useState(caseData.course_code || "");
  const [editProfessor, setEditProfessor] = useState(caseData.professor || "");
  const [editCredits, setEditCredits] = useState(caseData.credits?.toString() || "3");
  const [editColor, setEditColor] = useState(caseData.color || "#3B82F6");
  const [extractingDocId, setExtractingDocId] = useState<string | null>(null);
  const [transcribingDocId, setTranscribingDocId] = useState<string | null>(null);
  const [clearingDocId, setClearingDocId] = useState<string | null>(null);
  const [extractingPDFDocId, setExtractingPDFDocId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<Document | null>(null);
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncComplete, setSyncComplete] = useState(false);
  const [syncHasError, setSyncHasError] = useState(false);

  // Handle synchronize documents
  const handleSyncDocuments = async () => {
    // Initialize sync state
    setSyncModalOpen(true);
    setSyncComplete(false);
    setSyncHasError(false);
    setSyncResult(null);

    const initialTasks: SyncTask[] = [
      {
        id: "scan-uploaded",
        label: "Analyse des documents uploadés",
        status: "pending",
      },
      {
        id: "scan-linked",
        label: "Analyse des répertoires liés",
        status: "pending",
      },
      {
        id: "refresh",
        label: "Actualisation de la liste",
        status: "pending",
      },
    ];
    setSyncTasks(initialTasks);

    try {
      // Step 1: Sync uploaded documents
      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "scan-uploaded" ? { ...t, status: "running" } : t
        )
      );

      const uploadResult = await documentsApi.sync(caseData.id);
      const uploadDetails: string[] = [];
      if (uploadResult.discovered > 0) {
        uploadDetails.push(`${uploadResult.discovered} fichier(s) découvert(s)`);
      }

      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "scan-uploaded"
            ? { ...t, status: "completed", details: uploadDetails.length > 0 ? uploadDetails : ["Aucun changement"] }
            : t
        )
      );

      // Step 2: Sync linked directories
      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "scan-linked" ? { ...t, status: "running" } : t
        )
      );

      const linkedResult = await documentsApi.syncLinkedDirectories(caseData.id);
      const linkedDetails: string[] = [];
      if (linkedResult.added > 0) {
        linkedDetails.push(`${linkedResult.added} fichier(s) ajouté(s)`);
      }
      if (linkedResult.updated > 0) {
        linkedDetails.push(`${linkedResult.updated} fichier(s) mis à jour`);
      }
      if (linkedResult.removed > 0) {
        linkedDetails.push(`${linkedResult.removed} fichier(s) supprimé(s)`);
      }

      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "scan-linked"
            ? { ...t, status: "completed", details: linkedDetails.length > 0 ? linkedDetails : ["Aucun changement"] }
            : t
        )
      );

      // Step 3: Refresh documents list
      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "refresh" ? { ...t, status: "running" } : t
        )
      );

      if (onDocumentsChange) {
        await onDocumentsChange();
      }

      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "refresh" ? { ...t, status: "completed" } : t
        )
      );

      // Set final result
      setSyncResult({
        uploadedDiscovered: uploadResult.discovered,
        linkedAdded: linkedResult.added,
        linkedUpdated: linkedResult.updated,
        linkedRemoved: linkedResult.removed,
      });

      setSyncComplete(true);
      setSyncHasError(false);
    } catch (err) {
      // Mark current running task as error
      setSyncTasks((prev) =>
        prev.map((t) =>
          t.status === "running"
            ? {
                ...t,
                status: "error",
                error: err instanceof Error ? err.message : "Erreur inconnue",
              }
            : t
        )
      );
      setSyncComplete(true);
      setSyncHasError(true);
      toast.error("Erreur lors de la synchronisation");
    }
  };

  // Check if document is an audio file
  const isAudioFile = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return audioExtensions.includes(ext) || (doc.type_mime?.includes("audio") ?? false);
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
      const updateData: any = {
        description: editDescription,
      };

      // Add academic fields if they have values
      if (editSessionId) updateData.session_id = editSessionId;
      if (editCourseCode) updateData.course_code = editCourseCode;
      if (editProfessor) updateData.professor = editProfessor;
      if (editCredits) updateData.credits = parseInt(editCredits, 10);
      if (editColor) updateData.color = editColor;

      await onUpdateCase(updateData);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditDescription(caseData.description || "");
    setEditSessionId(caseData.session_id || "");
    setEditCourseCode(caseData.course_code || "");
    setEditProfessor(caseData.professor || "");
    setEditCredits(caseData.credits?.toString() || "3");
    setEditColor(caseData.color || "#3B82F6");
    setIsEditing(false);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Case Header */}
      <div className="p-4 border-b bg-background flex items-center justify-between shrink-0">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-bold">
            {caseData.course_code
              ? `${caseData.course_code} ${caseData.title || "Sans titre"}`
              : caseData.title || "Sans titre"}
          </h2>
        </div>
      </div>

      {/* Contenu principal avec padding */}
      <div className="px-6 py-2 space-y-4 flex-1 min-h-0 overflow-y-auto">
        {/* Mode édition */}
        {isEditing && (
          <div className="space-y-4 p-4 border rounded-lg bg-muted/50">
            <h3 className="font-semibold text-sm">{t("courses.editCourse")}</h3>

            {/* Academic fields */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm text-muted-foreground">{t("courses.academicInfo")}</h4>

              <div className="space-y-2">
                <Label htmlFor="edit-session">{t("courses.session")}</Label>
                <SessionSelector
                  value={editSessionId}
                  onValueChange={setEditSessionId}
                  disabled={isSaving}
                  placeholder={t("courses.selectSession")}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-course-code">{t("courses.courseCode")}</Label>
                  <Input
                    id="edit-course-code"
                    value={editCourseCode}
                    onChange={(e) => setEditCourseCode(e.target.value)}
                    placeholder="Ex: DRT-1151G"
                    disabled={isSaving}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-credits">{t("courses.credits")}</Label>
                  <Input
                    id="edit-credits"
                    type="number"
                    min="0"
                    max="6"
                    value={editCredits}
                    onChange={(e) => setEditCredits(e.target.value)}
                    disabled={isSaving}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-description">{t("courses.description")}</Label>
                <Textarea
                  id="edit-description"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder={t("courses.descriptionPlaceholder")}
                  disabled={isSaving}
                  className="text-sm min-h-[80px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-professor">{t("courses.professor")}</Label>
                <Input
                  id="edit-professor"
                  value={editProfessor}
                  onChange={(e) => setEditProfessor(e.target.value)}
                  placeholder="Ex: Prof. Dupont"
                  disabled={isSaving}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-color">{t("courses.color")}</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="edit-color"
                    type="color"
                    value={editColor}
                    onChange={(e) => setEditColor(e.target.value)}
                    disabled={isSaving}
                    className="w-20 h-10"
                  />
                  <span className="text-sm text-muted-foreground">{editColor}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
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
                {t("common.save")}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                <X className="h-4 w-4" />
                {t("common.cancel")}
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
            <span>{t("common.edit")}</span>
          </Button>
          <Button
            size="sm"
            onClick={onLinkFile}
            className="gap-2"
          >
            <Folder className="h-4 w-4" />
            <span>{t("courses.linkDirectory")}</span>
          </Button>
          <Button
            size="sm"
            onClick={onUploadDocuments}
            className="gap-2"
          >
            <FileUp className="h-4 w-4" />
            <span>{t("documents.addDocuments")}</span>
          </Button>
          <Button
            size="sm"
            onClick={onRecordAudio}
            className="gap-2"
          >
            <Mic className="h-4 w-4" />
            <span>{t("courses.recordAudio")}</span>
          </Button>
          <Button
            size="sm"
            onClick={onYouTubeImport}
            className="gap-2"
          >
            <Youtube className="h-4 w-4" />
            <span>{t("courses.youtube")}</span>
          </Button>
          <Button
            size="sm"
            onClick={handleSyncDocuments}
            disabled={syncModalOpen && !syncComplete}
            className="gap-2"
          >
            {syncModalOpen && !syncComplete ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span>{t("courses.synchronize")}</span>
          </Button>
        </div>

      {/* Répertoires liés */}
      {(() => {
        const linkedDocs = documents.filter((doc) => doc.source_type === "linked");
        const docusaurusDocs = documents.filter((doc) => doc.source_type === "docusaurus");

        // Debug: afficher les source_types trouvés
        console.log("Documents source types:", {
          linked: linkedDocs.length,
          docusaurus: docusaurusDocs.length,
          total: documents.length,
          allSourceTypes: documents.map(d => d.source_type)
        });

        console.log("LinkedDirectoriesSection condition check:", {
          hasLinkedDocs: linkedDocs.length > 0,
          linkedDocsCount: linkedDocs.length,
          hasOnDocumentsChange: !!onDocumentsChange,
          onDocumentsChangeType: typeof onDocumentsChange,
          willRender: linkedDocs.length > 0 && !!onDocumentsChange
        });

        if (linkedDocs.length > 0 && onDocumentsChange) {
          console.log("✅ Rendering LinkedDirectoriesSection with", linkedDocs.length, "documents");
          return (
            <div className="mb-4">
              <LinkedDirectoriesSection
                caseId={caseData.id}
                documents={linkedDocs}
                onDocumentsChange={onDocumentsChange}
                onPreviewDirectory={onPreviewDirectory}
              />
            </div>
          );
        }
        console.log("❌ NOT rendering LinkedDirectoriesSection");
        return null;
      })()}

      {/* Liste des documents */}
      <div className="space-y-2">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <FileText className="h-4 w-4" />
          {t("documents.title")} ({documents.filter((doc) => doc.source_type !== "linked").length})
        </h3>

        {/* DataTable with filters */}
        <DocumentsDataTable
          documents={documents.filter((doc) => doc.source_type !== "linked")}
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
              {t("common.delete")}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t("table.confirmDeletion")}</AlertDialogTitle>
              <AlertDialogDescription>
                {t("courses.deleteWarning")}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
              <AlertDialogAction onClick={onDelete}>
                {t("common.delete")}
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

      {/* Sync Progress Modal */}
      <SyncProgressModal
        open={syncModalOpen}
        onOpenChange={setSyncModalOpen}
        tasks={syncTasks}
        result={syncResult}
        isComplete={syncComplete}
        hasError={syncHasError}
      />
    </div>
  );
}
