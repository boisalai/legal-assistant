"""
Service de gestion de la progression des analyses.

Ce service permet de:
- Enregistrer des listeners pour suivre la progression d'une analyse
- Émettre des événements de progression depuis le workflow
- Streamer les événements via SSE au frontend
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncIterator, Callable, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ProgressEventType(str, Enum):
    """Types d'événements de progression."""
    START = "start"           # Début de l'analyse
    STEP_START = "step_start" # Début d'une étape
    STEP_END = "step_end"     # Fin d'une étape
    PROGRESS = "progress"     # Progression intermédiaire
    COMPLETE = "complete"     # Analyse terminée
    ERROR = "error"           # Erreur
    HEARTBEAT = "heartbeat"   # Keep-alive pour maintenir la connexion SSE


@dataclass
class ProgressEvent:
    """Événement de progression."""
    event_type: ProgressEventType
    step: Optional[int] = None
    step_name: Optional[str] = None
    message: str = ""
    progress_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Convertit en JSON string (pour EventSourceResponse)."""
        data = {
            "type": self.event_type.value,
            "step": self.step,
            "stepName": self.step_name,
            "message": self.message,
            "progressPercent": self.progress_percent,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }
        return json.dumps(data)

    def to_sse(self) -> str:
        """Convertit en format SSE complet (avec 'data: ' prefix)."""
        return f"data: {self.to_json()}\n\n"


class ProgressManager:
    """
    Gestionnaire de progression pour les analyses.

    Utilise des queues asyncio pour permettre la communication
    entre le workflow et les endpoints SSE.
    """

    def __init__(self):
        # Queues par dossier_id pour les événements
        self._queues: dict[str, list[asyncio.Queue]] = {}
        # État actuel par dossier_id
        self._current_state: dict[str, ProgressEvent] = {}
        # Lock pour thread-safety
        self._lock = asyncio.Lock()

    async def subscribe(self, dossier_id: str, heartbeat_interval: float = 2.0) -> AsyncIterator[ProgressEvent]:
        """
        S'abonne aux événements de progression d'un dossier.

        Envoie des heartbeats périodiques pour garder la connexion SSE ouverte.

        Args:
            dossier_id: ID du dossier
            heartbeat_interval: Intervalle entre les heartbeats (secondes)

        Yields:
            ProgressEvent à chaque nouvel événement ou heartbeat
        """
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            if dossier_id not in self._queues:
                self._queues[dossier_id] = []
            self._queues[dossier_id].append(queue)

            # Envoyer l'état actuel si disponible
            if dossier_id in self._current_state:
                await queue.put(self._current_state[dossier_id])

        try:
            while True:
                try:
                    # Attendre un événement avec timeout
                    event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                    yield event

                    # Si l'événement est terminal, arrêter
                    if event.event_type in (ProgressEventType.COMPLETE, ProgressEventType.ERROR):
                        break
                except asyncio.TimeoutError:
                    # Pas d'événement reçu, envoyer un heartbeat
                    heartbeat = ProgressEvent(
                        event_type=ProgressEventType.HEARTBEAT,
                        message="heartbeat",
                        progress_percent=0.0,
                    )
                    yield heartbeat
        finally:
            async with self._lock:
                if dossier_id in self._queues and queue in self._queues[dossier_id]:
                    self._queues[dossier_id].remove(queue)

    async def emit(self, dossier_id: str, event: ProgressEvent):
        """
        Émet un événement de progression.

        Args:
            dossier_id: ID du dossier concerné
            event: Événement à émettre
        """
        async with self._lock:
            # Sauvegarder l'état actuel
            self._current_state[dossier_id] = event

            # Envoyer à tous les subscribers
            if dossier_id in self._queues:
                for queue in self._queues[dossier_id]:
                    try:
                        await queue.put(event)
                    except Exception as e:
                        logger.warning(f"Failed to send event to queue: {e}")

        logger.debug(f"Progress event emitted: {event.event_type.value} - {event.message}")

    async def clear(self, dossier_id: str):
        """Nettoie l'état d'un dossier."""
        async with self._lock:
            if dossier_id in self._current_state:
                del self._current_state[dossier_id]
            if dossier_id in self._queues:
                del self._queues[dossier_id]

    def create_callback(self, dossier_id: str) -> Callable:
        """
        Crée une callback de progression pour le workflow.

        Args:
            dossier_id: ID du dossier

        Returns:
            Fonction callback async pour émettre des événements
        """
        async def progress_callback(
            step: int,
            step_name: str,
            event_type: str = "step_start",
            message: str = "",
            progress_percent: float = 0.0,
            data: dict = None,
        ):
            """Callback appelée par le workflow pour signaler la progression."""
            event = ProgressEvent(
                event_type=ProgressEventType(event_type),
                step=step,
                step_name=step_name,
                message=message or f"Étape {step}: {step_name}",
                progress_percent=progress_percent,
                data=data or {},
            )
            await self.emit(dossier_id, event)

        return progress_callback


# Instance globale singleton
_progress_manager: Optional[ProgressManager] = None


def get_progress_manager() -> ProgressManager:
    """Retourne l'instance singleton du ProgressManager."""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager
