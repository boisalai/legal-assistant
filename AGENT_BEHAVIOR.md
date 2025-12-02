# Comportement de l'Agent IA

## Principe fondamental

L'agent IA fonctionne selon une **règle absolue** : **il répond UNIQUEMENT en se basant sur les documents du dossier**.

## Règles de fonctionnement

### 1. Recherche sémantique obligatoire

- **Pour TOUTE question**, l'agent utilise l'outil `semantic_search` en premier
- Que la question soit générale ("Qu'est-ce que le notariat?") ou spécifique ("Quel est le prix?"), l'agent cherche toujours dans les documents
- L'agent ne répond **JAMAIS** avec ses propres connaissances générales

### 2. Si l'information n'est pas trouvée

Quand la recherche sémantique ne trouve rien de pertinent, l'agent informe clairement :

> "Je n'ai pas trouvé d'information pertinente sur [sujet] dans les documents du dossier."

### 3. Utilisation des outils

| Outil | Quand l'utiliser |
|-------|-----------------|
| `semantic_search` | **TOUJOURS** - Pour toute question de l'utilisateur |
| `search_documents` | Seulement si l'utilisateur demande explicitement de chercher un mot/phrase exact |
| `list_documents` | Si l'utilisateur demande la liste des documents |
| `transcribe_audio` | Si l'utilisateur demande de transcrire un fichier audio |
| `extract_entities` | Pour extraire des informations structurées |

## Exemples

### Question générale

**Utilisateur** : "Qu'est-ce que le notariat?"

**Agent** :
1. Utilise `semantic_search` avec la question
2. Si trouvé dans les documents → répond avec les passages trouvés
3. Si non trouvé → "Je n'ai pas trouvé d'information pertinente sur le notariat dans les documents du dossier."

### Question spécifique

**Utilisateur** : "Quel est le prix mentionné dans le contrat?"

**Agent** :
1. Utilise `semantic_search` avec la question
2. Retourne les passages pertinents avec le prix

### Recherche exacte

**Utilisateur** : "Cherche le mot exact 'signature'"

**Agent** :
1. Utilise `search_documents` (car demande explicite de mot exact)
2. Retourne toutes les occurrences du mot "signature"

## Avantages de cette approche

1. **Fiabilité** : Les réponses sont basées sur des sources vérifiables (les documents du dossier)
2. **Traçabilité** : Chaque réponse cite ses sources avec le nom du document et le score de pertinence
3. **Polyvalence** : L'agent peut traiter n'importe quel domaine (droit, astronomie, cinéma, etc.) tant que les documents sont dans le dossier
4. **Apprentissage** : Parfait pour apprendre différents patterns d'agents et concepts d'IA (RAG, recherche sémantique, etc.)

## Configuration technique

- **Recherche sémantique** : Utilise des embeddings pour comprendre le sens des questions
- **Score minimum** : 50% de similarité (configurable dans `semantic_search_tool.py`)
- **Indexation** : Automatique lors de l'upload de documents avec du texte extrait
- **Modèle d'embeddings** : Configurable (actuellement via Ollama)

## Notes importantes

- Les documents doivent être **indexés** pour la recherche sémantique
- L'indexation se fait automatiquement lors de l'upload si le document a du texte extrait
- Pour forcer la réindexation, utilisez l'outil `index_document_tool`
- Vérifiez l'état de l'indexation avec `get_index_stats`
