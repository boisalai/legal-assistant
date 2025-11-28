# Notary 🏛️

> **⚠️ PROJET CONFIDENTIEL - PROPRIÉTÉ PRIVÉE**
> 
> Ce dépôt contient du code propriétaire. L'accès est strictement limité 
> aux collaborateurs autorisés. Toute divulgation non autorisée est interdite.

## 📋 Description

Assistant IA pour l'automatisation des vérifications préliminaires dans les 
cabinets de notaires au Québec.

## 🎯 Fonctionnalités principales

### MVP (Phase 1)
- ✅ Upload sécurisé de documents PDF
- ✅ Extraction automatique d'informations
- ✅ Génération de checklist de vérification
- ✅ Interface web intuitive
- ✅ Rapports exportables

### Roadmap
- 🔲 Intégration avec logiciels notariaux existants
- 🔲 Surveillance automatique de dossiers
- 🔲 Notifications en temps réel
- 🔲 Dashboard analytique

## 🏗️ Architecture
```
Frontend (Next.js) ←→ API (FastAPI) ←→ Agno Workflows ←→ Claude AI
                                  ↓
                            PostgreSQL + S3
```

## 🚀 Installation

Voir [docs/setup.md](docs/setup.md) pour les instructions détaillées.

## 🔒 Sécurité

- Chiffrement AES-256 au repos
- OAuth2 + JWT pour l'authentification
- Conformité Loi 25 (Québec)
- Audit trail complet

## 📞 Contact

Pour toute question: $EMAIL

## 📄 Licence

Propriétaire - Copyright © 2025 $COMPANY_NAME
Voir [LICENSE](LICENSE) pour plus de détails.
