"use client";

import * as React from "react";
import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ChevronRight,
  ChevronDown,
  MoreVertical,
  Pencil,
  Trash2,
  Upload,
  FolderOpen,
  FileText,
  FileAudio,
  File,
  GraduationCap,
  CheckCircle2,
  BookOpen,
  Sparkles,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { modulesApi } from "@/lib/api";
import type { ModuleWithProgress, Document, MasteryLevel } from "@/types";
import { formatFileSize } from "@/lib/utils";

interface ModuleAccordionItemProps {
  module: ModuleWithProgress;
  documents: Document[];
  isRecommended?: boolean;
  onEdit: (module: ModuleWithProgress) => void;
  onDelete: (module: ModuleWithProgress) => void;
  onUploadClick: (moduleId: string) => void;
  onLinkDirectoryClick: (moduleId: string) => void;
  onDocumentClick?: (document: Document) => void;
  isDeleting?: boolean;
}

function getMasteryBadgeVariant(level: MasteryLevel): "default" | "secondary" | "destructive" | "outline" {
  switch (level) {
    case "mastered":
      return "default";
    case "proficient":
      return "secondary";
    case "learning":
      return "outline";
    default:
      return "destructive";
  }
}

function getMasteryIcon(level: MasteryLevel) {
  switch (level) {
    case "mastered":
      return <CheckCircle2 className="h-3 w-3" />;
    case "proficient":
      return <GraduationCap className="h-3 w-3" />;
    case "learning":
      return <BookOpen className="h-3 w-3" />;
    default:
      return <Sparkles className="h-3 w-3" />;
  }
}

function getFileIcon(fileType: string) {
  const type = fileType?.toLowerCase() || "";
  if (["mp3", "wav", "m4a", "ogg", "webm"].includes(type)) {
    return <FileAudio className="h-4 w-4 text-purple-500" />;
  }
  if (["pdf"].includes(type)) {
    return <FileText className="h-4 w-4 text-red-500" />;
  }
  if (["md", "markdown", "txt"].includes(type)) {
    return <FileText className="h-4 w-4 text-blue-500" />;
  }
  if (["doc", "docx"].includes(type)) {
    return <FileText className="h-4 w-4 text-blue-600" />;
  }
  return <File className="h-4 w-4 text-gray-500" />;
}

export function ModuleAccordionItem({
  module,
  documents,
  isRecommended = false,
  onEdit,
  onDelete,
  onUploadClick,
  onLinkDirectoryClick,
  onDocumentClick,
  isDeleting = false,
}: ModuleAccordionItemProps) {
  const t = useTranslations("modules");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [moduleDocuments, setModuleDocuments] = useState<Document[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [documentsLoaded, setDocumentsLoaded] = useState(false);

  // Filter documents that belong to this module
  const filteredDocuments = React.useMemo(() => {
    return documents.filter(
      (doc) => doc.module_id === module.id || doc.module_id === module.id.replace("module:", "")
    );
  }, [documents, module.id]);

  // Load documents when accordion opens
  const handleOpenChange = useCallback(async (open: boolean) => {
    setIsOpen(open);

    if (open && !documentsLoaded && filteredDocuments.length === 0) {
      setLoadingDocuments(true);
      try {
        const result = await modulesApi.getDocuments(module.id);
        setModuleDocuments(result.documents);
        setDocumentsLoaded(true);
      } catch (error) {
        console.error("Error loading module documents:", error);
        toast.error(t("loadDocumentsError"));
      } finally {
        setLoadingDocuments(false);
      }
    }
  }, [documentsLoaded, filteredDocuments.length, module.id, t]);

  // Use filtered documents from props, fallback to loaded documents
  const displayDocuments = filteredDocuments.length > 0 ? filteredDocuments : moduleDocuments;

  // Progress color
  const progress = module.overall_progress;
  let progressColor = "bg-red-500";
  if (progress >= 80) {
    progressColor = "bg-green-500";
  } else if (progress >= 50) {
    progressColor = "bg-yellow-500";
  } else if (progress >= 25) {
    progressColor = "bg-orange-500";
  }

  return (
    <Collapsible open={isOpen} onOpenChange={handleOpenChange}>
      <div
        className={`border rounded-lg ${isRecommended ? "border-yellow-300 bg-yellow-50/30" : "border-gray-200"}`}
      >
        {/* Header */}
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50/50 transition-colors">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              {/* Chevron */}
              <div className="text-gray-400">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </div>

              {/* Module name and badges */}
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="font-medium text-sm truncate" title={module.name}>
                  {module.name}
                </span>
                {isRecommended && (
                  <Badge
                    variant="outline"
                    className="text-xs bg-yellow-50 text-yellow-700 border-yellow-300 shrink-0"
                  >
                    {t("recommended")}
                  </Badge>
                )}
              </div>

              {/* Document count */}
              <span className="text-sm text-muted-foreground shrink-0">
                {module.document_count} {t("documents")}
              </span>

              {/* Progress bar */}
              <div className="w-24 shrink-0">
                <div className="relative h-2 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className={`h-full transition-all ${progressColor}`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              {/* Progress percentage */}
              <span className="text-sm text-muted-foreground w-12 text-right shrink-0">
                {Math.round(progress)}%
              </span>

              {/* Mastery badge */}
              <Badge
                variant={getMasteryBadgeVariant(module.mastery_level)}
                className="gap-1 shrink-0"
              >
                {getMasteryIcon(module.mastery_level)}
                <span className="hidden sm:inline">
                  {t(`masteryLevels.${module.mastery_level}`)}
                </span>
              </Badge>
            </div>

            {/* Actions menu */}
            <div className="ml-2 shrink-0" onClick={(e) => e.stopPropagation()}>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    disabled={isDeleting}
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem onClick={() => onUploadClick(module.id)}>
                    <Upload className="h-4 w-4 mr-2" />
                    {t("uploadToModule")}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onLinkDirectoryClick(module.id)}>
                    <FolderOpen className="h-4 w-4 mr-2" />
                    {t("linkDirectory")}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => onEdit(module)}>
                    <Pencil className="h-4 w-4 mr-2" />
                    {tCommon("edit")}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(module)}
                    className="text-destructive"
                    disabled={isDeleting}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    {tCommon("delete")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CollapsibleTrigger>

        {/* Content */}
        <CollapsibleContent>
          <div className="border-t px-3 py-2 bg-gray-50/30">
            {loadingDocuments ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : displayDocuments.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground text-sm">
                <p>{t("noDocumentsInModule")}</p>
                <div className="flex justify-center gap-2 mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onUploadClick(module.id)}
                    className="gap-1"
                  >
                    <Upload className="h-3 w-3" />
                    {t("uploadToModule")}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                {displayDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 p-2 rounded hover:bg-gray-100 cursor-pointer transition-colors"
                    onClick={() => onDocumentClick?.(doc)}
                  >
                    {getFileIcon(doc.file_type)}
                    <span className="flex-1 text-sm truncate" title={doc.filename}>
                      {doc.filename}
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {formatFileSize(doc.size)}
                    </span>
                  </div>
                ))}
                {/* Upload button at bottom */}
                <div className="pt-2 border-t mt-2 flex gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onUploadClick(module.id)}
                    className="gap-1 text-xs"
                  >
                    <Upload className="h-3 w-3" />
                    {t("addDocument")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onLinkDirectoryClick(module.id)}
                    className="gap-1 text-xs"
                  >
                    <FolderOpen className="h-3 w-3" />
                    {t("linkDirectory")}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
