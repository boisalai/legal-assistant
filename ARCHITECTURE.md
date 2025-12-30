# Legal Assistant - Architecture Technique

## Vue d'ensemble

Application d'assistant juridique avec transcription audio, analyse de documents et agent conversationnel.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│    SurrealDB    │
│   (Next.js)     │     │   (FastAPI)     │     │   (Port 8002)   │
│   Port 3001     │     │   Port 8000     │     └─────────────────┘
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐
              │ Whisper │  │  Agno   │  │   LLM   │
              │  (MLX)  │  │ Agent   │  │ Provider│
              └─────────┘  └─────────┘  └─────────┘
```

## Structure des dossiers

```
legal-assistant/
├── backend/
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── config/
│   │   └── settings.py         # Configuration (env vars, paths)
│   ├── models/
│   │   └── *.py                # Modèles Pydantic
│   ├── routes/
│   │   ├── judgments.py        # CRUD dossiers
│   │   ├── documents.py        # Upload/gestion documents
│   │   ├── analysis.py         # Analyse de dossiers
│   │   └── chat.py             # Agent conversationnel
│   ├── services/
│   │   ├── surreal_service.py  # Client SurrealDB
│   │   ├── whisper_service.py  # Transcription audio (MLX)
│   │   ├── model_factory.py    # Création modèles LLM
│   │   └── llm_settings.py     # Persistance config LLM
│   ├── tools/
│   │   └── transcription_tool.py  # Outil Agno pour transcription
│   └── workflows/
│       └── transcribe_audio.py    # Workflow transcription complet
│
├── frontend/
│   ├── src/
│   │   ├── app/                # Pages Next.js (App Router)
│   │   │   ├── cases/[id]/     # Page détail dossier
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── ui/             # Composants shadcn/ui
│   │   │   ├── layout/         # AppShell, navigation
│   │   │   └── cases/          # Composants spécifiques dossiers
│   │   ├── lib/
│   │   │   └── api.ts          # Client API
│   │   └── types/
│   │       └── index.ts        # Types TypeScript
│   └── ...
│
└── uploads/                    # Fichiers uploadés (par dossier)
```

## Backend

### Services principaux

#### SurrealDB Service (`services/surreal_service.py`)
```python
from services.surreal_service import get_surreal_service

service = get_surreal_service()
await service.connect()

# CRUD
await service.create("document", data, record_id="abc123")
await service.query("SELECT * FROM document WHERE judgment_id = $id", {"id": "judgment:xxx"})
await service.merge("document:abc", {"field": "value"})  # Mise à jour partielle
await service.update("document:abc", data)               # Remplace tout
await service.delete("document:abc")
```

#### Whisper Service (`services/whisper_service.py`)
```python
from services.whisper_service import get_whisper_service, WHISPER_AVAILABLE

if WHISPER_AVAILABLE:
    service = get_whisper_service(model_name="large-v3-turbo")
    result = await service.transcribe("/path/to/audio.mp3", language="fr")
    # result.success, result.text, result.duration, result.segments
```

Modèles disponibles: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo` (recommandé)

#### Model Factory (`services/model_factory.py`)
```python
from services.model_factory import create_model

# Formats supportés
model = create_model("ollama:qwen2.5:7b")
model = create_model("anthropic:claude-sonnet-4-20250514")
model = create_model("openai:gpt-4o")
```

### Routes API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/judgments` | GET/POST | Liste/création dossiers |
| `/api/judgments/{id}` | GET/PATCH/DELETE | CRUD dossier |
| `/api/judgments/{id}/documents` | GET/POST | Liste/upload documents |
| `/api/judgments/{id}/documents/{doc_id}` | DELETE | Suppression document |
| `/api/judgments/{id}/documents/{doc_id}/download` | GET | Téléchargement |
| `/api/judgments/{id}/chat` | POST | Chat avec agent |
| `/api/judgments/{id}/chat/stream` | POST | Chat streaming (SSE) |
| `/api/analysis/{id}/start` | POST | Démarrer analyse |
| `/api/settings/llm` | GET/POST | Configuration LLM |

### Créer un nouvel outil Agno

1. Créer le fichier dans `tools/`:
```python
# tools/mon_outil.py
from agno.tools import tool

@tool(name="mon_outil")
async def mon_outil(case_id: str, param: str) -> str:
    """
    Description de l'outil pour l'agent.

    Args:
        case_id: ID du dossier
        param: Description du paramètre

    Returns:
        Résultat de l'opération
    """
    # Logique de l'outil
    return "Résultat"
```

