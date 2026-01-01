"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
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
} from "lucide-react";
import { toast } from "sonner";
import { modulesApi } from "@/lib/api";
import { ModulesDataTable } from "./modules-data-table";
import { CreateModuleModal } from "./create-module-modal";
import type { Module, Document } from "@/types";

interface ModulesSectionProps {
  courseId: string;
  documents: Document[];
  onDocumentsChange?: () => void;
  refreshKey?: number;
}

export function ModulesSection({
  courseId,
  documents,
  onDocumentsChange,
  refreshKey,
}: ModulesSectionProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");

  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);

  const [deletingModuleId, setDeletingModuleId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [moduleToDelete, setModuleToDelete] = useState<Module | null>(null);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<Module | null>(null);

  // Fetch modules on mount and when refreshKey changes
  useEffect(() => {
    const fetchModules = async () => {
      try {
        const response = await modulesApi.list(courseId);
        setModules(response.modules);
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

  const handleDeleteClick = (module: Module) => {
    setModuleToDelete(module);
    setDeleteDialogOpen(true);
  };

  const handleEdit = (module: Module) => {
    setEditingModule(module);
    setCreateModalOpen(true);
  };

  const handleCreateSuccess = async () => {
    // Refresh modules list
    try {
      const response = await modulesApi.list(courseId);
      setModules(response.modules);
    } catch (error) {
      console.error("Error refreshing modules:", error);
    }
    setEditingModule(null);
    onDocumentsChange?.();
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
      <div className="space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {t("title")} ({modules.length})
          </h3>
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

        {/* DataTable */}
        <ModulesDataTable
          modules={modules}
          onEdit={handleEdit}
          onDelete={handleDeleteClick}
          deletingModuleId={deletingModuleId}
        />
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
