// API client for Legal Assistant
// Handles communication with FastAPI backend

import type { Case, AuthToken, User, Document, AnalysisResult, Checklist } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Generic fetch wrapper with error handling
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {};

  // Copy existing headers
  if (options.headers) {
    const existingHeaders = options.headers as Record<string, string>;
    Object.assign(headers, existingHeaders);
  }

  // Add auth token if available
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // Add content-type for JSON requests
  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || error.error?.message || `HTTP ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// ============================================
// Cases API (maps to /api/cases in backend)
// ============================================

export interface CaseListResponse {
  cases: Case[];
  total: number;
}

export const casesApi = {
  // List all cases
  async list(skip: number = 0, limit: number = 20): Promise<Case[]> {
    const response = await fetchApi<CaseListResponse>(
      `/api/cases?skip=${skip}&limit=${limit}`
    );
    return response.cases;
  },

  // Get single judgment by ID
  async get(id: string): Promise<Case> {
    return fetchApi<Case>(`/api/cases/${encodeURIComponent(id)}`);
  },

  // Upload new judgment (PDF or text)
  async upload(data: {
    file?: File;
    text?: string;
    title?: string;
    description?: string;
    citation?: string;
    court?: string;
    decision_date?: string;
    legal_domain?: string;
  }): Promise<Case> {
    const formData = new FormData();

    if (data.file) {
      formData.append("file", data.file);
    }
    if (data.text) {
      formData.append("text", data.text);
    }
    if (data.description) {
      formData.append("description", data.description);
    }
    if (data.title) {
      formData.append("title", data.title);
    }
    if (data.citation) {
      formData.append("citation", data.citation);
    }
    if (data.court) {
      formData.append("court", data.court);
    }
    if (data.decision_date) {
      formData.append("decision_date", data.decision_date);
    }
    if (data.legal_domain) {
      formData.append("legal_domain", data.legal_domain);
    }

    const response = await fetch(`${API_BASE_URL}/api/cases`, {
      method: "POST",
      body: formData,
      headers: {
        ...(typeof window !== "undefined" && localStorage.getItem("auth_token")
          ? { Authorization: `Bearer ${localStorage.getItem("auth_token")}` }
          : {}),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  // Update case
  async update(
    id: string,
    data: {
      title?: string;
      description?: string;
      keywords?: string[];
    }
  ): Promise<Case> {
    // Remove "judgment:" or "case:" prefix if present
    const cleanId = id.replace("judgment:", "").replace("case:", "");
    return fetchApi<Case>(`/api/cases/${encodeURIComponent(cleanId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  // Delete judgment
  async delete(id: string): Promise<void> {
    // Remove "judgment:" prefix if present
    const cleanId = id.replace("judgment:", "");
    await fetchApi<void>(`/api/cases/${encodeURIComponent(cleanId)}`, {
      method: "DELETE",
    });
  },

  // Batch delete cases
  async deleteMany(ids: string[]): Promise<void> {
    await Promise.all(ids.map((id) => this.delete(id)));
  },

  // Generate summary (case brief) for a judgment
  async summarize(id: string, modelId?: string): Promise<any> {
    const cleanId = id.replace("judgment:", "");
    return fetchApi<any>(
      `/api/cases/${encodeURIComponent(cleanId)}/summarize`,
      {
        method: "POST",
        body: JSON.stringify({ model_id: modelId }),
      }
    );
  },

  // Get existing summary for a judgment
  async getSummary(id: string): Promise<any> {
    const cleanId = id.replace("judgment:", "");
    return fetchApi<any>(
      `/api/cases/${encodeURIComponent(cleanId)}/summary`
    );
  },
};


// ============================================
// Models API
// ============================================

export interface LLMModel {
  id: string;
  name: string;
  provider?: string;  // Provider name (e.g., "Ollama", "Claude")
  params?: string;
  ram?: string;
  speed?: string;
  quality?: string;
  best_for?: string;
  recommended?: boolean;
  test_score?: string;
  issues?: string | null;
}

export interface LLMProvider {
  name: string;
  description: string;
  icon: string;
  requires_api_key: boolean;
  default: string;
  models: LLMModel[];
}

// The response is a direct map of provider names to their data
// Can be accessed either directly (response.ollama) or via response.providers if wrapped
export interface ModelsResponse {
  providers?: { [provider: string]: LLMProvider };
  defaults?: { model_id?: string };
  // Direct provider access (actual backend response)
  [provider: string]: LLMProvider | { [provider: string]: LLMProvider } | { model_id?: string } | undefined;
}

export const modelsApi = {
  // Get available LLM models
  async list(): Promise<ModelsResponse> {
    return fetchApi<ModelsResponse>("/api/models");
  },
};

// ============================================
// Auth API
// ============================================

export const authApi = {
  // Login
  async login(email: string, password: string): Promise<AuthToken> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(error.detail || "Invalid credentials");
    }

    const token = await response.json();

    // Store token
    if (typeof window !== "undefined") {
      localStorage.setItem("auth_token", token.access_token);
    }

    return token;
  },

  // Logout
  logout(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
    }
  },

  // Register new user
  async register(name: string, email: string, password: string): Promise<{ message: string; user: User }> {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(error.detail || "Registration failed");
    }

    return response.json();
  },

  // Get current user
  async getCurrentUser(): Promise<User> {
    return fetchApi<User>("/api/auth/me");
  },

  // Check if authenticated
  isAuthenticated(): boolean {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("auth_token");
  },
};

