"""Utilitaires pour la gestion des fichiers."""

import hashlib
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Allowed file types
ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.mdx': 'text/markdown',  # MDX (Markdown + JSX)
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.webm': 'audio/webm',
}

# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.webm'}

# Types de fichiers supportés pour les liens (fichiers/répertoires)
LINKABLE_EXTENSIONS = {'.md', '.mdx', '.pdf', '.txt', '.docx'}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB - Pour supporter les enregistrements audio de 3h+
MAX_LINKED_FILES = 50  # Limite de fichiers lors de la liaison d'un répertoire


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        SHA-256 hash as hexadecimal string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.

    Args:
        filename: Name or path of the file

    Returns:
        File extension in lowercase (e.g., '.pdf')
    """
    return Path(filename).suffix.lower()


def is_allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed.

    Args:
        filename: Name or path of the file

    Returns:
        True if file extension is in ALLOWED_EXTENSIONS
    """
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def get_mime_type(filename: str) -> str:
    """
    Get MIME type from filename.

    Args:
        filename: Name or path of the file

    Returns:
        MIME type string (e.g., 'application/pdf')
    """
    ext = get_file_extension(filename)
    return ALLOWED_EXTENSIONS.get(ext, 'application/octet-stream')


def is_audio_file(filename: str) -> bool:
    """
    Check if file is an audio file.

    Args:
        filename: Name or path of the file

    Returns:
        True if file extension is in AUDIO_EXTENSIONS
    """
    ext = get_file_extension(filename)
    return ext in AUDIO_EXTENSIONS


def is_linkable_file(filename: str) -> bool:
    """
    Check if file can be linked (for folder linking).

    Args:
        filename: Name or path of the file

    Returns:
        True if file extension is in LINKABLE_EXTENSIONS
    """
    ext = get_file_extension(filename)
    return ext in LINKABLE_EXTENSIONS


def scan_folder_for_files(folder_path: Path, max_files: int = MAX_LINKED_FILES) -> List[Path]:
    """
    Scan a folder for linkable files (non-recursive).

    Args:
        folder_path: Path to the folder to scan
        max_files: Maximum number of files to return

    Returns:
        List of file paths, limited to max_files, sorted by name.
        Filters by LINKABLE_EXTENSIONS.
    """
    files = []

    try:
        for item in folder_path.iterdir():
            if len(files) >= max_files:
                break

            # Skip hidden files and directories
            if item.name.startswith('.'):
                continue

            # Only process files (not subdirectories)
            if item.is_file() and is_linkable_file(item.name):
                files.append(item)
    except Exception as e:
        logger.error(f"Error scanning folder {folder_path}: {e}")

    return sorted(files, key=lambda p: p.name)
