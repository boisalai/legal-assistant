# Tutoriel Architecture - Notary Assistant

> Guide progressif pour comprendre l'architecture du backend de Notary Assistant, du plus simple au plus complexe.
> Chaque section inclut les chemins de fichiers précis et des scripts à exécuter pour voir le comportement en action.

Lecture du 17 novembre 2025.

## 📂 Structure du projet

Avant de commencer, voici l'organisation complète du projet:

```
/Users/alain/Workspace/GitHub/notary/
├── backend/                           ← Tout le code backend est ici
│   ├── config/
│   │   └── settings.py               ← Configuration centralisée
│   ├── models/                        ← Modèles Pydantic
│   │   ├── user.py
│   │   ├── dossier.py
│   │   ├── document.py
│   │   ├── checklist.py
│   │   └── agent_execution.py
│   ├── services/                      ← Services (DB, LLM, métier)
│   │   ├── surreal_service.py        ← Service SurrealDB
│   │   ├── llm_provider.py           ← Interface LLM abstraite
│   │   ├── mlx_provider.py           ← Provider MLX
│   │   ├── anthropic_provider.py     ← Provider Claude
│   │   ├── ollama_provider.py        ← Provider Ollama
│   │   ├── huggingface_provider.py   ← Provider HuggingFace
│   │   ├── llm_service.py            ← Service LLM unifié
│   │   └── dossier_service.py        ← Service métier dossiers
│   ├── routes/                        ← Routes API REST
│   │   └── dossiers.py               ← Endpoints /api/dossiers
│   ├── workflows/                     ← Workflows Agno
│   │   ├── analyse_dossier.py        ← Workflow principal
│   │   ├── tools.py                  ← Outils pour les agents
│   │   └── exemple_simple.py         ← Exemple pédagogique
│   ├── data/
│   │   ├── surreal/
│   │   │   └── schema.surql          ← Schéma SurrealDB
│   │   ├── surrealdb/                ← Données SurrealDB (RocksDB)
│   │   └── uploads/                  ← Fichiers uploadés
│   ├── tests/                         ← Tous les tests
│   │   ├── conftest.py               ← Config pytest
│   │   ├── test_mlx.py
│   │   ├── test_surrealdb.py
│   │   ├── test_integration.py
│   │   └── test_all_providers.py
│   ├── main.py                        ← Point d'entrée application
│   ├── init_schema.py                 ← Initialisation DB
│   ├── pyproject.toml                 ← Dépendances Python
│   ├── pytest.ini                     ← Configuration pytest
│   ├── .env                           ← Configuration locale
│   └── .env.example                   ← Template configuration
├── docs/                              ← Documentation
│   ├── tutorial-architecture.md      ← Ce fichier!
│   ├── providers.md                  ← Guide providers LLM
│   ├── agno-concepts.md              ← Concepts Agno
│   └── surrealdb-architecture.md     ← Architecture SurrealDB
└── docker-compose.yml                 ← Services Docker
```

---

## Table des matières

