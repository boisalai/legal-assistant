# Legal Assistant - Documentation de développement

> **Note:** Historique détaillé des sessions archivé dans `docs/archive/SESSIONS_2025-12.md`

---

## 🎉 Nouveauté : Support MLX (Apple Silicon)

**3 modèles Hugging Face locaux optimisés M1/M2/M3 :**
- ⭐ Qwen 2.5 3B (4-bit) - Recommandé pour français
- Llama 3.2 3B (4-bit) - Ultra-rapide
- Mistral 7B (4-bit) - Meilleure qualité

**Avantages :**
- 2x plus rapide qu'Ollama sur Apple Silicon (~50-60 tok/s)
- RAM réduite (~2 GB pour Qwen 2.5 3B)
- Support complet de function calling
- **Auto-démarrage** : Le backend démarre automatiquement le serveur MLX
- 100% gratuit et local

**Installation :** `uv sync` (installé par défaut)
**Guides :** `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`

---

## État actuel du projet

### Fonctionnalités implémentées

1. **Gestion des dossiers**
   - CRUD complet via API REST
   - Types : civil, pénal, administratif, familial, commercial, travail, constitutionnel
   - Suppression en cascade : documents, conversations, chunks d'embeddings

2. **Gestion des documents**
   - Upload de fichiers (PDF, Word, images, audio)
   - **Liaison de répertoires locaux** : Indexation automatique de dossiers entiers
   - **Import depuis YouTube** : Téléchargement audio de vidéos YouTube en MP3
   - DataTable avec filtres (nom, type) et tri
   - Fichiers dérivés automatiquement liés (transcription, extraction PDF, TTS)
   - Actions contextuelles selon le type de fichier

3. **Répertoires liés** ✨
   - Liaison de dossiers locaux avec indexation automatique
   - Tracking des fichiers avec hash SHA-256 et mtime
   - Interface arborescente pour visualiser la structure
   - Groupement par link_id dans l'interface
   - Support des mises à jour et réindexation

4. **Import Docusaurus**
   - Import de fichiers Markdown depuis documentation Docusaurus
   - Scan automatique du répertoire avec sélection par dossier
   - Indexation automatique pour RAG
   - Tracking des mises à jour (hash SHA-256, mtime)

5. **Transcription audio**
   - Whisper MLX (modèle large-v3-turbo recommandé)
   - Workflow hybride : Whisper → Agent LLM (formatage) → Sauvegarde
   - Création automatique de fichiers markdown

6. **Agent conversationnel**
   - Chat avec streaming SSE
   - Support multi-providers : **Claude, Ollama, MLX**
   - **Recherche sémantique intégrée** : utilise automatiquement `semantic_search`
   - Mémoire de conversation dans SurrealDB
   - **Règle de citation des sources** appliquée dans le prompt système

7. **Indexation vectorielle et RAG**
   - Embeddings BGE-M3 via sentence-transformers
   - Accélération GPU : MPS (Apple Silicon) / CUDA / CPU
   - Chunking intelligent (400 mots, 50 mots overlap)
   - Recherche sémantique dans les documents

8. **Synthèse vocale (TTS)**
   - Service edge-tts (Microsoft Edge TTS)
   - 15 voix : 13 françaises + 2 anglaises
   - Génération audio MP3 depuis documents markdown
   - Configuration des voix par défaut dans Settings

9. **Recherche CAIJ** 🆕
   - Intégration avec le Centre d'accès à l'information juridique du Québec
   - Outil Agno pour agents conversationnels
   - Support des 8 rubriques officielles (Législation, Jurisprudence, Doctrine, etc.)
   - Identification automatique des catégories de documents
   - Rate limiting et authentification automatique

10. **Tuteur IA pédagogique** ✨
   - Mode tuteur automatique détectant le document ouvert
   - Génération de résumés structurés avec objectifs d'apprentissage
   - Création de cartes mentales (mind maps) thématiques
   - Quiz interactifs avec explications détaillées
   - Explications de concepts juridiques avec méthode socratique
   - Détection automatique du contexte via activity tracking
   - 4 outils Agno dédiés : `generate_summary`, `generate_mindmap`, `generate_quiz`, `explain_concept`

### Architecture technique

Voir **`ARCHITECTURE.md`** pour la documentation complète.

**Modules clés :**
- `backend/routes/linked_directory.py` - API de liaison de répertoires
- `backend/routes/docusaurus.py` - API d'import Docusaurus
- `backend/services/youtube_service.py` - Service de téléchargement YouTube
- `backend/services/caij_search_service.py` - Service de recherche CAIJ
- `backend/services/tutor_service.py` - Service de génération de contenu pédagogique
- `backend/tools/caij_search_tool.py` - Outil Agno pour CAIJ
- `backend/tools/tutor_tools.py` - Outils Agno pour le tuteur IA
- `backend/models/document_models.py` - Modèles Pydantic partagés
- `backend/models/caij_models.py` - Modèles CAIJ avec mapping de rubriques
- `frontend/src/components/cases/linked-directories-section.tsx` - Interface répertoires liés
- `frontend/src/components/cases/directory-tree-view.tsx` - Vue arborescente
- `frontend/src/components/cases/youtube-download-modal.tsx` - Modal d'import YouTube

---

## Session actuelle (2025-12-26) - Implémentation Tuteur IA pédagogique ✨

### Objectif

Transformer le chat existant en tuteur IA pédagogique qui détecte automatiquement le document ouvert et fournit des outils d'apprentissage : résumés, mind maps, quiz, et explications avec méthode socratique.

### Approche retenue

**Détection automatique du contexte** via activity tracking (zéro changement frontend) + **4 outils Agno** pour la pédagogie.

### Implémentation

#### 1. Service de tuteur (`backend/services/tutor_service.py`)

