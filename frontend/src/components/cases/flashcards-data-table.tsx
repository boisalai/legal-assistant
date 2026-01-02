"use client";

import * as React from "react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Play, Trash2, MoreVertical, Headphones } from "lucide-react";
import { GenericDataTable } from "@/components/ui/generic-data-table";
import { SortableHeader, DateCell, TruncatedCell } from "@/components/ui/column-helpers";
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

  const columns: ColumnDef<FlashcardDeck>[] = React.useMemo(
    () => [
      {
        accessorKey: "name",
        header: ({ column }) => (
          <SortableHeader column={column} label={t("setName")} />
        ),
        cell: ({ row }) => <TruncatedCell text={row.original.name} />,
      },
      {
        id: "docs",
        header: () => t("columns.docs"),
        cell: ({ row }) => (
          <span className="text-[14px] text-black">
            {row.original.source_documents.length}
          </span>
        ),
      },
      {
        id: "cards",
        header: () => t("columns.cards"),
        cell: ({ row }) => (
          <span className="text-[14px] text-black">
            {row.original.total_cards}
          </span>
        ),
      },
      {
        accessorKey: "created_at",
        header: ({ column }) => (
          <SortableHeader column={column} label={t("columns.createdAt")} />
        ),
        cell: ({ row }) => <DateCell date={row.original.created_at} />,
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
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    disabled={isDeleting}
                  >
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
    ],
    [t, tCommon, onStudy, onListenAudio, onDelete, deletingDeckId]
  );

  return (
    <GenericDataTable
      data={decks}
      columns={columns}
      emptyMessage={t("noSets")}
    />
  );
}
