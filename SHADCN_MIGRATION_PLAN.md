# Plan de migration shadcn/ui vers versions officielles

**Objectif** : Mettre à jour tous les composants shadcn/ui vers leurs versions officielles les plus récentes sans aucune modification personnalisée.

**Date de création** : 2025-12-07
**Statut** : ⏳ En attente d'exécution

---

## 📊 État actuel

**Total composants UI** : 31 fichiers dans `frontend/src/components/ui/`

### Catégories

| Catégorie | Nombre | Status |
|-----------|---------|--------|
| Composants shadcn/ui officiels | 24 | ⚠️ À mettre à jour |
| Composants personnalisés métier | 4 | ✅ À conserver |
| Utilitaires/Extensions | 3 | ✅ À conserver |

---

## 🎯 Composants à migrer (24)

### 1. Composants de base (9)

Ces composants sont des wrappers simples d'éléments HTML natifs :

```bash
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add textarea
npx shadcn@latest add label
npx shadcn@latest add card
npx shadcn@latest add badge
npx shadcn@latest add skeleton
npx shadcn@latest add alert
npx shadcn@latest add table
```

**Impact attendu** : Faible
**Risque** : Minimal - Ce sont des wrappers simples

---

### 2. Composants Radix UI (12)

Ces composants utilisent @radix-ui primitives :

```bash
npx shadcn@latest add dialog
npx shadcn@latest add alert-dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add select
npx shadcn@latest add checkbox
npx shadcn@latest add switch
npx shadcn@latest add slider
npx shadcn@latest add progress
npx shadcn@latest add tabs
npx shadcn@latest add tooltip
npx shadcn@latest add avatar
npx shadcn@latest add separator
```

**Impact attendu** : Moyen
**Risque** : Moyen - Possible changement d'API ou de classes CSS

---

### 3. Composants de layout (3)

```bash
npx shadcn@latest add collapsible
npx shadcn@latest add sheet
npx shadcn@latest add scroll-area
```

**Impact attendu** : Moyen
**Risque** : Moyen - Utilisés dans des layouts critiques

---

## ✅ Composants à conserver (7)

### Composants personnalisés métier (4)

**NE PAS TOUCHER** - Ces composants sont spécifiques au domaine juridique :

- `audio-recorder.tsx` - Interface d'enregistrement audio avec Web Audio API
- `file-upload.tsx` - Upload drag-and-drop avec react-dropzone
- `language-selector.tsx` - Sélecteur i18n avec next-intl
- `markdown.tsx` - Rendu Markdown avec react-markdown et remark-gfm

### Utilitaires et extensions (3)

**NE PAS TOUCHER** - Composants utilitaires :

- `sidebar.tsx` - Système de layout complexe (shadcn/ui officiel v2)
- `sonner.tsx` - Wrapper pour notifications Toast
- `use-mobile.tsx` - Hook personnalisé de détection mobile

---

## 🚨 Points d'attention critiques

### 1. Dialog - Texte en français

**Fichier actuel** : `frontend/src/components/ui/dialog.tsx`

**Modification actuelle** :
```typescript
<DialogPrimitive.Close className="...">
  <X className="h-4 w-4" />
  <span className="sr-only">Fermer</span>  // ← Français au lieu de "Close"
</DialogPrimitive.Close>
```

**Solution après migration** :
- Laisser le composant en anglais (version officielle)
- Gérer la traduction via `next-intl` dans les composants parents
- **OU** Accepter que le texte `sr-only` (screen reader) soit en anglais

**Recommandation** : Accepter l'anglais pour `sr-only` - ce n'est jamais visible à l'écran.

---

### 2. Card - Nouvelles fonctionnalités

**Version actuelle (v0.x)** : 6 sous-composants
```typescript
Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
```

**Version officielle (v1.x)** : 7 sous-composants + nouvelles features
```typescript
Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent, CardFooter
```

**Nouveautés** :
- `CardAction` - Nouveau composant pour actions dans le header
- `data-slot` attributes - Pour styling avancé
- Container queries - `@container/card-header`
- Grid layout - Layout plus sophistiqué

**Impact** :
- Changement de structure CSS (padding, spacing)
- Possible besoin d'ajuster les cards existantes
- Nouveaux attributs `data-slot` sur tous les éléments

**Actions requises après migration** :
1. Vérifier toutes les pages utilisant `<Card>` :
   - `/cases` - Liste des dossiers
   - `/cases/[id]` - Détails d'un dossier
   - Settings pages
2. Tester l'espacement et l'alignement
3. Ajuster si nécessaire en composant les cards différemment

---

### 3. Sidebar - Composant récent

**Fichier** : `frontend/src/components/ui/sidebar.tsx` (774 lignes)

