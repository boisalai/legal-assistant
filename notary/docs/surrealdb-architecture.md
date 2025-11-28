# Architecture SurrealDB - Notary Assistant

> Documentation de l'architecture de données avec SurrealDB
> Dernière mise à jour: 2025-11-17

## 📋 Vue d'ensemble

**Notary Assistant** utilise SurrealDB comme base de données principale pour exploiter ses capacités multi-modèles (relationnel, document, graphe) et temps réel.

### Pourquoi SurrealDB?

**Décision**: Migration de PostgreSQL vers SurrealDB dès le début du projet (aucune donnée à migrer).

**Besoins du projet:**
1. ✅ **États des workflows Agno**: Stockage flexible sans schéma rigide
2. ✅ **Historique complet**: Toutes les décisions IA, prompts, réponses
3. ✅ **Relations complexes**: Graphe de connaissances (personnes, documents, propriétés)
4. ✅ **Temps réel**: Live queries pour suivre l'avancement des workflows
5. ✅ **Logs et métriques**: Traçabilité complète de l'exécution
6. ✅ **Recherche sémantique**: Embeddings vectoriels (futur)

**Avantages SurrealDB:**
- Multi-modèle natif (relationnel + document + graphe)
- Live queries WebSocket natives
- Recherche vectorielle intégrée
- Mix SCHEMAFULL/SCHEMALESS pour flexibilité
- Une seule base de données pour tout

---

## 🏗️ Architecture de déploiement

### Développement (MVP)
```
Mode: RocksDB (embedded)
├── Stockage local: backend/data/surrealdb/
├── Port: 8001 (pour éviter conflit avec FastAPI:8000)
└── Interface: HTTP + WebSocket
```

**Commande Docker:**
```bash
docker run --name notary-surrealdb \
  -p 8001:8000 \
  -v $(pwd)/backend/data/surrealdb:/data \
  surrealdb/surrealdb:latest \
  start --log trace --user root --pass root file:/data/notary.db
```

### Production (futur)
```
Mode: TiKV (distributed) ou SurrealDB Cloud
├── Haute disponibilité
├── Scalabilité horizontale
└── Backup automatique
```

---

## 🗂️ Modèle de données

### Philosophie: Hybride SCHEMAFULL + SCHEMALESS

**SCHEMAFULL** pour:
- Données métier critiques (users, dossiers, documents)
- Données nécessitant validation (email, dates, montants)
- Relations immuables

**SCHEMALESS** pour:
- États des agents (structure variable)
- Historique des exécutions (données arbitraires)
- Logs et métriques (flexibilité)
- Contexte des workflows

---

## 📊 Schéma des tables

### 1. Tables métier (SCHEMAFULL)

#### **user** - Utilisateurs (notaires)
```surrealql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD email ON user TYPE string ASSERT string::is::email($value);
DEFINE FIELD nom ON user TYPE string;
DEFINE FIELD prenom ON user TYPE string;
DEFINE FIELD role ON user TYPE string DEFAULT "notaire";
DEFINE FIELD actif ON user TYPE bool DEFAULT true;
DEFINE FIELD created_at ON user TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON user TYPE datetime VALUE time::now();

-- Index unique sur email
DEFINE INDEX idx_user_email ON user FIELDS email UNIQUE;
```

#### **dossier** - Dossiers notariaux
```surrealql
DEFINE TABLE dossier SCHEMAFULL;
DEFINE FIELD nom ON dossier TYPE string;
DEFINE FIELD type_transaction ON dossier TYPE string;
  -- Types: vente, hypotheque, testament, succession, etc.
DEFINE FIELD statut ON dossier TYPE string DEFAULT "nouveau";
  -- États: nouveau, en_analyse, verifie, pret, termine
DEFINE FIELD priorite ON dossier TYPE string DEFAULT "normale";
  -- Priorités: basse, normale, haute, urgente
DEFINE FIELD created_by ON dossier TYPE record<user>;
DEFINE FIELD created_at ON dossier TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON dossier TYPE datetime VALUE time::now();
DEFINE FIELD completed_at ON dossier TYPE option<datetime>;

-- Index pour recherche rapide
DEFINE INDEX idx_dossier_statut ON dossier FIELDS statut;
DEFINE INDEX idx_dossier_type ON dossier FIELDS type_transaction;
```

