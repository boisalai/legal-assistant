"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  FolderOpen,
  MoreVertical,
  Trash2,
  Eye,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { DirectoryTreeView } from "./directory-tree-view";
import { documentsApi } from "@/lib/api";
import type { Document } from "@/types";

interface LinkedDirectoriesSectionProps {
  caseId: string;
  documents: Document[];
  onDocumentsChange: () => void;
}

interface LinkedDirectory {
  linkId: string;
  basePath: string;
  linkedAt: string;
  totalFiles: number;
  totalSize: number;
  documents: Document[];
}

export function LinkedDirectoriesSection({
  caseId,
  documents,
  onDocumentsChange,
}: LinkedDirectoriesSectionProps) {
  const [selectedDirectory, setSelectedDirectory] = useState<LinkedDirectory | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
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
        name: doc.nom_fichier,
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
      dir.totalSize += doc.taille || 0;
    });

    const result = Array.from(byLinkId.values());
    console.log("LinkedDirectoriesSection: Final result", {
      directoriesCount: result.length,
      directories: result
    });

    return result;
  }, [documents]);

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  // Format date
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString("fr-CA", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  // View directory tree
  const handleViewTree = (directory: LinkedDirectory) => {
    setSelectedDirectory(directory);
    setSheetOpen(true);
  };

  // Unlink directory
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
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Folder className="h-4 w-4" />
            Répertoires liés ({linkedDirectories.length})
          </CardTitle>
          <CardDescription>
            Répertoires locaux indexés automatiquement
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {linkedDirectories.map((directory) => (
              <div
                key={directory.linkId}
                className="flex items-center gap-3 p-4 rounded-lg border hover:bg-muted/50 transition-colors"
              >
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950">
                  <FolderOpen className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="font-mono text-sm truncate mb-1" title={directory.basePath}>
                    {directory.basePath}
                  </p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{directory.totalFiles} fichiers</span>
                    <span>•</span>
                    <span>{formatFileSize(directory.totalSize)}</span>
                    <span>•</span>
                    <span>Lié le {formatDate(directory.linkedAt)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    Lié
                  </Badge>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleViewTree(directory)}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Voir l'arborescence
                  </Button>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleViewTree(directory)}>
                        <Eye className="h-4 w-4 mr-2" />
                        Voir l'arborescence
                      </DropdownMenuItem>

                      <DropdownMenuSeparator />

                      <DropdownMenuItem
                        onClick={() => {
                          setDirectoryToUnlink(directory);
                          setUnlinkDialogOpen(true);
                        }}
                        className="text-destructive"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Délier le répertoire
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tree view sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              Arborescence du répertoire
            </SheetTitle>
            <SheetDescription>
              {selectedDirectory?.totalFiles} fichiers • {formatFileSize(selectedDirectory?.totalSize || 0)}
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 h-[calc(100vh-120px)]">
            {selectedDirectory && (
              <DirectoryTreeView
                documents={selectedDirectory.documents}
                basePath={selectedDirectory.basePath}
              />
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* Unlink confirmation dialog */}
      <AlertDialog open={unlinkDialogOpen} onOpenChange={setUnlinkDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Délier ce répertoire ?</AlertDialogTitle>
            <AlertDialogDescription>
              Tous les fichiers de ce répertoire ({directoryToUnlink?.totalFiles} fichiers) seront retirés de ce dossier.
              <br />
              <br />
              <span className="font-mono text-xs block p-2 bg-muted rounded mt-2">
                {directoryToUnlink?.basePath}
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDirectoryToUnlink(null)}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleUnlink} disabled={unlinking}>
              {unlinking ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Suppression...
                </>
              ) : (
                "Délier"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
