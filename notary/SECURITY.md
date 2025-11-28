# Politique de Sécurité

## ⚠️ Données Sensibles

Ce projet traite des informations hautement confidentielles:
- Documents notariaux
- Informations personnelles de clients
- Transactions immobilières
- Données financières

## 🔒 Règles Strictes

### INTERDIT
- ❌ Commiter des documents réels (.pdf, .docx)
- ❌ Commiter des clés API ou secrets
- ❌ Partager des accès base de données
- ❌ Tester avec de vraies données clients
- ❌ Partager le code hors du repo privé

### OBLIGATOIRE
- ✅ Utiliser .env pour TOUTE configuration
- ✅ Utiliser des données de test anonymisées
- ✅ Chiffrer les backups
- ✅ Activer 2FA sur GitHub
- ✅ Signer un NDA avant d'accéder au code

## 🚨 Signalement de Vulnérabilités

**Contact privé uniquement**: ay.boisvert@gmail.com

**NE JAMAIS** créer d'issue publique pour les failles de sécurité.

## 📋 Checklist de Sécurité

Avant chaque commit:
- [ ] Pas de secrets dans le code
- [ ] Pas de données réelles
- [ ] .env.example à jour
- [ ] Tests de sécurité passés

## 🔐 Conformité

- **Loi 25** (Québec): Protection des renseignements personnels
- **RGPD**: Si clients européens
- **Chambre des notaires du Québec**: Règles déontologiques
