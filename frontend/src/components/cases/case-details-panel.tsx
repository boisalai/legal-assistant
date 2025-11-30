"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  FileUp,
  Mic,
  Trash2,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Edit2,
  Check,
  X,
  FileText,
  Music,
  Loader2,
  Link2,
  Brain,
  Database,
  MoreVertical,
  DatabaseBackup,
} from "lucide-react";
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
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { Case, Document, Checklist } from "@/types";
import { AnalysisProgressIndicator } from "./analysis-progress-indicator";
import { documentsApi } from "@/lib/api";
import { toast } from "sonner";

// Status configuration
const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  nouveau: { label: "Nouveau", variant: "default" },
  pending: { label: "Nouveau", variant: "default" },
  en_analyse: { label: "En analyse", variant: "secondary" },
  analyzing: { label: "En analyse", variant: "secondary" },
  termine: { label: "Terminé", variant: "outline" },
  summarized: { label: "Terminé", variant: "outline" },
  en_erreur: { label: "En erreur", variant: "destructive" },
  error: { label: "En erreur", variant: "destructive" },
  archive: { label: "Archivé", variant: "secondary" },
  archived: { label: "Archivé", variant: "secondary" },
};

// Transaction type labels
const typeLabels: Record<string, string> = {
  vente: "Vente",
  achat: "Achat",
  hypotheque: "Hypothèque",
  testament: "Testament",
  succession: "Succession",
  autre: "Autre",
  civil: "Civil",
  criminal: "Pénal",
  administrative: "Administratif",
  family: "Familial",
  commercial: "Commercial",
  labor: "Travail",
  constitutional: "Constitutionnel",
  juridique: "Juridique",
  other: "Autre",
};

// Type options for the select
const typeOptions = [
  { value: "civil", label: "Civil" },
  { value: "criminal", label: "Pénal" },
  { value: "administrative", label: "Administratif" },
  { value: "family", label: "Familial" },
  { value: "commercial", label: "Commercial" },
  { value: "labor", label: "Travail" },
  { value: "constitutional", label: "Constitutionnel" },
  { value: "other", label: "Autre" },
];

interface CaseDetailsPanelProps {
  caseData: Case;
  documents: Document[];
  checklist: Checklist | null;
  onUploadDocuments: () => void;
  onRecordAudio: () => void;
  onLinkFile: () => void;
  onAnalyze: () => void;
  onUpdateCase: (data: { description?: string; type_transaction?: string }) => Promise<void>;
  onDeleteDocument: (docId: string) => Promise<void>;
  onPreviewDocument: (docId: string) => void;
  onDelete: () => void;
  onAnalysisComplete?: () => void;
  onDocumentsChange?: () => Promise<void>;
  deleting: boolean;
  isAnalyzing: boolean;
}

