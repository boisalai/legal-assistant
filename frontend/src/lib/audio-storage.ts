/**
 * Service de stockage audio persistant avec IndexedDB.
 *
 * Permet d'enregistrer des audios de longue durée (3h+) de manière fiable
 * en sauvegardant les chunks sur disque au fur et à mesure.
 *
 * Fonctionnalités:
 * - Sauvegarde incrémentale des chunks audio
 * - Récupération après crash/fermeture du navigateur
 * - Assemblage final en un seul fichier
 */

const DB_NAME = "legal-assistant-audio";
const DB_VERSION = 1;
const CHUNKS_STORE = "chunks";
const SESSIONS_STORE = "sessions";

export interface RecordingSession {
  id: string;
  caseId: string;
  name: string;
  startedAt: string;
  lastUpdatedAt: string;
  mimeType: string;
  chunkCount: number;
  totalSize: number;
  status: "recording" | "paused" | "completed" | "interrupted";
}

interface AudioChunk {
  sessionId: string;
  index: number;
  data: Blob;
  timestamp: string;
}

class AudioStorageService {
  private db: IDBDatabase | null = null;
  private dbPromise: Promise<IDBDatabase> | null = null;

  /**
   * Initialise la connexion à IndexedDB
   */
  private async getDB(): Promise<IDBDatabase> {
    if (this.db) return this.db;

    if (this.dbPromise) return this.dbPromise;

    this.dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error("Erreur ouverture IndexedDB:", request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Store pour les chunks audio
        if (!db.objectStoreNames.contains(CHUNKS_STORE)) {
          const chunksStore = db.createObjectStore(CHUNKS_STORE, {
            keyPath: ["sessionId", "index"],
          });
          chunksStore.createIndex("sessionId", "sessionId", { unique: false });
        }

        // Store pour les métadonnées de session
        if (!db.objectStoreNames.contains(SESSIONS_STORE)) {
          const sessionsStore = db.createObjectStore(SESSIONS_STORE, {
            keyPath: "id",
          });
          sessionsStore.createIndex("status", "status", { unique: false });
          sessionsStore.createIndex("caseId", "caseId", { unique: false });
        }
      };
    });

    return this.dbPromise;
  }

  /**
   * Démarre une nouvelle session d'enregistrement
   */
  async startSession(caseId: string, name: string, mimeType: string): Promise<string> {
    const db = await this.getDB();
    const sessionId = `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const session: RecordingSession = {
      id: sessionId,
      caseId,
      name,
      startedAt: new Date().toISOString(),
      lastUpdatedAt: new Date().toISOString(),
      mimeType,
      chunkCount: 0,
      totalSize: 0,
      status: "recording",
    };

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([SESSIONS_STORE], "readwrite");
      const store = transaction.objectStore(SESSIONS_STORE);
      const request = store.add(session);

      request.onsuccess = () => resolve(sessionId);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Sauvegarde un chunk audio
   */
  async saveChunk(sessionId: string, index: number, data: Blob): Promise<void> {
    const db = await this.getDB();

    const chunk: AudioChunk = {
      sessionId,
      index,
      data,
      timestamp: new Date().toISOString(),
    };

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([CHUNKS_STORE, SESSIONS_STORE], "readwrite");

      // Sauvegarder le chunk
      const chunksStore = transaction.objectStore(CHUNKS_STORE);
      chunksStore.put(chunk);

      // Mettre à jour la session
      const sessionsStore = transaction.objectStore(SESSIONS_STORE);
      const getRequest = sessionsStore.get(sessionId);

      getRequest.onsuccess = () => {
        const session = getRequest.result as RecordingSession;
        if (session) {
          session.chunkCount = Math.max(session.chunkCount, index + 1);
          session.totalSize += data.size;
          session.lastUpdatedAt = new Date().toISOString();
          sessionsStore.put(session);
        }
      };

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  /**
   * Met à jour le statut de la session
   */
  async updateSessionStatus(
    sessionId: string,
    status: RecordingSession["status"]
  ): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([SESSIONS_STORE], "readwrite");
      const store = transaction.objectStore(SESSIONS_STORE);
      const getRequest = store.get(sessionId);

      getRequest.onsuccess = () => {
        const session = getRequest.result as RecordingSession;
        if (session) {
          session.status = status;
          session.lastUpdatedAt = new Date().toISOString();
          store.put(session);
        }
      };

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  /**
   * Récupère une session par ID
   */
  async getSession(sessionId: string): Promise<RecordingSession | null> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([SESSIONS_STORE], "readonly");
      const store = transaction.objectStore(SESSIONS_STORE);
      const request = store.get(sessionId);

      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Récupère les sessions interrompues (pour proposer la récupération)
   */
  async getInterruptedSessions(): Promise<RecordingSession[]> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([SESSIONS_STORE], "readonly");
      const store = transaction.objectStore(SESSIONS_STORE);
      const index = store.index("status");

      const sessions: RecordingSession[] = [];

      // Récupérer les sessions "recording" ou "paused" (interrompues)
      const recordingRequest = index.openCursor(IDBKeyRange.only("recording"));
      const pausedRequest = index.openCursor(IDBKeyRange.only("paused"));

      recordingRequest.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          sessions.push(cursor.value);
          cursor.continue();
        }
      };

      pausedRequest.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          sessions.push(cursor.value);
          cursor.continue();
        }
      };

      transaction.oncomplete = () => resolve(sessions);
      transaction.onerror = () => reject(transaction.error);
    });
  }

  /**
   * Assemble tous les chunks d'une session en un seul Blob
   */
  async assembleRecording(sessionId: string): Promise<Blob | null> {
    const db = await this.getDB();
    const session = await this.getSession(sessionId);

    if (!session) return null;

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([CHUNKS_STORE], "readonly");
      const store = transaction.objectStore(CHUNKS_STORE);
      const index = store.index("sessionId");
      const request = index.openCursor(IDBKeyRange.only(sessionId));

      const chunks: { index: number; data: Blob }[] = [];

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          chunks.push({
            index: cursor.value.index,
            data: cursor.value.data,
          });
          cursor.continue();
        }
      };

      transaction.oncomplete = () => {
        // Trier par index et assembler
        chunks.sort((a, b) => a.index - b.index);
        const blobs = chunks.map((c) => c.data);
        const finalBlob = new Blob(blobs, { type: session.mimeType });
        resolve(finalBlob);
      };

      transaction.onerror = () => reject(transaction.error);
    });
  }

  /**
   * Supprime une session et tous ses chunks
   */
  async deleteSession(sessionId: string): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([CHUNKS_STORE, SESSIONS_STORE], "readwrite");

      // Supprimer tous les chunks de cette session
      const chunksStore = transaction.objectStore(CHUNKS_STORE);
      const index = chunksStore.index("sessionId");
      const cursorRequest = index.openCursor(IDBKeyRange.only(sessionId));

      cursorRequest.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        }
      };

      // Supprimer la session
      const sessionsStore = transaction.objectStore(SESSIONS_STORE);
      sessionsStore.delete(sessionId);

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  /**
   * Nettoie les sessions complétées de plus de 24h
   */
  async cleanupOldSessions(): Promise<void> {
    const db = await this.getDB();
    const cutoffDate = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([SESSIONS_STORE], "readonly");
      const store = transaction.objectStore(SESSIONS_STORE);
      const request = store.openCursor();

      const toDelete: string[] = [];

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          const session = cursor.value as RecordingSession;
          if (session.status === "completed" && session.lastUpdatedAt < cutoffDate) {
            toDelete.push(session.id);
          }
          cursor.continue();
        }
      };

      transaction.oncomplete = async () => {
        for (const sessionId of toDelete) {
          await this.deleteSession(sessionId);
        }
        resolve();
      };

      transaction.onerror = () => reject(transaction.error);
    });
  }

  /**
   * Obtient la taille totale utilisée par le stockage audio
   */
  async getStorageSize(): Promise<number> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([SESSIONS_STORE], "readonly");
      const store = transaction.objectStore(SESSIONS_STORE);
      const request = store.openCursor();

      let totalSize = 0;

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          totalSize += (cursor.value as RecordingSession).totalSize;
          cursor.continue();
        }
      };

      transaction.oncomplete = () => resolve(totalSize);
      transaction.onerror = () => reject(transaction.error);
    });
  }
}

// Export singleton
export const audioStorage = new AudioStorageService();
