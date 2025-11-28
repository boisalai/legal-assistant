# Schéma SurrealDB Créé par Agno

> Documentation du schéma de tables créées automatiquement par Agno
> Basé sur les exemples officiels: https://github.com/agno-agi/agno/tree/main/cookbook/db/surrealdb

## 📋 Vue d'ensemble

Quand on passe le paramètre `db=` à un `Workflow`, `Agent` ou `Team`, Agno **crée automatiquement** les tables nécessaires dans SurrealDB pour persister:
- L'historique des exécutions
- Les sessions de conversation
- Les états intermédiaires
- Les métadonnées

## 🏗️ Tables Créées par Agno

### 1. `workflow_runs`

**Description:** Historique de toutes les exécutions de workflows

**Champs principaux:**
```typescript
{
  id: RecordID,                 // ID unique de l'exécution
  workflow_name: string,        // Nom du workflow
  status: "running" | "success" | "error",
  input: any,                   // Input passé au workflow
  output: any,                  // Résultat du workflow
  metadata: {
    dossier_id?: string,        // Métadonnées custom
    user_id?: string,
    // ... autres métadonnées
  },
  created_at: datetime,
  updated_at: datetime,
  completed_at?: datetime,
  error_message?: string
}
```

**Utilisation:**
```python
# Agno crée automatiquement un enregistrement à chaque .run()
workflow = Workflow(name="analyse_dossier", db=db)
result = workflow.run(input_data, metadata={"dossier_id": "123"})
# ✅ Enregistré dans workflow_runs automatiquement
```

### 2. `workflow_sessions`

**Description:** Sessions persistées de workflows multi-tours

**Champs principaux:**
```typescript
{
  id: RecordID,
  workflow_name: string,
  session_id: string,           // ID de session unique
  state: any,                   // État du workflow
  created_at: datetime,
  updated_at: datetime
}
```

### 3. `agent_sessions`

**Description:** Sessions de conversation des agents individuels

**Champs principaux:**
```typescript
{
  id: RecordID,
  agent_name: string,
  session_id: string,
  messages: [                   // Historique des messages
    {
      role: "user" | "assistant",
      content: string,
      timestamp: datetime
    }
  ],
  created_at: datetime,
  updated_at: datetime
}
```

**Utilisation:**
```python
# Agent avec persistance
agent = Agent(name="extracteur", db=db)
response = agent.run("Extraire les données")
# ✅ Session sauvegardée automatiquement
```

### 4. `team_sessions`

**Description:** Sessions pour les équipes multi-agents

**Champs principaux:**
```typescript
{
  id: RecordID,
  team_name: string,
  session_id: string,
  agents: string[],             // Liste des agents de la team
  state: any,
  created_at: datetime,
  updated_at: datetime
}
```

## 🔗 Relations Implicites

Agno ne crée **pas** de relations formelles (RELATE dans SurrealDB), mais utilise des **IDs de référence** dans les métadonnées:

```python
# Exemple: Lier un workflow_run à un dossier
metadata = {
    "dossier_id": "dossier:abc123",
    "user_id": "user:notaire1"
}

workflow.run(input_data, metadata=metadata)
# Le workflow_run contiendra ces métadonnées
```

## 🎯 Pattern Hybride: Tables Agno + Tables Métier

### Tables Gérées par Agno (Auto-créées)
- ✅ `workflow_runs` - Historique d'exécutions
- ✅ `workflow_sessions` - États de workflows
- ✅ `agent_sessions` - Conversations agents
- ✅ `team_sessions` - États teams

### Tables Métier Personnalisées (Manuelles)
- 🔧 `user` - Utilisateurs (notaires)
- 🔧 `dossier` - Dossiers notariaux
- 🔧 `document` - Documents uploadés
- 🔧 `checklist` - Checklists générées

### Connexion Entre Les Deux

```python
# Dans DossierService
async def analyser_dossier(self, dossier_id: str):
    # 1. Récupérer le dossier (table métier)
    dossier = await self.get_dossier(dossier_id)

    # 2. Lancer le workflow Agno avec métadonnées
    workflow = WorkflowAnalyseDossier(db=self.db)
    result = workflow.run(
        input_data,
        metadata={
            "dossier_id": dossier_id,      # ✅ Lie workflow_run au dossier
            "user_id": dossier.user_id
        }
    )

    # 3. Sauvegarder le résultat (table métier)
    checklist = await self._create_checklist(
        dossier_id=dossier_id,
        checklist_data=result
    )

    return checklist
```

## 📊 Requêtes Utiles

### Historique d'un Dossier

```surql
-- Tous les workflows exécutés pour un dossier
SELECT * FROM workflow_runs
WHERE metadata.dossier_id = "dossier:abc123"
ORDER BY created_at DESC;
```

### Statistiques des Workflows

```surql
-- Nombre d'exécutions par workflow
SELECT
    workflow_name,
    count() AS executions,
    count(status = 'success') AS successes,
    count(status = 'error') AS errors
FROM workflow_runs
GROUP BY workflow_name;
```

### Dernières Exécutions

```surql
-- 10 dernières exécutions
SELECT
    workflow_name,
    status,
    created_at,
    completed_at,
    metadata
FROM workflow_runs
ORDER BY created_at DESC
LIMIT 10;
```

### Workflows En Cours

```surql
-- Workflows actuellement en cours
SELECT * FROM workflow_runs
WHERE status = 'running'
AND created_at > time::now() - 1h;
```

## 🔧 Configuration

### Pattern Officiel Agno

```python
from agno import Workflow
from agno.db.surrealdb import SurrealDb

# Configuration simple
db = SurrealDb(
    None,                                # Session (None pour auto)
    "ws://localhost:8000",              # URL WebSocket
    {"user": "root", "pass": "root"},   # Credentials
    namespace="agno",                   # Namespace
    database="notary_db"                # Database
)

# Utilisation dans Workflow
workflow = Workflow(
    name="analyse_dossier",
    db=db,  # ✅ Agno gère tout automatiquement
    agents=[...]
)

# ✅ Les tables sont créées automatiquement au premier .run()
```

## 🚀 Migration depuis Tables Manuelles

### Avant (Tables Manuelles)

```python
# On gérait tout manuellement
await db.create("agent_execution", {
    "dossier_id": dossier_id,
    "agent_name": "extracteur",
    "input": input_data,
    "output": output_data
})
```

### Après (Pattern Agno)

```python
# Agno gère automatiquement
workflow = Workflow(name="analyse", db=db)
result = workflow.run(
    input_data,
    metadata={"dossier_id": dossier_id}  # Juste passer les métadonnées
)
# ✅ Sauvegardé automatiquement dans workflow_runs
```

## 📚 Références

- [Agno SurrealDB Cookbook](https://github.com/agno-agi/agno/tree/main/cookbook/db/surrealdb)
- [surrealdb_for_workflow.py](https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_workflow.py)
- [surrealdb_for_agent.py](https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_agent.py)
- [surrealdb_for_team.py](https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_team.py)

## ⚠️ Notes Importantes

1. **Création Automatique:** Les tables sont créées **la première fois** qu'un workflow/agent/team est exécuté
2. **Pas de Migration:** Agno ne modifie pas les tables existantes
3. **Namespace Unique:** Utiliser un seul namespace pour tout (Agno + métier)
4. **Métadonnées Custom:** Profiter du champ `metadata` pour lier aux tables métier
5. **Pas de Schéma Strict:** Les tables Agno sont flexibles (SCHEMALESS)

---

**Dernière mise à jour:** 2025-11-19
**Statut:** ✅ Documenté selon exemples officiels
