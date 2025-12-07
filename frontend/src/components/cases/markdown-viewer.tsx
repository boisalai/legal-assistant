"use client";

import { useState, useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import { Button } from "@/components/ui/button";
import { Download, Maximize2, Type } from "lucide-react";
import { Markdown } from "@/components/ui/markdown";
import { cn } from "@/lib/utils";

interface MarkdownViewerProps {
  content: string;
  fileName: string;
  className?: string;
  highlightText?: string | null;
}

export interface MarkdownViewerHandle {
  scrollToText: (text: string) => void;
  highlightText: (text: string) => void;
}

export const MarkdownViewer = forwardRef<MarkdownViewerHandle, MarkdownViewerProps>(
  ({ content, fileName, className, highlightText }, ref) => {
    const [fontSize, setFontSize] = useState(14);
    const containerRef = useRef<HTMLDivElement>(null);
    const [highlightedText, setHighlightedText] = useState<string | null>(null);

    // Expose methods to parent via ref
    useImperativeHandle(ref, () => ({
      scrollToText: (text: string) => {
        if (!containerRef.current) return;

        // Find the text in the DOM
        const walker = document.createTreeWalker(
          containerRef.current,
          NodeFilter.SHOW_TEXT,
          null
        );

        let node: Node | null;
        while ((node = walker.nextNode())) {
          if (node.textContent?.toLowerCase().includes(text.toLowerCase())) {
            const element = node.parentElement;
            if (element) {
              element.scrollIntoView({ behavior: "smooth", block: "center" });
              // Temporarily highlight
              setHighlightedText(text);
              setTimeout(() => setHighlightedText(null), 3000);
              break;
            }
          }
        }
      },
      highlightText: (text: string) => {
        setHighlightedText(text);
      },
    }));

    // Auto-scroll when highlightText prop changes
    useEffect(() => {
      if (highlightText && containerRef.current) {
        const walker = document.createTreeWalker(
          containerRef.current,
          NodeFilter.SHOW_TEXT,
          null
        );

        let node: Node | null;
        while ((node = walker.nextNode())) {
          if (node.textContent?.toLowerCase().includes(highlightText.toLowerCase())) {
            const element = node.parentElement;
            if (element) {
              element.scrollIntoView({ behavior: "smooth", block: "center" });
              setHighlightedText(highlightText);
              setTimeout(() => setHighlightedText(null), 3000);
              break;
            }
          }
        }
      }
    }, [highlightText]);

    const handleIncreaseFontSize = () => {
      setFontSize((prev) => Math.min(prev + 2, 24));
    };

    const handleDecreaseFontSize = () => {
      setFontSize((prev) => Math.max(prev - 2, 10));
    };

    const handleDownload = () => {
      const blob = new Blob([content], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    };

    return (
      <div className={cn("flex flex-col h-full bg-background", className)}>
        {/* Toolbar */}
        <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30 gap-2">
          <div className="flex items-center gap-2">
            <Type className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium text-muted-foreground">Markdown</span>
          </div>

          <div className="flex items-center gap-1">
            {/* Font size controls */}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              onClick={handleDecreaseFontSize}
              disabled={fontSize <= 10}
              title="Réduire la taille du texte"
            >
              <span className="text-xs">A-</span>
            </Button>
            <span className="text-sm text-muted-foreground min-w-[2.5rem] text-center">
              {fontSize}px
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              onClick={handleIncreaseFontSize}
              disabled={fontSize >= 24}
              title="Augmenter la taille du texte"
            >
              <span className="text-xs">A+</span>
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

        {/* Markdown content */}
        <div
          ref={containerRef}
          className="flex-1 overflow-y-auto p-6"
          style={{ fontSize: `${fontSize}px` }}
        >
          <div className={cn(
            "prose prose-sm dark:prose-invert max-w-none",
            highlightedText && "prose-mark:bg-yellow-200 prose-mark:dark:bg-yellow-900"
          )}>
            <Markdown content={content} />
          </div>
        </div>
      </div>
    );
  }
);

MarkdownViewer.displayName = "MarkdownViewer";
