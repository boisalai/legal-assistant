# Guide de Test End-to-End - Notary Assistant

Ce guide explique comment tester le flux complet de l'application Notary Assistant:
**Creer dossier -> Telecharger PDF -> Analyser -> Voir resultats**

---

## Prerequis

### 1. Services requis

| Service | Port | Description |
|---------|------|-------------|
| SurrealDB | 8001 | Base de donnees |
| FastAPI Backend | 8000 | API REST |
| Next.js Frontend | 3001 | Interface web |

### 2. Demarrer les services

```bash
# Terminal 1: SurrealDB
cd /home/user/notary
docker compose up -d surrealdb

# Verifier que SurrealDB est demarre
docker compose ps

# Terminal 2: Backend FastAPI
cd /home/user/notary/backend
uv run python main.py

# Verifier: http://localhost:8000/docs

# Terminal 3: Frontend Next.js
cd /home/user/notary/frontend
npm run dev

# Verifier: http://localhost:3001
```

### 3. Verifier la connexion

```bash
# Test API backend
curl http://localhost:8000/health

# Reponse attendue: {"status":"healthy"}

# Test proxy frontend -> backend
curl http://localhost:3001/api/dossiers

# Reponse attendue: [] (liste vide)
```

---

## Test End-to-End via Interface Web

### Etape 1: Acceder au Dashboard

1. Ouvrir http://localhost:3001/dashboard dans le navigateur
2. La page doit afficher "Aucun dossier" si c'est la premiere utilisation

### Etape 2: Creer un nouveau dossier

1. Cliquer sur "Nouveau dossier" (bouton en haut a droite)
2. Remplir le formulaire:
   - **Nom du dossier**: `Test Vente 123 Rue Exemple`
   - **Type de transaction**: `Vente`
3. Telecharger un fichier PDF:
   - Glisser-deposer un PDF dans la zone de televersement
   - OU cliquer sur "Parcourir" pour selectionner un fichier
4. Cliquer sur "Creer et analyser"

### Etape 3: Suivre la progression

1. Vous etes automatiquement redirige vers la page de detail du dossier
2. Observez la progression de l'analyse:
   - Etape 1/4: Extraction des donnees
   - Etape 2/4: Classification de la transaction
   - Etape 3/4: Verification de coherence
   - Etape 4/4: Generation liste de verification

### Etape 4: Voir les resultats

Une fois l'analyse terminee:
1. **Score de confiance**: Barre de progression avec pourcentage
2. **Points d'attention**: Alertes importantes (encadre orange)
3. **Documents manquants**: Liste des documents requis (encadre rouge)
4. **Liste de verification**: Items interactifs avec checkboxes
   - Cochez les items au fur et a mesure de leur verification
   - Les priorites sont affichees avec des badges colores:
     - Rouge: Critique/Haute
     - Orange: Moyenne
     - Gris: Basse

### Etape 5: Retourner au Dashboard

1. Cliquer sur "Retour" dans l'en-tete
2. Le dossier apparait dans la liste avec son statut "Complete"
3. Cliquez sur le dossier pour revoir les details

---

## Test End-to-End via API (curl)

### 1. Creer un dossier

```bash
curl -X POST http://localhost:8000/api/dossiers \
  -H "Content-Type: application/json" \
  -d '{
    "nom_dossier": "Test API Vente",
    "type_transaction": "vente",
    "user_id": "user:test_notaire"
  }'
```

Reponse attendue:
```json
{
  "id": "dossier:abc123...",
  "nom_dossier": "Test API Vente",
  "type_transaction": "vente",
  "statut": "nouveau",
  "created_at": "2025-11-22T..."
}
```

Sauvegarder l'ID retourne pour les etapes suivantes.

### 2. Telecharger un document PDF

```bash
# Remplacer DOSSIER_ID par l'ID du dossier cree
DOSSIER_ID="dossier:abc123..."

curl -X POST "http://localhost:8000/api/dossiers/${DOSSIER_ID}/upload" \
  -F "file=@/chemin/vers/document.pdf"
```

Reponse attendue:
```json
{
  "id": "document:xyz789...",
  "dossier_id": "dossier:abc123...",
  "nom_fichier": "document.pdf",
  "type_fichier": "PDF"
}
```

### 3. Lancer l'analyse

```bash
curl -X POST "http://localhost:8000/api/dossiers/${DOSSIER_ID}/analyser-stream" \
  -H "Content-Type: application/json"
```

