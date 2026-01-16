"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Edit2,
  MoreVertical,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import type { Course, Document, Checklist, FlashcardDeck, Module, AudioSummary } from "@/types";
import type { LinkedDirectory } from "./linked-directories-data-table";
import { CaseEditForm } from "./case-edit-form";
import { DocumentsSection } from "./documents-section";
import { SyncSection } from "./sync-section";
import { FlashcardsSection } from "./flashcards-section";
import { AudioSummarySection } from "./audio-summary-section";
import { ModulesSection } from "./modules-section";

interface CaseDetailsPanelProps {
  caseData: Course;
  documents: Document[];
  checklist: Checklist | null;
  onUploadDocuments: () => void;
  onRecordAudio: () => void;
  onLinkFile: () => void;
  onYouTubeImport: () => void;
  onAnalyze?: () => void;
  onEdit?: () => void;
  onUpdateCase: (data: {
    description?: string;
    type_transaction?: string;
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
  // Flashcard props
  onStudyDeck?: (deck: FlashcardDeck) => void;
  onCreateDeck?: () => void;
  onListenFlashcardAudio?: (deck: FlashcardDeck) => void;
  flashcardsRefreshKey?: number;
  // Module props
  onViewModule?: (module: Module) => void;
  // Audio summary props
  onCreateAudioSummary?: () => void;
  onPlayAudioSummary?: (summary: AudioSummary) => void;
  audioSummaryRefreshKey?: number;
}

export function CaseDetailsPanel({
  caseData,
  documents,
  checklist,
  onUploadDocuments,
  onRecordAudio,
  onLinkFile,
  onYouTubeImport,
  onEdit,
  onUpdateCase,
  onDeleteDocument,
  onPreviewDocument,
  onPreviewDirectory,
  onDelete,
  onDocumentsChange,
  deleting,
  onStudyDeck,
  onCreateDeck,
  onListenFlashcardAudio,
  flashcardsRefreshKey,
  onViewModule,
  onCreateAudioSummary,
  onPlayAudioSummary,
  audioSummaryRefreshKey,
}: CaseDetailsPanelProps) {
  const t = useTranslations();
  const [isEditing, setIsEditing] = useState(false);

  const handleSaveEdit = async (data: {
    description?: string;
    course_code?: string;
    professor?: string;
    credits?: number;
    color?: string;
  }) => {
    await onUpdateCase(data);
    setIsEditing(false);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Case Header */}
      <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
        <h2 className="text-xl font-bold">
          {caseData.course_code
            ? `${caseData.course_code} ${caseData.title || "Sans titre"}`
            : caseData.title || "Sans titre"}
        </h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreVertical className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => (onEdit ? onEdit() : setIsEditing(true))}>
              <Edit2 className="h-4 w-4 mr-2" />
              {t("common.edit")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Main content */}
      <div className="px-6 py-2 space-y-4 flex-1 min-h-0 overflow-y-auto">
        {/* Edit mode */}
        {isEditing && (
          <CaseEditForm
            caseData={caseData}
            onSave={handleSaveEdit}
            onCancel={() => setIsEditing(false)}
          />
        )}

        {/* Modules Section */}
        <div className="mb-4">
          <ModulesSection
            courseId={caseData.id}
            documents={documents}
            onDocumentsChange={onDocumentsChange}
            onViewModule={onViewModule}
          />
        </div>

        {/* Flashcards Section */}
        {onStudyDeck && onCreateDeck && (
          <div className="mb-4">
            <FlashcardsSection
              courseId={caseData.id}
              documents={documents}
              onStudyDeck={onStudyDeck}
              onCreateDeck={onCreateDeck}
              onListenAudio={onListenFlashcardAudio}
              refreshKey={flashcardsRefreshKey}
            />
          </div>
        )}

        {/* Audio Summary Section */}
        {onCreateAudioSummary && (
          <div className="mb-4">
            <AudioSummarySection
              courseId={caseData.id}
              documents={documents}
              modules={[]}
              onCreateSummary={onCreateAudioSummary}
              onPlayAudio={onPlayAudioSummary}
              refreshKey={audioSummaryRefreshKey}
            />
          </div>
        )}

        {/* Linked Directories & Sync */}
        <div className="mb-4">
          <SyncSection
            courseId={caseData.id}
            documents={documents}
            onDocumentsChange={onDocumentsChange}
            onPreviewDirectory={onPreviewDirectory}
            onLinkDirectory={onLinkFile}
          />
        </div>

        {/* Documents Section */}
        <DocumentsSection
          courseId={caseData.id}
          documents={documents}
          onUploadDocuments={onUploadDocuments}
          onRecordAudio={onRecordAudio}
          onYouTubeImport={onYouTubeImport}
          onPreviewDocument={onPreviewDocument}
          onDeleteDocument={onDeleteDocument}
          onDocumentsChange={onDocumentsChange}
        />

        {/* Checklist */}
        {checklist && (
          <>
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

      {/* Footer with delete button */}
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
              <AlertDialogAction
                onClick={onDelete}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {t("common.delete")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