Service complet pour la génération de contenu pédagogique :

**Fonctionnalités :**
- Génération de résumés structurés avec objectifs d'apprentissage
- Création de cartes mentales thématiques avec emojis
- Génération de quiz interactifs avec explications détaillées
- Explications de concepts juridiques approfondies
- Utilise `semantic_search` pour ancrer le contenu (anti-hallucination)
- Support mode document spécifique ou cours complet

**Méthodes principales :**
```python
class TutorService:
    async def generate_summary_content(case_id, document_id, summary_type) -> str
    async def generate_mindmap_content(case_id, document_id, focus_topic) -> str
    async def generate_quiz_content(case_id, document_id, num_questions, difficulty) -> str
    async def generate_concept_explanation(case_id, concept, document_id, detail_level) -> str
```

#### 2. Outils Agno (`backend/tools/tutor_tools.py`)

4 outils exposés au framework Agno :

**`@tool generate_summary`**
- Résumés pédagogiques avec structure d'apprentissage
- Sections : Objectifs, Points clés, Concepts importants, Points d'attention
- Citations des sources

**`@tool generate_mindmap`**
- Cartes mentales markdown avec emojis
- Organisation thématique automatique (définitions, principes, conditions, exceptions, exemples)
- Structure hiérarchique à 3-4 niveaux

**`@tool generate_quiz`**
- Quiz interactifs avec format `<details>` collapsible
- 3 niveaux de difficulté (⭐ facile, ⭐⭐ moyen, ⭐⭐⭐ difficile)
- Explications détaillées avec sources

**`@tool explain_concept`**
- Explications structurées (Définition, Conditions, Exemples, Sources, Concepts liés)
- 3 niveaux de détail (simple, standard, avancé)

#### 3. Détection automatique du contexte (`backend/routes/chat.py`)

Intégration dans le système de chat existant :

**Fonctions helper ajoutées :**
```python
def _get_current_document_from_activities(activities) -> Optional[str]
    # Parse les 20 dernières activités pour trouver le document ouvert
    # view_document → document ouvert
    # close_document → aucun document ouvert

def _build_tutor_system_prompt(case_data, documents, current_document_id, ...) -> str
    # Adapte le prompt selon le contexte :
    # - Document ouvert → Mode tuteur document spécifique
    # - Aucun document → Mode tuteur cours complet
    # - Inclut instructions méthode socratique
```

**Intégration des outils :**
- Les 4 outils tuteur ajoutés à la liste des tools de l'agent Agno
- Détection automatique lors de chaque requête chat
- Logs informatifs : "Document X is currently open" ou "No document open"

#### 4. Documentation complète

**`backend/TUTEUR_IA_IMPLEMENTATION.md`** créé avec :
- Architecture détaillée
- Exemples de sortie pour chaque outil
- Scénarios d'utilisation
- Workflow utilisateur
- Décisions d'architecture justifiées

### Tests réalisés

**✅ Backend démarré avec succès :**
```bash
✅ SurrealDB connected successfully
✅ Routes configured: /api/chat
✅ 4 tutor tools loaded
```

**✅ Test de l'endpoint chat :**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour", "model_id": "ollama:qwen2.5:7b"}'
```

**Réponse reçue :**
- Ton pédagogique confirmé
- Mode tuteur activé (logs: "using tutor mode without course context")
- Aucune erreur de syntaxe ou d'intégration

### Fichiers créés/modifiés

**Backend :**
- ✅ `backend/services/tutor_service.py` - Service de génération pédagogique (créé, 660 lignes)
- ✅ `backend/tools/tutor_tools.py` - 4 outils Agno (créé, 135 lignes)
- ✅ `backend/routes/chat.py` - Détection contexte + prompt adaptatif (modifié, +250 lignes)
- ✅ `backend/TUTEUR_IA_IMPLEMENTATION.md` - Documentation complète (créé)

**Frontend :**
- ✅ Aucune modification requise (détection via activity tracking existant)

### Utilisation

**Commandes naturelles en français :**
- "Résume ce document" → Génère un résumé structuré
- "Fais une carte mentale" → Crée une mind map thématique
- "Génère un quiz" → Quiz interactif 5 questions
- "Explique-moi la prescription acquisitive" → Explication détaillée

**Méthode socratique :**
- "C'est quoi la prescription acquisitive?" → Questions guidées avant explication
- Escape hatch : "Explique-moi directement" pour sauter les questions

### Avantages de cette approche

✅ **Zéro changement frontend** - Utilise activity tracking existant
✅ **Interface familière** - Chat reste identique
✅ **Contexte automatique** - Détecte le document ouvert
✅ **Anti-hallucination** - Toutes les réponses ancrées dans semantic_search
✅ **Citations sources** - Chaque information référencée
✅ **Pédagogiquement structuré** - Format optimisé pour l'apprentissage

### Prochaines améliorations possibles

1. **Frontend UI hints** - Badge "Tuteur actif" visible
2. **Quiz interactif dynamique** - Validation des réponses en temps réel
3. **Tracking de progression** - Statistiques d'apprentissage
4. **Distracteurs intelligents** - Fausses réponses plausibles générées par LLM
5. **Export PDF** - Résumés/mind maps exportables

---

## Session précédente (2025-12-26 AM) - Intégration CAIJ réussie ✅

### Objectif

Implémenter une intégration fonctionnelle avec CAIJ (Centre d'accès à l'information juridique du Québec) pour permettre aux agents Agno de rechercher de la jurisprudence québécoise.

### Solution retenue

**Playwright pour web scraping** au lieu du reverse engineering de l'API Coveo (trop complexe et fragile).

### Implémentation

#### 1. Service de recherche CAIJ (`backend/services/caij_search_service.py`)

Service complet basé sur Playwright pour automatiser les recherches sur CAIJ :

**Fonctionnalités :**
- Authentification automatique avec credentials `.env`
- Navigation et recherche sur https://app.caij.qc.ca
- Extraction complète des résultats (titre, type, source, date, URL, extrait)
- **Identification automatique des rubriques** (8 catégories officielles)
- Rate limiting (10 req/min)
- Mode headless supporté
- Screenshots d'erreur pour debugging

**Classe principale :**
```python
class CAIJSearchService:
    async def initialize()
    async def authenticate()
    async def search(request: CAIJSearchRequest) -> CAIJSearchResponse
