"""
Service pour télécharger l'audio de vidéos YouTube.

Utilise yt-dlp pour extraire l'audio en MP3.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Vérifier si yt-dlp est disponible
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    logger.warning("yt-dlp non disponible. Installer avec: uv add yt-dlp")


@dataclass
class VideoInfo:
    """Informations sur une vidéo YouTube."""
    title: str
    duration: int  # secondes
    uploader: str
    thumbnail: str
    url: str


@dataclass
class DownloadResult:
    """Résultat du téléchargement."""
    success: bool
    file_path: str = ""
    filename: str = ""
    title: str = ""
    duration: int = 0
    error: str = ""


class YouTubeService:
    """Service pour télécharger l'audio de vidéos YouTube."""

    # Regex pour valider les URLs YouTube
    YOUTUBE_REGEX = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+',
        re.IGNORECASE
    )

    def __init__(self):
        if not YTDLP_AVAILABLE:
            raise RuntimeError("yt-dlp n'est pas installé. Exécuter: uv add yt-dlp")

    def is_valid_youtube_url(self, url: str) -> bool:
        """Vérifie si l'URL est une URL YouTube valide."""
        return bool(self.YOUTUBE_REGEX.match(url))

    async def get_video_info(self, url: str) -> VideoInfo:
        """Récupère les informations d'une vidéo sans la télécharger."""
        if not self.is_valid_youtube_url(url):
            raise ValueError("URL YouTube invalide")

        def _extract_info():
            options = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                return VideoInfo(
                    title=info.get('title', 'Sans titre'),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', 'Inconnu'),
                    thumbnail=info.get('thumbnail', ''),
                    url=url,
                )

        return await asyncio.to_thread(_extract_info)

    async def download_audio(
        self,
        url: str,
        output_dir: str,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> DownloadResult:
        """
        Télécharge l'audio d'une vidéo YouTube en MP3.

        Args:
            url: URL de la vidéo YouTube
            output_dir: Répertoire de destination
            on_progress: Callback de progression (pourcentage, message)

        Returns:
            DownloadResult avec le chemin du fichier téléchargé
        """
        if not self.is_valid_youtube_url(url):
            return DownloadResult(success=False, error="URL YouTube invalide")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Variables pour capturer le résultat
        result_info = {}
        downloaded_file = None

        def progress_hook(d):
            nonlocal downloaded_file
            if d['status'] == 'downloading':
                if on_progress and 'total_bytes' in d and d['total_bytes']:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    on_progress(percent, f"Téléchargement: {percent:.1f}%")
                elif on_progress and 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                    on_progress(percent, f"Téléchargement: {percent:.1f}%")
            elif d['status'] == 'finished':
                if on_progress:
                    on_progress(100, "Conversion en MP3...")
                # Le fichier final sera .mp3 après postprocessing
                downloaded_file = d.get('filename', '')

        def postprocessor_hook(d):
            nonlocal downloaded_file
            if d['status'] == 'finished':
                # Récupérer le chemin du fichier après conversion
                if 'info_dict' in d and 'filepath' in d['info_dict']:
                    downloaded_file = d['info_dict']['filepath']

        def _download():
            nonlocal result_info, downloaded_file

            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'postprocessor_hooks': [postprocessor_hook],
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                result_info = {
                    'title': info.get('title', 'Sans titre'),
                    'duration': info.get('duration', 0),
                }
                # Construire le chemin final du fichier MP3
                if not downloaded_file or not Path(downloaded_file).exists():
                    # Fallback: chercher le fichier mp3 par titre
                    title = info.get('title', 'download')
                    # Nettoyer le titre pour le nom de fichier
                    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                    downloaded_file = str(output_path / f"{safe_title}.mp3")

        try:
            await asyncio.to_thread(_download)

            # Vérifier que le fichier existe
            if downloaded_file and Path(downloaded_file).exists():
                final_path = Path(downloaded_file)
            else:
                # Chercher le fichier mp3 le plus récent dans le répertoire
                mp3_files = list(output_path.glob("*.mp3"))
                if mp3_files:
                    final_path = max(mp3_files, key=lambda p: p.stat().st_mtime)
                else:
                    return DownloadResult(
                        success=False,
                        error="Fichier MP3 non trouvé après téléchargement"
                    )

            logger.info(f"Audio téléchargé: {final_path}")

            return DownloadResult(
                success=True,
                file_path=str(final_path.absolute()),
                filename=final_path.name,
                title=result_info.get('title', final_path.stem),
                duration=result_info.get('duration', 0),
            )

        except Exception as e:
            logger.error(f"Erreur téléchargement YouTube: {e}", exc_info=True)
            return DownloadResult(success=False, error=str(e))


# Singleton
_youtube_service: Optional[YouTubeService] = None


def get_youtube_service() -> YouTubeService:
    """Récupère l'instance du service YouTube."""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service