// ============================================
// Health API
// ============================================

export const healthApi = {
  async check(): Promise<{
    status: string;
    database: string;
    model: string;
    debug: boolean;
  }> {
    return fetchApi("/health");
  },
};

// ============================================
// Documents API
// ============================================

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface TranscriptionProgress {
  step: string;
  message: string;
  percentage: number;
}

export interface TranscriptionResult {
  success: boolean;
  document_id?: string;
  document_path?: string;
  transcript_text?: string;
  error?: string;
}

export interface PDFExtractionProgress {
  step: string;
  message: string;
  percentage: number;
}

export interface PDFExtractionResult {
  success: boolean;
  pdf_filename?: string;
  page_count?: number;
  document_id?: string;
  document_path?: string;
  error?: string;
}

export interface YouTubeVideoInfo {
  title: string;
  duration: number;
  uploader: string;
  thumbnail: string;
  url: string;
}

export interface YouTubeDownloadResult {
  success: boolean;
  document_id?: string;
  filename?: string;
  title?: string;
  duration?: number;
  error?: string;
}

export const documentsApi = {
  async list(caseId: string): Promise<Document[]> {
    // Clean ID (remove judgment: prefix if present)
    const cleanId = caseId.replace("judgment:", "");
    const response = await fetchApi<DocumentListResponse>(
      `/api/cases/${encodeURIComponent(cleanId)}/documents`
    );
    return response.documents;
  },

  // Sync documents - auto-discover orphaned files in uploads directory
  async sync(caseId: string): Promise<{ documents: Document[]; discovered: number }> {
    const cleanId = caseId.replace("judgment:", "");
    const response = await fetchApi<DocumentListResponse>(
      `/api/cases/${encodeURIComponent(cleanId)}/documents?auto_discover=true`
    );
    // Count newly discovered documents (those with auto_discovered flag)
    const discovered = response.documents.filter((d: any) => d.auto_discovered).length;
    return { documents: response.documents, discovered };
  },

  // Sync linked directories - reindex, add new files, remove deleted files
  async syncLinkedDirectories(caseId: string): Promise<{
    added: number;
    updated: number;
    removed: number;
    unchanged: number;
    message: string;
  }> {
    const cleanId = caseId.replace("judgment:", "").replace("case:", "");
    return fetchApi(
      `/api/cases/${encodeURIComponent(cleanId)}/sync-linked-directories`,
      { method: "POST" }
    );
  },

  // Get derived documents (transcriptions, extractions, TTS) for a source document
  async getDerived(caseId: string, documentId: string): Promise<{ derived: Document[]; total: number }> {
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");
    const response = await fetchApi<{ derived: Document[]; total: number }>(
      `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}/derived`
    );
    return response;
  },

  // Transcribe an audio document with workflow and SSE progress
  async transcribeWithWorkflow(
    caseId: string,
    documentId: string,
    options: {
      language?: string;
      createMarkdown?: boolean;
      onProgress?: (progress: TranscriptionProgress) => void;
      onStepStart?: (step: string) => void;
      onStepComplete?: (step: string, success: boolean) => void;
    } = {}
  ): Promise<TranscriptionResult> {
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");

    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    const response = await fetch(
      `${API_BASE_URL}/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}/transcribe-workflow`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          language: options.language || "fr",
          create_markdown: options.createMarkdown !== false,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Transcription failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Read SSE stream
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let result: TranscriptionResult = { success: false };
    let receivedComplete = false;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n");

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              switch (eventType) {
                case "progress":
                  options.onProgress?.(data as TranscriptionProgress);
                  break;
                case "step_start":
                  options.onStepStart?.(data.step);
                  break;
                case "step_complete":
                  options.onStepComplete?.(data.step, data.success);
                  break;
                case "complete":
                  result = data as TranscriptionResult;
                  receivedComplete = true;
                  break;
                case "error":
                  throw new Error(data.message);
              }
            } catch (parseError) {
              // Ignore JSON parse errors for individual events
              console.warn("Failed to parse SSE data:", line, parseError);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    // If we didn't receive a complete event, the stream was interrupted
    if (!receivedComplete) {
      throw new Error("La transcription a été interrompue avant la fin. Vérifiez les logs du serveur.");
    }

    return result;
  },

  // Extract PDF to markdown with workflow and SSE progress
  async extractPDFToMarkdown(
    caseId: string,
    documentId: string,
    options: {
      onProgress?: (progress: PDFExtractionProgress) => void;
      onStepStart?: (step: string) => void;
      onStepComplete?: (step: string, success: boolean) => void;
    } = {}
  ): Promise<PDFExtractionResult> {
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");

    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    const response = await fetch(
      `${API_BASE_URL}/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}/extract-to-markdown`,
      {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "PDF extraction failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Read SSE stream
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let result: PDFExtractionResult = { success: false };
    let receivedComplete = false;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n");

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              switch (eventType) {
                case "progress":
                  options.onProgress?.(data as PDFExtractionProgress);
                  break;
                case "step_start":
                  options.onStepStart?.(data.step);
                  break;
                case "step_complete":
                  options.onStepComplete?.(data.step, data.success);
                  break;
                case "complete":
                  result = data as PDFExtractionResult;
                  receivedComplete = true;
                  break;
                case "error":
                  throw new Error(data.message);
              }
            } catch (parseError) {
              // Ignore JSON parse errors for individual events
              console.warn("Failed to parse SSE data:", line, parseError);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    // If we didn't receive a complete event, the stream was interrupted
    if (!receivedComplete) {
      throw new Error("L'extraction a été interrompue avant la fin. Vérifiez les logs du serveur.");
    }

    return result;
  },

  async upload(caseId: string, file: File): Promise<Document> {
    // Clean ID (remove judgment: prefix if present)
    const cleanId = caseId.replace("judgment:", "");

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/cases/${encodeURIComponent(cleanId)}/documents`, {
      method: "POST",
      body: formData,
      headers: {
        ...(typeof window !== "undefined" && localStorage.getItem("auth_token")
          ? { Authorization: `Bearer ${localStorage.getItem("auth_token")}` }
          : {}),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  async register(caseId: string, filePath: string): Promise<Document> {
    // Register a document by file path (no upload/copy)
    const cleanId = caseId.replace("judgment:", "");

    return fetchApi<Document>(
      `/api/cases/${encodeURIComponent(cleanId)}/documents/register`,
      {
        method: "POST",
        body: JSON.stringify({ file_path: filePath }),
      }
    );
  },

  // Link a file or folder (without copying)
  async link(caseId: string, path: string): Promise<{ success: boolean; linked_count: number; documents: Document[]; warnings?: string[] }> {
    const cleanId = caseId.replace("judgment:", "");

    return fetchApi<{ success: boolean; linked_count: number; documents: Document[]; warnings?: string[] }>(
      `/api/cases/${encodeURIComponent(cleanId)}/documents/link`,
      {
        method: "POST",
        body: JSON.stringify({ path }),
      }
    );
  },

  async delete(caseId: string, documentId: string, filename?: string, filePath?: string): Promise<void> {
    // Clean IDs
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");

    // Build URL with optional query parameters
    const params = new URLSearchParams();
    if (filename) params.append("filename", filename);
    if (filePath) params.append("file_path", filePath);

    const queryString = params.toString();
    const url = `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}${queryString ? `?${queryString}` : ""}`;

    await fetchApi<void>(url, { method: "DELETE" });
  },

  getDownloadUrl(caseId: string, documentId: string): string {
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");
    return `${API_BASE_URL}/api/cases/${cleanCaseId}/documents/${cleanDocId}/download`;
  },

  getPreviewUrl(caseId: string, documentId: string): string {
    // For now, preview uses the same URL as download
    return this.getDownloadUrl(caseId, documentId);
  },

  async download(caseId: string, documentId: string, filename: string): Promise<void> {
    const url = this.getDownloadUrl(caseId, documentId);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  preview(caseId: string, documentId: string): void {
    const url = this.getPreviewUrl(caseId, documentId);
    window.open(url, "_blank");
  },

  async extract(caseId: string, documentId: string): Promise<{
    success: boolean;
    text?: string;
    method?: string;
    error?: string;
  }> {
    // Extract text from a document (PDF, Word, text, etc.)
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");

    return fetchApi(
      `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}/extract`,
      { method: "POST" }
    );
  },

  async clearText(caseId: string, documentId: string): Promise<{
    success: boolean;
    message?: string;
  }> {
    // Clear extracted text from a document
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");

    return fetchApi(
      `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}/text`,
      { method: "DELETE" }
    );
  },

  // YouTube methods
  async getYouTubeInfo(caseId: string, url: string): Promise<YouTubeVideoInfo> {
    const cleanCaseId = caseId.replace("judgment:", "");
    return fetchApi<YouTubeVideoInfo>(
      `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/youtube/info`,
      {
        method: "POST",
        body: JSON.stringify({ url }),
      }
    );
  },

  async downloadYouTube(caseId: string, url: string): Promise<YouTubeDownloadResult> {
    const cleanCaseId = caseId.replace("judgment:", "");
    return fetchApi<YouTubeDownloadResult>(
      `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/youtube`,
      {
        method: "POST",
        body: JSON.stringify({ url }),
      }
    );
  },
};

// ============================================
// Chat/Assistant API
// ============================================

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface DocumentSource {
  name: string;
  type: string;
  word_count: number;
  is_transcription: boolean;
}

export interface ChatResponse {
  message: string;
  model: string;
  document_created?: boolean;  // Indicates if a new document was created during the chat
  sources?: DocumentSource[];  // Sources consulted for RAG
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export const chatApi = {
  async send(
    message: string,
    context: {
      caseId?: string;
      model?: string;
      history?: ChatMessage[];
    } = {}
  ): Promise<ChatResponse> {
    return fetchApi<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        case_id: context.caseId,
        model_id: context.model || "ollama:qwen2.5:7b",
        history: context.history || [],
      }),
    });
  },

  async stream(
    message: string,
    context: {
      caseId?: string;
      model?: string;
      history?: ChatMessage[];
    } = {}
  ): Promise<Response> {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(typeof window !== "undefined" && localStorage.getItem("auth_token")
          ? { Authorization: `Bearer ${localStorage.getItem("auth_token")}` }
          : {}),
      },
      body: JSON.stringify({
        message,
        case_id: context.caseId,
        model_id: context.model || "ollama:qwen2.5:7b",
        history: context.history || [],
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Chat failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response;
  },

  async health(): Promise<{ status: string; default_model: string }> {
    try {
      return await fetchApi<{ status: string; default_model: string }>("/api/chat/health");
    } catch {
      throw new Error("Chat service unavailable");
    }
  },
};

// ============================================
// Settings API
// ============================================

export const settingsApi = {
  async getModels(): Promise<ModelsResponse> {
    return modelsApi.list();
  },

  async getExtractionMethods(): Promise<{
    methods: Record<string, { name: string; description: string; available: boolean }>;
    docling_available: boolean;
    default: string;
  }> {
    return fetchApi("/api/settings/extraction-methods");
  },

  async getCurrent(): Promise<{
    analysis: { model_id: string; extraction_method: string; use_ocr: boolean };
    available_models: Record<string, LLMModel[]>;
    available_extraction_methods: Record<string, unknown>;
  }> {
    return fetchApi("/api/settings/current");
  },

  async update(settings: {
    model_id?: string;
    extraction_method?: string;
    use_ocr?: boolean;
  }): Promise<{ message: string; settings: unknown }> {
    return fetchApi("/api/settings/current", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
  },
};

// ============================================
// Admin API
// ============================================

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  actif: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UsersListResponse {
  users: AdminUser[];
  total: number;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
  role: string;
  actif: boolean;
}

export interface UpdateUserRequest {
  email?: string;
  name?: string;
  password?: string;
  role?: string;
  actif?: boolean;
}

export const adminApi = {
  async listUsers(skip: number = 0, limit: number = 50): Promise<UsersListResponse> {
    return fetchApi<UsersListResponse>(`/api/admin/users?skip=${skip}&limit=${limit}`);
  },

  async getUser(id: string): Promise<AdminUser> {
    return fetchApi<AdminUser>(`/api/admin/users/${encodeURIComponent(id)}`);
  },

  async createUser(data: CreateUserRequest): Promise<AdminUser> {
    return fetchApi<AdminUser>("/api/admin/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateUser(id: string, data: UpdateUserRequest): Promise<AdminUser> {
    return fetchApi<AdminUser>(`/api/admin/users/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async deleteUser(id: string): Promise<void> {
    await fetchApi<void>(`/api/admin/users/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },
};

// ============================================
// Analysis API - Pipeline d'analyse complete
// ============================================

export interface AnalysisStartResponse {
  message: string;
  case_id: string;
  documents_count: number;
  model: string;
}

export interface AnalysisStatus {
  case_id: string;
  status: string;
  progress: number;
  message: string;
  documents_processed: number;
  documents_total: number;
}

export interface AnalysisChecklistResponse {
  items: Array<{ titre: string; description?: string; complete: boolean }>;
  points_attention: string[];
  key_points: string[];
  summary: string;
  confidence_score: number;
  model_used: string;
  created_at: string;
}

export const analysisApi = {
  // Demarre l'analyse complete d'un dossier
  async start(caseId: string, modelId?: string): Promise<AnalysisStartResponse> {
    const cleanId = caseId.replace("judgment:", "");
    return fetchApi<AnalysisStartResponse>(
      `/api/analysis/${encodeURIComponent(cleanId)}/start`,
      {
        method: "POST",
        body: JSON.stringify({ model_id: modelId }),
      }
    );
  },

  // Recupere le statut de l'analyse
  async getStatus(caseId: string): Promise<AnalysisStatus> {
    const cleanId = caseId.replace("judgment:", "");
    return fetchApi<AnalysisStatus>(
      `/api/analysis/${encodeURIComponent(cleanId)}/status`
    );
  },

  // Recupere la checklist generee par l'analyse
  async getChecklist(caseId: string): Promise<Checklist> {
    const cleanId = caseId.replace("judgment:", "");
    try {
      const response = await fetchApi<AnalysisChecklistResponse>(
        `/api/analysis/${encodeURIComponent(cleanId)}/checklist`
      );
      return {
        case_id: caseId,
        items: response.items.map(item => ({
          titre: item.titre,
          description: item.description || "",
          statut: item.complete ? "complete" as const : "incomplete" as const,
          priorite: "normale" as const,
        })),
        points_attention: response.points_attention,
        documents_manquants: [],
        score_confiance: response.confidence_score * 100,
        summary: response.summary,
        key_points: response.key_points,
      };
    } catch {
      // Fallback si pas d'analyse disponible
      return {
        case_id: caseId,
        items: [],
        points_attention: [],
        documents_manquants: [],
        score_confiance: 0,
      };
    }
  },

  // Pour compatibilite arriere
  async startStream(_caseId: string): Promise<Response> {
    throw new Error("Streaming analysis not implemented");
  },

  // Get derived documents (transcriptions, extractions, TTS) for a source document
  async getDerived(caseId: string, documentId: string): Promise<{ derived: Document[]; total: number }> {
    const cleanCaseId = caseId.replace("judgment:", "");
    const cleanDocId = documentId.replace("document:", "");

    const response = await fetchApi<{ derived: Document[]; total: number }>(
      `/api/cases/${encodeURIComponent(cleanCaseId)}/documents/${encodeURIComponent(cleanDocId)}/derived`
    );
    return response;
  },
};

// ============================================
// ============================================
// Docusaurus API (maps to /api/docusaurus)
// ============================================

import type { DocusaurusFile } from "@/types";

export interface DocusaurusListResponse {
  files: DocusaurusFile[];
  total: number;
  base_path: string;
}

export interface CheckUpdatesResponse {
  documents_checked: number;
  documents_needing_update: string[];
}

export interface ReindexResponse {
  success: boolean;
  document_id: string;
  chunks_created?: number;
  error?: string;
}

export const docusaurusApi = {
  // List available Docusaurus files
  async listFiles(basePath?: string): Promise<DocusaurusListResponse> {
    const params = basePath ? `?base_path=${encodeURIComponent(basePath)}` : "";
    return fetchApi<DocusaurusListResponse>(`/api/docusaurus/list${params}`);
  },

  // Import selected Docusaurus files into a case
  async importFiles(caseId: string, filePaths: string[]): Promise<Document[]> {
    const cleanId = caseId.replace("case:", "");
    return fetchApi<Document[]>(`/api/cases/${cleanId}/import-docusaurus`, {
      method: "POST",
      body: JSON.stringify({ file_paths: filePaths }),
    });
  },

  // Check for updates on Docusaurus documents
  async checkUpdates(caseId: string): Promise<CheckUpdatesResponse> {
    const cleanId = caseId.replace("case:", "");
    return fetchApi<CheckUpdatesResponse>(`/api/cases/${cleanId}/check-docusaurus-updates`, {
      method: "POST",
    });
  },

  // Reindex a Docusaurus document
  async reindex(documentId: string): Promise<ReindexResponse> {
    const cleanId = documentId.replace("document:", "");
    return fetchApi<ReindexResponse>(`/api/documents/${cleanId}/reindex-docusaurus`, {
      method: "POST",
    });
  },
};

// ============================================
// Linked Directory API
// ============================================

import type { LinkedDirectoryScanResult, LinkedDirectoryProgressEvent } from "@/types";

export const linkedDirectoryApi = {
  // Scan a directory and return statistics
  async scan(directoryPath: string): Promise<LinkedDirectoryScanResult> {
    return fetchApi<LinkedDirectoryScanResult>("/api/linked-directory/scan", {
      method: "POST",
      body: JSON.stringify({ directory_path: directoryPath }),
    });
  },

  // Link a directory to a case with SSE progress
  async link(
    caseId: string,
    directoryPath: string,
    onProgress?: (event: LinkedDirectoryProgressEvent) => void,
    onComplete?: (result: { success: boolean; total_indexed: number; link_id: string }) => void,
    onError?: (error: string) => void
  ): Promise<void> {
    const cleanId = caseId.replace("case:", "");
    const url = `${API_BASE_URL}/api/cases/${cleanId}/link-directory`;

    // Build headers
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Add auth token if available
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("auth_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ directory_path: directoryPath }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error("Response body is null");
    }

    let currentEvent = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
            continue;
          }

          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));

            if (currentEvent === "progress" && onProgress) {
              onProgress(data);
            } else if (currentEvent === "complete" && onComplete) {
              onComplete(data);
            } else if (currentEvent === "error" && onError) {
              onError(data.error);
            }

            currentEvent = "";
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};

// ============================================
// Export all APIs
// ============================================

export const api = {
  cases: casesApi,
  documents: documentsApi,
  analysis: analysisApi,
  chat: chatApi,
  settings: settingsApi,
  models: modelsApi,
  auth: authApi,
  admin: adminApi,
  health: healthApi,
  docusaurus: docusaurusApi,
  linkedDirectory: linkedDirectoryApi,
};

export default api;
