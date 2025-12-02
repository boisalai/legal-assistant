# Correction du bug des IDs malformés (document:document:xxx)

## Problème identifié

Des documents avec des IDs malformés étaient créés dans SurrealDB avec le format `document:document:xxx` au lieu de `document:xxx`. Cela causait :

1. **Erreurs de suppression** : "too many values to unpack (expected 2)"
2. **Messages d'erreur trompeurs** : L'extraction PDF vers markdown échouait en disant qu'un fichier markdown existait déjà, alors qu'il n'existait qu'en base de données (document fantôme)
3. **Impossibilité de supprimer** : Les enregistrements malformés ne pouvaient pas être supprimés automatiquement

## Cause racine

Dans `backend/routes/documents.py`, ligne 1402, lors de la création d'un document markdown extrait d'un PDF :

```python
doc_record = {
    "id": f"document:{doc_id}",  # ❌ ERREUR: Inclure l'ID dans les données
    "judgment_id": judgment_id,
    ...
}

await service.query("CREATE document CONTENT $data", {"data": doc_record})
```

**Problème** : Quand on utilise `CREATE document CONTENT $data` avec un `id` déjà présent dans les données, SurrealDB crée un enregistrement avec l'ID fourni **ET** ajoute automatiquement le préfixe de table, résultant en `document:document:xxx`.

## Solution appliquée

### 1. Correction du code d'extraction PDF (documents.py:1400-1416)

**AVANT** :
```python
doc_record = {
    "id": f"document:{doc_id}",  # ❌ Incluait l'ID
    ...
}
await service.query("CREATE document CONTENT $data", {"data": doc_record})
```

**APRÈS** :
```python
doc_record = {
    # ✅ NE PAS inclure "id" dans doc_record
    "judgment_id": judgment_id,
    ...
}
# ✅ Utiliser service.create() avec record_id séparé
await service.create("document", doc_record, record_id=doc_id)
```

### 2. Ajout de validations dans surreal_service.py (lignes 206-222)

Deux validations ont été ajoutées dans la méthode `create()` :

```python
# Validation 1: Nettoyer record_id si il contient déjà un préfixe
if record_id and ":" in record_id:
    logger.warning(f"record_id '{record_id}' contains ':'. Removing prefix.")
    record_id = record_id.split(":")[-1]

# Validation 2: Ignorer le champ "id" dans data
if "id" in data:
    logger.warning(f"'id' field found in data. This will be ignored.")
    data = {k: v for k, v in data.items() if k != "id"}
```

Ces validations préviennent la création d'IDs malformés même si du code incorrect passe des paramètres invalides.

### 3. Script de migration pour nettoyer les IDs existants

Un script a été créé : `backend/migrations/fix_malformed_ids.py`

**Utilisation** :
```bash
cd backend
uv run python migrations/fix_malformed_ids.py
```

Ce script :
- Détecte tous les IDs malformés
- Crée de nouveaux enregistrements avec des IDs corrects
- Supprime les anciens enregistrements malformés

### 4. Script de nettoyage manuel

Pour supprimer un document malformé spécifique :

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8002/rpc")
await db.signin({"username": "root", "password": "root"})
await db.use("legal", "legal_db")

# Méthode 1: Par nom de fichier
await db.query(
    "DELETE document WHERE nom_fichier = $filename",
    {"filename": "DRT1151_M1_Notes de cours.md"}
)

# Méthode 2: Par ID malformé (avec backticks)
await db.query("DELETE `document:document:bbb01c49-8f30-4b1f-9115-022600a7b3af`")
```

## Vérification

Pour vérifier qu'il n'y a plus d'IDs malformés :

```bash
cd backend
uv run python -c "
import asyncio
from surrealdb import AsyncSurreal

async def check():
    db = AsyncSurreal('ws://localhost:8002/rpc')
    await db.signin({'username': 'root', 'password': 'root'})
    await db.use('legal', 'legal_db')

    result = await db.query('SELECT * FROM document')
    docs = result[0].get('result', []) if result else []

    malformed = [d for d in docs if str(d.get('id', '')).count(':') > 1]

    if malformed:
        print(f'⚠️  {len(malformed)} ID(s) malformé(s) trouvé(s):')
        for d in malformed:
            print(f\"  - {d.get('id')}: {d.get('nom_fichier')}\")
    else:
        print('✓ Tous les IDs sont corrects!')

    await db.close()

asyncio.run(check())
"
```

## Prévention future

Avec les corrections appliquées, ce problème ne devrait plus se reproduire car :

1. ✅ Le code d'extraction PDF utilise maintenant la bonne méthode
2. ✅ `surreal_service.create()` valide et nettoie automatiquement les paramètres
3. ✅ Les warnings dans les logs alertent si du code essaie de passer des IDs malformés

## Fichiers modifiés

- ✅ `backend/routes/documents.py` (ligne 1400-1416)
- ✅ `backend/services/surreal_service.py` (ligne 206-222)
- ✅ `backend/migrations/fix_malformed_ids.py` (nouveau)
- ✅ `MALFORMED_IDS_FIX.md` (cette documentation)

## Date de correction

2025-12-01
