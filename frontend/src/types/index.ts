// Types for Legal Assistant application
// Assistant d'etudes juridiques - Gestion de dossiers

// ============================================
// Course Types
// ============================================

// Main Course type (academic folders/courses)
export interface Course {
  id: string;
  title?: string;             // Title (e.g., "DRT-1001 - Introduction au droit")
  description?: string;       // Description of the case/course
  keywords: string[];         // Keywords
  status?: string;            // Optional status (legacy field for analysis page)
  created_at: string;
  updated_at?: string;
  pinned?: boolean;           // Optional pinned flag

  // Academic fields (optional - dual mode support)
  course_code?: string;       // Course code (e.g., "DRT-1151G")
  professor?: string;         // Professor name
  credits?: number;           // Number of credits (1-12)
  color?: string;             // UI color (hex code)
  year?: number;              // Academic year (e.g., 2025)
  semester?: string;          // Semester (Hiver, Été, Automne)

  // Legacy fields for analysis page
  nom_dossier?: string;       // Deprecated: use title instead
  type_transaction?: string;  // Deprecated: legacy field
  score_confiance?: number;   // Deprecated: legacy field
}

// Document attached to a course
export interface Document {
  id: string;
  course_id: string;          // Course ID (formerly case_id)
  filename: string;           // File name
  file_type: string;          // File type (pdf, docx, txt, audio, etc.)
  size: number;               // Size in bytes
  chemin_stockage: string;    // Storage path (legacy)
  file_path: string;          // Absolute path to file on disk
  hash_sha256: string;        // File hash
  uploaded_at: string;
  file_exists: boolean;       // Whether the file exists on disk

  // Document metadata
  mime_type?: string;         // MIME type
  document_type?: string;     // Type of document
  language?: string;          // Language (fr, en)
  use_ocr?: boolean;          // OCR was used
  is_recording?: boolean;     // Is an audio recording
  identify_speakers?: boolean; // Identify speakers in transcription
  created_at?: string;        // Creation timestamp

  // Extraction and transcription
  extracted_text?: string;    // Extracted text
  transcription?: string;     // Audio transcription
  extraction_status?: "pending" | "processing" | "completed" | "error";

  // Derived documents (for transcriptions, extractions, TTS)
  source_document_id?: string;  // ID of the source document if this is derived
  is_derived?: boolean;         // True if this is a derived file
  derivation_type?: "transcription" | "pdf_extraction" | "tts";  // Type of derivation

  // Linked and Docusaurus source documents
  source_type?: "upload" | "linked" | "docusaurus" | "youtube";  // Source type
  linked_source?: {
    absolute_path: string;      // Absolute path to source file
    relative_path: string;      // Relative path from base directory
    parent_folder: string;      // Parent folder path
    link_id: string;            // Unique ID for this linked directory
    base_path?: string;         // Base path of the linked directory
    last_sync: string;          // Last sync timestamp
    source_hash: string;        // SHA-256 hash of source
    source_mtime: number;       // Source file modification time
  };
  docusaurus_source?: {
    absolute_path: string;      // Absolute path to source file
    relative_path: string;      // Relative path in Docusaurus
    last_sync: string;          // Last sync timestamp
    source_hash: string;        // SHA-256 hash of source
    source_mtime: number;       // Source file modification time
    needs_reindex: boolean;     // True if source has changed
  };
  indexed?: boolean;            // True if indexed for RAG search
}

// Docusaurus file listing
export interface DocusaurusFile {
  absolute_path: string;
  relative_path: string;
  filename: string;
  size: number;
  modified_time: number;
  folder: string;
}

// Linked directory types
export interface LinkedDirectoryFile {
  absolute_path: string;
  relative_path: string;
  filename: string;
  size: number;
  modified_time: number;
  extension: string;
  parent_folder: string;
}

export interface LinkedDirectoryScanResult {
  base_path: string;
  total_files: number;
  total_size: number;
  files_by_type: Record<string, number>;
  files: LinkedDirectoryFile[];
  folder_structure: Record<string, number>;
}

export interface LinkedDirectoryProgressEvent {
  indexed: number;
  total: number;
  current_file: string;
  percentage: number;
}

