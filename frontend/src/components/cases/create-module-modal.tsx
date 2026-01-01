"use client";

import { useState, useEffect } from "react";
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
import { Loader2, FileText } from "lucide-react";
import { toast } from "sonner";
import { modulesApi } from "@/lib/api";
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
  const [examWeight, setExamWeight] = useState<number | undefined>(undefined);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const isEditing = !!module;

  // Reset form when modal opens/closes or module changes
  useEffect(() => {
    if (open) {
      if (module) {
        setName(module.name);
        setDescription(module.description || "");
        setOrderIndex(module.order_index);
        setExamWeight(module.exam_weight);
        // Get documents assigned to this module
        const assignedDocs = documents.filter(
          (doc) => doc.module_id === module.id
        );
        setSelectedDocIds(assignedDocs.map((d) => d.id));
      } else {
        setName("");
        setDescription("");
        setOrderIndex(0);
        setExamWeight(undefined);
        setSelectedDocIds([]);
      }
    }
  }, [open, module, documents]);

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
          exam_weight: examWeight,
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
          exam_weight: examWeight,
        });

        // Assign selected documents
        if (selectedDocIds.length > 0) {
          await modulesApi.assignDocuments(savedModule.id, selectedDocIds);
        }

        toast.success(t("created"));
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
      <DialogContent className="max-w-2xl">
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

          {/* Order Index and Exam Weight */}
          <div className="grid grid-cols-2 gap-4">
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

            <div className="space-y-2">
              <Label htmlFor="exam-weight">{t("examWeight")}</Label>
              <Input
                id="exam-weight"
                type="number"
                min={0}
                max={100}
                step={5}
                value={examWeight !== undefined ? examWeight * 100 : ""}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "") {
                    setExamWeight(undefined);
                  } else {
                    setExamWeight(Math.min(100, Math.max(0, parseInt(val))) / 100);
                  }
                }}
                placeholder="20"
              />
              <p className="text-xs text-muted-foreground">
                {t("examWeightHint")}
              </p>
            </div>
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
                      className="flex items-center space-x-2 p-2 hover:bg-muted rounded"
                    >
                      <Checkbox
                        id={`doc-${doc.id}`}
                        checked={selectedDocIds.includes(doc.id)}
                        onCheckedChange={() => handleToggleDocument(doc.id)}
                      />
                      <label
                        htmlFor={`doc-${doc.id}`}
                        className="flex-1 flex items-center gap-2 cursor-pointer text-sm"
                      >
                        <FileText className="h-4 w-4 text-muted-foreground" />
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
