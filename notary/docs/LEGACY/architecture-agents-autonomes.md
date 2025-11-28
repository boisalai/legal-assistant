# Architecture avec Agents Autonomes - Analyse et Recommandations

> **Date:** 2025-11-18
> **Statut:** Proposition d'architecture alternative
> **Auteur:** Claude Code

---

## 📊 Résumé Exécutif

Après analyse de la documentation **agentOS** et des protocoles de communication inter-agents (MCP, A2A), nous recommandons une **refonte architecturale majeure** du projet Notary Assistant vers une architecture d'**agents autonomes** communiquant via des protocoles standards.

### Problèmes de l'architecture actuelle

1. ⚠️ **Workflow séquentiel rigide** - Les 4 agents (Extracteur, Classificateur, Vérificateur, Générateur) s'exécutent de manière séquentielle, orchestrés par un workflow Python
2. ⚠️ **Couplage fort** - Tous les agents sont dans le même processus FastAPI
3. ⚠️ **Import Agno cassé** - `cannot import name 'Agent' from 'agno'` bloque l'exécution
4. ⚠️ **Pas de parallélisation** - Impossible d'exécuter plusieurs analyses simultanément efficacement
5. ⚠️ **Pas de résilience** - Si un agent échoue, tout le workflow s'arrête
6. ⚠️ **Difficulté à scaler** - Impossible de scaler un agent spécifique indépendamment

### Architecture proposée

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vue.js)                      │
│                  Interface Web pour notaires                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API / WebSocket / MCP
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AgentOS Control Plane                         │
│          - Orchestration                                         │
│          - Monitoring                                            │
│          - Session Management                                    │
│          - MCP Server (endpoint: /mcp)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP / A2A Protocol
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agents Autonomes                              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Agent     │  │   Agent     │  │   Agent     │            │
│  │ Extracteur  │  │Classificateur│ │Vérificateur │            │
│  │             │  │             │  │             │            │
│  │ - MLX/LLM   │  │ - MLX/LLM   │  │ - MLX/LLM   │            │
│  │ - Tools PDF │  │ - Knowledge │  │ - Validation│            │
│  │ - Memory    │  │   Rules     │  │ - Memory    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │   Agent     │  │Human-in-Loop│                              │
│  │ Générateur  │  │   Agent     │                              │
│  │             │  │             │                              │
│  │ - Templates │  │ - WebSocket │                              │
│  │ - PDF Export│  │ - Validation│                              │
│  │ - Memory    │  │ - Approvals │                              │
│  └─────────────┘  └─────────────┘                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SurrealDB                                  │
│  - Dossiers                                                      │
│  - Documents                                                     │
│  - Agent Sessions                                                │
│  - Memory Store                                                  │
│  - Knowledge Base                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Avantages de l'Architecture Autonome

### 1. Découplage et Scalabilité

**Avant:**
```python
# Tout dans un workflow Python
workflow.agent_extracteur.run()  # Bloquant
workflow.agent_classificateur.run()  # Doit attendre
workflow.agent_verificateur.run()  # Doit attendre
workflow.agent_generateur.run()  # Doit attendre
```

**Après:**
```python
# Agents autonomes communiquant via MCP
# L'AgentOS orchestre de manière asynchrone
agent_os.dispatch("extracteur", task_id="dossier_123")
agent_os.dispatch("classificateur", task_id="dossier_123")  # En parallèle !
# Les agents communiquent entre eux via events/messages
```

**Bénéfices:**
- ✅ Exécution parallèle des agents
- ✅ Chaque agent peut scaler indépendamment
- ✅ Déploiement séparé (containers, serverless, etc.)

### 2. Résilience et Tolérance aux Pannes

**Avant:**
```python
try:
    resultat = workflow.run(fichiers)  # Si extraction échoue → tout échoue
except Exception:
    return {"error": "Workflow failed"}
```

**Après:**
```python
# Agents autonomes avec retry, fallback, timeout
# Si l'extracteur échoue → les autres agents continuent
# Le control plane route vers un agent de backup
# Résultats partiels disponibles via sessions
```

**Bénéfices:**
- ✅ Pas de point de défaillance unique
- ✅ Dégradation gracieuse (résultats partiels)
- ✅ Retry automatique par agent
- ✅ Circuit breakers

### 3. Communication Inter-Agents Standard

**Protocoles supportés:**

#### MCP (Model Context Protocol)
- Agent ↔ Tools/APIs
- Agent ↔ SurrealDB
- Agent ↔ Frontend
- Standardisé par Anthropic (late 2024)
- "USB-C pour l'IA"

#### A2A (Agent2Agent - Google)
- Communication structurée agent ↔ agent
- Négociation de tâches
- Partage de contexte

