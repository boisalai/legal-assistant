"""
Course service for managing academic courses.

Courses are stored in the "case" table with academic fields populated.
This service provides helper methods for academic-specific operations.
"""

import logging
from typing import List, Optional, Dict, Any

from services.surreal_service import get_surreal_service
from models.case import Case, CaseCreate, CaseUpdate

logger = logging.getLogger(__name__)


class CourseService:
    """Service for managing academic courses."""

    def __init__(self):
        self.service = get_surreal_service()

    async def get_courses_by_session(
        self,
        session_id: str,
        sort_by: str = "course_code"
    ) -> List[Case]:
        """
        Get all courses for a specific session.

        Args:
            session_id: Session ID (with or without "session:" prefix)
            sort_by: Field to sort by (course_code, course_name, created_at)

        Returns:
            List of courses
        """
        try:
            # Normalize session_id
            if not session_id.startswith("session:"):
                session_id = f"session:{session_id}"

            # Validate sort_by
            valid_sorts = ["course_code", "course_name", "created_at"]
            if sort_by not in valid_sorts:
                sort_by = "course_code"

            query = f"""
                SELECT * FROM case
                WHERE session_id = {session_id}
                ORDER BY {sort_by}
            """

            result = await self.service.query(query)

            courses = []
            if result and len(result) > 0:
                raw_courses = result[0].get("result", [])
                courses = [Case(**c) for c in raw_courses]

            logger.info(f"Found {len(courses)} courses for session {session_id}")
            return courses

        except Exception as e:
            logger.error(f"Failed to get courses for session {session_id}: {e}", exc_info=True)
            return []

    async def get_course_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for courses in a session.

        Args:
            session_id: Session ID (with or without "session:" prefix)

        Returns:
            Dict with course statistics
        """
        try:
            # Normalize session_id
            if not session_id.startswith("session:"):
                session_id = f"session:{session_id}"

            query = f"""
                SELECT
                    count() AS total_courses,
                    math::sum(credits) AS total_credits,
                    math::avg(credits) AS avg_credits,
                    math::min(credits) AS min_credits,
                    math::max(credits) AS max_credits
                FROM case
                WHERE session_id = {session_id}
                GROUP ALL
            """

            result = await self.service.query(query)

            stats = {
                "total_courses": 0,
                "total_credits": 0,
                "avg_credits": 0.0,
                "min_credits": 0,
                "max_credits": 0,
            }

            if result and len(result) > 0:
                raw_stats = result[0].get("result", [])
                if raw_stats and len(raw_stats) > 0:
                    stats_data = raw_stats[0]
                    stats["total_courses"] = stats_data.get("total_courses", 0)
                    stats["total_credits"] = stats_data.get("total_credits", 0) or 0
                    stats["avg_credits"] = stats_data.get("avg_credits", 0.0) or 0.0
                    stats["min_credits"] = stats_data.get("min_credits", 0) or 0
                    stats["max_credits"] = stats_data.get("max_credits", 0) or 0

            logger.info(f"Course stats for session {session_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get course stats for session {session_id}: {e}", exc_info=True)
            return {
                "total_courses": 0,
                "total_credits": 0,
                "avg_credits": 0.0,
                "min_credits": 0,
                "max_credits": 0,
            }

    async def check_course_code_exists(
        self,
        course_code: str,
        session_id: Optional[str] = None,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if a course code already exists.

        Args:
            course_code: Course code to check
            session_id: Optional session ID to scope the check
            exclude_id: Optional case ID to exclude (for updates)

        Returns:
            True if course code exists, False otherwise
        """
        try:
            # Build query
            conditions = [f"course_code = '{course_code}'"]

            if session_id:
                if not session_id.startswith("session:"):
                    session_id = f"session:{session_id}"
                conditions.append(f"session_id = {session_id}")

            if exclude_id:
                if not exclude_id.startswith("case:"):
                    exclude_id = f"case:{exclude_id}"
                conditions.append(f"id != {exclude_id}")

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT count() FROM case
                WHERE {where_clause}
                GROUP ALL
            """

            result = await self.service.query(query)

            if result and len(result) > 0:
                count_data = result[0].get("result", [])
                if count_data and len(count_data) > 0:
                    count = count_data[0].get("count", 0)
                    return count > 0

            return False

        except Exception as e:
            logger.error(f"Failed to check course code: {e}", exc_info=True)
            return False

    async def get_courses_by_professor(self, professor: str) -> List[Case]:
        """
        Get all courses taught by a specific professor.

        Args:
            professor: Professor name

        Returns:
            List of courses
        """
        try:
            query = f"""
                SELECT * FROM case
                WHERE professor = '{professor}'
                ORDER BY created_at DESC
            """

            result = await self.service.query(query)

            courses = []
            if result and len(result) > 0:
                raw_courses = result[0].get("result", [])
                courses = [Case(**c) for c in raw_courses]

            logger.info(f"Found {len(courses)} courses for professor '{professor}'")
            return courses

        except Exception as e:
            logger.error(f"Failed to get courses for professor '{professor}': {e}", exc_info=True)
            return []

    async def get_recent_courses(self, limit: int = 10) -> List[Case]:
        """
        Get recently created courses.

        Args:
            limit: Maximum number of courses to return

        Returns:
            List of recent courses
        """
        try:
            query = f"""
                SELECT * FROM case
                WHERE course_code IS NOT NONE
                ORDER BY created_at DESC
                LIMIT {limit}
            """

            result = await self.service.query(query)

            courses = []
            if result and len(result) > 0:
                raw_courses = result[0].get("result", [])
                courses = [Case(**c) for c in raw_courses]

            logger.info(f"Found {len(courses)} recent courses")
            return courses

        except Exception as e:
            logger.error(f"Failed to get recent courses: {e}", exc_info=True)
            return []


# Singleton instance
_course_service: Optional[CourseService] = None


def get_course_service() -> CourseService:
    """Get or create the course service singleton."""
    global _course_service
    if _course_service is None:
        _course_service = CourseService()
    return _course_service