export function CaseDetailsPanel({
  caseData,
  documents,
  checklist,
  onUploadDocuments,
  onRecordAudio,
  onLinkFile,
  onAnalyze,
  onUpdateCase,
  onDeleteDocument,
  onPreviewDocument,
  onDelete,
  onAnalysisComplete,
  onDocumentsChange,
  deleting,
  isAnalyzing,
}: CaseDetailsPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editDescription, setEditDescription] = useState(caseData.description || "");
  const [editType, setEditType] = useState(caseData.type_transaction || "civil");
  const [isSaving, setIsSaving] = useState(false);
  const [extractingDocId, setExtractingDocId] = useState<string | null>(null);
  const [transcribingDocId, setTranscribingDocId] = useState<string | null>(null);
  const [clearingDocId, setClearingDocId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<Document | null>(null);

  // Check if document is an audio file
  const isAudioFile = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const audioExtensions = ["mp3", "mp4", "m4a", "wav", "webm", "ogg", "opus", "flac", "aac"];
    return audioExtensions.includes(ext) || doc.type_mime?.includes("audio");
  };

  // Check if a document can have text extracted (non-audio without texte_extrait)
  const canExtractText = (doc: Document) => {
    const ext = doc.nom_fichier?.split(".").pop()?.toLowerCase() || "";
    const extractableExtensions = ["pdf", "doc", "docx", "txt", "rtf", "md"];
    return extractableExtensions.includes(ext);
  };

  // Check if a document needs text extraction (non-audio without texte_extrait)
  const needsExtraction = (doc: Document) => {
    return canExtractText(doc) && !doc.texte_extrait;
  };

  const handleExtractText = async (doc: Document) => {
    setExtractingDocId(doc.id);
    try {
      const result = await documentsApi.extract(caseData.id, doc.id);
      if (result.success) {
        toast.success(`Texte extrait avec succes (${result.method})`);
        // Refresh the documents list
        if (onDocumentsChange) {
          await onDocumentsChange();
        }
      } else {
        toast.error(result.error || "Erreur lors de l'extraction");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de l'extraction");
    } finally {
      setExtractingDocId(null);
    }
  };

  // Handle transcription for audio files
  const handleTranscribe = async (doc: Document) => {
    setTranscribingDocId(doc.id);
    try {
      await documentsApi.transcribeWithWorkflow(caseData.id, doc.id, {
        language: "fr",
        createMarkdown: true,
      });
      toast.success("Transcription terminée");
      if (onDocumentsChange) {
        await onDocumentsChange();
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la transcription");
    } finally {
      setTranscribingDocId(null);
    }
  };

  // Handle clearing extracted text
  const handleClearText = async (doc: Document) => {
    setClearingDocId(doc.id);
    try {
      await documentsApi.clearText(caseData.id, doc.id);
      toast.success("Texte retiré de la base de données");
      if (onDocumentsChange) {
        await onDocumentsChange();
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la suppression du texte");
    } finally {
      setClearingDocId(null);
    }
  };

  // Handle document deletion (also clears extracted text from DB if present)
  const handleConfirmDelete = async () => {
    if (docToDelete) {
      // If document has extracted text, clear it first
      if (docToDelete.texte_extrait) {
        try {
          await documentsApi.clearText(caseData.id, docToDelete.id);
        } catch (err) {
          // Continue with deletion even if clearing text fails
          console.warn("Failed to clear text before deletion:", err);
        }
      }
      await onDeleteDocument(docToDelete.id);
      setDocToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdateCase({
        description: editDescription,
        type_transaction: editType,
      });
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditDescription(caseData.description || "");
    setEditType(caseData.type_transaction || "civil");
    setIsEditing(false);
  };

  const getFileIcon = (type: string) => {
    if (type.includes("audio")) return <Music className="h-5 w-5 text-purple-500" />;
    return <FileText className="h-5 w-5 text-blue-500" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const statusInfo = statusConfig[caseData.status] || statusConfig.nouveau;

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Case Header */}
      <div className="px-6 py-4 border-b bg-background">
        <div className="flex flex-col">
          <h2 className="text-xl font-bold">{caseData.nom_dossier}</h2>
          <span className="text-xs text-muted-foreground/60">
            Statut : {statusInfo.label}. Date de création : {new Date(caseData.created_at).toLocaleDateString("fr-CA")}
          </span>
        </div>
      </div>

      {/* Contenu principal avec padding */}
      <div className="px-6 py-4 space-y-4 flex-1">
        {/* Mode édition ou affichage */}
        {isEditing ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Description du dossier"
                disabled={isSaving}
                className="text-sm min-h-[80px]"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-type">Type de dossier</Label>
              <Select value={editType} onValueChange={setEditType} disabled={isSaving}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un type" />
                </SelectTrigger>
                <SelectContent>
                  {typeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Enregistrer
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                <X className="h-4 w-4" />
                Annuler
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {caseData.description && (
              <p className="text-sm text-foreground">{caseData.description}</p>
            )}
            <p className="text-sm text-foreground">
              <span className="font-medium">Type :</span> {typeLabels[caseData.type_transaction] || caseData.type_transaction}
            </p>
          </div>
        )}

        {/* Boutons d'action */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            onClick={() => setIsEditing(true)}
            disabled={isEditing}
            className="gap-2"
          >
            <Edit2 className="h-4 w-4" />
            <span>Modifier</span>
          </Button>
          <Button
            size="sm"
            onClick={onUploadDocuments}
            className="gap-2"
          >
            <FileUp className="h-4 w-4" />
            <span>Ajouter des documents</span>
          </Button>
          <Button
            size="sm"
            onClick={onLinkFile}
            className="gap-2"
          >
            <Link2 className="h-4 w-4" />
            <span>Lier un fichier</span>
          </Button>
          <Button
            size="sm"
            onClick={onRecordAudio}
            className="gap-2"
          >
            <Mic className="h-4 w-4" />
            <span>Enregistrer un audio</span>
          </Button>
        </div>

      {/* Liste des documents */}
      <div className="space-y-2">
        <h3 className="font-semibold text-sm">Documents ({documents.length})</h3>
        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">
            Aucun document. Ajoutez-en un pour commencer.
          </p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center gap-3 p-3 border rounded-md hover:bg-muted/50 transition-colors">
                {getFileIcon(doc.type_mime || doc.type_fichier)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">
                    {doc.nom_fichier}
                  </p>
                  <p className="text-xs text-muted-foreground/60 truncate" title={doc.file_path}>
                    {formatFileSize(doc.taille)}{doc.file_path && ` • ${doc.file_path}`}
                  </p>
                </div>
                {/* Status badges */}
                {(extractingDocId === doc.id || transcribingDocId === doc.id || clearingDocId === doc.id) && (
                  <Badge variant="secondary" className="shrink-0 text-xs">
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    {extractingDocId === doc.id ? "Extraction..." : transcribingDocId === doc.id ? "Transcription..." : "Suppression..."}
                  </Badge>
                )}
                {doc.texte_extrait && !(extractingDocId === doc.id || transcribingDocId === doc.id || clearingDocId === doc.id) && (
                  <Database className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                {/* Dropdown menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {/* Preview */}
                    <DropdownMenuItem onClick={() => onPreviewDocument(doc.id)}>
                      <Eye className="h-4 w-4 mr-2" />
                      Visualiser
                    </DropdownMenuItem>

                    <DropdownMenuSeparator />

                    {/* Transcribe audio */}
                    {isAudioFile(doc) && !doc.texte_extrait && (
                      <DropdownMenuItem
                        onClick={() => handleTranscribe(doc)}
                        disabled={transcribingDocId === doc.id}
                      >
                        <Mic className="h-4 w-4 mr-2" />
                        Transcrire en markdown
                      </DropdownMenuItem>
                    )}

                    {/* Extract text */}
                    {needsExtraction(doc) && (
                      <DropdownMenuItem
                        onClick={() => handleExtractText(doc)}
                        disabled={extractingDocId === doc.id}
                      >
                        <Database className="h-4 w-4 mr-2" />
                        Charger dans la base de données
                      </DropdownMenuItem>
                    )}

                    {/* Clear text from DB */}
                    {doc.texte_extrait && (
                      <DropdownMenuItem
                        onClick={() => handleClearText(doc)}
                        disabled={clearingDocId === doc.id}
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
            ))}
          </div>
        )}

        {/* Analysis Progress Indicator */}
        <AnalysisProgressIndicator
          caseId={caseData.id}
          isAnalyzing={isAnalyzing}
          onComplete={onAnalysisComplete}
        />
      </div>

      {/* Score de confiance */}
      {caseData.score_confiance !== null && caseData.score_confiance !== undefined && (
        <div className="space-y-2">
          <h3 className="font-semibold text-sm">Score de confiance</h3>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Niveau de confiance</span>
              <span className="font-semibold">{caseData.score_confiance}%</span>
            </div>
            <Progress
              value={caseData.score_confiance}
              className="h-2"
            />
          </div>
        </div>
      )}

      {/* Points de vérification et d'attention */}
      {checklist && (
        <>
          {/* Points de vérification */}
          {checklist.items && checklist.items.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                Points de vérification
              </h3>
              <ul className="space-y-1.5">
                {checklist.items.slice(0, 5).map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-600 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{item.titre}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Points d'attention */}
          {checklist.points_attention && checklist.points_attention.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                Points d'attention ({checklist.points_attention.length})
              </h3>
              <ul className="space-y-1.5">
                {checklist.points_attention.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      </div>

      {/* Footer avec bouton Supprimer */}
      <div className="p-4 border-t mt-auto flex justify-end items-center">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button disabled={deleting}>
              <Trash2 className="h-4 w-4 mr-2" />
              Supprimer
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
              <AlertDialogDescription>
                Êtes-vous sûr de vouloir supprimer ce dossier ? Cette action
                est irréversible.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction onClick={onDelete}>
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

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
            <AlertDialogAction onClick={handleConfirmDelete}>
              Retirer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
