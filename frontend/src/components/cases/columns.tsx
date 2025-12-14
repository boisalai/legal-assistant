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
import { MoreHorizontal, ArrowUpDown } from "lucide-react";

export const createColumns = (
  onDelete: (id: string) => void,
  onTogglePin: (id: string) => void
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
        aria-label="Selectionner tout"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Selectionner la ligne"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "title",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="-ml-4"
        >
          Nom
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
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
    accessorKey: "course_code",
    header: "Code",
    cell: ({ row }) => {
      const courseCode = row.original.course_code;
      return courseCode ? (
        <code className="text-xs font-mono bg-muted px-2 py-1 rounded">
          {courseCode}
        </code>
      ) : (
        <span className="text-muted-foreground">-</span>
      );
    },
  },
  {
    accessorKey: "professor",
    header: "Professeur",
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
    accessorKey: "credits",
    header: "Crédits",
    cell: ({ row }) => {
      const credits = row.original.credits;
      return credits ? (
        <span className="text-sm font-medium">{credits}</span>
      ) : (
        <span className="text-muted-foreground">-</span>
      );
    },
  },
  {
    accessorKey: "description",
    header: "Description",
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
    accessorKey: "created_at",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="-ml-4"
        >
          Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
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
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => navigator.clipboard.writeText(caseItem.id)}
            >
              Copier l'ID
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => window.location.href = `/cases/${caseItem.id.replace("case:", "")}`}
            >
              Ouvrir
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onDelete(caseItem.id)}
              className="text-red-600"
            >
              Supprimer
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];
