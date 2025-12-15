-- ============================================================================
-- Migration 003: Rename case + judgment → course
-- ============================================================================
-- This migration consolidates the "case" and "judgment" tables into a single
-- "course" table, updating all foreign key references throughout the database.
-- ============================================================================

-- Step 1: Create the new course table
DEFINE TABLE course SCHEMAFULL;

-- Step 2: Copy all data from case → course
-- Note: SurrealDB requires explicit field selection for INSERT
LET $case_records = (SELECT * FROM case);
FOR $record IN $case_records {
    CREATE course SET
        id = string::replace(string($record.id), 'case:', 'course:'),
        title = $record.title,
        description = $record.description,
        keywords = $record.keywords,
        created_at = $record.created_at,
        updated_at = $record.updated_at,
        session_id = $record.session_id,
        course_code = $record.course_code,
        course_name = $record.course_name,
        professor = $record.professor,
        credits = $record.credits OR 3,
        color = $record.color
};

-- Step 3: Copy all data from judgment → course (if exists)
LET $judgment_records = (SELECT * FROM judgment);
FOR $record IN $judgment_records {
    CREATE course SET
        id = string::replace(string($record.id), 'judgment:', 'course:'),
        title = $record.title,
        description = $record.description,
        keywords = $record.keywords OR [],
        created_at = $record.created_at,
        updated_at = $record.updated_at,
        session_id = NONE,
        course_code = NONE,
        course_name = NONE,
        professor = NONE,
        credits = 3,
        color = NONE
};

-- Step 4: Update all foreign keys in dependent tables

-- 4.1 document table: Add course_id field
DEFINE FIELD course_id ON document TYPE option<string>;

-- 4.2 Update document records from case_id
LET $docs_with_case = (SELECT * FROM document WHERE case_id IS NOT NONE);
FOR $doc IN $docs_with_case {
    UPDATE $doc.id SET course_id = string::replace(string($doc.case_id), 'case:', 'course:')
};

-- 4.3 Update document records from judgment_id
LET $docs_with_judgment = (SELECT * FROM document WHERE judgment_id IS NOT NONE);
FOR $doc IN $docs_with_judgment {
    UPDATE $doc.id SET course_id = string::replace(string($doc.judgment_id), 'judgment:', 'course:')
};

-- 4.4 conversation table: Add course_id field
DEFINE FIELD course_id ON conversation TYPE option<string>;

-- 4.5 Update conversation records from case_id
LET $convs_with_case = (SELECT * FROM conversation WHERE case_id IS NOT NONE);
FOR $conv IN $convs_with_case {
    UPDATE $conv.id SET course_id = string::replace(string($conv.case_id), 'case:', 'course:')
};

-- 4.6 Update conversation records from judgment_id
LET $convs_with_judgment = (SELECT * FROM conversation WHERE judgment_id IS NOT NONE);
FOR $conv IN $convs_with_judgment {
    UPDATE $conv.id SET course_id = string::replace(string($conv.judgment_id), 'judgment:', 'course:')
};

-- 4.7 document_embedding table: Add course_id field
DEFINE FIELD course_id ON document_embedding TYPE option<string>;

-- 4.8 Update document_embedding records from judgment_id
LET $embs_with_judgment = (SELECT * FROM document_embedding WHERE judgment_id IS NOT NONE);
FOR $emb IN $embs_with_judgment {
    UPDATE $emb.id SET course_id = string::replace(string($emb.judgment_id), 'judgment:', 'course:')
};

-- 4.9 document_chunk table: Add course_id field (if table exists)
DEFINE FIELD course_id ON document_chunk TYPE option<string>;

-- 4.10 Update document_chunk records from case_id
LET $chunks_with_case = (SELECT * FROM document_chunk WHERE case_id IS NOT NONE);
FOR $chunk IN $chunks_with_case {
    UPDATE $chunk.id SET course_id = string::replace(string($chunk.case_id), 'case:', 'course:')
};

