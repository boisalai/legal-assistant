# Instructions de Migration des Statuts

## Contexte

Les statuts des dossiers ont été uniformisés à travers l'application pour utiliser 5 valeurs cohérentes :
1. **nouveau** - Nouveau dossier
2. **en_analyse** - Dossier en cours d'analyse
3. **termine** - Dossier terminé
4. **en_erreur** - Dossier avec erreur
5. **archive** - Dossier archivé

## Problème

Certains dossiers dans la base de données SurrealDB utilisent encore les anciens statuts :
- `complete` → doit devenir `termine`
- `erreur` → doit devenir `en_erreur`
- `valide` → doit devenir `termine`
- `analyse_complete` → doit devenir `termine`

Ces anciens statuts provoquent une erreur de validation Pydantic :
```
Validation error: 1 validation error for Dossier
statut
  Input should be 'nouveau', 'en_analyse', 'termine', 'en_erreur' or 'archive'
```

## Solution

Un script de migration a été créé : `/home/user/notary/backend/fix_statuts.sh`

### Étapes pour exécuter la migration

1. **Assurez-vous que SurrealDB est démarré**
   ```bash
   docker compose up -d surrealdb
   ```

2. **Vérifiez que SurrealDB est accessible**
   ```bash
   curl -X POST http://localhost:8001/sql \
     -H "NS: notary" -H "DB: notary_db" \
     -u "root:root" \
     -d "SELECT statut, count() as total FROM dossier GROUP BY statut;"
   ```

3. **Rendez le script exécutable (si ce n'est pas déjà fait)**
   ```bash
   chmod +x /home/user/notary/backend/fix_statuts.sh
   ```

4. **Exécutez le script de migration**
   ```bash
   cd /home/user/notary/backend
   ./fix_statuts.sh
   ```

### Ce que fait le script

Le script `fix_statuts.sh` :

1. **Affiche les statuts actuels** - Montre la distribution des statuts avant migration
2. **Migre 'complete' → 'termine'** (3 fois pour être sûr de tout capturer)
3. **Migre 'erreur' → 'en_erreur'**
4. **Migre 'valide' → 'termine'**
5. **Migre 'analyse_complete' → 'termine'**
6. **Affiche les statuts après migration**
7. **Liste les statuts invalides restants** (devrait être vide)

### Résultat attendu

Après l'exécution du script, vous devriez voir :

```
🔍 Vérification des statuts actuels...
[Liste des statuts avant migration]

🔄 Correction de TOUS les statuts invalides...

📝 Migration: 'complete' → 'termine'
  ✅ Terminé
📝 Migration: 'erreur' → 'en_erreur'
  ✅ Terminé
📝 Migration: 'valide' → 'termine'
  ✅ Terminé
📝 Migration: 'analyse_complete' → 'termine'
  ✅ Terminé

📊 Statuts après correction:
[Liste des statuts après migration - devrait montrer seulement les 5 nouveaux statuts]

✅ Correction terminée!

🔍 Vérification des statuts invalides restants:
[Devrait être vide ou "[]"]
```

### Vérification post-migration

1. **Vérifiez que l'erreur a disparu dans le backend**
   - Les logs du backend ne devraient plus afficher d'erreur de validation Pydantic
   - L'endpoint GET `/api/dossiers` devrait fonctionner sans erreur

2. **Testez l'interface web**
   - Allez sur http://localhost:3001/cases
   - La liste des dossiers devrait se charger sans erreur "Impossible de charger les dossiers"

3. **Vérifiez le tableau de bord**
   - Allez sur http://localhost:3001/dashboard
   - Les statistiques devraient afficher correctement avec les nouveaux statuts

## Fichiers modifiés

### Backend
- `/home/user/notary/backend/data/surreal/schema.surql` - Contrainte de validation des statuts
- `/home/user/notary/backend/models/__init__.py` - Type Literal CaseStatus

### Frontend
- `/home/user/notary/frontend/src/types/index.ts` - Type TypeScript CaseStatus
- `/home/user/notary/frontend/messages/fr.json` - Traductions françaises
- `/home/user/notary/frontend/messages/en.json` - Traductions anglaises
- `/home/user/notary/frontend/src/components/cases/columns.tsx` - Configuration badges de statut
- `/home/user/notary/frontend/src/components/cases/case-details-panel.tsx` - Affichage statut
- `/home/user/notary/frontend/src/components/cases/data-table.tsx` - Options de filtre
- `/home/user/notary/frontend/src/app/dashboard/page.tsx` - Titres des cards statistiques
- `/home/user/notary/frontend/src/app/analysis/page.tsx` - Configuration statuts

## Dépannage

### Erreur "Connection refused" ou curl échoue

**Cause** : SurrealDB n'est pas démarré ou n'écoute pas sur le port 8001

**Solution** :
```bash
docker compose up -d surrealdb
docker compose logs surrealdb  # Vérifier les logs
```

### Le script s'exécute mais les erreurs persistent

**Cause** : Certains dossiers n'ont pas été migrés

**Solution** : Exécutez le script plusieurs fois
```bash
./fix_statuts.sh
./fix_statuts.sh
./fix_statuts.sh
```

### Vérification manuelle des statuts

Si vous voulez vérifier manuellement quels dossiers ont quel statut :

```bash
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: notary" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "SELECT id, nom_dossier, statut FROM dossier ORDER BY created_at DESC;" | jq
```

### Migration manuelle d'un dossier spécifique

Si un dossier spécifique pose problème, vous pouvez le mettre à jour manuellement :

```bash
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: notary" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "UPDATE dossier:ID_DU_DOSSIER SET statut = 'termine';"
```

Remplacez `ID_DU_DOSSIER` par l'ID réel du dossier.

## Commit

Une fois la migration réussie, pensez à committer les changements :

```bash
git add -A
git commit -m "feat: Uniformiser les statuts des dossiers à travers l'application"
git push
```

## Questions ou problèmes ?

Si vous rencontrez des problèmes avec la migration :
1. Vérifiez que SurrealDB est bien démarré
2. Vérifiez les logs de SurrealDB : `docker compose logs surrealdb`
3. Vérifiez les logs du backend pour voir les erreurs de validation
4. Exécutez le script plusieurs fois si nécessaire
5. Utilisez la vérification manuelle pour identifier les dossiers problématiques
