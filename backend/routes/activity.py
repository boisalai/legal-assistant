"""
User activity tracking API routes.

Provides endpoints to track and retrieve user actions for contextual AI awareness.
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.user_activity_service import get_activity_service, ActivityType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["Activity"])


class TrackActivityRequest(BaseModel):
    """Request to track a user activity."""
    action_type: str  # Will be validated against ActivityType
    metadata: Optional[Dict[str, Any]] = None


class ActivityResponse(BaseModel):
    """Response containing activity information."""
    id: str
    course_id: str
    action_type: str
    timestamp: str
    metadata: Dict[str, Any]


@router.post("/{course_id}/activity")
async def track_activity(course_id: str, request: TrackActivityRequest):
    """
    Track a user activity for contextual awareness.

    Args:
        course_id: ID of the course
        request: Activity details

    Returns:
        Success status and activity ID
    """
    try:
        # Validate action_type
        try:
            action_type = ActivityType(request.action_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action_type. Must be one of: {[t.value for t in ActivityType]}"
            )

        activity_service = get_activity_service()
        activity_id = await activity_service.track_activity(
            course_id=f"course:{course_id}",
            action_type=action_type,
            metadata=request.metadata
        )

        if activity_id:
            return {
                "success": True,
                "activity_id": activity_id,
                "message": "Activity tracked successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to track activity"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking activity: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error tracking activity: {str(e)}"
        )


@router.get("/{course_id}/activity")
async def get_activities(course_id: str, limit: int = 50):
    """
    Get recent user activities for a course.

    Args:
        course_id: ID of the course
        limit: Maximum number of activities to retrieve (default: 50, max: 100)

    Returns:
        List of recent activities
    """
    try:
        # Enforce max limit
        if limit > 100:
            limit = 100

        activity_service = get_activity_service()
        activities = await activity_service.get_recent_activities(
            course_id=f"course:{course_id}",
            limit=limit
        )

        return {
            "course_id": course_id,
            "activities": activities,
            "count": len(activities)
        }

    except Exception as e:
        logger.error(f"Error retrieving activities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving activities: {str(e)}"
        )


@router.delete("/{course_id}/activity")
async def clear_activities(course_id: str):
    """
    Clear all activity history for a course.

    Args:
        course_id: ID of the course

    Returns:
        Success status
    """
    try:
        activity_service = get_activity_service()
        success = await activity_service.clear_activities(course_id=f"course:{course_id}")

        if success:
            return {
                "success": True,
                "message": "Activity history cleared successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear activity history"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing activities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing activities: {str(e)}"
        )


@router.get("/{course_id}/activity/context")
async def get_activity_context(course_id: str, limit: int = 50):
    """
    Get a formatted context summary of recent activities for the AI agent.

    Args:
        course_id: ID of the course
        limit: Maximum number of activities to include (default: 50)

    Returns:
        Formatted context string
    """
    try:
        activity_service = get_activity_service()
        context = await activity_service.get_activity_context(
            course_id=f"course:{course_id}",
            limit=limit
        )

        return {
            "course_id": course_id,
            "context": context
        }

    except Exception as e:
        logger.error(f"Error getting activity context: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting activity context: {str(e)}"
        )
