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
} from "lucide-react";
import { LinkedDirectoriesDataTable, type LinkedDirectory } from "./linked-directories-data-table";
import { documentsApi } from "@/lib/api";
import type { Document } from "@/types";

interface LinkedDirectoriesSectionProps {
  caseId: string;
  documents: Document[];
  onDocumentsChange: () => void;
  onPreviewDirectory?: (directory: LinkedDirectory) => void;
}

export function LinkedDirectoriesSection({
  caseId,
  documents,
  onDocumentsChange,
  onPreviewDirectory,
}: LinkedDirectoriesSectionProps) {
  const t = useTranslations();
  const [unlinkDialogOpen, setUnlinkDialogOpen] = useState(false);
  const [directoryToUnlink, setDirectoryToUnlink] = useState<LinkedDirectory | null>(null);
  const [unlinking, setUnlinking] = useState(false);

  // Group documents by link_id
  const linkedDirectories = useMemo(() => {
    console.log("LinkedDirectoriesSection: Grouping documents", {
      totalDocs: documents.length,
      sampleDoc: documents[0]
    });

    const byLinkId = new Map<string, LinkedDirectory>();

    documents.forEach((doc) => {
      console.log("Processing doc:", {
        id: doc.id,
        name: doc.filename,
        source_type: doc.source_type,
        has_linked_source: !!doc.linked_source,
        linked_source: doc.linked_source
      });

      if (doc.source_type !== "linked" || !doc.linked_source) {
        console.log("Skipping doc (not linked or no linked_source):", doc.id);
        return;
      }

      const linkId = doc.linked_source.link_id || "unknown";

      if (!byLinkId.has(linkId)) {
        // Create new directory entry
        const basePath = doc.linked_source.absolute_path
          ? doc.linked_source.absolute_path.split("/").slice(0, -1).join("/")
          : doc.file_path?.split("/").slice(0, -1).join("/") || "";

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

    const result = Array.from(byLinkId.values());
    console.log("LinkedDirectoriesSection: Final result", {
      directoriesCount: result.length,
      directories: result
    });

    return result;
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
      // Delete all documents with this link_id
      for (const doc of directoryToUnlink.documents) {
        await documentsApi.delete(caseId, doc.id);
      }

      onDocumentsChange();
      setUnlinkDialogOpen(false);
      setDirectoryToUnlink(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de la suppression");
    } finally {
      setUnlinking(false);
    }
  };

  console.log("LinkedDirectoriesSection: About to render", {
    linkedDirectoriesCount: linkedDirectories.length,
    willReturnNull: linkedDirectories.length === 0
  });

  if (linkedDirectories.length === 0) {
    console.log("❌ LinkedDirectoriesSection: Returning null (no directories)");
    return null;
  }

  console.log("✅ LinkedDirectoriesSection: Rendering card with", linkedDirectories.length, "directories");

  return (
    <>
      <div className="space-y-2">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Folder className="h-4 w-4" />
          {t("courses.linkedDirectories")} ({linkedDirectories.length})
        </h3>
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
              {t("courses.unlinkWarning", { count: directoryToUnlink?.totalFiles || 0 })}
              <br />
              <br />
              <span className="font-mono text-xs block p-2 bg-muted rounded mt-2">
                {directoryToUnlink?.basePath}
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDirectoryToUnlink(null)}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleUnlink} disabled={unlinking}>
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
