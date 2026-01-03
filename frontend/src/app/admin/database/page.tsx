"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Database,
  Loader2,
  AlertCircle,
  Eye,
  ArrowLeft,
  MoreVertical,
  Trash2,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AppShell } from "@/components/layout";
import { DataTable } from "@/components/cases/data-table";
import { adminApi, authApi, type TableInfo } from "@/lib/api";

export default function AdminDatabasePage() {
  const t = useTranslations("admin");
  const router = useRouter();

  // State
  const [tables, setTables] = useState<(TableInfo & { id: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Table viewer state
  const [selectedTable, setSelectedTable] = useState<TableInfo | null>(null);
  const [tableData, setTableData] = useState<any[]>([]);
  const [loadingData, setLoadingData] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

  // Delete confirmation state
  const [recordToDelete, setRecordToDelete] = useState<{
    tableName: string;
    recordId: string;
    rowIndex: number;
  } | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Handle view table
  const handleViewTable = async (table: TableInfo) => {
    setSelectedTable(table);
    setLoadingData(true);
    setDataError(null);
    try {
      const data = await adminApi.database.getTableData(table.name, {
        limit: 50,
      });
      setTableData(data.rows);
    } catch (err: any) {
      console.error("Error fetching table data:", err);
      setDataError(err.message || "Erreur lors du chargement des données");
    } finally {
      setLoadingData(false);
    }
  };

  // Handle back to tables list
  const handleBackToTables = () => {
    setSelectedTable(null);
    setTableData([]);
    setDataError(null);
  };

  // Handle delete record
  const handleDeleteRecord = async () => {
    if (!recordToDelete) return;

    setDeleting(true);
    try {
      await adminApi.database.deleteRecord(
        recordToDelete.tableName,
        recordToDelete.recordId
      );

      // Remove the record from the table data
      setTableData((prev) =>
        prev.filter((_, idx) => idx !== recordToDelete.rowIndex)
      );

      // Close the dialog
      setRecordToDelete(null);

      // Optionally reload the table data to ensure consistency
      if (selectedTable) {
        await handleViewTable(selectedTable);
      }
    } catch (err: any) {
      console.error("Error deleting record:", err);
      setDataError(err.message || "Erreur lors de la suppression");
    } finally {
      setDeleting(false);
    }
  };

  // Table columns for tables list
  const tablesColumns = useMemo<ColumnDef<TableInfo & { id: string }>[]>(
    () => [
      {
        accessorKey: "displayName",
        header: "Table",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-blue-600" />
            <div>
              <div className="font-medium">{row.original.displayName}</div>
              <div className="text-xs text-muted-foreground font-mono">
                {row.original.name}
              </div>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "rowCount",
        header: "Lignes",
        cell: ({ row }) =>
          row.original.rowCount !== undefined
            ? row.original.rowCount.toLocaleString("fr-FR")
            : "N/A",
      },
      {
        accessorKey: "estimatedSizeMb",
        header: "Taille",
        cell: ({ row }) =>
          row.original.estimatedSizeMb
            ? `${row.original.estimatedSizeMb.toFixed(2)} MB`
            : "—",
      },
      {
        accessorKey: "hasOrphans",
        header: "État",
        cell: ({ row }) =>
          row.original.hasOrphans ? "Orphelins" : "OK",
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleViewTable(row.original)}
          >
            <Eye className="h-4 w-4 mr-2" />
            Voir
          </Button>
        ),
      },
    ],
    []
  );

  // Check if user is admin
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (!authApi.isAuthenticated()) {
          router.push("/login");
          return;
        }

        const user = await authApi.getCurrentUser();
        if (user.role !== "admin") {
          router.push("/dashboard");
          return;
        }

        // User is admin, fetch tables
        await fetchTables();
      } catch (err) {
        console.error("Auth check error:", err);
        router.push("/login");
      }
    };

    checkAuth();
  }, [router]);

  const fetchTables = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.database.listTables();
      // Add id field for DataTable compatibility
      const tablesWithId = data.map((table) => ({
        ...table,
        id: table.name,
      }));
      setTables(tablesWithId);
    } catch (err: any) {
      console.error("Error fetching tables:", err);
      setError(err.message || "Erreur lors du chargement des tables");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppShell noPadding>
        <div className="flex h-full items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell noPadding>
        <div className="flex flex-col h-full overflow-hidden">
          <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
            <h2 className="text-xl font-bold">{t("database.title")}</h2>
          </div>
          <div className="px-6 py-2 flex-1 min-h-0 overflow-y-auto">
            <div className="border border-destructive rounded-md p-3">
              <div className="flex items-center gap-2 text-destructive text-sm">
                <AlertCircle className="h-4 w-4" />
                <p>{error}</p>
              </div>
              <Button onClick={fetchTables} variant="outline" size="sm" className="mt-2">
                Réessayer
              </Button>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell noPadding>
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header - fixed 65px */}
        <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
          <h2 className="text-xl font-bold">{t("database.title")}</h2>
          {selectedTable && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleBackToTables}
              className="gap-1"
            >
              <ArrowLeft className="h-3 w-3" />
              Retour aux tables
            </Button>
          )}
        </div>

        {/* Scrollable content */}
        <div className="px-6 py-2 space-y-4 flex-1 min-h-0 overflow-y-auto">
          {/* Tables List OR Table Data View */}
          {!selectedTable ? (
            // Show tables list
            <div className="space-y-2">
              <h3 className="font-semibold text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                Tables ({tables.length})
              </h3>
              {tables.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-sm text-muted-foreground">
                    {t("database.noTables")}
                  </p>
                </div>
              ) : (
                <DataTable columns={tablesColumns} data={tables} />
              )}
            </div>
          ) : (
            // Show selected table data
            <div className="space-y-2">
              {/* Table header info */}
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-base flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  {selectedTable.displayName}
                  <span className="font-normal text-sm text-muted-foreground">
                    ({selectedTable.rowCount?.toLocaleString("fr-FR")} ligne(s))
                  </span>
                </h3>
              </div>

              {/* Table content */}
              {loadingData ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : dataError ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-center">
                    <AlertCircle className="h-6 w-6 mx-auto text-destructive mb-2" />
                    <p className="text-sm text-destructive">{dataError}</p>
                  </div>
                </div>
              ) : tableData.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-sm text-muted-foreground">Aucune donnée</p>
                </div>
              ) : (
                <div className="border rounded-md overflow-auto max-h-[600px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {(() => {
                          // Get all unique keys from all rows (in case some rows have different fields)
                          const allKeys = new Set<string>();
                          tableData.forEach(row => {
                            Object.keys(row).forEach(key => allKeys.add(key));
                          });

                          // Sort keys: id first, then alphabetically
                          const sortedKeys = Array.from(allKeys).sort((a, b) => {
                            if (a === 'id') return -1;
                            if (b === 'id') return 1;
                            return a.localeCompare(b);
                          });

                          return sortedKeys.map((key) => (
                            <TableHead key={key} className="text-sm">
                              {key}
                            </TableHead>
                          ));
                        })()}
                        <TableHead className="w-[50px] text-sm">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tableData.map((row, idx) => {
                        // Get sorted keys for consistent column order
                        const allKeys = new Set<string>();
                        tableData.forEach(r => {
                          Object.keys(r).forEach(key => allKeys.add(key));
                        });
                        const sortedKeys = Array.from(allKeys).sort((a, b) => {
                          if (a === 'id') return -1;
                          if (b === 'id') return 1;
                          return a.localeCompare(b);
                        });

                        return (
                          <TableRow key={idx}>
                            {sortedKeys.map((key) => {
                              const value = row[key];
                              return (
                                <TableCell key={key} className="text-sm max-w-xs truncate">
                                  {value === null || value === undefined
                                    ? <span className="text-muted-foreground italic">null</span>
                                    : typeof value === "object"
                                    ? JSON.stringify(value)
                                    : String(value)}
                                </TableCell>
                              );
                            })}
                            <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0"
                                >
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  className="text-red-600"
                                  onClick={() => {
                                    const recordId = row.id;
                                    if (recordId) {
                                      setRecordToDelete({
                                        tableName: selectedTable.name,
                                        recordId: String(recordId),
                                        rowIndex: idx,
                                      });
                                    }
                                  }}
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Supprimer
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}
        </div>

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={!!recordToDelete}
          onOpenChange={(open) => {
            if (!open) setRecordToDelete(null);
          }}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
              <AlertDialogDescription>
                Êtes-vous sûr de vouloir supprimer cet enregistrement ?
                Cette action est irréversible.
                <br />
                <span className="font-mono text-xs mt-2 block">
                  ID: {recordToDelete?.recordId}
                </span>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleting}>Annuler</AlertDialogCancel>
              <AlertDialogAction
                onClick={(e) => {
                  e.preventDefault();
                  handleDeleteRecord();
                }}
                disabled={deleting}
                className="bg-red-600 hover:bg-red-700"
              >
                {deleting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Suppression...
                  </>
                ) : (
                  "Supprimer"
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AppShell>
  );
}
