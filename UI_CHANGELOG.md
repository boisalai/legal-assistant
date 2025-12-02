# Journal de bord - Améliorations de l'interface utilisateur

## Contexte du projet

**Utilisateur** : Étudiant en droit (bacc.) + maîtrise en IA
**Objectifs** :
- Application d'aide aux études en droit (questions sur documents, résumés, fiches de révision)
- Expérimentation de patterns d'agents (recherche, résumé, quiz, etc.)
- Interface professionnelle pour notaires/avocats

**Pain points identifiés** :
1. ❌ Pas évident qu'un document a été uploadé dans SurrealDB
2. ❌ Pas évident que la recherche RAG a été effectuée
3. ❌ Pas évident que l'agent a analysé le dossier
4. ❌ Progression des workflows non visible
5. ❌ Gestion des fichiers peu claire

---

## Plan d'amélioration proposé (par priorité)

### 🎯 Phase 1 : Transparence et feedback (CRITICAL - répond aux pain points)
- [ ] **Étape 1.1** : Indicateurs visuels d'état des documents
- [ ] **Étape 1.2** : Suivi de progression des workflows en temps réel
- [ ] **Étape 1.3** : Amélioration de la gestion des fichiers avec états clairs

### 🔍 Phase 2 : Outils d'étude et d'exploration
- [ ] **Étape 2.1** : Suggestions contextuelles dans l'assistant (quiz, résumé, fiche)
- [ ] **Étape 2.2** : Historique des conversations sauvegardé par dossier
- [ ] **Étape 2.3** : Export de fiches de révision en markdown

### 🧪 Phase 3 : Expérimentation d'agents
- [ ] **Étape 3.1** : Sélecteur de "patterns d'agents" dans l'interface
- [ ] **Étape 3.2** : Dashboard d'observabilité des agents (traces, logs)
- [ ] **Étape 3.3** : Comparaison de modèles LLM côte à côte

### 🎨 Phase 4 : Professionnalisation de l'interface
- [ ] **Étape 4.1** : Système d'onglets pour navigation claire
- [ ] **Étape 4.2** : Dashboard avec statistiques et métriques
- [ ] **Étape 4.3** : Command palette (Cmd+K) pour navigation rapide

---

## Modifications effectuées

### Date : 2025-12-01

#### ✅ Étape 1.1 : Indicateurs visuels d'état des documents
**Objectif** : Résoudre les pain points #1 (upload dans DB), #2 (RAG effectué), #5 (gestion fichiers)

**Modifications apportées** :

1. **Section récapitulative discrète** (`case-details-panel.tsx:399-438`)
   - Affichage compact des statistiques d'indexation
   - Compte : documents indexés, mots totaux, transcriptions, non indexés
   - Design discret : bg-muted/30, text-xs, border léger
   - S'affiche uniquement si des documents sont indexés

2. **Tooltip enrichi sur l'icône Database** (`case-details-panel.tsx:464-468`)
   - Affiche le nombre de mots extraits
   - Indique que le document est disponible pour RAG
   - Format : "✅ Texte indexé dans SurrealDB\n📄 X mots extraits\n🔍 Disponible pour recherche RAG"

3. **Menu contextuel réorganisé** (`case-details-panel.tsx:480-548`)
   - Groupement logique des actions :
     - GESTION DU FICHIER : Visualiser
     - INDEXATION (RAG) : Indexer, Réindexer, Retirer
     - AUDIO : Transcrire en markdown
     - DANGER : Retirer du dossier
   - Terminologie claire : "Indexer dans la base de données" au lieu de "Charger"
   - Action "Réindexer (mettre à jour)" pour documents déjà indexés

4. **Affichage des sources consultées** (Frontend)
   - `assistant-panel.tsx:20-24` : Ajout du champ `sources` à l'interface Message
   - `assistant-panel.tsx:289-293` : Capture des sources depuis la réponse API
   - `assistant-panel.tsx:416-438` : Affichage automatique des sources sous chaque réponse
   - Design discret : bg-muted/50, text-xs, liste avec icône Database
   - Affiche : nom du fichier, type (transcription), nombre de mots

