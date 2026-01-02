"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Check, X, Loader2 } from "lucide-react";
import type { Course } from "@/types";

interface CaseEditFormProps {
  caseData: Course;
  onSave: (data: {
    description?: string;
    course_code?: string;
    professor?: string;
    credits?: number;
    color?: string;
  }) => Promise<void>;
  onCancel: () => void;
}

export function CaseEditForm({ caseData, onSave, onCancel }: CaseEditFormProps) {
  const t = useTranslations();
  const [isSaving, setIsSaving] = useState(false);
  const [editDescription, setEditDescription] = useState(caseData.description || "");
  const [editCourseCode, setEditCourseCode] = useState(caseData.course_code || "");
  const [editProfessor, setEditProfessor] = useState(caseData.professor || "");
  const [editCredits, setEditCredits] = useState(caseData.credits?.toString() || "3");
  const [editColor, setEditColor] = useState(caseData.color || "#3B82F6");

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const updateData: {
        description?: string;
        course_code?: string;
        professor?: string;
        credits?: number;
        color?: string;
      } = {
        description: editDescription,
      };

      if (editCourseCode) updateData.course_code = editCourseCode;
      if (editProfessor) updateData.professor = editProfessor;
      if (editCredits) updateData.credits = parseInt(editCredits, 10);
      if (editColor) updateData.color = editColor;

      await onSave(updateData);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditDescription(caseData.description || "");
    setEditCourseCode(caseData.course_code || "");
    setEditProfessor(caseData.professor || "");
    setEditCredits(caseData.credits?.toString() || "3");
    setEditColor(caseData.color || "#3B82F6");
    onCancel();
  };

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-muted/50">
      <h3 className="font-semibold text-sm">{t("courses.editCourse")}</h3>

      <div className="space-y-4">
        <h4 className="font-medium text-sm text-muted-foreground">
          {t("courses.academicInfo")}
        </h4>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="edit-course-code">{t("courses.courseCode")}</Label>
            <Input
              id="edit-course-code"
              value={editCourseCode}
              onChange={(e) => setEditCourseCode(e.target.value)}
              placeholder="Ex: DRT-1151G"
              disabled={isSaving}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-credits">{t("courses.credits")}</Label>
            <Input
              id="edit-credits"
              type="number"
              min="0"
              max="6"
              value={editCredits}
              onChange={(e) => setEditCredits(e.target.value)}
              disabled={isSaving}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="edit-description">{t("courses.description")}</Label>
          <Textarea
            id="edit-description"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            placeholder={t("courses.descriptionPlaceholder")}
            disabled={isSaving}
            className="text-sm min-h-[80px]"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="edit-professor">{t("courses.professor")}</Label>
          <Input
            id="edit-professor"
            value={editProfessor}
            onChange={(e) => setEditProfessor(e.target.value)}
            placeholder="Ex: Prof. Dupont"
            disabled={isSaving}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="edit-color">{t("courses.color")}</Label>
          <div className="flex items-center gap-2">
            <Input
              id="edit-color"
              type="color"
              value={editColor}
              onChange={(e) => setEditColor(e.target.value)}
              disabled={isSaving}
              className="w-20 h-10"
            />
            <span className="text-sm text-muted-foreground">{editColor}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 pt-2">
        <Button size="sm" onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
          {t("common.save")}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={handleCancel}
          disabled={isSaving}
        >
          <X className="h-4 w-4" />
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}
