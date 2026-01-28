"""
Course service for managing academic courses.

Courses are stored in the "course" table with academic fields populated.
This service provides helper methods for academic-specific operations.
"""

import logging
from typing import List, Optional, Dict, Any

from services.surreal_service import get_surreal_service
from models.course import Case, CaseCreate, CaseUpdate

logger = logging.getLogger(__name__)


class CourseService:
    """Service for managing academic courses."""

    def __init__(self):
        self.service = get_surreal_service()

    async def check_course_code_exists(
        self,
        course_code: str,
        year: Optional[int] = None,
        semester: Optional[str] = None,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if a course code already exists for a given year/semester.

        Args:
            course_code: Course code to check
            year: Optional year to scope the check (e.g., 2025)
            semester: Optional semester to scope the check (Hiver, Été, Automne)
            exclude_id: Optional case ID to exclude (for updates)

        Returns:
            True if course code exists, False otherwise
        """
        try:
            # Build query
            conditions = [f"course_code = '{course_code}'"]

            if year is not None:
                conditions.append(f"year = {year}")

            if semester:
                conditions.append(f"semester = '{semester}'")

            if exclude_id:
                if not exclude_id.startswith("course:"):
                    exclude_id = f"course:{exclude_id}"
                conditions.append(f"id != {exclude_id}")

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT count() FROM course
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
                SELECT * FROM course
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
                SELECT * FROM course
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