5. **Backend : retour des sources utilisées**
   - `chat.py:43-48` : Nouveau modèle DocumentSource (name, type, word_count, is_transcription)
   - `chat.py:56` : Ajout du champ `sources` à ChatResponse
   - `chat.py:173-218` : Collecte des sources lors de l'injection du contexte RAG
   - `chat.py:309` : Retour des sources dans la réponse

6. **Types TypeScript** (`api.ts:687-698`)
   - Interface DocumentSource ajoutée
   - Champ `sources` ajouté à ChatResponse

**Fichiers modifiés** :
- `frontend/src/components/cases/case-details-panel.tsx` (4 modifications)
- `frontend/src/components/cases/assistant-panel.tsx` (3 modifications)
- `frontend/src/lib/api.ts` (1 modification)
- `backend/routes/chat.py` (4 modifications)

**Status** : ✅ COMPLÉTÉ
**Approuvé par** : Alain
**Tests effectués** : En attente - À tester par l'utilisateur
**Feedback** : En attente

---

#### 🐛 Étape 1.1.1 : Correction du toast de transcription prématuré
**Objectif** : Corriger le toast "Transcription terminée" qui s'affichait immédiatement

**Problème identifié** :
- Le toast success s'affichait avant la fin réelle de la transcription
- Le système ne vérifiait pas le statut `result.success` du workflow

**Modifications apportées** :
- `case-details-panel.tsx:196-219` : Récupération du `result` de l'API
- Vérification de `result.success` avant d'afficher le toast
- Toast success uniquement si la transcription a réussi
- Toast error avec le message d'erreur si échec

**Fichiers modifiés** :
- `frontend/src/components/cases/case-details-panel.tsx` (1 modification)

