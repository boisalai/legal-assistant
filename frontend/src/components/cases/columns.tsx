"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
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
import {
  MoreHorizontal,
  ArrowUpDown,
  Circle,
  Timer,
  CheckCircle,
  XCircle,
  ArrowUp,
  ArrowRight,
  ArrowDown,
  Pin,
} from "lucide-react";

// Status configuration
const statusConfig: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
  nouveau: { label: "Nouveau", icon: <Circle className="h-3.5 w-3.5" />, className: "text-blue-600" },
  en_analyse: { label: "En analyse", icon: <Timer className="h-3.5 w-3.5" />, className: "text-yellow-600" },
  termine: { label: "Terminé", icon: <CheckCircle className="h-3.5 w-3.5" />, className: "text-green-600" },
  en_erreur: { label: "En erreur", icon: <XCircle className="h-3.5 w-3.5" />, className: "text-red-600" },
  archive: { label: "Archivé", icon: <XCircle className="h-3.5 w-3.5" />, className: "text-gray-500" },
};

// Priority based on score
const getPriority = (score: number | null | undefined) => {
  if (!score || score < 50) return { label: "Urgent", icon: <ArrowUp className="h-3.5 w-3.5" />, className: "text-red-600" };
  if (score < 75) return { label: "Moyen", icon: <ArrowRight className="h-3.5 w-3.5" />, className: "text-yellow-600" };
  return { label: "Faible", icon: <ArrowDown className="h-3.5 w-3.5" />, className: "text-green-600" };
};

// Type labels
const typeLabels: Record<string, string> = {
  vente: "Vente",
  achat: "Achat",
  hypotheque: "Hypotheque",
  testament: "Testament",
  succession: "Succession",
  autre: "Autre",
};

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
    id: "pin",
    header: () => null,
    cell: ({ row }) => {
      const caseItem = row.original;
      const isPinned = caseItem.pinned || false;

      return (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => onTogglePin(caseItem.id)}
          aria-label={isPinned ? "Dé-épingler" : "Épingler"}
        >
          <Pin
            className={`h-4 w-4 ${isPinned ? "fill-current text-primary" : "text-muted-foreground"}`}
          />
        </Button>
      );
    },
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => {
      const id = row.getValue("id") as string;
      const shortId = id.replace("dossier:", "").substring(0, 8);
      return <code className="text-xs font-mono text-muted-foreground">{shortId}</code>;
    },
  },
  {
    accessorKey: "nom_dossier",
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
      const fullId = row.getValue("id") as string;
      // Extract clean ID without "dossier:" prefix for URL
      const urlId = fullId.replace("dossier:", "");
      return (
        <Link
          href={`/cases/${urlId}`}
          className="font-medium hover:underline"
        >
          {row.getValue("nom_dossier")}
        </Link>
      );
    },
  },
  {
    accessorKey: "type_transaction",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="-ml-4"
        >
          Type
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const type = row.getValue("type_transaction") as string;
      return <span className="capitalize">{typeLabels[type] || type}</span>;
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
  },
  {
    accessorKey: "statut",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="-ml-4"
        >
          Statut
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const statut = row.getValue("statut") as string;
      const config = statusConfig[statut] || statusConfig.nouveau;
      return (
        <div className={`flex items-center gap-2 ${config.className}`}>
          {config.icon}
          <span>{config.label}</span>
        </div>
      );
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
  },
  {
    accessorKey: "score_confiance",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="-ml-4"
        >
          Priorité
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const score = row.getValue("score_confiance") as number | null;
      const priority = getPriority(score);
      return (
        <div className={`flex items-center gap-2 ${priority.className}`}>
          {priority.icon}
          <span>{priority.label}</span>
          {score !== null && score !== undefined && (
            <span className="text-xs text-muted-foreground">({score}%)</span>
          )}
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
              onClick={() => window.location.href = `/cases/${caseItem.id.replace("dossier:", "")}`}
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
