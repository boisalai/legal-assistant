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
import { Badge } from "@/components/ui/badge";
import {
  Pencil,
  Trash2,
  MoreVertical,
  ArrowUpDown,
  FileText,
  GraduationCap,
  CheckCircle2,
  BookOpen,
  Sparkles,
} from "lucide-react";
import type { ModuleWithProgress, MasteryLevel } from "@/types";

interface ModulesDataTableProps {
  modules: ModuleWithProgress[];
  onEdit: (module: ModuleWithProgress) => void;
  onDelete: (module: ModuleWithProgress) => void;
  onViewDocuments: (module: ModuleWithProgress) => void;
  deletingModuleId: string | null;
  recommendedModuleId?: string | null;
}

function getMasteryBadgeVariant(level: MasteryLevel): "default" | "secondary" | "destructive" | "outline" {
  switch (level) {
    case "mastered":
      return "default";
    case "proficient":
      return "secondary";
    case "learning":
      return "outline";
    default:
      return "destructive";
  }
}

function getMasteryIcon(level: MasteryLevel) {
  switch (level) {
    case "mastered":
      return <CheckCircle2 className="h-3 w-3" />;
    case "proficient":
      return <GraduationCap className="h-3 w-3" />;
    case "learning":
      return <BookOpen className="h-3 w-3" />;
    default:
      return <Sparkles className="h-3 w-3" />;
  }
}

export function ModulesDataTable({
  modules,
  onEdit,
  onDelete,
  onViewDocuments,
  deletingModuleId,
  recommendedModuleId,
}: ModulesDataTableProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: "order_index", desc: false },
  ]);

  const columns: ColumnDef<ModuleWithProgress>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {t("name")}
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const module = row.original;
        const isRecommended = module.id === recommendedModuleId;
        return (
          <div className="flex items-center gap-2">
            <span
              className="text-[14px] text-[#000000] truncate max-w-xs"
              title={module.name}
            >
              {module.name}
            </span>
            {isRecommended && (
              <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300">
                {t("recommended")}
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "order_index",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            #
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <span className="text-[14px] text-[#000000]">{row.original.order_index + 1}</span>
      ),
    },
    {
      id: "documents",
      header: () => t("columns.documents"),
      cell: ({ row }) => (
        <span className="text-[14px] text-[#000000]">{row.original.document_count}</span>
      ),
    },
    {
      id: "progress",
      header: () => t("columns.progress"),
      cell: ({ row }) => {
        const module = row.original;
        const progress = module.overall_progress;

        // Color based on progress
        let progressColor = "bg-red-500";
        if (progress >= 80) {
          progressColor = "bg-green-500";
        } else if (progress >= 50) {
          progressColor = "bg-yellow-500";
        } else if (progress >= 25) {
          progressColor = "bg-orange-500";
        }

        return (
          <div className="w-32 space-y-1">
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className={`h-full transition-all ${progressColor}`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{Math.round(progress)}%</span>
            </div>
          </div>
        );
      },
    },
    {
      id: "mastery",
      header: () => t("columns.mastery"),
      cell: ({ row }) => {
        const module = row.original;
        return (
          <Badge
            variant={getMasteryBadgeVariant(module.mastery_level)}
            className="gap-1"
          >
            {getMasteryIcon(module.mastery_level)}
            {t(`masteryLevels.${module.mastery_level}`)}
          </Badge>
        );
      },
    },
    {
      id: "breakdown",
      header: () => t("columns.breakdown"),
      cell: ({ row }) => {
        const module = row.original;
        return (
          <div className="flex gap-3 text-xs text-muted-foreground">
            <span title={t("reading")}>
              {Math.round(module.reading_percent)}% {t("readingShort")}
            </span>
            <span title={t("flashcards")}>
              {Math.round(module.flashcard_percent)}% {t("flashcardsShort")}
            </span>
            <span title={t("quizzes")}>
              {Math.round(module.quiz_average_score)}% {t("quizzesShort")}
            </span>
          </div>
        );
      },
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
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" disabled={isDeleting}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onClick={() => onViewDocuments(module)}>
                  <FileText className="h-4 w-4 mr-2" />
                  {t("viewDocuments")}
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
  ];

  const table = useReactTable({
    data: modules,
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
                className={row.original.id === recommendedModuleId ? "bg-yellow-50/50" : ""}
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
                {t("noModules")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
