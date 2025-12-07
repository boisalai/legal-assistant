"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Citation } from "@/hooks/use-citation-detection";
import type { Document } from "@/types";

interface SourceNavigatorProps {
  citations: Citation[];
  activeDocumentId: string | null;
  activePage: number | null;
  onSourceClick: (documentId: string, page?: number) => void;
  className?: string;
}

export function SourceNavigator({
  citations,
  activeDocumentId,
  activePage,
  onSourceClick,
  className,
}: SourceNavigatorProps) {
  // Group citations by document
  const citationsByDocument = citations.reduce((acc, citation) => {
    if (!acc[citation.documentId]) {
      acc[citation.documentId] = [];
    }
    acc[citation.documentId].push(citation);
    return acc;
  }, {} as Record<string, Citation[]>);

  // Get unique pages for each document
  const uniqueCitationsByDocument = Object.entries(citationsByDocument).map(
    ([documentId, docCitations]) => {
      const pages = Array.from(
        new Set(docCitations.map((c) => c.page).filter((p) => p !== undefined))
      ).sort((a, b) => (a || 0) - (b || 0));

      return {
        documentId,
        documentName: docCitations[0].documentName,
        pages,
        citations: docCitations,
      };
    }
  );

  if (citations.length === 0) {
    return (
      <div className={cn("p-4 text-center text-sm text-muted-foreground", className)}>
        <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>Aucune source citée</p>
      </div>
    );
  }

  return (
    <div className={cn("p-3 space-y-3", className)}>
      <div className="flex items-center gap-2 mb-2">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">
          Sources citées ({uniqueCitationsByDocument.length})
        </h3>
      </div>

      <div className="space-y-2">
        {uniqueCitationsByDocument.map(({ documentId, documentName, pages }) => (
          <div
            key={documentId}
            className={cn(
              "rounded-lg border p-3 transition-colors",
              activeDocumentId === documentId
                ? "bg-primary/10 border-primary"
                : "bg-muted/50 hover:bg-muted"
            )}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" title={documentName}>
                  {documentName}
                </p>
              </div>
              {activeDocumentId !== documentId && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 shrink-0"
                  onClick={() => onSourceClick(documentId)}
                  title="Visualiser ce document"
                >
                  <Eye className="h-3 w-3" />
                </Button>
              )}
            </div>

            {pages.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {pages.map((page) => (
                  <Button
                    key={page}
                    variant={
                      activeDocumentId === documentId && activePage === page
                        ? "default"
                        : "outline"
                    }
                    size="sm"
                    className="h-6 px-2 text-xs"
                    onClick={() => onSourceClick(documentId, page)}
                    title={`Aller à la page ${page}`}
                  >
                    p. {page}
                  </Button>
                ))}
              </div>
            )}

            {pages.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Document mentionné (page non spécifiée)
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