// Extracted data from documents
export interface ExtractedData {
  documents: ExtractedDocument[];
}

export interface ExtractedDocument {
  nom_fichier: string;
  texte: string;
  montants: Array<{
    montant: number;
    format_original: string;
    contexte: string;
  }>;
  dates: Array<{
    date: string;
    format_original: string;
    contexte: string;
  }>;
  noms: Array<{
    nom: string;
    role: string;
    contexte: string;
  }>;
  adresses: Array<{
    adresse_complete: string;
    numero_civique?: string;
    rue?: string;
    ville?: string;
    code_postal?: string;
  }>;
}

// Classification result
export interface Classification {
  type_transaction: string;
  type_propriete: string;
  documents_identifies: string[];
  documents_manquants: string[];
}

// Verification result
export interface Verification {
  coherence_dates: Record<string, unknown>;
  coherence_montants: Record<string, unknown>;
  completude: Record<string, unknown>;
  alertes: string[];
  score_verification: number;
}

// Checklist item priority
export type Priority = "critique" | "haute" | "moyenne" | "basse" | "normale";

// Checklist item status
export type ChecklistItemStatus =
  | "complete"
  | "incomplete"
  | "en_attente"
  | "a_verifier"
  | "non_applicable";

// Single checklist item
export interface ChecklistItem {
  titre: string;
  description?: string;
  statut: ChecklistItemStatus;
  priorite: Priority;
  categorie?: string;
}

// Next step in workflow
export interface NextStep {
  etape: string;
  delai: string;
  responsable: string;
}

// Complete checklist
export interface Checklist {
  id?: string;
  course_id: string;          // Formerly dossier_id and case_id
  items: ChecklistItem[];
  points_attention: string[];
  documents_manquants: string[];
  score_confiance: number;
  commentaires?: string;
  generated_by?: string;
  created_at?: string;
  // New fields from analysis API
  summary?: string;
  key_points?: string[];
}

// Analysis result
export interface AnalysisResult {
  success: boolean;
  donnees_extraites?: ExtractedData;
  classification?: Classification;
  verification?: Verification;
  checklist?: Checklist;
  score_confiance?: number;
  requiert_validation?: boolean;
  etapes_completees?: string[];
  erreur_message?: string;
}

// API error response
export interface ApiError {
  detail: string;
}

// SSE Progress event types
export type ProgressEventType =
  | "start"
  | "step_start"
  | "step_end"
  | "progress"
  | "complete"
  | "error"
  | "heartbeat";

// Real-time progress event (SSE)
export interface ProgressEvent {
  type: ProgressEventType;
  step: number | null;
  stepName: string | null;
  message: string;
  progressPercent: number;
  timestamp: string;
  data: Record<string, unknown>;
}

// Analysis step status
export type AnalysisStepStatus = "pending" | "in_progress" | "completed" | "error";

// Analysis step
export interface AnalysisStep {
  number: number;
  name: string;
  status: AnalysisStepStatus;
  message?: string;
}

// User type for authentication
export interface User {
  id: string;
  email: string;
  nom: string;
  prenom: string;
  role: "notaire" | "assistant" | "admin";
  created_at: string;
}

// Auth token response
export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ============================================
// User Activity Tracking Types
// ============================================

export type ActivityType =
  | "view_case"
  | "view_document"
  | "close_document"
  | "send_message"
  | "upload_document"
  | "delete_document"
  | "link_file"
  | "transcribe_audio"
  | "extract_pdf"
  | "generate_tts"
  | "search_documents"
  | "semantic_search";

export interface UserActivity {
  id: string;
  course_id: string;
  action_type: ActivityType;
  timestamp: string;
  metadata?: {
    document_id?: string;
    document_name?: string;
    message?: string;
    query?: string;
    [key: string]: unknown;
  };
}

// Legacy type aliases for backward compatibility
export type DonneesExtraites = ExtractedData;
export type DocumentExtrait = ExtractedDocument;
export type ItemChecklist = ChecklistItem;
export type EtapeSuivante = NextStep;

// Legacy aliases for judgment/case compatibility
export type Judgment = Course;
export type Dossier = Course;
export type Case = Course;  // Backward compatibility