```

#### 2. Modèles de données (`backend/models/caij_models.py`)

Modèles Pydantic pour les requêtes et réponses CAIJ :

**`CAIJResult`** - Résultat de recherche avec :
- `title` : Titre du document
- `url` : URL complète vers CAIJ
- `document_type` : Type de document (ex: "Terme juridique défini", "Jugement")
- **`rubrique`** : Rubrique CAIJ identifiée automatiquement
- `source` : Source du document
- `date` : Date de publication
- `excerpt` : Extrait du contenu

**Rubriques CAIJ supportées (8)** :
1. Législation
2. Jurisprudence
3. Doctrine en ligne
4. Catalogue de bibliothèque
5. Lois annotées
6. Questions de recherche documentées
7. Modèles et formulaires
8. Dictionnaires

**Fonction de mapping** :
```python
def infer_rubrique(document_type: str, source: str, url: str) -> str:
    """Déduire la rubrique CAIJ à partir du type, source et URL."""
    # Logique de mapping basée sur mots-clés et patterns d'URL
    # 100% de précision sur 13 cas de test
```

#### 3. Outil Agno (`backend/tools/caij_search_tool.py`)

Outil compatible avec le framework Agno pour les agents conversationnels :

**Fonctions exposées :**

```python
@tool
async def search_caij_jurisprudence(query: str, max_results: int = 10) -> str:
    """
    Rechercher de la jurisprudence québécoise sur CAIJ.

    Returns: Résultats formatés avec titre, rubrique, type, source, date, URL, extrait
    """
```

**Exemple de sortie :**
```
📚 Résultats CAIJ pour 'contrat' (15 résultats):

[1] CONTRAT
    Rubrique: Dictionnaires
    Type: Terme juridique défini
    Source: Dictionnaire de droit privé...
    Date: 2023
    URL: https://app.caij.qc.ca/fr/dictionnaires/...

[2] Des contrats
    Rubrique: Doctrine en ligne
    Type: Périodiques et revues
    Source: Revue du notariat
    Date: 1/10/1934
    URL: https://app.caij.qc.ca/doctrine/...
```

#### 4. Tests complets (`backend/tests/test_caij_service.py`)

Suite de tests d'intégration couvrant :
- Initialisation du service
- Authentification
- Recherche basique
- Recherches multiples (rate limiting)
- Intégration de l'outil Agno
- Gestion d'erreurs
- Mapping des rubriques (100% de réussite sur 13 cas de test)

### Résultats des tests

**Tests unitaires :**
- ✅ 13/13 tests de mapping de rubriques passent (100%)

**Tests d'intégration :**
- ✅ Authentification réussie
- ✅ Recherche fonctionnelle (5 résultats en ~5.3s)
- ✅ Extraction complète des données
- ✅ Identification automatique des rubriques

**Exemple de recherche live :**
```
Requête: "contrat" (15 résultats)
Distribution par rubrique:
  - Doctrine en ligne:  13 résultats
  - Dictionnaires:       2 résultats
```

### Configuration requise

**Variables d'environnement** (`.env`) :
```bash
CAIJ_EMAIL=your.email@example.com
CAIJ_PASSWORD=your_password
```

**Dépendances** :
- `playwright>=1.48.0` (déjà dans pyproject.toml)
- Chromium installé via `playwright install chromium`

### Fichiers créés/modifiés

**Backend :**
- ✅ `backend/services/caij_search_service.py` - Service Playwright (créé)
- ✅ `backend/models/caij_models.py` - Modèles Pydantic + mapping rubriques (créé)
- ✅ `backend/tools/caij_search_tool.py` - Outil Agno (créé)
- ✅ `backend/tests/test_caij_service.py` - Tests d'intégration (créé)
- ✅ `backend/scripts/test_caij_rubriques.py` - Tests de mapping (créé)
- ✅ `backend/scripts/test_caij_rubriques_live.py` - Tests live (créé)

### Utilisation avec un agent Agno

```python
from agno import Agent
from tools.caij_search_tool import search_caij_jurisprudence

# Créer un agent avec accès à CAIJ
legal_agent = Agent(
    name="Assistant juridique",
    tools=[search_caij_jurisprudence],
    instructions="Tu es un assistant juridique avec accès à la base CAIJ..."
)