-- 4.11 Update document_chunk records from judgment_id
LET $chunks_with_judgment = (SELECT * FROM document_chunk WHERE judgment_id IS NOT NONE);
FOR $chunk IN $chunks_with_judgment {
    UPDATE $chunk.id SET course_id = string::replace(string($chunk.judgment_id), 'judgment:', 'course:')
};

-- 4.12 summary table: Add course_id field
DEFINE FIELD course_id ON summary TYPE option<string>;

-- 4.13 Update summary records from judgment_id
LET $sums_with_judgment = (SELECT * FROM summary WHERE judgment_id IS NOT NONE);
FOR $sum IN $sums_with_judgment {
    UPDATE $sum.id SET course_id = string::replace(string($sum.judgment_id), 'judgment:', 'course:')
};

-- 4.14 analysis_result table: Add course_id field (if table exists)
DEFINE FIELD course_id ON analysis_result TYPE option<string>;

-- 4.15 Update analysis_result records from case_id
LET $analysis_with_case = (SELECT * FROM analysis_result WHERE case_id IS NOT NONE);
FOR $result IN $analysis_with_case {
    UPDATE $result.id SET course_id = string::replace(string($result.case_id), 'case:', 'course:')
};

-- 4.16 Update analysis_result records from judgment_id
LET $analysis_with_judgment = (SELECT * FROM analysis_result WHERE judgment_id IS NOT NONE);
FOR $result IN $analysis_with_judgment {
    UPDATE $result.id SET course_id = string::replace(string($result.judgment_id), 'judgment:', 'course:')
};

-- 4.17 module table: Update course_id references (already named correctly)
LET $modules = (SELECT * FROM module WHERE course_id IS NOT NONE);
FOR $mod IN $modules {
    UPDATE $mod.id SET course_id = string::replace(string($mod.course_id), 'case:', 'course:')
};

-- Step 5: Remove old fields from tables

-- 5.1 Remove old fields from document
REMOVE FIELD case_id ON document;
REMOVE FIELD judgment_id ON document;

-- 5.2 Remove old fields from conversation
REMOVE FIELD case_id ON conversation;
REMOVE FIELD judgment_id ON conversation;

-- 5.3 Remove old fields from document_embedding
REMOVE FIELD judgment_id ON document_embedding;

-- 5.4 Remove old fields from document_chunk
REMOVE FIELD case_id ON document_chunk;
REMOVE FIELD judgment_id ON document_chunk;

-- 5.5 Remove old fields from summary
REMOVE FIELD judgment_id ON summary;

-- 5.6 Remove old fields from analysis_result
REMOVE FIELD case_id ON analysis_result;
REMOVE FIELD judgment_id ON analysis_result;

-- Step 6: Remove old tables
REMOVE TABLE case;
REMOVE TABLE judgment;

-- Step 7: Define complete schema for course table
DEFINE FIELD title ON course TYPE string;
DEFINE FIELD description ON course TYPE option<string>;
DEFINE FIELD keywords ON course TYPE option<array<string>>;
DEFINE FIELD created_at ON course TYPE datetime;
DEFINE FIELD updated_at ON course TYPE option<datetime>;
DEFINE FIELD session_id ON course TYPE option<record<session>>;
DEFINE FIELD course_code ON course TYPE option<string>;
DEFINE FIELD course_name ON course TYPE option<string>;
DEFINE FIELD professor ON course TYPE option<string>;
DEFINE FIELD credits ON course TYPE int;
DEFINE FIELD color ON course TYPE option<string>;

-- Step 8: Update indexes
DEFINE INDEX idx_course_id ON document_embedding FIELDS course_id;
REMOVE INDEX idx_judgment_id ON document_embedding;

-- Step 9: Update field definitions in dependent tables to make course_id required
DEFINE FIELD course_id ON document TYPE string;
DEFINE FIELD course_id ON conversation TYPE string;
DEFINE FIELD course_id ON document_embedding TYPE string;
DEFINE FIELD course_id ON document_chunk TYPE string;
DEFINE FIELD course_id ON summary TYPE string;
DEFINE FIELD course_id ON analysis_result TYPE string;

-- Migration complete!
