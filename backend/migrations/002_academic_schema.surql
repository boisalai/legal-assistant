-- Migration 002: Academic Schema for Legal Study Assistant
-- Description: Adds support for academic organization (sessions, courses, modules)
-- Date: 2024-12-12
-- Author: Legal Study Assistant Migration

-- =========================================
-- 1. CREATE SESSION TABLE
-- =========================================
-- Sessions académiques (ex: "Automne 2024", "Hiver 2025")

DEFINE TABLE session SCHEMAFULL;

-- Fields
DEFINE FIELD title ON session TYPE string
    ASSERT string::len($value) > 0;
DEFINE FIELD semester ON session TYPE string
    ASSERT string::len($value) > 0;
DEFINE FIELD year ON session TYPE int
    ASSERT $value >= 2020 AND $value <= 2100;
DEFINE FIELD start_date ON session TYPE datetime;
DEFINE FIELD end_date ON session TYPE datetime;
DEFINE FIELD created_at ON session TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON session TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX session_semester_year ON session FIELDS semester, year UNIQUE;

-- =========================================
-- 2. ADD ACADEMIC FIELDS TO CASE TABLE
-- =========================================
-- Ajouter champs académiques sans casser l'existant (dual mode)
-- Renommage case → course sera fait plus tard (Phase 2)

DEFINE FIELD session_id ON case TYPE option<record<session>>;
DEFINE FIELD course_code ON case TYPE option<string>;
DEFINE FIELD course_name ON case TYPE option<string>;
DEFINE FIELD professor ON case TYPE option<string>;
DEFINE FIELD credits ON case TYPE int DEFAULT 3
    VALUE $value OR 3;
DEFINE FIELD color ON case TYPE option<string>;

-- =========================================
-- 3. CREATE MODULE TABLE
-- =========================================
-- Modules/semaines de cours (ex: "Semaine 1 - Sources du droit")

DEFINE TABLE module SCHEMAFULL;

-- Fields
DEFINE FIELD course_id ON module TYPE record<case>
    ASSERT $value != NONE;
DEFINE FIELD title ON module TYPE string
    ASSERT string::len($value) > 0;
DEFINE FIELD order ON module TYPE int DEFAULT 0
    ASSERT $value >= 0;
DEFINE FIELD week_number ON module TYPE option<int>
    ASSERT $value == NONE OR $value >= 1;
DEFINE FIELD topics ON module TYPE option<array<string>>
    DEFAULT [];
DEFINE FIELD start_date ON module TYPE option<datetime>;
DEFINE FIELD end_date ON module TYPE option<datetime>;
DEFINE FIELD created_at ON module TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON module TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX module_course_order ON module FIELDS course_id, order UNIQUE;

-- =========================================
-- 4. ADD MODULE LINK TO DOCUMENT TABLE
-- =========================================
-- Permet de lier un document à un module spécifique (optionnel)

DEFINE FIELD module_id ON document TYPE option<record<module>>;

-- =========================================
-- VERIFICATION QUERIES (commented)
-- =========================================

-- Liste toutes les sessions
-- SELECT * FROM session ORDER BY year DESC, semester;

-- Liste tous les cours d'une session
-- SELECT * FROM case WHERE session_id = session:xxx;

-- Liste tous les modules d'un cours
-- SELECT * FROM module WHERE course_id = case:xxx ORDER BY order;

-- Liste tous les documents d'un module
-- SELECT * FROM document WHERE module_id = module:xxx;

-- Requête complète : Session → Cours → Modules → Documents
-- SELECT
--   *,
--   (SELECT * FROM case WHERE session_id = $parent.id) AS courses,
--   (SELECT * FROM module WHERE course_id IN courses.id) AS modules,
--   (SELECT * FROM document WHERE module_id IN modules.id OR case_id IN courses.id) AS documents
-- FROM session:xxx;
