"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import { AlertTriangle, FileWarning, CheckCircle2, User, MapPin, Calendar, DollarSign, FileText, Building } from "lucide-react";
import type { Case, Checklist, Document } from "@/types";
import { useState } from "react";

interface OverviewTabProps {
  caseData: Case;
  documents: Document[];
  checklist: Checklist | null;
}

export function OverviewTab({ caseData, documents, checklist }: OverviewTabProps) {
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});

  const score = caseData.score_confiance !== undefined
    ? Math.round(caseData.score_confiance * 100)
    : null;

  const getScoreColor = (s: number) => {
    if (s >= 70) return "text-emerald-600";
    if (s >= 50) return "text-amber-600";
    return "text-red-600";
  };

  const getScoreBarColor = (s: number) => {
    if (s >= 70) return "[&>div]:bg-emerald-500";
    if (s >= 50) return "[&>div]:bg-amber-500";
    return "[&>div]:bg-red-500";
  };

  const toggleCheckItem = (index: number) => {
    setCheckedItems(prev => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <div className="space-y-6">
      {/* Summary Row */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Score Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Score de confiance
            </CardTitle>
          </CardHeader>
          <CardContent>
            {score !== null && score > 0 ? (
              <div className="space-y-2">
                <span className={`text-3xl font-bold ${getScoreColor(score)}`}>
                  {score}%
                </span>
                <Progress value={score} className={`h-2 ${getScoreBarColor(score)}`} />
              </div>
            ) : (
              <span className="text-muted-foreground">Non analysé</span>
            )}
          </CardContent>
        </Card>

        {/* Documents Count */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{documents.length}</span>
            <p className="text-sm text-muted-foreground">
              {documents.length === 1 ? "document uploadé" : "documents uploadés"}
            </p>
          </CardContent>
        </Card>

        {/* Checklist Progress */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Vérifications
            </CardTitle>
          </CardHeader>
          <CardContent>
            {checklist ? (
              <>
                <span className="text-3xl font-bold">
                  {Object.values(checkedItems).filter(Boolean).length}/{checklist.items.length}
                </span>
                <p className="text-sm text-muted-foreground">tâches complétées</p>
              </>
            ) : (
              <span className="text-muted-foreground">Non disponible</span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Extracted Info */}
      {checklist && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Informations extraites</CardTitle>
            <CardDescription>Données identifiées dans les documents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <InfoItem icon={User} label="Parties" value="À compléter" />
              <InfoItem icon={Building} label="Type de propriété" value={caseData.type_transaction} />
              <InfoItem icon={MapPin} label="Adresse" value="À extraire" />
              <InfoItem icon={DollarSign} label="Prix de vente" value="À extraire" />
              <InfoItem icon={Calendar} label="Date prévue" value="À déterminer" />
              <InfoItem icon={FileText} label="Documents" value={`${documents.length} fichier(s)`} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Points d'attention */}
      {checklist?.points_attention && checklist.points_attention.length > 0 && (
        <Card className="border-amber-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-4 w-4" />
              Points d'attention ({checklist.points_attention.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {checklist.points_attention.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-amber-500 mt-0.5">•</span>
                  {point}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Documents manquants */}
      {checklist?.documents_manquants && checklist.documents_manquants.length > 0 && (
        <Card className="border-red-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2 text-red-600">
              <FileWarning className="h-4 w-4" />
              Documents manquants ({checklist.documents_manquants.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {checklist.documents_manquants.map((doc, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-red-500 mt-0.5">•</span>
                  {doc}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Checklist */}
      {checklist && checklist.items.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Liste de vérification ({checklist.items.length} éléments)
            </CardTitle>
            <CardDescription>
              Cochez les éléments au fur et à mesure de leur vérification
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {checklist.items.map((item, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 p-3 rounded-lg border ${
                    checkedItems[i] ? "bg-muted/50 border-muted" : "bg-background"
                  }`}
                >
                  <Checkbox
                    id={`item-${i}`}
                    checked={checkedItems[i] || false}
                    onCheckedChange={() => toggleCheckItem(i)}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <label
                      htmlFor={`item-${i}`}
                      className={`text-sm font-medium cursor-pointer ${
                        checkedItems[i] ? "line-through text-muted-foreground" : ""
                      }`}
                    >
                      {item.titre}
                    </label>
                    {item.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                    )}
                  </div>
                  <Badge
                    variant={
                      item.priorite === "critique" ? "destructive" :
                      item.priorite === "haute" ? "default" :
                      item.priorite === "moyenne" ? "secondary" : "outline"
                    }
                    className="shrink-0"
                  >
                    {item.priorite}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface InfoItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}

function InfoItem({ icon: Icon, label, value }: InfoItemProps) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
      <Icon className="h-5 w-5 text-muted-foreground shrink-0" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium truncate">{value}</p>
      </div>
    </div>
  );
}
