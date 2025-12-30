"""
Utilitaires pour la gestion des répertoires liés.

Ce module contient les fonctions de scan et d'extraction partagées entre :
- routes/linked_directory.py (endpoints API)
- services/auto_sync_service.py (synchronisation automatique)
"""

import json
import logging
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel

from utils.file_utils import LINKABLE_EXTENSIONS

logger = logging.getLogger(__name__)

# Alias pour compatibilité
SUPPORTED_EXTENSIONS = LINKABLE_EXTENSIONS


class FileInfo(BaseModel):
    """Information sur un fichier trouvé."""

    absolute_path: str
    relative_path: str
    filename: str
    size: int
    modified_time: float
    extension: str
    parent_folder: str  # Chemin relatif du dossier parent


class DirectoryScanResult(BaseModel):
    """Résultat du scan d'un répertoire."""

    base_path: str
    total_files: int
    total_size: int
    files_by_type: Dict[str, int]  # ex: {"pdf": 5, "md": 12, ...}
    files: List[FileInfo]
    folder_structure: Dict[str, int]  # ex: {"contrats/": 5, "jurisprudence/2024/": 8}


def normalize_linked_source(linked_source) -> dict:
    """
    Normalise linked_source qui peut être une chaîne JSON ou un dict.

    Args:
        linked_source: Peut être un dict, une chaîne JSON, ou None

    Returns:
        Un dictionnaire Python
    """
    if linked_source is None:
        return {}
    if isinstance(linked_source, str):
        try:
            return json.loads(linked_source)
        except json.JSONDecodeError:
            logger.warning(f"Impossible de parser linked_source: {linked_source}")
            return {}
    if isinstance(linked_source, dict):
        return linked_source
    return {}


def scan_directory(directory_path: str) -> DirectoryScanResult:
    """
    Scanne un répertoire et retourne les statistiques.

    Args:
        directory_path: Chemin du répertoire à scanner

    Returns:
        DirectoryScanResult avec les statistiques
    """
    # Normaliser le chemin en NFD (forme décomposée) pour macOS
    # macOS utilise NFD pour les noms de fichiers, mais les navigateurs envoient en NFC
    normalized_path = unicodedata.normalize("NFD", directory_path)
    base_path = Path(normalized_path)

    if not base_path.exists():
        raise ValueError(f"Le répertoire n'existe pas: {directory_path}")

    if not base_path.is_dir():
        raise ValueError(f"Le chemin n'est pas un répertoire: {directory_path}")

    files = []
    total_size = 0
    files_by_type = defaultdict(int)
    folder_structure = defaultdict(int)

    # Parcourir récursivement le répertoire
    for file_path in base_path.rglob("*"):
        # Ignorer les dossiers cachés et node_modules
        if any(
            part.startswith(".") or part == "node_modules" for part in file_path.parts
        ):
            continue

        # Ignorer les dossiers
        if file_path.is_dir():
            continue

        # Vérifier l'extension
        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            continue

        try:
            stat = file_path.stat()
            relative = file_path.relative_to(base_path)
            parent_folder = str(relative.parent) if str(relative.parent) != "." else "root"

            file_info = FileInfo(
                absolute_path=str(file_path),
                relative_path=str(relative),
                filename=file_path.name,
                size=stat.st_size,
                modified_time=stat.st_mtime,
                extension=extension.lstrip("."),
                parent_folder=parent_folder,
            )

            files.append(file_info)
            total_size += stat.st_size
            files_by_type[extension.lstrip(".")] += 1
            folder_structure[parent_folder] += 1

        except Exception as e:
            logger.warning(f"Erreur lors de la lecture du fichier {file_path}: {e}")

    # Trier les fichiers par chemin relatif
    files.sort(key=lambda f: f.relative_path)

    return DirectoryScanResult(
        base_path=str(base_path),
        total_files=len(files),
        total_size=total_size,
        files_by_type=dict(files_by_type),
        files=files,
        folder_structure=dict(folder_structure),
    )


def extract_text_from_file(file_path: Path) -> str:
    """
    Extrait le texte d'un fichier selon son type.

    Args:
        file_path: Chemin du fichier

    Returns:
        Contenu textuel du fichier
    """
    extension = file_path.suffix.lower()

    if extension in [".md", ".mdx", ".txt"]:
        # Fichiers texte : lecture directe
        return file_path.read_text(encoding="utf-8", errors="ignore")

    elif extension == ".pdf":
        # PDF : Pour l'instant, on retourne un placeholder
        # L'extraction PDF sera faite via docling dans un second temps
        return f"[Contenu PDF - {file_path.name}]"

    elif extension in [".docx", ".doc"]:
        # Word : Pour l'instant, on retourne un placeholder
        # L'extraction Word sera faite via python-docx dans un second temps
        return f"[Contenu Word - {file_path.name}]"

    else:
        return ""