2. Enregistrer dans `routes/chat.py`:
```python
from tools.mon_outil import mon_outil

# Dans create_agent()
agent = Agent(
    tools=[transcribe_audio, mon_outil],  # Ajouter ici
    ...
)
```

### Workflows Agno

Agno propose deux approches pour orchestrer des traitements multi-étapes :

#### 1. Workflow déclaratif (agents uniquement)

Pour enchaîner plusieurs agents LLM, utilisez l'API native `Workflow` :

```python
from agno.agent import Agent
from agno.workflow import Workflow

# Créer les agents spécialisés
analyst = Agent(
    name="Analyst",
    model=model,
    instructions="Tu analyses les documents juridiques...",
)

summarizer = Agent(
    name="Summarizer",
    model=model,
    instructions="Tu crées des résumés structurés...",
)

# Créer le workflow
workflow = Workflow(
    name="Document Analysis",
    steps=[analyst, summarizer],  # Exécutés séquentiellement
)

# Exécuter
workflow.print_response("Analyse ce document: ...", stream=True)
```

#### 2. Workflow hybride (Python + agents)

Agno permet de mélanger des fonctions Python et des agents dans un même workflow :

```python
from agno.agent import Agent
from agno.workflow import Workflow, StepOutput

# Fonction Python comme étape
def preprocess_step(step_input):
    """Étape de prétraitement (non-LLM)."""
    data = step_input.input
    # Logique Python: validation, extraction, API externe...
    processed = f"Données prétraitées: {data}"
    return StepOutput(content=processed)

def postprocess_step(step_input):
    """Étape de post-traitement (non-LLM)."""
    # Récupérer le résultat de l'étape précédente
    result = step_input.input
    # Logique: sauvegarde, formatage, notification...
    return StepOutput(content=f"Finalisé: {result}")

# Agent LLM
analyzer = Agent(
    name="Analyzer",
    model=model,
    instructions="Tu analyses les données prétraitées...",
)

# Workflow mixte: Python → Agent → Python
workflow = Workflow(
    name="Pipeline Hybride",
    steps=[
        preprocess_step,   # Étape Python
        analyzer,          # Agent LLM
        postprocess_step,  # Étape Python
    ]
)

# Exécuter
workflow.print_response("Données à traiter...", stream=True)
```

#### 3. Workflow avec classe personnalisée

Pour des workflows complexes avec état et callbacks de progression :

```python
from agno.agent import Agent
from agno.workflow import Workflow
from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class WorkflowResult:
    success: bool
    data: str = ""
    error: Optional[str] = None

class MonWorkflowAvance:
    """Wrapper pour workflow avec progression et gestion d'erreurs."""

    def __init__(
        self,
        model,
        on_progress: Optional[Callable[[str, int], None]] = None,
    ):
        self.model = model
        self.on_progress = on_progress
        self._workflow = self._build_workflow()

    def _emit(self, message: str, pct: int):
        if self.on_progress:
            self.on_progress(message, pct)

    def _build_workflow(self) -> Workflow:
        agent = Agent(
            name="Processor",
            model=self.model,
            instructions="Tu traites les données...",
        )
        return Workflow(name="Mon Workflow", steps=[agent])

    async def run(self, input_data: str) -> WorkflowResult:
        try:
            self._emit("Démarrage...", 10)
            result = self._workflow.run(input_data)
            self._emit("Terminé", 100)
            return WorkflowResult(success=True, data=result.content)
        except Exception as e:
            return WorkflowResult(success=False, error=str(e))
```

#### Exemple concret : TranscriptionWorkflow

Voir `workflows/transcribe_audio.py` pour un exemple complet combinant :
1. **Whisper** (Python) - Transcription audio
2. **Agent Formatter** (LLM) - Formatage markdown
3. **Sauvegarde** (Python) - Persistance SurrealDB

```python
from workflows.transcribe_audio import TranscriptionWorkflow

workflow = TranscriptionWorkflow(
    whisper_model="large-v3-turbo",
    on_progress=lambda step, msg, pct: print(f"{step}: {msg} ({pct}%)")
)

result = await workflow.run(
    audio_path="/path/to/audio.mp3",
    judgment_id="judgment:xxx",
    language="fr"
)
# result.transcript_text, result.formatted_markdown, result.document_id
```

