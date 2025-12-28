# Plan de Refactoring - documents.py

**Date:** 2025-12-28  
**Objectif:** Réduire `routes/documents.py` de 1946 lignes à < 1000 lignes  
**État actuel:** Phase 2 en cours (15/18 endpoints refactorisés)

---

## Analyse Actuelle

### Statistiques
- **Lignes totales:** 1946
- **Fonctions/endpoints:** 18
- **Services déjà utilisés:** `DocumentService` (7 méthodes)
- **Routes séparées existantes:** 
  - `linked_directory.py` (28K)
  - `docusaurus.py` (18K)
  - `transcription.py` (18K)
  - `extraction.py` (19K)

### Endpoints dans documents.py

| Endpoint | Lignes (approx) | Service Utilisé | À Extraire |
|----------|-----------------|-----------------|------------|
| `list_documents` | ~60 | ✅ DocumentService | Logique validation |
| `upload_document` | ~80 | ✅ DocumentService | Validation fichiers |
| `register_document` | ~100 | ✅ DocumentService | - |
| `link_file_or_folder` | ~200 | ❌ | ➡️ LinkedDirectoryService |
| `diagnose_documents` | ~150 | ⚠️ Partiel | ➡️ DocumentService |
| `get_derived_documents` | ~30 | ✅ DocumentService | - |
| `get_document` | ~50 | ✅ DocumentService | - |
| `delete_document` | ~200 | ✅ DocumentService | Cleanup logique |
| `download_document` | ~40 | ❌ | - (simple) |
| `extract_document_text` | ~150 | ❌ | ➡️ ExtractionService |
| `clear_document_text` | ~40 | ❌ | ➡️ DocumentService |
| `transcribe_document` | ~80 | ❌ | ➡️ TranscriptionService |
| `transcribe_document_workflow` | ~100 | ❌ | ➡️ TranscriptionService |
| `extract_pdf_to_markdown` | ~200 | ❌ | ➡️ ExtractionService |
| `_auto_transcribe_youtube` | ~60 | ❌ | ➡️ YouTubeService |
| `get_youtube_info` | ~40 | ❌ | ➡️ YouTubeService |
| `download_youtube_audio` | ~150 | ❌ | ➡️ YouTubeService |
| `list_tts_voices` | ~30 | ❌ | ➡️ TTSService (déjà existe) |
| `generate_tts` | ~100 | ❌ | ➡️ TTSService |

---

## Plan d'Action

### Phase 3.1 - Services YouTube (2-3h)

**Créer:** `services/youtube_service.py` (existe déjà !)

**Extraire depuis documents.py:**
```python
# Déjà implémenté dans services/youtube_service.py
class YouTubeService:
    async def get_video_info(url: str) -> dict
    async def download_audio(url: str, course_id: str) -> dict
```

**Migration:**
1. Vérifier que `services/youtube_service.py` a toutes les méthodes
2. Refactorer les endpoints dans `documents.py` pour utiliser le service
3. Réduire endpoints à ~20 lignes chacun (validation + appel service)

**Réduction estimée:** ~200 lignes

---

### Phase 3.2 - Services Extraction (2-3h)

**Améliorer:** `services/document_extraction_service.py` (existe déjà !)

**Ajouter méthodes manquantes:**
```python
class DocumentExtractionService:
    async def extract_document_text(doc_id: str) -> dict
    async def extract_pdf_to_markdown(doc_id: str, force: bool) -> dict
    async def clear_document_text(doc_id: str) -> dict
```

**Migration:**
1. Déplacer logique d'extraction depuis `documents.py`
2. Simplifier endpoints extraction
3. Utiliser service dans routes

**Réduction estimée:** ~300 lignes

---

### Phase 3.3 - Services Transcription (1-2h)

**Note:** La transcription a déjà sa propre route dans `routes/transcription.py`

**Actions:**
1. Vérifier si endpoints transcription dans `documents.py` sont dupliqués
2. Si oui, rediriger vers `routes/transcription.py`
3. Si non, déplacer vers `routes/transcription.py`

**Réduction estimée:** ~180 lignes

---

### Phase 3.4 - Services TTS (1h)

**Améliorer:** `services/tts_service.py` (existe déjà !)

**Actions:**
1. Vérifier méthodes `list_voices()` et `generate_tts()` dans service
2. Simplifier endpoints dans `documents.py`
3. Extraire logique validation

**Réduction estimée:** ~100 lignes

---

### Phase 3.5 - Service LinkedDirectory (2h)

**Note:** Déjà route séparée `routes/linked_directory.py` 

**Actions:**
1. Vérifier si `link_file_or_folder` dans `documents.py` est dupliqué
2. Déplacer vers `routes/linked_directory.py` si nécessaire
3. Créer service si logique métier trop complexe

**Réduction estimée:** ~200 lignes

---

### Phase 3.6 - Nettoyage Final (1h)

**Actions:**
1. Supprimer imports inutilisés
2. Regrouper fonctions helpers similaires
3. Ajouter docstrings manquants
4. Vérifier cohérence du code

**Réduction estimée:** ~100 lignes

---

## Résultat Attendu

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Lignes totales | 1946 | < 950 | -51% |
| Endpoints | 18 | ~10-12 | -33% |
| Logique métier | Dans routes | Dans services | ✅ |
| Maintenabilité | 🟡 Moyenne | 🟢 Bonne | +++ |

---

## Ordre d'Exécution Recommandé

1. ✅ **Phase 3.1 - YouTube** (facile, services existe)
2. ✅ **Phase 3.4 - TTS** (facile, services existe)  
3. ⚠️ **Phase 3.5 - LinkedDirectory** (vérifier duplications)
4. ⚠️ **Phase 3.3 - Transcription** (vérifier duplications)
5. 🔴 **Phase 3.2 - Extraction** (complexe, beaucoup de logique)
6. ✅ **Phase 3.6 - Nettoyage** (final)

---

## Risques et Mitigation

### Risque 1: Casser des tests
**Mitigation:** Exécuter tests après chaque phase

### Risque 2: Duplications entre routes
**Mitigation:** Audit des routes existantes avant migration

### Risque 3: Logique métier complexe
**Mitigation:** Refactoring progressif avec commits intermédiaires

---

## Commandes Utiles

```bash
# Compter lignes par endpoint
grep -n "^async def" routes/documents.py | while read line; do 
  echo "$line"
done

# Vérifier usage d'un service
grep -n "service_name" routes/*.py

# Tester après refactoring
uv run pytest tests/test_documents.py -v
```

---

**Prochaines Étapes Immédiates:**
1. Audit des routes existantes (linked_directory, transcription)
2. Commencer par Phase 3.1 (YouTube) - quick win
3. Commit après chaque phase réussie

