"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Scale, Upload, FileText, Loader2, ArrowLeft } from "lucide-react";
import { createJudgment, summarizeJudgment } from "@/lib/api";

export default function NewJudgmentPage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setText(reader.result as string);
        setTitle(file.name.replace(/\.[^/.]+$/, ""));
      };
      reader.readAsText(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/plain": [".txt"],
    },
    maxFiles: 1,
  });

  const handleSubmit = async () => {
    if (!text.trim()) {
      setError("Veuillez entrer le texte du jugement");
      return;
    }

    setLoading(true);
    setError(null);
    setProgress(0);

    try {
      setStatus("Creation du jugement...");
      setProgress(25);
      const judgment = await createJudgment(text, title || undefined);

      setStatus("Analyse en cours...");
      setProgress(50);

      setStatus("Generation du resume...");
      setProgress(75);
      await summarizeJudgment(judgment.id);

      setProgress(100);
      setStatus("Termine!");

      router.push(`/judgments/${judgment.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'analyse");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold flex items-center gap-2">
            <Scale className="h-5 w-5" />
            Legal Assistant
          </Link>
          <nav className="flex items-center gap-2">
            <Link href="/judgments">
              <Button variant="ghost" size="sm">
                Jugements
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 container mx-auto px-4 py-8 max-w-3xl">
        <div className="mb-6">
          <Link href="/judgments" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-4">
            <ArrowLeft className="h-4 w-4" />
            Retour aux jugements
          </Link>
          <h1 className="text-2xl font-semibold">Nouveau jugement</h1>
          <p className="text-muted-foreground">
            Ajoutez un jugement pour generer un case brief automatique
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Texte du jugement</CardTitle>
            <CardDescription>
              Collez le texte ou telechargez un fichier
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <Tabs defaultValue="paste">
              <TabsList>
                <TabsTrigger value="paste">Coller le texte</TabsTrigger>
                <TabsTrigger value="upload">Telecharger un fichier</TabsTrigger>
              </TabsList>

              <TabsContent value="paste" className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Titre (optionnel)</Label>
                  <input
                    id="title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Ex: R. c. Smith, 2024 CSC 12"
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="text">Texte du jugement</Label>
                  <Textarea
                    id="text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Collez ici le texte integral du jugement..."
                    className="min-h-[300px] font-mono text-sm"
                  />
                </div>
              </TabsContent>

              <TabsContent value="upload">
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
                    isDragActive
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-primary/50"
                  }`}
                >
                  <input {...getInputProps()} />
                  <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                  {isDragActive ? (
                    <p>Deposez le fichier ici...</p>
                  ) : (
                    <>
                      <p className="mb-2">
                        Glissez-deposez un fichier texte ici
                      </p>
                      <p className="text-sm text-muted-foreground">
                        ou cliquez pour selectionner un fichier (.txt)
                      </p>
                    </>
                  )}
                </div>
                {text && (
                  <div className="mt-4 p-4 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 text-sm">
                      <FileText className="h-4 w-4" />
                      <span className="font-medium">{title || "Fichier charge"}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {text.length} caracteres
                    </p>
                  </div>
                )}
              </TabsContent>
            </Tabs>

            {loading && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{status}</span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} />
              </div>
            )}

            {error && (
              <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-3">
              <Link href="/judgments">
                <Button variant="outline" disabled={loading}>
                  Annuler
                </Button>
              </Link>
              <Button onClick={handleSubmit} disabled={loading || !text.trim()}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyse en cours...
                  </>
                ) : (
                  <>
                    <Scale className="h-4 w-4 mr-2" />
                    Analyser le jugement
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Footer */}
      <footer className="border-t py-4">
        <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
          Legal Assistant - Assistant d'etudes juridiques
        </div>
      </footer>
    </div>
  );
}
