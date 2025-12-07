"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/layout";
import { CaseDetailsPanel } from "@/components/cases/case-details-panel";
import { AssistantPanel, type Message } from "@/components/cases/assistant-panel";
import { DocumentPreviewPanel } from "@/components/cases/document-preview-panel";
import { DocumentUploadModal } from "@/components/cases/document-upload-modal";
import { AudioRecorderModal } from "@/components/cases/audio-recorder-modal";
import { LinkFileModal } from "@/components/cases/link-file-modal";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { casesApi, documentsApi, analysisApi } from "@/lib/api";
import type { Case, Checklist, Document } from "@/types";

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();

  // Use the raw ID - the API will handle the judgment: prefix
  const rawId = params.id as string;
  const caseId = rawId;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [audioModalOpen, setAudioModalOpen] = useState(false);
  const [linkFileModalOpen, setLinkFileModalOpen] = useState(false);
  const [previewDocument, setPreviewDocument] = useState<Document | null>(null);

  // Assistant messages - lifted to parent to persist across preview open/close
  const [assistantMessages, setAssistantMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Bonjour! Je suis votre assistant IA. Comment puis-je vous aider avec ce dossier?",
    },
  ]);

  const fetchCaseDetails = useCallback(async () => {
    try {
      const data = await casesApi.get(caseId);
      setCaseData(data);

      try {
        const docs = await documentsApi.list(caseId);
        setDocuments(docs);
      } catch {
        // Documents endpoint may not exist yet
      }

      if (data.status && ["termine", "summarized", "analyse_complete", "complete"].includes(data.status)) {
        try {
          const checklistData = await analysisApi.getChecklist(caseId);
          setChecklist(checklistData);
        } catch {
          // Checklist may not exist yet
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) fetchCaseDetails();
  }, [caseId, fetchCaseDetails]);

  // Poll for updates during analysis
  useEffect(() => {
    if (caseData?.status === "en_analyse" || caseData?.status === "analyzing") {
      const interval = setInterval(fetchCaseDetails, 5000);
      return () => clearInterval(interval);
    }
  }, [caseData?.status, fetchCaseDetails]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await casesApi.delete(caseId);
      toast.success("Dossier supprimé avec succès");
      router.push("/cases");
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
    setLinkFileModalOpen(true);
  };

  const handleUploadComplete = async () => {
    // Refresh documents list
    await fetchCaseDetails();
  };

  const handleAnalyze = async () => {
    try {
      await analysisApi.start(caseId);
      toast.success("Analyse demarree");
      await fetchCaseDetails();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de l'analyse");
    }
  };

  const handleAnalysisComplete = useCallback(async () => {
    toast.success("Analyse terminee!");
    await fetchCaseDetails();
  }, [fetchCaseDetails]);

  const handleDocumentCreated = useCallback(async () => {
    // Refresh documents list when a new document is created via chat (e.g., transcription)
    await fetchCaseDetails();
  }, [fetchCaseDetails]);

  const handleUpdateCase = async (data: { description?: string; type_transaction?: string }) => {
    try {
      // @ts-ignore - TODO: Implement update method in casesApi or remove this functionality
      const updated = await casesApi.update(caseId, data as any);
      setCaseData(updated);
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
      const filename = doc?.nom_fichier;
      const filePath = doc?.file_path;

      await documentsApi.delete(caseId, docId, filename, filePath);
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
    }
  };

  const handleClosePreview = () => {
    setPreviewDocument(null);
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

  if (error || !caseData) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-full gap-4">
          <p className="text-lg text-destructive">
            {error?.replace("Jugement", "Dossier") || "Dossier introuvable"}
          </p>
          <Button asChild>
            <Link href="/cases">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour aux dossiers
            </Link>
          </Button>
        </div>
      </AppShell>
    );
  }

  const isAnalyzing = caseData.status === "en_analyse" || caseData.status === "analyzing";

  return (
    <AppShell noPadding>
      <div className="flex flex-col h-full max-h-full">
        {/* Split View */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <PanelGroup direction="horizontal" className="h-full">
            {/* Left Panel: Case Details */}
            <Panel defaultSize={60} minSize={30} className="overflow-hidden">
              <CaseDetailsPanel
                caseData={caseData}
                documents={documents}
                checklist={checklist}
                onUploadDocuments={handleUploadDocuments}
                onRecordAudio={handleRecordAudio}
                onLinkFile={handleLinkFile}
                onAnalyze={handleAnalyze}
                onUpdateCase={handleUpdateCase}
                onDeleteDocument={handleDeleteDocument}
                onPreviewDocument={handlePreviewDocument}
                onDelete={handleDelete}
                onAnalysisComplete={handleAnalysisComplete}
                onDocumentsChange={fetchCaseDetails}
                deleting={deleting}
                isAnalyzing={isAnalyzing}
              />
            </Panel>

            {/* Resize Handle */}
            <PanelResizeHandle className="w-px bg-border hover:bg-primary/50 transition-colors" />

            {/* Right Panel: Document Preview (top) + AI Assistant (bottom) */}
            <Panel defaultSize={40} minSize={30} className="overflow-hidden">
              {previewDocument ? (
                <PanelGroup direction="vertical" className="h-full">
                  {/* Document Preview Panel (top) */}
                  <Panel defaultSize={50} minSize={20} className="overflow-hidden">
                    <DocumentPreviewPanel
                      document={previewDocument}
                      caseId={caseId}
                      onClose={handleClosePreview}
                    />
                  </Panel>

                  {/* Vertical Resize Handle */}
                  <PanelResizeHandle className="h-px bg-border hover:bg-primary/50 transition-colors" />

                  {/* AI Assistant Panel (bottom) */}
                  <Panel defaultSize={50} minSize={20} className="overflow-hidden">
                    <div className="h-full overflow-hidden">
                      <AssistantPanel
                        caseId={caseId}
                        onAnalyze={handleAnalyze}
                        isAnalyzing={isAnalyzing}
                        hasDocuments={documents.length > 0}
                        onDocumentCreated={handleDocumentCreated}
                        messages={assistantMessages}
                        setMessages={setAssistantMessages}
                      />
                    </div>
                  </Panel>
                </PanelGroup>
              ) : (
                <div className="h-full overflow-hidden">
                  <AssistantPanel
                    caseId={caseId}
                    onAnalyze={handleAnalyze}
                    isAnalyzing={isAnalyzing}
                    hasDocuments={documents.length > 0}
                    onDocumentCreated={handleDocumentCreated}
                    messages={assistantMessages}
                    setMessages={setAssistantMessages}
                  />
                </div>
              )}
            </Panel>
          </PanelGroup>
        </div>

        {/* Modals */}
        <DocumentUploadModal
          open={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          caseId={caseId}
          onUploadComplete={handleUploadComplete}
        />
        <AudioRecorderModal
          open={audioModalOpen}
          onClose={() => setAudioModalOpen(false)}
          caseId={caseId}
          onUploadComplete={handleUploadComplete}
        />
        <LinkFileModal
          open={linkFileModalOpen}
          onClose={() => setLinkFileModalOpen(false)}
          caseId={caseId}
          onLinkComplete={handleUploadComplete}
        />
      </div>
    </AppShell>
  );
}
