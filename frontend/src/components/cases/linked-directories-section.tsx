"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
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
import {
  Folder,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LinkedDirectoriesDataTable, type LinkedDirectory } from "./linked-directories-data-table";
import { linkedDirectoryApi } from "@/lib/api";
import type { Document } from "@/types";

interface LinkedDirectoriesSectionProps {
  caseId: string;
  documents: Document[];
  onDocumentsChange: () => void;
  onPreviewDirectory?: (directory: LinkedDirectory) => void;
  onLinkDirectory?: () => void;
  onSync?: () => void;
  isSyncing?: boolean;
}

export function LinkedDirectoriesSection({
  caseId,
  documents,
  onDocumentsChange,
  onPreviewDirectory,
  onLinkDirectory,
  onSync,
  isSyncing,
}: LinkedDirectoriesSectionProps) {
  const t = useTranslations();
  const [unlinkDialogOpen, setUnlinkDialogOpen] = useState(false);
  const [directoryToUnlink, setDirectoryToUnlink] = useState<LinkedDirectory | null>(null);
  const [unlinking, setUnlinking] = useState(false);

  // Group documents by link_id
  const linkedDirectories = useMemo(() => {
    const byLinkId = new Map<string, LinkedDirectory>();

    documents.forEach((doc) => {
      if (doc.source_type !== "linked" || !doc.linked_source) {
        return;
      }

      const linkId = doc.linked_source.link_id || "unknown";

      if (!byLinkId.has(linkId)) {
        // Create new directory entry
        // Use base_path from linked_source if available (new documents)
        // Otherwise fallback to calculating from absolute_path (old documents)
        const basePath = doc.linked_source.base_path
          || (doc.linked_source.absolute_path
            ? doc.linked_source.absolute_path.split("/").slice(0, -1).join("/")
            : doc.file_path?.split("/").slice(0, -1).join("/") || "");

        byLinkId.set(linkId, {
          linkId,
          basePath,
          linkedAt: doc.created_at || "",
          totalFiles: 0,
          totalSize: 0,
          documents: [],
        });
      }

      const dir = byLinkId.get(linkId)!;
      dir.documents.push(doc);
      dir.totalFiles++;
      dir.totalSize += doc.size || 0;
    });

    return Array.from(byLinkId.values());
  }, [documents]);

  // View directory tree
  const handleViewTree = (directory: LinkedDirectory) => {
    onPreviewDirectory?.(directory);
  };

  // Handle unlink click (opens confirmation dialog)
  const handleUnlinkClick = (directory: LinkedDirectory) => {
    setDirectoryToUnlink(directory);
    setUnlinkDialogOpen(true);
  };

  // Unlink directory (confirmed)
  const handleUnlink = async () => {
    if (!directoryToUnlink) return;

    setUnlinking(true);

    try {
      // Use dedicated backend endpoint to unlink all documents at once
      await linkedDirectoryApi.unlink(caseId, directoryToUnlink.linkId);

      onDocumentsChange();
      setUnlinkDialogOpen(false);
      setDirectoryToUnlink(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de la suppression");
    } finally {
      setUnlinking(false);
    }
  };

  return (
    <>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base flex items-center gap-2">
            <Folder className="h-4 w-4" />
            {t("courses.linkedDirectories")} ({linkedDirectories.length})
          </h3>
          <div className="flex items-center gap-2">
            {onLinkDirectory && (
              <Button size="sm" onClick={onLinkDirectory} className="gap-1">
                <Folder className="h-3 w-3" />
                {t("courses.linkDirectory")}
              </Button>
            )}
            {onSync && (
              <Button size="sm" onClick={onSync} disabled={isSyncing} className="gap-1">
                {isSyncing ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3" />
                )}
                {t("courses.synchronize")}
              </Button>
            )}
          </div>
        </div>
        <LinkedDirectoriesDataTable
          directories={linkedDirectories}
          onViewTree={handleViewTree}
          onUnlink={handleUnlinkClick}
        />
      </div>

      {/* Unlink confirmation dialog */}
      <AlertDialog open={unlinkDialogOpen} onOpenChange={setUnlinkDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("courses.unlinkDirectory")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("courses.unlinkWarning", {
                count: directoryToUnlink?.totalFiles || 0,
                path: directoryToUnlink?.basePath || ""
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDirectoryToUnlink(null)}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleUnlink}
              disabled={unlinking}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
            >
              {unlinking ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t("courses.unlinking")}
                </>
              ) : (
                t("courses.unlink")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
