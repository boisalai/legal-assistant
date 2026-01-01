"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  Loader2,
  Layers,
  Wand2,
  Target,
  ChevronDown,
  ChevronRight,
  FileText,
  Inbox,
} from "lucide-react";
import { toast } from "sonner";
import { modulesApi, documentsApi } from "@/lib/api";
import { ModuleAccordionItem } from "./module-accordion-item";
import { CreateModuleModal } from "./create-module-modal";
import { AutoDetectModulesModal } from "./auto-detect-modules-modal";
import { UploadToModuleModal } from "./upload-to-module-modal";
import type { ModuleWithProgress, Document } from "@/types";
import { formatFileSize } from "@/lib/utils";

interface ModulesSectionProps {
  courseId: string;
  documents: Document[];
  onDocumentsChange?: () => void;
  refreshKey?: number;
  onDocumentClick?: (document: Document) => void;
}

export function ModulesSection({
  courseId,
  documents,
  onDocumentsChange,
  refreshKey,
  onDocumentClick,
}: ModulesSectionProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");

  const [modules, setModules] = useState<ModuleWithProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [courseProgress, setCourseProgress] = useState(0);
  const [recommendedModuleId, setRecommendedModuleId] = useState<string | null>(null);
  const [recommendationMessage, setRecommendationMessage] = useState<string | null>(null);

  const [deletingModuleId, setDeletingModuleId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [moduleToDelete, setModuleToDelete] = useState<ModuleWithProgress | null>(null);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [autoDetectModalOpen, setAutoDetectModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<ModuleWithProgress | null>(null);

  // Upload to module state
  const [uploadModuleId, setUploadModuleId] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Unassigned documents section
  const [unassignedOpen, setUnassignedOpen] = useState(false);

  // Compute unassigned documents
  const unassignedDocuments = documents.filter(
    (doc) => !doc.module_id && !doc.is_derived
  );

  // Fetch modules on mount and when refreshKey changes
  useEffect(() => {
    const fetchModules = async () => {
      try {
        const response = await modulesApi.listWithProgress(courseId);
        setModules(response.modules);
        setCourseProgress(response.course_overall_progress);
        setRecommendedModuleId(response.recommended_module_id || null);
        setRecommendationMessage(response.recommendation_message || null);
      } catch (error) {
        console.error("Error fetching modules:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchModules();
  }, [courseId, refreshKey]);

  const handleDeleteModule = async () => {
    if (!moduleToDelete) return;

    setDeletingModuleId(moduleToDelete.id);
    try {
      await modulesApi.delete(moduleToDelete.id);
      setModules((prev) => prev.filter((m) => m.id !== moduleToDelete.id));
      toast.success(t("deleted"));
      onDocumentsChange?.();
    } catch (error) {
      toast.error(t("deleteError"));
    } finally {
      setDeletingModuleId(null);
      setModuleToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleDeleteClick = (module: ModuleWithProgress) => {
    setModuleToDelete(module);
    setDeleteDialogOpen(true);
  };

  const handleEdit = (module: ModuleWithProgress) => {
    setEditingModule(module);
    setCreateModalOpen(true);
  };

  const handleUploadClick = (moduleId: string) => {
    setUploadModuleId(moduleId);
    setUploadModalOpen(true);
  };

  const handleLinkDirectoryClick = (moduleId: string) => {
    // TODO: Open link directory modal with module pre-selected
    toast.info(t("linkDirectoryComingSoon"));
  };

  const handleCreateSuccess = async () => {
    // Refresh modules list
    try {
      const response = await modulesApi.listWithProgress(courseId);
      setModules(response.modules);
      setCourseProgress(response.course_overall_progress);
      setRecommendedModuleId(response.recommended_module_id || null);
      setRecommendationMessage(response.recommendation_message || null);
    } catch (error) {
      console.error("Error refreshing modules:", error);
    }
    setEditingModule(null);
    onDocumentsChange?.();
  };

  const handleAutoDetectSuccess = async () => {
    // Refresh modules list
    try {
      const response = await modulesApi.listWithProgress(courseId);
      setModules(response.modules);
      setCourseProgress(response.course_overall_progress);
      setRecommendedModuleId(response.recommended_module_id || null);
      setRecommendationMessage(response.recommendation_message || null);
    } catch (error) {
      console.error("Error refreshing modules:", error);
    }
    onDocumentsChange?.();
  };

  const handleUploadSuccess = () => {
    setUploadModalOpen(false);
    setUploadModuleId(null);
    onDocumentsChange?.();
    // Refresh modules to update document counts
    handleCreateSuccess();
  };

  if (loading) {
    return (
      <div className="space-y-2">
        <h3 className="font-semibold text-base flex items-center gap-2">
          <Layers className="h-4 w-4" />
          {t("title")}
        </h3>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {t("title")} ({modules.length})
          </h3>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setAutoDetectModalOpen(true)}
              className="gap-1"
              disabled={documents.length === 0}
            >
              <Wand2 className="h-3 w-3" />
              {t("autoDetect")}
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setEditingModule(null);
                setCreateModalOpen(true);
              }}
              className="gap-1"
            >
              <Plus className="h-3 w-3" />
              {t("newModule")}
            </Button>
          </div>
        </div>

        {/* Course Progress Card */}
        {modules.length > 0 && (
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-4">
                <Target className="h-5 w-5 text-muted-foreground" />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{t("courseProgress")}</span>
                    <span className="text-sm text-muted-foreground">
                      {Math.round(courseProgress)}%
                    </span>
                  </div>
                  <Progress value={courseProgress} className="h-2" />
                  {recommendationMessage && (
                    <p className="text-sm text-muted-foreground mt-2">
                      {recommendationMessage}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Modules Accordion */}
        {modules.length > 0 ? (
          <div className="space-y-2">
            {modules
              .sort((a, b) => a.order_index - b.order_index)
              .map((module) => (
                <ModuleAccordionItem
                  key={module.id}
                  module={module}
                  documents={documents}
                  isRecommended={module.id === recommendedModuleId}
                  onEdit={handleEdit}
                  onDelete={handleDeleteClick}
                  onUploadClick={handleUploadClick}
                  onLinkDirectoryClick={handleLinkDirectoryClick}
                  onDocumentClick={onDocumentClick}
                  isDeleting={deletingModuleId === module.id}
                />
              ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground border rounded-lg">
            <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-sm">{t("noModules")}</p>
            <p className="text-xs mt-1">{t("noModulesHint")}</p>
          </div>
        )}

        {/* Unassigned Documents Section */}
        {unassignedDocuments.length > 0 && (
          <Collapsible open={unassignedOpen} onOpenChange={setUnassignedOpen}>
            <div className="border rounded-lg border-dashed border-gray-300 bg-gray-50/50">
              <CollapsibleTrigger asChild>
                <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-100/50 transition-colors">
                  <div className="flex items-center gap-2">
                    <div className="text-gray-400">
                      {unassignedOpen ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </div>
                    <Inbox className="h-4 w-4 text-gray-400" />
                    <span className="font-medium text-sm text-gray-600">
                      {t("unassigned")}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      ({unassignedDocuments.length})
                    </span>
                  </div>
                </div>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="border-t px-3 py-2">
                  <div className="space-y-1">
                    {unassignedDocuments.slice(0, 10).map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center gap-3 p-2 rounded hover:bg-gray-100 cursor-pointer transition-colors"
                        onClick={() => onDocumentClick?.(doc)}
                      >
                        <FileText className="h-4 w-4 text-gray-400" />
                        <span className="flex-1 text-sm truncate" title={doc.filename}>
                          {doc.filename}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatFileSize(doc.size)}
                        </span>
                      </div>
                    ))}
                    {unassignedDocuments.length > 10 && (
                      <p className="text-xs text-muted-foreground text-center py-2">
                        {t("andMore", { count: unassignedDocuments.length - 10 })}
                      </p>
                    )}
                  </div>
                </div>
              </CollapsibleContent>
            </div>
          </Collapsible>
        )}
      </div>

      {/* Create/Edit Module Modal */}
      <CreateModuleModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        courseId={courseId}
        documents={documents}
        module={editingModule}
        onSuccess={handleCreateSuccess}
      />

      {/* Auto-detect Modules Modal */}
      <AutoDetectModulesModal
        open={autoDetectModalOpen}
        onOpenChange={setAutoDetectModalOpen}
        courseId={courseId}
        onSuccess={handleAutoDetectSuccess}
      />

      {/* Upload to Module Modal */}
      {uploadModuleId && (
        <UploadToModuleModal
          open={uploadModalOpen}
          onOpenChange={setUploadModalOpen}
          moduleId={uploadModuleId}
          moduleName={modules.find((m) => m.id === uploadModuleId)?.name || ""}
          onSuccess={handleUploadSuccess}
        />
      )}

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription", { name: moduleToDelete?.name || "" })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setModuleToDelete(null)}>
              {tCommon("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteModule}
              className="bg-red-600 hover:bg-red-700"
            >
              {tCommon("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
