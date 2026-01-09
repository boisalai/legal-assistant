"use client";

import * as React from "react";
import { useTranslations } from "next-intl";
import { ColumnDef, Table as TanstackTable } from "@tanstack/react-table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileText,
  Eye,
  Trash2,
  MoreVertical,
  Database,
  Loader2,
  DatabaseBackup,
  Mic,
  AlertCircle,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { GenericDataTable } from "@/components/ui/generic-data-table";
import { SortableHeader, DateCell } from "@/components/ui/column-helpers";
import type { Document } from "@/types";

interface DocumentsDataTableProps {
  documents: Document[];
  onPreview: (docId: string) => void;
  onDelete: (doc: Document) => void;
  onExtract: (doc: Document) => void;
  onExtractPDF: (doc: Document) => void;
  onTranscribe: (doc: Document) => void;
  onClearText: (doc: Document) => void;
  extractingDocId: string | null;
  extractingPDFDocId: string | null;
  transcribingDocId: string | null;
  clearingDocId: string | null;
  needsExtraction: (doc: Document) => boolean;
  isPDFFile: (doc: Document) => boolean;
  isAudioFile: (doc: Document) => boolean;
}

export function DocumentsDataTable({
  documents,
  onPreview,
  onDelete,
  onExtract,
  onExtractPDF,
  onTranscribe,
  onClearText,
  extractingDocId,
  extractingPDFDocId,
  transcribingDocId,
  clearingDocId,
  needsExtraction,
  isPDFFile,
  isAudioFile,
}: DocumentsDataTableProps) {
  const t = useTranslations();

  const columns: ColumnDef<Document>[] = React.useMemo(
    () => [
      {
        accessorKey: "filename",
        header: ({ column }) => (
          <SortableHeader column={column} label={t("documents.fileName")} />
        ),
        cell: ({ row }) => {
          const doc = row.original;
          const isOcrProcessing = doc.ocr_status === "pending" || doc.ocr_status === "processing";
          const isOcrError = doc.ocr_status === "error";
          const isTranscriptionProcessing = doc.transcription_status === "pending" || doc.transcription_status === "processing";
          const isTranscriptionError = doc.transcription_status === "error";

          return (
            <div className="flex items-center gap-2">
              <span className="font-normal">{doc.filename}</span>
              {isOcrProcessing && (
                <Loader2
                  className="h-4 w-4 text-blue-500 animate-spin shrink-0"
                  aria-label="OCR en cours"
                />
              )}
              {isOcrError && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <AlertCircle
                        className="h-4 w-4 text-destructive shrink-0 cursor-help"
                        aria-label="Erreur OCR"
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">{doc.ocr_error || "Erreur lors de l'extraction OCR"}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {isTranscriptionProcessing && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Loader2
                        className="h-4 w-4 text-green-500 animate-spin shrink-0"
                        aria-label="Transcription en cours"
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Transcription en cours...</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {isTranscriptionError && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <AlertCircle
                        className="h-4 w-4 text-orange-500 shrink-0 cursor-help"
                        aria-label="Erreur transcription"
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">{doc.transcription_error || "Erreur lors de la transcription"}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {doc.extracted_text && (
                <Database
                  className="h-4 w-4 text-muted-foreground shrink-0"
                  aria-label={t("documents.indexed")}
                />
              )}
            </div>
          );
        },
      },
      {
        accessorKey: "is_derived",
        header: ({ column }) => (
          <SortableHeader column={column} label={t("documents.fileType")} />
        ),
        cell: ({ row }) => {
          const doc = row.original;
          if (doc.is_derived) {
            const labels: Record<string, string> = {
              transcription: t("documents.transcription"),
              pdf_extraction: t("documents.pdfExtraction"),
              tts: t("documents.audioTts"),
            };
            return (
              <span className="text-sm">
                {labels[doc.derivation_type || ""] || t("documents.derived")}
              </span>
            );
          }
          return <span className="text-sm">{t("documents.source")}</span>;
        },
        filterFn: (row, _id, value) => {
          if (value === "all") return true;
          if (value === "source") return !row.original.is_derived;
          if (value === "transcription")
            return row.original.derivation_type === "transcription";
          if (value === "pdf_extraction")
            return row.original.derivation_type === "pdf_extraction";
          if (value === "tts") return row.original.derivation_type === "tts";
          return true;
        },
      },
      {
        accessorKey: "created_at",
        header: ({ column }) => (
          <SortableHeader column={column} label={t("documents.date")} />
        ),
        cell: ({ row }) => (
          <DateCell date={row.original.created_at || row.original.uploaded_at} />
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => {
          const doc = row.original;
          return (
            <div className="flex justify-end">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onClick={() => onPreview(doc.id)}>
                    <Eye className="h-4 w-4 mr-2" />
                    {t("documents.view")}
                  </DropdownMenuItem>

                  {/* INDEXATION (RAG) */}
                  {(needsExtraction(doc) || doc.extracted_text) && (
                    <>
                      <DropdownMenuSeparator />
                      {needsExtraction(doc) && (
                        <DropdownMenuItem
                          onClick={() => onExtract(doc)}
                          disabled={extractingDocId === doc.id}
                        >
                          {extractingDocId === doc.id ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Database className="h-4 w-4 mr-2" />
                          )}
                          {t("documents.indexInDb")}
                        </DropdownMenuItem>
                      )}
                      {doc.extracted_text && (
                        <>
                          {!doc.filename?.endsWith(".md") && (
                            <DropdownMenuItem
                              onClick={() => onExtract(doc)}
                              disabled={extractingDocId === doc.id}
                            >
                              <Database className="h-4 w-4 mr-2" />
                              {t("documents.reindex")}
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            onClick={() => onClearText(doc)}
                            disabled={clearingDocId === doc.id}
                            className="text-orange-600"
                          >
                            <DatabaseBackup className="h-4 w-4 mr-2" />
                            {t("documents.removeFromDb")}
                          </DropdownMenuItem>
                        </>
                      )}
                    </>
                  )}

                  {/* PDF */}
                  {isPDFFile(doc) && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => onExtractPDF(doc)}
                        disabled={extractingPDFDocId === doc.id}
                      >
                        {extractingPDFDocId === doc.id ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <FileText className="h-4 w-4 mr-2" />
                        )}
                        {t("documents.extractToMarkdown")}
                      </DropdownMenuItem>
                    </>
                  )}

                  {/* AUDIO */}
                  {isAudioFile(doc) && !doc.extracted_text && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => onTranscribe(doc)}
                        disabled={transcribingDocId === doc.id}
                      >
                        {transcribingDocId === doc.id ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Mic className="h-4 w-4 mr-2" />
                        )}
                        {t("documents.transcribeToMarkdown")}
                      </DropdownMenuItem>
                    </>
                  )}

                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(doc)}
                    className="text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    {t("common.delete")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        },
      },
    ],
    [
      t,
      onPreview,
      onDelete,
      onExtract,
      onExtractPDF,
      onTranscribe,
      onClearText,
      extractingDocId,
      extractingPDFDocId,
      transcribingDocId,
      clearingDocId,
      needsExtraction,
      isPDFFile,
      isAudioFile,
    ]
  );

  const renderFilters = (table: TanstackTable<Document>) => (
    <div className="flex items-center gap-2">
      <Input
        placeholder={t("documents.filterByName")}
        value={(table.getColumn("filename")?.getFilterValue() as string) ?? ""}
        onChange={(event) =>
          table.getColumn("filename")?.setFilterValue(event.target.value)
        }
        className="max-w-sm"
      />
      <Select
        value={
          (table.getColumn("is_derived")?.getFilterValue() as string) ?? "all"
        }
        onValueChange={(value) =>
          table.getColumn("is_derived")?.setFilterValue(value)
        }
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder={t("documents.fileType")} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t("documents.allFiles")}</SelectItem>
          <SelectItem value="source">{t("documents.source")}</SelectItem>
          <SelectItem value="transcription">
            {t("documents.transcription")}
          </SelectItem>
          <SelectItem value="pdf_extraction">
            {t("documents.pdfExtraction")}
          </SelectItem>
          <SelectItem value="tts">{t("documents.audioTts")}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );

  return (
    <GenericDataTable
      data={documents}
      columns={columns}
      emptyMessage={t("documents.noDocumentsFound")}
      enableFiltering={true}
      renderFilters={renderFilters}
    />
  );
}
