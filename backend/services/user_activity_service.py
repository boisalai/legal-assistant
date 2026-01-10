"""
User activity tracking service.

Tracks user actions to provide contextual awareness to the AI agent.
Maintains a rolling window of the N most recent activities per course.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


class ActivityType(str, Enum):
    """Types of user activities that can be tracked."""
    # Navigation
    VIEW_CASE = "view_case"
    VIEW_DOCUMENT = "view_document"
    CLOSE_DOCUMENT = "close_document"
    VIEW_MODULE = "view_module"
    CLOSE_MODULE = "close_module"
    VIEW_FLASHCARD_STUDY = "view_flashcard_study"
    VIEW_FLASHCARD_AUDIO = "view_flashcard_audio"
    VIEW_DIRECTORY = "view_directory"

    # Communication
    SEND_MESSAGE = "send_message"

    # File management
    UPLOAD_DOCUMENT = "upload_document"
    DELETE_DOCUMENT = "delete_document"
    LINK_FILE = "link_file"

    # Processing
    TRANSCRIBE_AUDIO = "transcribe_audio"
    EXTRACT_PDF = "extract_pdf"
    GENERATE_TTS = "generate_tts"

    # Search
    SEARCH_DOCUMENTS = "search_documents"
    SEMANTIC_SEARCH = "semantic_search"


class UserActivityService:
    """Service for tracking and retrieving user activities."""

    def __init__(self, max_activities: int = 50):
        """
        Initialize the user activity service.

        Args:
            max_activities: Maximum number of activities to keep per course (default: 50)
        """
        self.service = get_surreal_service()
        self.max_activities = max_activities

    async def track_activity(
        self,
        course_id: str,
        action_type: ActivityType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Track a user activity.

        Args:
            course_id: ID of the course
            action_type: Type of activity (from ActivityType enum)
            metadata: Additional context about the activity

        Returns:
            Activity ID if successful, None otherwise
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            activity_data = {
                "course_id": course_id,
                "action_type": action_type.value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            result = await self.service.create("user_activity", activity_data)

            activity_id = None
            if result:
                if isinstance(result, dict) and "id" in result:
                    activity_id = result["id"]
                elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                    activity_id = result[0].get("id")

            if activity_id:
                logger.debug(f"Tracked activity: {action_type.value} for course {course_id}")

                # Clean up old activities asynchronously (keep only max_activities)
                await self._cleanup_old_activities(course_id)

                return activity_id

            return None

        except Exception as e:
            logger.error(f"Failed to track activity: {e}", exc_info=True)
            return None

    async def get_recent_activities(
        self,
        course_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities for a course.

        Args:
            course_id: ID of the course
            limit: Maximum number of activities to retrieve (default: max_activities)

        Returns:
            List of activity dicts ordered by timestamp (newest first)
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            if limit is None:
                limit = self.max_activities

            result = await self.service.query(
                """
                SELECT * FROM user_activity
                WHERE course_id = $course_id
                ORDER BY timestamp DESC
                LIMIT $limit
                """,
                {
                    "course_id": course_id,
                    "limit": limit
                }
            )

            activities = []
            if result and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict):
                    if "result" in first_item:
                        activities = first_item["result"] if isinstance(first_item["result"], list) else []
                    elif "id" in first_item or "action_type" in first_item:
                        activities = result
                elif isinstance(first_item, list):
                    activities = first_item

            logger.debug(f"Retrieved {len(activities)} activities for {course_id}")
            return activities

        except Exception as e:
            logger.error(f"Failed to get recent activities: {e}", exc_info=True)
            return []

    async def get_activity_context(
        self,
        course_id: str,
        limit: Optional[int] = None
    ) -> str:
        """
        Get a formatted context summary of recent user activities for the AI agent.

        Args:
            course_id: ID of the course
            limit: Maximum number of activities to include (default: max_activities)

        Returns:
            Formatted context string ready for inclusion in the AI prompt
        """
        try:
            activities = await self.get_recent_activities(course_id, limit)

            if not activities:
                return ""

            # Build context string
            context = "\n📍 Contexte d'activité utilisateur (chronologie récente):\n"

            # Reverse to show oldest first (chronological order)
            activities_chronological = list(reversed(activities))

            for i, activity in enumerate(activities_chronological, 1):
                timestamp = activity.get("timestamp", "")
                action_type = activity.get("action_type", "unknown")
                metadata = activity.get("metadata", {})

                # Format timestamp (show only time if same day)
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp

                # Build activity description
                description = self._format_activity_description(action_type, metadata)

                context += f"{i}. [{time_str}] {description}\n"

            # Add inference hint
            context += "\n=> Utilisez ce contexte pour mieux comprendre les intentions de l'utilisateur.\n"
            context += "   Par exemple, si l'utilisateur a récemment ouvert un document et pose une question,\n"
            context += "   il est probable qu'il parle de ce document.\n"

            return context

        except Exception as e:
            logger.error(f"Failed to get activity context: {e}", exc_info=True)
            return ""

    def _format_activity_description(self, action_type: str, metadata: Dict[str, Any]) -> str:
        """
        Format an activity description for human readability.

        Args:
            action_type: Type of activity
            metadata: Activity metadata

        Returns:
            Human-readable description
        """
        # Map action types to French descriptions
        action_labels = {
            "view_case": "Consultation du cours",
            "view_document": "Visualisation du document",
            "close_document": "Fermeture du document",
            "view_module": "Consultation du module",
            "close_module": "Fermeture du module",
            "view_flashcard_study": "Étude des fiches de révision",
            "view_flashcard_audio": "Écoute audio des fiches",
            "view_directory": "Consultation du répertoire",
            "send_message": "Message envoyé",
            "upload_document": "Upload de document",
            "delete_document": "Suppression du document",
            "link_file": "Liaison de fichier",
            "transcribe_audio": "Transcription audio",
            "extract_pdf": "Extraction PDF",
            "generate_tts": "Génération audio (TTS)",
            "search_documents": "Recherche par mots-clés",
            "semantic_search": "Recherche sémantique",
        }

        base_label = action_labels.get(action_type, action_type)

        # Add context from metadata
        if metadata:
            if "document_name" in metadata:
                return f"{base_label} '{metadata['document_name']}'"
            elif "document_id" in metadata:
                return f"{base_label} (ID: {metadata['document_id']})"
            elif "deck_name" in metadata:
                return f"{base_label} '{metadata['deck_name']}'"
            elif "module_name" in metadata:
                return f"{base_label} '{metadata['module_name']}'"
            elif "directory_path" in metadata:
                return f"{base_label} '{metadata['directory_path']}'"
            elif "course_name" in metadata:
                return f"{base_label} '{metadata['course_name']}'"
            elif "message" in metadata:
                # Truncate long messages
                msg = metadata["message"]
                if len(msg) > 100:
                    msg = msg[:100] + "..."
                return f"{base_label}: \"{msg}\""
            elif "query" in metadata:
                query = metadata["query"]
                if len(query) > 100:
                    query = query[:100] + "..."
                return f"{base_label}: \"{query}\""

        return base_label

    async def clear_activities(self, course_id: str) -> bool:
        """
        Clear all activities for a course.

        Args:
            course_id: ID of the course

        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            await self.service.query(
                "DELETE FROM user_activity WHERE course_id = $course_id",
                {"course_id": course_id}
            )

            logger.info(f"Cleared all activities for {course_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear activities: {e}", exc_info=True)
            return False

    async def _cleanup_old_activities(self, course_id: str):
        """
        Clean up old activities to maintain the rolling window.
        Keeps only the most recent max_activities entries.

        Args:
            course_id: ID of the course
        """
        try:
            # Get count of activities
            result = await self.service.query(
                """
                SELECT count() as total FROM user_activity
                WHERE course_id = $course_id
                """,
                {"course_id": course_id}
            )

            total = 0
            if result and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict):
                    if "result" in first_item and isinstance(first_item["result"], list):
                        stats = first_item["result"][0] if first_item["result"] else {}
                        total = stats.get("total", 0)
                    else:
                        total = first_item.get("total", 0)

            # If we have more than max_activities, delete the oldest ones
            if total > self.max_activities:
                # Get IDs of activities to delete (oldest ones beyond the limit)
                to_delete = total - self.max_activities

                delete_result = await self.service.query(
                    """
                    DELETE FROM user_activity
                    WHERE course_id = $course_id
                    ORDER BY timestamp ASC
                    LIMIT $to_delete
                    """,
                    {
                        "course_id": course_id,
                        "to_delete": to_delete
                    }
                )

                logger.debug(f"Cleaned up {to_delete} old activities for {course_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup old activities: {e}", exc_info=True)


# Singleton instance
_activity_service: Optional[UserActivityService] = None


def get_activity_service() -> UserActivityService:
    """Get the global user activity service instance."""
    global _activity_service
    if _activity_service is None:
        _activity_service = UserActivityService(max_activities=50)
    return _activity_service
