"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  FileText,
  Upload,
  Download,
  Loader2,
  CheckCircle,
  AlertCircle,
  File,
  X,
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
};

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".pptx"];

export default function MarkdownConverterPage() {
  const t = useTranslations("tools.markdownConverter");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [converting, setConverting] = useState(false);
  const [result, setResult] = useState<{ markdown: string; filename: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = useCallback((file: File) => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setError(t("error") + `: ${t("supportedFormats")}`);
      return;
    }
    setSelectedFile(file);
    setResult(null);
    setError(null);
  }, [t]);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  const handleConvert = async () => {
    if (!selectedFile) return;

    setConverting(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

      const response = await fetch(`${API_BASE_URL}/api/tools/convert-to-markdown`, {
        method: "POST",
        body: formData,
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Conversion failed" }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setResult({
          markdown: data.markdown,
          filename: data.filename,
        });
      } else {
        throw new Error(data.error || t("error"));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setConverting(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;

    // Create blob and download
    const blob = new Blob([result.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = result.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const clearFile = () => {
    setSelectedFile(null);
    setResult(null);
    setError(null);
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    return <File className="h-8 w-8 text-muted-foreground" />;
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-3xl">
        {/* Page Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">{t("title")}</h1>
            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Success Alert */}
        {result && (
          <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-600">
              {t("success")}
            </AlertDescription>
          </Alert>
        )}

        {/* Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Upload className="h-4 w-4" />
              {t("selectFile")}
            </CardTitle>
            <CardDescription>{t("supportedFormats")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Dropzone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50"
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.pptx"
                className="hidden"
                onChange={handleFileInputChange}
              />
              {selectedFile ? (
                <div className="flex items-center justify-center gap-4">
                  {getFileIcon(selectedFile.name)}
                  <div className="text-left">
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      clearFile();
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="h-10 w-10 mx-auto text-muted-foreground" />
                  <p className="text-muted-foreground">{t("dropzone")}</p>
                  <p className="text-xs text-muted-foreground">{t("supportedFormats")}</p>
                </div>
              )}
            </div>

            {/* Convert Button */}
            <Button
              onClick={handleConvert}
              disabled={!selectedFile || converting}
              className="w-full"
            >
              {converting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t("converting")}
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4 mr-2" />
                  {t("convert")}
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Result Card */}
        {result && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <FileText className="h-4 w-4" />
                {t("preview")}
              </CardTitle>
              <CardDescription>{result.filename}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Preview */}
              <div className="bg-muted rounded-lg p-4 max-h-80 overflow-y-auto">
                <pre className="text-sm whitespace-pre-wrap font-mono">
                  {result.markdown.length > 5000
                    ? result.markdown.substring(0, 5000) + "\n\n... [truncated]"
                    : result.markdown}
                </pre>
              </div>

              {/* Download Button */}
              <Button onClick={handleDownload} className="w-full">
                <Download className="h-4 w-4 mr-2" />
                {t("download")}
              </Button>

              <p className="text-xs text-center text-muted-foreground">
                {t("downloadPath")}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