**Exemple d'interaction:**
```
1. Frontend → AgentOS MCP: "Analyser dossier_123"
2. AgentOS → Agent Extracteur (A2A): "Extract documents from dossier_123"
3. Agent Extracteur → SurrealDB (MCP): "Get documents for dossier_123"
4. Agent Extracteur → Agent Classificateur (A2A): "Classify this data: {...}"
5. Agent Classificateur → Agent Vérificateur (A2A): "Verify classification: {...}"
6. Agent Vérificateur → Human-in-Loop Agent (A2A): "Require validation for item X"
7. Human-in-Loop → Frontend (WebSocket): "Notaire, validate this?"
8. Frontend → AgentOS (MCP): "Validated by user"
9. Agent Générateur → Frontend (MCP): "Checklist ready: {...}"
```

### 4. Interface Web Découplée

**Technologie recommandée:**
- **React** ou **Vue.js 3** avec TypeScript
- Communication via:
  - **REST API** pour CRUD (dossiers, documents)
  - **WebSocket** pour temps réel (suivi workflow, notifications)
  - **MCP Client** pour interactions avancées avec agents

**Avantages:**
- ✅ Frontend et backend totalement indépendants
- ✅ Peut déployer frontend séparément (Vercel, Netlify, Cloudflare)
- ✅ Backend API réutilisable (mobile app, CLI, etc.)
- ✅ Tests unitaires simplifiés

### 5. Observabilité et Monitoring

**AgentOS Control Plane** offre:
- Dashboard web pour voir tous les agents
- Logs et traces de chaque agent
- Sessions de conversations
- Métriques de performance
- Debug en temps réel

**Intégration possible:**
- Prometheus + Grafana pour métriques
- OpenTelemetry pour tracing
- SurrealDB `agent_execution` et `audit_log` pour historique

---

## 🏗️ Plan de Migration

### Phase 1: Setup AgentOS (1-2 jours)

**Objectif:** Créer un premier AgentOS avec un agent simple

```bash
# Installation
cd backend
uv add "agno[mcp]>=0.2.0" "fastapi[standard]" uvicorn

# Créer agent_os.py
```

**Code minimal:**
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

# Agent simple pour test
assistant = Agent(
    name="NotaryAssistant",
    model=OpenAIChat(id="gpt-4-mini"),  # Remplacer par MLX
    instructions=["Tu es un assistant notarial."],
    markdown=True,
)

# Créer l'AgentOS
agent_os = AgentOS(
    id="notary-assistant-os",
    description="Système d'agents autonomes pour notaires",
    agents=[assistant],
    enable_mcp_server=True,  # Activer MCP
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="agent_os:app", reload=True)
```

**Tester:**
```bash
uv run python agent_os.py
# Accéder à http://localhost:7777
# MCP endpoint: http://localhost:7777/mcp
```

### Phase 2: Migrer les Agents Existants (2-3 jours)

**Refactoriser chaque agent:**

```python
# backend/agents/extracteur_agent.py
from agno.agent import Agent
from backend.services.llm_service import LLMService
from backend.workflows.tools import (
    extraire_texte_pdf,
    extraire_montants,
    extraire_dates,
    extraire_noms,
    extraire_adresses,
)

def create_extracteur_agent():
    """Agent autonome d'extraction."""
    llm = LLMService.get_provider()  # MLX

    return Agent(
        name="ExtracteurDocuments",
        model=llm,
        description="Expert extraction documents notariaux québécois",
        instructions=[
            "Extrais les informations des documents PDF",
            "Utilise les tools disponibles",
            "Retourne JSON structuré",
            "Communique résultats via MCP au ClassificateurAgent"
        ],
        tools=[
            extraire_texte_pdf,
            extraire_montants,
            extraire_dates,
            extraire_noms,
            extraire_adresses,
        ],
        markdown=False,
    )
```

**Faire la même chose pour:**
- `classificateur_agent.py`
- `verificateur_agent.py`
- `generateur_agent.py`
- `human_loop_agent.py` (nouveau!)

### Phase 3: Communication Inter-Agents (2-3 jours)

**Option A: Utiliser AgentOS Teams**

```python
from agno.team import Team

# Créer une équipe d'agents
analyse_team = Team(
    name="AnalyseNotarialeTeam",
    agents=[
        extracteur_agent,
        classificateur_agent,
        verificateur_agent,
        generateur_agent,
    ],
    # Les agents communiquent automatiquement
)

agent_os = AgentOS(
    id="notary-os",
    teams=[analyse_team],
    enable_mcp_server=True,
)
```

**Option B: Event-Driven avec Message Queue**

```python
# Utiliser Redis ou Kafka pour messages inter-agents
# Agent Extracteur publie "extraction_complete"
# Agent Classificateur subscribe à "extraction_complete"

