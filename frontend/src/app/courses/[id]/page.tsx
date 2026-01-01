"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/layout";
import { CaseDetailsPanel } from "@/components/cases/course-details-panel";
import { AssistantPanel, type Message } from "@/components/cases/assistant-panel";
import { DocumentPreviewPanel } from "@/components/cases/document-preview-panel";
import { DirectoryTreeView } from "@/components/cases/directory-tree-view";
import { DocumentUploadModal } from "@/components/cases/document-upload-modal";
import { AudioRecorderModal } from "@/components/cases/audio-recorder-modal";
import { LinkDirectoryModal } from "@/components/cases/link-directory-modal";
import { YouTubeDownloadModal } from "@/components/cases/youtube-download-modal";
import { EditCourseModal } from "@/components/cases/edit-course-modal";
import { CreateFlashcardDeckModal } from "@/components/cases/create-flashcard-deck-modal";
import { FlashcardStudyPanel } from "@/components/cases/flashcard-study-panel";
import { FlashcardAudioPanel } from "@/components/cases/flashcard-audio-panel";
import type { LinkedDirectory } from "@/components/cases/linked-directories-data-table";
import type { FlashcardDeck } from "@/types";
import { ArrowLeft, Loader2, X, Folder } from "lucide-react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { coursesApi, documentsApi } from "@/lib/api";
import type { Course, Checklist, Document } from "@/types";

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const t = useTranslations();

  // Use the raw ID - the API will handle the judgment: prefix
  const rawId = params.id as string;
  const courseId = rawId;

  const [courseData, setCourseData] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [audioModalOpen, setAudioModalOpen] = useState(false);
  const [linkDirectoryModalOpen, setLinkDirectoryModalOpen] = useState(false);
  const [youtubeModalOpen, setYoutubeModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [previewDocument, setPreviewDocument] = useState<Document | null>(null);
  const [previewDirectory, setPreviewDirectory] = useState<LinkedDirectory | null>(null);
  const [createDeckModalOpen, setCreateDeckModalOpen] = useState(false);
  const [studyDeck, setStudyDeck] = useState<FlashcardDeck | null>(null);
  const [audioDeck, setAudioDeck] = useState<FlashcardDeck | null>(null);
  const [flashcardsRefreshKey, setFlashcardsRefreshKey] = useState(0);

  // Assistant messages - lifted to parent to persist across preview open/close
  const [assistantMessages, setAssistantMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Bonjour! Je suis votre assistant IA. Comment puis-je vous aider avec ce dossier?",
    },
  ]);

  const fetchCaseDetails = useCallback(async () => {
    try {
      const data = await coursesApi.get(courseId);
      setCourseData(data);

      try {
        const docs = await documentsApi.list(courseId);
        setDocuments(docs);
      } catch {
        // Documents endpoint may not exist yet
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    if (courseId) fetchCaseDetails();
  }, [courseId, fetchCaseDetails]);

  // Poll for updates during analysis
  useEffect(() => {
    if (courseData?.status === "en_analyse" || courseData?.status === "analyzing") {
      const interval = setInterval(fetchCaseDetails, 5000);
      return () => clearInterval(interval);
    }
  }, [courseData?.status, fetchCaseDetails]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await coursesApi.delete(courseId);
      toast.success("Dossier supprimé avec succès");
      router.push("/courses");
    } catch (err) {
      toast.error("Erreur lors de la suppression");
      setDeleting(false);
    }
  };

  const handleUploadDocuments = () => {
    setUploadModalOpen(true);
  };

  const handleRecordAudio = () => {
    setAudioModalOpen(true);
  };

  const handleLinkFile = () => {
    setLinkDirectoryModalOpen(true);
  };

  const handleYouTubeImport = () => {
    setYoutubeModalOpen(true);
  };

  const handleEdit = () => {
    setEditModalOpen(true);
  };

  const handleUploadComplete = async () => {
    // Refresh documents list
    await fetchCaseDetails();
  };

  const handleDocumentCreated = useCallback(async () => {
    // Refresh documents list when a new document is created via chat (e.g., transcription)
    await fetchCaseDetails();
  }, [fetchCaseDetails]);

  const handleUpdateCase = async (data: { description?: string; type_transaction?: string }) => {
    try {
      const updated = await coursesApi.update(courseId, data);
      setCourseData(updated);
      toast.success("Dossier mis à jour avec succès");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la mise à jour");
      throw err;
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    try {
      // Find the document to get its filename and file_path
      const doc = documents.find((d) => d.id === docId);
      const filename = doc?.filename;
      const filePath = doc?.file_path;

      await documentsApi.delete(courseId, docId, filename, filePath);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      toast.success("Document retiré");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors du retrait");
    }
  };

  const handlePreviewDocument = (docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    if (doc) {
      setPreviewDocument(doc);
      setPreviewDirectory(null); // Close directory preview if open
    }
  };

  const handlePreviewDirectory = (directory: LinkedDirectory) => {
    setPreviewDirectory(directory);
    setPreviewDocument(null); // Close document preview if open
  };

  const handleClosePreview = () => {
    // If we're viewing a document, just close it and return to previous view
    // (either directory tree or case details panel)
    if (previewDocument) {
      setPreviewDocument(null);
      // Keep previewDirectory as is - if it was set, we return to tree view
    } else {
      // If we're viewing directory tree, close it and return to case details
      setPreviewDirectory(null);
    }
  };

  // Flashcard handlers
  const handleStudyDeck = (deck: FlashcardDeck) => {
    setStudyDeck(deck);
    setAudioDeck(null);
    setPreviewDocument(null);
    setPreviewDirectory(null);
  };

  const handleCreateDeck = () => {
    setCreateDeckModalOpen(true);
  };

  const handleCloseStudy = () => {
    setStudyDeck(null);
  };

  const handleListenFlashcardAudio = (deck: FlashcardDeck) => {
    setAudioDeck(deck);
    setStudyDeck(null);
    setPreviewDocument(null);
    setPreviewDirectory(null);
  };

  const handleCloseAudio = () => {
    setAudioDeck(null);
  };

  const handleFlashcardsUpdated = async () => {
    // Refresh deck list by incrementing refresh key
    setFlashcardsRefreshKey((prev) => prev + 1);
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error || !courseData) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-full gap-4">
          <p className="text-lg text-destructive">
            {error || "Cours introuvable"}
          </p>
          <Button asChild>
            <Link href="/courses">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour aux cours
            </Link>
          </Button>
        </div>
      </AppShell>
    );
  }

  const isAnalyzing = courseData.status === "en_analyse" || courseData.status === "analyzing";

  return (
    <AppShell noPadding>
      <div className="flex flex-col h-full max-h-full">
        {/* Split View */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <PanelGroup direction="horizontal" className="h-full">
            {/* Left Panel: Case Details, Document Preview, Directory Tree, Flashcard Study, or Flashcard Audio */}
            <Panel defaultSize={60} minSize={30} className="overflow-hidden">
              {studyDeck ? (
                <FlashcardStudyPanel
                  deck={studyDeck}
                  onClose={handleCloseStudy}
                  onDeckUpdate={handleFlashcardsUpdated}
                />
              ) : audioDeck ? (
                <FlashcardAudioPanel
                  deck={audioDeck}
                  courseId={courseId}
                  onClose={handleCloseAudio}
                />
              ) : previewDocument ? (
                <DocumentPreviewPanel
                  document={previewDocument}
                  caseId={courseId}
                  onClose={handleClosePreview}
                />
              ) : previewDirectory ? (
                <div className="flex flex-col h-full overflow-hidden">
                  {/* Header - matching AssistantPanel style */}
                  <div className="p-4 border-b bg-background flex items-center justify-between shrink-0 min-h-[65px]">
                    <div className="flex flex-col gap-1 flex-1 min-w-0">
                      <h2 className="text-xl font-bold">{t("courses.directoryContent")}</h2>
                      <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                        <Folder className="h-4 w-4 flex-shrink-0" />
                        <span className="truncate">
                          {previewDirectory.basePath}
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={handleClosePreview}
                      className="shrink-0 ml-4"
                    >
                      <X className="h-5 w-5" />
                    </Button>
                  </div>

                  {/* Content */}
                  <div className="flex-1 overflow-auto p-6">
                    <DirectoryTreeView
                      documents={previewDirectory.documents}
                      basePath={previewDirectory.basePath}
                      caseId={courseId}
                      onPreviewDocument={handlePreviewDocument}
                      onExtractPDF={async (doc) => {
                        try {
                          toast.info("Extraction en cours...");
                          const result = await documentsApi.extractPDFToMarkdown(courseId, doc.id);
                          if (result.success) {
                            toast.success("Markdown créé avec succès");
                            await fetchCaseDetails();
                          } else {
                            toast.error(result.error || "Erreur lors de l'extraction");
                          }
                        } catch (err) {
                          toast.error(err instanceof Error ? err.message : "Erreur lors de l'extraction");
                        }
                      }}
                      onTranscribe={async (doc) => {
                        try {
                          toast.info("Transcription en cours...");
                          const result = await documentsApi.transcribeWithWorkflow(courseId, doc.id, {
                            language: "fr",
                            createMarkdown: true,
                          });
                          if (result.success) {
                            toast.success("Transcription terminée");
                            await fetchCaseDetails();
                          } else {
                            toast.error(result.error || "Erreur lors de la transcription");
                          }
                        } catch (err) {
                          toast.error(err instanceof Error ? err.message : "Erreur lors de la transcription");
                        }
                      }}
                    />
                  </div>
                </div>
              ) : (
                <CaseDetailsPanel
                  caseData={courseData}
                  documents={documents}
                  checklist={checklist}
                  onUploadDocuments={handleUploadDocuments}
                  onRecordAudio={handleRecordAudio}
                  onLinkFile={handleLinkFile}
                  onYouTubeImport={handleYouTubeImport}
                  onEdit={handleEdit}
                  onUpdateCase={handleUpdateCase}
                  onDeleteDocument={handleDeleteDocument}
                  onPreviewDocument={handlePreviewDocument}
                  onPreviewDirectory={handlePreviewDirectory}
                  onDelete={handleDelete}
                  onDocumentsChange={fetchCaseDetails}
                  deleting={deleting}
                  isAnalyzing={isAnalyzing}
                  onStudyDeck={handleStudyDeck}
                  onCreateDeck={handleCreateDeck}
                  onListenFlashcardAudio={handleListenFlashcardAudio}
                  flashcardsRefreshKey={flashcardsRefreshKey}
                />
              )}
            </Panel>

            {/* Resize Handle */}
            <PanelResizeHandle className="w-px bg-border hover:bg-primary/50 transition-colors" />

            {/* Right Panel: AI Assistant */}
            <Panel defaultSize={40} minSize={30} className="overflow-hidden">
              <div className="h-full overflow-hidden">
                <AssistantPanel
                  caseId={courseId}
                  isAnalyzing={isAnalyzing}
                  hasDocuments={documents.length > 0}
                  onDocumentCreated={handleDocumentCreated}
                  messages={assistantMessages}
                  setMessages={setAssistantMessages}
                />
              </div>
            </Panel>
          </PanelGroup>
        </div>

        {/* Modals */}
        <DocumentUploadModal
          open={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          caseId={courseId}
          onUploadComplete={handleUploadComplete}
        />
        <AudioRecorderModal
          open={audioModalOpen}
          onClose={() => setAudioModalOpen(false)}
          caseId={courseId}
          onUploadComplete={handleUploadComplete}
        />
        <LinkDirectoryModal
          open={linkDirectoryModalOpen}
          onOpenChange={setLinkDirectoryModalOpen}
          caseId={courseId}
          onLinkSuccess={handleUploadComplete}
        />

        {/* YouTube Download Modal */}
        <YouTubeDownloadModal
          open={youtubeModalOpen}
          onClose={() => setYoutubeModalOpen(false)}
          caseId={courseId}
          onDownloadComplete={handleUploadComplete}
        />

        {/* Edit Course Modal */}
        <EditCourseModal
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          course={courseData}
          onSuccess={fetchCaseDetails}
        />

        {/* Create Flashcard Deck Modal */}
        <CreateFlashcardDeckModal
          open={createDeckModalOpen}
          onOpenChange={setCreateDeckModalOpen}
          courseId={courseId}
          documents={documents}
          onSuccess={handleFlashcardsUpdated}
        />
      </div>
    </AppShell>
  );
}
