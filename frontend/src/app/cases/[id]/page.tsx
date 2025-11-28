"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/layout";
import { CaseDetailsPanel } from "@/components/cases/case-details-panel";
import { AssistantPanel } from "@/components/cases/assistant-panel";
import { DocumentUploadModal } from "@/components/cases/document-upload-modal";
import { AudioRecorderModal } from "@/components/cases/audio-recorder-modal";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { casesApi, documentsApi, analysisApi } from "@/lib/api";
import type { Case, Checklist, Document } from "@/types";

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();

  // Reconstruct full ID with "dossier:" prefix if not present
  const rawId = params.id as string;
  const caseId = rawId.startsWith("dossier:") ? rawId : `dossier:${rawId}`;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [audioModalOpen, setAudioModalOpen] = useState(false);

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

      if (["analyse_complete", "complete"].includes(data.statut)) {
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
    if (caseData?.statut === "en_analyse") {
      const interval = setInterval(fetchCaseDetails, 5000);
      return () => clearInterval(interval);
    }
  }, [caseData?.statut, fetchCaseDetails]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await casesApi.delete(caseId);
      router.push("/cases");
    } catch (err) {
      alert("Erreur lors de la suppression");
      setDeleting(false);
    }
  };

  const handleUploadDocuments = () => {
    setUploadModalOpen(true);
  };

  const handleRecordAudio = () => {
    setAudioModalOpen(true);
  };

  const handleUploadComplete = async () => {
    // Refresh documents list
    await fetchCaseDetails();
  };

  const handleAnalyze = async () => {
    try {
      await analysisApi.start(caseId);
      await fetchCaseDetails();
    } catch (err) {
      alert(`Erreur: ${err instanceof Error ? err.message : "Erreur inconnue"}`);
    }
  };

  const handleUpdateSummary = async (summary: string) => {
    try {
      const updated = await casesApi.update(caseId, { summary } as any);
      setCaseData(updated);
    } catch (err) {
      alert(`Erreur: ${err instanceof Error ? err.message : "Erreur inconnue"}`);
      throw err;
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    try {
      await documentsApi.delete(caseId, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      alert(`Erreur: ${err instanceof Error ? err.message : "Erreur inconnue"}`);
    }
  };

  const handleDownloadDocument = (docId: string) => {
    // Trigger download
    window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/dossiers/${caseId}/documents/${docId}/download`, "_blank");
  };

  const handlePreviewDocument = (docId: string) => {
    // TODO: Open preview modal
    alert(`Prévisualisation du document ${docId}`);
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
            {error || "Dossier introuvable"}
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

  const isAnalyzing = caseData.statut === "en_analyse";

  return (
    <AppShell>
      <div className="flex flex-col h-full">
        {/* Split View */}
        <div className="flex-1 overflow-hidden">
          <PanelGroup direction="horizontal">
            {/* Left Panel: Case Details */}
            <Panel defaultSize={60} minSize={30}>
              <CaseDetailsPanel
                caseData={caseData}
                documents={documents}
                checklist={checklist}
                onUploadDocuments={handleUploadDocuments}
                onRecordAudio={handleRecordAudio}
                onAnalyze={handleAnalyze}
                onUpdateSummary={handleUpdateSummary}
                onDeleteDocument={handleDeleteDocument}
                onDownloadDocument={handleDownloadDocument}
                onPreviewDocument={handlePreviewDocument}
                onDelete={handleDelete}
                deleting={deleting}
                isAnalyzing={isAnalyzing}
              />
            </Panel>

            {/* Resize Handle */}
            <PanelResizeHandle className="w-px bg-border hover:bg-primary/50 transition-colors" />

            {/* Right Panel: AI Assistant */}
            <Panel defaultSize={40} minSize={30}>
              <AssistantPanel caseId={caseId} />
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
      </div>
    </AppShell>
  );
}
