"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import {
  BookOpen,
  Upload,
  FileUp,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Download,
  Settings2,
  RotateCcw,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AppShell } from "@/components/layout/app-shell";
import { authApi } from "@/lib/api";

interface OCRProgressEvent {
  status: string;
  current_page: number;
  total_pages: number;
  images_extracted: number;
  message: string;
  percentage: number;
}

type ProcessingStatus = "idle" | "uploading" | "processing" | "completed" | "error";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminOCRPage() {
  const router = useRouter();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auth state
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  // Form state
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [startPage, setStartPage] = useState(1);
  const [extractImages, setExtractImages] = useState(true);
  const [postProcessLLM, setPostProcessLLM] = useState(true);

  // Processing state
  const [status, setStatus] = useState<ProcessingStatus>("idle");
  const [progress, setProgress] = useState<OCRProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultFilename, setResultFilename] = useState<string | null>(null);

  // Check auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (!authApi.isAuthenticated()) {
        router.push("/login");
        return;
      }
      try {
        const user = await authApi.getCurrentUser();
        if (user.role !== "admin") {
          router.push("/dashboard");
          return;
        }
        setIsAuthorized(true);
      } catch {
        router.push("/login");
      }
    };
    checkAuth();
  }, [router]);

  // Dropzone
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/zip": [".zip"],
    },
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024, // 500 MB
  });

  // Start processing
  const handleProcess = async () => {
    if (!file) return;

    setStatus("uploading");
    setError(null);
    setResultFilename(null);
    setProgress(null);

    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    formData.append("start_page", startPage.toString());
    formData.append("extract_images", extractImages.toString());
    formData.append("post_process_with_llm", postProcessLLM.toString());

    try {
      abortControllerRef.current = new AbortController();
      const token = localStorage.getItem("authToken");

      const response = await fetch(`${API_BASE_URL}/api/admin/ocr/process`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Erreur" }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      setStatus("processing");

      // Read SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event: OCRProgressEvent = JSON.parse(line.slice(6));
              setProgress(event);

              if (event.status === "completed") {
                // The message contains the filename on completion
                if (event.message && event.message.endsWith(".zip")) {
                  setResultFilename(event.message);
                }
                setStatus("completed");
              } else if (event.status === "error") {
                setError(event.message);
                setStatus("error");
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err: unknown) {
      const error = err as Error;
      if (error.name === "AbortError") {
        setError("Traitement annule");
      } else {
        setError(error.message || "Erreur de traitement");
      }
      setStatus("error");
    }
  };

  // Cancel processing
  const handleCancel = () => {
    abortControllerRef.current?.abort();
    setStatus("idle");
  };

  // Download result
  const handleDownload = () => {
    if (!resultFilename) return;
    const token = localStorage.getItem("authToken");
    const url = `${API_BASE_URL}/api/admin/ocr/download/${encodeURIComponent(resultFilename)}`;

    // For authenticated download, we need to use fetch and create a blob
    fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((response) => response.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = resultFilename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
      })
      .catch((err) => {
        console.error("Download error:", err);
        setError("Erreur lors du telechargement");
      });
  };

  // Reset form
  const handleReset = () => {
    setFile(null);
    setTitle("");
    setStartPage(1);
    setStatus("idle");
    setProgress(null);
    setError(null);
    setResultFilename(null);
  };

  if (isAuthorized === null) {
    return (
      <AppShell noPadding>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell noPadding>
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            OCR de livres
          </h2>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6 flex-1 min-h-0 overflow-y-auto">
          {/* Instructions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Instructions</CardTitle>
              <CardDescription>
                Convertissez un livre scanne (images) en document Markdown avec
                extraction d&apos;images.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              <ol className="list-decimal list-inside space-y-1">
                <li>
                  Preparez un fichier ZIP contenant les images JPG des pages
                  (une image par page)
                </li>
                <li>
                  Nommez les fichiers pour un tri naturel (ex: page_001.jpg,
                  page_002.jpg...)
                </li>
                <li>Uploadez le ZIP et configurez les options ci-dessous</li>
                <li>Le traitement prend environ 5 secondes par page</li>
              </ol>
            </CardContent>
          </Card>

          {/* Upload Zone */}
          {status === "idle" && (
            <>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : file
                      ? "border-green-500 bg-green-50 dark:bg-green-950"
                      : "border-muted-foreground/25 hover:border-primary/50"
                }`}
              >
                <input {...getInputProps()} />
                {file ? (
                  <div className="space-y-2">
                    <CheckCircle2 className="h-12 w-12 mx-auto text-green-600" />
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                    >
                      Changer de fichier
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <FileUp className="h-12 w-12 mx-auto text-muted-foreground" />
                    <p className="font-medium">
                      {isDragActive
                        ? "Deposez le fichier ici..."
                        : "Glissez-deposez un fichier ZIP"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      ou cliquez pour parcourir (max 500 MB)
                    </p>
                  </div>
                )}
              </div>

              {/* Options */}
              {file && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Settings2 className="h-4 w-4" />
                      Options
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="title">Titre du livre (optionnel)</Label>
                        <Input
                          id="title"
                          value={title}
                          onChange={(e) => setTitle(e.target.value)}
                          placeholder="Ex: Droit civil - Tome 1"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="startPage">Page de depart</Label>
                        <Input
                          id="startPage"
                          type="number"
                          min={1}
                          value={startPage}
                          onChange={(e) =>
                            setStartPage(parseInt(e.target.value) || 1)
                          }
                        />
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="extractImages"
                          checked={extractImages}
                          onCheckedChange={(checked) =>
                            setExtractImages(checked as boolean)
                          }
                        />
                        <Label htmlFor="extractImages" className="text-sm">
                          Extraire les images
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="postProcessLLM"
                          checked={postProcessLLM}
                          onCheckedChange={(checked) =>
                            setPostProcessLLM(checked as boolean)
                          }
                        />
                        <Label htmlFor="postProcessLLM" className="text-sm">
                          Post-traitement LLM (correction OCR)
                        </Label>
                      </div>
                    </div>

                    <Button onClick={handleProcess} className="w-full">
                      <Upload className="h-4 w-4 mr-2" />
                      Demarrer le traitement
                    </Button>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* Processing Status */}
          {(status === "uploading" || status === "processing") && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Traitement en cours...
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Progress value={progress?.percentage || 0} className="h-2" />
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>{progress?.message || "Initialisation..."}</span>
                  <span>{progress?.percentage || 0}%</span>
                </div>
                {progress && progress.total_pages > 0 && (
                  <div className="text-sm">
                    Page {progress.current_page} / {progress.total_pages}
                    {progress.images_extracted > 0 && (
                      <span className="ml-4">
                        {progress.images_extracted} image(s) extraite(s)
                      </span>
                    )}
                  </div>
                )}
                <Button variant="outline" onClick={handleCancel}>
                  Annuler
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Completed */}
          {status === "completed" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="h-5 w-5" />
                  Traitement termine!
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {progress && (
                  <div className="text-sm text-muted-foreground">
                    {progress.total_pages} pages traitees,{" "}
                    {progress.images_extracted} images extraites
                  </div>
                )}
                <div className="flex gap-2">
                  <Button onClick={handleDownload}>
                    <Download className="h-4 w-4 mr-2" />
                    Telecharger le resultat
                  </Button>
                  <Button variant="outline" onClick={handleReset}>
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Nouveau traitement
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error */}
          {status === "error" && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  Erreur
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm">{error}</p>
                <Button variant="outline" onClick={handleReset}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Recommencer
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
