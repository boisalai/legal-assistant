"use client";

import * as React from "react";
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Eye, MoreVertical, ArrowUpDown, FileText, Mic, FileDown } from "lucide-react";
import type { Document } from "@/types";

interface DirectoryTreeViewProps {
  documents: Document[];
  basePath: string;
  caseId?: string; // Optional - not used internally, only needed by parent
  onPreviewDocument?: (docId: string) => void;
  onExtractPDF?: (doc: Document) => void;
  onTranscribe?: (doc: Document) => void;
}

export function DirectoryTreeView({
  documents,
  basePath,
  onPreviewDocument,
  onExtractPDF,
  onTranscribe,
}: DirectoryTreeViewProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);

  // Calculate relative path from basePath
  const getRelativePath = (fullPath: string) => {
    if (!fullPath) return "";

    // Normalize paths
    const normalizedBase = basePath.replace(/\/$/, "");
    const normalizedFull = fullPath.replace(/\/$/, "");

    if (normalizedFull.startsWith(normalizedBase)) {
      const relative = normalizedFull.substring(normalizedBase.length);
      return relative.startsWith("/") ? relative.substring(1) : relative;
    }

    return fullPath;
  };

  // Format file size (French by default, ready for i18n)
  const formatFileSize = (bytes: number, locale: string = "fr") => {
    if (bytes === 0) {
      return locale === "fr" ? "0 octet" : "0 byte";
    }
    const k = 1024;
    const sizesFr = ["octets", "Ko", "Mo", "Go"];
    const sizesEn = ["bytes", "KB", "MB", "GB"];
    const sizes = locale === "fr" ? sizesFr : sizesEn;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const value = parseFloat((bytes / Math.pow(k, i)).toFixed(1));

    // Special case for bytes/octets: no space before unit, and handle plural
    if (i === 0) {
      return locale === "fr"
        ? `${value} ${value <= 1 ? "octet" : "octets"}`
        : `${value} ${value === 1 ? "byte" : "bytes"}`;
    }

    return `${value} ${sizes[i]}`;
  };

  // Check if document is a PDF file
  const isPDFFile = (doc: Document) => {
    const ext = doc.filename?.split(".").pop()?.toLowerCase() || "";
    return ext === "pdf" || doc.mime_type === "application/pdf";
  };

  // Check if document is a Word file
  const isWordFile = (doc: Document) => {
    const ext = doc.filename?.split(".").pop()?.toLowerCase() || "";
    return ["doc", "docx"].includes(ext);
  };

  // Check if document is an audio file
  const isAudioFile = (doc: Document) => {
    const ext = doc.filename?.split(".").pop()?.toLowerCase() || "";
    const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return audioExtensions.includes(ext) || (doc.mime_type?.includes("audio") ?? false);
  };

  const columns: ColumnDef<Document>[] = [
    {
      accessorKey: "relativePath",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Nom du fichier
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const doc = row.original;
        const relativePath = getRelativePath(doc.file_path || "");
        const parts = relativePath.split("/");

        if (parts.length > 1) {
          // File in subdirectory
          const dirPath = parts.slice(0, -1).join("/");
          const fileName = parts[parts.length - 1];

          return (
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="flex items-baseline gap-1 min-w-0">
                <span className="text-muted-foreground text-sm truncate">
                  {dirPath}/
                </span>
                <span className="font-medium truncate">{fileName}</span>
              </div>
            </div>
          );
        } else {
          // File in root
          return (
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="font-medium">{relativePath || doc.filename}</span>
            </div>
          );
        }
      },
      accessorFn: (row) => getRelativePath(row.file_path || ""),
    },
    {
      accessorKey: "linked_source.source_mtime",
      header: ({ column }) => {
        return (
          <div className="flex justify-end">
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              Date de modification
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          </div>
        );
      },
      cell: ({ row }) => {
        const doc = row.original;
        const mtime = doc.linked_source?.source_mtime;

        if (!mtime) {
          return (
            <div className="text-right">
              <span className="text-sm text-muted-foreground">—</span>
            </div>
          );
        }

        // Convert Unix timestamp (seconds) to Date object
        const date = new Date(mtime * 1000);

        return (
          <div className="text-right">
            <span className="text-sm text-muted-foreground">
              {date.toLocaleDateString("fr-CA")}
            </span>
          </div>
        );
      },
      accessorFn: (row) => row.linked_source?.source_mtime || 0,
    },
    {
      accessorKey: "size",
      header: ({ column }) => {
        return (
          <div className="flex justify-end">
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              Taille
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          </div>
        );
      },
      cell: ({ row }) => {
        return (
          <div className="text-right">
            <span className="text-sm text-muted-foreground">
              {formatFileSize(row.original.size || 0)}
            </span>
          </div>
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
                <DropdownMenuItem onClick={() => onPreviewDocument?.(doc.id)}>
                  <Eye className="h-4 w-4 mr-2" />
                  Visualiser
                </DropdownMenuItem>

                {/* Extract to markdown for PDF, Word, or Audio */}
                {(isPDFFile(doc) || isWordFile(doc) || isAudioFile(doc)) && (
                  <>
                    {(isPDFFile(doc) || isWordFile(doc)) && onExtractPDF && (
                      <DropdownMenuItem onClick={() => onExtractPDF(doc)}>
                        <FileDown className="h-4 w-4 mr-2" />
                        Extraire en markdown
                      </DropdownMenuItem>
                    )}
                    {isAudioFile(doc) && onTranscribe && (
                      <DropdownMenuItem onClick={() => onTranscribe(doc)}>
                        <Mic className="h-4 w-4 mr-2" />
                        Transcrire en markdown
                      </DropdownMenuItem>
                    )}
                  </>
                )}
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
    state: {
      sorting,
      columnFilters,
    },
  });

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Search filter */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="Filtrer par nom de fichier..."
          value={(table.getColumn("relativePath")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("relativePath")?.setFilterValue(event.target.value)
          }
          className="max-w-sm"
        />
      </div>

      {/* Table */}
      <div className="rounded-md border flex-1 overflow-auto">
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
                    <TableCell key={cell.id} className="text-black">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-black">
                  Aucun fichier trouvé.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
