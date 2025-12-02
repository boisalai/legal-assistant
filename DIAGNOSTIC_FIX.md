# Fix: Problème de détection de fichiers markdown existants

## Problème identifié

L'agent indiquait qu'un fichier markdown existait déjà alors qu'il n'existait pas physiquement sur le disque. Cela était causé par:

1. **Enregistrements orphelins en base de données**: Des documents peuvent avoir été créés en base de données mais leurs fichiers physiques ont été supprimés manuellement
2. **Manque de vérification de cohérence**: Le workflow de transcription ne vérifiait pas l'existence réelle du fichier avant de rejeter une nouvelle transcription
3. **Code "spaghetti"**: Logique de vérification dupliquée entre extraction PDF et transcription audio

## Solutions implémentées

### 1. Vérification d'existence dans le workflow de transcription

**Fichier**: `backend/workflows/transcribe_audio.py`

Ajout de vérifications dans la méthode `_save_step()`:

```python
# Vérifier si le fichier physique existe
if file_path.exists():
    error_msg = f"Un fichier markdown '{md_filename}' existe déjà sur le disque..."
    raise FileExistsError(error_msg)

# Vérifier si un enregistrement existe en base de données
existing_docs_result = await service.query(...)
if existing_docs and len(existing_docs) > 0:
    error_msg = f"Un fichier markdown '{md_filename}' existe déjà en base de données..."
    raise FileExistsError(error_msg)
```

Cette logique est maintenant cohérente avec l'extraction PDF (`backend/routes/documents.py:1314-1353`).

### 2. Endpoint de diagnostic

**Fichier**: `backend/routes/documents.py`

Nouvel endpoint: `GET /api/judgments/{judgment_id}/documents/diagnostic`

Retourne:
- `total_documents`: Nombre total de documents enregistrés
- `missing_files`: Documents en base sans fichier physique
- `orphan_records`: Alias pour les fichiers manquants
- `ok_count`: Nombre de documents OK

**Usage**:
```bash
curl http://localhost:8000/api/judgments/{case_id}/documents/diagnostic
```

### 3. Script de nettoyage

**Fichier**: `backend/cleanup_orphan_records.py`

Script CLI pour identifier et supprimer les enregistrements orphelins.

**Usage**:
```bash
# Dry-run (sans suppression)
uv run python cleanup_orphan_records.py --dry-run

# Nettoyer tous les dossiers
uv run python cleanup_orphan_records.py

# Nettoyer un dossier spécifique
uv run python cleanup_orphan_records.py --judgment-id 1f9fc70e
```

## Comment utiliser ces outils

### Diagnostic d'un problème

1. **Via l'API** (depuis le frontend ou curl):
   ```bash
   curl http://localhost:8000/api/judgments/YOUR_CASE_ID/documents/diagnostic
   ```

2. **Vérifier les logs du backend** pour les warnings:
   ```
   WARNING - Un fichier markdown 'audio.md' existe déjà...
   ```

### Nettoyage des orphelins

1. **Dry-run** (voir sans supprimer):
   ```bash
   cd backend
   uv run python cleanup_orphan_records.py --dry-run
   ```

2. **Suppression réelle**:
   ```bash
   cd backend
   uv run python cleanup_orphan_records.py
   ```
   Le script demandera confirmation avant de supprimer.

3. **Pour un dossier spécifique**:
   ```bash
   uv run python cleanup_orphan_records.py --judgment-id YOUR_CASE_ID
   ```

## Prévention future

### Bonnes pratiques

1. **Ne jamais supprimer manuellement les fichiers** du répertoire `uploads/`
   - Toujours utiliser l'API DELETE pour supprimer des documents
   - L'API supprime à la fois le fichier et l'enregistrement en base

2. **Utiliser le diagnostic régulièrement**
   - Ajouter un bouton "Diagnostic" dans le frontend
   - Afficher un warning si des orphelins sont détectés

3. **Backup régulier**
   - Les fichiers markdown de transcription sont précieux
   - Considérer un backup automatique hebdomadaire

### Améliorations possibles

1. **Réparation automatique**:
   - Détecter les orphelins au démarrage
   - Proposer un nettoyage automatique

2. **Validation à l'upload**:
   - Vérifier que le fichier existe après création
   - Rollback si la création échoue

3. **Interface frontend**:
   - Bouton "Nettoyer les orphelins" dans les paramètres
   - Affichage visuel des problèmes de cohérence

## Résumé des fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `backend/workflows/transcribe_audio.py` | Ajout vérification d'existence (lignes 347-379) |
| `backend/routes/documents.py` | Nouvel endpoint `/diagnostic` (lignes 1637-1718) |
| `backend/cleanup_orphan_records.py` | Nouveau script de nettoyage |
| `DIAGNOSTIC_FIX.md` | Cette documentation |

## Test de la solution

1. **Créer un orphelin de test** (simulation du problème):
   ```bash
   # 1. Uploader un fichier audio et le transcrire
   # 2. Supprimer manuellement le fichier .md du disque
   rm uploads/YOUR_CASE_ID/audio.md
   # 3. Tenter de retranscrire → devrait maintenant donner une erreur claire
   ```

2. **Diagnostiquer**:
   ```bash
   curl http://localhost:8000/api/judgments/YOUR_CASE_ID/documents/diagnostic
   ```

3. **Nettoyer**:
   ```bash
   uv run python cleanup_orphan_records.py --judgment-id YOUR_CASE_ID
   ```

4. **Retranscrire** → devrait maintenant fonctionner!

---

**Date**: 2025-12-01
**Auteur**: Claude Code
**Contexte**: Fix du bug de détection erronée de fichiers markdown existants
