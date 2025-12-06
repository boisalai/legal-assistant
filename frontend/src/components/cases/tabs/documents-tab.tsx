"use client";

import { useState, useCallback, useEffect } from "react";
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
} from "@/components/ui/alert-dialog";
import {
  FileText,
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
  Database,
  Brain,
  Loader2,
  MoreVertical,
  DatabaseBackup,
  Youtube,
  FileDown,
  RefreshCw,
  BookOpen,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from "@/components/ui/dropdown-menu";
import { documentsApi } from "@/lib/api";
import type { Document } from "@/types";
import { YouTubeDownloadModal } from "@/components/cases/youtube-download-modal";
import { ImportDocusaurusModal } from "@/components/cases/import-docusaurus-modal";

interface DocumentsTabProps {
  caseId: string;
  documents: Document[];
  onDocumentsChange: () => void;
  onPreviewDocument?: (docId: string) => void;
}

export function DocumentsTab({ caseId, documents, onDocumentsChange, onPreviewDocument }: DocumentsTabProps) {
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [processingAction, setProcessingAction] = useState<"transcribe" | "extract" | "clear" | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<Document | null>(null);
  const [youtubeModalOpen, setYoutubeModalOpen] = useState(false);
  const [docusaurusModalOpen, setDocusaurusModalOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [derivedCounts, setDerivedCounts] = useState<Record<string, number>>({});

  // Load derived file counts for all documents
  useEffect(() => {
    const loadDerivedCounts = async () => {
      const counts: Record<string, number> = {};
      for (const doc of documents) {
        try {
          const result = await documentsApi.getDerived(caseId, doc.id);
          if (result.total > 0) {
            counts[doc.id] = result.total;
          }
        } catch (err) {
          // Ignore errors, just don't show count
        }
      }
      setDerivedCounts(counts);
    };

    if (documents.length > 0) {
      loadDerivedCounts();
    }
  }, [documents, caseId]);

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

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      const result = await documentsApi.sync(caseId);
      onDocumentsChange();

      if (result.discovered > 0) {
        alert(`Synchronisation réussie: ${result.discovered} fichier(s) découvert(s) et ajouté(s).`);
      } else {
        alert("Synchronisation réussie: Aucun nouveau fichier découvert.");
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de la synchronisation");
    } finally {
      setSyncing(false);
    }
  }, [caseId, onDocumentsChange]);

  const handlePreview = (document: Document) => {
    if (onPreviewDocument) {
      onPreviewDocument(document.id);
    } else {
      // Fallback to open in new tab
      documentsApi.preview(caseId, document.id);
    }
  };

  // Check if file is audio
  const isAudioFile = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return audioExtensions.includes(ext) || doc.type_mime?.includes("audio");
  };

  // Check if file can have text extracted (Word, text files)
  // Note: PDF files should use "Extraire en markdown" instead
  const canExtractText = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const extractableExtensions = ["doc", "docx", "txt", "rtf", "md"];
    return extractableExtensions.includes(ext);
  };

  // Check if file is a PDF
  const isPDFFile = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    return ext === "pdf" || doc.type_mime === "application/pdf";
  };

  // Check if file can be transcribed to markdown (audio files only)
  // Note: PDF and Word files are handled separately
  const canTranscribeToMarkdown = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const transcribableExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return transcribableExtensions.includes(ext) || doc.type_mime?.includes("audio");
  };

  // Handle transcription for audio files
  const handleTranscribe = async (doc: Document) => {
    setProcessingId(doc.id);
    setProcessingAction("transcribe");
    try {
      await documentsApi.transcribeWithWorkflow(caseId, doc.id, {
        language: "fr",
        createMarkdown: true,
      });
      onDocumentsChange();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de la transcription");
    } finally {
      setProcessingId(null);
      setProcessingAction(null);
    }
  };

  // Handle text extraction for documents (Word, text files, etc. - NOT PDF)
  const handleExtractText = async (doc: Document) => {
    setProcessingId(doc.id);
    setProcessingAction("extract");
    try {
      const result = await documentsApi.extract(caseId, doc.id);
      if (result.success) {
        onDocumentsChange();
      } else {
        alert(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de l'extraction");
    } finally {
      setProcessingId(null);
      setProcessingAction(null);
    }
  };

  // Handle PDF extraction to markdown
  const handleExtractPDF = async (doc: Document) => {
    setProcessingId(doc.id);
    setProcessingAction("extract");
    try {
      const result = await documentsApi.extractPDFToMarkdown(caseId, doc.id);
      if (result.success) {
        onDocumentsChange();
        alert("Markdown créé avec succès");
      } else {
        alert(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de l'extraction");
    } finally {
      setProcessingId(null);
      setProcessingAction(null);
    }
  };

  // Handle clearing extracted text
  const handleClearText = async (doc: Document) => {
    setProcessingId(doc.id);
    setProcessingAction("clear");
    try {
      await documentsApi.clearText(caseId, doc.id);
      onDocumentsChange();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors de la suppression du texte");
    } finally {
      setProcessingId(null);
      setProcessingAction(null);
    }
  };

  // Handle document deletion (also clears extracted text from DB if present)
  const handleConfirmDelete = async () => {
    if (docToDelete) {
      setDeletingId(docToDelete.id);
      try {
        // If document has extracted text, clear it first
        if (docToDelete.texte_extrait) {
          try {
            await documentsApi.clearText(caseId, docToDelete.id);
          } catch (err) {
            // Continue with deletion even if clearing text fails
            console.warn("Failed to clear text before deletion:", err);
          }
        }
        await documentsApi.delete(caseId, docToDelete.id);
        onDocumentsChange();
      } catch (err) {
        alert(err instanceof Error ? err.message : "Erreur lors de la suppression");
      } finally {
        setDeletingId(null);
        setDocToDelete(null);
        setDeleteDialogOpen(false);
      }
    }
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

      {/* YouTube Download Modal */}
      <YouTubeDownloadModal
        open={youtubeModalOpen}
        onClose={() => setYoutubeModalOpen(false)}
        caseId={caseId}
        onDownloadComplete={onDocumentsChange}
      />

      {/* Import Docusaurus Modal */}
      <ImportDocusaurusModal
        open={docusaurusModalOpen}
        onOpenChange={setDocusaurusModalOpen}
        caseId={caseId}
        onImportSuccess={onDocumentsChange}
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
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setDocusaurusModalOpen(true)}>
              <BookOpen className="h-4 w-4 mr-2" />
              Docusaurus
            </Button>
            <Button variant="outline" size="sm" onClick={() => setYoutubeModalOpen(true)}>
              <Youtube className="h-4 w-4 mr-2" />
              YouTube
            </Button>
            <Button variant="outline" size="sm" onClick={() => setUploadModalOpen(true)}>
              <Mic className="h-4 w-4 mr-2" />
              Enregistrer
            </Button>
          </div>
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
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="space-y-1.5">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Documents ({documents.length})
            </CardTitle>
            <CardDescription>
              Liste des documents attachés à ce dossier
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={syncing}
            title="Synchroniser - Découvre les fichiers dans le répertoire du dossier"
          >
            {syncing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="ml-2">Synchroniser</span>
          </Button>
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
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm truncate">{doc.nom_fichier}</p>
                        {derivedCounts[doc.id] > 0 && (
                          <Badge variant="secondary" className="text-xs shrink-0">
                            +{derivedCounts[doc.id]}
                          </Badge>
                        )}
                      </div>
                      {doc.file_path && (
                        <p className="text-xs text-muted-foreground/60 truncate" title={doc.file_path}>
                          {doc.file_path}
                        </p>
                      )}
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatFileSize(doc.taille)}</span>
                        <span>•</span>
                        <span>{new Date(doc.uploaded_at).toLocaleDateString("fr-CA")}</span>
                      </div>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-xs">
                      {typeLabel.toUpperCase()}
                    </Badge>
                    {/* Status badges */}
                    {processingId === doc.id && (
                      <Badge variant="secondary" className="shrink-0 text-xs">
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        {processingAction === "extract" ? "Extraction..." : processingAction === "transcribe" ? "Transcription..." : "Suppression..."}
                      </Badge>
                    )}
                    {doc.texte_extrait && processingId !== doc.id && (
                      <Database className="h-4 w-4 text-muted-foreground shrink-0" />
                    )}
                    {/* Dropdown menu */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {/* Preview */}
                        <DropdownMenuItem onClick={() => handlePreview(doc)}>
                          <Eye className="h-4 w-4 mr-2" />
                          Visualiser
                        </DropdownMenuItem>


                        <DropdownMenuSeparator />

                        {/* Transcribe audio to markdown */}
                        {canTranscribeToMarkdown(doc) && !doc.texte_extrait && (
                          <DropdownMenuItem
                            onClick={() => handleTranscribe(doc)}
                            disabled={processingId === doc.id}
                          >
                            <FileDown className="h-4 w-4 mr-2" />
                            Transcrire en markdown
                          </DropdownMenuItem>
                        )}

                        {/* Extract PDF to markdown */}
                        {isPDFFile(doc) && (
                          <DropdownMenuItem
                            onClick={() => handleExtractPDF(doc)}
                            disabled={processingId === doc.id}
                          >
                            <FileText className="h-4 w-4 mr-2" />
                            Extraire en markdown
                          </DropdownMenuItem>
                        )}

                        {/* Extract text to database (Word, text files - NOT PDF) */}
                        {canExtractText(doc) && !doc.texte_extrait && (
                          <DropdownMenuItem
                            onClick={() => handleExtractText(doc)}
                            disabled={processingId === doc.id}
                          >
                            <Database className="h-4 w-4 mr-2" />
                            Charger dans la base de données
                          </DropdownMenuItem>
                        )}

                        {/* Clear text from DB */}
                        {doc.texte_extrait && (
                          <DropdownMenuItem
                            onClick={() => handleClearText(doc)}
                            disabled={processingId === doc.id}
                            className="text-orange-600"
                          >
                            <DatabaseBackup className="h-4 w-4 mr-2" />
                            Retirer de la base de données
                          </DropdownMenuItem>
                        )}

                        <DropdownMenuSeparator />

                        {/* Delete document */}
                        <DropdownMenuItem
                          onClick={() => {
                            setDocToDelete(doc);
                            setDeleteDialogOpen(true);
                          }}
                          className="text-destructive"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Retirer du dossier
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* AlertDialog for document deletion */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Retirer ce document ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le document « {docToDelete?.nom_fichier} » sera retiré de ce dossier.
              Le fichier original ne sera pas supprimé de votre disque.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDocToDelete(null)}>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deletingId === docToDelete?.id}
            >
              {deletingId === docToDelete?.id ? "Retrait..." : "Retirer"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
