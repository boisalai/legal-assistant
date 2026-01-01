"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { Loader2, FileText, Upload, X } from "lucide-react";
import { toast } from "sonner";
import { modulesApi } from "@/lib/api";
import { formatFileSize } from "@/lib/utils";
import type { Module, ModuleWithProgress, Document } from "@/types";

interface CreateModuleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  documents: Document[];
  module?: ModuleWithProgress | null; // For editing
  onSuccess: () => void;
}

export function CreateModuleModal({
  open,
  onOpenChange,
  courseId,
  documents,
  module,
  onSuccess,
}: CreateModuleModalProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [orderIndex, setOrderIndex] = useState(0);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // File upload state
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!module;

  // Reset form when modal opens/closes or module changes
  useEffect(() => {
    if (open) {
      if (module) {
        setName(module.name);
        setDescription(module.description || "");
        setOrderIndex(module.order_index);
        // Get documents assigned to this module
        const assignedDocs = documents.filter(
          (doc) => doc.module_id === module.id
        );
        setSelectedDocIds(assignedDocs.map((d) => d.id));
      } else {
        setName("");
        setDescription("");
        setOrderIndex(0);
        setSelectedDocIds([]);
      }
      setPendingFiles([]);
      setUploadProgress({ current: 0, total: 0 });
    }
  }, [open, module, documents]);

  // Drag & drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setPendingFiles((prev) => [...prev, ...files]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setPendingFiles((prev) => [...prev, ...files]);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  const removeFile = useCallback((index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Filter to show unassigned documents + documents assigned to current module (if editing)
  const availableDocuments = documents.filter((doc) => {
    // Show if unassigned
    if (!doc.module_id) return true;
    // Show if assigned to the module we're editing
    if (isEditing && doc.module_id === module?.id) return true;
    return false;
  });

  const handleToggleDocument = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    setSelectedDocIds(availableDocuments.map((d) => d.id));
  };

  const handleDeselectAll = () => {
    setSelectedDocIds([]);
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error(t("nameRequired"));
      return;
    }

    setSubmitting(true);
    try {
      let savedModule: Module;

      if (isEditing && module) {
        // Update existing module
        savedModule = await modulesApi.update(module.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          order_index: orderIndex,
        });

        // Update document assignments
        // First, get current assignments
        const currentlyAssigned = documents.filter(
          (doc) => doc.module_id === module.id
        );
        const currentIds = new Set(currentlyAssigned.map((d) => d.id));
        const newIds = new Set(selectedDocIds);

        // Documents to assign (in newIds but not in currentIds)
        const toAssign = selectedDocIds.filter((id) => !currentIds.has(id));
        // Documents to unassign (in currentIds but not in newIds)
        const toUnassign = currentlyAssigned
          .filter((d) => !newIds.has(d.id))
          .map((d) => d.id);

        if (toAssign.length > 0) {
          await modulesApi.assignDocuments(module.id, toAssign);
        }
        if (toUnassign.length > 0) {
          await modulesApi.unassignDocuments(module.id, toUnassign);
        }

        toast.success(t("updated"));
      } else {
        // Create new module
        savedModule = await modulesApi.create(courseId, {
          name: name.trim(),
          description: description.trim() || undefined,
          order_index: orderIndex,
        });

        // Assign selected documents
        if (selectedDocIds.length > 0) {
          await modulesApi.assignDocuments(savedModule.id, selectedDocIds);
        }

        // Upload pending files to the new module
        if (pendingFiles.length > 0) {
          setUploadProgress({ current: 0, total: pendingFiles.length });
          let uploadedCount = 0;

          for (const file of pendingFiles) {
            try {
              await modulesApi.uploadToModule(savedModule.id, file, false);
              uploadedCount++;
              setUploadProgress({ current: uploadedCount, total: pendingFiles.length });
            } catch (uploadError) {
              console.error(`Error uploading ${file.name}:`, uploadError);
              toast.error(t("uploadError", { filename: file.name }));
            }
          }

          if (uploadedCount > 0) {
            toast.success(t("createdWithFiles", { count: uploadedCount }));
          } else {
            toast.success(t("created"));
          }
        } else {
          toast.success(t("created"));
        }
      }

      onSuccess();
      onOpenChange(false);
    } catch (error) {
      console.error("Error saving module:", error);
      toast.error(isEditing ? t("updateError") : t("createError"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? t("editTitle") : t("createTitle")}
          </DialogTitle>
          <DialogDescription>
            {isEditing ? t("editDescription") : t("createDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Module Name */}
          <div className="space-y-2">
            <Label htmlFor="module-name">{t("name")} *</Label>
            <Input
              id="module-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("namePlaceholder")}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="module-description">{t("description")}</Label>
            <Textarea
              id="module-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("descriptionPlaceholder")}
              rows={2}
            />
          </div>

          {/* Order Index */}
          <div className="space-y-2">
            <Label htmlFor="order-index">{t("orderIndex")}</Label>
            <Input
              id="order-index"
              type="number"
              min={0}
              value={orderIndex}
              onChange={(e) => setOrderIndex(parseInt(e.target.value) || 0)}
            />
            <p className="text-xs text-muted-foreground">
              {t("orderIndexHint")}
            </p>
          </div>

          {/* Document Assignment */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>{t("assignDocuments")}</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleSelectAll}
                  disabled={availableDocuments.length === 0}
                >
                  {t("selectAll")}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleDeselectAll}
                  disabled={selectedDocIds.length === 0}
                >
                  {t("deselectAll")}
                </Button>
              </div>
            </div>

            {availableDocuments.length > 0 ? (
              <ScrollArea className="h-48 rounded-md border p-2">
                <div className="space-y-2">
                  {availableDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center space-x-2 p-2 hover:bg-muted rounded overflow-hidden"
                    >
                      <Checkbox
                        id={`doc-${doc.id}`}
                        checked={selectedDocIds.includes(doc.id)}
                        onCheckedChange={() => handleToggleDocument(doc.id)}
                        className="shrink-0"
                      />
                      <label
                        htmlFor={`doc-${doc.id}`}
                        className="flex-1 min-w-0 flex items-center gap-2 cursor-pointer text-sm"
                      >
                        <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="truncate">{doc.filename}</span>
                      </label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-24 flex items-center justify-center text-sm text-muted-foreground border rounded-md">
                {t("noDocumentsAvailable")}
              </div>
            )}

            <p className="text-sm text-muted-foreground">
              {t("documentsSelected", { count: selectedDocIds.length })}
            </p>
          </div>

          {/* File Upload Zone - Only for new modules */}
          {!isEditing && (
            <div className="space-y-2">
              <Label>{t("uploadNewFiles")}</Label>
              <div
                className={`
                  border-2 border-dashed rounded-lg p-6 text-center transition-colors
                  ${isDragOver
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/25 hover:border-muted-foreground/50"
                  }
                `}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileSelect}
                  accept=".pdf,.doc,.docx,.md,.mdx,.txt,.mp3,.wav,.m4a"
                />
                <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-2">
                  {t("dropFilesHere")}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {t("browseFiles")}
                </Button>
              </div>

              {/* Pending files list */}
              {pendingFiles.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">
                    {t("filesToUpload", { count: pendingFiles.length })}
                  </p>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {pendingFiles.map((file, index) => (
                      <div
                        key={`${file.name}-${index}`}
                        className="flex items-center justify-between p-2 bg-muted rounded text-sm"
                      >
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="truncate">{file.name}</span>
                          <span className="text-xs text-muted-foreground shrink-0">
                            ({formatFileSize(file.size)})
                          </span>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => removeFile(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Upload progress */}
              {submitting && uploadProgress.total > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>{t("uploading")}</span>
                    <span>
                      {uploadProgress.current} / {uploadProgress.total}
                    </span>
                  </div>
                  <Progress
                    value={(uploadProgress.current / uploadProgress.total) * 100}
                    className="h-2"
                  />
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tCommon("cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {isEditing ? t("updating") : t("creating")}
              </>
            ) : isEditing ? (
              tCommon("save")
            ) : (
              tCommon("create")
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
