-- ============================================================================
-- Migration 004: Add pinned field to course table
-- ============================================================================
-- Adds a boolean field to allow users to pin/unpin courses
-- Pinned courses appear first in the list
-- ============================================================================

-- Add pinned field to course table
DEFINE FIELD pinned ON course TYPE bool DEFAULT false PERMISSIONS FULL;

-- Migration complete!
