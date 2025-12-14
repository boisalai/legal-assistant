"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { SessionSelector } from "@/components/cases/session-selector";
import { casesApi } from "@/lib/api";

interface NewCaseModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NewCaseModal({ open, onOpenChange }: NewCaseModalProps) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Academic mode fields
  const [academicMode, setAcademicMode] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [courseCode, setCourseCode] = useState("");
  const [courseName, setCourseName] = useState("");
  const [professor, setProfessor] = useState("");
  const [credits, setCredits] = useState("3");
  const [color, setColor] = useState("#3B82F6");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);

    try {
      const payload: any = {
        title: title,
        description: description || undefined,
      };

      // Add academic fields if in academic mode
      if (academicMode) {
        if (sessionId) payload.session_id = sessionId;
        if (courseCode) payload.course_code = courseCode;
        if (courseName) payload.course_name = courseName;
        if (professor) payload.professor = professor;
        if (credits) payload.credits = parseInt(credits, 10);
        if (color) payload.color = color;
      }

      const newCase = await casesApi.upload(payload);

      // Reset form
      resetForm();
      onOpenChange(false);

      // Navigate to the new case
      const urlId = newCase.id.replace("case:", "");
      router.push(`/cases/${urlId}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la création");
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setAcademicMode(false);
    setSessionId("");
    setCourseCode("");
    setCourseName("");
    setProfessor("");
    setCredits("3");
    setColor("#3B82F6");
    setError(null);
  };

  const handleCancel = () => {
    resetForm();
    onOpenChange(false);
  };

  const isValid = title.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Nouveau dossier</DialogTitle>
            <DialogDescription>
              Informations sur le dossier
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="academic-mode"
                checked={academicMode}
                onCheckedChange={setAcademicMode}
              />
              <Label htmlFor="academic-mode" className="cursor-pointer">
                Mode académique (cours)
              </Label>
            </div>

            <div className="space-y-2">
              <Label htmlFor="title">Nom du dossier{academicMode && " / cours"}</Label>
              <Input
                id="title"
                placeholder={academicMode ? "Ex: Introduction au droit" : "Ex: DRT-1151G"}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Ex: Introduction à l'étude du droit de l'Université de Montréal."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>

            {academicMode && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="session">Session</Label>
                  <SessionSelector
                    value={sessionId}
                    onValueChange={setSessionId}
                    placeholder="Sélectionner une session"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="course-code">Code du cours</Label>
                    <Input
                      id="course-code"
                      placeholder="Ex: DRT-1151G"
                      value={courseCode}
                      onChange={(e) => setCourseCode(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="credits">Crédits</Label>
                    <Input
                      id="credits"
                      type="number"
                      min="1"
                      max="12"
                      value={credits}
                      onChange={(e) => setCredits(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="course-name">Nom du cours</Label>
                  <Input
                    id="course-name"
                    placeholder="Ex: Introduction au droit constitutionnel"
                    value={courseName}
                    onChange={(e) => setCourseName(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="professor">Professeur</Label>
                  <Input
                    id="professor"
                    placeholder="Ex: Prof. Dupont"
                    value={professor}
                    onChange={(e) => setProfessor(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="color">Couleur</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="color"
                      type="color"
                      value={color}
                      onChange={(e) => setColor(e.target.value)}
                      className="w-20 h-10"
                    />
                    <span className="text-sm text-muted-foreground">{color}</span>
                  </div>
                </div>
              </>
            )}

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Annuler
            </Button>
            <Button type="submit" disabled={!isValid || creating}>
              {creating ? "Création..." : "Créer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
