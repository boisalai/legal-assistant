"use client";

import { useState, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileUpload } from "@/components/ui/file-upload";
import { AudioRecorder } from "@/components/ui/audio-recorder";
import { Upload, Mic } from "lucide-react";
import { documentsApi } from "@/lib/api";

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId: string;
  onUploadComplete: () => void;
}

const DOCUMENT_TYPES = [
  { value: "piece_identite", label: "Pièce d'identité" },
  { value: "titre_propriete", label: "Titre de propriété" },
  { value: "certificat_localisation", label: "Certificat de localisation" },
  { value: "evaluation_municipale", label: "Évaluation municipale" },
  { value: "offre_achat", label: "Offre d'achat" },
  { value: "rapport_inspection", label: "Rapport d'inspection" },
  { value: "document_bancaire", label: "Document bancaire" },
  { value: "contrat", label: "Contrat" },
  { value: "correspondance", label: "Correspondance" },
  { value: "autre", label: "Autre" },
];

export function UploadModal({
  open,
  onOpenChange,
  caseId,
  onUploadComplete,
}: UploadModalProps) {
  const [activeTab, setActiveTab] = useState("upload");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [useOcr, setUseOcr] = useState(false);
  const [documentType, setDocumentType] = useState<string>("");
  const [language, setLanguage] = useState("fr");

  const handleFileUpload = useCallback(async () => {
    if (files.length === 0) return;

    setUploading(true);
    try {
      for (const file of files) {
        // Create FormData for each file
        const formData = new FormData();
        formData.append("file", file);
        formData.append("use_ocr", useOcr.toString());
        if (documentType) {
          formData.append("document_type", documentType);
        }
        formData.append("language", language);

        // Upload the file
        await documentsApi.upload(caseId, file);
      }

      // Reset state and close modal
      setFiles([]);
      setUseOcr(false);
      setDocumentType("");
      onOpenChange(false);
      onUploadComplete();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erreur lors du téléversement");
    } finally {
      setUploading(false);
    }
  }, [caseId, files, useOcr, documentType, language, onOpenChange, onUploadComplete]);

  const handleAudioRecordingComplete = useCallback(
    async (blob: Blob, name: string, audioLanguage: string, identifySpeakers: boolean) => {
      setUploading(true);
      try {
        // Create FormData for audio
        const formData = new FormData();
        formData.append("file", blob, `${name}.webm`);
        formData.append("name", name);
        formData.append("language", audioLanguage);
        formData.append("identify_speakers", identifySpeakers.toString());

        // Upload audio recording via dedicated endpoint
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/dossiers/${caseId}/audio`,
          {
            method: "POST",
            body: formData,
          }
        );

        if (!response.ok) {
          throw new Error("Erreur lors de la sauvegarde de l'enregistrement");
        }

        onOpenChange(false);
        onUploadComplete();
      } catch (err) {
        alert(err instanceof Error ? err.message : "Erreur lors de la sauvegarde");
      } finally {
        setUploading(false);
      }
    },
    [caseId, onOpenChange, onUploadComplete]
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Ajouter des documents</DialogTitle>
          <DialogDescription>
            Téléversez des fichiers ou enregistrez un audio
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Téléverser des fichiers
            </TabsTrigger>
            <TabsTrigger value="record" className="flex items-center gap-2">
              <Mic className="h-4 w-4" />
              Enregistrement audio
            </TabsTrigger>
          </TabsList>

          {/* Tab 1: File Upload */}
          <TabsContent value="upload" className="mt-6 space-y-6">
            {/* Drop zone */}
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

            {/* Options */}
            {files.length > 0 && (
              <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                {/* OCR checkbox */}
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="use-ocr"
                    checked={useOcr}
                    onCheckedChange={(checked) => setUseOcr(checked === true)}
                  />
                  <div>
                    <Label htmlFor="use-ocr" className="text-sm font-medium">
                      Document scanné (exécuter l&apos;OCR)
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      L&apos;OCR est plus lent. Utilisez uniquement si nécessaire.
                    </p>
                  </div>
                </div>

                {/* Document type */}
                <div className="space-y-2">
                  <Label htmlFor="document-type">Type de document</Label>
                  <Select value={documentType} onValueChange={setDocumentType}>
                    <SelectTrigger id="document-type">
                      <SelectValue placeholder="Sélectionner un type (optionnel)" />
                    </SelectTrigger>
                    <SelectContent>
                      {DOCUMENT_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Language for audio files */}
                {files.some((f) =>
                  [".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac", ".webm", ".mp4"].some(
                    (ext) => f.name.toLowerCase().endsWith(ext)
                  )
                ) && (
                  <div className="space-y-2">
                    <Label htmlFor="audio-language">Langue de l&apos;audio</Label>
                    <Select value={language} onValueChange={setLanguage}>
                      <SelectTrigger id="audio-language">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fr">Français</SelectItem>
                        <SelectItem value="en">Anglais</SelectItem>
                        <SelectItem value="fr-en">Bilingue (français/anglais)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            )}

            {/* Upload button */}
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Annuler
              </Button>
              <Button
                onClick={handleFileUpload}
                disabled={files.length === 0 || uploading}
              >
                {uploading
                  ? "Téléversement..."
                  : `Téléverser ${files.length} fichier(s)`}
              </Button>
            </div>
          </TabsContent>

          {/* Tab 2: Audio Recording */}
          <TabsContent value="record" className="mt-6">
            <AudioRecorder
              onRecordingComplete={handleAudioRecordingComplete}
              disabled={uploading}
            />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
