"use client";

import * as React from "react";
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  Table as TanstackTable,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface GenericDataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  emptyMessage: string;
  initialSort?: SortingState;
  enableFiltering?: boolean;
  renderFilters?: (table: TanstackTable<T>) => React.ReactNode;
}

export function GenericDataTable<T>({
  data,
  columns,
  emptyMessage,
  initialSort = [],
  enableFiltering = false,
  renderFilters,
}: GenericDataTableProps<T>) {
  const [sorting, setSorting] = React.useState<SortingState>(initialSort);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    ...(enableFiltering && { getFilteredRowModel: getFilteredRowModel() }),
    onSortingChange: setSorting,
    ...(enableFiltering && { onColumnFiltersChange: setColumnFilters }),
    ...(enableFiltering && { onColumnVisibilityChange: setColumnVisibility }),
    state: {
      sorting,
      ...(enableFiltering && { columnFilters, columnVisibility }),
    },
  });

  return (
    <div className={enableFiltering ? "space-y-4" : ""}>
      {enableFiltering && renderFilters && renderFilters(table)}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="bg-blue-50 text-black">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
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
                  {emptyMessage}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
