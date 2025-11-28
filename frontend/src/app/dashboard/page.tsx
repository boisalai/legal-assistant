"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/cases/data-table";
import { createColumns } from "@/components/cases/columns";
import { AppShell } from "@/components/layout";
import { casesApi } from "@/lib/api";
import type { Case } from "@/types";
import { Loader2 } from "lucide-react";

function DashboardContent() {
  const searchParams = useSearchParams();
  const searchQuery = searchParams.get("search") || "";

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

  const columns = createColumns(handleDelete);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-destructive">{error}</p>
        <Button
          variant="outline"
          onClick={() => { setError(null); setLoading(true); fetchCases(); }}
        >
          Réessayer
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatCard
          title="Total dossiers"
          value={cases.length}
          description="dossiers créés"
        />
        <StatCard
          title="Nouveaux"
          value={cases.filter(c => c.statut === "nouveau").length}
          description="à analyser"
          className="text-blue-600"
        />
        <StatCard
          title="En analyse"
          value={cases.filter(c => c.statut === "en_analyse").length}
          description="en cours"
          className="text-yellow-600"
        />
        <StatCard
          title="Terminés"
          value={cases.filter(c => c.statut === "termine").length}
          description="terminés"
          className="text-green-600"
        />
        <StatCard
          title="En erreur"
          value={cases.filter(c => c.statut === "en_erreur").length}
          description="à corriger"
          className="text-red-600"
        />
        <StatCard
          title="Archivés"
          value={cases.filter(c => c.statut === "archive").length}
          description="archivés"
          className="text-gray-500"
        />
      </div>

      {/* Cases Table */}
      {cases.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground border rounded-lg bg-card">
          <p>Aucun dossier pour le moment.</p>
          <p className="text-sm mt-2">Utilisez le bouton "+ Nouveau dossier" en haut à droite pour commencer.</p>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={cases}
          onDeleteSelected={handleDeleteSelected}
          initialFilter={searchQuery}
        />
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell>
      <Suspense fallback={
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }>
        <DashboardContent />
      </Suspense>
    </AppShell>
  );
}

interface StatCardProps {
  title: string;
  value: number;
  description: string;
  className?: string;
}

function StatCard({ title, value, description, className }: StatCardProps) {
  return (
    <div className="bg-card rounded-lg border p-4">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className={`text-2xl font-bold ${className || ""}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}
