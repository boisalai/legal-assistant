"""
Modèles Pydantic pour l'interface d'administration de la base de données.

Ce module contient les modèles de données utilisés par les endpoints admin
pour la consultation des tables et la gestion des orphelins.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class TableInfo(BaseModel):
    """Informations sur une table SurrealDB."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(..., description="Nom de la table dans SurrealDB")
    display_name: str = Field(..., description="Nom d'affichage pour l'UI")
    row_count: int = Field(..., description="Nombre de lignes dans la table")
    estimated_size_mb: Optional[float] = Field(
        None,
        description="Taille estimée en MB (optionnel)"
    )
    has_orphans: bool = Field(
        default=False,
        description="Indique si la table a des orphelins détectés"
    )


class TableDataResponse(BaseModel):
    """Réponse paginée pour les données d'une table."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    table_name: str = Field(..., description="Nom de la table")
    rows: List[Dict[str, Any]] = Field(..., description="Lignes de données")
    total: int = Field(..., description="Nombre total de lignes")
    skip: int = Field(..., description="Offset de pagination")
    limit: int = Field(..., description="Nombre de lignes par page")


class TableSchema(BaseModel):
    """Schéma d'une table SurrealDB."""
    table_name: str = Field(..., description="Nom de la table")
    fields: List["FieldInfo"] = Field(..., description="Liste des champs")
    indexes: List["IndexInfo"] = Field(..., description="Liste des index")


class FieldInfo(BaseModel):
    """Information sur un champ de table."""
    name: str = Field(..., description="Nom du champ")
    type: str = Field(..., description="Type du champ")
    optional: bool = Field(default=True, description="Champ optionnel")
    default: Optional[Any] = Field(None, description="Valeur par défaut")


class IndexInfo(BaseModel):
    """Information sur un index de table."""
    name: str = Field(..., description="Nom de l'index")
    fields: List[str] = Field(..., description="Champs indexés")


class OrphanTypeInfo(BaseModel):
    """Information sur un type d'orphelin détectable."""
    id: str = Field(..., description="ID unique du type d'orphelin")
    table_name: str = Field(..., description="Table concernée")
    description: str = Field(..., description="Description du problème")
    risk_level: str = Field(
        ...,
        description="Niveau de risque: 'high', 'medium', 'low'"
    )


class OrphanAnalysisResult(BaseModel):
    """Résultat de l'analyse des orphelins."""
    total_orphans: int = Field(..., description="Nombre total d'orphelins")
    orphans_by_table: Dict[str, int] = Field(
        ...,
        description="Nombre d'orphelins par table"
    )
    preview_samples: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="Échantillons d'orphelins (premiers 10 par table)"
    )
    analysis_timestamp: str = Field(..., description="Horodatage de l'analyse")
    safe_to_clean: bool = Field(
        ...,
        description="Indique si le nettoyage est sûr"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Avertissements éventuels"
    )


class OrphanCleanupResult(BaseModel):
    """Résultat du nettoyage d'orphelins."""
    success: bool = Field(..., description="Succès de l'opération")
    deleted_by_table: Dict[str, int] = Field(
        ...,
        description="Nombre de suppressions par table"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Erreurs rencontrées"
    )
    duration_seconds: float = Field(..., description="Durée de l'opération")


class DatabaseStats(BaseModel):
    """Statistiques globales de la base de données."""
    total_tables: int = Field(..., description="Nombre total de tables")
    total_rows: int = Field(..., description="Nombre total de lignes")
    estimated_size_mb: float = Field(..., description="Taille estimée en MB")
    tables: Dict[str, "TableStats"] = Field(
        ...,
        description="Statistiques par table"
    )


class TableStats(BaseModel):
    """Statistiques d'une table."""
    row_count: int = Field(..., description="Nombre de lignes")
    orphan_count: int = Field(
        default=0,
        description="Nombre d'orphelins détectés"
    )
    size_mb: Optional[float] = Field(None, description="Taille en MB")


# Mise à jour des forward references pour les modèles récursifs
TableSchema.model_rebuild()
DatabaseStats.model_rebuild()