## Frontend

### Client API (`lib/api.ts`)

```typescript
import { casesApi, documentsApi, chatApi } from "@/lib/api";

// Dossiers
const cases = await casesApi.list();
const caseData = await casesApi.get(id);
await casesApi.create({ nom_dossier: "Mon dossier" });
await casesApi.update(id, { description: "..." });
await casesApi.delete(id);

// Documents
const docs = await documentsApi.list(caseId);
await documentsApi.upload(caseId, file);
await documentsApi.delete(caseId, docId);

// Chat
const response = await chatApi.send(caseId, message);
// ou streaming
chatApi.stream(caseId, message, {
  onToken: (token) => console.log(token),
  onComplete: (response) => console.log("Fini"),
  onError: (error) => console.error(error),
});
```

### Types principaux (`types/index.ts`)

```typescript
interface Case {
  id: string;
  nom_dossier: string;
  type_transaction: string;
  status: CaseStatus;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface Document {
  id: string;
  dossier_id: string;
  nom_fichier: string;
  type_fichier: string;
  taille: number;
  texte_extrait?: string;  // Présent si transcrit/extrait
}
```

### Ajouter une nouvelle page

1. Créer le fichier dans `app/`:
```typescript
// app/ma-page/page.tsx
"use client";

import { AppShell } from "@/components/layout";

export default function MaPage() {
  return (
    <AppShell>
      <div className="p-4">
        {/* Contenu */}
      </div>
    </AppShell>
  );
}
```

2. Ajouter au menu dans `components/layout/app-shell.tsx` si nécessaire.

### Ajouter un composant

```typescript
// components/cases/mon-composant.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface MonComposantProps {
  data: string;
  onAction: () => void;
}

export function MonComposant({ data, onAction }: MonComposantProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Titre</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{data}</p>
        <Button onClick={onAction}>Action</Button>
      </CardContent>
    </Card>
  );
}
```

## Base de données (SurrealDB)

### Tables principales

```sql
-- Dossiers
judgment {
  id: string,
  nom_dossier: string,
  type_transaction: string,
  status: string,
  description: string,
  user_id: string,
  created_at: datetime,
  updated_at: datetime
}

-- Documents
document {
  id: string,
  judgment_id: string,        -- Référence au dossier
  nom_fichier: string,
  type_fichier: string,
  type_mime: string,
  taille: int,
  file_path: string,
  texte_extrait: string,      -- Texte extrait/transcrit
  is_transcription: bool,     -- Est une transcription générée
  source_audio: string,       -- Nom du fichier audio source
  created_at: datetime
}
```

### Requêtes utiles

```sql
-- Documents d'un dossier
SELECT * FROM document WHERE judgment_id = "judgment:xxx"

-- Documents audio non transcrits
SELECT * FROM document
WHERE judgment_id = $id
AND type_fichier IN ["mp3", "wav", "m4a", "webm"]
AND texte_extrait IS NULL
```

## Configuration

### Variables d'environnement (.env)

```bash
# Backend
SURREALDB_URL=ws://localhost:8002/rpc
SURREALDB_NAMESPACE=legal
SURREALDB_DATABASE=assistant
SURREALDB_USER=root
SURREALDB_PASS=root

# LLM (optionnel - configurable via UI)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Chemins
UPLOAD_DIR=./uploads
```

### Démarrage

```bash
# Terminal 1: SurrealDB
docker-compose up -d
# OU en natif (depuis la racine du projet)
surreal start --user root --pass root --bind 0.0.0.0:8002 file:backend/data/surrealdb/legal.db

# Terminal 2: Backend
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

## Patterns d'agents à explorer

### 1. Agent avec outils multiples
Ajouter des outils pour recherche juridique, extraction d'entités, etc.

### 2. Workflow multi-agents
Chaîner plusieurs agents spécialisés (analyse → synthèse → vérification).

### 3. RAG (Retrieval-Augmented Generation)
Indexer les documents avec embeddings pour recherche sémantique.

### 4. Agent avec mémoire
Utiliser SurrealDB pour stocker l'historique des conversations.

### 5. MCP (Model Context Protocol)
Intégrer des serveurs MCP pour accès à des sources externes (CanLII, etc.).
