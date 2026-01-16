/**
 * User activity tracking utilities.
 *
 * Tracks user actions to provide contextual awareness to the AI agent.
 */

import { useCallback } from "react";
import type { ActivityType } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Track a user activity.
 *
 * @param caseId - ID of the case
 * @param actionType - Type of activity
 * @param metadata - Additional context about the activity
 * @returns Promise that resolves when the activity is tracked
 */
export async function trackActivity(
  caseId: string,
  actionType: ActivityType,
  metadata?: Record<string, unknown>
): Promise<void> {
  try {
    // Clean case ID (remove "case:" prefix if present)
    const cleanCaseId = caseId.replace(/^case:/, "");

    const response = await fetch(`${API_BASE_URL}/api/courses/${cleanCaseId}/activity`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action_type: actionType,
        metadata: metadata || {},
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      console.error("Failed to track activity:", error);
    }
  } catch (error) {
    // Silently fail - activity tracking should not break the app
    console.error("Error tracking activity:", error);
  }
}

/**
 * React hook for tracking user activities.
 *
 * Provides a memoized callback to track activities within React components.
 *
 * @param caseId - ID of the case
 * @returns Function to track activities
 *
 * @example
 * ```tsx
 * const trackActivity = useActivityTracker(caseId);
 *
 * const handleViewDocument = (docId: string, docName: string) => {
 *   trackActivity("view_document", { document_id: docId, document_name: docName });
 * };
 * ```
 */
export function useActivityTracker(caseId: string) {
  return useCallback(
    (actionType: ActivityType, metadata?: Record<string, unknown>) => {
      trackActivity(caseId, actionType, metadata);
    },
    [caseId]
  );
}