#### **document** - Documents PDF uploadés
```surrealql
DEFINE TABLE document SCHEMAFULL;
DEFINE FIELD nom_fichier ON document TYPE string;
DEFINE FIELD type_document ON document TYPE string;
  -- Types: promesse_vente, offre_achat, titre_propriete, certificat_localisation, etc.
DEFINE FIELD chemin_stockage ON document TYPE string;
DEFINE FIELD taille_bytes ON document TYPE int;
DEFINE FIELD hash_sha256 ON document TYPE string;
DEFINE FIELD dossier ON document TYPE record<dossier>;
DEFINE FIELD uploaded_by ON document TYPE record<user>;
DEFINE FIELD uploaded_at ON document TYPE datetime DEFAULT time::now();

-- Index pour vérifier duplicatas
DEFINE INDEX idx_document_hash ON document FIELDS hash_sha256;
```

---

### 2. Tables agents (SCHEMALESS)

#### **workflow_execution** - Exécutions de workflows
```surrealql
DEFINE TABLE workflow_execution SCHEMALESS;

-- Exemple de document:
{
  id: workflow_execution:abc123,
  workflow_name: "analyse_dossier",
  dossier: dossier:xyz789,
  status: "running", // pending, running, completed, failed
  started_at: "2025-11-17T10:30:00Z",
  completed_at: null,
  current_step: "extraction",
  progress: 0.35,
  context: {
    documents_to_process: 5,
    documents_processed: 2,
    errors: []
  },
  result: null // Résultat final quand completed
}
```

#### **agent_execution** - Exécutions d'agents individuels
```surrealql
DEFINE TABLE agent_execution SCHEMALESS;

-- Exemple:
{
  id: agent_execution:def456,
  workflow: workflow_execution:abc123,
  agent_name: "extracteur",
  agent_type: "extraction_pdf",
  status: "completed",
  started_at: "2025-11-17T10:30:05Z",
  completed_at: "2025-11-17T10:32:15Z",
  duration_seconds: 130,
  input: {
    document: document:pdf001,
    task: "Extraire les informations clés"
  },
  output: {
    vendeur: "Jean Dupont",
    acheteur: "Marie Tremblay",
    prix_vente: 450000,
    adresse: "123 Rue St-Denis, Montréal",
    confidence: 0.92
  },
  metadata: {
    pages_processed: 15,
    extraction_method: "pypdf + mlx"
  }
}
```

#### **llm_call** - Appels aux LLM (traçabilité IA)
```surrealql
DEFINE TABLE llm_call SCHEMALESS;

-- Exemple:
{
  id: llm_call:ghi789,
  agent: agent_execution:def456,
  workflow: workflow_execution:abc123,
  timestamp: "2025-11-17T10:31:30Z",

  // Modèle utilisé
  provider: "mlx",
  model: "phi-3-mini-4k-instruct-4bit",

  // Prompt et réponse
  prompt: "Classifie cette transaction...",
  response: "Il s'agit d'une vente résidentielle...",

  // Métriques
  tokens_prompt: 123,
  tokens_response: 67,
  tokens_total: 190,
  latency_ms: 1245,

  // Qualité
  confidence: 0.89,
  temperature: 0.3
}
```

#### **system_log** - Logs système
```surrealql
DEFINE TABLE system_log SCHEMALESS;

-- Exemple:
{
  id: system_log:jkl012,
  timestamp: "2025-11-17T10:35:00Z",
  level: "info", // debug, info, warning, error, critical
  component: "workflow_engine",
  message: "Workflow analyse_dossier_123 completed successfully",
  context: {
    workflow_id: workflow_execution:abc123,
    duration_seconds: 285,
    documents_processed: 5,
    agents_executed: 4,
    llm_calls: 12,
    total_tokens: 3456
  }
}
```

---

### 3. Tables graphe (Relations)

#### **contient** - Dossier contient documents
```surrealql
DEFINE TABLE contient SCHEMALESS;
RELATE dossier:xyz789->contient->document:pdf001 SET {
  ajout_le: time::now()
};
```

#### **mentionne** - Document mentionne personne
```surrealql
DEFINE TABLE mentionne SCHEMALESS;
RELATE document:pdf001->mentionne->personne:jean_dupont SET {
  role: "vendeur",
  confidence: 0.95,
  page: 3
};
```

#### **vend/achete** - Transactions
```surrealql
DEFINE TABLE vend SCHEMALESS;
DEFINE TABLE achete SCHEMALESS;

RELATE personne:jean_dupont->vend->propriete:maison123 SET {
  dossier: dossier:xyz789,
  prix: 450000,
  date_offre: "2025-10-15"
};

RELATE personne:marie_tremblay->achete->propriete:maison123 SET {
  dossier: dossier:xyz789,
  prix: 450000,
  date_acceptation: "2025-10-20"
};
```

#### **situe_a** - Localisation
```surrealql
DEFINE TABLE situe_a SCHEMALESS;
RELATE propriete:maison123->situe_a->adresse:mtl_st_denis_123 SET {
  numero_cadastre: "1234567"
};
```

