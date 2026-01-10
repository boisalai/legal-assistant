-- Migration 005: Rename case_id to course_id in document, conversation, and user_activity tables
-- This standardizes the foreign key naming to match the course table

-- Step 1: Add course_id field to document table (copy from case_id)
UPDATE document SET course_id = case_id WHERE case_id IS NOT NONE;

-- Step 2: Add course_id field to conversation table (copy from case_id)
UPDATE conversation SET course_id = case_id WHERE case_id IS NOT NONE;

-- Step 3: Add course_id field to user_activity table (copy from case_id)
UPDATE user_activity SET course_id = case_id WHERE case_id IS NOT NONE;

-- Step 4: Remove old case_id field from document table
UPDATE document UNSET case_id;

-- Step 5: Remove old case_id field from conversation table
UPDATE conversation UNSET case_id;

-- Step 6: Remove old case_id field from user_activity table
UPDATE user_activity UNSET case_id;

-- Verification queries (run manually):
-- SELECT count() FROM document WHERE course_id IS NOT NONE GROUP ALL;
-- SELECT count() FROM conversation WHERE course_id IS NOT NONE GROUP ALL;
-- SELECT count() FROM user_activity WHERE course_id IS NOT NONE GROUP ALL;
-- SELECT count() FROM document WHERE case_id IS NOT NONE GROUP ALL; -- Should be 0
-- SELECT count() FROM conversation WHERE case_id IS NOT NONE GROUP ALL; -- Should be 0
-- SELECT count() FROM user_activity WHERE case_id IS NOT NONE GROUP ALL; -- Should be 0
