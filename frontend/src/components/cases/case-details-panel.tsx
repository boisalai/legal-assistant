"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
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
  Play,
  Download,
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
} from "lucide-react";
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

// Status configuration
const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  nouveau: { label: "Nouveau", variant: "default" },
  en_analyse: { label: "En analyse", variant: "secondary" },
  termine: { label: "Terminé", variant: "outline" },
  en_erreur: { label: "En erreur", variant: "destructive" },
  archive: { label: "Archivé", variant: "secondary" },
};

// Transaction type labels
const typeLabels: Record<string, string> = {
  vente: "Vente",
  achat: "Achat",
  hypotheque: "Hypothèque",
  testament: "Testament",
  succession: "Succession",
  autre: "Autre",
};

interface CaseDetailsPanelProps {
  caseData: Case;
  documents: Document[];
  checklist: Checklist | null;
  onUploadDocuments: () => void;
  onRecordAudio: () => void;
  onAnalyze: () => void;
  onUpdateSummary: (summary: string) => Promise<void>;
  onDeleteDocument: (docId: string) => Promise<void>;
  onDownloadDocument: (docId: string) => void;
  onPreviewDocument: (docId: string) => void;
  onDelete: () => void;
  deleting: boolean;
  isAnalyzing: boolean;
}

export function CaseDetailsPanel({
  caseData,
  documents,
  checklist,
  onUploadDocuments,
  onRecordAudio,
  onAnalyze,
  onUpdateSummary,
  onDeleteDocument,
  onDownloadDocument,
  onPreviewDocument,
  onDelete,
  deleting,
  isAnalyzing,
}: CaseDetailsPanelProps) {
  const [isEditingSummary, setIsEditingSummary] = useState(false);
  const [summaryValue, setSummaryValue] = useState(
    caseData.summary || "Cliquez pour ajouter un résumé du dossier"
  );
  const [isSavingSummary, setIsSavingSummary] = useState(false);

  const handleSaveSummary = async () => {
    setIsSavingSummary(true);
    try {
      await onUpdateSummary(summaryValue);
      setIsEditingSummary(false);
    } finally {
      setIsSavingSummary(false);
    }
  };

  const handleCancelEdit = () => {
    setSummaryValue(caseData.summary || "Cliquez pour ajouter un résumé du dossier");
    setIsEditingSummary(false);
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

  const statusInfo = statusConfig[caseData.statut] || statusConfig.nouveau;

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4 space-y-4">
      {/* Case Header */}
      <div className="pb-4 border-b">
        <h2 className="text-xl font-bold">{caseData.nom_dossier}</h2>
        <div className="flex items-center gap-4 mt-1">
          <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          <span className="text-sm text-muted-foreground">
            {typeLabels[caseData.type_transaction]}
          </span>
          <span className="text-sm text-muted-foreground">
            {new Date(caseData.created_at).toLocaleDateString("fr-CA")}
          </span>
        </div>
      </div>

      {/* Résumé éditable */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">Résumé :</span>
          {!isEditingSummary && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => setIsEditingSummary(true)}
            >
              <Edit2 className="h-3 w-3" />
            </Button>
          )}
        </div>
        {isEditingSummary ? (
          <div className="space-y-2">
            <Input
              value={summaryValue}
              onChange={(e) => setSummaryValue(e.target.value)}
              placeholder="Entrez un résumé du dossier"
              maxLength={200}
              disabled={isSavingSummary}
              className="text-sm"
            />
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleSaveSummary}
                disabled={isSavingSummary}
              >
                {isSavingSummary ? (
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
                disabled={isSavingSummary}
              >
                <X className="h-4 w-4" />
                Annuler
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {summaryValue}
          </p>
        )}
      </div>

      {/* Boutons d'action */}
      <div className="flex items-center gap-2">
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
          onClick={onRecordAudio}
          className="gap-2"
        >
          <Mic className="h-4 w-4" />
          <span>Enregistrer un audio</span>
        </Button>
        <Button
          onClick={onAnalyze}
          disabled={isAnalyzing || documents.length === 0}
          size="sm"
          className="gap-2 ml-auto"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyse en cours...
            </>
          ) : (
            <>
              <FileText className="h-4 w-4" />
              Analyser
            </>
          )}
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
              <div key={doc.id} className="flex items-start gap-3 p-3 border rounded-md hover:bg-muted/50 transition-colors">
                {getFileIcon(doc.type_mime || doc.type_fichier)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">
                    {doc.nom_fichier}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(doc.taille)} • {doc.type_fichier.toUpperCase()}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => onPreviewDocument(doc.id)}
                    title="Voir"
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => onDownloadDocument(doc.id)}
                    title="Télécharger"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                    onClick={() => onDeleteDocument(doc.id)}
                    title="Supprimer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
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

      {/* Delete Button */}
      <div className="pt-4 border-t mt-auto flex justify-end">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" disabled={deleting}>
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
    </div>
  );
}
