"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileUpload } from "@/components/ui/file-upload";
import { UploadModal } from "@/components/cases/upload-modal";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  FileText,
  Download,
  Trash2,
  Eye,
  Upload,
  File,
  Image,
  FileSpreadsheet,
  FileAudio,
  FileType2,
  FileCode2,
  Mic,
} from "lucide-react";
import { documentsApi } from "@/lib/api";
import type { Document } from "@/types";

interface DocumentsTabProps {
  caseId: string;
  documents: Document[];
  onDocumentsChange: () => void;
}

export function DocumentsTab({ caseId, documents, onDocumentsChange }: DocumentsTabProps) {
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;

    setUploading(true);
    try {
      for (const file of files) {
        await documentsApi.upload(caseId, file);
      }
      setFiles([]);
      onDocumentsChange();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de l'upload");
    } finally {
      setUploading(false);
    }
  }, [caseId, files, onDocumentsChange]);

  const handleDelete = async (documentId: string) => {
    setDeletingId(documentId);
    try {
      await documentsApi.delete(caseId, documentId);
      onDocumentsChange();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de la suppression");
    } finally {
      setDeletingId(null);
    }
  };

  const handlePreview = (document: Document) => {
    documentsApi.preview(caseId, document.id);
  };

  const handleDownload = (document: Document) => {
    documentsApi.download(caseId, document.id, document.nom_fichier);
  };

  // Determine file icon based on type/extension - uniform Lucide icons
  const getFileIcon = (type?: string | null, filename?: string | null) => {
    if (!type && !filename) return File;

    const lowerType = (type || "").toLowerCase();
    const ext = filename ? filename.split(".").pop()?.toLowerCase() : "";

    // PDF
    if (lowerType.includes("pdf") || ext === "pdf") return FileText;

    // Images
    if (
      lowerType.includes("image") ||
      ["jpg", "jpeg", "png", "gif", "webp", "tiff", "tif", "bmp"].includes(ext || "")
    ) {
      return Image;
    }

    // Audio
    if (
      lowerType.includes("audio") ||
      lowerType.includes("video") ||
      ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac", "mp2", "pcm", "wma"].includes(ext || "")
    ) {
      return FileAudio;
    }

    // Word documents
    if (lowerType.includes("word") || ["doc", "docx"].includes(ext || "")) return FileType2;

    // Text and Markdown
    if (lowerType.includes("text") || ["txt", "rtf", "md", "markdown"].includes(ext || "")) return FileCode2;

    // Spreadsheets
    if (
      lowerType.includes("excel") ||
      lowerType.includes("spreadsheet") ||
      ["xls", "xlsx", "csv"].includes(ext || "")
    ) {
      return FileSpreadsheet;
    }

    return File;
  };

  const getFileTypeLabel = (type?: string | null, filename?: string | null) => {
    if (!type && !filename) return "fichier";

    const ext = filename ? filename.split(".").pop()?.toLowerCase() : "";

    // Use extension if available
    if (ext) {
      const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
      if (audioExtensions.includes(ext)) return "audio";
      return ext;
    }

    return (type || "fichier").split("/").pop() || "fichier";
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Upload Modal */}
      <UploadModal
        open={uploadModalOpen}
        onOpenChange={setUploadModalOpen}
        caseId={caseId}
        onUploadComplete={onDocumentsChange}
      />

      {/* Upload Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Ajouter des documents
            </CardTitle>
            <CardDescription>
              Glissez-déposez vos fichiers ou cliquez pour les sélectionner
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => setUploadModalOpen(true)}>
            <Mic className="h-4 w-4 mr-2" />
            Enregistrer un audio
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUpload
            files={files}
            onFilesChange={setFiles}
            maxFiles={10}
            maxSize={100 * 1024 * 1024}
            disabled={uploading}
            accept={{
              // PDF
              "application/pdf": [".pdf"],
              // Word
              "application/msword": [".doc"],
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
              // Text
              "text/plain": [".txt"],
              "text/rtf": [".rtf"],
              "text/markdown": [".md"],
              // Images
              "image/*": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif"],
              // Audio
              "audio/*": [".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac", ".webm"],
              "video/mp4": [".mp4"],
              "video/webm": [".webm"],
            }}
          />
          {files.length > 0 && (
            <div className="flex justify-end">
              <Button onClick={handleUpload} disabled={uploading}>
                {uploading ? "Téléversement..." : `Téléverser ${files.length} fichier(s)`}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Documents ({documents.length})
          </CardTitle>
          <CardDescription>
            Liste des documents attachés à ce dossier
          </CardDescription>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
              <p>Aucun document pour le moment</p>
              <p className="text-sm">Utilisez la zone ci-dessus pour ajouter des fichiers</p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => {
                const Icon = getFileIcon(doc.type_fichier, doc.nom_fichier);
                const typeLabel = getFileTypeLabel(doc.type_fichier, doc.nom_fichier);
                return (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                  >
                    {/* Uniform icon style for all file types */}
                    <div className="p-2 rounded-lg bg-muted">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{doc.nom_fichier}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatFileSize(doc.taille)}</span>
                        <span>•</span>
                        <span>{new Date(doc.uploaded_at).toLocaleDateString("fr-CA")}</span>
                      </div>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-xs">
                      {typeLabel.toUpperCase()}
                    </Badge>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        title="Prévisualiser"
                        onClick={() => handlePreview(doc)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        title="Télécharger"
                        onClick={() => handleDownload(doc)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            title="Supprimer"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Supprimer ce document ?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Le document "{doc.nom_fichier}" sera supprimé définitivement.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Annuler</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(doc.id)}
                              disabled={deletingId === doc.id}
                            >
                              {deletingId === doc.id ? "Suppression..." : "Supprimer"}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
