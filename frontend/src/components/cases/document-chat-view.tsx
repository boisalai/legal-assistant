"use client";

import { useState, useRef, useEffect } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { Button } from "@/components/ui/button";
import { X, Maximize2, Minimize2, ChevronDown, ChevronUp } from "lucide-react";
import { PDFViewer, type PDFViewerHandle } from "./pdf-viewer";
import { MarkdownViewer, type MarkdownViewerHandle } from "./markdown-viewer";
import { AssistantPanel, type Message } from "./assistant-panel";
import { SourceNavigator } from "./source-navigator";
import { useCitationDetection } from "@/hooks/use-citation-detection";
import type { Document } from "@/types";
import { cn } from "@/lib/utils";

interface DocumentChatViewProps {
  document: Document;
  caseId: string;
  documents: Document[];
  onClose: () => void;
  onDocumentChange?: (documentId: string) => void;
  messages?: Message[];
  setMessages?: React.Dispatch<React.SetStateAction<Message[]>>;
  onDocumentCreated?: () => void;
}

export function DocumentChatView({
  document,
  caseId,
  documents,
  onClose,
  onDocumentChange,
  messages: controlledMessages,
  setMessages: controlledSetMessages,
  onDocumentCreated,
}: DocumentChatViewProps) {
  const [activeDocument, setActiveDocument] = useState<Document>(document);
  const [highlightPage, setHighlightPage] = useState<number | null>(null);
  const [isFullWidth, setIsFullWidth] = useState(false);
  const [showSourceNav, setShowSourceNav] = useState(true);

  const pdfViewerRef = useRef<PDFViewerHandle>(null);
  const markdownViewerRef = useRef<MarkdownViewerHandle>(null);

  // Internal messages state if not provided by parent
  const [internalMessages, setInternalMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Je peux vous aider à analyser le document "${activeDocument.nom_fichier}". Posez-moi des questions!`,
    },
  ]);

  const messages = controlledMessages ?? internalMessages;
  const setMessages = controlledSetMessages ?? setInternalMessages;

  // Detect citations in messages
  const citations = useCitationDetection(messages, documents);

  // Update active document when prop changes
  useEffect(() => {
    setActiveDocument(document);
  }, [document]);

  // Determine file type
  const ext = activeDocument.nom_fichier?.split(".").pop()?.toLowerCase() || "";
  const isPdf =
    activeDocument.type_mime?.includes("pdf") ||
    activeDocument.type_fichier === "pdf" ||
    ext === "pdf";
  const isMarkdown =
    activeDocument.type_mime?.includes("markdown") ||
    activeDocument.type_fichier === "md" ||
    ext === "md" ||
    ext === "markdown";

  // Build document URL
  const cleanCaseId = caseId.replace("judgment:", "");
  const cleanDocId = activeDocument.id.replace("document:", "");
  const documentUrl = `${
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  }/api/cases/${cleanCaseId}/documents/${cleanDocId}/download?inline=true`;

  // Handle source navigation
  const handleSourceClick = (documentId: string, page?: number) => {
    const targetDoc = documents.find((d) => d.id === documentId);
    if (targetDoc) {
      setActiveDocument(targetDoc);
      if (onDocumentChange) {
        onDocumentChange(documentId);
      }

      if (page) {
        setHighlightPage(page);
        // Scroll to page
        if (isPdf && pdfViewerRef.current) {
          pdfViewerRef.current.scrollToPage(page);
        }
      }
    }
  };

  // Auto-detect latest citation and scroll
  useEffect(() => {
    if (citations.length > 0) {
      const latestCitation = citations[citations.length - 1];
      if (
        latestCitation.documentId === activeDocument.id &&
        latestCitation.page
      ) {
        setHighlightPage(latestCitation.page);
        if (isPdf && pdfViewerRef.current) {
          setTimeout(() => {
            pdfViewerRef.current?.scrollToPage(latestCitation.page!);
          }, 500);
        }
      }
    }
  }, [citations, activeDocument.id, isPdf]);

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="font-semibold text-sm truncate">
            {activeDocument.nom_fichier}
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2"
            onClick={() => setIsFullWidth(!isFullWidth)}
            title={isFullWidth ? "Vue partagée" : "Document pleine largeur"}
          >
            {isFullWidth ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onClose}
            title="Fermer"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main content: Document + Chat */}
      <div className="flex-1 overflow-hidden">
        {isFullWidth ? (
          // Full-width document view
          <div className="h-full">
            {isPdf && (
              <PDFViewer
                ref={pdfViewerRef}
                url={documentUrl}
                fileName={activeDocument.nom_fichier || ""}
                highlightPage={highlightPage}
              />
            )}
            {isMarkdown && activeDocument.texte_extrait && (
              <MarkdownViewer
                ref={markdownViewerRef}
                content={activeDocument.texte_extrait}
                fileName={activeDocument.nom_fichier || ""}
              />
            )}
          </div>
        ) : (
          // Split view: Document (50%) + Chat (50%)
          <PanelGroup direction="horizontal">
            {/* Left: Document viewer */}
            <Panel defaultSize={50} minSize={30}>
              {isPdf && (
                <PDFViewer
                  ref={pdfViewerRef}
                  url={documentUrl}
                  fileName={activeDocument.nom_fichier || ""}
                  highlightPage={highlightPage}
                />
              )}
              {isMarkdown && activeDocument.texte_extrait && (
                <MarkdownViewer
                  ref={markdownViewerRef}
                  content={activeDocument.texte_extrait}
                  fileName={activeDocument.nom_fichier || ""}
                />
              )}
              {!isPdf && !isMarkdown && (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <p>Aperçu non disponible pour ce type de fichier</p>
                </div>
              )}
            </Panel>

            {/* Resize handle */}
            <PanelResizeHandle className="w-px bg-border hover:bg-primary/50 transition-colors" />

            {/* Right: Chat + Sources */}
            <Panel defaultSize={50} minSize={30}>
              <div className="flex flex-col h-full">
                {/* Assistant panel */}
                <div className="flex-1 overflow-hidden min-h-0">
                  <AssistantPanel
                    caseId={caseId}
                    messages={messages}
                    setMessages={setMessages}
                    onDocumentCreated={onDocumentCreated}
                    hasDocuments={documents.length > 0}
                  />
                </div>

                {/* Source navigator (collapsible) */}
                {showSourceNav && citations.length > 0 && (
                  <>
                    <div className="border-t" />
                    <div className="max-h-48 overflow-y-auto border-t bg-muted/10 shrink-0">
                      <SourceNavigator
                        citations={citations}
                        activeDocumentId={activeDocument.id}
                        activePage={highlightPage}
                        onSourceClick={handleSourceClick}
                      />
                    </div>
                  </>
                )}
              </div>
            </Panel>
          </PanelGroup>
        )}
      </div>
    </div>
  );
}
