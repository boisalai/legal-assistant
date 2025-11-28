"use client";

import { useCallback } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Upload, FileText, X, AlertCircle } from "lucide-react";

interface FileUploadProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  accept?: Record<string, string[]>;
  maxSize?: number;
  maxFiles?: number;
  disabled?: boolean;
  className?: string;
}

export function FileUpload({
  files,
  onFilesChange,
  accept = { "application/pdf": [".pdf"] },
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 10,
  disabled = false,
  className,
}: FileUploadProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      if (rejectedFiles.length > 0) {
        // Handle rejected files (could show a toast notification)
        console.warn("Fichiers rejetes:", rejectedFiles);
      }

      // Add new files, avoiding duplicates
      const newFiles = acceptedFiles.filter(
        (newFile) => !files.some((f) => f.name === newFile.name && f.size === newFile.size)
      );

      if (newFiles.length > 0) {
        const totalFiles = [...files, ...newFiles].slice(0, maxFiles);
        onFilesChange(totalFiles);
      }
    },
    [files, onFilesChange, maxFiles]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept,
    maxSize,
    maxFiles: maxFiles - files.length,
    disabled: disabled || files.length >= maxFiles,
    multiple: true,
  });

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 o";
    const k = 1024;
    const sizes = ["o", "Ko", "Mo", "Go"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1).replace(".", ",")} ${sizes[i]}`;
  };

  const totalSize = files.reduce((acc, f) => acc + f.size, 0);

  return (
    <div className={cn("space-y-3", className)}>
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200",
          "hover:border-primary/50 hover:bg-muted/50",
          isDragActive && !isDragReject && "border-primary bg-primary/5 scale-[1.02]",
          isDragReject && "border-destructive bg-destructive/5",
          disabled && "opacity-50 cursor-not-allowed hover:border-muted-foreground/25 hover:bg-transparent",
          !isDragActive && !disabled && "border-muted-foreground/25"
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-3">
          {isDragReject ? (
            <>
              <AlertCircle className="h-10 w-10 text-destructive" />
              <div>
                <p className="text-sm font-medium text-destructive">Fichier non accepte</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Seuls les fichiers PDF sont acceptes (max {formatSize(maxSize)})
                </p>
              </div>
            </>
          ) : isDragActive ? (
            <>
              <Upload className="h-10 w-10 text-primary animate-bounce" />
              <p className="text-sm font-medium text-primary">Deposez vos fichiers ici</p>
            </>
          ) : (
            <>
              <div className="p-3 rounded-full bg-muted">
                <Upload className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">
                  Glissez vos fichiers PDF ici
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  ou cliquez pour sélectionner (max. {maxFiles} fichiers, {formatSize(maxSize)} chacun)
                </p>
              </div>
              <Button type="button" variant="outline" size="sm" className="mt-2">
                Parcourir
              </Button>
            </>
          )}
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="border rounded-lg divide-y">
          {files.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center gap-3 px-3 py-2 group hover:bg-muted/50 transition-colors"
            >
              <div className="p-1.5 rounded bg-primary/10">
                <FileText className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeFile(index)}
                className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}

          {/* Summary */}
          <div className="px-3 py-2 bg-muted/30 text-xs text-muted-foreground flex justify-between">
            <span>{files.length} fichier{files.length > 1 ? "s" : ""}</span>
            <span>{formatSize(totalSize)} au total</span>
          </div>
        </div>
      )}
    </div>
  );
}
