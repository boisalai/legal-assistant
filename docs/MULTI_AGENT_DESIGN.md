# Architecture Multi-Agent pour Legal-Assistant

> **Statut** : Notes de conception (à implémenter dans une session future)
> **Date** : 2026-01-06
> **Inspiration** : [DeepTutor](https://github.com/HKUDS/DeepTutor) - Architecture multi-agent (Investigator, Planner, Solver, Validator)

---

## Contexte

### Architecture actuelle

Agent unique Agno avec outils :
- `semantic_search` - RAG sur documents indexés
- `search_caij` - Recherche jurisprudence québécoise
- `generate_summary` - Résumés structurés
- `generate_mindmap` - Cartes mentales
- `generate_quiz` - Quiz interactifs
- `explain_concept` - Explications socratiques

### Limites identifiées

1. **Pas de vérification croisée** - Risque d'hallucination sur citations juridiques
2. **Priorisation sous-optimale** - L'agent peut oublier CAIJ ou mal structurer
3. **Pas de spécialisation** - Même agent pour recherche, analyse et rédaction

---

## Architecture multi-agent proposée

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATEUR                            │
│              (comprend l'intention, délègue)                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│ CHERCHEUR │  │ ANALYSTE  │  │ RÉDACTEUR │  │ VALIDATEUR│
│           │  │ JURIDIQUE │  │           │  │           │
│ - RAG     │  │ - Doctrine│  │ - Synthèse│  │ - Sources │
│ - CAIJ    │  │ - Lois    │  │ - Vulgar. │  │ - Cohér.  │
│ - Web     │  │ - Jurisp. │  │ - Format  │  │ - Hallu.  │
└───────────┘  └───────────┘  └───────────┘  └───────────┘
```

### Rôles des agents

| Agent | Responsabilité | Outils |
|-------|----------------|--------|
| **Orchestrateur** | Comprendre l'intention, router vers les bons agents, assembler la réponse finale | Aucun (coordination pure) |
| **Chercheur** | Trouver l'information dans toutes les sources disponibles | `semantic_search`, `search_caij`, `web_search` |
| **Analyste juridique** | Interpréter les textes, identifier les articles pertinents, extraire la doctrine | `analyze_legal_text`, `extract_citations` |
| **Rédacteur** | Synthétiser, vulgariser, formater selon le contexte | `generate_summary`, `generate_quiz`, `generate_mindmap` |
| **Validateur** | Vérifier les citations, détecter les incohérences, prévenir les hallucinations | `verify_citations`, `check_consistency` |

---

## Situations types illustrées

### 1. Question de recherche juridique complexe

**Question** : *"Quels sont les recours d'un acheteur contre un vendeur pour vices cachés d'un immeuble au Québec ?"*

| Étape | Agent | Action |
|-------|-------|--------|
| 1 | **Orchestrateur** | Détecte question multi-sources, active Chercheur + Analyste |
| 2 | **Chercheur** | RAG sur documents + CAIJ "vices cachés immeuble" en parallèle |
| 3 | **Analyste** | Identifie art. 1726-1731 C.c.Q., extrait conditions et recours |
| 4 | **Rédacteur** | Structure : conditions, recours, délais, preuves |
| 5 | **Validateur** | Vérifie que chaque article cité existe, cohérence globale |

**Résultat attendu** :
```markdown
## Recours pour vices cachés (art. 1726 C.c.Q.)

### 1. Conditions d'application
- Vice antérieur à la vente
- Vice grave rendant le bien impropre à l'usage
- Vice non apparent lors de l'achat

### 2. Recours disponibles
- Diminution du prix (art. 1728 C.c.Q.)
- Résolution de la vente (vice grave)
- Dommages-intérêts si mauvaise foi du vendeur

### 3. Jurisprudence récente
- **Tremblay c. Gagnon, 2024 QCCS 1234** : [résumé]

### Sources
- Code civil du Québec, art. 1726-1731
- CAIJ : 3 décisions pertinentes
- Documents du cours : Module 4 - Vente immobilière
```

### 2. Préparation d'examen avec sources multiples

**Question** : *"Génère un quiz sur les servitudes en utilisant mes notes ET la jurisprudence récente"*

| Agent | Rôle |
|-------|------|
| **Orchestrateur** | Détecte : quiz + 2 sources (notes + CAIJ) |
| **Chercheur** | RAG sur modules "servitudes" + CAIJ "servitudes 2024" |
| **Analyste** | Extrait concepts clés : établissement, extinction, types |
| **Rédacteur** | Génère 10 questions avec références croisées |
| **Validateur** | Vérifie que chaque question cite une source valide |

**Avantage** : Questions ancrées dans la doctrine ET la jurisprudence, pas juste les notes.

### 3. Analyse d'un jugement uploadé

**Scénario** : L'utilisateur uploade un PDF de jugement et demande *"Résume ce jugement et compare avec la jurisprudence similaire"*

```
Utilisateur → Upload PDF → OCR automatique
                              ↓
                        Orchestrateur
                              ↓
              ┌───────────────┴───────────────┐
              ▼                               ▼
        Chercheur                        Analyste
     (CAIJ: cas similaires)         (Extrait: parties,
                                     faits, motifs, dispositif)
              │                               │
              └───────────────┬───────────────┘
                              ▼
                         Rédacteur
                    (Tableau comparatif)
                              ↓
                         Validateur
                    (Vérifie références)
```

**Résultat** : Analyse structurée + tableau comparatif avec 3-5 décisions similaires.

### 4. Détection d'hallucination (cas critique en droit)

**Question** : *"L'article 427 du Code civil permet-il de résilier un bail commercial ?"*

| Agent unique (actuel) | Multi-agent |
|-----------------------|-------------|
| Risque de "inventer" un contenu pour l'art. 427 | **Chercheur** : Trouve art. 427 dans les sources |
| Pas de vérification croisée | **Validateur** : Compare avec C.c.Q. officiel |
| Réponse potentiellement fausse | **Alerte** : "Art. 427 concerne les tutelles, pas les baux" |

**Le Validateur prévient les erreurs graves** qui pourraient avoir des conséquences juridiques.

---

## Bénéfices attendus

| Aspect | Impact |
|--------|--------|
| **Fiabilité** | Validateur anti-hallucination (crucial en droit) |
| **Complétude** | Chercheur explore RAG + CAIJ + web en parallèle |
| **Qualité** | Analyste spécialisé en interprétation juridique |
| **Clarté** | Rédacteur adapte au niveau (étudiant vs praticien) |
| **Traçabilité** | Chaque agent documente ses sources |

---

## Implémentation avec Agno

Agno supporte les workflows multi-agents via `Team` :

```python
from agno.agent import Agent
from agno.team import Team

# Définition des agents spécialisés
chercheur = Agent(
    name="Chercheur",
    role="Recherche d'information juridique",
    tools=[semantic_search, search_caij, web_search],
    instructions=[
        "Cherche dans toutes les sources disponibles",
        "Retourne les extraits pertinents avec références",
    ]
)

analyste = Agent(
    name="Analyste Juridique",
    role="Interprétation et analyse de textes juridiques",
    tools=[analyze_legal_text, extract_citations],
    instructions=[
        "Identifie les articles de loi applicables",
        "Extrait la doctrine et les principes juridiques",
    ]
)

redacteur = Agent(
    name="Rédacteur",
    role="Synthèse et vulgarisation",
    tools=[generate_summary, generate_quiz, generate_mindmap],
    instructions=[
        "Structure la réponse de façon claire",
        "Adapte le niveau au contexte (étudiant vs praticien)",
    ]
)

validateur = Agent(
    name="Validateur",
    role="Vérification et contrôle qualité",
    tools=[verify_citations, check_consistency],
    instructions=[
        "Vérifie que chaque citation existe",
        "Détecte les incohérences et hallucinations potentielles",
        "Alerte si une information ne peut être vérifiée",
    ]
)

# Équipe coordonnée
equipe_juridique = Team(
    name="Équipe Juridique",
    agents=[chercheur, analyste, redacteur, validateur],
    mode="coordinate",  # L'orchestrateur coordonne les agents
    # Alternatives: "route" (un seul agent), "collaborate" (tous en parallèle)
)

# Utilisation
response = equipe_juridique.run("Quels sont les recours pour vices cachés ?")
```

### Modes de coordination Agno

| Mode | Description | Cas d'usage |
|------|-------------|-------------|
| `route` | Un seul agent sélectionné | Questions simples |
| `coordinate` | Orchestrateur séquence les agents | Questions complexes |
| `collaborate` | Tous les agents en parallèle | Recherche exhaustive |

---

## Prochaines étapes

1. **Prototyper** avec 2 agents (Chercheur + Validateur) pour valider le concept
2. **Mesurer** l'amélioration de qualité vs latence/coût
3. **Itérer** en ajoutant Analyste et Rédacteur si bénéfice confirmé
4. **Optimiser** le prompt de l'Orchestrateur pour un routage efficace

---

## Références

- [DeepTutor](https://github.com/HKUDS/DeepTutor) - Architecture multi-agent de référence
- [Agno Teams Documentation](https://docs.agno.com/teams) - Documentation officielle
- [Multi-Agent Patterns](https://docs.agno.com/patterns/multi-agent) - Patterns recommandés