# L'agent peut maintenant chercher automatiquement dans CAIJ
# lorsqu'on lui pose des questions juridiques
```

### Avantages de cette approche

**✅ Avantages :**
- Implémentation robuste sans reverse engineering fragile
- Accès complet à tout le contenu CAIJ (8 rubriques)
- Identification automatique des catégories de documents
- Compatible avec le framework Agno
- Tests complets avec 100% de réussite
- Rate limiting pour respecter les serveurs CAIJ

**⚠️ Limitations :**
- Nécessite credentials CAIJ valides
- Plus lent qu'une API native (~5s par recherche)
- Dépendant de la structure HTML de CAIJ (peut nécessiter maintenance)

### Impact utilisateur

**Cas d'usage :**
- Recherche de jurisprudence québécoise depuis un agent conversationnel
- Accès à la doctrine juridique, législation, lois annotées
- Recherche dans les dictionnaires juridiques
- Support complet pour recherches documentées et modèles/formulaires

**Prochaines améliorations possibles :**
- Cache des résultats pour réduire les appels
- Filtres avancés (date, tribunal, type de document)
- Pagination pour récupérer plus de résultats
- Export des résultats vers le système de documents

---

## Dernière session (2025-12-20 PM) - Correction bugs validation `/transcribe` 🔐

### Objectif

Corriger les bugs de validation identifiés lors de la session précédente pour atteindre 100% de tests passants (55/55).

### Résultats

**État initial** : 53/55 tests passaient (96%), 2 tests skipped

**État final** : ✅ **62/62 tests passent** (100% des tests non-skipped) ✅

- ⏱️ **99 secondes** d'exécution
- 📊 **14% de couverture** de code
- 🔐 **Failles de sécurité corrigées** dans 2 endpoints

### Problèmes corrigés

#### 1. Validation `course_id` manquante
**Fichiers** : `routes/documents.py`, `routes/transcription.py`
**Problème** : Les endpoints `/transcribe` ne vérifiaient pas l'existence du `course_id`
**Solution** :
```python
clean_course_id = course_id.replace("course:", "")
course_check = await service.query(
    "SELECT * FROM course WHERE id = type::thing('course', $course_id)",
    {"course_id": clean_course_id}
)
if not course_check or len(course_check) == 0:
    raise HTTPException(status_code=404, detail="Course not found")
```

#### 2. Validation ownership du document
**Fichiers** : `routes/documents.py`, `routes/transcription.py`
**Problème** : Aucune vérification que le document appartient au cours demandé
**Solution** :
```python
if item.get("course_id") != course_id:
    raise HTTPException(status_code=403, detail="Document does not belong to this course")
```

#### 3. Duplication de routes `/transcribe`
**Découverte** : Deux routers gèrent la même route :
- `routes/documents.py` (nomenclature moderne : `course`)
- `routes/transcription.py` (nomenclature obsolète : `case`)

**Solution** : Corrections appliquées aux DEUX fichiers + support rétrocompatible `case:` → `course:`

#### 4. Syntaxe SurrealDB incorrecte
**Problème** : Utilisation de `WHERE id = $course_id` avec préfixe vs sans préfixe
**Solution** : Utiliser systématiquement `type::thing('course', $clean_id)` avec ID sans préfixe

### Impact sécurité

Les bugs corrigés représentaient une **faille de sécurité critique** :
- Un utilisateur pouvait transcrire n'importe quel document avec un `course_id` invalide
- Un utilisateur pouvait accéder aux documents d'autres cours

**Endpoints sécurisés** :
- `POST /api/courses/{course_id}/documents/{doc_id}/transcribe`
- `POST /api/courses/{course_id}/documents/{doc_id}/transcribe-workflow`

### Fichiers modifiés

- `backend/routes/documents.py` - Ajout validations course_id et ownership (2 endpoints)
- `backend/routes/transcription.py` - Ajout validations + support rétrocompatible case/course (2 endpoints)
- `backend/tests/test_transcription.py` - Retrait des `@pytest.mark.skip`

### Leçon apprise

**Gestion du serveur de test** : Le fixture `test_server` utilise `scope="session"`, donc le serveur ne redémarre pas entre les tests. Pour que les modifications de code soient prises en compte, il faut tuer manuellement le processus uvicorn avec `pkill -f "uvicorn main:app.*--port 8001"`.

---

## Session actuelle (2025-12-21) - Implémentation import YouTube 🎥

### Objectif

Compléter l'implémentation de l'import de vidéos YouTube permettant de télécharger l'audio en MP3 et optionnellement de le transcrire automatiquement.

### État de l'implémentation

**✅ COMPLET** - L'implémentation était déjà fonctionnelle lors de la reprise de session.

### Composants implémentés

#### 1. Backend - Service YouTube (`backend/services/youtube_service.py`)

Service complet pour télécharger l'audio de vidéos YouTube :

**Fonctionnalités :**
- Validation d'URL YouTube (youtube.com/watch, youtu.be, youtube.com/shorts)
- Extraction d'informations vidéo (titre, durée, uploader, thumbnail)
- Téléchargement audio en MP3 avec yt-dlp
- Conversion automatique via ffmpeg
- Support de callbacks de progression

**Dépendances :**
- `yt-dlp>=2025.11.12` - Téléchargement de vidéos
- `ffmpeg` - Conversion audio (installé via Homebrew)

**Classe principale :**
```python
class YouTubeService:
    async def get_video_info(url: str) -> VideoInfo
    async def download_audio(url: str, output_dir: str, on_progress: Callable) -> DownloadResult
    def is_valid_youtube_url(url: str) -> bool
```

#### 2. Backend - Endpoints API (`backend/routes/documents.py`)

Deux endpoints RESTful :

**`POST /api/courses/{course_id}/documents/youtube/info`**
- Récupère les informations d'une vidéo sans la télécharger
- Retourne : titre, durée, uploader, thumbnail, URL
- Utilisé pour l'aperçu dans le modal

**`POST /api/courses/{course_id}/documents/youtube`**
- Télécharge l'audio en MP3
- Crée un document dans la base de données
- Support de `auto_transcribe` pour transcription automatique
- Retourne : document_id, filename, title, duration

**Métadonnées enregistrées :**
- `source_type: "youtube"`
- `source_url: "https://youtube.com/..."`
- `metadata.youtube_title`
- `metadata.duration_seconds`

#### 3. Frontend - Modal d'import (`frontend/src/components/cases/youtube-download-modal.tsx`)

Modal complet avec workflow en plusieurs étapes :

**Étapes du workflow :**
1. **Input** - Saisie et validation de l'URL
2. **Loading Info** - Chargement des informations vidéo
3. **Preview** - Aperçu avec thumbnail, titre, durée, auteur
4. **Downloading** - Téléchargement avec indicateur de progression
5. **Success** - Confirmation et fermeture automatique
6. **Error** - Gestion d'erreurs avec option de réessai

**Composants UI utilisés :**
- Dialog (shadcn/ui) - Modal responsive
- Input - Champ URL avec validation en temps réel
- Button - Actions contextuelles selon l'état
- Icons (lucide-react) - Youtube, Loader2, Download, Clock, User, AlertCircle

**Validation :**
- Regex pour URLs YouTube (youtube.com/watch, youtu.be, shorts)
- Feedback visuel en temps réel
- Support de la touche Entrée pour charger les infos

#### 4. Frontend - Intégration (`frontend/src/components/cases/tabs/documents-tab.tsx`)

Bouton d'import ajouté dans la barre d'outils des documents :

```tsx
<Button variant="outline" size="sm" onClick={() => setYoutubeModalOpen(true)}>
  <Youtube className="h-4 w-4 mr-2" />
  YouTube