**Status** : ✅ Déjà à jour (v2, récemment ajouté)

**Action** : Aucune - Ne pas toucher

---

## 📋 Plan d'exécution par phases

### Phase 1 : Préparation (15 min)

```bash
# 1. Créer une branche de migration
git checkout -b feat/shadcn-ui-migration

# 2. Installer la dernière version de shadcn CLI
npm install -D @shadcn/ui@latest

# 3. Vérifier la configuration
cat frontend/components.json

# 4. Créer un backup des composants actuels
mkdir -p frontend/src/components/ui.backup
cp -r frontend/src/components/ui/* frontend/src/components/ui.backup/
```

---

### Phase 2 : Migration des composants de base (20 min)

**Composants** : button, input, textarea, label, card, badge, skeleton, alert, table

```bash
cd frontend

# Installation en batch
npx shadcn@latest add button input textarea label card badge skeleton alert table

# Répondre "Yes" à tous les prompts d'écrasement
```

**Tests après chaque composant** :
1. `npm run dev`
2. Naviguer vers `/cases`
3. Vérifier l'affichage des cartes
4. Vérifier les formulaires et inputs
5. Vérifier les badges de statut

**Rollback si problème** :
```bash
# Restaurer un composant
cp frontend/src/components/ui.backup/card.tsx frontend/src/components/ui/card.tsx
```

---

### Phase 3 : Migration des composants Radix (30 min)

**Composants** : dialog, alert-dialog, dropdown-menu, select, checkbox, switch, slider, progress, tabs, tooltip, avatar, separator

```bash
cd frontend

# Installation en batch
npx shadcn@latest add dialog alert-dialog dropdown-menu select checkbox switch slider progress tabs tooltip avatar separator
```

**Tests critiques** :
1. Modals et dialogs :
   - Upload de document
   - Création de dossier
   - Settings modal
2. Dropdowns :
   - Menu utilisateur
   - Actions sur documents
3. Forms :
   - Checkboxes dans les filtres
   - Switches dans settings

---

### Phase 4 : Migration des composants de layout (15 min)

**Composants** : collapsible, sheet, scroll-area

```bash
cd frontend

# Installation
npx shadcn@latest add collapsible sheet scroll-area
```

**Tests critiques** :
1. Mobile sidebar (sheet)
2. Scroll dans les listes de documents
3. Sections collapsibles

---

### Phase 5 : Tests complets (45 min)

#### 5.1 Tests manuels par page

**Pages à tester** :

| Page | Composants à vérifier | Actions |
|------|----------------------|---------|
| `/login` | Input, Button, Card | Login/logout |
| `/cases` | Card, Table, Badge, Button, Dialog | Créer, modifier, supprimer dossier |
| `/cases/[id]` | Tabs, Card, Table, Dialog, Progress | Upload doc, transcription, TTS |
| `/assistant` | Card, Textarea, Button, Separator | Chat, streaming |
| `/settings` | Card, Switch, Select, Slider | Modifier paramètres |

#### 5.2 Tests de responsive

```bash
# Tester sur différentes tailles
# Mobile: 375px, 414px
# Tablet: 768px, 1024px
# Desktop: 1280px, 1920px
```

#### 5.3 Tests thème dark/light

```bash
# Vérifier que tous les composants supportent les deux thèmes
```

---

### Phase 6 : Cleanup et documentation (15 min)

```bash
# 1. Supprimer le backup si tout fonctionne
rm -rf frontend/src/components/ui.backup

# 2. Mettre à jour package.json si nécessaire
npm update

# 3. Documenter les changements
```

**Créer** : `docs/migration/shadcn-ui-migration-2025-12-07.md`
```markdown
# Migration shadcn/ui - 2025-12-07

## Composants migrés : 24
## Composants conservés : 7
## Problèmes rencontrés : [liste]
## Solutions appliquées : [liste]
```

---

## 🔄 Procédure de rollback

En cas de problème critique pendant la migration :

```bash
# Option 1 : Rollback d'un composant spécifique
cp frontend/src/components/ui.backup/card.tsx frontend/src/components/ui/card.tsx

# Option 2 : Rollback complet
rm -rf frontend/src/components/ui
cp -r frontend/src/components/ui.backup frontend/src/components/ui
mv frontend/src/components/ui frontend/src/components/ui.old
mv frontend/src/components/ui.backup frontend/src/components/ui

# Option 3 : Git reset
git checkout -- frontend/src/components/ui/
```

---

## ✅ Checklist de validation

Avant de merger la branche `feat/shadcn-ui-migration` :

### Tests fonctionnels

