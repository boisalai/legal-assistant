"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { sessionsApi } from "@/lib/api";
import type { Session } from "@/types";

interface SessionSelectorProps {
  value?: string;
  onValueChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function SessionSelector({
  value,
  onValueChange,
  disabled = false,
  placeholder = "Sélectionner une session",
}: SessionSelectorProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await sessionsApi.list(1, 100); // Get first 100 sessions
      setSessions(response.items);
    } catch (err) {
      console.error("Failed to load sessions:", err);
      setError(err instanceof Error ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="text-sm text-destructive">
        Erreur : {error}
      </div>
    );
  }

  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled || loading}>
      <SelectTrigger>
        <SelectValue placeholder={loading ? "Chargement..." : placeholder} />
      </SelectTrigger>
      <SelectContent>
        {sessions.length === 0 && !loading && (
          <div className="p-2 text-sm text-muted-foreground">
            Aucune session disponible
          </div>
        )}
        {sessions.map((session) => (
          <SelectItem key={session.id} value={session.id}>
            {session.title} ({session.semester} {session.year})
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
