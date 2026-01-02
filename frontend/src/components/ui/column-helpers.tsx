"use client";

import { Column } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";

/**
 * Creates a sortable header button for DataTable columns.
 */
export function SortableHeader<T>({
  column,
  label,
}: {
  column: Column<T>;
  label: string;
}) {
  return (
    <Button
      variant="ghost"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {label}
      <ArrowUpDown className="ml-2 h-4 w-4" />
    </Button>
  );
}

/**
 * Formats a date string to fr-CA locale (YYYY-MM-DD).
 */
export function DateCell({ date }: { date: string | undefined }) {
  if (!date) return <span className="text-[14px] text-black">—</span>;

  return (
    <span className="text-[14px] text-black">
      {new Date(date).toLocaleDateString("fr-CA")}
    </span>
  );
}

/**
 * Renders a text cell with truncation.
 */
export function TruncatedCell({
  text,
  maxWidth = "max-w-xs",
}: {
  text: string;
  maxWidth?: string;
}) {
  return (
    <span className={`text-[14px] text-black truncate ${maxWidth}`} title={text}>
      {text}
    </span>
  );
}