---

## 🔍 Requêtes types

### Données métier classiques
```surrealql
-- Tous les dossiers d'un notaire
SELECT * FROM dossier WHERE created_by = user:notaire123;

-- Documents d'un dossier
SELECT * FROM document WHERE dossier = dossier:xyz789;

-- Dossiers en cours
SELECT * FROM dossier WHERE statut = "en_analyse";
```

### Workflows et agents
```surrealql
-- État actuel d'un workflow
SELECT * FROM workflow_execution WHERE id = workflow_execution:abc123;

-- Tous les agents d'un workflow
SELECT * FROM agent_execution WHERE workflow = workflow_execution:abc123
ORDER BY started_at;

-- Performance des LLM sur un workflow
SELECT
  count() as total_calls,
  math::sum(tokens_total) as total_tokens,
  math::avg(latency_ms) as avg_latency,
  math::avg(confidence) as avg_confidence
FROM llm_call
WHERE workflow = workflow_execution:abc123;
```

### Requêtes graphe
```surrealql
-- Tous les documents mentionnant une personne
SELECT * FROM document WHERE id IN (
  SELECT <-mentionne<-document FROM personne:jean_dupont
);

-- Historique de transactions d'une personne
SELECT * FROM personne:jean_dupont->(vend|achete)->propriete;

-- Tous les acteurs d'un dossier
SELECT * FROM personne WHERE id IN (
  SELECT ->mentionne->personne
  FROM document
  WHERE dossier = dossier:xyz789
);
```

### Recherche full-text (futur)
```surrealql
-- Rechercher dans les documents extraits
SELECT * FROM document WHERE
  search::fulltext(contenu_extrait, "hypothèque");
```

---

## ⚡ Live Queries (Temps réel)

### Backend Python
```python
# Émettre une mise à jour
await db.query(f"""
  UPDATE workflow_execution:{workflow_id} SET
    status = 'running',
    progress = 0.65,
    current_step = 'verification'
""")
# Tous les clients abonnés reçoivent la mise à jour automatiquement!
```

### Frontend (Next.js/React)
```javascript
import { Surreal } from 'surrealdb.js';

const db = new Surreal();
await db.connect('ws://localhost:8001/rpc');
await db.signin({ user: 'root', pass: 'root' });
await db.use({ ns: 'notary', db: 'notary_db' });

// S'abonner aux changements d'un workflow
const queryUuid = await db.live(
  `SELECT * FROM workflow_execution WHERE id = ${workflowId}`,
  (action, result) => {
    console.log('Action:', action); // CREATE, UPDATE, DELETE
    console.log('Data:', result);

    // Mettre à jour l'UI
    setWorkflowState(result);
    setProgress(result.progress);
  }
);

// Se désabonner plus tard
await db.kill(queryUuid);
```

---

## 🔐 Sécurité et permissions

### Namespaces et databases
```surrealql
-- Namespace pour l'application
USE NS notary;

-- Database principale
USE DB notary_db;

-- Database de test (séparée)
USE DB notary_test;
```

### Utilisateurs et rôles (à implémenter)
```surrealql
-- Utilisateur application (backend Python)
DEFINE USER notary_app ON DATABASE PASSWORD 'secret_password'
  ROLES EDITOR;

-- Utilisateur read-only (monitoring)
DEFINE USER notary_readonly ON DATABASE PASSWORD 'another_secret'
  ROLES VIEWER;
```

### Permissions au niveau des enregistrements (futur)
```surrealql
-- Un notaire ne peut voir que ses dossiers
DEFINE TABLE dossier SCHEMAFULL
  PERMISSIONS
    FOR select WHERE created_by = $auth.id
    FOR create, update WHERE created_by = $auth.id
    FOR delete WHERE created_by = $auth.id AND statut != "termine";
```

---

## 📦 Scripts d'initialisation

### backend/data/surreal/init.surql
```surrealql
-- Namespace et database
USE NS notary;
USE DB notary_db;

-- Définition des tables (voir sections précédentes)
DEFINE TABLE user SCHEMAFULL;
-- ...

-- Données de test
CREATE user:test_notaire SET {
  email: "test@notaire.qc.ca",
  nom: "Tremblay",
  prenom: "François",
  role: "notaire",
  actif: true
};

CREATE dossier:test_dossier SET {
  nom: "Vente Dupont-Tremblay",
  type_transaction: "vente",
  statut: "nouveau",
  created_by: user:test_notaire
};
```

---

## 🔧 Service Python

