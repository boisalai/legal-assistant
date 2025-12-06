# Historique des sessions de développement - Décembre 2025

Ce fichier archive les sessions de développement détaillées pour référence future.

---

## Session du 2025-12-02 (soir) - Débogage et correction du système RAG

**Objectif:** Déboguer l'intégration agent + semantic_search et rendre le RAG pleinement fonctionnel.

### Problème identifié et résolu ✅

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

### Tests effectués et résultats ✅

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

### Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `backend/tools/semantic_search_tool.py:119-123` | **FIX** - Utilisation de `type::thing()` pour les UUIDs |
| `backend/tools/semantic_search_tool.py:56-115` | Ajout de logs détaillés pour débogage |
| `backend/scripts/test_indexing.py` | **NOUVEAU** - Script de test d'indexation |
| `backend/scripts/test_semantic_search_tool.py` | **NOUVEAU** - Script de test de l'outil semantic_search |

### État final du système RAG

**✅ Fonctionnel:**
- Indexation vectorielle avec BGE-M3 sur MPS (GPU Apple Silicon)
- Recherche sémantique par similarité cosinus
- Chunking intelligent avec overlap
- Outil `semantic_search` opérationnel

### Amélioration de la citation des sources ✅

**Problème observé** : Claude Sonnet 4.5 répondait correctement mais sans citer explicitement ses sources.

**Solution appliquée** : Ajout d'une règle de citation obligatoire dans le prompt système (`backend/routes/chat.py:91-96`)

```python
**RÈGLE ABSOLUE - CITATION DES SOURCES**:
- TOUJOURS indiquer la source de chaque information dans ta réponse
- Format obligatoire : "Selon [nom du fichier], ..." ou "D'après [nom du fichier], ..."
- Exemple : "Selon Carter.pdf, l'arrêt Carter c. Canada établit que..."
- Si plusieurs sources, les citer toutes : "D'après Document1.md et Document2.pdf, ..."
- NE JAMAIS présenter une information sans citer sa source
```

### Limitation identifiée : Qwen 2.5 7B ne supporte pas function calling ⚠️

**Observation** : Qwen 2.5 7B hallucine du contenu au lieu d'utiliser l'outil `semantic_search`.

**Diagnostic** :
- Qwen 2.5 7B supporte techniquement les outils (tool calling dans le template Ollama)
- Mais en pratique, le modèle ne comprend pas quand et comment utiliser les outils
- Résultat : Répond avec ses connaissances générales au lieu de chercher dans les documents

**Décision architecture** : Laisser l'utilisateur choisir le modèle selon le cas d'usage
- **Claude Sonnet 4.5** : Questions nécessitant RAG (accès aux documents)
- **Qwen 2.5 7B** : Conversations simples sans accès aux documents

---

## Session du 2025-12-02 (après-midi) - Audit et amélioration de la recherche sémantique

**Objectif:** Vérifier l'état de l'implémentation de la recherche sémantique et de la mémoire de conversation.

### Audit effectué

**✅ Ce qui fonctionne déjà:**

1. **Recherche sémantique intégrée au chat** (`backend/routes/chat.py:364`)
   - L'outil `semantic_search` est disponible pour l'agent
   - Instructions claires dans le prompt système pour l'utiliser en priorité
   - Intégration complète avec tous les autres outils

2. **Mémoire de conversation dans SurrealDB** (`backend/services/conversation_service.py`)
   - Service complet avec CRUD
   - Sauvegarde automatique de chaque message (user et assistant)
   - Métadonnées incluses : model_id, sources consultées
   - API endpoints complets

3. **MPS (Apple Silicon GPU) pour embeddings** (`backend/services/embedding_service.py:128-136`)
   - Détection automatique : MPS > CUDA > CPU
   - Modèle BGE-M3 se charge sur MPS automatiquement
   - Logs explicites pour confirmation

**❌ Ce qui manquait:**

- **Suppression en cascade de l'historique des conversations**
- **Suppression des chunks d'embeddings**

### Implémentation effectuée

**Suppression en cascade complète** (`backend/routes/judgments.py:499-552`)

Lors de la suppression d'un dossier, le système efface maintenant dans l'ordre :

1. **Fichiers physiques** : répertoire uploads complet
2. **Historique des conversations** : table `conversation`
3. **Chunks d'embeddings** : table `document_chunk`
4. **Documents** : table `document`
5. **Dossier lui-même** : table `judgment`

---

## Session du 2025-12-02 (matin) - DataTable pour affichage unifié des documents

**Objectif:** Simplifier l'affichage des documents avec un DataTable moderne.

### Implémentation finale

**Nouveau composant `DocumentsDataTable`** avec :
- DataTable TanStack Table
- Filtres : nom de fichier + type (Source, Transcription, Extraction PDF, Audio TTS)
- Actions contextuelles selon le type de fichier
- Compteur de documents

**Avantages** :
- Code réduit de 200+ lignes à ~15 lignes
- UX professionnelle
- Filtres et tri puissants

---

## Session du 2025-12-01 (soir) - Fichiers dérivés

**Implémentation réalisée** :

1. Nouveaux champs : `source_document_id`, `is_derived`, `derivation_type`
2. Endpoint `list_documents` avec paramètre `include_derived`
3. Workflows modifiés pour créer les champs de dérivation
4. Auto-découverte désactivée par défaut pour éviter duplicatas

---

## Session du 2025-12-01 (matin) - Améliorations de robustesse

1. **Fix : UI affichant "échec"** alors que l'extraction réussissait
   - Solution : Flag `receivedComplete` dans le frontend

2. **Fix : Crashes Ollama** pendant l'indexation
   - Solution : Retry automatique (3 tentatives)

3. **Migration : Ollama → sentence-transformers local avec MPS**
   - Plus stable, plus rapide (GPU)
   - Modèle : `BAAI/bge-m3`

4. **Synthèse vocale (TTS)** :
   - Service edge-tts (Microsoft Edge TTS)
   - 15 voix : 13 françaises + 2 anglaises
   - Génération MP3 avec nettoyage markdown