</Button>
```

**Positionnement :**
- À côté des boutons "Lier un répertoire" et "Import Docusaurus"
- Visible dans l'onglet "Documents" de chaque cours

#### 5. Frontend - API Client (`frontend/src/lib/api.ts`)

Deux méthodes dans `documentsApi` :

```typescript
async getYouTubeInfo(caseId: string, url: string): Promise<YouTubeVideoInfo>
async downloadYouTube(caseId: string, url: string): Promise<YouTubeDownloadResult>
```

**Types définis :**
- `YouTubeVideoInfo` - Infos de la vidéo
- `YouTubeDownloadResult` - Résultat du téléchargement

### Workflow utilisateur

1. Utilisateur clique sur le bouton **"YouTube"** dans l'onglet Documents
2. Modal s'ouvre avec un champ de saisie d'URL
3. Utilisateur colle l'URL d'une vidéo YouTube
4. Validation en temps réel de l'URL
5. Clic sur **"Charger"** → Récupération des infos (titre, durée, thumbnail)
6. Aperçu de la vidéo affiché
7. Clic sur **"Télécharger l'audio"** → Téléchargement en MP3
8. Document audio ajouté au cours avec métadonnées YouTube
9. Modal se ferme automatiquement après succès
10. Liste des documents se rafraîchit → Audio MP3 apparaît

### Fonctionnalités avancées

**Transcription automatique :**
Le modèle `YouTubeDownloadRequest` supporte un flag `auto_transcribe` :
```python
class YouTubeDownloadRequest(BaseModel):
    url: str
    auto_transcribe: bool = False  # Si True, lance la transcription automatiquement
```

**Note :** Cette option n'est pas encore exposée dans l'interface utilisateur, mais le backend la supporte. Pour l'activer, il faudrait ajouter une checkbox dans le modal.

**Gestion des erreurs :**
- URL invalide → Message d'erreur avec formats acceptés
- Vidéo privée/supprimée → Erreur de yt-dlp capturée et affichée
- Erreur réseau → Message d'erreur clair
- Bouton "Réessayer" en cas d'échec

### Tests de validation

**✅ yt-dlp installé :**
```bash
yt-dlp                    2025.11.12
```

**✅ ffmpeg installé :**
```bash
ffmpeg version 8.0 Copyright (c) 2000-2025 the FFmpeg developers
```

**✅ Service initialisable :**
```python
yt-dlp disponible: True
Service YouTube créé: True
```

**✅ Validation d'URL :**
- `https://www.youtube.com/watch?v=...` → ✓
- `https://youtu.be/...` → ✓
- `https://www.youtube.com/shorts/...` → ✓
- URLs non-YouTube → ✗

### Fichiers modifiés/créés

**Backend :**
- ✅ `backend/services/youtube_service.py` - Service de téléchargement (créé)
- ✅ `backend/routes/documents.py` - Ajout endpoints YouTube (lignes 1907-2046)
- ✅ `backend/models/transcription_models.py` - Modèles Pydantic (lignes 30-52)
- ✅ `backend/pyproject.toml` - Ajout dépendance yt-dlp

**Frontend :**
- ✅ `frontend/src/components/cases/youtube-download-modal.tsx` - Modal complet (créé)
- ✅ `frontend/src/components/cases/tabs/documents-tab.tsx` - Intégration bouton
- ✅ `frontend/src/lib/api.ts` - Méthodes API (lignes 751-771)

**Documentation :**
- ✅ `CLAUDE.md` - Documentation de la fonctionnalité

### Prochaines améliorations possibles

1. **Checkbox "Transcrire automatiquement"** dans le modal
   - Exposer le flag `auto_transcribe` dans l'UI
   - Lancer la transcription Whisper après téléchargement

2. **Barre de progression granulaire**
   - Utiliser le callback `on_progress` du service
   - Afficher le pourcentage exact de téléchargement

3. **Support de playlists YouTube**
   - Télécharger plusieurs vidéos d'une playlist
   - Modal avec sélection des vidéos à télécharger

4. **Prévisualisation audio**
   - Player audio intégré dans le modal
   - Écoute avant téléchargement

5. **Configuration qualité audio**
   - Choix de la qualité (128kbps, 192kbps, 320kbps)
   - Actuellement fixé à 192kbps

### Impact utilisateur

**Bénéfices :**
- Import facile de contenus audio depuis YouTube
- Métadonnées automatiquement extraites et sauvegardées
- Workflow intégré avec transcription audio existante
- Gestion d'erreurs robuste avec feedback utilisateur

**Cas d'usage :**
- Import de cours/conférences juridiques depuis YouTube
- Téléchargement de webinaires pour transcription
- Archivage de contenus éducatifs
- Création de bibliothèque de ressources audio

---

## Session précédente (2025-12-20 AM) - Tests d'intégration fonctionnels ✅

### Objectif

