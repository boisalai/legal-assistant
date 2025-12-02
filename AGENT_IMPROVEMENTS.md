# Améliorations de l'agent conversationnel

**Date:** 2025-12-01

## Résumé des changements

L'agent conversationnel juridique a été considérablement amélioré avec de nouveaux outils et une mémoire de conversation persistante.

## Nouvelles fonctionnalités

### 1. Recherche dans les documents (`search_documents`)

**Fichier:** `backend/tools/document_search_tool.py`

Permet à l'agent de rechercher des mots-clés dans tous les documents d'un dossier et de retourner les passages pertinents avec leur contexte.

**Fonctionnalités:**
- Recherche multi-mots-clés (séparés par des virgules)
- Contexte de 150 caractères avant et après chaque occurrence
- Groupement des résultats par document et par mot-clé
- Limitation du nombre de résultats pour éviter la surcharge

**Exemple d'utilisation:**
```
Utilisateur: "Cherche les mentions de signature et de date dans les documents"
Agent: *utilise search_documents(case_id="xxx", keywords="signature, date")*
```

### 2. Liste des documents (`list_documents`)

**Fichier:** `backend/tools/document_search_tool.py`

Permet à l'agent de lister tous les documents disponibles dans un dossier avec leur statut.

**Fonctionnalités:**
- Catégorisation des documents (avec contenu / audio / autres)
- Indication du nombre de mots pour les documents textuels
- Statut de transcription pour les fichiers audio
- Résumé du nombre de documents recherchables

**Exemple d'utilisation:**
```
Utilisateur: "Quels documents sont disponibles dans ce dossier?"
Agent: *utilise list_documents(case_id="xxx")*
```

### 3. Extraction d'entités juridiques (`extract_entities`)

**Fichier:** `backend/tools/entity_extraction_tool.py`

Utilise Agno avec un LLM local pour extraire automatiquement des entités structurées des documents.

**Types d'entités extraites:**
- **Personnes**: Noms de parties, témoins, avocats, etc.
- **Dates**: Dates importantes avec leur description
- **Montants**: Montants financiers avec leur contexte
- **Références légales**: Articles de loi, jurisprudence, etc.

**Fonctionnalités:**
- Extraction intelligente avec contexte pour chaque entité
- Support de types d'entités personnalisables
- Analyse d'un document spécifique ou de tous les documents
- Formatage structuré des résultats

**Exemple d'utilisation:**
```
Utilisateur: "Quelles sont les personnes mentionnées dans ce dossier?"
Agent: *utilise extract_entities(case_id="xxx", entity_types="personnes")*
```

### 4. Recherche d'entité spécifique (`find_entity`)

**Fichier:** `backend/tools/entity_extraction_tool.py`

Permet de rechercher rapidement une entité spécifique et voir tous les contextes où elle apparaît.

