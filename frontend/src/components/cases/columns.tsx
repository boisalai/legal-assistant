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
import type { Course } from "@/types";
import { MoreHorizontal, Pin, PinOff } from "lucide-react";

export const createColumns = (
  onDelete: (id: string) => void,
  onTogglePin: (id: string) => void,
  t: (key: string) => string
): ColumnDef<Course>[] => [
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
      const fullId = row.original.id;
      const urlId = fullId.replace("course:", "").replace("case:", "");
      return courseCode ? (
        <Link
          href={`/courses/${urlId}`}
          className="text-sm hover:underline"
        >
          {courseCode}
        </Link>
      ) : (
        <span className="text-sm">-</span>
      );
    },
  },
  {
    accessorKey: "title",
    header: t("table.columns.title"),
    cell: ({ row }) => {
      const title = row.getValue("title") as string;
      const isPinned = row.original.pinned;
      return (
        <div className="flex items-center gap-2">
          {isPinned && <Pin className="h-3 w-3 text-muted-foreground" />}
          <span className="text-sm">
            {title}
          </span>
        </div>
      );
    },
  },
  {
    accessorKey: "description",
    header: t("table.columns.description"),
    cell: ({ row }) => {
      const description = row.getValue("description") as string | undefined;
      return (
        <span className="text-sm max-w-md truncate block">
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
          {professor || "-"}
        </span>
      );
    },
  },
  {
    accessorKey: "created_at",
    header: t("table.columns.date"),
    cell: ({ row }) => {
      const date = row.getValue("created_at") as string;
      if (!date) return <span className="text-sm">-</span>;
      return (
        <span className="text-sm">
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
            <DropdownMenuItem
              onClick={() => onTogglePin(caseItem.id)}
            >
              {caseItem.pinned ? (
                <>
                  <PinOff className="mr-2 h-4 w-4" />
                  {t("table.actions.unpin")}
                </>
              ) : (
                <>
                  <Pin className="mr-2 h-4 w-4" />
                  {t("table.actions.pin")}
                </>
              )}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => window.location.href = `/courses/${caseItem.id.replace("course:", "").replace("case:", "")}`}
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
