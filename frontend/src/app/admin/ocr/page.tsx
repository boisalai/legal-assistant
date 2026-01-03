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
  const [ocrEngine, setOcrEngine] = useState<"docling" | "paddleocr_vl">("docling");
  const [extractImages, setExtractImages] = useState(false);
  const [postProcessLLM, setPostProcessLLM] = useState(false);

  // Processing state
  const [status, setStatus] = useState<ProcessingStatus>("idle");
  const [progress, setProgress] = useState<OCRProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultFilename, setResultFilename] = useState<string | null>(null);
  const [processingDuration, setProcessingDuration] = useState<number | null>(null);
  const startTimeRef = useRef<number>(0);

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
      "application/pdf": [".pdf"],
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
    startTimeRef.current = Date.now();
    setProcessingDuration(null);

    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    formData.append("start_page", startPage.toString());
    formData.append("ocr_engine", ocrEngine);
    formData.append("extract_images", extractImages.toString());
    formData.append("post_process_with_llm", postProcessLLM.toString());

    try {
      abortControllerRef.current = new AbortController();
      const token = localStorage.getItem("auth_token");

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
                // The message contains the filename on completion (.zip or .md)
                if (event.message && (event.message.endsWith(".zip") || event.message.endsWith(".md"))) {
                  setResultFilename(event.message);
                }
                // Calculate processing duration
                setProcessingDuration(Date.now() - startTimeRef.current);
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
    const token = localStorage.getItem("auth_token");
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
    setOcrEngine("docling");
    setExtractImages(false);
    setPostProcessLLM(false);
    setStatus("idle");
    setProgress(null);
    setError(null);
    setResultFilename(null);
    setProcessingDuration(null);
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
        <div className="px-6 py-4 flex-1 min-h-0 overflow-y-auto">
          <div className="max-w-3xl space-y-6">
          {/* Instructions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Instructions</CardTitle>
              <CardDescription>
                Convertissez un livre scanne (images ou PDF) en document Markdown.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              <ol className="list-decimal list-inside space-y-1">
                <li>
                  Chargez un fichier PDF multi-pages ou un ZIP contenant les images JPG/PNG
                </li>
                <li>
                  Pour les ZIP, nommez les fichiers pour un tri naturel (ex: page_001.jpg,
                  page_002.jpg...)
                </li>
                <li>
                  Choisissez le moteur OCR : Docling VLM est recommande pour
                  Apple Silicon (acceleration MLX)
                </li>
                <li>Le traitement depend du modele et de la complexite des pages</li>
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
                        : "Glissez-deposez un fichier ZIP ou PDF"}
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

                    {/* OCR Engine Selection */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Moteur OCR</Label>
                      <div className="grid gap-2">
                        <label
                          className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                            ocrEngine === "docling"
                              ? "border-primary bg-primary/5"
                              : "border-muted hover:border-primary/50"
                          }`}
                        >
                          <input
                            type="radio"
                            name="ocrEngine"
                            value="docling"
                            checked={ocrEngine === "docling"}
                            onChange={() => {
                              setOcrEngine("docling");
                              setExtractImages(false); // Docling handles images internally
                            }}
                            className="mt-1"
                          />
                          <div>
                            <div className="font-medium text-sm">
                              Docling VLM - Recommande
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Local, acceleration MLX sur Apple Silicon.
                              100% gratuit, pas d&apos;API externe.
                            </p>
                          </div>
                        </label>
                        <label
                          className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                            ocrEngine === "paddleocr_vl"
                              ? "border-primary bg-primary/5"
                              : "border-muted hover:border-primary/50"
                          }`}
                        >
                          <input
                            type="radio"
                            name="ocrEngine"
                            value="paddleocr_vl"
                            checked={ocrEngine === "paddleocr_vl"}
                            onChange={() => setOcrEngine("paddleocr_vl")}
                            className="mt-1"
                          />
                          <div>
                            <div className="font-medium text-sm">
                              PaddleOCR-VL
                            </div>
                            <p className="text-xs text-muted-foreground">
                              ~4 Go RAM.
                              Supporte l&apos;extraction d&apos;images.
                            </p>
                          </div>
                        </label>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {/* Image extraction - only for PaddleOCR-VL */}
                      {ocrEngine === "paddleocr_vl" && (
                        <div className="flex items-start space-x-2">
                          <Checkbox
                            id="extractImages"
                            checked={extractImages}
                            onCheckedChange={(checked) =>
                              setExtractImages(checked as boolean)
                            }
                            className="mt-0.5"
                          />
                          <div>
                            <Label htmlFor="extractImages" className="text-sm">
                              Extraire les images
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              Detecte et extrait les figures/illustrations.
                            </p>
                          </div>
                        </div>
                      )}
                      <div className="flex items-start space-x-2">
                        <Checkbox
                          id="postProcessLLM"
                          checked={postProcessLLM}
                          onCheckedChange={(checked) =>
                            setPostProcessLLM(checked as boolean)
                          }
                          className="mt-0.5"
                        />
                        <div>
                          <Label htmlFor="postProcessLLM" className="text-sm">
                            Correction LLM du texte
                          </Label>
                          <p className="text-xs text-muted-foreground">
                            Corrige les erreurs OCR avec un LLM. Gourmand en ressources.
                          </p>
                        </div>
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
                  <div className="text-sm text-muted-foreground space-y-1">
                    <div>
                      {progress.total_pages} pages traitees,{" "}
                      {progress.images_extracted} images extraites
                    </div>
                    {processingDuration && processingDuration > 0 && (
                      <div>
                        Duree totale : {Math.floor(processingDuration / 60000)}m {Math.floor((processingDuration % 60000) / 1000)}s
                        {progress.total_pages > 0 && (
                          <> — Moyenne : {(processingDuration / 1000 / progress.total_pages).toFixed(1)}s/page</>
                        )}
                      </div>
                    )}
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
      </div>
    </AppShell>
  );
}
