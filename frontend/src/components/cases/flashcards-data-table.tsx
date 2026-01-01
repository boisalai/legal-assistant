"use client";

import * as React from "react";
import { useTranslations } from "next-intl";
import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
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
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Play,
  Trash2,
  MoreVertical,
  ArrowUpDown,
  Headphones,
} from "lucide-react";
import type { FlashcardDeck } from "@/types";

interface FlashcardsDataTableProps {
  decks: FlashcardDeck[];
  onStudy: (deck: FlashcardDeck) => void;
  onListenAudio: (deck: FlashcardDeck) => void;
  onDelete: (deck: FlashcardDeck) => void;
  deletingDeckId: string | null;
}

export function FlashcardsDataTable({
  decks,
  onStudy,
  onListenAudio,
  onDelete,
  deletingDeckId,
}: FlashcardsDataTableProps) {
  const t = useTranslations("flashcards");
  const tCommon = useTranslations("common");
  const [sorting, setSorting] = React.useState<SortingState>([]);

  const columns: ColumnDef<FlashcardDeck>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {t("setName")}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const deck = row.original;
        return (
          <span className="text-[14px] text-[#000000] truncate max-w-xs" title={deck.name}>
            {deck.name}
          </span>
        );
      },
    },
    {
      id: "docs",
      header: () => t("columns.docs"),
      cell: ({ row }) => (
        <span className="text-[14px] text-[#000000]">{row.original.source_documents.length}</span>
      ),
    },
    {
      id: "cards",
      header: () => t("columns.cards"),
      cell: ({ row }) => (
        <span className="text-[14px] text-[#000000]">{row.original.total_cards}</span>
      ),
    },
    {
      id: "progress",
      header: () => t("progress"),
      cell: ({ row }) => {
        const deck = row.original;
        if (deck.total_cards === 0) {
          return <span className="text-[14px] text-[#000000]">-</span>;
        }
        return (
          <div className="w-24 space-y-1">
            <Progress value={deck.progress_percent} className="h-1.5" />
            <span className="text-[14px] text-[#000000]">
              {Math.round(deck.progress_percent)}%
            </span>
          </div>
        );
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
            {t("columns.createdAt")}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return (
          <span className="text-[14px] text-[#000000]">
            {date.toLocaleDateString("fr-CA", {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </span>
        );
      },
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const deck = row.original;
        const isDeleting = deletingDeckId === deck.id;

        return (
          <div className="flex justify-end">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" disabled={isDeleting}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem
                  onClick={() => onStudy(deck)}
                  disabled={deck.total_cards === 0}
                >
                  <Play className="h-4 w-4 mr-2" />
                  {deck.total_cards === 0 ? t("generateFirst") : t("study")}
                </DropdownMenuItem>

                {deck.has_summary_audio && (
                  <DropdownMenuItem onClick={() => onListenAudio(deck)}>
                    <Headphones className="h-4 w-4 mr-2" />
                    {t("listenSummary")}
                  </DropdownMenuItem>
                )}

                <DropdownMenuSeparator />

                <DropdownMenuItem
                  onClick={() => onDelete(deck)}
                  className="text-destructive"
                  disabled={isDeleting}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  {tCommon("delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        );
      },
    },
  ];

  const table = useReactTable({
    data: decks,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
  });

  return (
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
                  <TableCell key={cell.id} className="text-black">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center text-black">
                {t("noSets")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
