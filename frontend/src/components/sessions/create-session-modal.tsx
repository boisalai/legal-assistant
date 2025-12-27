"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { sessionsApi } from "@/lib/api";

interface CreateSessionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSessionCreated?: () => void;
}

export function CreateSessionModal({
  open,
  onOpenChange,
  onSessionCreated,
}: CreateSessionModalProps) {
  const t = useTranslations();
  const [creating, setCreating] = useState(false);

  // Form state
  const currentYear = new Date().getFullYear();
  const [semester, setSemester] = useState<string>("Automne");
  const [year, setYear] = useState<string>(currentYear.toString());
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // Generate title from semester and year
  const getTitle = () => `${semester} ${year}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!semester || !year || !startDate || !endDate) {
      toast.error("Veuillez remplir tous les champs");
      return;
    }

    const yearNum = parseInt(year, 10);
    if (isNaN(yearNum) || yearNum < 2000 || yearNum > 2100) {
      toast.error("Année invalide");
      return;
    }

    if (new Date(startDate) >= new Date(endDate)) {
      toast.error("La date de début doit être avant la date de fin");
      return;
    }

    setCreating(true);
    try {
      await sessionsApi.create({
        title: getTitle(),
        semester,
        year: yearNum,
        start_date: startDate,
        end_date: endDate,
      });

      toast.success("Session créée avec succès");
      onOpenChange(false);

      // Reset form
      setSemester("Automne");
      setYear(currentYear.toString());
      setStartDate("");
      setEndDate("");

      // Notify parent
      if (onSessionCreated) {
        onSessionCreated();
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur lors de la création");
    } finally {
      setCreating(false);
    }
  };

  // Suggest dates based on semester and year
  const suggestDates = () => {
    const yearNum = parseInt(year, 10);
    if (isNaN(yearNum)) return;

    let start = "";
    let end = "";

    switch (semester) {
      case "Hiver":
        start = `${yearNum}-01-08`;
        end = `${yearNum}-04-30`;
        break;
      case "Été":
        start = `${yearNum}-05-01`;
        end = `${yearNum}-08-31`;
        break;
      case "Automne":
        start = `${yearNum}-09-01`;
        end = `${yearNum}-12-20`;
        break;
    }

    if (start && end) {
      setStartDate(start);
      setEndDate(end);
      toast.info("Dates suggérées appliquées");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Nouvelle session académique</DialogTitle>
            <DialogDescription>
              Créez une session pour organiser vos cours par semestre.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Semester and Year */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="semester">Semestre</Label>
                <Select value={semester} onValueChange={setSemester} disabled={creating}>
                  <SelectTrigger id="semester">
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Hiver">Hiver</SelectItem>
                    <SelectItem value="Été">Été</SelectItem>
                    <SelectItem value="Automne">Automne</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="year">Année</Label>
                <Input
                  id="year"
                  type="number"
                  min="2000"
                  max="2100"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  placeholder="2025"
                  disabled={creating}
                />
              </div>
            </div>

            {/* Title preview */}
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm text-muted-foreground">Titre de la session :</p>
              <p className="font-semibold">{getTitle()}</p>
            </div>

            {/* Dates with suggestion button */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Dates de session</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={suggestDates}
                  disabled={creating || !year}
                >
                  Suggérer dates
                </Button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="start-date">Date de début</Label>
                  <Input
                    id="start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    disabled={creating}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="end-date">Date de fin</Label>
                  <Input
                    id="end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    disabled={creating}
                  />
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={creating}
            >
              Annuler
            </Button>
            <Button type="submit" disabled={creating}>
              {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Créer la session
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
