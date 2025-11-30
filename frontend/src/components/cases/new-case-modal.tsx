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
import { casesApi } from "@/lib/api";

interface NewCaseModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CASE_TYPES = [
  { value: "civil", label: "Civil" },
  { value: "criminal", label: "Pénal" },
  { value: "administrative", label: "Administratif" },
  { value: "family", label: "Familial" },
  { value: "commercial", label: "Commercial" },
  { value: "labor", label: "Travail" },
  { value: "constitutional", label: "Constitutionnel" },
  { value: "other", label: "Autre" },
];

export function NewCaseModal({ open, onOpenChange }: NewCaseModalProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("civil");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);

    try {
      const newCase = await casesApi.create({
        nom_dossier: name,
        type_transaction: type,
        description: description || undefined,
      });

      // Reset form
      setName("");
      setDescription("");
      setType("civil");
      onOpenChange(false);

      // Navigate to the new case
      const urlId = newCase.id.replace("dossier:", "").replace("judgment:", "");
      router.push(`/cases/${urlId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la création");
    } finally {
      setCreating(false);
    }
  };

  const handleCancel = () => {
    setName("");
    setDescription("");
    setType("civil");
    setError(null);
    onOpenChange(false);
  };

  const isValid = name.trim() !== "";

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
            <div className="space-y-2">
              <Label htmlFor="name">Nom du dossier</Label>
              <Input
                id="name"
                placeholder="Ex: Dupont c. Lavoie 2024"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Description optionnelle..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger id="type">
                  <SelectValue placeholder="Sélectionner un type" />
                </SelectTrigger>
                <SelectContent>
                  {CASE_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
