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
import { Eye, Pencil, Trash2, MoreVertical } from "lucide-react";
import { GenericDataTable } from "@/components/ui/generic-data-table";
import { SortableHeader, DateCell, TruncatedCell } from "@/components/ui/column-helpers";
import type { Module } from "@/types";

interface ModulesDataTableProps {
  modules: Module[];
  onView: (module: Module) => void;
  onEdit: (module: Module) => void;
  onDelete: (module: Module) => void;
  deletingModuleId: string | null;
}

export function ModulesDataTable({
  modules,
  onView,
  onEdit,
  onDelete,
  deletingModuleId,
}: ModulesDataTableProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");
  const tTable = useTranslations("table");

  const columns: ColumnDef<Module>[] = React.useMemo(
    () => [
      {
        accessorKey: "name",
        header: ({ column }) => (
          <SortableHeader column={column} label={t("name")} />
        ),
        cell: ({ row }) => <TruncatedCell text={row.original.name} />,
      },
      {
        id: "documents",
        header: () => t("columns.documents"),
        cell: ({ row }) => (
          <span className="text-[14px] text-black">
            {row.original.document_count}
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
          const module = row.original;
          const isDeleting = deletingModuleId === module.id;

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
                  <DropdownMenuItem onClick={() => onView(module)}>
                    <Eye className="h-4 w-4 mr-2" />
                    {tTable("actions.open")}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onEdit(module)}>
                    <Pencil className="h-4 w-4 mr-2" />
                    {tCommon("edit")}
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />

                  <DropdownMenuItem
                    onClick={() => onDelete(module)}
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
    [t, tCommon, tTable, onView, onEdit, onDelete, deletingModuleId]
  );

  return (
    <GenericDataTable
      data={modules}
      columns={columns}
      emptyMessage={t("noModules")}
      initialSort={[{ id: "order_index", desc: false }]}
    />
  );
}
