-- Migration: Create audio_summary table for audio summaries of course documents
-- Purpose: Store audio summary metadata, scripts, and generated audio file paths

-- Create audio_summary table
DEFINE TABLE audio_summary SCHEMAFULL;

-- Fields
DEFINE FIELD course_id ON audio_summary TYPE string;
DEFINE FIELD name ON audio_summary TYPE string;
DEFINE FIELD source_documents ON audio_summary TYPE array;
DEFINE FIELD status ON audio_summary TYPE string DEFAULT "pending";
DEFINE FIELD script_path ON audio_summary TYPE option<string>;
DEFINE FIELD audio_path ON audio_summary TYPE option<string>;
DEFINE FIELD script_data ON audio_summary TYPE option<object>;
DEFINE FIELD voice_config ON audio_summary TYPE object;
DEFINE FIELD estimated_duration_seconds ON audio_summary TYPE float DEFAULT 0.0;
DEFINE FIELD actual_duration_seconds ON audio_summary TYPE option<float>;
DEFINE FIELD section_count ON audio_summary TYPE int DEFAULT 0;
DEFINE FIELD error_message ON audio_summary TYPE option<string>;
DEFINE FIELD model_id ON audio_summary TYPE option<string>;
DEFINE FIELD created_at ON audio_summary TYPE datetime;
DEFINE FIELD updated_at ON audio_summary TYPE option<datetime>;

-- Indexes
DEFINE INDEX idx_audio_summary_course_id ON audio_summary FIELDS course_id;
DEFINE INDEX idx_audio_summary_status ON audio_summary FIELDS status;
DEFINE INDEX idx_audio_summary_created_at ON audio_summary FIELDS created_at;
