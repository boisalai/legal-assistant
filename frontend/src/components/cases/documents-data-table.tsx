"use client";

import * as React from "react";
import { useTranslations } from "next-intl";
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  ArrowUpDown,
  Mic,
  DatabaseBackup,
} from "lucide-react";
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
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});

  const columns: ColumnDef<Document>[] = [
    {
      accessorKey: "filename",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {t("documents.fileName")}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const doc = row.original;

        return (
          <div className="flex items-center gap-2">
            <span className="font-normal">{doc.filename}</span>
            {doc.extracted_text && (
              <Database className="h-4 w-4 text-muted-foreground shrink-0" aria-label={t("documents.indexed")} />
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "is_derived",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {t("documents.fileType")}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const doc = row.original;

        if (doc.is_derived) {
          const labels: Record<string, string> = {
            transcription: t("documents.transcription"),
            pdf_extraction: t("documents.pdfExtraction"),
            tts: t("documents.audioTts"),
          };
          const label = labels[doc.derivation_type || ""] || t("documents.derived");

          return <span className="text-sm">{label}</span>;
        }

        return <span className="text-sm">{t("documents.source")}</span>;
      },
      filterFn: (row, _id, value) => {
        if (value === "all") return true;
        if (value === "source") return !row.original.is_derived;
        if (value === "transcription") return row.original.derivation_type === "transcription";
        if (value === "pdf_extraction") return row.original.derivation_type === "pdf_extraction";
        if (value === "tts") return row.original.derivation_type === "tts";
        return true;
      },
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {t("documents.date")}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const dateStr = row.original.created_at || row.original.uploaded_at;
        return (
          <span className="text-sm text-black">
            {dateStr ? new Date(dateStr).toLocaleDateString("fr-CA") : "—"}
          </span>
        );
      },
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
                      {!doc.filename?.endsWith('.md') && (
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

              {/* PDF (si applicable) */}
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

              {/* AUDIO (si applicable) */}
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
  ];

  const table = useReactTable({
    data: documents,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
    },
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
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
          value={(table.getColumn("is_derived")?.getFilterValue() as string) ?? "all"}
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
            <SelectItem value="transcription">{t("documents.transcription")}</SelectItem>
            <SelectItem value="pdf_extraction">{t("documents.pdfExtraction")}</SelectItem>
            <SelectItem value="tts">{t("documents.audioTts")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id} className="bg-blue-50 font-bold text-black">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="font-normal text-black">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center font-normal text-black">
                  {t("documents.noDocumentsFound")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
