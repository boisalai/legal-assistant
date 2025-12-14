"""
Session service for managing academic sessions.

Manages CRUD operations for academic sessions (ex: "Automne 2024", "Hiver 2025").
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from services.surreal_service import get_surreal_service
from models.session import Session, SessionCreate, SessionUpdate, SessionList

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing academic sessions."""

    def __init__(self):
        self.service = get_surreal_service()

    async def create_session(self, session_data: SessionCreate) -> Optional[Session]:
        """
        Create a new academic session.

        Args:
            session_data: Session creation data

        Returns:
            Created session if successful, None otherwise
        """
        try:
            # Convert Pydantic model to dict, keeping datetime objects
            # SurrealDB Python library will handle datetime conversion automatically
            data = session_data.model_dump()

            result = await self.service.create("session", data)

            if result:
                # Extract session from result
                if isinstance(result, dict):
                    # Convert RecordID to string
                    result["id"] = str(result["id"])
                    logger.info(f"Created session: {result.get('id')}")
                    return Session(**result)
                elif isinstance(result, list) and len(result) > 0:
                    # Convert RecordID to string
                    result[0]["id"] = str(result[0]["id"])
                    logger.info(f"Created session: {result[0].get('id')}")
                    return Session(**result[0])

            return None

        except Exception as e:
            logger.error(f"Failed to create session: {e}", exc_info=True)
            return None

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID (with or without "session:" prefix)

        Returns:
            Session if found, None otherwise
        """
        try:
            # Normalize session_id
            if not session_id.startswith("session:"):
                session_id = f"session:{session_id}"

            # Extract record ID
            record_id = session_id.replace("session:", "")

            query = "SELECT * FROM session WHERE id = type::thing('session', $record_id)"
            result = await self.service.query(query, {"record_id": record_id})

            if result and len(result) > 0:
                first_item = result[0]
                session_data = None

                if isinstance(first_item, dict):
                    if "result" in first_item and first_item["result"]:
                        session_data = first_item["result"][0] if isinstance(first_item["result"], list) and len(first_item["result"]) > 0 else None
                    elif "id" in first_item:
                        session_data = first_item

                if session_data:
                    # Convert RecordID to string
                    session_data["id"] = str(session_data["id"])
                    return Session(**session_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
            return None

    async def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        year: Optional[int] = None
    ) -> SessionList:
        """
        List all sessions with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of sessions per page
            year: Optional year filter

        Returns:
            SessionList with sessions and pagination info
        """
        try:
            # Build query
            offset = (page - 1) * page_size

            if year:
                query = f"""
                    SELECT * FROM session
                    WHERE year = {year}
                    ORDER BY year DESC, semester
                    LIMIT {page_size}
                    START {offset}
                """
            else:
                query = f"""
                    SELECT * FROM session
                    ORDER BY year DESC, semester
                    LIMIT {page_size}
                    START {offset}
                """

            result = await self.service.query(query)

            sessions = []
            if result and len(result) > 0:
                first_item = result[0]
                raw_sessions = []

                if isinstance(first_item, dict):
                    if "result" in first_item:
                        raw_sessions = first_item["result"] if isinstance(first_item["result"], list) else []
                    elif "id" in first_item:
                        # Direct list of sessions
                        raw_sessions = result
                elif isinstance(first_item, list):
                    raw_sessions = first_item
                else:
                    raw_sessions = result

                # Convert RecordID to string and create Session objects
                for s in raw_sessions:
                    if isinstance(s, dict):
                        s["id"] = str(s["id"])
                        sessions.append(Session(**s))

            # Get total count
            count_query = "SELECT count() FROM session GROUP ALL"
            if year:
                count_query = f"SELECT count() FROM session WHERE year = {year} GROUP ALL"

            count_result = await self.service.query(count_query)
            total = 0
            if count_result and len(count_result) > 0:
                count_data = count_result[0].get("result", [])
                if count_data and len(count_data) > 0:
                    total = count_data[0].get("count", 0)

            has_more = (offset + len(sessions)) < total

            return SessionList(
                items=sessions,
                total=total,
                page=page,
                page_size=page_size,
                has_more=has_more
            )

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}", exc_info=True)
            return SessionList(items=[], total=0, page=page, page_size=page_size)

    async def update_session(
        self,
        session_id: str,
        session_data: SessionUpdate
    ) -> Optional[Session]:
        """
        Update an existing session.

        Args:
            session_id: Session ID (with or without "session:" prefix)
            session_data: Session update data

        Returns:
            Updated session if successful, None otherwise
        """
        try:
            # Normalize session_id
            if not session_id.startswith("session:"):
                session_id = f"session:{session_id}"

            # Convert Pydantic model to dict, excluding unset fields
            data = session_data.model_dump(exclude_unset=True)

            # Convert datetime to ISO format if present
            if "start_date" in data:
                data["start_date"] = data["start_date"].isoformat()
            if "end_date" in data:
                data["end_date"] = data["end_date"].isoformat()

            # Update updated_at timestamp
            data["updated_at"] = datetime.now().isoformat()

            result = await self.service.update(session_id, data)

            if result:
                logger.info(f"Updated session: {session_id}")
                return Session(**result)

            return None

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}", exc_info=True)
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID (with or without "session:" prefix)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Normalize session_id
            if not session_id.startswith("session:"):
                session_id = f"session:{session_id}"

            # Check if session has courses
            query = f"SELECT count() FROM case WHERE session_id = {session_id} GROUP ALL"
            result = await self.service.query(query)

            count = 0
            if result and len(result) > 0:
                count_data = result[0].get("result", [])
                if count_data and len(count_data) > 0:
                    count = count_data[0].get("count", 0)

            if count > 0:
                logger.warning(f"Cannot delete session {session_id}: has {count} courses")
                raise ValueError(f"Cannot delete session: {count} courses are linked to this session")

            await self.service.delete(session_id)
            logger.info(f"Deleted session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
            return False

    async def get_session_courses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all courses in a session.

        Args:
            session_id: Session ID (with or without "session:" prefix)

        Returns:
            List of courses
        """
        try:
            # Normalize session_id
            if not session_id.startswith("session:"):
                session_id = f"session:{session_id}"

            query = f"""
                SELECT * FROM case
                WHERE session_id = '{session_id}'
                ORDER BY course_code
            """

            result = await self.service.query(query)

            courses = []
            if result and len(result) > 0:
                first_item = result[0]

                if isinstance(first_item, dict):
                    if "result" in first_item:
                        courses = first_item["result"] if isinstance(first_item["result"], list) else []
                    elif "id" in first_item:
                        courses = result
                elif isinstance(first_item, list):
                    courses = first_item
                else:
                    courses = result

                # Convert RecordID to string for each course
                for course in courses:
                    if isinstance(course, dict) and "id" in course:
                        course["id"] = str(course["id"])
                        if "session_id" in course:
                            course["session_id"] = str(course["session_id"])

                logger.info(f"Found {len(courses)} courses for session {session_id}")

            return courses

        except Exception as e:
            logger.error(f"Failed to get courses for session {session_id}: {e}", exc_info=True)
            return []


# Singleton instance
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Get or create the session service singleton."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