1. [Niveau 1: Configuration et Settings](#niveau-1-configuration-et-settings)
2. [Niveau 2: Modèles de données (Pydantic)](#niveau-2-modèles-de-données-pydantic)
3. [Niveau 3: Service de base de données (SurrealDB)](#niveau-3-service-de-base-de-données-surrealdb)
4. [Niveau 4: Providers LLM (Intelligence Artificielle)](#niveau-4-providers-llm-intelligence-artificielle)
5. [Niveau 5: Service LLM unifié](#niveau-5-service-llm-unifié)
6. [Niveau 6: Services métier](#niveau-6-services-métier)
7. [Niveau 7: Routes API REST](#niveau-7-routes-api-rest)
8. [Niveau 8: Application principale](#niveau-8-application-principale)
9. [Niveau 9: Workflows et Agents (Agno)](#niveau-9-workflows-et-agents-agno)
10. [Comment tout s'interconnecte](#comment-tout-sinterconnecte)

---

## Niveau 1: Configuration et Settings

**📁 Fichier**: `backend/config/settings.py`

### Pourquoi la configuration est importante?

Avant de construire une application, nous avons besoin de définir comment elle se comporte. Par exemple, sur quel port l'API doit-elle écouter? Quelle base de données utiliser? Quel modèle d'IA choisir? Toutes ces décisions sont regroupées dans un seul endroit: le fichier de configuration.

### Comment ça fonctionne?

Au lieu de coder en dur des valeurs dans le code (ce qui serait une mauvaise pratique), nous utilisons Pydantic Settings pour charger la configuration depuis plusieurs sources possibles:

1. **Variables d'environnement** (ce qui est dans votre terminal)
2. **Fichier `.env`** (pour le développement local - `backend/.env`)
3. **Valeurs par défaut** (définies dans `backend/config/settings.py`)

### Ce qui est configuré

Le fichier `backend/config/settings.py` configure:

**1. Configuration de l'API FastAPI**
```python
api_host: str = "0.0.0.0"  # L'API écoute sur toutes les interfaces réseau
api_port: int = 8000        # L'API écoute sur le port 8000
debug: bool = True          # Mode debug activé en développement
```

**2. Configuration de SurrealDB**
```python
surreal_url: str = "ws://localhost:8001/rpc"
surreal_namespace: str = "notary"
surreal_database: str = "notary_db"
surreal_username: str = "root"
surreal_password: str = "root"
```

**3. Configuration des LLMs**
```python
llm_provider: str = "mlx"  # Quel provider utiliser
mlx_model_path: str = "mlx-community/Phi-3-mini-4k-instruct-4bit"
anthropic_api_key: str = ""  # Clé API Claude
ollama_base_url: str = "http://localhost:11434"
```

### 📝 Explorer ce composant

```bash
# 1. Voir le fichier de configuration
cat backend/config/settings.py

# 2. Voir le template de configuration
cat backend/.env.example

# 3. Créer votre fichier .env (si pas déjà fait)
cd backend
cp .env.example .env

# 4. Modifier la configuration
nano .env  # ou vim .env, ou ouvrez dans votre éditeur

# 5. Tester la lecture de configuration
cat > test_config.py << 'EOF'
#!/usr/bin/env python3
"""Script pour tester la configuration."""

from config.settings import settings

print("=== Configuration actuelle ===")
print(f"API Host: {settings.api_host}")
print(f"API Port: {settings.api_port}")
print(f"Debug: {settings.debug}")
print(f"\nSurrealDB URL: {settings.surreal_url}")
print(f"Namespace: {settings.surreal_namespace}")
print(f"Database: {settings.surreal_database}")
print(f"\nLLM Provider: {settings.llm_provider}")
print(f"MLX Model: {settings.mlx_model_path}")
print(f"Upload Dir: {settings.upload_dir}")
EOF

chmod +x test_config.py
uv run python test_config.py
```

### 🧪 Expérimenter

```bash
# Tester avec des variables d'environnement
LLM_PROVIDER=ollama API_PORT=9000 uv run python test_config.py

# Voir la différence: la configuration change dynamiquement!
```

---

## Niveau 2: Modèles de données (Pydantic)

**📁 Répertoire**: `backend/models/`

**Fichiers**:
- `backend/models/user.py` - Modèle utilisateur (notaire, assistant)
- `backend/models/dossier.py` - Modèle dossier notarial
- `backend/models/document.py` - Modèle document PDF
- `backend/models/checklist.py` - Modèle checklist générée
- `backend/models/agent_execution.py` - Modèle exécution agent Agno

### Qu'est-ce qu'un modèle de données?

Un modèle de données est comme un contrat ou un schéma qui définit la structure exacte d'une donnée dans votre application. Les modèles Pydantic permettent de définir ces structures avec validation automatique, sérialisation (conversion en JSON), et type-safety.

### Exemple concret: Le modèle User

**📁 Fichier**: `backend/models/user.py`

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal

class UserBase(BaseModel):
    """Modèle de base pour un utilisateur."""
    email: EmailStr  # Type spécial qui valide que c'est bien un email
    nom_complet: str
    role: Literal["notaire", "assistant", "admin"] = "notaire"

class UserCreate(UserBase):
    """Modèle pour créer un utilisateur."""
    password: str  # Obligatoire à la création

class User(UserBase):
    """Modèle complet d'un utilisateur (tel qu'en DB)."""
    id: str  # Généré par SurrealDB
    date_creation: datetime
    date_modification: datetime
    actif: bool = True
```

### 📝 Explorer ce composant

```bash
# 1. Voir tous les modèles disponibles
ls -l backend/models/

# 2. Lire le modèle User complet
cat backend/models/user.py

# 3. Lire le modèle Dossier
cat backend/models/dossier.py

# 4. Tester les modèles Pydantic
cat > test_models.py << 'EOF'
#!/usr/bin/env python3
"""Script pour tester les modèles Pydantic."""

from models.user import UserBase, UserCreate, User
from models.dossier import DossierBase, DossierCreate, Dossier
from datetime import datetime

print("=== Test 1: Créer un utilisateur valide ===")
try:
    user = UserBase(
        email="john@example.com",
        nom_complet="John Doe",
        role="notaire"
    )
    print(f"✓ Utilisateur créé: {user.email}")
    print(f"  JSON: {user.model_dump_json()}")
except Exception as e:
    print(f"✗ Erreur: {e}")

print("\n=== Test 2: Email invalide (devrait échouer) ===")
try:
    user = UserBase(
        email="pas-un-email",  # Invalide!
        nom_complet="John Doe",
        role="notaire"
    )
    print(f"✓ Utilisateur créé: {user.email}")
except Exception as e:
    print(f"✓ Erreur capturée (normal): {e}")

print("\n=== Test 3: Rôle invalide (devrait échouer) ===")
try:
    user = UserBase(
        email="john@example.com",
        nom_complet="John Doe",
        role="super-admin"  # Invalide! Doit être notaire/assistant/admin
    )
    print(f"✓ Utilisateur créé")
except Exception as e:
    print(f"✓ Erreur capturée (normal): {type(e).__name__}")

print("\n=== Test 4: Créer un dossier ===")
try:
    dossier = DossierCreate(
        nom_dossier="Vente Dupont-Tremblay",
        type_transaction="vente",
        user_id="user:abc123",
        montant_transaction=450000.00
    )
    print(f"✓ Dossier créé: {dossier.nom_dossier}")
    print(f"  Type: {dossier.type_transaction}")
    print(f"  Montant: {dossier.montant_transaction}$")
except Exception as e:
    print(f"✗ Erreur: {e}")

print("\n=== Test 5: Sérialisation JSON ===")
dossier_dict = dossier.model_dump()
print(f"Dict Python: {dossier_dict}")
dossier_json = dossier.model_dump_json(indent=2)
print(f"JSON:\n{dossier_json}")
EOF

chmod +x test_models.py
cd backend && uv run python ../test_models.py
```

---

## Niveau 3: Service de base de données (SurrealDB)

**📁 Fichier**: `backend/services/surreal_service.py`
**📁 Schéma**: `backend/data/surreal/schema.surql`
**📁 Init**: `backend/init_schema.py`

### Architecture du service

Le `SurrealService` encapsule toutes les opérations de base de données. Cela permet de centraliser la logique de connexion et les requêtes.

### 🚀 Options de démarrage de SurrealDB

Vous avez **deux options** pour exécuter SurrealDB sur votre machine. Choisissez celle qui vous convient le mieux.

#### Option 1: Via Docker (recommandé pour la production)

**Avantages:**
- Configuration isolée dans un container
- Même environnement partout (dev, staging, prod)
- Facile à démarrer/arrêter
- Données persistantes dans `backend/data/surrealdb/`

**Commandes:**

```bash
# Démarrer SurrealDB
docker-compose up -d surrealdb

# Vérifier le statut
docker-compose ps

# Voir les logs
docker-compose logs -f surrealdb

# Arrêter
docker-compose stop surrealdb

# Redémarrer
docker-compose restart surrealdb

# URL d'accès: http://localhost:8001
```

**Configuration dans `.env`:**
```bash
SURREAL_URL=http://localhost:8001
SURREAL_NAMESPACE=notary
SURREAL_DATABASE=notary_db
SURREAL_USERNAME=root
SURREAL_PASSWORD=root
```

#### Option 2: Via Homebrew (pratique pour le développement)

**Avantages:**
- Pas besoin de Docker
- Démarrage plus rapide
- Commande `surreal` disponible directement
- Utile pour tests rapides et debugging

**Installation:**

```bash
# Installer SurrealDB via Homebrew
brew install surrealdb/tap/surreal

# Vérifier l'installation
surreal version
```

**Démarrage:**

```bash
# Option A: En mémoire (données volatiles - pour tests rapides)
surreal start --log trace --user root --pass root memory

# Option B: Avec fichier (données persistantes)
surreal start --log trace --user root --pass root \
  file://backend/data/surrealdb/notary.db

# Option C: Avec RocksDB (comme Docker - recommandé)
surreal start --log trace --user root --pass root \
  rocksdb://backend/data/surrealdb

# URL d'accès: http://localhost:8000 (port par défaut différent de Docker!)
```

**⚠️ Attention au port:** Homebrew utilise le port `8000` par défaut, alors que Docker utilise `8001`.

**Configuration dans `.env` pour Homebrew:**
```bash
SURREAL_URL=http://localhost:8000  # Port 8000 au lieu de 8001!
SURREAL_NAMESPACE=notary
SURREAL_DATABASE=notary_db
SURREAL_USERNAME=root
SURREAL_PASSWORD=root
```

**Script de démarrage pratique:**

Créez un fichier `backend/start_surreal.sh`:

```bash
#!/bin/bash
# Script pour démarrer SurrealDB localement via Homebrew

echo "🚀 Démarrage de SurrealDB..."
echo "📂 Données stockées dans: backend/data/surrealdb"
echo "🌐 URL: http://localhost:8000"
echo ""

surreal start \
  --log trace \
  --user root \
  --pass root \
  --bind 0.0.0.0:8000 \
  rocksdb://data/surrealdb

# Pour utiliser ce script:
# chmod +x backend/start_surreal.sh
# cd backend && ./start_surreal.sh
```

#### Quelle option choisir?

| Critère | Docker | Homebrew |
|---------|--------|----------|
| **Développement rapide** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Production** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Isolation** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Facilité debugging** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Portabilité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**Recommandation:** Utilisez **Docker** pour le développement normal et la production, et **Homebrew** pour des tests rapides ou du debugging.

### Opérations disponibles

```python
# CRUD de base
await db.create("user", data)      # Créer
await db.select("user:abc")        # Lire
await db.update("user:abc", data)  # Mettre à jour
await db.delete("user:abc")        # Supprimer

# Requêtes personnalisées
await db.query("SELECT * FROM user WHERE role = 'notaire'")
```

### 📝 Explorer ce composant

```bash
# 1. Voir le service SurrealDB
cat backend/services/surreal_service.py

# 2. Voir le schéma de base de données
cat backend/data/surreal/schema.surql

# 3. Démarrer SurrealDB (si pas déjà fait)
docker-compose up -d surrealdb

# 4. Vérifier que SurrealDB tourne
docker-compose ps

# 5. Initialiser le schéma
cd backend
uv run python init_schema.py

# 6. Tester la connexion à SurrealDB
cat > test_surreal.py << 'EOF'
#!/usr/bin/env python3
"""Script pour tester SurrealDB."""

import asyncio
from services.surreal_service import get_surreal_service

async def test_surreal():
    print("=== Test connexion SurrealDB ===")

    service = get_surreal_service()

    async with service.get_connection() as db:
        print("✓ Connexion établie")

        # Test 1: Créer un utilisateur
        print("\n=== Test 1: Créer un utilisateur ===")
        user_data = {
            "email": "test@example.com",
            "nom_complet": "Test User",
            "role": "notaire",
            "actif": True
        }

        user = await db.create("user", user_data)
        print(f"✓ Utilisateur créé: {user['id']}")
        print(f"  Email: {user['email']}")

        # Test 2: Récupérer l'utilisateur
        print("\n=== Test 2: Récupérer l'utilisateur ===")
        user_retrieved = await db.select(user["id"])
        print(f"✓ Utilisateur récupéré: {user_retrieved['nom_complet']}")

        # Test 3: Lister tous les utilisateurs
        print("\n=== Test 3: Lister tous les utilisateurs ===")
        all_users = await db.select("user")
        print(f"✓ Nombre d'utilisateurs: {len(all_users)}")
        for u in all_users:
            print(f"  - {u['nom_complet']} ({u['email']})")

        # Test 4: Requête personnalisée
        print("\n=== Test 4: Requête personnalisée ===")
        result = await db.query("SELECT * FROM user WHERE role = 'notaire'")
        notaires = result[0]["result"]
        print(f"✓ Nombre de notaires: {len(notaires)}")

        # Test 5: Nettoyer (supprimer l'utilisateur de test)
        print("\n=== Test 5: Nettoyer ===")
        await db.delete(user["id"])
        print(f"✓ Utilisateur supprimé")

    print("\n✓ Tous les tests SurrealDB passés!")

if __name__ == "__main__":
    asyncio.run(test_surreal())
EOF

chmod +x test_surreal.py
uv run python test_surreal.py
```

### 🧪 Expérimenter avec SurrealDB directement

```bash
# Se connecter au shell SurrealDB
docker exec -it surrealdb surreal sql \
  --endpoint http://localhost:8000 \
  --namespace notary \
  --database notary_db \
  --auth root:root

# Dans le shell SurrealDB:
# SELECT * FROM user;
# SELECT * FROM dossier;
# INFO FOR DB;
```

---

## Niveau 4: Providers LLM (Intelligence Artificielle)

**📁 Fichiers**:
- `backend/services/llm_provider.py` - Interface abstraite
- `backend/services/mlx_provider.py` - Provider MLX (Apple Silicon)
- `backend/services/anthropic_provider.py` - Provider Claude API
- `backend/services/ollama_provider.py` - Provider Ollama
- `backend/services/huggingface_provider.py` - Provider HuggingFace

### Les 4 providers disponibles

| Provider | Fichier | Plateforme | Installation |
|----------|---------|------------|--------------|
| **MLX** | `mlx_provider.py` | Apple Silicon | `uv sync --extra mlx` |
| **Anthropic** | `anthropic_provider.py` | Cloud API | `uv sync --extra anthropic` |
| **Ollama** | `ollama_provider.py` | Cross-platform | `uv sync --extra ollama` |
| **HuggingFace** | `huggingface_provider.py` | Cross-platform | `uv sync --extra hf` |

### 📝 Explorer ce composant

```bash
# 1. Voir l'interface abstraite
cat backend/services/llm_provider.py

# 2. Voir un provider concret (MLX)
cat backend/services/mlx_provider.py

# 3. Comparer avec un autre provider (Ollama)
cat backend/services/ollama_provider.py

# 4. Tester MLX Provider
cat > test_mlx_provider.py << 'EOF'
#!/usr/bin/env python3
"""Script pour tester le MLX Provider."""

from services.mlx_provider import MLXProvider
from services.llm_provider import LLMMessage

print("=== Test MLX Provider ===")

# Créer le provider
provider = MLXProvider(
    model_name="mlx-community/Phi-3-mini-4k-instruct-4bit"
)

# Vérifier disponibilité
print(f"\n1. MLX disponible: {provider.is_available()}")

# Informations sur le provider
info = provider.get_info()
print(f"\n2. Informations:")
print(f"   - Nom: {info['name']}")
print(f"   - Modèle: {info['model']}")
print(f"   - Plateforme: {info['platform']}")

if provider.is_available():
    # Tester la génération
    print(f"\n3. Test de génération...")

    messages = [
        LLMMessage(role="system", content="Tu es un assistant juridique."),
        LLMMessage(role="user", content="Qu'est-ce qu'un notaire? Réponds en 2 phrases.")
    ]

    response = provider.generate(messages, max_tokens=100, temperature=0.7)

    print(f"\n   Réponse: {response.content}")
    print(f"   Modèle: {response.model}")
    if response.tokens_used:
        print(f"   Tokens: {response.tokens_used}")
else:
    print("\n⚠️  MLX n'est pas disponible sur ce système")
    print("   (nécessite macOS avec Apple Silicon)")
EOF

chmod +x test_mlx_provider.py
cd backend && uv run python ../test_mlx_provider.py
```

### 🧪 Tester tous les providers

```bash
# Script de test complet (déjà créé)
cd backend
uv run python tests/test_all_providers.py

# Tester un provider spécifique
uv run python tests/test_all_providers.py --provider mlx
uv run python tests/test_all_providers.py --provider ollama

# Pour Ollama: d'abord l'installer et le démarrer
brew install ollama  # ou télécharger depuis ollama.ai
ollama serve  # dans un autre terminal
ollama pull mistral  # télécharger un modèle
uv run python tests/test_all_providers.py --provider ollama
```

---

## Niveau 5: Service LLM unifié

**📁 Fichier**: `backend/services/llm_service.py`

### Pourquoi un service unifié?

Le `LLMService` choisit automatiquement le bon provider selon la configuration (`LLM_PROVIDER` dans `.env`), et fournit une interface simple pour générer du texte.

### Méthodes disponibles

```python
from services.llm_service import get_llm_service

llm = get_llm_service()

# Méthode simple
text = llm.generate(
    prompt="Qu'est-ce qu'un testament?",
    system_prompt="Tu es un notaire.",
    max_tokens=200
)

# Méthode avec conversation
from services.llm_provider import LLMMessage

messages = [
    LLMMessage(role="system", content="Tu es un notaire."),
    LLMMessage(role="user", content="Question...")
]
response = llm.generate_with_messages(messages)
```

### 📝 Explorer ce composant

```bash
# 1. Voir le service LLM
cat backend/services/llm_service.py

# 2. Tester le service
cat > test_llm_service.py << 'EOF'
#!/usr/bin/env python3
"""Script pour tester le LLM Service."""

from services.llm_service import get_llm_service
from config.settings import settings

print(f"=== Test LLM Service ===")
print(f"Provider configuré: {settings.llm_provider}")

# Obtenir le service
llm = get_llm_service()

# Vérifier qu'il est prêt
print(f"\nService prêt: {llm.is_ready()}")

# Informations sur le provider
info = llm.get_provider_info()
print(f"\nProvider: {info.get('name')}")
print(f"Modèle: {info.get('model')}")

if llm.is_ready():
    # Test de génération simple
    print(f"\n=== Test de génération ===")

    response = llm.generate(
        prompt="Explique ce qu'est un acte notarié en 2 phrases.",
        system_prompt="Tu es un expert en droit notarial québécois.",
        max_tokens=150,
        temperature=0.5
    )

    print(f"\nRéponse:\n{response}")
else:
    print(f"\n⚠️  Service LLM non disponible")
    print(f"Vérifiez la configuration dans .env")
EOF

chmod +x test_llm_service.py
cd backend && uv run python ../test_llm_service.py

# Tester avec un autre provider
LLM_PROVIDER=ollama uv run python ../test_llm_service.py
```

---

## Niveau 6: Services métier

**📁 Fichier**: `backend/services/dossier_service.py`

### Qu'est-ce qu'un service métier?

Le `DossierService` contient toute la logique d'application pour gérer les dossiers notariaux. Il orchestre les différents composants (DB, LLM, storage).

### Opérations disponibles

```python
from services.dossier_service import DossierService

# Créer le service
service = DossierService(surreal_service)

# CRUD Dossiers
dossier = await service.create_dossier(dossier_create)
dossier = await service.get_dossier(dossier_id)
dossiers = await service.list_dossiers(user_id, statut="en_cours")
await service.update_dossier(dossier_id, {"statut": "termine"})
await service.delete_dossier(dossier_id)

# Gestion documents
doc = await service.add_document(dossier_id, file, "contrat")
docs = await service.list_documents(dossier_id)

# Analyse
resultat = await service.analyser_dossier(dossier_id)
```

### 📝 Explorer ce composant

```bash
# 1. Voir le service complet
cat backend/services/dossier_service.py

# 2. Compter les lignes de code
wc -l backend/services/dossier_service.py

# 3. Voir la structure (seulement les définitions de fonctions)
grep -n "async def" backend/services/dossier_service.py

# 4. Tester le service (via le script d'intégration)
cd backend
uv run python tests/test_integration.py
```

---

## Niveau 7: Routes API REST

**📁 Fichier**: `backend/routes/dossiers.py`

### Endpoints disponibles

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| **GET** | `/api/dossiers` | Liste les dossiers |
| **POST** | `/api/dossiers` | Crée un dossier |
| **GET** | `/api/dossiers/{id}` | Récupère un dossier |
| **PUT** | `/api/dossiers/{id}` | Modifie un dossier |
| **DELETE** | `/api/dossiers/{id}` | Supprime un dossier |
| **POST** | `/api/dossiers/{id}/upload` | Upload un PDF |
| **GET** | `/api/dossiers/{id}/documents` | Liste les documents |
| **POST** | `/api/dossiers/{id}/analyser` | Lance l'analyse |

### 📝 Explorer ce composant

```bash
# 1. Voir toutes les routes
cat backend/routes/dossiers.py

# 2. Lister les endpoints (seulement les décorateurs)
grep "@router\." backend/routes/dossiers.py

# 3. Démarrer l'API (si pas déjà fait)
cd backend
uv run uvicorn main:app --reload

# 4. Tester l'API avec curl
# (dans un autre terminal)

# Endpoint racine
curl http://localhost:8000/

# Endpoint de santé
curl http://localhost:8000/health

# Documentation Swagger (ouvrir dans navigateur)
open http://localhost:8000/docs

# Créer un dossier
curl -X POST http://localhost:8000/api/dossiers \
  -H 'Content-Type: application/json' \
  -d '{
    "nom_dossier": "Test Dossier",
    "type_transaction": "vente",
    "user_id": "user:test",
    "montant_transaction": 250000
  }'

# Lister les dossiers
curl "http://localhost:8000/api/dossiers?user_id=user:test"

# 5. Utiliser le script de test API complet
chmod +x backend/test_api_complete.sh
./backend/test_api_complete.sh
```

### 🧪 Explorer l'API interactivement

```bash
# Installer httpie (plus convivial que curl)
brew install httpie  # ou: pip install httpie

# Créer un dossier avec httpie
http POST http://localhost:8000/api/dossiers \
  nom_dossier="Vente Dupont" \
  type_transaction="vente" \
  user_id="user:john" \
  montant_transaction:=350000

# Lister les dossiers
http GET http://localhost:8000/api/dossiers user_id==user:john

# Upload un fichier (créer d'abord un PDF de test)
echo "Test PDF" > test.pdf
http -f POST http://localhost:8000/api/dossiers/dossier:xyz/upload \
  file@test.pdf \
  type_document="contrat"
```

---

## Niveau 8: Application principale

**📁 Fichier**: `backend/main.py`

### Structure de main.py

Le point d'entrée de l'application qui:
1. Configure FastAPI
2. Enregistre les routes
3. Configure les middlewares (CORS)
4. Gère le cycle de vie (startup/shutdown)

### 📝 Explorer ce composant

```bash
# 1. Voir le fichier principal
cat backend/main.py

# 2. Compter les routes enregistrées
grep "include_router" backend/main.py

# 3. Démarrer l'application en mode debug
cd backend
DEBUG=true uv run python main.py

# 4. Démarrer avec uvicorn directement
uv run uvicorn main:app --reload --log-level debug

# 5. Tester les endpoints de base
curl http://localhost:8000/
curl http://localhost:8000/health

# 6. Voir les logs en temps réel
tail -f backend/logs/app.log  # si logging vers fichier activé

# 7. Voir toutes les routes disponibles
cat > list_routes.py << 'EOF'
#!/usr/bin/env python3
"""Liste toutes les routes de l'API."""

from main import app

print("=== Routes disponibles ===\n")

for route in app.routes:
    if hasattr(route, "methods"):
        methods = ", ".join(route.methods)
        print(f"{methods:20} {route.path}")

print(f"\nTotal: {len([r for r in app.routes if hasattr(r, 'methods')])} routes")
EOF

chmod +x list_routes.py
cd backend && uv run python ../list_routes.py
```

---

## Niveau 9: Workflows et Agents (Agno)

**📁 Fichiers**:
- `backend/workflows/analyse_dossier.py` - Workflow principal
- `backend/workflows/tools.py` - Outils pour les agents
- `backend/workflows/exemple_simple.py` - Exemple pédagogique

### Architecture multi-agents

```
Document PDF
    ↓
Agent Extracteur (extraire texte)
    ↓
Agent Classificateur (type de transaction)
    ↓
Agent Vérificateur (cohérence)
    ↓
Agent Générateur (checklist)
    ↓
Checklist pour notaire
```

### 📝 Explorer ce composant

```bash
# 1. Voir le workflow principal
cat backend/workflows/analyse_dossier.py

# 2. Voir les outils disponibles
cat backend/workflows/tools.py

# 3. Voir l'exemple simple (bon point de départ)
cat backend/workflows/exemple_simple.py

# 4. Tester l'exemple simple
cat > test_workflow_simple.py << 'EOF'
#!/usr/bin/env python3
"""Test du workflow simple."""

import asyncio
from workflows.exemple_simple import exemple_simple

async def main():
    print("=== Test Workflow Simple ===\n")

    result = await exemple_simple()

    print(f"Résultat: {result}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x test_workflow_simple.py
cd backend && uv run python ../test_workflow_simple.py

# 5. Tester un outil individuellement
cat > test_tool.py << 'EOF'
#!/usr/bin/env python3
"""Test d'un outil Agno."""

from workflows.tools import extraire_montants, extraire_dates, extraire_noms

texte_test = """
Vente immobilière entre M. Jean Dupont et Mme Marie Tremblay.
Prix de vente: 450,000.00 $
Date de signature: 15 décembre 2024
Acompte: 45,000 $
"""

print("=== Test des outils d'extraction ===\n")

# Test extraire_montants
print("1. Montants extraits:")
montants = extraire_montants(texte_test)
for montant in montants:
    print(f"   - {montant:,.2f} $")

# Test extraire_dates
print("\n2. Dates extraites:")
dates = extraire_dates(texte_test)
for date in dates:
    print(f"   - {date}")

# Test extraire_noms
print("\n3. Noms extraits:")
noms = extraire_noms(texte_test)
for nom in noms:
    print(f"   - {nom}")
EOF

chmod +x test_tool.py
cd backend && uv run python ../test_tool.py
```

---

## Comment tout s'interconnecte

### Flow complet d'une requête

Suivons une requête du début à la fin avec les chemins de fichiers précis:

```
1. Frontend → HTTP POST /api/dossiers/123/analyser

2. main.py (ligne ~50)
   ↓ Route la requête

3. routes/dossiers.py (ligne ~200, fonction analyser_dossier)
   ↓ Valide les paramètres
   ↓ Injecte les dépendances

4. services/dossier_service.py (ligne ~350, méthode analyser_dossier)
   ↓ Récupère le dossier depuis SurrealDB
   ↓ Récupère les documents

5. workflows/analyse_dossier.py (fonction workflow_analyse_dossier)
   ↓ Agent Extracteur lit les PDFs
   ↓   → workflows/tools.py (extraire_texte_pdf)
   ↓   → services/llm_service.py (génération)
   ↓   → services/mlx_provider.py (ou autre provider)
   ↓
   ↓ Agent Classificateur analyse
   ↓   → workflows/tools.py (extraire_montants, extraire_dates)
   ↓   → services/llm_service.py
   ↓
   ↓ Agent Vérificateur valide
   ↓   → workflows/tools.py (verifier_registre_foncier)
   ↓   → services/llm_service.py
   ↓
   ↓ Agent Générateur crée checklist
   ↓   → services/llm_service.py

6. services/dossier_service.py
   ↓ Sauvegarde les résultats dans SurrealDB
   ↓   → services/surreal_service.py (create)

7. routes/dossiers.py
   ↓ Convertit en JSON (via models/checklist.py)
   ↓ Retourne HTTP 200

8. Frontend reçoit la checklist
```

### 🧪 Tracer une requête complète

```bash
# Script pour tracer tout le flow
cat > trace_request.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Trace d'une requête complète ==="
echo

# 1. Démarrer SurrealDB
echo "1. Démarrage SurrealDB..."
docker-compose up -d surrealdb
sleep 2

# 2. Initialiser le schéma
echo "2. Initialisation du schéma..."
cd backend
uv run python init_schema.py

# 3. Démarrer l'API en arrière-plan
echo "3. Démarrage de l'API..."
uv run uvicorn main:app --reload &
API_PID=$!
sleep 3

# 4. Créer un utilisateur
echo "4. Création d'un utilisateur..."
USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/dossiers \
  -H 'Content-Type: application/json' \
  -d '{
    "nom_dossier": "Trace Test",
    "type_transaction": "vente",
    "user_id": "user:trace",
    "montant_transaction": 100000
  }')
echo "   Réponse: $USER_RESPONSE"

DOSSIER_ID=$(echo $USER_RESPONSE | jq -r '.id')
echo "   Dossier ID: $DOSSIER_ID"

# 5. Upload un document
echo "5. Upload d'un document de test..."
echo "Test PDF content" > test.pdf
curl -s -X POST "http://localhost:8000/api/dossiers/${DOSSIER_ID}/upload" \
  -F "file=@test.pdf" \
  -F "type_document=contrat"
echo "   ✓ Document uploadé"

# 6. Lancer l'analyse
echo "6. Lancement de l'analyse (workflow Agno)..."
ANALYSE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/dossiers/${DOSSIER_ID}/analyser")
echo "   Réponse: $ANALYSE_RESPONSE"

# 7. Récupérer la checklist
echo "7. Récupération de la checklist..."
# TODO: endpoint pour récupérer la checklist

# Nettoyer
echo
echo "8. Nettoyage..."
kill $API_PID 2>/dev/null || true
rm -f test.pdf

echo
echo "✓ Trace complète terminée!"
EOF

chmod +x trace_request.sh
./trace_request.sh
```

---

## Scripts pratiques à exécuter

### 🎯 Script complet de démonstration

```bash
cat > demo_complete.sh << 'EOF'
#!/bin/bash
set -e

echo "╔════════════════════════════════════════╗"
echo "║   DÉMONSTRATION NOTARY ASSISTANT       ║"
echo "╚════════════════════════════════════════╝"
echo

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

section() {
    echo
    echo -e "${BLUE}═══ $1 ═══${NC}"
    echo
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

section "1. VÉRIFICATION DE L'ENVIRONNEMENT"
echo "Structure du projet:"
ls -la backend/ | grep -E "^d" | awk '{print "  " $9}'
success "Structure validée"

section "2. CONFIGURATION"
echo "Configuration actuelle:"
cd backend
uv run python -c "from config.settings import settings; print(f'  API: {settings.api_host}:{settings.api_port}'); print(f'  LLM: {settings.llm_provider}'); print(f'  DB: {settings.surreal_url}')"
success "Configuration chargée"

section "3. BASE DE DONNÉES"
echo "Démarrage SurrealDB..."
docker-compose up -d surrealdb >/dev/null 2>&1
sleep 2
success "SurrealDB démarré"

echo "Initialisation du schéma..."
uv run python init_schema.py >/dev/null 2>&1
success "Schéma initialisé"

section "4. MODÈLES PYDANTIC"
echo "Test de validation Pydantic..."
uv run python -c "
from models.dossier import DossierCreate
d = DossierCreate(nom_dossier='Demo', type_transaction='vente', user_id='user:demo')
print(f'  Dossier: {d.nom_dossier}')
print(f'  Type: {d.type_transaction}')
"
success "Modèles Pydantic fonctionnels"

section "5. PROVIDERS LLM"
echo "Providers disponibles:"
for provider in mlx anthropic ollama huggingface; do
    uv run python -c "
from services.${provider}_provider import ${provider^}Provider
p = ${provider^}Provider()
available = '✓' if p.is_available() else '✗'
print(f'  {available} ${provider}: {p.get_info()[\"model\"]}')
" 2>/dev/null || echo "  ✗ ${provider}: non installé"
done

section "6. API FASTAPI"
echo "Démarrage de l'API..."
uv run uvicorn main:app --reload >/dev/null 2>&1 &
API_PID=$!
sleep 3
success "API démarrée (PID: $API_PID)"

echo "Test de l'API:"
curl -s http://localhost:8000/ | jq -r '.message'
curl -s http://localhost:8000/health | jq -r '.status'
success "API opérationnelle"

section "7. TESTS"
echo "Lancement des tests..."
uv run pytest tests/ -v --tb=short 2>&1 | tail -5
success "Tests exécutés"

section "8. NETTOYAGE"
kill $API_PID 2>/dev/null || true
success "API arrêtée"

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   DÉMONSTRATION TERMINÉE! ✓            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
EOF

chmod +x demo_complete.sh
./demo_complete.sh
```

### 📊 Script d'inspection du système

```bash
cat > inspect_system.sh << 'EOF'
#!/bin/bash

echo "╔════════════════════════════════════════╗"
echo "║   INSPECTION DU SYSTÈME                ║"
echo "╚════════════════════════════════════════╝"
echo

echo "📁 STRUCTURE DES FICHIERS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
tree -L 2 -I '__pycache__|.venv|node_modules' backend/

echo
echo "📊 STATISTIQUES DE CODE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Services:"
wc -l backend/services/*.py | tail -1
echo "Models:"
wc -l backend/models/*.py | tail -1
echo "Routes:"
wc -l backend/routes/*.py | tail -1
echo "Workflows:"
wc -l backend/workflows/*.py | tail -1
echo "Tests:"
wc -l backend/tests/test_*.py | tail -1

echo
echo "🔧 DÉPENDANCES INSTALLÉES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
cd backend
uv pip list | grep -E "(fastapi|pydantic|surrealdb|mlx|anthropic|pytest)"

echo
echo "🐳 SERVICES DOCKER"
echo "━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose ps

echo
echo "📝 FICHIERS DE CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lh backend/.env* backend/pyproject.toml backend/pytest.ini 2>/dev/null

echo
echo "✅ Inspection terminée"
EOF

chmod +x inspect_system.sh
./inspect_system.sh
```

---

## Conclusion

Vous avez maintenant:

1. ✅ **Les chemins complets** de tous les fichiers importants
2. ✅ **Des scripts pratiques** pour explorer chaque composant
3. ✅ **Une compréhension progressive** de l'architecture
4. ✅ **Des exemples exécutables** pour voir le système en action

### Prochaines étapes recommandées

1. **Exécutez les scripts** dans l'ordre du tutoriel
2. **Modifiez des petites choses** et observez les résultats
3. **Lisez le code** des fichiers mentionnés
4. **Posez des questions** sur les parties qui restent floues

### Ressources

- **Documentation Agno**: `docs/agno-concepts.md`
- **Guide Providers**: `docs/providers.md`
- **Architecture SurrealDB**: `docs/surrealdb-architecture.md`
- **Tests**: `backend/tests/README.md`

---

**Maintenu par**: Claude Code
**Dernière mise à jour**: 2025-11-17
**Version**: 2.0 (avec chemins complets et scripts)
