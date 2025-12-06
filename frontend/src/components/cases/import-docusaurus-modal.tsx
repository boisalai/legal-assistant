"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { FileText, Folder, Loader2, Search } from "lucide-react";
import { docusaurusApi } from "@/lib/api";
import type { DocusaurusFile } from "@/types";

interface ImportDocusaurusModalProps {
  caseId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess: () => void;
}

export function ImportDocusaurusModal({
  caseId,
  open,
  onOpenChange,
  onImportSuccess,
}: ImportDocusaurusModalProps) {
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [files, setFiles] = useState<DocusaurusFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Load Docusaurus files when modal opens
  useEffect(() => {
    if (open) {
      loadFiles();
    }
  }, [open]);

  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await docusaurusApi.listFiles();
      setFiles(response.files);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement des fichiers");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFile = (filePath: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(filePath)) {
      newSelected.delete(filePath);
    } else {
      newSelected.add(filePath);
    }
    setSelectedFiles(newSelected);
  };

  const handleSelectFolder = (folder: string) => {
    const folderFiles = files
      .filter((f) => f.folder === folder)
      .map((f) => f.absolute_path);

    const newSelected = new Set(selectedFiles);
    const allSelected = folderFiles.every((path) => newSelected.has(path));

    if (allSelected) {
      // Deselect all files in folder
      folderFiles.forEach((path) => newSelected.delete(path));
    } else {
      // Select all files in folder
      folderFiles.forEach((path) => newSelected.add(path));
    }

    setSelectedFiles(newSelected);
  };

  const handleImport = async () => {
    if (selectedFiles.size === 0) {
      return;
    }

    setImporting(true);
    setError(null);

    try {
      await docusaurusApi.importFiles(caseId, Array.from(selectedFiles));
      onImportSuccess();
      onOpenChange(false);
      setSelectedFiles(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'import");
    } finally {
      setImporting(false);
    }
  };

  // Filter files based on search query
  const filteredFiles = files.filter(
    (file) =>
      file.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      file.folder.toLowerCase().includes(searchQuery.toLowerCase()) ||
      file.relative_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group files by folder
  const filesByFolder = filteredFiles.reduce((acc, file) => {
    if (!acc[file.folder]) {
      acc[file.folder] = [];
    }
    acc[file.folder].push(file);
    return acc;
  }, {} as Record<string, DocusaurusFile[]>);

  const folders = Object.keys(filesByFolder).sort();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>📚 Importer depuis Docusaurus</DialogTitle>
          <DialogDescription>
            Sélectionnez les fichiers de documentation à importer dans ce dossier.
            Les fichiers seront indexés automatiquement pour la recherche sémantique.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="flex-1 flex flex-col min-h-0">
          {/* Search */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Rechercher par nom de fichier ou dossier..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* File list */}
          <ScrollArea className="flex-1 border rounded-md p-4">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            ) : folders.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                {searchQuery ? "Aucun fichier trouvé" : "Aucun fichier disponible"}
              </div>
            ) : (
              <div className="space-y-6">
                {folders.map((folder) => {
                  const folderFiles = filesByFolder[folder];
                  const allSelected = folderFiles.every((f) => selectedFiles.has(f.absolute_path));
                  const someSelected = folderFiles.some((f) => selectedFiles.has(f.absolute_path));

                  return (
                    <div key={folder} className="space-y-2">
                      {/* Folder header */}
                      <div className="flex items-center space-x-2 sticky top-0 bg-white py-2 border-b">
                        <Checkbox
                          checked={allSelected}
                          onCheckedChange={() => handleSelectFolder(folder)}
                          className={someSelected && !allSelected ? "opacity-50" : ""}
                        />
                        <Folder className="h-4 w-4 text-blue-500" />
                        <span className="font-medium text-sm">{folder}</span>
                        <Badge variant="outline" className="ml-auto">
                          {folderFiles.length} fichier{folderFiles.length > 1 ? "s" : ""}
                        </Badge>
                      </div>

                      {/* Files in folder */}
                      <div className="pl-6 space-y-1">
                        {folderFiles.map((file) => (
                          <div
                            key={file.absolute_path}
                            className="flex items-center space-x-2 py-1 hover:bg-gray-50 rounded px-2"
                          >
                            <Checkbox
                              checked={selectedFiles.has(file.absolute_path)}
                              onCheckedChange={() => handleToggleFile(file.absolute_path)}
                            />
                            <FileText className="h-4 w-4 text-gray-400" />
                            <span className="text-sm flex-1">{file.filename}</span>
                            <span className="text-xs text-gray-400">
                              {(file.size / 1024).toFixed(1)} KB
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>

          {/* Selection summary */}
          {selectedFiles.size > 0 && (
            <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
              <p className="text-sm text-blue-700">
                <strong>{selectedFiles.size}</strong> fichier{selectedFiles.size > 1 ? "s" : ""}{" "}
                sélectionné{selectedFiles.size > 1 ? "s" : ""}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={importing}>
            Annuler
          </Button>
          <Button onClick={handleImport} disabled={selectedFiles.size === 0 || importing}>
            {importing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Importer {selectedFiles.size > 0 && `(${selectedFiles.size})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