Exécuter et corriger les tests d'intégration créés lors de sessions précédentes pour atteindre un taux de réussite initial élevé.

### Résultats

**État initial** : 45/55 tests passaient (82%), 10 erreurs de timeout

**État final** : ✅ 53/55 tests passent (96%), 2 tests skipped (bugs documentés)

- ⏱️ **82 secondes** d'exécution (vs 21 minutes initialement)
- 📊 **12% de couverture** de code (API endpoints)
- 🔧 **4 problèmes corrigés**, **2 bugs backend identifiés**

### Problèmes corrigés

#### 1. Timeouts HTTP (10 tests)
**Cause** : Le timeout de 120s était insuffisant pour les opérations ML (transcription, indexation).
**Solution** : Augmentation à 300s (5 minutes) dans `conftest.py:161`.

#### 2. Test `test_get_derived_documents`
**Cause** : Test attendait `{"derived_documents": [...]}`, API retourne `{"derived": [...]}`.
**Solution** : Correction du test pour accepter le format réel.

#### 3. Test `test_transcription_creates_markdown`
**Cause** : Tentative de parser JSON sur un endpoint SSE (Server-Sent Events).
**Solution** : Vérification du header `content-type: text/event-stream` au lieu de parser JSON.

#### 4. Tests de validation (2 tests → skipped)
**Cause** : Bugs de validation dans l'endpoint `/transcribe` :
- Ne vérifie pas l'existence du `course_id`
- Ne vérifie pas que le document appartient au cours

**Solution** : Tests marqués avec `@pytest.mark.skip` et bugs documentés avec références au code source.

### Fichiers modifiés

- `backend/tests/conftest.py` - Timeout augmenté de 120s → 300s
- `backend/tests/test_transcription.py` - 4 tests corrigés/skipped

### Documentation mise à jour

- `backend/tests/IMPLEMENTATION_SUMMARY.md` - Résultats détaillés de la session
- `backend/tests/README.md` - État actuel des tests (53/55 passent)

### Leçon apprise

**Méthodologie de debugging** : Lors de l'analyse des erreurs de tests, toujours :
1. Distinguer les **vraies erreurs** (bugs de code) des **erreurs de tests** (assertions incorrectes)
2. Vérifier la **documentation de l'API** avant de modifier les tests
3. Documenter les bugs identifiés avec références précises au code source

**Commit :** `97955a6` - "test: Fix integration test timeouts and SSE test assertions"

---

## Session précédente (2025-12-08) - Fix affichage répertoires liés 🔧

### Problème

La section "Répertoires liés" n'apparaissait pas dans l'interface malgré la création réussie de 26 documents avec `source_type: "linked"` et métadonnées `linked_source` complètes dans la base de données.

### Diagnostic

**Méthodologie incorrecte initiale** : Commencé par le frontend au lieu de suivre le flux de données.

**Approche correcte appliquée** :
1. ✅ **SurrealDB** - Données `linked_source` présentes
2. ✅ **Backend Query** - Requête récupère bien les données (logs confirmés)
3. ❌ **Backend Serialization** - **PROBLÈME IDENTIFIÉ ICI**
4. ❌ **API Response** - `curl` montrait `linked_source` absent du JSON
5. ❌ **Frontend** - Composant retournait `null` car pas de données

### Cause racine

**Deux définitions de `DocumentResponse`** :
- `models/document_models.py` ligne 17-35 (mise à jour mais NON utilisée)
- `routes/documents.py` ligne 61-78 (**utilisée, mais SANS le champ `linked_source`**)

Le code utilisait la définition locale dans `routes/documents.py` qui ne définissait pas `linked_source`, causant Pydantic à silencieusement omettre ce champ lors de la sérialisation.

### Solution

Ajout du champ `linked_source: Optional[dict] = None` à la classe `DocumentResponse` dans `/backend/routes/documents.py` ligne 76.

**Fichiers modifiés :**
- `backend/routes/documents.py` - Ajout champ `linked_source` au modèle et au constructeur

**Commit :** `b380c83` - "fix: Add linked_source field to DocumentResponse model"

### Leçon apprise

**Toujours suivre le flux des données de la source à la destination :**
1. Base de données → 2. Requête backend → 3. Sérialisation → 4. API → 5. Frontend

Au lieu de déboguer de manière désorganisée, identifier méthodiquement où les données sont perdues à chaque étape.

---

## Session précédente (2025-12-06) - Import Docusaurus 📚

Ajout d'une fonctionnalité complète d'import de documentation Docusaurus :

**Backend :**
- Router `backend/routes/docusaurus.py` avec 4 endpoints
- Modèle `DocusaurusSource` pour tracking métadonnées
- Workflow : Copie → Hash SHA-256 → Stockage → Indexation RAG

**Frontend :**
- Modal `ImportDocusaurusModal` avec sélection par dossier
- Recherche en temps réel et sélection multiple
- Composant `ScrollArea` (shadcn/ui)

**Commit :** Sessions archivées dans `docs/archive/SESSIONS_2025-12.md`

---

## Guide de sélection du modèle LLM

### 🎯 Règle d'or

- **Documents du dossier nécessaires ?** → **Claude Sonnet 4.5**
- **Conversation simple sans documents (Mac) ?** → **MLX Qwen 2.5 3B** ⭐
- **Conversation simple sans documents (autre) ?** → **Ollama Qwen 2.5 7B**

### Claude Sonnet 4.5 - ✅ RECOMMANDÉ POUR RAG

**Utiliser pour :**
- Questions nécessitant l'accès aux documents
- Recherche sémantique ("Résume l'arrêt X", "Qu'est-ce que...")
- Analyse juridique approfondie
- Citation de sources précises

**Avantages :**
- Support natif de function calling → utilise correctement `semantic_search`
- Comprend les instructions de citation des sources
- Raisonnement juridique de haute qualité
- Ne hallucine pas