import redis.asyncio as redis
from agno.agent import Agent

async def setup_agent_communication():
    r = await redis.from_url("redis://localhost:6379")

    # Agent Extracteur
    async def on_extraction_complete(data):
        await r.publish("extraction_complete", json.dumps(data))

    # Agent Classificateur
    async def listen_extraction():
        pubsub = r.pubsub()
        await pubsub.subscribe("extraction_complete")
        async for message in pubsub.listen():
            # Process message
            classificateur_agent.run(message['data'])
```

### Phase 4: Frontend React/Vue (1 semaine)

**Stack recommandée:**
```json
{
  "frontend": {
    "framework": "React 18 + TypeScript",
    "state": "Zustand ou TanStack Query",
    "ui": "shadcn/ui + Tailwind CSS",
    "api": "Axios + React Query",
    "websocket": "Socket.io-client",
    "mcp": "@modelcontextprotocol/sdk"
  }
}
```

**Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── DossierUpload.tsx      # Drag & drop PDFs
│   │   ├── AnalyseProgress.tsx    # Suivi en temps réel
│   │   ├── ChecklistView.tsx      # Affichage checklist
│   │   └── AgentStatus.tsx        # Statut des agents
│   ├── hooks/
│   │   ├── useMCP.ts              # Hook pour MCP
│   │   ├── useWebSocket.ts        # Hook pour WS
│   │   └── useAgentOS.ts          # Hook pour AgentOS API
│   ├── services/
│   │   ├── api.ts                 # API REST
│   │   ├── mcp.ts                 # MCP client
│   │   └── websocket.ts           # WebSocket
│   └── pages/
│       ├── Dashboard.tsx
│       ├── DossierList.tsx
│       └── DossierDetail.tsx
```

**Communication Frontend ↔ Backend:**

```typescript
// frontend/src/hooks/useAgentOS.ts
import { useMutation, useQuery } from '@tanstack/react-query'
import { MCPClient } from '@modelcontextprotocol/sdk'

export function useAgentOS() {
  const mcpClient = new MCPClient('http://localhost:7777/mcp')

  // Lancer analyse via MCP
  const analyser = useMutation({
    mutationFn: async (dossierId: string) => {
      return await mcpClient.call('analyse_dossier', {
        dossier_id: dossierId
      })
    }
  })

  // Suivre progression via WebSocket
  const { data: progress } = useQuery({
    queryKey: ['progress', dossierId],
    queryFn: () => fetchProgress(dossierId),
    refetchInterval: 1000  // Poll every 1s
  })

  return { analyser, progress }
}
```

### Phase 5: Déploiement Production (3-5 jours)

**Architecture de déploiement recommandée:**

```yaml
# docker-compose.production.yml
version: '3.9'

services:
  # Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=https://api.notary.com
      - NEXT_PUBLIC_MCP_URL=wss://api.notary.com/mcp
    deploy:
      replicas: 2

  # AgentOS Control Plane
  agent-os:
    build: ./backend
    command: uvicorn agent_os:app --host 0.0.0.0 --port 7777
    ports:
      - "7777:7777"
    environment:
      - SURREALDB_URL=ws://surrealdb:8000
      - REDIS_URL=redis://redis:6379
    deploy:
      replicas: 2

  # Agent Extracteur (scalable indépendamment)
  agent-extracteur:
    build: ./backend
    command: python agents/extracteur_service.py
    environment:
      - AGENT_ID=extracteur
      - REDIS_URL=redis://redis:6379
    deploy:
      replicas: 3  # Scaler car extraction intensive

  # Agent Classificateur
  agent-classificateur:
    build: ./backend
    command: python agents/classificateur_service.py
    deploy:
      replicas: 1

  # Agent Vérificateur
  agent-verificateur:
    build: ./backend
    command: python agents/verificateur_service.py
    deploy:
      replicas: 2

  # Agent Générateur
  agent-generateur:
    build: ./backend
    command: python agents/generateur_service.py
    deploy:
      replicas: 1

  # SurrealDB
  surrealdb:
    image: surrealdb/surrealdb:latest
    volumes:
      - surreal-data:/data
    ports:
      - "8000:8000"

  # Redis (message queue)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  surreal-data:
```

**Orchestration Kubernetes (optionnel):**
```yaml
# k8s/agent-extracteur-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-extracteur
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-extracteur
  template:
    metadata:
      labels:
        app: agent-extracteur
    spec:
      containers:
      - name: extracteur
        image: notary/agent-extracteur:latest
        resources:
          requests:
            memory: "2Gi"  # MLX model
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        env:
        - name: AGENT_ID
          value: "extracteur"
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis_url
```

