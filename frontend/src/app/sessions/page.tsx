"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/cases/data-table";
import { createSessionColumns } from "@/components/sessions/columns";
import { AppShell } from "@/components/layout";
import { CreateSessionModal } from "@/components/sessions/create-session-modal";
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
import { sessionsApi } from "@/lib/api";
import type { Session } from "@/types";
import { Loader2, Calendar } from "lucide-react";
import { toast } from "sonner";

export default function SessionsPage() {
  const t = useTranslations();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await sessionsApi.list(1, 100);
      setSessions(response.items);
    } catch (err) {
      console.error("Failed to load sessions:", err);
      setError(err instanceof Error ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleEdit = (id: string) => {
    // TODO: Implement edit modal
    toast.info("Modification de session - à implémenter");
  };

  const handleDelete = (id: string) => {
    setSessionToDelete(id);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;

    try {
      await sessionsApi.delete(sessionToDelete);
      setSessions((prev) => prev.filter((s) => s.id !== sessionToDelete));
      toast.success("Session supprimée avec succès");
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Erreur lors de la suppression"
      );
    } finally {
      setSessionToDelete(null);
    }
  };

  const handleDeleteSelected = async (ids: string[]) => {
    try {
      // Delete sessions one by one
      await Promise.all(ids.map((id) => sessionsApi.delete(id)));
      setSessions((prev) => prev.filter((s) => !ids.includes(s.id)));
      toast.success(`${ids.length} session(s) supprimée(s)`);
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      toast.error("Erreur lors de la suppression");
    }
  };

  const columns = createSessionColumns(handleEdit, handleDelete, (key: string) =>
    t(key)
  );

  // Sort sessions by year and semester
  const sortedSessions = [...sessions].sort((a, b) => {
    if (a.year !== b.year) return b.year - a.year;
    const semesterOrder: Record<string, number> = {
      Hiver: 1,
      Été: 2,
      Automne: 3,
    };
    return (semesterOrder[a.semester] || 0) - (semesterOrder[b.semester] || 0);
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
            onClick={() => {
              setError(null);
              setLoading(true);
              fetchSessions();
            }}
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
        {/* Sessions Table */}
        {sessions.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground border rounded-lg bg-card">
            <Calendar className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <p className="mb-4">Aucune session académique</p>
            <p className="text-sm mb-6">
              Créez une session pour organiser vos cours par semestre
            </p>
            <Button onClick={() => setCreateModalOpen(true)}>
              + Nouvelle Session
            </Button>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={sortedSessions}
            onDeleteSelected={handleDeleteSelected}
            onNewCase={() => setCreateModalOpen(true)}
            newCaseLabel="Nouvelle Session"
          />
        )}

        {/* Create Session Modal */}
        <CreateSessionModal
          open={createModalOpen}
          onOpenChange={setCreateModalOpen}
          onSessionCreated={fetchSessions}
        />

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={!!sessionToDelete}
          onOpenChange={(open) => !open && setSessionToDelete(null)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Supprimer cette session ?</AlertDialogTitle>
              <AlertDialogDescription>
                Cette action est irréversible. La session sera définitivement
                supprimée.
                {sessions.find((s) => s.id === sessionToDelete) && (
                  <div className="mt-2 font-semibold">
                    {sessions.find((s) => s.id === sessionToDelete)?.title}
                  </div>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction
                onClick={confirmDelete}
                className="bg-destructive hover:bg-destructive/90"
              >
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AppShell>
  );
}
