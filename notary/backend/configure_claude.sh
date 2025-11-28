#!/bin/bash
# Script de configuration de la clé API Claude pour le workflow

set -e

echo "🔧 Configuration de Claude API pour Notary Assistant"
echo "===================================================="
echo ""

# Vérifier si .env existe
if [ ! -f .env ]; then
    echo "⚠️  Fichier .env non trouvé, création à partir de .env.example..."
    cp .env.example .env
    echo "✅ Fichier .env créé"
    echo ""
fi

# Vérifier si ANTHROPIC_API_KEY existe déjà
if grep -q "^ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
    echo "✅ ANTHROPIC_API_KEY déjà configurée dans .env"
    echo ""
    read -p "Voulez-vous la remplacer? (o/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Oo]$ ]]; then
        echo "Configuration annulée."
        exit 0
    fi
fi

# Demander la clé API
echo "📝 Entrez votre clé API Anthropic:"
echo "   (Vous pouvez l'obtenir sur: https://console.anthropic.com/settings/keys)"
echo ""
read -p "Clé API (sk-ant-...): " -r API_KEY

# Valider le format
if [[ ! $API_KEY =~ ^sk-ant- ]]; then
    echo "❌ Erreur: La clé API doit commencer par 'sk-ant-'"
    exit 1
fi

# Ajouter ou mettre à jour la clé dans .env
if grep -q "^ANTHROPIC_API_KEY=" .env; then
    # Remplacer la clé existante (compatible macOS et Linux)
    sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" .env
    rm -f .env.bak
    echo "✅ ANTHROPIC_API_KEY mise à jour dans .env"
else
    # Ajouter la clé
    echo "" >> .env
    echo "# Anthropic Claude API (ajouté automatiquement)" >> .env
    echo "ANTHROPIC_API_KEY=$API_KEY" >> .env
    echo "✅ ANTHROPIC_API_KEY ajoutée à .env"
fi

echo ""
echo "🎉 Configuration terminée!"
echo ""
echo "Prochaines étapes:"
echo "  1. Tester la connexion: uv run python test_claude_api.py"
echo "  2. Créer des PDFs de test réalistes"
echo "  3. Lancer le workflow d'analyse"
echo ""
