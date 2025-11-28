# Guide des Concepts Agno

Ce document explique les concepts clés d'Agno et comment les utiliser dans le projet Notary Assistant.

## Qu'est-ce qu'Agno?

**Agno** est un framework Python pour créer des **workflows multi-agents** avec des LLMs (Large Language Models). Il permet de:

- Orchestrer plusieurs agents IA qui collaborent
- Créer des workflows déterministes et reproductibles
- Gérer l'état entre les différentes étapes
- Intégrer des confirmations humaines (human-in-the-loop)
- Tester et déboguer facilement les workflows

## Concepts fondamentaux

### 1. Agent 🤖

Un **Agent** est un "travailleur IA" avec un rôle spécifique.

```python
agent = Agent(
    name="MonAgent",              # Identifiant unique
    role="Expert en X",           # Rôle/expertise
    instructions=[...],           # Comment il doit se comporter
    tools=[fonction1, fonction2], # Outils qu'il peut utiliser
    model="gpt-4"                 # Modèle LLM
)
```

**Caractéristiques:**
- Un agent a une **personnalité** définie (role + instructions)
- Il peut utiliser des **tools** (fonctions Python)
- Il peut **raisonner** et prendre des décisions
- Il retourne des résultats structurés

**Exemple concret:**
```python
agent_verificateur = Agent(
    name="VerificateurTitres",
    role="Notaire spécialiste en vérification de titres",
    instructions=[
        "Tu vérifies la validité des titres de propriété",
        "Tu identifies les vices cachés ou problèmes légaux",
        "Tu es rigoureux et méthodique"
    ],
    tools=[verifier_registre_foncier, calculer_droits_mutation]
)
```

### 2. Tools 🛠️

Les **Tools** sont des fonctions Python que les agents peuvent appeler.

```python
def verifier_registre_foncier(adresse: str) -> dict:
    """
    Vérifie les informations au registre foncier.

    Args:
        adresse: Adresse de la propriété

    Returns:
        Informations du registre
    """
    # Logique de vérification
    return {"propriétaire": "...", "charges": [...]}
```

**Règles importantes:**
- Les tools doivent avoir des **docstrings claires**
- Les **type hints** sont obligatoires (Agno les utilise)
- Retourner des **données structurées** (dict, list, etc.)
- Une tool = une responsabilité unique

### 3. Workflow 🔄

Un **Workflow** orchestre plusieurs agents dans un ordre logique.

```python
class MonWorkflow(Workflow):
    def __init__(self):
        super().__init__(name="MonWorkflow")
        self.agent1 = Agent(...)
        self.agent2 = Agent(...)

    def run(self, input_data):
        # Étape 1
        resultat1 = self.agent1.run("Fais X")

        # Étape 2 (utilise le résultat de l'étape 1)
        resultat2 = self.agent2.run(f"Basé sur {resultat1}, fais Y")

        return {"resultat_final": resultat2}
```

**Principes:**
- Un workflow = un processus métier
- Les étapes s'exécutent dans un ordre déterministe
- Chaque étape peut utiliser les résultats des précédentes
- On peut brancher (if/else) selon les résultats

### 4. State (État) 💾

L'**état** permet de partager des données entre les étapes du workflow.

```python
class WorkflowAvecEtat(Workflow):
    def run(self, input_data):
        # Initialiser l'état
        state = {
            "dossier_id": "abc-123",
            "documents_traites": []
        }

        # Étape 1: Extraire
        extraction = self.agent_extract.run(...)
        state["extraction"] = extraction

        # Étape 2: Utiliser l'état
        verification = self.agent_verify.run(
            f"Vérifie ces données: {state['extraction']}"
        )

        return state
```

## Architecture pour Notary Assistant

### Workflow principal: Analyse de dossier

```
Input: Documents PDF du dossier
    ↓
[Agent 1: Extracteur]
    - Lit les PDFs
    - Extrait les informations clés
    - Tool: extraire_texte_pdf()
    ↓
[Agent 2: Classificateur]
    - Identifie le type de transaction
    - Classe les documents
    ↓
[Agent 3: Vérificateur]
    - Vérifie la cohérence des données
    - Identifie les informations manquantes
    - Tool: verifier_registre_foncier()
    ↓
[Agent 4: Générateur de checklist]
    - Crée la checklist pour le notaire
    - Calcule le score de confiance
    - Identifie les points d'attention
    ↓
Output: Checklist + Rapport d'analyse
```

### Agents spécialisés

**1. Agent Extracteur**
- Role: Expert en extraction de données de documents notariaux
- Tools: `extraire_texte_pdf()`, `parser_dates()`, `extraire_montants()`
- Output: Données structurées (JSON)

**2. Agent Classificateur**
- Role: Expert en droit notarial québécois
- Tools: `classifier_transaction()`, `identifier_type_document()`
- Output: Type de transaction + catégories de documents

**3. Agent Vérificateur**
- Role: Vérificateur rigoureux de conformité
- Tools: `verifier_registre_foncier()`, `calculer_droits_mutation()`
- Output: Liste de vérifications + alertes

**4. Agent Générateur**
- Role: Assistant organisationnel pour notaires
- Tools: Aucun (synthèse seulement)
- Output: Checklist formatée + recommandations

## Human-in-the-loop

Pour les décisions critiques, on peut demander une validation humaine:

```python
from agno import HumanApproval

# Dans le workflow
if score_confiance < 0.85:
    # Demander validation humaine
    approval = HumanApproval(
        message="Score de confiance faible. Vérifier manuellement?",
        options=["Continuer", "Arrêter", "Réviser"]
    )

    choix = approval.get_approval()

    if choix == "Arrêter":
        return {"status": "stopped", "reason": "validation_humaine"}
```

## Bonnes pratiques

### 1. Instructions claires
```python
# ❌ Mauvais
instructions = ["Tu es un agent"]

# ✅ Bon
instructions = [
    "Tu es un expert en vérification de titres de propriété au Québec",
    "Tu dois vérifier chaque titre avec rigueur",
    "Tu utilises le registre foncier comme source de vérité",
    "Si tu trouves un problème, tu le signales immédiatement",
    "Tu fournis toujours tes sources et références légales"
]
```

### 2. Tools focalisées
```python
# ❌ Mauvais: tool qui fait trop de choses
def tout_faire(dossier):
    # extrait, vérifie, génère le rapport...
    pass

# ✅ Bon: tools spécialisées
def extraire_texte_pdf(chemin_pdf: str) -> str:
    """Extrait uniquement le texte."""
    pass

def verifier_titre(numero_titre: str) -> dict:
    """Vérifie uniquement un titre."""
    pass
```

### 3. Gestion d'erreurs
```python
def run(self, input_data):
    try:
        resultat = self.agent.run(...)

        # Vérifier la qualité du résultat
        if not self._valider_resultat(resultat):
            return {"error": "Résultat invalide", "retry": True}

        return {"success": True, "data": resultat}

    except Exception as e:
        return {"error": str(e), "success": False}
```

## Prochaines étapes

1. ✅ Comprendre les concepts de base
2. 🔄 Créer le workflow principal (`workflows/analyse_dossier.py`)
3. ⏳ Intégrer MLX pour l'inférence locale
4. ⏳ Tester avec des documents fictifs
5. ⏳ Ajouter le human-in-the-loop pour validation

## Ressources

- [Documentation Agno](https://docs.agno.com)
- [Exemples de workflows](https://github.com/agno-agi/agno/tree/main/examples)
- Code local: `backend/workflows/exemple_simple.py`
