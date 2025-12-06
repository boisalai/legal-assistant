// Types for Legal Assistant application
// Assistant d'etudes juridiques - Gestion de dossiers

// ============================================
// Case Types
// ============================================

// Main Case type (academic folders/courses)
export interface Case {
  id: string;
  title?: string;             // Title (e.g., "DRT-1001 - Introduction au droit")
  description?: string;       // Description of the case/course
  keywords: string[];         // Keywords
  created_at: string;
  updated_at?: string;
}

// Document attached to a case
export interface Document {
  id: string;
  case_id: string;            // Case ID (formerly case_id)
  nom_fichier: string;        // File name
  type_fichier: string;       // File type (pdf, docx, txt, audio, etc.)
  taille: number;             // Size in bytes
  chemin_stockage: string;    // Storage path (legacy)
  file_path: string;          // Absolute path to file on disk
  hash_sha256: string;        // File hash
  uploaded_at: string;
  file_exists: boolean;       // Whether the file exists on disk

  // Document metadata
  type_mime?: string;         // MIME type
  document_type?: string;     // Type of document
  language?: string;          // Language (fr, en)
  use_ocr?: boolean;          // OCR was used
  is_recording?: boolean;     // Is an audio recording
  identify_speakers?: boolean; // Identify speakers in transcription

  // Extraction and transcription
  texte_extrait?: string;     // Extracted text
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
    last_sync: string;          // Last sync timestamp
    source_hash: string;        // SHA-256 hash of source
    source_mtime: number;       // Source file modification time
    needs_reindex: boolean;     // True if source has changed
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
  case_id: string;            // Formerly dossier_id
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

// Legacy type aliases for backward compatibility
export type DonneesExtraites = ExtractedData;
export type DocumentExtrait = ExtractedDocument;
export type ItemChecklist = ChecklistItem;
export type EtapeSuivante = NextStep;

// Legacy aliases for judgment/case compatibility
export type Judgment = Case;
export type Dossier = Case;
