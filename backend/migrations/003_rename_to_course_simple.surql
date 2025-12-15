-- ============================================================================
-- Migration 003: Create course table structure (Simple version - DB is empty)
-- ============================================================================
-- Since the database has no existing data, we just create the new structure
-- ============================================================================

-- Step 1: Remove old tables if they exist
REMOVE TABLE IF EXISTS case;
REMOVE TABLE IF EXISTS judgment;

-- Step 2: Create the new course table with schema
DEFINE TABLE course SCHEMAFULL;

-- Step 3: Define fields for course table
DEFINE FIELD title ON course TYPE string;
DEFINE FIELD description ON course TYPE option<string>;
DEFINE FIELD keywords ON course TYPE option<array<string>>;
DEFINE FIELD created_at ON course TYPE datetime;
DEFINE FIELD updated_at ON course TYPE option<datetime>;
DEFINE FIELD session_id ON course TYPE option<record<session>>;
DEFINE FIELD course_code ON course TYPE option<string>;
DEFINE FIELD course_name ON course TYPE option<string>;
DEFINE FIELD professor ON course TYPE option<string>;
DEFINE FIELD credits ON course TYPE int DEFAULT 3;
DEFINE FIELD color ON course TYPE option<string>;

-- Step 4: Update field definitions in dependent tables
-- Note: These tables might not exist yet, but defining fields won't hurt

-- Document table
DEFINE FIELD course_id ON document TYPE option<string>;

-- Conversation table
DEFINE FIELD course_id ON conversation TYPE option<string>;

-- Document embedding table
DEFINE FIELD course_id ON document_embedding TYPE string;
DEFINE INDEX idx_course_id ON document_embedding FIELDS course_id;

-- Remove old index if it exists
REMOVE INDEX IF EXISTS idx_judgment_id ON document_embedding;

-- Document chunk table
DEFINE FIELD course_id ON document_chunk TYPE option<string>;

-- Summary table
DEFINE FIELD course_id ON summary TYPE string;

-- Analysis result table
DEFINE FIELD course_id ON analysis_result TYPE option<string>;

-- Migration complete!