Reponse attendue (HTTP 202):
```json
{
  "message": "Analysis started",
  "dossier_id": "dossier:abc123...",
  "stream_url": "/api/dossiers/dossier:abc123.../analyse-stream",
  "checklist_url": "/api/dossiers/dossier:abc123.../checklist"
}
```

### 4. Suivre la progression (SSE)

```bash
curl -N "http://localhost:8000/api/dossiers/${DOSSIER_ID}/analyse-stream"
```

Les evenements SSE arrivent au fur et a mesure:
```
data: {"event_type":"start","step":0,"step_name":"Initialisation",...}
data: {"event_type":"step_start","step":1,"step_name":"Extraction",...}
data: {"event_type":"step_end","step":1,...}
...
data: {"event_type":"complete","step":4,...}
```

### 5. Recuperer la checklist

```bash
curl "http://localhost:8000/api/dossiers/${DOSSIER_ID}/checklist"
```

Reponse attendue:
```json
{
  "id": "checklist:...",
  "dossier_id": "dossier:abc123...",
  "score_confiance": 0.75,
  "items": [
    {
      "titre": "Verifier les informations du vendeur",
      "description": "...",
      "priorite": "haute"
    },
    ...
  ],
  "documents_manquants": ["Certificat de localisation"],
  "points_attention": ["Verifier la date de signature"]
}
```

### 6. Verifier le statut du dossier

```bash
curl "http://localhost:8000/api/dossiers/${DOSSIER_ID}"
```

Le statut doit etre "complete" ou "analyse_complete".

---

## Modeles LLM supportes

L'analyse peut utiliser differents modeles LLM:

### Ollama (local, gratuit)
```bash
# Modele recommande
curl -X POST "http://localhost:8000/api/dossiers/${DOSSIER_ID}/analyser-stream?model_id=ollama:qwen2.5:7b"

# Alternatives
?model_id=ollama:mistral
?model_id=ollama:llama3.2
```

### Claude API (cloud, payant)
```bash
curl -X POST "http://localhost:8000/api/dossiers/${DOSSIER_ID}/analyser-stream?model_id=anthropic:claude-sonnet-4-5-20250929"
```

Note: Necessite ANTHROPIC_API_KEY dans .env

---

## Depannage

### Probleme: "Connexion refusee" sur port 8000

**Cause**: Le backend n'est pas demarre.

**Solution**:
```bash
cd /home/user/notary/backend
uv run python main.py
```

### Probleme: "Connexion refusee" sur port 3001

**Cause**: Le frontend n'est pas demarre.

**Solution**:
```bash
cd /home/user/notary/frontend
npm run dev
```

### Probleme: "SurrealDB connection error"

**Cause**: SurrealDB n'est pas demarre ou mal configure.

**Solution**:
```bash
docker compose down
docker compose up -d surrealdb
docker compose logs surrealdb
```

### Probleme: L'analyse ne demarre pas

**Causes possibles**:
1. Aucun document telecharge
2. Modele LLM non disponible (Ollama non demarre)

**Solutions**:
```bash
# Verifier Ollama
ollama list
ollama pull qwen2.5:7b

# Verifier les documents
curl "http://localhost:8000/api/dossiers/${DOSSIER_ID}/documents"
```

### Probleme: Score de confiance tres bas (< 30%)

**Causes possibles**:
1. PDF de mauvaise qualite ou scanne
2. PDF non lisible (image sans OCR)

**Solutions**:
- Utiliser un PDF avec du texte extractible
- Activer l'OCR: `?use_ocr=true`
- Essayer un autre modele plus performant

---

## Checklist de validation

- [ ] Dashboard affiche correctement la liste des dossiers
- [ ] Creation de dossier fonctionne
- [ ] Upload de PDF par drag & drop fonctionne
- [ ] Upload de PDF par bouton Parcourir fonctionne
- [ ] Progression de l'analyse s'affiche en temps reel
- [ ] Score de confiance s'affiche correctement
- [ ] Points d'attention s'affichent si presents
- [ ] Documents manquants s'affichent si presents
- [ ] Liste de verification interactive fonctionne
- [ ] Suppression de dossier fonctionne
- [ ] Navigation Retour fonctionne

---

## Resultats attendus

Apres un test reussi:

1. **Dashboard**: Le dossier apparait avec statut "Complete"
2. **Page detail**:
   - Score de confiance visible (ex: 75%)
   - Liste de verification avec items interactifs
   - Points d'attention et documents manquants si pertinents
3. **Base de donnees**: Enregistrements dans SurrealDB verifiables
