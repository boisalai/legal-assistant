# Scripts de Backup SurrealDB

Ce dossier contient les scripts pour **ne plus jamais perdre vos données** SurrealDB.

## 🎯 Scripts Disponibles

### 1. `start_surreal.sh` - Démarrage avec backup automatique

**Remplace la commande manuelle de SurrealDB.**

```bash
# ❌ ANCIENNE MÉTHODE (ne pas utiliser):
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# ✅ NOUVELLE MÉTHODE (recommandée - depuis la racine du projet):
./dev.sh
# OU pour démarrage manuel de SurrealDB uniquement:
./backend/scripts/start_surreal.sh
```

**Avantages:**
- ✅ Backup automatique avant démarrage
- ✅ Utilise un chemin absolu (évite les pertes de données)
- ✅ Détecte si SurrealDB tourne déjà

### 2. `backup_db.sh` - Backup manuel

**Créer un backup immédiat de la base de données.**

```bash
cd /Users/alain/Code/legal-assistant/backend
./scripts/backup_db.sh
```

**Résultat:**
- Crée `backups/backup_YYYYMMDD_HHMMSS.surql.gz`
- Garde automatiquement les 30 derniers backups
- Nettoie les anciens backups

### 3. `restore_db.sh` - Restauration

**Restaurer une sauvegarde précédente.**

```bash
# Lister les backups disponibles
cd /Users/alain/Code/legal-assistant/backend
./scripts/restore_db.sh

# Restaurer un backup spécifique
./scripts/restore_db.sh backups/backup_20251228_132500.surql.gz
```

**⚠️ Attention:** La restauration **écrase** la base actuelle (confirmation requise).

## 🔄 Backups Automatiques

### Hook Git Pre-Commit

Un hook Git a été installé dans `.git/hooks/pre-commit` qui **backup automatiquement** avant chaque commit.

**Résultat:** Chaque fois que vous faites `git commit`, un backup est créé.

### Backup Quotidien (Optionnel)

Pour un backup quotidien automatique, ajoutez à votre crontab:

```bash
# Ouvrir crontab
crontab -e

# Ajouter cette ligne (backup tous les jours à 2h du matin)
0 2 * * * /Users/alain/Code/legal-assistant/backend/scripts/backup_db.sh
```

## 📂 Structure des Backups

```
backend/
├── backups/
│   ├── backup_20251228_132500.surql.gz  (1.2 MB)
│   ├── backup_20251228_140000.surql.gz  (1.3 MB)
│   └── ...  (max 30 backups gardés)
└── scripts/
    ├── start_surreal.sh
    ├── backup_db.sh
    └── restore_db.sh
```

## 🛡️ Garanties de Sécurité

1. **Backup automatique au démarrage** - Impossible de perdre des données en redémarrant SurrealDB
2. **Backup avant commit** - Chaque commit Git = backup automatique
3. **Rétention 30 jours** - Les 30 derniers backups sont gardés
4. **Compression gzip** - Économise l'espace disque
5. **Chemin absolu** - Pas de confusion sur la localisation de la base

## ❓ FAQ

### Q: Pourquoi mes cours disparaissent-ils?

**Avant:** SurrealDB utilisait un chemin relatif (`file:data/surreal.db`). Si vous démarriez la commande depuis un autre dossier, une nouvelle base vide était créée.

**Maintenant:** `start_surreal.sh` utilise un **chemin absolu**, garantissant que c'est toujours la même base qui est utilisée.

### Q: Comment voir tous mes backups?

```bash
ls -lht backend/backups/
```

### Q: Puis-je supprimer manuellement de vieux backups?

Oui, mais les 30 derniers sont gardés automatiquement. Pour supprimer manuellement:

```bash
rm backend/backups/backup_20251201_*.surql.gz
```

### Q: Que se passe-t-il si le backup échoue au démarrage?

Le script affiche un warning mais **démarre quand même SurrealDB**. Cela peut arriver si la base est vide (première utilisation).

## 🚀 Workflow Recommandé

**Démarrage quotidien:**

```bash
# Terminal 1: SurrealDB (avec backup auto)
cd /Users/alain/Code/legal-assistant/backend
./scripts/start_surreal.sh

# Terminal 2: Backend
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

**Avant modifications importantes:**

```bash
# Backup manuel de précaution
./scripts/backup_db.sh
```

**En cas de problème:**

```bash
# Lister les backups
./scripts/restore_db.sh

# Restaurer le dernier backup
./scripts/restore_db.sh backups/backup_YYYYMMDD_HHMMSS.surql.gz
```

## ✅ Checklist de Migration

- [x] Scripts de backup créés
- [x] Hook pre-commit installé
- [x] Backups ajoutés au .gitignore
- [ ] Utiliser `start_surreal.sh` pour démarrer SurrealDB
- [ ] Recréer vos cours (dernière fois!)
- [ ] Tester la restauration une fois

---

**🎉 Vous ne perdrez plus jamais vos cours!**
