# Documentation Index - Notary Assistant

> Navigation rapide vers toute la documentation du projet
> Derniere mise a jour: 2025-11-28

---

## Documents Principaux

| Document | Description |
|----------|-------------|
| [CLAUDE.md](../CLAUDE.md) | Plan de developpement et historique des sessions |
| [README.md](../README.md) | Presentation generale du projet |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Guide de contribution |
| [SECURITY.md](../SECURITY.md) | Politique de securite |

---

## Architecture et Concepts

| Document | Description |
|----------|-------------|
| [architecture.md](./architecture.md) | Architecture generale du systeme |
| [agno-concepts.md](./agno-concepts.md) | Guide complet du framework Agno |
| [agno-surrealdb-schema.md](./agno-surrealdb-schema.md) | Schema des tables Agno dans SurrealDB |
| [surrealdb-architecture.md](./surrealdb-architecture.md) | Architecture de la base de donnees SurrealDB |
| [automatisation.md](./automatisation.md) | Capacites d'automatisation Agno |

---

## Guides de Configuration

| Document | Description |
|----------|-------------|
| [ollama-setup.md](./ollama-setup.md) | Guide d'installation et configuration Ollama |
| [GUIDE_CLAUDE_API.md](../GUIDE_CLAUDE_API.md) | Configuration de l'API Claude Anthropic |
| [Backend README](../backend/README.md) | Installation et configuration du backend |
| [Frontend README](../frontend/README.md) | Installation et configuration du frontend |

---

## Tests et Validation

| Document | Description |
|----------|-------------|
| [E2E_TEST_GUIDE.md](../E2E_TEST_GUIDE.md) | Guide des tests end-to-end |
| [Tests README](../backend/tests/README.md) | Guide des tests backend (pytest) |
| [TEST_WORKFLOW.md](../backend/TEST_WORKFLOW.md) | Guide de test des workflows |
| [SPRINT1_FINAL_REPORT.md](../SPRINT1_FINAL_REPORT.md) | Rapport final Sprint 1 |
| [SPRINT1_OLLAMA_MODELS_TEST_RESULTS.md](../SPRINT1_OLLAMA_MODELS_TEST_RESULTS.md) | Resultats tests multi-modeles Ollama |

---

## Troubleshooting

| Document | Description |
|----------|-------------|
| [SURREALDB_FIX_README.md](../backend/SURREALDB_FIX_README.md) | Correction problemes SurrealDB/Agno |
| [BUGFIX_DB_PERSISTENCE.md](../backend/docs/BUGFIX_DB_PERSISTENCE.md) | Documentation bugs DB resolus |
| [MIGRATION_INSTRUCTIONS.md](../backend/MIGRATION_INSTRUCTIONS.md) | Instructions de migration des statuts |

---

## Prompts et IA

| Document | Description |
|----------|-------------|
| [PROMPTS_AMELIORES.md](../PROMPTS_AMELIORES.md) | Prompts optimises pour les agents |
| [OPTION2_PROMPTS_INTEGRATION.md](../OPTION2_PROMPTS_INTEGRATION.md) | Integration des prompts ameliores |

---

## Specifications

| Document | Description |
|----------|-------------|
| [specifications.md](../documents/specifications.md) | Specifications fonctionnelles du projet |

---

## Documents Archives (Legacy)

Ces documents sont conserves pour reference historique mais ne sont plus actifs.

| Document | Raison archivage |
|----------|------------------|
| [architecture-agents-autonomes.md](./LEGACY/architecture-agents-autonomes.md) | Approche abandonnee |
| [phase2-agents-autonomes.md](./LEGACY/phase2-agents-autonomes.md) | Sprint 2 obsolete |
| [agentos-setup-results.md](./LEGACY/agentos-setup-results.md) | Experimentation non retenue |
| [tutorial-architecture.md](./LEGACY/tutorial-architecture.md) | Patterns depasses |

Voir [LEGACY/README.md](./LEGACY/README.md) pour plus de details.

---

## Structure de la Documentation

```
notary/
├── CLAUDE.md              # Plan developpement (document principal)
├── README.md              # Presentation projet
├── CONTRIBUTING.md        # Guide contribution
├── SECURITY.md            # Politique securite
│
├── docs/
│   ├── INDEX.md           # Ce fichier (navigation)
│   ├── architecture.md    # Architecture systeme
│   ├── agno-concepts.md   # Guide Agno
│   ├── agno-surrealdb-schema.md  # Schema DB Agno
│   ├── surrealdb-architecture.md # Architecture DB
│   ├── ollama-setup.md    # Guide Ollama
│   ├── automatisation.md  # Automatisation
│   └── LEGACY/            # Documents archives
│
├── backend/
│   ├── README.md          # Guide backend
│   ├── SURREALDB_FIX_README.md  # Troubleshooting DB
│   ├── MIGRATION_INSTRUCTIONS.md
│   ├── TEST_WORKFLOW.md
│   ├── docs/
│   │   └── BUGFIX_DB_PERSISTENCE.md
│   └── tests/
│       └── README.md
│
├── frontend/
│   └── README.md          # Guide frontend
│
├── documents/
│   └── specifications.md  # Specs fonctionnelles
│
└── Reports/
    ├── SPRINT1_FINAL_REPORT.md
    ├── SPRINT1_OLLAMA_MODELS_TEST_RESULTS.md
    ├── GUIDE_CLAUDE_API.md
    ├── E2E_TEST_GUIDE.md
    ├── PROMPTS_AMELIORES.md
    └── OPTION2_PROMPTS_INTEGRATION.md
```

---

## Liens Rapides

### Demarrage Rapide
1. [Installation Backend](../backend/README.md#installation)
2. [Installation Frontend](../frontend/README.md)
3. [Configuration Ollama](./ollama-setup.md)

### Developpement
1. [Architecture](./architecture.md)
2. [Concepts Agno](./agno-concepts.md)
3. [Tests](../backend/tests/README.md)

### Troubleshooting
1. [Problemes SurrealDB](../backend/SURREALDB_FIX_README.md)
2. [Bugs DB](../backend/docs/BUGFIX_DB_PERSISTENCE.md)

---

**Maintenu par:** Claude Code
**Derniere revision:** 2025-11-28