**Status** : ✅ COMPLÉTÉ
**Approuvé par** : Alain (via feedback capture d'écran)
**Tests effectués** : En attente - À retester
**Feedback** : Problème identifié et corrigé

---

#### ✅ Étape 1.2 : Workflow PDF → Markdown → Indexation
**Objectif** : Permettre l'extraction de PDFs en markdown formaté avant indexation (cohérence avec workflow audio)

**Problème identifié** :
- PDFs étaient indexés directement avec texte brut
- Incohérence avec le workflow audio (qui crée d'abord un markdown)
- Pas d'utilisation du service `DocumentExtractionService` existant avec MarkItDown

**Décisions prises** :
1. **PDFs ne sont PAS indexés** - Seuls les markdowns sont indexés
2. **Utiliser DocumentExtractionService** avec MarkItDown (déjà implémenté)
3. **Workflow en 2 étapes** :
   - Étape 1 : Extraire PDF → Markdown (MarkItDown détecte structure automatiquement)
   - Étape 2 : Indexer le markdown créé

**Modifications apportées** :

1. **Endpoint backend** (`documents.py:1099-1298`)
   - POST `/documents/{doc_id}/extract-to-markdown`
   - Utilise `DocumentExtractionService` avec MarkItDown
   - Crée un fichier `.md` (ex: `Document.pdf` → `Document.md`)
   - Indexe automatiquement le markdown avec `texte_extrait`
   - Retourne SSE stream avec progression

2. **API Frontend** (`api.ts:434-641`)
   - Interface `PDFExtractionProgress` et `PDFExtractionResult`
   - Fonction `extractPDFToMarkdown()` avec callbacks SSE

3. **Menu contextuel PDF** (`case-details-panel.tsx`)
   - Nouvelle fonction `isPDFFile()` pour détecter les PDFs
   - Handler `handleExtractPDF()` avec gestion d'état
   - Action "Extraire et formater en markdown" dans le menu
   - Badge "Extraction..." pendant le traitement
   - State `extractingPDFDocId` pour UI loading

4. **Suppression fichier redondant**
   - Workflow `extract_pdf.py` supprimé (redondant avec `DocumentExtractionService`)

**Avantages** :
- ✅ Utilise MarkItDown (déjà installé, meilleur que PyPDF2)
- ✅ Détection automatique des structures (titres, sections, listes)
- ✅ Cohérence : Audio → MD → Indexé | PDF → MD → Indexé
- ✅ Pas de coût LLM (MarkItDown fait tout)
- ✅ Support multi-format (PDF, Word, Excel, PowerPoint via MarkItDown)

**Fichiers modifiés** :
- `backend/routes/documents.py` (ajout endpoint + import StreamingResponse)
- `frontend/src/lib/api.ts` (interfaces + fonction extractPDFToMarkdown)
- `frontend/src/components/cases/case-details-panel.tsx` (helper isPDFFile, handler, menu, badge)

**Fichiers supprimés** :
- `backend/workflows/extract_pdf.py` (redondant)

**Status** : ✅ COMPLÉTÉ
**Approuvé par** : Alain
**Tests effectués** : En attente - À tester par l'utilisateur
**Feedback** : En attente

**À tester** :
1. Upload un PDF
2. Clic droit → "Extraire et formater en markdown"
3. Vérifier le cercle qui tourne
4. Vérifier le toast "Markdown créé avec succès"
5. Vérifier qu'un fichier `.md` apparaît dans la liste
6. Vérifier que le `.md` a l'icône Database (indexé)
7. Vérifier que le PDF original n'a PAS l'icône Database
8. Clic droit sur le `.md` → Option "Réindexer" n'apparaît PAS (normal)

**Corrections appliquées** :
- `settings.UPLOAD_DIR` → `settings.upload_dir` (casse incorrecte)
- Menu contextuel markdown : Option "Réindexer" masquée (les `.md` sont déjà à jour)
- Prévention des doublons : Vérification si un `.md` existe déjà avant l'extraction

**Comportement anti-doublon** :
- Si `Document.pdf` → `Document.md` existe déjà, affiche une erreur
- Message : "Un fichier markdown 'Document.md' existe déjà pour ce PDF. Supprimez-le d'abord si vous voulez réextraire."
- Empêche la création de doublons `Document.md`, `Document.md` (2), etc.

---

#### ✅ Étape 1.2.1 : Suppression réelle des fichiers uploadés
**Objectif** : Distinguer fichiers uploadés vs fichiers liés pour la suppression

**Modifications apportées** :

1. **Menu contextuel** (`case-details-panel.tsx:600-601`)
   - **Fichiers uploadés** (dans `data/uploads/`) : "Supprimer du dossier"
   - **Fichiers liés** (chemin externe) : "Retirer du dossier"
   - Détection automatique via `file_path?.includes('data/uploads/')`

2. **Backend suppression** (`documents.py:504-524`)
   - **Fichiers uploadés** : Supprimés du disque ET de la base de données
   - **Fichiers liés** : Supprimés SEULEMENT de la base de données (fichier conservé sur disque)
   - Log détaillé pour tracer les opérations

**Comportement** :
```
Fichier uploadé (data/uploads/1f9fc70e/Document.pdf) :
  → Menu : "Supprimer du dossier"
  → Action : Supprime le fichier physique + supprime la référence DB

Fichier lié (/Users/alain/Documents/Document.pdf) :
  → Menu : "Retirer du dossier"
  → Action : Supprime SEULEMENT la référence DB (fichier conservé)
```

**Fichiers modifiés** :
- `frontend/src/components/cases/case-details-panel.tsx`
- `backend/routes/documents.py`

**Status** : ✅ COMPLÉTÉ
**Approuvé par** : Alain
**Tests effectués** : En attente
**Feedback** : En attente

---

#### 🐛 Étape 1.2.2 : Correction de la modale de suppression et du bug "Document non trouvé"
**Objectif** : Adapter la modale de confirmation selon le type de fichier et corriger l'erreur lors de la suppression

**Problèmes identifiés** :
1. Modale de suppression affichait toujours "Retirer ce document ?" même pour les fichiers uploadés
2. Bouton affichait "Retirer" au lieu de "Supprimer" pour les fichiers uploadés
3. Erreur "Document non trouvé" lors de la suppression de fichiers markdown
4. La fonction `clearText()` était appelée sur les fichiers markdown, causant une erreur

**Modifications apportées** :

1. **Modale de confirmation adaptative** (`case-details-panel.tsx:710-730`)
   - **Fichiers uploadés** (data/uploads/) :
     - Titre : "Supprimer ce document ?"
     - Description : "sera définitivement supprimé du dossier et du disque"
     - Bouton : "Supprimer"
   - **Fichiers liés** (chemin externe) :
     - Titre : "Retirer ce document ?"
     - Description : "sera retiré de ce dossier. Le fichier original ne sera pas supprimé"
     - Bouton : "Retirer"

2. **Correction de handleConfirmDelete** (`case-details-panel.tsx:268-285`)
   - Ajout vérification : Ne pas appeler `clearText()` pour les fichiers markdown
   - Les fichiers markdown stockent leur contenu dans `texte_extrait` mais n'ont pas besoin de "clear"
   - Logique : `if (docToDelete.texte_extrait && !isMarkdown)`

**Fichiers modifiés** :
- `frontend/src/components/cases/case-details-panel.tsx` (2 modifications)
- `backend/routes/documents.py` (ajout logs détaillés pour déboguer "Document non trouvé")

**Status** : 🔍 EN COURS DE DÉBOGAGE
**Approuvé par** : Alain (via capture d'écran bug report)
**Tests effectués** : Erreur "Document non trouvé" persiste, ajout de logs pour identifier la cause
**Feedback** : Débogage en cours - logs ajoutés dans le backend

---

#### ✅ Étape 0.1 : Création du journal de bord
**Fichiers créés** :
- `UI_CHANGELOG.md` - Ce fichier pour tracer toutes les modifications

**Status** : ✅ COMPLÉTÉ
**Approuvé par** : Alain
**Feedback** : Accepté

---

## Notes techniques

### Architecture actuelle
- Frontend : Next.js 14 (App Router) + TypeScript + shadcn/ui
- Backend : FastAPI + Agno + SurrealDB
- État actuel : Split panel (dossier | assistant), preview documents, chat avec streaming

### Conventions
- Commits en anglais avec footer Claude Code
- Documentation en français
- Branches : `feature/ui-[nom-etape]` pour chaque étape

---

#### ✅ Étape 1.2.3 : Suppression idempotente et auto-découverte de fichiers
**Objectif** : Corriger les problèmes de suppression de fichiers et ajouter l'auto-découverte des fichiers orphelins

**Problèmes identifiés** :
1. Erreur 404 lors de la suppression de documents auto-supprimés (race condition)
2. Fichiers markdown non supprimés du disque lors de la suppression
3. Fichiers présents dans `/data/uploads/[id]/` non listés dans l'interface

**Modifications apportées** :

1. **Suppression idempotente** (`documents.py:441-561`)
   - DELETE retourne succès (204) même si le document n'existe plus en base
   - Suppression des fichiers orphelins en cherchant par ID dans le répertoire
   - Distinction entre fichiers uploadés (supprimés) et liés (conservés)
   - Logs détaillés pour tracer les opérations

2. **Auto-découverte de fichiers** (`documents.py:103-244`)
   - Nouveau paramètre `auto_discover` (activé par défaut) dans `list_documents`
   - Scanne le répertoire `/data/uploads/[judgment_id]/`
   - Détecte les fichiers non enregistrés dans la base
   - Enregistre automatiquement avec flag `auto_discovered: true`
   - Affiche immédiatement les fichiers découverts dans l'interface

**Bénéfices** :
- ✅ Plus d'erreurs 404 lors de suppressions multiples
- ✅ Fichiers markdown correctement supprimés du disque
- ✅ Fichiers copiés manuellement détectés automatiquement
- ✅ Synchronisation automatique filesystem ↔ base de données
- ✅ Conformité REST (DELETE idempotent)

**Fichiers modifiés** :
- `backend/routes/documents.py` (2 modifications majeures)

**Status** : ✅ COMPLÉTÉ
**Approuvé par** : Alain (via rapport de bug terminal)
**Tests effectués** : En attente - À tester par l'utilisateur
**Feedback** : En attente

**À tester** :
1. Supprimer un fichier markdown → vérifier qu'il disparaît du disque
2. Copier manuellement un PDF dans `/data/uploads/[id]/` → rafraîchir → vérifier qu'il apparaît
3. Supprimer deux fois le même document → vérifier qu'aucune erreur 404

---

## Backlog d'idées (à prioriser plus tard)
- Annotations PDF
- Mode Picture-in-Picture pour preview
- Recherche globale (Cmd+K)
- Workspaces personnalisables
- Collaboration et partage