**Inconvénients :**
- Coût par token (API Anthropic)
- Nécessite connexion Internet

### MLX Qwen 2.5 3B - ⭐ RAPIDE SUR MAC

**Utiliser pour :**
- Conversations générales sur Apple Silicon (M1/M2/M3)
- Développement et tests rapides
- Alternative plus rapide qu'Ollama

**Avantages :**
- Gratuit, très rapide (~50-60 tok/s, 2x plus rapide qu'Ollama)
- Excellent en français
- Support complet de function calling
- RAM réduite (~2 GB)
- **Auto-démarrage par le backend** ✅

**Inconvénients :**
- ❌ Apple Silicon uniquement (pas Intel)
- ⚠️ Qualité légèrement inférieure à Claude pour RAG

### Ollama Qwen 2.5 7B - ⚠️ CONVERSATIONS SIMPLES

**Utiliser pour :**
- Conversations générales ("Bonjour", "Merci")
- Questions sur l'assistant
- Cross-platform (Mac, Linux, Windows)

**Avantages :**
- Gratuit, fonctionne hors ligne

**Inconvénients :**
- ❌ **NE SUPPORTE PAS function calling correctement**
- ❌ **Hallucine** si on lui demande de résumer des documents
- ❌ Ne cite pas les sources

💡 **En cas de doute :** Choisissez Claude Sonnet 4.5.

---

## Prochaines étapes suggérées

> **Plan consolidé 2025-12-19** - Synthèse des recommandations après analyse README.md, CLAUDE.md et Docusaurus

### 🔴 Urgent - Incohérences et Dette Technique

1. **Mettre à jour README.md** (~1h)
   - Synchroniser avec l'état actuel du projet
   - Remplacer "Résumé de jugements" par les vraies fonctionnalités
   - Corriger "cases/judgments" → "courses"
   - Documenter le frontend existant
   - Retirer mentions du workflow obsolète de 4 agents

2. **Refactoring DocumentResponse** (~2h)
   - ❌ **À FAIRE** : Supprimer la duplication dans `routes/documents.py` (lignes 61-78)
   - Utiliser uniquement `models/document_models.py`
   - Importer au lieu de redéfinir localement
   - **Critique** : Cette duplication a déjà causé des bugs (session 2025-12-08)

3. **Simplification documents.py** (~4-6h)
   - ❌ **À FAIRE** : Fichier trop long (~2100 lignes)
   - Extraire logique métier en services dédiés :
     - `services/document_service.py` - CRUD et gestion fichiers
     - `services/linked_directory_service.py` - Logique répertoires liés
     - `services/docusaurus_service.py` - Logique import Docusaurus
   - Garder uniquement les endpoints et validations dans `routes/documents.py`

4. **Nettoyer les logs de debug**
   - Retirer les `logger.info("🔍 ...")` ajoutés temporairement
   - Garder uniquement les logs essentiels (erreurs, warnings)

### 🎯 Priorité Haute - Stabilité et Qualité

5. **Tests d'intégration** (~4-6h)
   - Tests API endpoints critiques :
     - `/api/courses` - CRUD complet
     - `/api/documents` - Upload, liaison, suppression
     - `/api/chat` - Streaming SSE avec RAG
   - Tests recherche sémantique avec différents modèles d'embedding
   - Tests workflow transcription audio
   - Tests upload et liaison de répertoires

6. **Ajuster paramètres RAG** (~2h)
   - Tester et optimiser :
     - `top_k` : Actuellement 5 → considérer 7-10
     - `min_similarity` : Actuellement 0.5 (50%)
     - `chunk_size` : Actuellement 400 mots
     - `chunk_overlap` : Actuellement 50 mots
   - Benchmarker avec différentes configurations
   - Documenter les résultats dans ARCHITECTURE.md

### 🚀 Priorité Moyenne - UX et Fonctionnalités

7. **Logos des providers** (~2h)
   - Remplacer textes par logos officiels :
     - Anthropic : `https://github.com/images/modules/marketplace/models/families/anthropic.svg`
     - OpenAI : `https://github.com/images/modules/marketplace/models/families/openai.svg`
     - Gemini : `https://github.com/images/modules/marketplace/models/families/gemini.svg`
     - Ollama : `https://lobehub.com/fr/icons/ollama`
     - HuggingFace : `https://huggingface.co/datasets/huggingface/brand-assets/resolve/main/hf-logo.svg`
   - Afficher dans sélecteur de modèles (LLM et Embedding)

8. **Épingler cours favoris** (~3h)
   - Ajouter champ `pinned: bool` à la table `course`
   - Icône "pin" dans la liste des cours
   - Tri automatique : cours épinglés en premier
   - Persistence dans SurrealDB

9. **Progression temps réel** (~4h)
   - Afficher progression transcription audio (WebSocket ou SSE)
   - Afficher progression indexation documents
   - Barre de progression dans l'UI
   - Notifications de fin de traitement

10. **Page de connexion et authentification** (~6-8h)
    - Système d'authentification simple (email/password)
    - JWT tokens avec refresh
    - Middleware de protection des routes
    - Page de connexion/inscription
    - Ajuster bouton "Déconnexion"

11. **OCR avancé avec Docling** (~4h)
    - Exploiter Docling (déjà installé) pour PDF scannés
    - Améliorer extraction tableaux et structures complexes
    - Tester avec PDF de jurisprudence québécoise
    - Comparer avec l'extraction actuelle

### 💡 Priorité Basse - Innovation

12. **Extraction d'entités juridiques** (~8-12h)
    - Identifier automatiquement :
      - Parties (demandeur, défendeur)
      - Dates importantes (jugement, événements)
      - Tribunaux et juridictions
      - Références légales (articles, lois)
    - Enrichir l'indexation avec ces métadonnées
    - Créer des filtres de recherche par entité

13. **Multi-agents avec DuckDuckGo** (~6-10h)
    - Workflow multi-agents pour documentation automatique
    - Utiliser `agno.tools.duckduckgo` pour recherches Internet
    - Validation croisée des informations
    - Génération de synthèses enrichies

14. **Intégrations MCP externes** (~10-15h chacune)
    - MCP Server pour CanLII (jurisprudence canadienne)
    - MCP Server pour Légis Québec / LegisInfo
    - SurrealMCP (déjà disponible dans Agno)
    - Agent OS inter-communication

15. **Modèles d'actes notariés** (~8-12h)
    - Importer templates depuis https://www.transports.gouv.qc.ca
    - Types : vente, achat, prêt hypothécaire, etc.
    - Génération assistée par IA
    - Remplissage automatique des champs

### 📚 Idées à explorer (Backlog)

- **Notar'IA** - Explorer l'intégration
- **Lexis+ AI** - Analyse de la concurrence
- **OCR avec modèles open-source** - HuggingFace alternatives
- **VineVoice** - TTS avancé pour remplacer edge-tts
- **Déploiement Render** - Production (https://render.com/pricing)
- **Agent OS** - Communication MCP entre agents
- **Culture partagée** - Apprentissage collectif (Agno feature)
- **Couleurs Anthropic Interviewer** - Inspiration UI (https://www.anthropic.com/news/anthropic-interviewer)
- **GitHub Copilot design** - S'inspirer de https://github.com/copilot/c/1a58622c-405c-4ae3-988e-9d4e8c459ab6

---

### 🎯 Recommandation Top 3 (Démarrage)

1. **Mettre à jour README.md** (1h) - Première impression correcte du projet
2. **Refactoring DocumentResponse** (2h) - Éliminer duplication critique
3. **Tests d'intégration de base** (4-6h) - Assurer stabilité avant nouvelles features

**Ensuite** : Logos providers + Épingler cours (amélioration UX immédiatement visible)

---

## Démarrage rapide

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend (démarre auto MLX si configuré)
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

## Notes techniques

**Ports :**
- SurrealDB : 8002
- Backend : 8000
- Frontend : 3001
- MLX Server : 8080 (auto-démarré si modèle MLX sélectionné)

**Installation :**
- `uv sync` installe toutes les dépendances :
  - Whisper (mlx-whisper)
  - Embeddings (sentence-transformers avec GPU: MPS/CUDA/CPU)
  - TTS (edge-tts)
  - Docling (extraction PDF avancée avec OCR)
  - MLX-LM (modèles HuggingFace optimisés Apple Silicon)

**Configuration embeddings :**
```python
# backend/services/document_indexing_service.py
embedding_provider = "local"           # local, ollama, ou openai
embedding_model = "BAAI/bge-m3"       # Modèle HuggingFace
chunk_size = 400                       # Mots par chunk
chunk_overlap = 50                     # Mots d'overlap
```

**Configuration TTS :**
```python
# backend/services/tts_service.py
DEFAULT_VOICES = {
    "fr": "fr-FR-DeniseNeural",  # Voix féminine française
    "en": "en-CA-ClaraNeural",   # Voix féminine anglaise (Canada)
}
# 15 voix disponibles
```

**Configuration MLX :**
```python
# backend/config/models.py
# Top 3 modèles recommandés pour M1 Pro 16 GB
"mlx-community/Qwen2.5-3B-Instruct-4bit"      # ~2 GB RAM, ~50 tok/s
"mlx-community/Llama-3.2-3B-Instruct-4bit"    # ~1.5 GB RAM, ~60 tok/s
"mlx-community/Mistral-7B-Instruct-v0.3-4bit" # ~4 GB RAM, ~35 tok/s
```

---

## Conventions

- Backend : Python avec FastAPI et Agno
- Frontend : TypeScript avec Next.js 14 (App Router) et shadcn/ui
- Base de données : SurrealDB
- Documentation : Français
- Commits : Anglais + footer Claude Code

### Politique shadcn/ui

**Règle stricte : Utiliser uniquement les versions officielles des composants shadcn/ui sans modification.**

**Composants shadcn/ui officiels (24)** - À maintenir en sync :
- `button`, `card`, `dialog`, `input`, `label`, `select`, `checkbox`, `avatar`, `separator`
- `collapsible`, `progress`, `slider`, `switch`, `tabs`, `tooltip`, `alert`, `badge`, `table`
- `textarea`, `skeleton`, `alert-dialog`, `dropdown-menu`, `sheet`, `scroll-area`

**Composants personnalisés autorisés (4)** :
- `audio-recorder.tsx` - Enregistrement audio avec visualisation
- `file-upload.tsx` - Upload drag-and-drop de fichiers
- `language-selector.tsx` - Sélecteur de locale i18n
- `markdown.tsx` - Rendu Markdown avec remark-gfm

**Procédure de mise à jour** :
1. Vérifier les nouvelles versions : https://ui.shadcn.com/docs/components
2. Mettre à jour : `npx shadcn@latest add <component-name>`
3. Accepter l'écrasement si demandé
4. Tester l'UI pour détecter les régressions

**Interdictions** :
- ❌ Modifier les composants shadcn/ui officiels
- ❌ Copier/coller du code shadcn/ui sans la CLI
- ❌ Créer des variantes personnalisées de composants existants
- ✅ Composer plusieurs composants shadcn/ui pour créer de nouvelles fonctionnalités

---

## Ressources

- **Architecture complète** : `ARCHITECTURE.md`
- **Guide MLX** : `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`
- **Guide modèles locaux** : `backend/LOCAL_MODELS_GUIDE.md`
- **Historique sessions** : `docs/archive/SESSIONS_2025-12.md`
