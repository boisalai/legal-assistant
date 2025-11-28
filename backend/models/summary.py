"""
Modeles de donnees pour les resumes de jugements (Case Briefs).

Ce module definit les schemas Pydantic pour:
- CaseBrief: Resume structure d'un jugement
- LegalIssue: Question en litige
- LegalRule: Regle de droit applicable
- AnalysisPoint: Point d'analyse
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Type de resume
SummaryType = Literal[
    "case_brief",       # Resume complet (format case brief)
    "quick_summary",    # Resume rapide (points cles)
    "ratio_only",       # Ratio decidendi seulement
    "facts_only"        # Faits seulement
]

# Statut du resume
SummaryStatus = Literal[
    "generating",   # En cours de generation
    "completed",    # Termine
    "error"         # Erreur
]


class Party(BaseModel):
    """Une partie au litige."""

    name: str = Field(..., description="Nom de la partie")
    role: Literal["plaintiff", "defendant", "appellant", "respondent", "intervenor", "other"] = Field(
        ..., description="Role dans le litige"
    )
    represented_by: Optional[str] = Field(None, description="Avocat/procureur")


class LegalIssue(BaseModel):
    """Question en litige."""

    question: str = Field(..., description="La question juridique")
    answer: Optional[str] = Field(None, description="Reponse du tribunal")
    importance: Literal["primary", "secondary", "incidental"] = Field(
        default="primary", description="Importance de la question"
    )


class LegalRule(BaseModel):
    """Regle de droit applicable."""

    rule: str = Field(..., description="La regle de droit")
    source: Optional[str] = Field(None, description="Source (article, precedent)")
    source_type: Literal["statute", "regulation", "case_law", "doctrine", "principle"] = Field(
        default="case_law", description="Type de source"
    )


class AnalysisPoint(BaseModel):
    """Point d'analyse du tribunal."""

    point: str = Field(..., description="Le point d'analyse")
    is_ratio: bool = Field(default=False, description="Fait partie du ratio decidendi")
    is_obiter: bool = Field(default=False, description="Obiter dictum")


class CaseBriefCreate(BaseModel):
    """Schema pour creer un resume."""

    judgment_id: str = Field(..., description="ID du jugement source")
    summary_type: SummaryType = Field(default="case_brief", description="Type de resume")
    model_id: Optional[str] = Field(None, description="Modele LLM utilise")


class CaseBrief(BaseModel):
    """Resume complet d'un jugement (Case Brief)."""

    id: str = Field(..., description="ID unique du resume")
    judgment_id: str = Field(..., description="ID du jugement source")

    # ===== Identification =====
    case_name: str = Field(..., description="Nom de l'affaire")
    citation: Optional[str] = Field(None, description="Reference")
    court: str = Field(..., description="Tribunal")
    decision_date: Optional[str] = Field(None, description="Date de la decision")
    judge: Optional[str] = Field(None, description="Juge")

    # ===== Parties =====
    parties: list[Party] = Field(default_factory=list, description="Parties au litige")

    # ===== Faits =====
    facts: list[str] = Field(default_factory=list, description="Faits pertinents")
    procedural_history: Optional[str] = Field(None, description="Historique procedural")

    # ===== Questions en litige =====
    issues: list[LegalIssue] = Field(default_factory=list, description="Questions en litige")

    # ===== Regles de droit =====
    rules: list[LegalRule] = Field(default_factory=list, description="Regles applicables")

    # ===== Analyse =====
    analysis: list[AnalysisPoint] = Field(default_factory=list, description="Points d'analyse")
    ratio_decidendi: Optional[str] = Field(None, description="Ratio decidendi (motifs essentiels)")
    obiter_dicta: list[str] = Field(default_factory=list, description="Obiter dicta (remarques incidentes)")

    # ===== Conclusion =====
    holding: str = Field(..., description="Decision/Dispositif")
    remedy: Optional[str] = Field(None, description="Remede accorde")

    # ===== Metadata =====
    summary_type: SummaryType = Field(default="case_brief")
    status: SummaryStatus = Field(default="completed")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Score de confiance (0-1)")

    # Generation info
    model_id: Optional[str] = Field(None, description="Modele LLM utilise")
    generation_time_seconds: Optional[float] = Field(None, description="Temps de generation")

    # Notes personnelles (ajoutees par l'utilisateur)
    personal_notes: Optional[str] = Field(None, description="Notes personnelles")
    tags: list[str] = Field(default_factory=list, description="Tags personnalises")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class CaseBriefUpdate(BaseModel):
    """Schema pour mettre a jour un resume."""

    # L'utilisateur peut modifier ses notes et tags
    personal_notes: Optional[str] = None
    tags: Optional[list[str]] = None

    # Corrections manuelles possibles
    facts: Optional[list[str]] = None
    issues: Optional[list[LegalIssue]] = None
    rules: Optional[list[LegalRule]] = None
    ratio_decidendi: Optional[str] = None
    holding: Optional[str] = None


class QuickSummary(BaseModel):
    """Resume rapide (points cles seulement)."""

    id: str
    judgment_id: str
    case_name: str
    citation: Optional[str]

    # Points cles
    key_facts: list[str] = Field(default_factory=list, max_length=5)
    main_issue: str
    holding: str
    key_takeaway: str = Field(..., description="A retenir")

    # Metadata
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)


class SummaryList(BaseModel):
    """Liste de resumes (pagination)."""

    items: list[CaseBrief]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
