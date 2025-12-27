"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus } from "lucide-react";
import { sessionsApi } from "@/lib/api";
import type { Session } from "@/types";
import { CreateSessionModal } from "@/components/sessions/create-session-modal";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
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
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Sessions Académiques</h1>
          <p className="text-muted-foreground mt-2">
            Gérez vos sessions académiques (semestres, années)
          </p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouvelle Session
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">Erreur : {error}</p>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">Chargement des sessions...</p>
          </CardContent>
        </Card>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">
              Aucune session académique. Créez-en une pour commencer.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <Card key={session.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <CardTitle className="text-lg">{session.title}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {session.semester} {session.year}
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Début : </span>
                    <span>{new Date(session.start_date).toLocaleDateString("fr-FR")}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Fin : </span>
                    <span>{new Date(session.end_date).toLocaleDateString("fr-FR")}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Session Modal */}
      <CreateSessionModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onSessionCreated={loadSessions}
      />
    </div>
  );
}
