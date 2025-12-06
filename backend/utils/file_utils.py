"""Utilitaires pour la gestion des fichiers."""

from pathlib import Path

# Allowed file types
ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.webm': 'audio/webm',
}

# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.webm'}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB - Pour supporter les enregistrements audio de 3h+


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
