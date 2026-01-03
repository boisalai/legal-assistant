import { useState, useCallback } from "react";
import { useDropzone, Accept, DropzoneOptions, FileRejection } from "react-dropzone";

/**
 * Common file type presets for the application
 */
export const FILE_TYPE_PRESETS = {
  documents: {
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
  },
  audio: {
    "audio/mpeg": [".mp3"],
    "audio/wav": [".wav"],
    "audio/mp4": [".m4a"],
  },
  all: {
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "audio/mpeg": [".mp3"],
    "audio/wav": [".wav"],
    "audio/mp4": [".m4a"],
  },
} as const;

export interface UseFileDropOptions {
  /** File types to accept (use FILE_TYPE_PRESETS or custom Accept object) */
  accept?: Accept;
  /** Maximum file size in bytes (default: 50MB) */
  maxSize?: number;
  /** Allow multiple files (default: true) */
  multiple?: boolean;
  /** Called when valid files are dropped/selected */
  onFilesAdded?: (files: File[]) => void;
  /** Called when files are rejected */
  onFilesRejected?: (errors: string[]) => void;
  /** Disabled state */
  disabled?: boolean;
}

export interface UseFileDropReturn {
  /** Files currently in the drop zone */
  files: File[];
  /** Whether a drag is currently over the drop zone */
  isDragActive: boolean;
  /** Props to spread on the drop zone container */
  getRootProps: ReturnType<typeof useDropzone>["getRootProps"];
  /** Props to spread on the hidden input */
  getInputProps: ReturnType<typeof useDropzone>["getInputProps"];
  /** Open the file dialog programmatically */
  openFileDialog: () => void;
  /** Remove a file by index */
  removeFile: (index: number) => void;
  /** Clear all files */
  clearFiles: () => void;
  /** Add files programmatically */
  addFiles: (newFiles: File[]) => void;
}

const DEFAULT_MAX_SIZE = 50 * 1024 * 1024; // 50MB

/**
 * Hook for handling file drag-and-drop with react-dropzone
 *
 * @example
 * ```tsx
 * const { files, isDragActive, getRootProps, getInputProps, removeFile } = useFileDrop({
 *   accept: FILE_TYPE_PRESETS.documents,
 *   maxSize: 50 * 1024 * 1024,
 *   onFilesAdded: (newFiles) => console.log('Added:', newFiles),
 * });
 *
 * return (
 *   <div {...getRootProps()} className={isDragActive ? 'drag-active' : ''}>
 *     <input {...getInputProps()} />
 *     <p>Drop files here or click to select</p>
 *   </div>
 * );
 * ```
 */
export function useFileDrop({
  accept = FILE_TYPE_PRESETS.all,
  maxSize = DEFAULT_MAX_SIZE,
  multiple = true,
  onFilesAdded,
  onFilesRejected,
  disabled = false,
}: UseFileDropOptions = {}): UseFileDropReturn {
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      if (acceptedFiles.length > 0) {
        setFiles((prev) => [...prev, ...acceptedFiles]);
        onFilesAdded?.(acceptedFiles);
      }

      if (fileRejections.length > 0) {
        const errors = fileRejections.map((rejection) => {
          const errorMessages = rejection.errors.map((e) => e.message).join(", ");
          return `${rejection.file.name}: ${errorMessages}`;
        });
        onFilesRejected?.(errors);
      }
    },
    [onFilesAdded, onFilesRejected]
  );

  const dropzoneOptions: DropzoneOptions = {
    onDrop,
    accept,
    maxSize,
    multiple,
    disabled,
  };

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone(dropzoneOptions);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  const addFiles = useCallback((newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles]);
    onFilesAdded?.(newFiles);
  }, [onFilesAdded]);

  return {
    files,
    isDragActive,
    getRootProps,
    getInputProps,
    openFileDialog: open,
    removeFile,
    clearFiles,
    addFiles,
  };
}
