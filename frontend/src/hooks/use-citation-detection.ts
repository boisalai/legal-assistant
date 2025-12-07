import { useMemo } from "react";
import type { Message } from "@/components/cases/assistant-panel";
import type { Document } from "@/types";

export interface Citation {
  documentId: string;
  documentName: string;
  page?: number;
  text?: string;
  messageIndex: number;
}

/**
 * Detects citations in chat messages
 * Supports formats like:
 * - "page 12", "p. 5", "pages 3-5"
 * - "doc1.pdf page 12"
 * - "selon le document X.pdf"
 */
export function useCitationDetection(
  messages: Message[],
  documents: Document[]
): Citation[] {
  return useMemo(() => {
    const citations: Citation[] = [];

    messages.forEach((message, messageIndex) => {
      if (message.role !== "assistant") return;

      const content = message.content.toLowerCase();

      // Pattern 1: "page X" or "p. X" or "pages X-Y"
      const pagePatterns = [
        /\bpage\s+(\d+)/gi,
        /\bp\.\s*(\d+)/gi,
        /\bpages\s+(\d+)(?:\s*-\s*(\d+))?/gi,
      ];

      pagePatterns.forEach((pattern) => {
        const matches = Array.from(message.content.matchAll(pattern));
        matches.forEach((match) => {
          const page = parseInt(match[1], 10);
          if (!isNaN(page)) {
            // Try to find a document reference in the message
            // Look for sources or recent document mentions
            if (message.sources && message.sources.length > 0) {
              message.sources.forEach((source) => {
                const doc = documents.find((d) => d.nom_fichier === source.name);
                if (doc) {
                  citations.push({
                    documentId: doc.id,
                    documentName: doc.nom_fichier || "",
                    page,
                    messageIndex,
                  });
                }
              });
            }
          }
        });
      });

      // Pattern 2: "document X.pdf" or "fichier X.pdf" with optional page
      documents.forEach((doc) => {
        const fileName = doc.nom_fichier?.toLowerCase() || "";
        if (fileName && content.includes(fileName)) {
          // Check if there's a page reference nearby
          const docIndex = content.indexOf(fileName);
          const contextAfter = content.slice(docIndex, docIndex + 100);

          const pageMatch = contextAfter.match(/(?:page|p\.)\s*(\d+)/i);
          const page = pageMatch ? parseInt(pageMatch[1], 10) : undefined;

          citations.push({
            documentId: doc.id,
            documentName: doc.nom_fichier || "",
            page,
            messageIndex,
          });
        }
      });

      // Pattern 3: Sources mentioned explicitly
      if (message.sources && message.sources.length > 0) {
        message.sources.forEach((source) => {
          const doc = documents.find((d) => d.nom_fichier === source.name);
          if (doc) {
            // Only add if not already added
            const exists = citations.some(
              (c) =>
                c.documentId === doc.id &&
                c.messageIndex === messageIndex &&
                c.page === undefined
            );
            if (!exists) {
              citations.push({
                documentId: doc.id,
                documentName: doc.nom_fichier || "",
                messageIndex,
              });
            }
          }
        });
      }
    });

    // Deduplicate citations (same doc + page in same message)
    const uniqueCitations = citations.filter(
      (citation, index, self) =>
        index ===
        self.findIndex(
          (c) =>
            c.documentId === citation.documentId &&
            c.page === citation.page &&
            c.messageIndex === citation.messageIndex
        )
    );

    return uniqueCitations;
  }, [messages, documents]);
}
