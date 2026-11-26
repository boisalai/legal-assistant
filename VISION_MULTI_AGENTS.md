# Vision : Assistant Notarial Multi-Agents Auto-Apprenant

> **CLAUDE CODE** : Ce document définit la vision et la planification pour l'évolution du projet. Référence-le pour comprendre l'architecture cible et les prochaines étapes.

## Instructions pour Claude Code

```
STACK OBLIGATOIRE : Agno, MLX, SurrealDB, FastAPI, Next.js/React
NE PAS PROPOSER : LangChain, LangGraph, CrewAI, AutoGen, PostgreSQL, MongoDB

PRIORITÉ ACTUELLE : Phase 1 — Boucle d'apprentissage (voir section 3.1)

AVANT DE CODER :
1. Vérifier la structure existante dans /backend et /frontend
2. Étendre les services existants plutôt que créer de nouvelles abstractions
3. Suivre les patterns Agno déjà utilisés dans le projet
```

---

## Contexte

Ce document présente la vision et la planification pour transformer l'application `legal-assistant` (actuellement un assistant d'études juridiques) en un **assistant intelligent pour notaires** doté de capacités multi-agents auto-apprenants.

**Idée centrale** : un notaire utilise une interface web simple pour travailler sur ses dossiers, sans savoir qu'un nombre variable d'agents intelligents (de 1 à 100) collaborent en arrière-plan pour répondre à ses demandes.

---

## 1. Vision

### 1.1 Philosophie

Les workflows traditionnels (définis étape par étape) ne correspondent pas à la réalité du travail notarial :

- Les processus sont difficiles à documenter exhaustivement
- La connaissance se construit au fil des dossiers traités
- Chaque dossier a ses particularités

**L'approche visée** : un système qui apprend le métier en observant et en interagissant, plutôt qu'en étant programmé explicitement.

