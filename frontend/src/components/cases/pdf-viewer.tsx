"use client";

import { useState, useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, Download } from "lucide-react";
import { cn } from "@/lib/utils";

interface PDFViewerProps {
  url: string;
  fileName: string;
  className?: string;
  onPageChange?: (page: number) => void;
  highlightPage?: number | null;
}

export interface PDFViewerHandle {
  scrollToPage: (page: number) => void;
}

export const PDFViewer = forwardRef<PDFViewerHandle, PDFViewerProps>(
  ({ url, fileName, className, onPageChange, highlightPage }, ref) => {
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState<number | null>(null);
    const [pageInput, setPageInput] = useState("1");
    const [zoom, setZoom] = useState(100);
    const iframeRef = useRef<HTMLIFrameElement>(null);

    // Expose scrollToPage method to parent via ref
    useImperativeHandle(ref, () => ({
      scrollToPage: (page: number) => {
        if (page >= 1 && (totalPages === null || page <= totalPages)) {
          setCurrentPage(page);
          setPageInput(page.toString());
          if (onPageChange) {
            onPageChange(page);
          }
        }
      },
    }));

    // Auto-scroll when highlightPage changes
    useEffect(() => {
      if (highlightPage !== null && highlightPage !== undefined && highlightPage !== currentPage) {
        setCurrentPage(highlightPage);
        setPageInput(highlightPage.toString());
        if (onPageChange) {
          onPageChange(highlightPage);
        }
      }
    }, [highlightPage, currentPage, onPageChange]);

    const handlePreviousPage = () => {
      if (currentPage > 1) {
        const newPage = currentPage - 1;
        setCurrentPage(newPage);
        setPageInput(newPage.toString());
        if (onPageChange) {
          onPageChange(newPage);
        }
      }
    };

    const handleNextPage = () => {
      if (totalPages === null || currentPage < totalPages) {
        const newPage = currentPage + 1;
        setCurrentPage(newPage);
        setPageInput(newPage.toString());
        if (onPageChange) {
          onPageChange(newPage);
        }
      }
    };

    const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setPageInput(e.target.value);
    };

    const handlePageInputSubmit = () => {
      const page = parseInt(pageInput, 10);
      if (!isNaN(page) && page >= 1 && (totalPages === null || page <= totalPages)) {
        setCurrentPage(page);
        if (onPageChange) {
          onPageChange(page);
        }
      } else {
        // Reset to current page if invalid
        setPageInput(currentPage.toString());
      }
    };

    const handlePageInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handlePageInputSubmit();
      }
    };

    const handleZoomIn = () => {
      setZoom((prev) => Math.min(prev + 10, 200));
    };

    const handleZoomOut = () => {
      setZoom((prev) => Math.max(prev - 10, 50));
    };

    const handleDownload = () => {
      window.open(url, "_blank");
    };

    // Build PDF URL with page parameter
    const pdfUrlWithPage = `${url}#page=${currentPage}&zoom=${zoom}`;

    return (
      <div className={cn("flex flex-col h-full bg-background", className)}>
        {/* Toolbar */}
        <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30 gap-2">
          <div className="flex items-center gap-1">
            {/* Page navigation */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handlePreviousPage}
              disabled={currentPage === 1}
              title="Page précédente"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="flex items-center gap-1 text-sm">
              <Input
                type="text"
                value={pageInput}
                onChange={handlePageInputChange}
                onBlur={handlePageInputSubmit}
                onKeyDown={handlePageInputKeyDown}
                className="h-8 w-12 text-center px-1"
              />
              <span className="text-muted-foreground">
                {totalPages ? `/ ${totalPages}` : ""}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleNextPage}
              disabled={totalPages !== null && currentPage >= totalPages}
              title="Page suivante"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex items-center gap-1">
            {/* Zoom controls */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleZoomOut}
              disabled={zoom <= 50}
              title="Zoom arrière"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground min-w-[3rem] text-center">
              {zoom}%
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleZoomIn}
              disabled={zoom >= 200}
              title="Zoom avant"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>

            {/* Download button */}
            <div className="h-4 w-px bg-border mx-1" />
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleDownload}
              title="Télécharger"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* PDF iframe */}
        <div className="flex-1 overflow-hidden relative">
          <iframe
            ref={iframeRef}
            src={pdfUrlWithPage}
            className="w-full h-full border-0"
            title={fileName}
          />
          {highlightPage === currentPage && (
            <div className="absolute top-0 left-0 right-0 h-1 bg-yellow-400 animate-pulse" />
          )}
        </div>
      </div>
    );
  }
);

PDFViewer.displayName = "PDFViewer";