### backend/services/surreal_service.py
```python
from surrealdb import Surreal
from typing import Any, Optional
from contextlib import asynccontextmanager

class SurrealDBService:
    def __init__(self, url: str, namespace: str, database: str):
        self.url = url
        self.namespace = namespace
        self.database = database
        self.db: Optional[Surreal] = None

    async def connect(self):
        """Connexion à SurrealDB"""
        self.db = Surreal()
        await self.db.connect(self.url)
        await self.db.signin({"user": "root", "pass": "root"})
        await self.db.use(self.namespace, self.database)

    async def disconnect(self):
        """Fermer la connexion"""
        if self.db:
            await self.db.close()

    async def query(self, query: str, params: Optional[dict] = None) -> Any:
        """Exécuter une requête SurrealQL"""
        if not self.db:
            raise RuntimeError("Database not connected")
        return await self.db.query(query, params)

    async def create(self, table: str, data: dict) -> Any:
        """Créer un enregistrement"""
        return await self.db.create(table, data)

    async def select(self, thing: str) -> Any:
        """Sélectionner un enregistrement"""
        return await self.db.select(thing)

    async def update(self, thing: str, data: dict) -> Any:
        """Mettre à jour un enregistrement"""
        return await self.db.update(thing, data)

    async def delete(self, thing: str) -> Any:
        """Supprimer un enregistrement"""
        return await self.db.delete(thing)

# Instance globale
surreal_service = SurrealDBService(
    url="ws://localhost:8001/rpc",
    namespace="notary",
    database="notary_db"
)
```

---

## 🧪 Tests

### Tests de base
```python
# backend/test_surrealdb.py
async def test_connection():
    await surreal_service.connect()
    assert surreal_service.db is not None

async def test_create_user():
    user = await surreal_service.create("user", {
        "email": "test@example.com",
        "nom": "Test",
        "prenom": "User"
    })
    assert user[0]["email"] == "test@example.com"

async def test_live_query():
    # S'abonner aux changements
    callback_called = False

    def callback(action, data):
        nonlocal callback_called
        callback_called = True

    await surreal_service.db.live("SELECT * FROM user", callback)

    # Créer un user (doit déclencher le callback)
    await surreal_service.create("user", {...})

    await asyncio.sleep(0.1)
    assert callback_called
```

---

## 📈 Métriques et monitoring

### Données à surveiller
```surrealql
-- Nombre de workflows actifs
SELECT count() FROM workflow_execution WHERE status = "running";

-- Performance moyenne des agents
SELECT
  agent_name,
  math::avg(duration_seconds) as avg_duration,
  count() as total_executions
FROM agent_execution
GROUP BY agent_name;

-- Utilisation des tokens LLM
SELECT
  date::format(timestamp, "%Y-%m-%d") as date,
  math::sum(tokens_total) as total_tokens
FROM llm_call
GROUP BY date
ORDER BY date DESC;

-- Taux d'erreur
SELECT
  count() as total_workflows,
  count(status = "failed") as failed_workflows,
  (count(status = "failed") / count() * 100) as error_rate_percent
FROM workflow_execution;
```

---

## 🚀 Migration future (Production)

### De RocksDB vers TiKV
```bash
# 1. Exporter les données
surrealdb export --conn http://localhost:8001 \
  --user root --pass root \
  --ns notary --db notary_db \
  backup.surql

# 2. Démarrer cluster TiKV
# (voir documentation SurrealDB)

# 3. Importer les données
surrealdb import --conn http://tikv-cluster:8000 \
  --user root --pass root \
  --ns notary --db notary_db \
  backup.surql
```

---

## 📚 Ressources

- **Documentation SurrealDB**: https://surrealdb.com/docs
- **SDK Python**: https://surrealdb.com/docs/sdk/python
- **SurrealQL**: https://surrealdb.com/docs/surrealql
- **Surrealist (GUI)**: https://surrealdb.com/surrealist
- **GitHub**: https://github.com/surrealdb/surrealdb

---

## 🔄 Historique des décisions

| Date | Décision | Raison |
|------|----------|--------|
| 2025-11-17 | Migration PostgreSQL → SurrealDB | Multi-modèle, temps réel, flexibilité pour agents |
| 2025-11-17 | Mode RocksDB pour dev | Simplicité, pas besoin de cluster pour MVP |
| 2025-11-17 | Modèle hybride SCHEMAFULL/SCHEMALESS | Rigidité pour données métier, flexibilité pour agents |
| 2025-11-17 | Requêtes SurrealQL directes | Simplicité, performance, contrôle total |

---

**Maintenu par:** Claude Code
**Projet:** Notary Assistant - Architecture SurrealDB
**Version:** 1.0
**Dernière mise à jour:** 2025-11-17
