// Types for Legal Assistant application
// Assistant d'etudes juridiques - Resume de jugements

// ============================================
// Judgment Types
// ============================================

// Judgment status enum
export type JudgmentStatus =
  | "pending"
  | "analyzing"
  | "summarized"
  | "error"
  | "archived";

// Legal domain enum
export type LegalDomain =
  | "civil"
  | "criminal"
  | "administrative"
  | "family"
  | "commercial"
  | "constitutional"
  | "labor"
  | "other";

// Court level enum
export type CourtLevel =
  | "tribunal_instance"
  | "cour_superieure"
  | "cour_appel"
  | "cour_supreme";

// Main Judgment type (maps to API "judgment")
export interface Judgment {
  id: string;
  title?: string;             // Title or case name
  description?: string;       // Description of the judgment
  citation?: string;          // Legal citation (e.g., "2024 QCCS 1234")
  court?: string;             // Court name
  decision_date?: string;     // Date of decision
  legal_domain?: string;      // Area of law
  text?: string;              // Full text of judgment
  file_path?: string;         // Path to uploaded PDF
  status: JudgmentStatus;
  user_id?: string;
  created_at: string;
  updated_at?: string;
}

// Judgment summary (Case Brief)
export interface JudgmentSummary {
  id: string;
  judgment_id: string;
  case_brief: CaseBrief;
  confidence_score: number;   // 0-1
  key_takeaway: string;
  model_used: string;
  created_at: string;
}

// Structured Case Brief
export interface CaseBrief {
  case_name?: string;
  citation?: string;
  court?: string;
  decision_date?: string;
  judge?: string;
  parties?: Party[];
  facts?: string[];
  procedural_history?: string;
  issues?: LegalIssue[];
  rules?: LegalRule[];
  ratio_decidendi?: string;
  obiter_dicta?: string[];
  holding?: string;
  remedy?: string;
}

// Party in a legal case
export interface Party {
  name: string;
  role: "plaintiff" | "defendant" | "appellant" | "respondent" | "other";
  lawyer?: string;
}

// Legal issue
export interface LegalIssue {
  question: string;
  importance: "primary" | "secondary";
  answer?: string;
}

// Legal rule
export interface LegalRule {
  rule: string;
  source: string;
  source_type: "statute" | "case_law" | "doctrine" | "principle";
}

// ============================================
// Case Types (for backwards compatibility)
// ============================================

// Case status enum
export type CaseStatus =
  | "nouveau"
  | "pending"
  | "en_analyse"
  | "analyzing"
  | "termine"
  | "summarized"
  | "en_erreur"
  | "error"
  | "archive"
  | "archived";

// Transaction type enum (now maps to legal domain)
export type TransactionType =
  | "civil"
  | "criminal"
  | "administrative"
  | "family"
  | "commercial"
  | "juridique"
  | "autre";

// Main Case type (maps to Judgment for compatibility)
export interface Case {
  id: string;
  nom_dossier: string;        // Case name / Title
  type_transaction: TransactionType | string;
  status: CaseStatus;
  statut?: CaseStatus;        // Alias for backwards compatibility
  user_id: string;
  created_at: string;
  updated_at: string;
  score_confiance?: number;   // Confidence score (0-1)
  pinned?: boolean;           // Whether the case is pinned
  summary?: string;           // One-line summary
  description?: string;       // Case description
  // Judgment-specific fields
  citation?: string;
  court?: string;
  decision_date?: string;
  text?: string;
}

// Legacy alias for backward compatibility
export type Dossier = Case;

// Document attached to a case
export interface Document {
  id: string;
  dossier_id: string;         // Case ID in API
  nom_fichier: string;        // File name
  type_fichier: string;       // File type (pdf, docx, txt, audio, etc.)
  taille: number;             // Size in bytes
  chemin_stockage: string;    // Storage path
  hash_sha256: string;        // File hash
  uploaded_at: string;

  // Document metadata
  type_mime?: string;         // MIME type
  document_type?: string;     // Type of document (certificat, contrat, etc.)
  language?: string;          // Language (fr, en)
  use_ocr?: boolean;          // OCR was used
  is_recording?: boolean;     // Is an audio recording
  identify_speakers?: boolean; // Identify speakers in transcription

  // Extraction and transcription
  texte_extrait?: string;     // Extracted text
  transcription?: string;     // Audio transcription
  extraction_status?: "pending" | "processing" | "completed" | "error";
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
  dossier_id: string;
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
