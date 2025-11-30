"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/cases/data-table";
import { createColumns } from "@/components/cases/columns";
import { AppShell } from "@/components/layout";
import { NewCaseModal } from "@/components/cases/new-case-modal";
import { casesApi } from "@/lib/api";
import type { Case } from "@/types";
import { Loader2 } from "lucide-react";

function DashboardContent() {
  const t = useTranslations();
  const searchParams = useSearchParams();
  const searchQuery = searchParams.get("search") || "";

  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewCaseModal, setShowNewCaseModal] = useState(false);

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
      {/* Cases Table */}
      {cases.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground border rounded-lg bg-card">
          <p>Aucun dossier pour le moment.</p>
          <p className="text-sm mt-2">Utilisez le bouton "+ Nouveau dossier" pour commencer.</p>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={cases}
          onDeleteSelected={handleDeleteSelected}
          initialFilter={searchQuery}
          onNewCase={() => setShowNewCaseModal(true)}
          newCaseLabel={t("nav.newCase")}
        />
      )}

      <NewCaseModal open={showNewCaseModal} onOpenChange={setShowNewCaseModal} />
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
