"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";
import type { Case } from "@/types";
import { MoreHorizontal } from "lucide-react";

export const createColumns = (
  onDelete: (id: string) => void,
  onTogglePin: (id: string) => void,
  t: (key: string) => string
): ColumnDef<Case>[] => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && "indeterminate")
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label={t("table.actions.selectAll")}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label={t("table.actions.selectRow")}
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "course_code",
    header: t("table.columns.code"),
    cell: ({ row }) => {
      const courseCode = row.original.course_code;
      return courseCode ? (
        <span className="text-sm">
          {courseCode}
        </span>
      ) : (
        <span className="text-muted-foreground">-</span>
      );
    },
  },
  {
    accessorKey: "title",
    header: t("table.columns.name"),
    cell: ({ row }) => {
      const fullId = row.original.id;
      const urlId = fullId.replace("case:", "");
      const title = row.getValue("title") as string;
      return (
        <Link
          href={`/cases/${urlId}`}
          className="font-medium hover:underline"
        >
          {title}
        </Link>
      );
    },
  },
  {
    accessorKey: "description",
    header: t("table.columns.description"),
    cell: ({ row }) => {
      const description = row.getValue("description") as string | undefined;
      return (
        <span className="text-muted-foreground max-w-md truncate block">
          {description || "-"}
        </span>
      );
    },
  },
  {
    accessorKey: "professor",
    header: t("table.columns.professor"),
    cell: ({ row }) => {
      const professor = row.original.professor;
      return (
        <span className="text-sm">
          {professor || <span className="text-muted-foreground">-</span>}
        </span>
      );
    },
  },
  {
    accessorKey: "created_at",
    header: t("table.columns.date"),
    cell: ({ row }) => {
      const date = row.getValue("created_at") as string;
      if (!date) return <span className="text-muted-foreground">-</span>;
      return (
        <span className="text-muted-foreground">
          {new Date(date).toLocaleDateString("fr-CA")}
        </span>
      );
    },
  },
  {
    id: "actions",
    enableHiding: false,
    cell: ({ row }) => {
      const caseItem = row.original;

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">{t("table.actions.openMenu")}</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{t("table.actions.actions")}</DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => navigator.clipboard.writeText(caseItem.id)}
            >
              {t("table.actions.copyId")}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => window.location.href = `/cases/${caseItem.id.replace("case:", "")}`}
            >
              {t("table.actions.open")}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onDelete(caseItem.id)}
              className="text-red-600"
            >
              {t("table.actions.delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];