### 1.2 Comportement cible

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Web                            │
│                                                             │
│  Notaire : "Prépare le dossier de succession Tremblay"     │
│                                                             │
│  [Le système, invisible pour l'utilisateur:]               │
│   → Analyse la demande                                     │
│   → Consulte sa mémoire : "Comment ai-je traité ça avant?" │
│   → Crée dynamiquement N agents selon la complexité        │
│   → Coordonne leur travail en parallèle                    │
│   → Apprend du résultat pour la prochaine fois            │
│                                                             │
│  Réponse : "J'ai analysé le dossier. Voici les documents   │
│  manquants : [...] Voulez-vous que je prépare les lettres  │
│  de demande ?"                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Types d'apprentissage visés

| Type | Description | Implémentation |
|------|-------------|----------------|
| **Processus** | Comment traite-t-on une succession ? | Observation des actions sur plusieurs dossiers |
| **Préférences** | Ce notaire préfère rédiger de telle façon | Feedback explicite + observation |
| **Domaine** | Règles fiscales pour une donation | RAG sur documentation juridique |
| **Contextuel** | Particularités de ce dossier-ci | Mémoire par dossier |

---

## 2. Architecture Cible

### 2.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION                      │
│  React/Next.js + conversation naturelle + feedback intégré  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE ORCHESTRATION                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Méta-orchestrateur                      │   │
│  │                                                      │   │
│  │  - Analyse la demande                               │   │
│  │  - Planifie les sous-tâches                         │   │
│  │  - Décide combien d'agents créer                    │   │
│  │  - Supervise l'exécution                            │   │
│  │  - Synthétise les résultats                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Pool d'agents dynamique                    │   │
│  │                                                      │   │
│  │  [Agent Recherche] [Agent Rédaction] [Agent Vérif]  │   │
│  │  [Agent N+1 créé si nécessaire...]                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE APPRENTISSAGE                     │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ Mémoire     │  │ Workflows   │  │ Préférences       │   │
│  │ épisodique  │  │ appris      │  │ utilisateur       │   │
│  │ (feedbacks) │  │ (patterns)  │  │ (corrections)     │   │
│  └─────────────┘  └─────────────┘  └───────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE CONNAISSANCE                      │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ RAG légal   │  │ Templates   │  │ Historique        │   │
│  │ (lois,      │  │ d'actes     │  │ dossiers          │   │
│  │ règlements) │  │             │  │                   │   │
│  └─────────────┘  └─────────────┘  └───────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE DONNÉES                           │
│                                                             │
│  SurrealDB (dossiers, documents, feedbacks, patterns)       │
│  ChromaDB / Qdrant (embeddings pour RAG)                    │
│  Fichiers (PDFs, courriels, actes)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE LLM                               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MLX local (tâches routinières, fine-tuné LoRA)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼ (si tâche complexe)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Claude (raisonnement juridique complexe)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Routeur LLM intelligent

Le système doit décider quel LLM utiliser selon la tâche :

| Tâche | LLM | Raison |
|-------|-----|--------|
| Classification de courriel | MLX local | Rapide, répétitif, gratuit |
| Extraction d'entités | MLX local | Pattern simple |
| Résumé de document | MLX local | Volume élevé |
| Analyse juridique complexe | API Claude | Raisonnement profond |
| Rédaction d'acte notarié | API Claude | Qualité critique |
| Cas ambigus | API Claude | Sécurité |

---

## 3. Planification des phases

### Phase 1 : Boucle d'apprentissage (2-3 semaines)

**Objectif** : Permettre au système d'apprendre des corrections de l'utilisateur.

#### 3.1.1 Modèles de données SurrealDB

```sql
-- Table des feedbacks
DEFINE TABLE feedback SCHEMAFULL;
DEFINE FIELD conversation_id ON feedback TYPE record<conversation>;
DEFINE FIELD message_id ON feedback TYPE string;
DEFINE FIELD agent_response ON feedback TYPE string;
DEFINE FIELD rating ON feedback TYPE int;  -- 1 à 5
DEFINE FIELD correction ON feedback TYPE option<string>;
DEFINE FIELD learned_pattern ON feedback TYPE option<string>;
DEFINE FIELD context ON feedback TYPE object;
DEFINE FIELD created_at ON feedback TYPE datetime DEFAULT time::now();

-- Table des patterns appris
DEFINE TABLE learned_pattern SCHEMAFULL;
DEFINE FIELD pattern_type ON learned_pattern TYPE string;  -- 'preference', 'workflow', 'correction'
DEFINE FIELD trigger_context ON learned_pattern TYPE string;
DEFINE FIELD learned_behavior ON learned_behavior TYPE string;
DEFINE FIELD confidence ON learned_pattern TYPE float;
DEFINE FIELD usage_count ON learned_pattern TYPE int DEFAULT 0;
DEFINE FIELD last_used ON learned_pattern TYPE option<datetime>;
DEFINE FIELD created_at ON learned_pattern TYPE datetime DEFAULT time::now();
DEFINE FIELD source_feedbacks ON learned_pattern TYPE array<record<feedback>>;

-- Table des préférences utilisateur
DEFINE TABLE user_preference SCHEMAFULL;
DEFINE FIELD user_id ON user_preference TYPE string;
DEFINE FIELD preference_type ON user_preference TYPE string;
DEFINE FIELD preference_value ON user_preference TYPE string;
DEFINE FIELD learned_from ON user_preference TYPE option<record<feedback>>;
DEFINE FIELD created_at ON user_preference TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON user_preference TYPE datetime DEFAULT time::now();
```

#### 3.1.2 Service d'apprentissage

Créer `backend/services/learning_service.py` :

```python
from typing import Optional, List
from datetime import datetime
from models.feedback import Feedback, LearnedPattern, UserPreference
from services.embedding_service import EmbeddingService
from services.llm_service import LLMService

class LearningService:
    """Service gérant l'apprentissage continu du système."""
    
    def __init__(self, db, embedding_service: EmbeddingService, llm_service: LLMService):
        self.db = db
        self.embedding_service = embedding_service
        self.llm_service = llm_service
    
    async def record_feedback(self, feedback: Feedback) -> Feedback:
        """Enregistre un feedback et extrait un pattern si pertinent."""
        # 1. Sauvegarder le feedback
        saved = await self.db.create("feedback", feedback.model_dump())
        
        # 2. Si correction fournie, extraire un pattern
        if feedback.correction:
            pattern = await self._extract_pattern(feedback)
            if pattern:
                await self.db.create("learned_pattern", pattern.model_dump())
        
        return saved
    
    async def _extract_pattern(self, feedback: Feedback) -> Optional[LearnedPattern]:
        """Utilise le LLM pour extraire un pattern généralisable."""
        prompt = f"""
        Analyse cette correction de l'utilisateur et extrait une règle généralisable.
        
        Réponse originale de l'agent:
        {feedback.agent_response}
        
        Correction de l'utilisateur:
        {feedback.correction}
        
        Contexte:
        {feedback.context}
        
        Réponds en JSON avec:
        - pattern_type: 'preference' | 'workflow' | 'correction'
        - trigger_context: dans quel contexte appliquer ce pattern
        - learned_behavior: ce que l'agent devrait faire différemment
        - confidence: 0.0 à 1.0
        """
        
        response = await self.llm_service.generate(prompt, response_format="json")
        # ... parser et retourner LearnedPattern
    
    async def get_relevant_learnings(self, context: str, limit: int = 5) -> List[LearnedPattern]:
        """Récupère les patterns pertinents pour le contexte actuel via RAG."""
        # 1. Générer embedding du contexte
        context_embedding = await self.embedding_service.embed(context)
        
        # 2. Recherche sémantique dans les patterns
        # (utiliser votre système de recherche vectorielle existant)
        
        # 3. Retourner les plus pertinents
        pass
    
    async def get_user_preferences(self, user_id: str) -> List[UserPreference]:
        """Récupère toutes les préférences d'un utilisateur."""
        return await self.db.query(
            "SELECT * FROM user_preference WHERE user_id = $user_id",
            {"user_id": user_id}
        )
    
    async def build_dynamic_prompt(
        self, 
        base_prompt: str, 
        context: str, 
        user_id: str
    ) -> str:
        """Construit un prompt enrichi avec les apprentissages."""
        learnings = await self.get_relevant_learnings(context)
        preferences = await self.get_user_preferences(user_id)
        
        learnings_text = "\n".join([
            f"- {l.learned_behavior} (contexte: {l.trigger_context})"
            for l in learnings
        ])
        
        preferences_text = "\n".join([
            f"- {p.preference_type}: {p.preference_value}"
            for p in preferences
        ])
        
        return f"""
{base_prompt}

## Apprentissages passés pertinents
{learnings_text if learnings_text else "Aucun apprentissage pertinent pour ce contexte."}

## Préférences de l'utilisateur
{preferences_text if preferences_text else "Aucune préférence enregistrée."}
"""
```

#### 3.1.3 Composants frontend

Ajouter dans `frontend/src/components/chat/` :

```typescript
// feedback-buttons.tsx
interface FeedbackButtonsProps {
  messageId: string;
  onFeedback: (rating: number, correction?: string) => void;
}

export function FeedbackButtons({ messageId, onFeedback }: FeedbackButtonsProps) {
  const [showCorrection, setShowCorrection] = useState(false);
  const [correction, setCorrection] = useState("");
  
  return (
    <div className="flex items-center gap-2 mt-2">
      <Button variant="ghost" size="sm" onClick={() => onFeedback(5)}>
        <ThumbsUp className="h-4 w-4" />
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setShowCorrection(true)}>
        <ThumbsDown className="h-4 w-4" />
      </Button>
      
      {showCorrection && (
        <Dialog open={showCorrection} onOpenChange={setShowCorrection}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Qu'est-ce qui n'allait pas ?</DialogTitle>
            </DialogHeader>
            <Textarea
              placeholder="Expliquez ce que vous attendiez..."
              value={correction}
              onChange={(e) => setCorrection(e.target.value)}
            />
            <Button onClick={() => {
              onFeedback(1, correction);
              setShowCorrection(false);
            }}>
              Envoyer
            </Button>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
```

#### 3.1.4 Routes API

Ajouter dans `backend/routes/` :

```python
# feedback_routes.py
from fastapi import APIRouter, Depends
from models.feedback import FeedbackCreate, Feedback
from services.learning_service import LearningService

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

@router.post("/", response_model=Feedback)
async def create_feedback(
    feedback: FeedbackCreate,
    learning_service: LearningService = Depends(get_learning_service)
):
    """Enregistre un feedback utilisateur."""
    return await learning_service.record_feedback(feedback)

@router.get("/patterns")
async def get_patterns(
    context: str,
    limit: int = 5,
    learning_service: LearningService = Depends(get_learning_service)
):
    """Récupère les patterns pertinents pour un contexte."""
    return await learning_service.get_relevant_learnings(context, limit)
```

---

### Phase 2 : Agents spécialisés (1-2 mois)

**Objectif** : Créer des agents Agno spécialisés par domaine avec un orchestrateur.

#### 3.2.1 Structure des agents

```
backend/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py           # Classe de base avec mémoire
│   ├── orchestrator.py         # Agent orchestrateur
│   ├── researcher_agent.py     # Recherche juridique
│   ├── writer_agent.py         # Rédaction d'actes
│   ├── checker_agent.py        # Vérification documentaire
│   └── classifier_agent.py     # Classification de documents
├── tools/
│   ├── existing_tools...
│   ├── delegation_tools.py     # Outils pour déléguer entre agents
│   └── workflow_tools.py       # Outils pour gérer les workflows
```

#### 3.2.2 Agent de base avec mémoire

```python
# backend/agents/base_agent.py
from agno import Agent
from services.learning_service import LearningService

class MemoryAgent(Agent):
    """Agent de base avec capacité d'apprentissage."""
    
    def __init__(
        self,
        name: str,
        tools: list,
        instructions: str,
        learning_service: LearningService,
        user_id: str,
        **kwargs
    ):
        self.learning_service = learning_service
        self.user_id = user_id
        self.base_instructions = instructions
        
        # Les instructions seront enrichies dynamiquement
        super().__init__(
            name=name,
            tools=tools,
            instructions=instructions,
            **kwargs
        )
    
    async def prepare_context(self, user_message: str) -> str:
        """Prépare le contexte avec les apprentissages."""
        return await self.learning_service.build_dynamic_prompt(
            self.base_instructions,
            user_message,
            self.user_id
        )
```

#### 3.2.3 Agent orchestrateur

```python
# backend/agents/orchestrator.py
from typing import List, Dict, Any
from agno import Agent
from agents.base_agent import MemoryAgent

class OrchestratorAgent(MemoryAgent):
    """Agent qui coordonne les autres agents."""
    
    def __init__(
        self,
        specialist_agents: Dict[str, Agent],
        **kwargs
    ):
        self.specialists = specialist_agents
        
        instructions = """
        Tu es l'orchestrateur d'une équipe d'agents spécialisés pour un cabinet de notaires.
        
        Agents disponibles:
        - researcher: Recherche juridique (lois, jurisprudence, doctrine)
        - writer: Rédaction d'actes et documents officiels
        - checker: Vérification de conformité et documents manquants
        - classifier: Classification de documents et courriels
        
        Pour chaque demande:
        1. Analyse la complexité et les besoins
        2. Décide quels agents mobiliser
        3. Délègue les sous-tâches appropriées
        4. Synthétise les résultats
        
        Tu peux déléguer à plusieurs agents en parallèle si les tâches sont indépendantes.
        """
        
        tools = [
            self._create_delegation_tool(name, agent)
            for name, agent in specialist_agents.items()
        ]
        
        super().__init__(
            name="Orchestrateur",
            tools=tools,
            instructions=instructions,
            **kwargs
        )
    
    def _create_delegation_tool(self, agent_name: str, agent: Agent):
        """Crée un outil de délégation pour un agent."""
        async def delegate(task: str, context: dict = None) -> str:
            """Délègue une tâche à l'agent spécialiste."""
            return await agent.run(task, context=context)
        
        delegate.__name__ = f"delegate_to_{agent_name}"
        delegate.__doc__ = f"Délègue une tâche à l'agent {agent_name}."
        
        return delegate
```

#### 3.2.4 Agents spécialisés

```python
# backend/agents/researcher_agent.py
from agents.base_agent import MemoryAgent
from tools.caij_search_tool import search_caij_jurisprudence
from tools.semantic_search_tool import semantic_search

class ResearcherAgent(MemoryAgent):
    """Agent spécialisé en recherche juridique."""
    
    def __init__(self, **kwargs):
        instructions = """
        Tu es un chercheur juridique spécialisé dans le droit québécois.
        
        Tes capacités:
        - Recherche dans le CAIJ (jurisprudence, doctrine)
        - Recherche sémantique dans la base documentaire
        - Analyse de textes de loi
        
        Tu fournis toujours tes sources avec précision.
        Tu distingues clairement les faits des interprétations.
        """
        
        super().__init__(
            name="Chercheur juridique",
            tools=[search_caij_jurisprudence, semantic_search],
            instructions=instructions,
            **kwargs
        )
```

```python
# backend/agents/checker_agent.py
from agents.base_agent import MemoryAgent

class CheckerAgent(MemoryAgent):
    """Agent spécialisé en vérification documentaire."""
    
    def __init__(self, **kwargs):
        instructions = """
        Tu es un vérificateur de conformité pour dossiers notariaux.
        
        Tes responsabilités:
        - Identifier les documents manquants selon le type de dossier
        - Vérifier la cohérence des informations entre documents
        - Signaler les anomalies ou incohérences
        - Proposer une checklist de points à valider
        
        Types de dossiers que tu connais:
        - Succession: testament, certificat de décès, inventaire, etc.
        - Vente immobilière: titre, certificat de localisation, etc.
        - Donation: évaluation, consentements, etc.
        - Testament: identité, capacité, témoins, etc.
        """
        
        super().__init__(
            name="Vérificateur",
            tools=[check_document_presence, compare_documents, generate_checklist],
            instructions=instructions,
            **kwargs
        )
```

---

### Phase 3 : Orchestration dynamique (3-6 mois)

**Objectif** : Permettre la création dynamique d'agents selon le contexte.

#### 3.3.1 Factory d'agents

```python
# backend/agents/agent_factory.py
from typing import Dict, Any, List
from agents.base_agent import MemoryAgent

class AgentFactory:
    """Crée des agents dynamiquement selon les besoins."""
    
    # Templates d'agents disponibles
    AGENT_TEMPLATES = {
        "researcher": {
            "class": "ResearcherAgent",
            "capabilities": ["search_legal", "search_semantic", "analyze_law"]
        },
        "writer": {
            "class": "WriterAgent", 
            "capabilities": ["draft_act", "write_letter", "format_document"]
        },
        "checker": {
            "class": "CheckerAgent",
            "capabilities": ["verify_documents", "check_compliance", "generate_checklist"]
        },
        "classifier": {
            "class": "ClassifierAgent",
            "capabilities": ["classify_email", "classify_document", "extract_entities"]
        }
    }
    
    def __init__(self, learning_service, llm_service):
        self.learning_service = learning_service
        self.llm_service = llm_service
    
    async def create_agents_for_task(
        self, 
        task_description: str,
        context: Dict[str, Any]
    ) -> List[MemoryAgent]:
        """Détermine et crée les agents nécessaires pour une tâche."""
        
        # 1. Analyser la tâche avec le LLM
        analysis_prompt = f"""
        Analyse cette tâche et détermine quels types d'agents sont nécessaires.
        
        Tâche: {task_description}
        Contexte: {context}
        
        Agents disponibles: {list(self.AGENT_TEMPLATES.keys())}
        
        Réponds en JSON:
        {{
            "agents_needed": ["agent1", "agent2"],
            "reasoning": "explication",
            "parallel_execution": true/false
        }}
        """
        
        analysis = await self.llm_service.generate(analysis_prompt, response_format="json")
        
        # 2. Créer les agents
        agents = []
        for agent_type in analysis["agents_needed"]:
            agent = await self._instantiate_agent(agent_type, context)
            agents.append(agent)
        
        return agents
    
    async def _instantiate_agent(
        self, 
        agent_type: str, 
        context: Dict[str, Any]
    ) -> MemoryAgent:
        """Instancie un agent avec le contexte approprié."""
        template = self.AGENT_TEMPLATES[agent_type]
        # ... logique d'instanciation
```

#### 3.3.2 Orchestrateur dynamique

```python
# backend/agents/dynamic_orchestrator.py
from typing import Dict, Any, List
from agents.agent_factory import AgentFactory
from services.learning_service import LearningService

class DynamicOrchestrator:
    """Orchestrateur qui crée et coordonne des agents dynamiquement."""
    
    def __init__(
        self,
        agent_factory: AgentFactory,
        learning_service: LearningService,
        llm_service
    ):
        self.agent_factory = agent_factory
        self.learning_service = learning_service
        self.llm_service = llm_service
    
    async def handle_request(
        self,
        request: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Traite une demande de bout en bout."""
        
        # 1. Planifier
        plan = await self._create_plan(request, context)
        
        # 2. Créer les agents nécessaires
        agents = await self.agent_factory.create_agents_for_task(
            request, context
        )
        
        # 3. Exécuter le plan
        results = await self._execute_plan(plan, agents)
        
        # 4. Synthétiser
        response = await self._synthesize_results(request, results)
        
        # 5. Apprendre
        await self._record_execution(plan, results, response)
        
        return response
    
    async def _create_plan(
        self,
        request: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crée un plan d'exécution."""
        
        # Récupérer les workflows appris similaires
        similar_workflows = await self.learning_service.get_similar_workflows(request)
        
        plan_prompt = f"""
        Crée un plan pour accomplir cette tâche.
        
        Demande: {request}
        Contexte: {context}
        
        Workflows similaires passés:
        {similar_workflows}
        
        Réponds en JSON:
        {{
            "tasks": [
                {{"id": "1", "type": "research", "description": "...", "depends_on": []}},
                {{"id": "2", "type": "verify", "description": "...", "depends_on": ["1"]}}
            ],
            "parallel_groups": [["1"], ["2"]],
            "estimated_complexity": "low/medium/high"
        }}
        """
        
        return await self.llm_service.generate(plan_prompt, response_format="json")
    
    async def _execute_plan(
        self,
        plan: Dict[str, Any],
        agents: List
    ) -> List[Dict[str, Any]]:
        """Exécute le plan en respectant les dépendances."""
        results = {}
        
        for parallel_group in plan["parallel_groups"]:
            # Exécuter les tâches en parallèle
            group_tasks = [
                task for task in plan["tasks"] 
                if task["id"] in parallel_group
            ]
            
            group_results = await asyncio.gather(*[
                self._execute_task(task, agents, results)
                for task in group_tasks
            ])
            
            for task, result in zip(group_tasks, group_results):
                results[task["id"]] = result
        
        return results
```

---

## 4. Considérations techniques

### 4.1 MLX vs Ollama

Pour l'hébergement local sur Mac Studio, **MLX est recommandé** :

| Aspect | MLX | Ollama |
|--------|-----|--------|
| Performance sur Apple Silicon | Native, optimisé | Via Docker/Rosetta |
| Utilisation mémoire | Meilleure | Plus gourmande |
| Fine-tuning LoRA | Supporté | Limité |
| Facilité d'installation | Moyenne | Simple |

Configuration MLX recommandée :
- Modèle de base : Qwen 2.5 14B ou Mistral 7B
- Quantification : 4-bit pour économiser la RAM
- Fine-tuning : LoRA sur les interactions passées

### 4.2 Fine-tuning LoRA périodique

Processus suggéré :

1. **Collecte** : Accumuler les feedbacks positifs (rating >= 4)
2. **Préparation** : Formater en paires (prompt, réponse attendue)
3. **Entraînement** : Fine-tuning LoRA toutes les semaines/mois
4. **Évaluation** : Tester sur un jeu de validation
5. **Déploiement** : Remplacer l'adaptateur si amélioration

```bash
# Exemple avec mlx-lm
mlx_lm.lora \
    --model mistral-7b-instruct \
    --train \
    --data ./training_data.jsonl \
    --adapter-path ./adapters/notarial_v1
```

### 4.3 Routeur de complexité

Implémenter un routeur qui décide quel LLM utiliser :

```python
# backend/services/llm_router.py
class LLMRouter:
    """Route les requêtes vers le LLM approprié."""
    
    COMPLEXITY_THRESHOLDS = {
        "low": ["classify", "extract", "summarize_short"],
        "medium": ["summarize_long", "draft_simple", "search"],
        "high": ["legal_analysis", "draft_act", "complex_reasoning"]
    }
    
    async def route(self, task_type: str, content: str) -> str:
        """Détermine quel LLM utiliser."""
        
        # Estimation de complexité
        complexity = self._estimate_complexity(task_type, content)
        
        if complexity == "low":
            return "mlx_local"  # Qwen local
        elif complexity == "medium":
            # Dépend de la charge et de la criticité
            return "mlx_local" if self._local_available() else "claude_api"
        else:
            return "claude_api"  # Toujours Claude pour le complexe
    
    def _estimate_complexity(self, task_type: str, content: str) -> str:
        # Logique d'estimation
        pass
```

### 4.4 Gestion des dossiers notariaux

Modèle de données pour les dossiers :

```sql
-- Table des dossiers
DEFINE TABLE dossier SCHEMAFULL;
DEFINE FIELD numero ON dossier TYPE string;
DEFINE FIELD type ON dossier TYPE string;  -- 'succession', 'vente', 'donation', etc.
DEFINE FIELD statut ON dossier TYPE string;  -- 'ouvert', 'en_cours', 'clos'
DEFINE FIELD client_principal ON dossier TYPE record<client>;
DEFINE FIELD parties ON dossier TYPE array<record<partie>>;
DEFINE FIELD documents ON dossier TYPE array<record<document>>;
DEFINE FIELD taches ON dossier TYPE array<record<tache>>;
DEFINE FIELD notes ON dossier TYPE array<object>;
DEFINE FIELD metadata ON dossier TYPE object;
DEFINE FIELD created_at ON dossier TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON dossier TYPE datetime DEFAULT time::now();

-- Table des tâches
DEFINE TABLE tache SCHEMAFULL;
DEFINE FIELD dossier ON tache TYPE record<dossier>;
DEFINE FIELD description ON tache TYPE string;
DEFINE FIELD statut ON tache TYPE string;  -- 'a_faire', 'en_cours', 'complete'
DEFINE FIELD assignee ON tache TYPE option<string>;
DEFINE FIELD echeance ON tache TYPE option<datetime>;
DEFINE FIELD generee_par_agent ON tache TYPE bool DEFAULT false;
DEFINE FIELD created_at ON tache TYPE datetime DEFAULT time::now();
```

---

## 5. Interface utilisateur

### 5.1 Principes

- **Simplicité** : Le notaire ne voit que ce qui est pertinent
- **Transparence contrôlée** : Option pour voir ce que font les agents
- **Feedback naturel** : Intégré dans le flux de travail

### 5.2 Composants clés à développer

1. **Vue Dossier** : Dashboard d'un dossier avec documents, tâches, historique
2. **Chat contextuel** : Conversation liée au dossier ouvert
3. **Indicateur d'agents** : Badge montrant "3 agents travaillent..." (optionnel)
4. **Panel de feedback** : Thumbs up/down + correction après chaque réponse
5. **Historique d'apprentissage** : Vue des patterns appris (pour admin)

---

## 6. Métriques et évaluation

### 6.1 Métriques à suivre

| Métrique | Description | Cible |
|----------|-------------|-------|
| Taux de satisfaction | % de thumbs up | > 85% |
| Taux de correction | % de réponses corrigées | < 15% |
| Temps de réponse | Latence moyenne | < 5s pour simple, < 30s pour complexe |
| Utilisation LLM local | % de requêtes traitées localement | > 70% |
| Patterns appris | Nombre de patterns actifs | Croissant |
| Réutilisation patterns | % de réponses utilisant un pattern | Croissant |

### 6.2 Tests

```python
# tests/test_learning_service.py
async def test_feedback_creates_pattern():
    """Vérifie qu'une correction génère un pattern."""
    feedback = Feedback(
        conversation_id="conv_1",
        agent_response="Le délai est de 30 jours.",
        rating=1,
        correction="Non, pour une succession, c'est 6 mois.",
        context={"type": "succession"}
    )
    
    result = await learning_service.record_feedback(feedback)
    
    patterns = await db.query("SELECT * FROM learned_pattern")
    assert len(patterns) == 1
    assert "succession" in patterns[0].trigger_context
    assert "6 mois" in patterns[0].learned_behavior
```

---

## 7. Stack technique (contraintes)

> **Important** : Ce projet utilise exclusivement les technologies suivantes. Ne pas proposer d'alternatives.

### 7.1 Stack obligatoire

| Composant | Technologie | Documentation |
|-----------|-------------|---------------|
| Framework agents | **Agno** | https://docs.agno.com |
| LLM local | **MLX** | https://ml-explore.github.io/mlx |
| Base de données | **SurrealDB** | https://surrealdb.com/docs |
| Frontend | **Next.js + React** | Existant dans `/frontend` |
| Backend | **FastAPI** | Existant dans `/backend` |

### 7.2 Modèles LLM

| Usage | Modèle | Taille | Notes |
|-------|--------|--------|-------|
| Local rapide | Qwen 2.5 7B | ~4GB (4-bit) | Bon en français |
| Local qualité | Qwen 2.5 14B | ~8GB (4-bit) | Meilleur raisonnement |
| Cloud complexe | Claude Sonnet 4 | API | Raisonnement juridique |
| Embeddings | BGE-M3 | ~2GB | Multilingue, local |

### 7.3 Principes de développement

- Utiliser les patterns Agno existants dans le projet
- Étendre les services existants plutôt que créer de nouvelles abstractions
- Garder la compatibilité avec la structure actuelle du projet
- Tester chaque ajout avant de passer au suivant

---

## 8. Checklist Phase 1 (ordre d'exécution)

> **Claude Code** : Suivre cet ordre. Cocher chaque étape complétée.

### Étape 1 : Modèles de données
- [ ] Créer `backend/models/feedback.py` avec `Feedback`, `LearnedPattern`, `UserPreference`
- [ ] Ajouter les définitions de tables dans SurrealDB (voir section 3.1.1)
- [ ] Tester la création/lecture des modèles

### Étape 2 : Service d'apprentissage
- [ ] Créer `backend/services/learning_service.py`
- [ ] Implémenter `record_feedback()`
- [ ] Implémenter `_extract_pattern()` avec appel LLM
- [ ] Implémenter `get_relevant_learnings()` avec RAG
- [ ] Implémenter `build_dynamic_prompt()`
- [ ] Écrire les tests unitaires

### Étape 3 : Routes API
- [ ] Créer `backend/routes/feedback_routes.py`
- [ ] Endpoint `POST /api/feedback`
- [ ] Endpoint `GET /api/feedback/patterns`
- [ ] Ajouter les routes dans `main.py`

### Étape 4 : Frontend
- [ ] Créer `frontend/src/components/chat/feedback-buttons.tsx`
- [ ] Intégrer dans le composant de message existant
- [ ] Connecter à l'API `/api/feedback`
- [ ] Tester le flux complet

### Étape 5 : Intégration agent
- [ ] Modifier l'agent existant pour utiliser `build_dynamic_prompt()`
- [ ] Vérifier que les patterns appris influencent les réponses
- [ ] Documenter le comportement

---

*Document créé le 30 janvier 2026 — À mettre à jour au fil du développement*
