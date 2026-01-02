"use client";

import { useState } from "react";
import { LinkedDirectoriesSection } from "./linked-directories-section";
import { SyncProgressModal, SyncTask, SyncResult } from "./sync-progress-modal";
import { documentsApi } from "@/lib/api";
import { toast } from "sonner";
import type { Document } from "@/types";
import type { LinkedDirectory } from "./linked-directories-data-table";

interface SyncSectionProps {
  courseId: string;
  documents: Document[];
  onDocumentsChange?: () => Promise<void>;
  onPreviewDirectory: (directory: LinkedDirectory) => void;
  onLinkDirectory: () => void;
}

export function SyncSection({
  courseId,
  documents,
  onDocumentsChange,
  onPreviewDirectory,
  onLinkDirectory,
}: SyncSectionProps) {
  // Sync state
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncComplete, setSyncComplete] = useState(false);
  const [syncHasError, setSyncHasError] = useState(false);

  // Filter to show only linked documents
  const linkedDocuments = documents.filter((doc) => doc.source_type === "linked");

  const handleSyncDocuments = async () => {
    setSyncModalOpen(true);
    setSyncComplete(false);
    setSyncHasError(false);
    setSyncResult(null);

    const initialTasks: SyncTask[] = [
      { id: "scan-uploaded", label: "Analyse des documents uploadés", status: "pending" },
      { id: "scan-linked", label: "Analyse des répertoires liés", status: "pending" },
      { id: "refresh", label: "Actualisation de la liste", status: "pending" },
    ];
    setSyncTasks(initialTasks);

    try {
      // Step 1: Sync uploaded documents
      setSyncTasks((prev) =>
        prev.map((t) => (t.id === "scan-uploaded" ? { ...t, status: "running" } : t))
      );

      const uploadResult = await documentsApi.sync(courseId);
      const uploadDetails: string[] = [];
      if (uploadResult.discovered > 0) {
        uploadDetails.push(`${uploadResult.discovered} fichier(s) découvert(s)`);
      }

      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "scan-uploaded"
            ? { ...t, status: "completed", details: uploadDetails.length > 0 ? uploadDetails : ["Aucun changement"] }
            : t
        )
      );

      // Step 2: Sync linked directories
      setSyncTasks((prev) =>
        prev.map((t) => (t.id === "scan-linked" ? { ...t, status: "running" } : t))
      );

      const linkedResult = await documentsApi.syncLinkedDirectories(courseId);
      const linkedDetails: string[] = [];
      if (linkedResult.added > 0) linkedDetails.push(`${linkedResult.added} fichier(s) ajouté(s)`);
      if (linkedResult.updated > 0) linkedDetails.push(`${linkedResult.updated} fichier(s) mis à jour`);
      if (linkedResult.removed > 0) linkedDetails.push(`${linkedResult.removed} fichier(s) supprimé(s)`);

      setSyncTasks((prev) =>
        prev.map((t) =>
          t.id === "scan-linked"
            ? { ...t, status: "completed", details: linkedDetails.length > 0 ? linkedDetails : ["Aucun changement"] }
            : t
        )
      );

      // Step 3: Refresh documents list
      setSyncTasks((prev) =>
        prev.map((t) => (t.id === "refresh" ? { ...t, status: "running" } : t))
      );

      if (onDocumentsChange) await onDocumentsChange();

      setSyncTasks((prev) =>
        prev.map((t) => (t.id === "refresh" ? { ...t, status: "completed" } : t))
      );

      setSyncResult({
        uploadedDiscovered: uploadResult.discovered,
        linkedAdded: linkedResult.added,
        linkedUpdated: linkedResult.updated,
        linkedRemoved: linkedResult.removed,
      });

      setSyncComplete(true);
      setSyncHasError(false);
    } catch (err) {
      setSyncTasks((prev) =>
        prev.map((t) =>
          t.status === "running"
            ? { ...t, status: "error", error: err instanceof Error ? err.message : "Erreur inconnue" }
            : t
        )
      );
      setSyncComplete(true);
      setSyncHasError(true);
      toast.error("Erreur lors de la synchronisation");
    }
  };

  return (
    <>
      <LinkedDirectoriesSection
        caseId={courseId}
        documents={linkedDocuments}
        onDocumentsChange={onDocumentsChange || (() => Promise.resolve())}
        onPreviewDirectory={onPreviewDirectory}
        onLinkDirectory={onLinkDirectory}
        onSync={handleSyncDocuments}
        isSyncing={syncModalOpen && !syncComplete}
      />

      <SyncProgressModal
        open={syncModalOpen}
        onOpenChange={setSyncModalOpen}
        tasks={syncTasks}
        result={syncResult}
        isComplete={syncComplete}
        hasError={syncHasError}
      />
    </>
  );
}
