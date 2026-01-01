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
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Loader2, Wand2, FileText, AlertCircle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { modulesApi } from "@/lib/api";
import type { DetectedModule, AutoDetectResponse } from "@/types";

interface AutoDetectModulesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  onSuccess: () => void;
}

export function AutoDetectModulesModal({
  open,
  onOpenChange,
  courseId,
  onSuccess,
}: AutoDetectModulesModalProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");

  const [detecting, setDetecting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [detected, setDetected] = useState<DetectedModule[]>([]);
  const [unassigned, setUnassigned] = useState<string[]>([]);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [selectedModules, setSelectedModules] = useState<Set<string>>(new Set());
  const [hasDetected, setHasDetected] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setDetected([]);
      setUnassigned([]);
      setTotalDocuments(0);
      setSelectedModules(new Set());
      setHasDetected(false);
    }
  }, [open]);

  const handleDetect = async () => {
    setDetecting(true);
    try {
      const response: AutoDetectResponse = await modulesApi.autoDetect(courseId);
      setDetected(response.detected_modules);
      setUnassigned(response.unassigned_documents);
      setTotalDocuments(response.total_documents);
      // Select all by default
      setSelectedModules(new Set(response.detected_modules.map((m) => m.suggested_name)));
      setHasDetected(true);

      if (response.detected_modules.length === 0) {
        toast.info(t("noModulesDetected"));
      }
    } catch (error) {
      console.error("Error detecting modules:", error);
      toast.error(t("detectError"));
    } finally {
      setDetecting(false);
    }
  };

  const handleToggleModule = (name: string) => {
    setSelectedModules((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(name)) {
        newSet.delete(name);
      } else {
        newSet.add(name);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    setSelectedModules(new Set(detected.map((m) => m.suggested_name)));
  };

  const handleDeselectAll = () => {
    setSelectedModules(new Set());
  };

  const handleCreate = async () => {
    if (selectedModules.size === 0) {
      toast.error(t("selectAtLeastOne"));
      return;
    }

    setCreating(true);
    try {
      // Filter detected modules to only include selected ones
      const modulesToCreate = detected.filter((m) =>
        selectedModules.has(m.suggested_name)
      );

      // Create modules one by one
      let createdCount = 0;
      for (let i = 0; i < modulesToCreate.length; i++) {
        const module = modulesToCreate[i];
        try {
          const created = await modulesApi.create(courseId, {
            name: module.suggested_name,
            order_index: i,
          });

          // Assign documents to the module
          if (module.document_ids.length > 0) {
            await modulesApi.assignDocuments(created.id, module.document_ids);
          }

          createdCount++;
        } catch (err) {
          console.error(`Error creating module ${module.suggested_name}:`, err);
        }
      }

      toast.success(t("modulesCreated", { count: createdCount }));
      onSuccess();
      onOpenChange(false);
    } catch (error) {
      console.error("Error creating modules:", error);
      toast.error(t("createError"));
    } finally {
      setCreating(false);
    }
  };

  const selectedCount = selectedModules.size;
  const totalDocs = detected
    .filter((m) => selectedModules.has(m.suggested_name))
    .reduce((sum, m) => sum + m.document_count, 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5" />
            {t("autoDetectTitle")}
          </DialogTitle>
          <DialogDescription>{t("autoDetectDescription")}</DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {!hasDetected ? (
            // Initial state - show detect button
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Wand2 className="h-12 w-12 text-muted-foreground" />
              <p className="text-sm text-muted-foreground text-center max-w-md">
                {t("autoDetectHint")}
              </p>
              <Button onClick={handleDetect} disabled={detecting}>
                {detecting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {t("detecting")}
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 mr-2" />
                    {t("startDetection")}
                  </>
                )}
              </Button>
            </div>
          ) : detected.length === 0 ? (
            // No modules detected
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <AlertCircle className="h-12 w-12 text-muted-foreground" />
              <p className="text-sm text-muted-foreground text-center">
                {t("noModulesDetected")}
              </p>
              <p className="text-xs text-muted-foreground text-center max-w-md">
                {t("noModulesDetectedHint")}
              </p>
            </div>
          ) : (
            // Show detected modules
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div className="text-sm">
                  <span className="font-medium">{detected.length}</span>{" "}
                  {t("modulesDetectedCount")}
                  {unassigned.length > 0 && (
                    <span className="text-muted-foreground ml-2">
                      ({unassigned.length} {t("unassignedDocs")})
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={handleSelectAll}>
                    {t("selectAll")}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleDeselectAll}>
                    {t("deselectAll")}
                  </Button>
                </div>
              </div>

              {/* Module List */}
              <ScrollArea className="h-64 rounded-md border">
                <div className="p-2 space-y-2">
                  {detected.map((module) => (
                    <div
                      key={module.suggested_name}
                      className={`flex items-start space-x-3 p-3 rounded-lg transition-colors ${
                        selectedModules.has(module.suggested_name)
                          ? "bg-primary/5 border border-primary/20"
                          : "hover:bg-muted"
                      }`}
                    >
                      <Checkbox
                        id={`module-${module.suggested_name}`}
                        checked={selectedModules.has(module.suggested_name)}
                        onCheckedChange={() =>
                          handleToggleModule(module.suggested_name)
                        }
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <label
                          htmlFor={`module-${module.suggested_name}`}
                          className="font-medium cursor-pointer"
                        >
                          {module.suggested_name}
                        </label>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="secondary" className="text-xs">
                            <FileText className="h-3 w-3 mr-1" />
                            {module.document_count}{" "}
                            {module.document_count === 1
                              ? t("document")
                              : t("documents")}
                          </Badge>
                        </div>
                      </div>
                      {selectedModules.has(module.suggested_name) && (
                        <CheckCircle2 className="h-5 w-5 text-primary" />
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>

              {/* Selection summary */}
              <p className="text-sm text-muted-foreground">
                {t("selectionSummary", {
                  modules: selectedCount,
                  documents: totalDocs,
                })}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tCommon("cancel")}
          </Button>
          {hasDetected && detected.length > 0 && (
            <Button
              onClick={handleCreate}
              disabled={creating || selectedModules.size === 0}
            >
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t("creatingModules")}
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  {t("createSelected", { count: selectedCount })}
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
