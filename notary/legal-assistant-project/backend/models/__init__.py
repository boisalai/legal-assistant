"""Models module for Legal Assistant."""

from .judgment import (
    CourtLevel,
    Judgment,
    JudgmentBase,
    JudgmentCreate,
    JudgmentList,
    JudgmentStatus,
    JudgmentUpdate,
    JurisdictionType,
    LegalDomain,
)
from .summary import (
    AnalysisPoint,
    CaseBrief,
    CaseBriefCreate,
    CaseBriefUpdate,
    LegalIssue,
    LegalRule,
    Party,
    QuickSummary,
    SummaryList,
    SummaryStatus,
    SummaryType,
)

__all__ = [
    # Judgment models
    "Judgment",
    "JudgmentBase",
    "JudgmentCreate",
    "JudgmentUpdate",
    "JudgmentList",
    "JudgmentStatus",
    "JurisdictionType",
    "CourtLevel",
    "LegalDomain",
    # Summary models
    "CaseBrief",
    "CaseBriefCreate",
    "CaseBriefUpdate",
    "QuickSummary",
    "SummaryList",
    "SummaryStatus",
    "SummaryType",
    "Party",
    "LegalIssue",
    "LegalRule",
    "AnalysisPoint",
]
