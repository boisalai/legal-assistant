"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { coursesApi } from "@/lib/api";

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

  // Course fields
  const [year, setYear] = useState<string>("");
  const [semester, setSemester] = useState<string>("");
  const [courseCode, setCourseCode] = useState("");
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

      // Add course fields
      if (year) payload.year = parseInt(year, 10);
      if (semester) payload.semester = semester;
      if (courseCode) payload.course_code = courseCode;
      if (professor) payload.professor = professor;
      if (credits) payload.credits = parseInt(credits, 10);
      if (color) payload.color = color;

      const newCase = await coursesApi.create(payload);

      // Reset form
      resetForm();
      onOpenChange(false);

      // Navigate to the new course
      const urlId = newCase.id.replace("course:", "").replace("case:", "");
      router.push(`/courses/${urlId}`);
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
    setYear("");
    setSemester("");
    setCourseCode("");
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
            <DialogTitle>Nouveau cours</DialogTitle>
            <DialogDescription>
              Informations sur le cours
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Nom du cours</Label>
              <Input
                id="title"
                placeholder="Ex: Introduction au droit"
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

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="year">Année</Label>
                <Select value={year} onValueChange={setYear}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2025">2025</SelectItem>
                    <SelectItem value="2026">2026</SelectItem>
                    <SelectItem value="2027">2027</SelectItem>
                    <SelectItem value="2028">2028</SelectItem>
                    <SelectItem value="2029">2029</SelectItem>
                    <SelectItem value="2030">2030</SelectItem>
                    <SelectItem value="2031">2031</SelectItem>
                    <SelectItem value="2032">2032</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="semester">Session</Label>
                <Select value={semester} onValueChange={setSemester}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Hiver">Hiver</SelectItem>
                    <SelectItem value="Été">Été</SelectItem>
                    <SelectItem value="Automne">Automne</SelectItem>
                  </SelectContent>
                </Select>
              </div>
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
                  min="0"
                  max="6"
                  value={credits}
                  onChange={(e) => setCredits(e.target.value)}
                />
              </div>
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
