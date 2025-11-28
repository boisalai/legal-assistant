"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileUpload } from "@/components/ui/file-upload";
import { AdvancedSettings, type AnalysisSettings } from "@/components/AdvancedSettings";
import { ArrowLeft, FolderPlus } from "lucide-react";
import { casesApi, documentsApi, analysisApi } from "@/lib/api";

export default function NewCasePage() {
  const router = useRouter();
  const [nomDossier, setNomDossier] = useState("");
  const [typeTransaction, setTypeTransaction] = useState("vente");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisSettings, setAnalysisSettings] = useState<AnalysisSettings>({
    model_id: "ollama:qwen2.5:7b",
    extraction_method: "pypdf",
    use_ocr: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setUploading(true);

    try {
      // Create case
      const newCase = await casesApi.create({
        nom_dossier: nomDossier,
        type_transaction: typeTransaction,
        user_id: "user:test_notaire",
      });

      // Upload files
      for (const file of files) {
        await documentsApi.upload(newCase.id, file);
      }

      setUploading(false);
      setAnalyzing(true);

      // Start analysis (fire and forget)
      analysisApi.startStream(newCase.id).catch(console.error);

      // Strip "dossier:" prefix for URL
      const urlId = newCase.id.replace("dossier:", "");
      router.push(`/cases/${urlId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
      setUploading(false);
      setAnalyzing(false);
    }
  };

  const isValid = nomDossier.trim() !== "" && files.length > 0;

  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold">Notary Assistant</Link>
          <Link href="/dashboard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Retour
            </Button>
          </Link>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 container mx-auto px-4 py-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-primary/10">
            <FolderPlus className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Nouveau dossier</h1>
            <p className="text-sm text-muted-foreground">Créez un dossier et téléversez vos documents</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Info Card */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Informations du dossier</CardTitle>
              <CardDescription>Donnez un nom et selectionnez le type de transaction</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="nom-dossier">Nom du dossier</Label>
                <Input
                  id="nom-dossier"
                  required
                  placeholder="Ex: Vente 123 Rue Exemple"
                  value={nomDossier}
                  onChange={(e) => setNomDossier(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="type-transaction">Type de transaction</Label>
                <Select value={typeTransaction} onValueChange={setTypeTransaction}>
                  <SelectTrigger id="type-transaction">
                    <SelectValue placeholder="Selectionner un type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vente">Vente</SelectItem>
                    <SelectItem value="achat">Achat</SelectItem>
                    <SelectItem value="hypotheque">Hypotheque</SelectItem>
                    <SelectItem value="testament">Testament</SelectItem>
                    <SelectItem value="succession">Succession</SelectItem>
                    <SelectItem value="autre">Autre</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Files Card */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Documents PDF</CardTitle>
              <CardDescription>Téléversez les documents à analyser</CardDescription>
            </CardHeader>
            <CardContent>
              <FileUpload
                files={files}
                onFilesChange={setFiles}
                maxFiles={10}
                maxSize={10 * 1024 * 1024}
                disabled={uploading || analyzing}
              />
            </CardContent>
          </Card>

          {/* Advanced Settings */}
          <AdvancedSettings
            initialSettings={analysisSettings}
            onSettingsChange={setAnalysisSettings}
          />

          {/* Error */}
          {error && (
            <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Link href="/dashboard" className="flex-1">
              <Button type="button" variant="outline" className="w-full">
                Annuler
              </Button>
            </Link>
            <Button type="submit" className="flex-1" disabled={!isValid || uploading || analyzing}>
              {uploading ? "Téléversement..." : analyzing ? <span className="text-base">Analyse en cours...</span> : "Créer et analyser"}
            </Button>
          </div>
        </form>
      </main>
    </div>
  );
}
