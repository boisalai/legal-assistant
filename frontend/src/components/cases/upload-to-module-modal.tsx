"use client";

import { useState, useRef } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Upload, File, X, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { modulesApi } from "@/lib/api";
import { formatFileSize } from "@/lib/utils";

interface UploadToModuleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  moduleId: string;
  moduleName: string;
  onSuccess: () => void;
}

interface FileToUpload {
  file: File;
  id: string;
  status: "pending" | "uploading" | "success" | "error";
  error?: string;
}

export function UploadToModuleModal({
  open,
  onOpenChange,
  moduleId,
  moduleName,
  onSuccess,
}: UploadToModuleModalProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");

  const [files, setFiles] = useState<FileToUpload[]>([]);
  const [autoExtractMarkdown, setAutoExtractMarkdown] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (!selectedFiles) return;

    const newFiles: FileToUpload[] = Array.from(selectedFiles).map((file) => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      status: "pending" as const,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const droppedFiles = event.dataTransfer.files;
    if (!droppedFiles) return;

    const newFiles: FileToUpload[] = Array.from(droppedFiles).map((file) => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      status: "pending" as const,
    }));

    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);

    let successCount = 0;
    let errorCount = 0;

    for (let i = 0; i < files.length; i++) {
      const fileItem = files[i];

      // Update status to uploading
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id ? { ...f, status: "uploading" } : f
        )
      );

      try {
        await modulesApi.uploadToModule(
          moduleId,
          fileItem.file,
          autoExtractMarkdown
        );

        // Update status to success
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id ? { ...f, status: "success" } : f
          )
        );
        successCount++;
      } catch (error: any) {
        // Update status to error
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? { ...f, status: "error", error: error.message }
              : f
          )
        );
        errorCount++;
      }

      // Update progress
      setUploadProgress(((i + 1) / files.length) * 100);
    }

    setUploading(false);

    if (successCount > 0) {
      toast.success(t("uploadSuccess", { count: successCount }));
    }
    if (errorCount > 0) {
      toast.error(t("uploadErrors", { count: errorCount }));
    }

    // If all succeeded, close modal
    if (errorCount === 0) {
      setTimeout(() => {
        setFiles([]);
        onSuccess();
      }, 500);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFiles([]);
      onOpenChange(false);
    }
  };

  const pendingFiles = files.filter((f) => f.status === "pending");
  const hasErrors = files.some((f) => f.status === "error");

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("uploadToModuleTitle")}</DialogTitle>
          <DialogDescription>
            {t("uploadToModuleDescription", { name: moduleName })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Drop zone */}
          <div
            className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 transition-colors"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              {t("dropFilesHere")}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              PDF, Word, Markdown, Audio
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.md,.markdown,.mp3,.wav,.m4a"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {files.map((fileItem) => (
                <div
                  key={fileItem.id}
                  className="flex items-center gap-2 p-2 bg-gray-50 rounded"
                >
                  {fileItem.status === "uploading" ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  ) : fileItem.status === "success" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : fileItem.status === "error" ? (
                    <X className="h-4 w-4 text-red-500" />
                  ) : (
                    <File className="h-4 w-4 text-gray-400" />
                  )}
                  <span
                    className="flex-1 text-sm truncate"
                    title={fileItem.file.name}
                  >
                    {fileItem.file.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(fileItem.file.size)}
                  </span>
                  {fileItem.status === "pending" && !uploading && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(fileItem.id);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Progress bar */}
          {uploading && (
            <div className="space-y-1">
              <Progress value={uploadProgress} className="h-2" />
              <p className="text-xs text-muted-foreground text-center">
                {Math.round(uploadProgress)}%
              </p>
            </div>
          )}

          {/* Options */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="auto-extract"
              checked={autoExtractMarkdown}
              onCheckedChange={(checked) =>
                setAutoExtractMarkdown(checked === true)
              }
              disabled={uploading}
            />
            <Label htmlFor="auto-extract" className="text-sm">
              {t("autoExtractMarkdown")}
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={uploading}>
            {tCommon("cancel")}
          </Button>
          <Button
            onClick={handleUpload}
            disabled={pendingFiles.length === 0 || uploading}
            className="gap-1"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t("uploading")}
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                {t("upload")} ({pendingFiles.length})
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