---

## 🔄 Comparaison Architectures

| Critère | Architecture Actuelle | Architecture Agents Autonomes |
|---------|----------------------|------------------------------|
| **Couplage** | Fort (monolithe) | Faible (microservices) |
| **Scalabilité** | Limitée (scale tout ou rien) | ✅ Excellente (scale par agent) |
| **Résilience** | Faible (1 erreur = tout échoue) | ✅ Élevée (isolation erreurs) |
| **Parallélisation** | Non (séquentiel) | ✅ Oui (asynchrone) |
| **Déploiement** | Monolithe | ✅ Indépendant par agent |
| **Observabilité** | Limitée | ✅ Excellente (AgentOS dashboard) |
| **Communication** | Appels Python directs | ✅ MCP/A2A standardisé |
| **Frontend** | Couplé (FastAPI templates) | ✅ Découplé (React/Vue SPA) |
| **Tests** | Difficile | ✅ Facile (agents isolés) |
| **Maintenance** | Difficile | ✅ Facile (responsabilités claires) |

---

## 📈 Feuille de Route Recommandée

### Court Terme (2-3 semaines)
1. ✅ **Semaine 1:** Setup AgentOS + migrer 1 agent (Extracteur)
2. ✅ **Semaine 2:** Migrer les 3 autres agents + communication MCP
3. ✅ **Semaine 3:** Frontend React basique + intégration WebSocket

### Moyen Terme (1-2 mois)
4. ✅ Frontend complet avec toutes les fonctionnalités
5. ✅ Tests end-to-end automatisés
6. ✅ Documentation complète
7. ✅ Déploiement Docker Compose

### Long Terme (3-6 mois)
8. ✅ Optimisations performance (cache, indexation)
9. ✅ Monitoring production (Prometheus/Grafana)
10. ✅ Déploiement Kubernetes si nécessaire
11. ✅ Features avancées (multi-tenancy, analytics)

---

## ❓ FAQ

### Q: Faut-il tout refaire from scratch?

**R:** Non ! On peut migrer progressivement:
1. Garder FastAPI actuel pour API REST (CRUD dossiers/documents)
2. Ajouter AgentOS en parallèle
3. Migrer un agent à la fois
4. Remplacer progressivement le workflow

### Q: MCP est-il mature?

**R:** Oui, MCP a été introduit par Anthropic fin 2024 et est déjà adopté par:
- Anthropic Claude
- Agno
- LangChain (support en cours)
- Plusieurs frameworks open-source

C'est le "USB-C pour l'IA" - standardisation en cours.

### Q: React ou Vue.js?

**R:** Les deux sont excellents. Recommandations:
- **React** si vous voulez l'écosystème le plus large (Next.js, Remix, etc.)
- **Vue.js** si vous préférez une syntaxe plus simple et progressive

Pour ce projet, **React avec Next.js** serait optimal (SSR, routing, API routes).

### Q: Quel effort de migration?

**Estimation:**
- **Setup AgentOS:** 1-2 jours
- **Migration agents (4):** 2-3 jours
- **Communication inter-agents:** 2-3 jours
- **Frontend React:** 1-2 semaines
- **Tests + déploiement:** 1 semaine

**Total: 3-4 semaines** pour une première version fonctionnelle.

### Q: Peut-on garder MLX local?

**R:** Oui ! MLX reste le modèle LLM local. On remplace juste:
- L'orchestration (Workflow → AgentOS)
- La communication (appels Python → MCP/A2A)
- Le frontend (aucun → React SPA)

Les agents utilisent toujours MLX pour l'inférence.

---

## 🎯 Recommandation Finale

**OUI, migrez vers une architecture d'agents autonomes avec AgentOS + React.**

**Raisons principales:**
1. ✅ Résout le problème d'imports Agno actuel
2. ✅ Architecture moderne, scalable et résiliente
3. ✅ Meilleure expérience utilisateur (temps réel, réactivité)
4. ✅ Facilite ajout de nouveaux agents (human-in-loop, validation, analytics)
5. ✅ Standards de l'industrie (MCP, A2A)
6. ✅ Prêt pour la production

**Commencez par:**
```bash
# 1. Setup AgentOS minimal
cd backend
uv add "agno[mcp]>=0.2.0"
python agent_os.py

# 2. Migrer Agent Extracteur
# Tester MCP endpoint

# 3. Itérer sur les autres agents
```

**Point de contact:**
Si vous voulez que je vous aide à implémenter cette architecture, je peux:
1. Créer le fichier `agent_os.py` de base
2. Migrer le premier agent (Extracteur)
3. Setup communication MCP
4. Créer structure frontend React

Voulez-vous que je commence?
