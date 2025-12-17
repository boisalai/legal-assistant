"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/cases/data-table";
import { createColumns } from "@/components/cases/columns";
import { AppShell } from "@/components/layout";
import { NewCaseModal } from "@/components/cases/new-case-modal";
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
  const [caseToDelete, setCaseToDelete] = useState<string | null>(null);

  const fetchCases = useCallback(async () => {
    try {
      const data = await casesApi.list();
      setCases(data);
    } catch {
      setError(t("dashboard.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const handleDelete = (id: string) => {
    setCaseToDelete(id);
  };

  const confirmDelete = async () => {
    if (!caseToDelete) return;

    try {
      await casesApi.delete(caseToDelete);
      setCases((prev) => prev.filter((c) => c.id !== caseToDelete));
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
    } finally {
      setCaseToDelete(null);
    }
  };

  const handleDeleteSelected = async (ids: string[]) => {
    try {
      await casesApi.deleteMany(ids);
      setCases((prev) => prev.filter((c) => !ids.includes(c.id)));
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
    }
  };

  const handleTogglePin = async (id: string) => {
    try {
      // @ts-ignore - TODO: Implement togglePin method in casesApi or remove this functionality
      const updatedCase = await casesApi.togglePin(id);
      setCases((prev) =>
        prev.map((c) => (c.id === id ? updatedCase : c))
      );
    } catch (error) {
      console.error("Erreur lors de l'épinglage:", error);
    }
  };

  const columns = createColumns(handleDelete, handleTogglePin, (key: string) => t(key));

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
          <p className="mb-4">Aucun cours pour le moment.</p>
          <Button onClick={() => setShowNewCaseModal(true)}>
            + Nouveau cours
          </Button>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={cases}
          onDeleteSelected={handleDeleteSelected}
          initialFilter={searchQuery}
          onNewCase={() => setShowNewCaseModal(true)}
          newCaseLabel={t("nav.newCourse")}
        />
      )}

      <NewCaseModal open={showNewCaseModal} onOpenChange={setShowNewCaseModal} />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!caseToDelete} onOpenChange={(open) => !open && setCaseToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce dossier ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette action est irréversible. Le dossier et tous ses documents seront définitivement supprimés.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive hover:bg-destructive/90">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
