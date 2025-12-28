"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Database, Loader2, AlertCircle, Eye } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AppShell } from "@/components/layout";
import { DataTable } from "@/components/cases/data-table";
import { adminApi, authApi, type TableInfo } from "@/lib/api";

export default function AdminDatabasePage() {
  const t = useTranslations("admin");
  const router = useRouter();

  // State
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Table viewer state
  const [selectedTable, setSelectedTable] = useState<TableInfo | null>(null);
  const [tableData, setTableData] = useState<any[]>([]);
  const [loadingData, setLoadingData] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

  // Handle view table
  const handleViewTable = async (table: TableInfo) => {
    setSelectedTable(table);
    setLoadingData(true);
    setDataError(null);
    try {
      const data = await adminApi.database.getTableData(table.name, {
        limit: 50,
      });
      console.log(`📊 Data for table ${table.name}:`, data);
      setTableData(data.rows);
    } catch (err: any) {
      console.error("Error fetching table data:", err);
      setDataError(err.message || "Erreur lors du chargement des données");
    } finally {
      setLoadingData(false);
    }
  };

  // Table columns
  const columns = useMemo<ColumnDef<TableInfo>[]>(
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
        cell: ({ row }) => (
          <Badge variant="outline">
            {row.original.rowCount !== undefined
              ? row.original.rowCount.toLocaleString("fr-FR")
              : "N/A"}
          </Badge>
        ),
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
          row.original.hasOrphans ? (
            <Badge variant="destructive" className="text-xs">
              Orphelins
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-xs">
              OK
            </Badge>
          ),
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
      console.log("📊 Tables data received:", data);
      setTables(data);
    } catch (err: any) {
      console.error("Error fetching tables:", err);
      setError(err.message || "Erreur lors du chargement des tables");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600" />
            <p className="mt-4 text-sm text-gray-500">{t("database.loading")}</p>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-5 w-5" />
                Erreur
              </CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={fetchTables} variant="outline">
                Réessayer
              </Button>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t("database.title")}
          </h1>
          <p className="text-muted-foreground mt-2">
            {t("database.description")}
          </p>
        </div>

        {/* DataTable */}
        {tables.length === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <div className="text-center">
                <Database className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-4 text-sm text-gray-500">
                  {t("database.noTables")}
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <DataTable columns={columns} data={tables} />
        )}

        {/* Table Viewer Dialog */}
        <Dialog
          open={!!selectedTable}
          onOpenChange={(open) => {
            if (!open) {
              setSelectedTable(null);
              setTableData([]);
              setDataError(null);
            }
          }}
        >
          <DialogContent className="max-w-6xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600" />
                {selectedTable?.displayName}
              </DialogTitle>
              <DialogDescription className="font-mono text-xs">
                {selectedTable?.name} — {selectedTable?.rowCount?.toLocaleString("fr-FR")} ligne(s)
              </DialogDescription>
            </DialogHeader>

            <div className="flex-1 overflow-auto">
              {loadingData ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
              ) : dataError ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <AlertCircle className="h-8 w-8 mx-auto text-red-600 mb-2" />
                    <p className="text-sm text-red-600">{dataError}</p>
                  </div>
                </div>
              ) : tableData.length === 0 ? (
                <div className="flex items-center justify-center py-12">
                  <p className="text-sm text-muted-foreground">Aucune donnée</p>
                </div>
              ) : (
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {Object.keys(tableData[0] || {}).map((key) => (
                          <TableHead key={key} className="font-mono text-xs">
                            {key}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tableData.map((row, idx) => (
                        <TableRow key={idx}>
                          {Object.entries(row).map(([key, value]) => (
                            <TableCell key={key} className="font-mono text-xs max-w-xs truncate">
                              {value === null
                                ? <span className="text-muted-foreground italic">null</span>
                                : typeof value === "object"
                                ? JSON.stringify(value)
                                : String(value)}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
