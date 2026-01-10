"""
Conversation memory service.

Manages conversation history storage and retrieval in SurrealDB.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history."""

    def __init__(self):
        self.service = get_surreal_service()

    async def save_message(
        self,
        course_id: str,
        role: str,
        content: str,
        model_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Save a message to the conversation history.

        Args:
            course_id: ID of the course
            role: Message role ("user" or "assistant")
            content: Message content
            model_id: Model used (for assistant messages)
            metadata: Additional metadata (tools used, sources, etc.)

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            message_data = {
                "course_id": course_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if model_id:
                message_data["model_id"] = model_id

            if metadata:
                message_data["metadata"] = metadata

            result = await self.service.create("conversation", message_data)

            if result:
                # Extract ID from result
                if isinstance(result, dict) and "id" in result:
                    logger.info(f"Saved message to conversation: {result['id']}")
                    return result["id"]
                elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                    logger.info(f"Saved message to conversation: {result[0].get('id')}")
                    return result[0].get("id")

            return None

        except Exception as e:
            logger.error(f"Failed to save conversation message: {e}", exc_info=True)
            return None

    async def get_conversation_history(
        self,
        course_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a course.

        Args:
            course_id: ID of the course
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            List of message dicts ordered by timestamp (oldest first)
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Query conversation messages
            result = await self.service.query(
                """
                SELECT * FROM conversation
                WHERE course_id = $course_id
                ORDER BY timestamp ASC
                LIMIT $limit
                START $offset
                """,
                {
                    "course_id": course_id,
                    "limit": limit,
                    "offset": offset
                }
            )

            messages = []
            if result and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict):
                    if "result" in first_item:
                        messages = first_item["result"] if isinstance(first_item["result"], list) else []
                    elif "id" in first_item or "role" in first_item:
                        messages = result
                elif isinstance(first_item, list):
                    messages = first_item

            logger.info(f"Retrieved {len(messages)} messages for {course_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}", exc_info=True)
            return []

    async def get_recent_context(
        self,
        course_id: str,
        max_messages: int = 10
    ) -> str:
        """
        Get recent conversation history formatted as context for the AI.

        Args:
            course_id: ID of the course
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted conversation context string
        """
        try:
            messages = await self.get_conversation_history(course_id, limit=max_messages)

            if not messages:
                return ""

            context = "Historique de conversation récent:\n\n"

            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")

                role_name = "Utilisateur" if role == "user" else "Assistant"
                context += f"{role_name}: {content}\n\n"

            return context

        except Exception as e:
            logger.error(f"Failed to get recent context: {e}", exc_info=True)
            return ""

    async def clear_conversation(self, course_id: str) -> bool:
        """
        Clear all conversation history for a course.

        Args:
            course_id: ID of the course

        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Delete all messages for this course
            await self.service.query(
                "DELETE FROM conversation WHERE course_id = $course_id",
                {"course_id": course_id}
            )

            logger.info(f"Cleared conversation history for {course_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}", exc_info=True)
            return False

    async def get_conversation_stats(self, course_id: str) -> Dict[str, Any]:
        """
        Get statistics about the conversation history.

        Args:
            course_id: ID of the course

        Returns:
            Dict with stats (message_count, first_message_time, last_message_time)
        """
        try:
            # Normalize course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Query stats
            result = await self.service.query(
                """
                SELECT
                    count() as message_count,
                    min(timestamp) as first_message_time,
                    max(timestamp) as last_message_time
                FROM conversation
                WHERE course_id = $course_id
                GROUP BY course_id
                """,
                {"course_id": course_id}
            )

            if result and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict):
                    if "result" in first_item and isinstance(first_item["result"], list):
                        stats = first_item["result"][0] if first_item["result"] else {}
                    else:
                        stats = first_item
                    return stats

            return {"message_count": 0}

        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}", exc_info=True)
            return {"message_count": 0}


# Singleton instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get the global conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
