# Frontend - Notary Assistant

Interface web pour le système d'analyse de dossiers notariaux.

## 🚀 Stack Technologique

- **Framework:** Next.js 15.5 (App Router)
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS 3.4
- **Components:** shadcn/ui
- **State:** React Hooks (useState, useEffect)
- **API:** Fetch API avec proxy vers backend

## 📁 Structure du Projet

```
frontend/
├── src/
│   ├── app/                    # Pages Next.js (App Router)
│   │   ├── page.tsx           # Page d'accueil
│   │   ├── dashboard/         # Dashboard liste dossiers
│   │   ├── nouveau-dossier/   # Création + upload
│   │   ├── dossiers/[id]/     # Détail d'un dossier
│   │   ├── layout.tsx         # Layout racine
│   │   └── globals.css        # Styles globaux
│   ├── components/
│   │   └── ui/                # Composants shadcn/ui
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       └── badge.tsx
│   ├── lib/
│   │   └── utils.ts           # Utilitaires (cn, etc.)
│   └── types/
│       └── index.ts           # Types TypeScript
├── public/                     # Assets statiques
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.ts
```

## 🛠️ Installation

```bash
cd frontend
npm install
```

## 🏃 Démarrage

### Mode Développement

```bash
npm run dev
```

L'application sera disponible sur [http://localhost:3000](http://localhost:3000)

### Build Production

```bash
npm run build
npm start
```

## 🔗 Configuration API

Le frontend communique avec le backend via un proxy configuré dans `next.config.ts` :

```typescript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*',
    },
  ];
}
```

**Important:** Le backend doit être lancé sur le port 8000.

## 📄 Pages

### 1. Page d'Accueil (`/`)
- Présentation du système
- Liens vers Dashboard et Nouveau Dossier

### 2. Dashboard (`/dashboard`)
- Liste de tous les dossiers
- Filtrage par statut
- Affichage du score de confiance
- Lien vers chaque dossier

### 3. Nouveau Dossier (`/nouveau-dossier`)
- Formulaire de création
- Upload de PDFs (drag & drop)
- Envoi au backend
- Déclenchement automatique de l'analyse

### 4. Détail Dossier (`/dossiers/[id]`)
- Informations complètes du dossier
- Score de confiance avec indicateur visuel
- Liste des documents uploadés
- **Checklist complète** (après analyse):
  - Points d'attention (alertes)
  - Documents manquants à obtenir
  - Items de vérification avec statut et priorité
  - Commentaires finaux

## 🎨 Composants UI

Basés sur [shadcn/ui](https://ui.shadcn.com/):

- **Button:** Variants (default, outline, ghost, destructive, etc.)
- **Card:** Container avec Header, Title, Description, Content, Footer
- **Badge:** Labels avec variants (success, warning, destructive, etc.)

### Utilisation

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

<Button variant="default">Créer</Button>
<Card>
  <CardHeader>
    <CardTitle>Titre</CardTitle>
  </CardHeader>
  <CardContent>Contenu</CardContent>
</Card>
<Badge variant="success">Complété</Badge>
```

## 🔧 Types TypeScript

Tous les types sont définis dans `src/types/index.ts`:

```typescript
interface Dossier {
  id: string;
  nom_dossier: string;
  type_transaction: "vente" | "achat" | "hypotheque" | "testament" | "autre";
  statut: "nouveau" | "en_analyse" | "analyse_complete" | "valide" | "archive";
  score_confiance?: number;
  // ...
}
```

## 🌐 API Endpoints Utilisés

- `GET /api/dossiers` - Liste des dossiers
- `POST /api/dossiers` - Créer un dossier
- `GET /api/dossiers/:id` - Détails d'un dossier
- `GET /api/dossiers/:id/documents` - Documents d'un dossier
- `GET /api/dossiers/:id/checklist` - **Checklist générée** (après analyse)
- `POST /api/dossiers/:id/upload` - Upload un document
- `POST /api/dossiers/:id/analyser` - Lancer l'analyse

## 🧪 Test Complet (Backend + Frontend)

### 1. Démarrer le Backend

```bash
cd backend
docker-compose up -d surrealdb
uv run python main.py
```

Backend sur http://localhost:8000

### 2. Démarrer le Frontend

```bash
cd frontend
npm run dev
```

Frontend sur http://localhost:3000

### 3. Tester le Workflow

1. Ouvrir http://localhost:3000
2. Cliquer "Nouveau Dossier"
3. Remplir le formulaire:
   - Nom: "Test Vente 123 Rue Example"
   - Type: "Vente"
4. Glisser-déposer des PDFs (ou cliquer pour sélectionner)
5. Cliquer "Créer et Analyser"
6. Redirection vers `/dossiers/:id`
7. Voir les documents uploadés
8. Attendre l'analyse (statut passe à "analyse_complete")
9. Voir le score de confiance

## 🎯 Prochaines Fonctionnalités

- [x] Affichage complet de la checklist ✅
- [ ] Export PDF de la checklist
- [ ] Filtrage checklist par statut/priorité
- [ ] Authentification (JWT)
- [ ] WebSocket pour statut en temps réel
- [ ] Recherche et filtres avancés dans dashboard
- [ ] Dark mode
- [ ] Notifications toast
- [ ] Tests E2E (Playwright)

## 📦 Dépendances Principales

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "next": "^15.1.3",
    "tailwindcss": "^3.4.1",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.4.0",
    "tailwindcss-animate": "^1.0.7"
  }
}
```

## 🐛 Troubleshooting

### Le frontend ne se connecte pas au backend

**Problème:** Erreur CORS ou connexion refusée

**Solutions:**
1. Vérifier que le backend tourne sur le port 8000
2. Vérifier le proxy dans `next.config.ts`
3. Vérifier les CORS dans le backend FastAPI

### Les uploads ne fonctionnent pas

**Problème:** Erreur lors de l'upload de fichiers

**Solutions:**
1. Vérifier que `MAX_UPLOAD_SIZE_MB` dans le backend est suffisant
2. Vérifier que le répertoire `data/uploads` existe et a les bonnes permissions
3. Vérifier les logs backend pour plus de détails

### La page de détail est vide

**Problème:** Données non chargées

**Solutions:**
1. Vérifier que l'ID du dossier est valide
2. Vérifier la console du navigateur pour les erreurs
3. Vérifier que le backend retourne bien les données avec `GET /api/dossiers/:id`

## 📝 Notes de Développement

### Proxy API

Le proxy Next.js redirige `/api/*` vers `http://localhost:8000/api/*`. Cela évite les problèmes CORS en développement.

### TypeScript Strict Mode

Le projet utilise TypeScript en mode strict. Tous les types doivent être définis.

### Styling

Tailwind CSS avec configuration shadcn/ui. Les couleurs utilisent des CSS variables pour supporter le dark mode (futur).

## 🤝 Contribution

1. Créer une branche feature
2. Faire vos modifications
3. Tester localement (backend + frontend)
4. Commit avec message descriptif
5. Push et créer une PR

---

**Maintenu par:** Claude Code
**Version:** 0.1.0 (MVP)
**Dernière mise à jour:** 2025-11-19