**Fonctionnalités:**
- Recherche insensible à la casse
- Affichage de tous les contextes (jusqu'à 10)
- Mise en évidence de l'entité dans le contexte
- Support de différents types d'entités

**Exemple d'utilisation:**
```
Utilisateur: "Où est-ce que Jean Dupont est mentionné?"
Agent: *utilise find_entity(case_id="xxx", entity_name="Jean Dupont", entity_type="personne")*
```

### 5. Mémoire de conversation persistante

**Fichier:** `backend/services/conversation_service.py`

Sauvegarde automatique de toutes les conversations dans SurrealDB.

**Fonctionnalités:**
- Sauvegarde automatique de chaque message (utilisateur et assistant)
- Stockage de métadonnées (modèle utilisé, sources, etc.)
- Récupération de l'historique par dossier
- Statistiques de conversation
- Effacement de l'historique

**Nouveaux endpoints API:**

#### GET `/api/chat/history/{case_id}`
Récupère l'historique de conversation pour un dossier.

**Paramètres:**
- `limit`: Nombre maximum de messages (défaut: 50)
- `offset`: Nombre de messages à sauter (défaut: 0)

**Réponse:**
```json
{
  "case_id": "judgment:xxx",
  "messages": [
    {
      "id": "conversation:xxx",
      "role": "user",
      "content": "Quels documents sont disponibles?",
      "timestamp": "2025-12-01T10:30:00Z"
    },
    {
      "id": "conversation:yyy",
      "role": "assistant",
      "content": "Il y a 3 documents disponibles...",
      "timestamp": "2025-12-01T10:30:05Z",
      "model_id": "ollama:qwen2.5:7b",
      "metadata": {"sources": [...]}
    }
  ],
  "count": 2
}
```

#### DELETE `/api/chat/history/{case_id}`
Efface tout l'historique de conversation pour un dossier.

**Réponse:**
```json
{
  "success": true,
  "message": "Historique effacé avec succès"
}
```

#### GET `/api/chat/stats/{case_id}`
Récupère les statistiques de conversation pour un dossier.

**Réponse:**
```json
{
  "case_id": "judgment:xxx",
  "message_count": 42,
  "first_message_time": "2025-11-28T14:20:00Z",
  "last_message_time": "2025-12-01T10:30:05Z"
}
```

## Structure de la base de données

### Nouvelle table: `conversation`

```
CREATE TABLE conversation (
    judgment_id: string,          // ID du dossier (relation vers judgment)
    role: string,                 // "user" ou "assistant"
    content: string,              // Contenu du message
    timestamp: datetime,          // Date et heure du message
    model_id: string (optional),  // Modèle utilisé (pour les réponses de l'assistant)
    metadata: object (optional)   // Métadonnées additionnelles (sources, outils utilisés, etc.)
);
```

## Intégration dans l'agent

**Fichier modifié:** `backend/routes/chat.py`

L'agent est maintenant équipé de 5 outils:
1. `transcribe_audio` (existant)
2. `search_documents` (nouveau)
3. `list_documents` (nouveau)
4. `extract_entities` (nouveau)
5. `find_entity` (nouveau)

Le prompt système a été mis à jour pour guider l'agent sur quand utiliser chaque outil:
- **transcribe_audio**: Quand l'utilisateur demande de transcrire un audio
- **search_documents**: Quand l'utilisateur cherche une information spécifique
- **list_documents**: Quand l'utilisateur demande quels documents sont disponibles
- **extract_entities**: Quand l'utilisateur veut des informations structurées
- **find_entity**: Quand l'utilisateur cherche où une entité spécifique est mentionnée

## Utilisation de Agno

Toutes les nouvelles fonctionnalités utilisent Agno pour l'interaction avec les LLMs:

- **Agent conversationnel principal**: Utilise Agno Agent avec outils
- **Extraction d'entités**: Utilise Agno Agent avec prompt structuré pour extraction JSON
- **Pas d'appel direct aux LLMs**: Tout passe par Agno

## Exemple de conversation avec les nouveaux outils

```
Utilisateur: "Quels documents sont disponibles dans ce dossier?"

Agent: [utilise list_documents]
**3 document(s) dans ce dossier:**

### Documents avec contenu recherchable:
- **transcription_audio.md** (MARKDOWN, 15.2 KB)
  📄 Transcription - 2543 mots

### Fichiers audio:
- **enregistrement_reunion.m4a** (M4A, 25.3 MB)
  ✅ Transcrit - 2543 mots

### Autres documents:
- **photo_contrat.jpg** (JPG, 3.2 MB)
  ℹ️ Contenu non extractible (image, PDF scanné, etc.)

**Résumé:** 2 document(s) avec contenu recherchable

---

Utilisateur: "Cherche les mentions de signature dans les documents"

Agent: [utilise search_documents]
J'ai trouvé **5 occurrences** du mot-clé **signature** dans **1 document**:

### transcription_audio.md
*5 occurrence(s) trouvée(s)*

**Mot-clé: signature** (5 fois)
  1. ...le contrat a été signé par les deux parties. La **signature** a eu lieu le 15 mars 2024...
  2. ...vérifier l'authenticité de la **signature** avant de procéder...
  3. ...la **signature** électronique est valide selon l'article...

---

Utilisateur: "Quelles sont les personnes mentionnées dans la transcription?"

Agent: [utilise extract_entities]
**Entités extraites du document: transcription_audio.md**

### Personnes
*3 trouvée(s)*

1. **Jean Dupont**
   *M. Jean Dupont, partie demanderesse dans cette affaire...*

2. **Marie Tremblay**
   *Mme Marie Tremblay, représentante de la partie défenderesse...*

3. **Me François Leblanc**
   *Me François Leblanc, avocat représentant la partie demanderesse...*

### Dates
*2 trouvée(s)*

1. **2024-03-15** - Date de signature du contrat
   *signé le 15 mars 2024 en présence des deux parties...*

2. **2024-06-20** - Date d'audience
   *l'audience a eu lieu le 20 juin 2024...*

**Total: 5 entités extraites**
```

## Prochaines étapes suggérées

1. **Frontend**: Créer une interface pour afficher l'historique de conversation
2. **Frontend**: Ajouter un bouton pour effacer l'historique
3. **Frontend**: Afficher les statistiques de conversation
4. **Backend**: Implémenter la recherche sémantique (RAG) pour améliorer la pertinence des réponses
5. **Backend**: Ajouter plus de types d'entités (lieux, organisations, etc.)
6. **Backend**: Créer un système de cache pour les extractions d'entités fréquentes

## Notes techniques

- Les outils d'extraction utilisent le modèle local `ollama:qwen2.5:7b` par défaut
- L'historique est sauvegardé automatiquement, aucune action requise de l'utilisateur
- Les outils sont appelés automatiquement par l'agent selon le contexte
- La recherche est insensible à la casse
- Les documents sans contenu extractible (images, PDFs scannés) ne sont pas recherchables