- [ ] Login/Logout fonctionne
- [ ] Création de dossier fonctionne
- [ ] Upload de documents fonctionne
- [ ] Transcription audio fonctionne
- [ ] TTS fonctionne
- [ ] Chat assistant fonctionne
- [ ] Recherche sémantique fonctionne
- [ ] Settings sont sauvegardés
- [ ] Modals s'ouvrent/ferment correctement
- [ ] Dropdowns fonctionnent
- [ ] Tooltips s'affichent
- [ ] Formulaires sont utilisables

### Tests UI/UX

- [ ] Pas de régression d'espacement
- [ ] Pas de régression de couleurs
- [ ] Animations fluides
- [ ] Focus states visibles
- [ ] Dark mode fonctionne
- [ ] Light mode fonctionne
- [ ] Mobile responsive
- [ ] Tablet responsive
- [ ] Desktop responsive

### Tests accessibilité

- [ ] Navigation clavier fonctionne
- [ ] Screen reader compatible (ARIA labels)
- [ ] Contraste suffisant
- [ ] Focus trapping dans modals
- [ ] Escape ferme les modals

### Validation technique

- [ ] Aucune erreur console
- [ ] Aucun warning React
- [ ] Build production réussit : `npm run build`
- [ ] TypeScript compile : `npm run type-check`
- [ ] Linter passe : `npm run lint`
- [ ] Taille du bundle acceptable

---

## 📊 Estimations

| Phase | Durée estimée | Risque |
|-------|---------------|--------|
| Phase 1 : Préparation | 15 min | Faible |
| Phase 2 : Composants de base | 20 min | Faible |
| Phase 3 : Composants Radix | 30 min | Moyen |
| Phase 4 : Composants layout | 15 min | Moyen |
| Phase 5 : Tests complets | 45 min | - |
| Phase 6 : Cleanup | 15 min | Faible |
| **TOTAL** | **2h 20min** | - |

**Temps avec régressions** : Ajouter 30-60 min pour débugger et corriger.

---

## 🎯 Commande unique de migration

Pour exécuter toute la migration d'un coup (déconseillé) :

```bash
cd frontend

# Backup
mkdir -p src/components/ui.backup
cp -r src/components/ui/* src/components/ui.backup/

# Migration en batch
npx shadcn@latest add \
  button input textarea label card badge skeleton alert table \
  dialog alert-dialog dropdown-menu select checkbox switch slider progress tabs tooltip avatar separator \
  collapsible sheet scroll-area

# Répondre "Yes" à tous les prompts
```

**⚠️ Attention** : Cette approche est risquée. Préférer la migration phase par phase.

---

## 📝 Notes importantes

### 1. Version de shadcn/ui

Vérifier la version installée :
```bash
cat frontend/package.json | grep shadcn
```

Version actuelle du registry : https://ui.shadcn.com/docs/changelog

### 2. Dépendances

Les composants shadcn/ui dépendent de :
- `@radix-ui/*` - Primitives UI
- `class-variance-authority` - Gestion de variantes
- `clsx` - Utilitaire de classes
- `tailwind-merge` - Merge de classes Tailwind

Vérifier que ces packages sont à jour :
```bash
npm outdated
```

### 3. Tailwind CSS

Vérifier `tailwind.config.ts` :
- Tous les chemins sont corrects
- Le thème CSS est bien configuré
- Les plugins sont présents

### 4. TypeScript

Les nouveaux composants peuvent avoir des types différents.
Vérifier les erreurs TypeScript :
```bash
cd frontend
npm run type-check
```

---

## 🔗 Ressources

- Documentation shadcn/ui : https://ui.shadcn.com/docs
- Changelog shadcn/ui : https://ui.shadcn.com/docs/changelog
- Composants : https://ui.shadcn.com/docs/components
- CLI : https://ui.shadcn.com/docs/cli
- GitHub : https://github.com/shadcn-ui/ui

---

## ✅ Après migration

Une fois la migration terminée et testée :

1. **Commit** :
   ```bash
   git add .
   git commit -m "chore(ui): Migrate all shadcn/ui components to latest official versions

   - Updated 24 components to latest shadcn/ui versions
   - Kept 7 custom components (audio-recorder, file-upload, etc.)
   - Verified all features work correctly
   - No breaking changes detected

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

2. **Push et PR** :
   ```bash
   git push origin feat/shadcn-ui-migration
   # Créer une Pull Request sur GitHub
   ```

3. **Mettre à jour CLAUDE.md** :
   - Marquer la migration comme ✅ COMPLÉTÉ
   - Noter la date de migration
   - Ajouter dans l'historique des sessions

4. **Supprimer ce document** :
   ```bash
   rm SHADCN_MIGRATION_PLAN.md
   ```

---

**Créé par** : Claude Sonnet 4.5
**Date** : 2025-12-07
**Référence** : Issue #[numéro] - Migration shadcn/ui vers versions officielles
