"""
Modèles Pydantic pour CAIJ (Centre d'accès à l'information juridique du Québec)
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import datetime
import re


def infer_rubrique(document_type: str, source: str, url: str) -> str:
    """
    Déduire la rubrique CAIJ à partir du type de document, de la source et de l'URL.

    Rubriques officielles CAIJ:
    - Législation
    - Jurisprudence
    - Doctrine en ligne
    - Catalogue de bibliothèque
    - Lois annotées
    - Questions de recherche documentées
    - Modèles et formulaires
    - Dictionnaires

    Args:
        document_type: Type de document extrait (ex: "Terme juridique défini", "Livres", etc.)
        source: Source du document (ex: "Dictionnaire de droit québécois...", "Revue du notariat", etc.)
        url: URL complète du document

    Returns:
        Rubrique CAIJ correspondante
    """
    doc_type_lower = document_type.lower()
    source_lower = source.lower()
    url_lower = url.lower()

    # Dictionnaires
    if "dictionnaire" in source_lower or "dictionnaire" in url_lower or "terme juridique" in doc_type_lower:
        return "Dictionnaires"

    # Lois annotées (AVANT Législation pour éviter confusion)
    if "annoté" in doc_type_lower or "annoté" in source_lower or "annotation" in doc_type_lower:
        return "Lois annotées"

    if "/lois-annotees" in url_lower:
        return "Lois annotées"

    # Doctrine en ligne (AVANT Jurisprudence pour éviter confusion avec "Cours")
    if any(keyword in doc_type_lower for keyword in [
        "périodique", "revue", "article", "doctrine",
        "congrès", "conférence", "colloque",
        "publication", "périodique et revue"
    ]):
        return "Doctrine en ligne"

    if any(keyword in source_lower for keyword in ["revue", "périodique", "doctrine", "congrès", "conférence"]):
        return "Doctrine en ligne"

    if "/doctrine" in url_lower:
        return "Doctrine en ligne"

    # Jurisprudence
    if any(keyword in doc_type_lower for keyword in ["jugement", "décision", "arrêt", "ordonnance"]):
        return "Jurisprudence"

    # Attention: vérifier que ce n'est pas "Cours" (formation) mais bien "Cour" (tribunal)
    if any(keyword in source_lower for keyword in ["cour d'", "cour ", "tribunal", "juge"]):
        return "Jurisprudence"

    if "/jurisprudence" in url_lower:
        return "Jurisprudence"

    # Législation
    if any(keyword in doc_type_lower for keyword in ["loi", "règlement", "code", "charte"]):
        return "Législation"

    if any(keyword in source_lower for keyword in ["loi", "règlement", "code", "éditeur officiel", "gazette"]):
        return "Législation"

    if "/legislation" in url_lower or "/lois" in url_lower:
        return "Législation"

    # Questions de recherche documentées
    if any(keyword in doc_type_lower for keyword in ["question", "recherche documentée", "q&a", "faq"]):
        return "Questions de recherche documentées"

    if "/questions-recherche" in url_lower:
        return "Questions de recherche documentées"

    # Modèles et formulaires
    if any(keyword in doc_type_lower for keyword in ["modèle", "formulaire", "gabarit", "template"]):
        return "Modèles et formulaires"

    if any(keyword in source_lower for keyword in ["modèle", "formulaire"]):
        return "Modèles et formulaires"

    if "/modeles-formulaires" in url_lower or "/formulaires" in url_lower:
        return "Modèles et formulaires"

    # Catalogue de bibliothèque
    if any(keyword in doc_type_lower for keyword in ["livre", "monographie", "ouvrage", "traité"]):
        return "Catalogue de bibliothèque"

    if "/catalogue" in url_lower or "/bibliotheque" in url_lower:
        return "Catalogue de bibliothèque"

    # Par défaut: essayer de déduire à partir de l'URL
    if "/dictionnaires" in url_lower:
        return "Dictionnaires"

    # Si aucune correspondance, retourner le type de document tel quel
    return document_type


class CAIJResult(BaseModel):
    """Résultat de recherche CAIJ."""

    title: str = Field(..., description="Titre du document juridique")
    url: str = Field(..., description="URL complète vers le document sur CAIJ")
    document_type: str = Field(..., description="Type de document (jurisprudence, doctrine, etc.)")
    rubrique: Optional[str] = Field(None, description="Rubrique CAIJ (Législation, Jurisprudence, Dictionnaires, etc.)")
    source: str = Field(..., description="Source du document (tribunal, revue, etc.)")
    date: str = Field(..., description="Date de publication ou du jugement")
    excerpt: str = Field(..., description="Extrait ou résumé du document")
    relevance_score: Optional[float] = Field(None, description="Score de pertinence (si disponible)")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Mariage",
                "url": "https://app.caij.qc.ca/fr/dictionnaires/dictionnaire-reid-6/Mariage",
                "document_type": "Terme juridique défini",
                "rubrique": "Dictionnaires",
                "source": "Dictionnaire de droit québécois et canadien",
                "date": "2024",
                "excerpt": "Mariage n.m. 1. Union légitime de deux personnes...",
                "relevance_score": None
            }
        }


class CAIJSearchRequest(BaseModel):
    """Requête de recherche CAIJ."""

    query: str = Field(..., description="Termes de recherche", min_length=1)
    max_results: int = Field(10, description="Nombre maximum de résultats", ge=1, le=50)
    filters: Optional[dict] = Field(None, description="Filtres avancés (type, date, tribunal, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "responsabilité civile",
                "max_results": 10,
                "filters": None
            }
        }


class CAIJSearchResponse(BaseModel):
    """Réponse de recherche CAIJ."""

    query: str = Field(..., description="Termes de recherche utilisés")
    results: List[CAIJResult] = Field(default_factory=list, description="Liste des résultats")
    total_found: int = Field(..., description="Nombre total de résultats trouvés")
    timestamp: datetime = Field(default_factory=datetime.now, description="Date/heure de la recherche")
    execution_time_seconds: Optional[float] = Field(None, description="Temps d'exécution en secondes")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "mariage",
                "results": [],
                "total_found": 25,
                "timestamp": "2025-12-23T16:00:00",
                "execution_time_seconds": 3.5
            }
        }


class CAIJCredentials(BaseModel):
    """Credentials CAIJ pour authentification."""

    email: str = Field(..., description="Email de connexion CAIJ")
    password: str = Field(..., description="Mot de passe CAIJ")

    class Config:
        # Ne jamais logger les credentials
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "********"
            }
        }
