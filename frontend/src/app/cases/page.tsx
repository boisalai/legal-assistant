"use client";

import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/cases/data-table";
import { createColumns } from "@/components/cases/columns";
import { AppShell } from "@/components/layout";
import { casesApi } from "@/lib/api";
import type { Case } from "@/types";
import { Loader2, FolderOpen } from "lucide-react";

export default function CasesListPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCases = useCallback(async () => {
    try {
      const data = await casesApi.list();
      setCases(data);
    } catch {
      setError("Impossible de charger les dossiers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer ce dossier ?")) return;
    try {
      await casesApi.delete(id);
      setCases((prev) => prev.filter((c) => c.id !== id));
    } catch {
      alert("Erreur lors de la suppression");
    }
  };

  const handleDeleteSelected = async (ids: string[]) => {
    try {
      await casesApi.deleteMany(ids);
      setCases((prev) => prev.filter((c) => !ids.includes(c.id)));
    } catch {
      alert("Erreur lors de la suppression");
    }
  };

  const handleTogglePin = async (id: string) => {
    try {
      const updatedCase = await casesApi.togglePin(id);
      setCases((prev) =>
        prev.map((c) => (c.id === id ? updatedCase : c))
      );
    } catch {
      alert("Erreur lors de l'épinglage");
    }
  };

  const columns = createColumns(handleDelete, handleTogglePin);

  // Sort cases: pinned first, then by updated_at descending
  const sortedCases = [...cases].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive">{error}</p>
          <Button
            variant="outline"
            onClick={() => { setError(null); setLoading(true); fetchCases(); }}
          >
            Réessayer
          </Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <FolderOpen className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Dossiers</h1>
            <p className="text-muted-foreground">
              {cases.length} dossier{cases.length !== 1 ? "s" : ""} au total
            </p>
          </div>
        </div>

        {/* Cases Table */}
        {cases.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground border rounded-lg bg-card">
            <FolderOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <p>Aucun dossier pour le moment.</p>
            <p className="text-sm mt-2">Utilisez le bouton "+ Nouveau dossier" en haut à droite pour commencer.</p>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={sortedCases}
            onDeleteSelected={handleDeleteSelected}
          />
        )}
      </div>
    </AppShell>
  );
}
