# Legal Assistant - Notes de développement

## État actuel du projet (2025-12-02)

### Fonctionnalités implémentées

1. **Gestion des dossiers (judgments)**
   - CRUD complet via API REST
   - Liste, création, modification, suppression
   - Types de dossiers : civil, pénal, administratif, familial, commercial, travail, constitutionnel
   - **Suppression en cascade complète** : efface automatiquement documents, conversations, et chunks d'embeddings

2. **Gestion des documents**
   - Upload de fichiers (PDF, Word, images, audio)
   - Téléchargement et prévisualisation inline (PDF s'affiche dans le navigateur)
   - Suppression avec nettoyage des fichiers (physiques + base de données)
   - Indicateur "Texte extrait" pour les fichiers transcrits
   - Liaison de fichiers locaux (File System Access API)
   - **DataTable avec filtres** (TanStack Table)
     - Filtrage par nom de fichier
     - Filtrage par type : Tous, Source, Transcription, Extraction PDF, Audio TTS
     - Tri par nom et date
     - Actions contextuelles selon le type de fichier
   - **Fichiers dérivés** automatiquement liés aux sources
     - Champs : `source_document_id`, `is_derived`, `derivation_type`
     - Types : `transcription`, `pdf_extraction`, `tts`
     - Affichage unifié dans le DataTable

3. **Transcription audio**
   - Whisper MLX (modèle large-v3-turbo recommandé)
   - Workflow hybride : Whisper → Agent LLM (formatage) → Sauvegarde
   - Création automatique de fichiers markdown
   - Synchronisation : supprimer une transcription efface `texte_extrait` de l'audio source

4. **Agent conversationnel**
   - Chat avec streaming SSE
   - Outil de transcription intégré (`transcribe_audio`)
   - Support multi-providers : Ollama, Anthropic, OpenAI
   - **Recherche sémantique intégrée** : l'agent utilise automatiquement `semantic_search` pour répondre aux questions
   - **Mémoire de conversation** : historique stocké dans SurrealDB avec métadonnées (modèle utilisé, sources consultées)
   - **Suppression en cascade** : l'historique des conversations est automatiquement supprimé avec le dossier

5. **Configuration LLM**
   - Interface UI pour changer de modèle
   - Persistance des paramètres dans localStorage
   - Chargement automatique de ANTHROPIC_API_KEY depuis .env

6. **Interface utilisateur (UI/UX)**
   - Panel de prévisualisation de documents avec affichage inline PDF
   - Panel Assistant IA avec split vertical lors de la prévisualisation
   - Panneaux redimensionnables (react-resizable-panels)
   - Messages chat avec padding réduit pour une meilleure densité

7. **Indexation vectorielle et recherche sémantique**
   - Embeddings via sentence-transformers (BGE-M3)
   - Accélération GPU avec MPS (Apple Silicon) / CUDA / CPU
   - Chunking intelligent avec overlap (400 mots, 50 mots d'overlap)
   - Recherche sémantique dans les documents via outil `semantic_search`
   - Indexation automatique lors de l'extraction/transcription
   - Retry automatique (3 tentatives) pour robustesse

8. **Synthèse vocale (Text-to-Speech)**
   - Service TTS avec edge-tts (Microsoft Edge TTS)
   - Support français (13 voix : France, Belgique, Canada, Suisse)
   - Support anglais (2 voix : Canada)
   - Génération audio MP3 à partir de documents
   - Nettoyage automatique du markdown avant synthèse
   - Configuration des voix par défaut dans Settings
   - Lecture en un clic depuis le document preview
   - Sauvegarde automatique des fichiers audio comme documents

### Architecture technique

Voir `ARCHITECTURE.md` pour la documentation complète :
- Structure des dossiers
- Services backend (SurrealDB, Whisper, Model Factory)
- Patterns Agno (Workflow déclaratif, hybride, avec classe)
- Routes API
- Composants frontend

### Fichiers clés modifiés récemment

| Fichier | Description |
|---------|-------------|
| `frontend/src/components/cases/documents-data-table.tsx` | **NOUVEAU** - DataTable avec filtres et actions contextuelles |
| `frontend/src/components/cases/case-details-panel.tsx` | Simplifié : utilise maintenant DocumentsDataTable |
| `backend/routes/documents.py` | `include_derived=True` par défaut + champs dérivation |
| `backend/workflows/transcribe_audio.py` | Crée champs `source_document_id`, `is_derived`, `derivation_type` |
| `backend/routes/documents.py` | Extraction PDF et TTS créent aussi les champs de dérivation |
| `frontend/src/lib/api.ts` | Méthode `documentsApi.getDerived()` (utilisée en debug) |

### Session du 2025-12-02 (soir) - Débogage et correction du système RAG

**Objectif:** Déboguer l'intégration agent + semantic_search et rendre le RAG pleinement fonctionnel.

#### Problème identifié et résolu ✅

**Bug critique** : SurrealDB rejetait les requêtes avec des UUIDs contenant des tirets dans les IDs de documents.

```
Erreur: Parse error: Unexpected character `1` expected `c`
SELECT nom_fichier FROM document:637d6a2c-5de1-4080-ab05-39e247eaffdb
                                             ^
```

**Cause** : Les UUIDs avec tirets (`-`) ne sont pas des identifiants valides sans échappement dans SurrealDB.

**Solution appliquée** : Utilisation de `type::thing()` pour gérer correctement les UUIDs.

```python
# Avant (backend/tools/semantic_search_tool.py:119)
doc_result = await surreal_service.query(f"SELECT nom_fichier FROM {doc_id}")

# Après (CORRIGÉ)
doc_result = await surreal_service.query(
    "SELECT nom_fichier FROM type::thing($table, $id)",
    {"table": "document", "id": doc_id.replace("document:", "")}
)
```

#### Tests effectués et résultats ✅

1. **Indexation manuelle d'un document de cours (88KB)**
   - 40 chunks créés (400 mots/chunk, 50 mots overlap)
   - Modèle : BGE-M3 (1024 dimensions)
   - GPU : MPS (Apple Silicon) détecté et utilisé
   - Performance : ~5 chunks/seconde avec embeddings

2. **Recherche sémantique directe (script Python)**
   - Question test : "Qu'est-ce que le droit?"
   - 20 résultats trouvés avec similarité entre 50% et 65%
   - Meilleur résultat (65%) : passage sur "le rapport entre le droit et le bonheur"
   - Performance : < 1 seconde pour la recherche

3. **Test de l'outil semantic_search**
   - Outil fonctionnel avec la correction `type::thing()`
   - Récupération correcte des noms de fichiers
   - Formatage markdown des résultats opérationnel

#### Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `backend/tools/semantic_search_tool.py:119-123` | **FIX** - Utilisation de `type::thing()` pour les UUIDs |
| `backend/tools/semantic_search_tool.py:56-115` | Ajout de logs détaillés pour débogage |
| `backend/scripts/test_indexing.py` | **NOUVEAU** - Script de test d'indexation |
| `backend/scripts/test_semantic_search_tool.py` | **NOUVEAU** - Script de test de l'outil semantic_search |

#### État final du système RAG

**✅ Fonctionnel:**
- Indexation vectorielle avec BGE-M3 sur MPS (GPU Apple Silicon)
- Recherche sémantique par similarité cosinus
- Chunking intelligent avec overlap
- Outil `semantic_search` opérationnel

**⚠️ Reste à faire:**
- Redémarrer le backend pour que le chat utilise la version corrigée
- Tester le chat complet avec des questions réelles
- Ajuster les paramètres (top_k, min_similarity, chunk_size) selon la qualité des réponses
- Documenter les workflows d'utilisation

---

### Session du 2025-12-02 (après-midi) - Audit et amélioration de la recherche sémantique

**Objectif:** Vérifier l'état de l'implémentation de la recherche sémantique et de la mémoire de conversation.

#### Audit effectué

**✅ Ce qui fonctionne déjà:**

1. **Recherche sémantique intégrée au chat** (`backend/routes/chat.py:364`)
   - L'outil `semantic_search` est disponible pour l'agent
   - Instructions claires dans le prompt système pour l'utiliser en priorité
   - Intégration complète avec tous les autres outils (transcription, extraction d'entités, etc.)

2. **Mémoire de conversation dans SurrealDB** (`backend/services/conversation_service.py`)
   - Service complet avec CRUD
   - Sauvegarde automatique de chaque message (user et assistant)
   - Métadonnées incluses : model_id, sources consultées
   - API endpoints complets :
     - `GET /api/chat/history/{case_id}` : récupérer l'historique
     - `DELETE /api/chat/history/{case_id}` : effacer l'historique
     - `GET /api/chat/stats/{case_id}` : statistiques

3. **MPS (Apple Silicon GPU) pour embeddings** (`backend/services/embedding_service.py:128-136`)
   - Détection automatique : MPS > CUDA > CPU
   - Modèle BGE-M3 se charge sur MPS automatiquement
   - Logs explicites pour confirmation

**❌ Ce qui manquait:**

- **Suppression en cascade de l'historique des conversations** : lors de la suppression d'un dossier, les conversations n'étaient pas effacées
- **Suppression des chunks d'embeddings** : les segments vectoriels restaient dans la base après suppression d'un dossier

#### Implémentation effectuée

**Suppression en cascade complète** (`backend/routes/judgments.py:499-552`)

Lors de la suppression d'un dossier (`DELETE /api/judgments/{id}`), le système efface maintenant dans l'ordre :

1. **Fichiers physiques** : répertoire uploads complet
2. **Historique des conversations** : table `conversation`
3. **Chunks d'embeddings** : table `document_chunk` pour chaque document
4. **Documents** : table `document`
5. **Dossier lui-même** : table `judgment`

Chaque étape est protégée par un try/catch pour garantir que les étapes suivantes s'exécutent même si une échoue.

#### Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `backend/routes/judgments.py:499-552` | Ajout suppression en cascade (conversations + chunks + documents) |
| `CLAUDE.md` | Documentation mise à jour avec les nouvelles fonctionnalités |

#### Points importants

- **Ordre de suppression** : Les entités dépendantes (conversations, chunks) sont supprimées AVANT le dossier parent
- **Gestion d'erreurs robuste** : Chaque suppression est dans un try/catch pour éviter les blocages
- **Logs détaillés** : Chaque étape est loguée pour faciliter le débogage
- **Compatibilité** : Support des différents formats de réponse SurrealDB

---

### Session du 2025-12-02 (matin) - DataTable pour affichage unifié des documents

**Objectif:** Simplifier l'affichage des documents en utilisant un DataTable moderne avec filtres au lieu de sous-menus imbriqués.

#### Problème résolu
Les sous-menus contextuels (`DropdownMenuSub`) ne fonctionnaient pas dans l'environnement (problème Radix UI). Pivot vers une solution plus simple et plus professionnelle : DataTable avec filtres.

#### Implémentation finale

**1. Nouveau composant `DocumentsDataTable`** (`frontend/src/components/cases/documents-data-table.tsx`)
   - ✅ DataTable avec TanStack Table (react-table)
   - ✅ **Colonnes:**
     - Nom du fichier (avec icône FileText/FileAudio + indicateur Database si indexé)
     - Type (texte simple : "Source", "Transcription", "Extraction PDF", "Audio TTS")
     - Date (triable)
     - Actions (menu contextuel)
   - ✅ **Filtres:**
     - Recherche par nom de fichier
     - Filtre par type : "Tous les fichiers", "Source", "Transcription", "Extraction PDF", "Audio TTS"
   - ✅ **Actions contextuelles par type de fichier:**
     - **Tous:** Visualiser, Supprimer
     - **PDF:** + Extraire en markdown, Indexer/Réindexer, Retirer de la base
     - **Audio:** + Transcrire en markdown (si pas encore transcrit)
     - **Markdown dérivés:** + Retirer de la base
   - ✅ Compteur de documents affichés

**2. Backend modifié** (`backend/routes/documents.py`)
   - ✅ Changé `include_derived=False` → `include_derived=True` (ligne 112)
   - Le filtrage est maintenant géré côté frontend dans le DataTable
   - L'API retourne TOUS les documents (sources + dérivés)

**3. Frontend simplifié** (`frontend/src/components/cases/case-details-panel.tsx`)
   - ✅ Remplacé ~200 lignes de code de liste avec cards par un simple appel au DataTable (~15 lignes)
   - ✅ Supprimé le code de badges `derivedCounts` devenu inutile
   - ✅ Supprimé le useEffect de chargement des compteurs
   - ✅ Toutes les fonctions existantes (handleExtractPDF, handleTranscribe, etc.) sont passées comme props

**4. Fichiers supprimés (nettoyage)**
   - ❌ `derived-files-modal.tsx` (modal inutilisée)
   - ❌ `derived-files-submenu.tsx` (sous-menu ne fonctionnait pas)
   - ❌ `derived-files-submenu-inline.tsx` (sous-menu inline inutile)

#### Avantages de la solution DataTable

1. **Simplicité:** Une seule table au lieu de multiples sous-menus imbriqués
2. **Clarté:** Voir tous les fichiers (sources + dérivés) d'un coup d'œil
3. **Filtres puissants:** Recherche par nom + filtre par type spécifique
4. **Tri facile:** Cliquez sur les colonnes pour trier
5. **Actions contextuelles:** Menu adapté selon le type de fichier
6. **Maintenabilité:** Code réduit de 200+ lignes à ~15 lignes
7. **Performance:** Pas besoin de charger les compteurs de fichiers dérivés
8. **UX professionnelle:** Interface moderne et intuitive

#### État final (fonctionnel)

- ✅ Affichage unifié des 4 types de documents dans une table
- ✅ Filtres fonctionnels (par nom et par type)
- ✅ Tri fonctionnel (par nom et date)
- ✅ Actions complètes selon le type de fichier
- ✅ Suppression nettoie fichiers physiques + base de données + texte indexé
- ✅ Indicateur visuel pour les documents indexés (icône Database)

---

### Session du 2025-12-01 (soir) - Fichiers dérivés (travail préliminaire)

**Note:** Cette session a permis d'implémenter les champs `source_document_id`, `is_derived` et `derivation_type` dans le backend, qui sont maintenant utilisés par le DataTable. Les sous-menus contextuels tentés dans cette session ne fonctionnaient pas (problème Radix UI).

#### Implémentation réalisée

**Backend:**
1. ✅ Nouveaux champs ajoutés au modèle `Document`:
   - `source_document_id`: ID du document parent
   - `is_derived`: Boolean pour identifier les fichiers dérivés
   - `derivation_type`: Type de dérivation ("transcription", "pdf_extraction", "tts")

2. ✅ Endpoint `list_documents` modifié:
   - Paramètre `include_derived=False` par défaut
   - Filtre SQL: `WHERE (is_derived = false OR is_derived IS NULL)`
   - N'affiche que les fichiers sources dans la liste principale

3. ✅ Nouvel endpoint `GET /api/judgments/{id}/documents/{doc_id}/derived`:
   - Retourne tous les fichiers dérivés d'un document source
   - Format: `{derived: Document[], total: number}`

4. ✅ Workflows modifiés pour créer les nouveaux champs:
   - `workflows/transcribe_audio.py`: Ajoute `source_document_id`, `is_derived=True`, `derivation_type="transcription"`
   - `routes/documents.py` (extraction PDF): Ajoute les 3 champs
   - `routes/documents.py` (TTS): Ajoute les 3 champs

5. ✅ Auto-découverte modifiée:
   - Skip les fichiers `.md` et `.markdown` (toujours des fichiers dérivés)
   - **Désactivée par défaut** (`auto_discover=False`) pour éviter les duplicatas

6. ✅ Vérification d'existence supprimée dans workflow transcription:
   - Remplacée par suppression automatique de l'ancien fichier
   - Permet de retranscrire sans erreur

**Frontend:**
1. ✅ API Client (`frontend/src/lib/api.ts`):
   - Méthode `documentsApi.getDerived(caseId, documentId)` ajoutée

2. ✅ Composant `DerivedFilesSubmenu` créé:
   - Sous-menu contextuel avec `DropdownMenuSub` (shadcn)
   - Affiche les fichiers dérivés avec icônes selon le type
   - Actions: Visualiser, Écouter (TTS), Supprimer
   - S'affiche uniquement si des fichiers dérivés existent

3. ✅ Intégration dans `DocumentsTab`:
   - Composant ajouté dans le menu contextuel des documents
   - Positionné après "Visualiser"

**Migration:**
- ✅ Script `backend/scripts/migrate_derived_documents.py` créé
- Migre les transcriptions, TTS, et extractions PDF existantes
- Non exécuté car données nettoyées

#### Problèmes rencontrés

**Problème principal: Duplicatas de documents**
- SurrealDB tourne dans Docker (`legal-assistant-surrealdb`)
- Chaque rafraîchissement créait des duplicatas (jusqu'à 29 copies du même fichier!)
- Cause: Auto-découverte s'exécutait à chaque appel API
- **Solution appliquée:** `auto_discover=False` par défaut dans `list_documents`

**Problème secondaire: Transcription liée au mauvais audio**
- La transcription pointait vers un ancien duplicata
- L'interface affichait un audio différent (le plus récent)
- Le sous-menu cherchait les dérivés du mauvais document
- **État:** Résolu en théorie par la désactivation de l'auto-découverte

#### État actuel (fin de session)

**Ce qui fonctionne:**
- ✅ Backend: Tous les endpoints créés et testés
- ✅ Champs `is_derived` correctement créés lors des transcriptions
- ✅ API `getDerived()` retourne les bons résultats
- ✅ Auto-découverte ne crée plus de duplicatas (désactivée)
- ✅ Fichiers markdown exclus de l'auto-découverte

**Ce qui ne fonctionne pas encore:**
- ❌ Le sous-menu "Fichiers dérivés" n'apparaît pas dans l'interface
- ❌ Cause probable: Composant `DerivedFilesSubmenu` ne charge pas les données ou problème de timing

**Fichiers modifiés:**
- `backend/routes/documents.py`: Nouveaux champs, endpoint derived, auto_discover=False
- `backend/workflows/transcribe_audio.py`: Nouveaux champs, vérification existence supprimée
- `frontend/src/lib/api.ts`: Méthode getDerived()
- `frontend/src/components/cases/derived-files-submenu.tsx`: Nouveau composant (créé)
- `frontend/src/components/cases/tabs/documents-tab.tsx`: Intégration DerivedFilesSubmenu
- `backend/scripts/migrate_derived_documents.py`: Script de migration (créé)

#### Prochaines étapes (session suivante)

1. **Déboguer le composant DerivedFilesSubmenu:**
   - Vérifier que le composant se charge (console.log)
   - Vérifier l'appel API dans le useEffect
   - Tester avec les DevTools React

2. **Vérifier l'état de la base de données:**
   - S'assurer qu'il n'y a plus de duplicatas
   - Créer un dossier de test propre
   - Uploader un fichier audio manuellement
   - Créer une transcription
   - Vérifier que le sous-menu apparaît

3. **Si le problème persiste:**
   - Ajouter des logs dans le composant
   - Vérifier que `documentId` passé est le bon
   - Tester l'endpoint directement avec curl

4. **Alternative si nécessaire:**
   - Forcer un rafraîchissement après création de transcription
   - Ou afficher un indicateur "(1)" sur le bouton menu si dérivés existent

---

### Dernières modifications (session du 2025-12-01 - matin)

#### Améliorations de robustesse et migration vers embeddings locaux

1. **Fix : UI affichant "échec" alors que l'extraction réussissait**
   - Problème : Le frontend ne détectait pas correctement la fin du stream SSE
   - Solution : Ajout d'un flag `receivedComplete` et gestion d'erreurs améliorée
   - Fichiers : `frontend/src/lib/api.ts` (fonctions `transcribeWithWorkflow` et `extractPDFToMarkdown`)

2. **Fix : Crashes intermittents d'Ollama pendant l'indexation**
   - Problème : Ollama retournait des erreurs EOF aléatoires
   - Solution : Retry automatique (3 tentatives, 2s de délai) + gestion d'erreurs robuste
   - Fichiers : `backend/services/document_indexing_service.py`

3. **Migration : Ollama → sentence-transformers local avec MPS**
   - Pourquoi : Plus stable, plus rapide (GPU), meilleur contrôle
   - Changements :
     - Modèle par défaut : `ollama:bge-m3` → `local:BAAI/bge-m3`
     - Détection automatique GPU : MPS (Apple Silicon) / CUDA / CPU
     - Réduction chunks : 500 → 400 mots pour plus de robustesse
   - Fichiers :
     - `backend/pyproject.toml` : Ajout `sentence-transformers` et `torch` en dépendances par défaut
     - `backend/services/embedding_service.py` : Support MPS/CUDA/CPU automatique
     - `backend/services/document_indexing_service.py` : Changement provider par défaut

4. **Simplification : Dépendances de développement par défaut**
   - `sentence-transformers`, `torch`, `mlx-whisper` installés par défaut
   - Plus besoin de `--extra embeddings` ou `--extra whisper` en développement
   - Un simple `uv sync` suffit pour avoir tous les outils

#### Synthèse vocale (Text-to-Speech)

1. **Service TTS avec edge-tts** (`backend/services/tts_service.py`)
   - Utilisation de Microsoft Edge TTS (gratuit, voix naturelles)
   - 15 voix disponibles : 13 françaises (France, Belgique, Canada, Suisse) + 2 anglaises (Canada)
   - Nettoyage automatique du markdown avant synthèse (suppression de `#`, `**`, `*`, etc.)
   - Génération de fichiers MP3 avec métadonnées complètes
   - Support du contrôle de vitesse et volume

2. **API Endpoints** (`backend/routes/documents.py`)
   - `GET /api/judgments/tts/voices` : Liste des voix disponibles
   - `POST /api/judgments/{judgment_id}/documents/{doc_id}/tts` : Génération audio TTS
   - Sauvegarde automatique des fichiers audio comme nouveaux documents
   - Métadonnées stockées : voix utilisée, langue, durée estimée

3. **Interface utilisateur TTS**
   - **Document Preview** (`frontend/src/components/cases/document-preview-panel.tsx`) :
     - Bouton "Lire" dans le header (visible uniquement si `texte_extrait` disponible)
     - Menu déroulant : choix Français ou English
     - Player audio intégré avec auto-play
     - Gestion d'erreurs avec affichage
   - **Settings** (`frontend/src/app/settings/page.tsx`) :
     - Section "Synthèse vocale (TTS)"
     - Sélection de la voix française par défaut (13 choix)
     - Sélection de la voix anglaise par défaut (2 choix)
     - Sauvegarde dans localStorage (`tts_voice_fr`, `tts_voice_en`)

4. **Workflow utilisateur**
   - Configuration initiale : Settings → choisir voix française et anglaise
   - Utilisation : Document preview → "Lire" → choisir langue
   - La voix configurée dans Settings est utilisée automatiquement
   - L'audio généré est sauvegardé et apparaît dans la liste des documents

5. **Voix disponibles**
   - 🇫🇷 France : Henri, Remy, Vivienne, Denise, Eloise (5 voix)
   - 🇧🇪 Belgique : Charline, Gerard (2 voix)
   - 🇨🇦 Canada français : Antoine, Jean, Sylvie, Thierry (4 voix)
   - 🇨🇭 Suisse : Ariane, Fabrice (2 voix)
   - 🇨🇦 Canada anglais : Clara, Liam (2 voix)

---

## Prochaines étapes suggérées (mise à jour 2025-12-02 soir)

### Immédiat (après redémarrage du backend)

1. **Tester le RAG complet** ✅ **PRIORITÉ HAUTE**
   - Redémarrer le backend pour charger la correction `type::thing()`
   - Tester avec la question : "Résume l'arrêt Carter"
   - Vérifier que l'agent utilise bien `semantic_search`
   - Observer les logs pour confirmer le bon fonctionnement
   - Mesurer la qualité des réponses générées

2. **Ajuster les paramètres RAG selon les résultats**
   - `top_k` : Actuellement 5 résultats, peut-être augmenter à 7-10
   - `min_similarity` : Actuellement 0.5 (50%), peut nécessiter ajustement
   - `chunk_size` : Actuellement 400 mots, optimiser selon la longueur des passages
   - `chunk_overlap` : Actuellement 50 mots, vérifier si suffisant

3. **Documenter l'utilisation du RAG**
   - Créer un guide utilisateur pour la recherche sémantique
   - Expliquer comment indexer les documents
   - Documenter les limitations et meilleures pratiques

### Court terme (améliorations immédiates)

1. **Analyse de dossiers**
   - ❌ **NE PAS FAIRE** : Pas de règles d'analyse précises actuellement

2. **Améliorer l'agent chat**
   - ✅ **FAIT** : Recherche sémantique intégrée (`semantic_search`)
   - ✅ **FAIT** : Mémoire de conversation dans SurrealDB
   - ❌ **REPORTER** : Extraction d'entités juridiques

3. **UI/UX**
   - ❌ **REPORTER** : Progression de transcription en temps réel
   - ✅ **FAIT** : Prévisualisation markdown
   - ✅ **FAIT** : Historique des conversations (API prête)

### Moyen terme (nouvelles fonctionnalités)

1. **RAG (Retrieval-Augmented Generation)** ✅ **FAIT**
   - ✅ Indexation avec embeddings BGE-M3 sur MPS
   - ✅ Recherche sémantique fonctionnelle
   - ✅ Contextualisation des réponses via `semantic_search`

2. **Multi-agents avec DuckDuckGo** 💡 **À EXPLORER**
   - Workflow multi-agents pour documentation automatique
   - Utiliser `agno.tools.duckduckgo` pour recherches Internet
   - Définir un objectif clair (ex: documenter un sujet spécifique)

3. **Intégrations externes** 💡 **BONNE IDÉE**
   - MCP Server pour CanLII (jurisprudence canadienne)
   - MCP Server pour Légis Québec / LegisInfo
   - ❌ **REPORTER** : Export PDF avec table des matières

### Patterns Agno à explorer

Voir `ARCHITECTURE.md` section "Patterns d'agents à explorer" :
- Agent avec outils multiples
- Workflow multi-agents
- RAG
- Agent avec mémoire
- MCP (Model Context Protocol)

---

## Démarrage rapide

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

## Notes techniques

- **Port SurrealDB** : 8002 (modifié de 8001)
- **Port Backend** : 8000
- **Port Frontend** : 3001
- **Installation** : `uv sync` installe toutes les dépendances de développement par défaut
  - Whisper (mlx-whisper pour transcription audio)
  - Embeddings (sentence-transformers avec GPU: MPS/CUDA/CPU)
  - TTS (edge-tts pour synthèse vocale)
  - Docling (extraction avancée PDF avec OCR)
- **Embeddings** : BGE-M3 via sentence-transformers avec accélération GPU (MPS/CUDA/CPU auto-détecté)
- **Whisper** : MLX Whisper optimisé Apple Silicon
- **TTS** : edge-tts (Microsoft Edge TTS) - 15 voix françaises et anglaises
- **Docling** : Extraction avancée de documents (tables, OCR, mise en page)
- **Variables d'environnement** : Voir `.env.example` ou `ARCHITECTURE.md`

### Configuration embeddings

```python
# backend/services/document_indexing_service.py
embedding_provider = "local"           # local, ollama, ou openai
embedding_model = "BAAI/bge-m3"       # Modèle HuggingFace
chunk_size = 400                       # Mots par chunk
chunk_overlap = 50                     # Mots d'overlap
```

### Configuration TTS

```python
# backend/services/tts_service.py
# Voix par défaut
DEFAULT_VOICES = {
    "fr": "fr-FR-DeniseNeural",  # Voix féminine française
    "en": "en-CA-ClaraNeural",   # Voix féminine anglaise (Canada)
}

# 15 voix disponibles au total
# Nettoyage automatique du markdown : suppression de #, **, *, liens, code, etc.
```

### Logs à surveiller lors du démarrage

```
# Embeddings
MPS (Metal Performance Shaders) detecte - utilisation du GPU Apple Silicon
Chargement du modele local: BAAI/bge-m3 sur mps
Modele BAAI/bge-m3 charge sur mps

# TTS
Service TTS initialisé avec edge-tts
Génération TTS avec voix fr-FR-DeniseNeural (rate: +0%, volume: +0%)
Markdown nettoyé: 5432 → 4821 caractères
Audio généré avec succès: /path/to/file.mp3 (123456 bytes)
```

## Conventions

- Backend en Python avec FastAPI et Agno
- Frontend en TypeScript avec Next.js 14 (App Router) et shadcn/ui
- Base de données SurrealDB
- Documentation en français
- Commits avec message en anglais + footer Claude Code
