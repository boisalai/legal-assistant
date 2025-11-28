"""
Workflow principal pour l'analyse de dossiers notariaux.

Ce workflow orchestre plusieurs agents pour:
1. Extraire les informations des documents PDF
2. Classifier le type de transaction
3. Vérifier la cohérence et complétude
4. Générer une checklist pour le notaire

Architecture multi-agents conforme à Agno v2.0:
- Agent Extracteur: Lit et extrait les données des PDFs
- Agent Classificateur: Identifie le type de transaction
- Agent Vérificateur: Vérifie la cohérence
- Agent Générateur: Crée la checklist finale
"""

import json
from pathlib import Path
from typing import Any, Optional
from textwrap import dedent

from agno.agent import Agent
from agno.db.surrealdb import SurrealDb
from agno.models.anthropic import Claude  # Claude API pour MVP
from agno.workflow import Workflow
from agno.utils.log import logger
from pydantic import BaseModel, Field

# Import de la configuration
from config.settings import settings

# Import des tools
from workflows.tools import (
    extraire_texte_pdf,
    extraire_texte_pdf_avance,
    extraire_montants,
    extraire_dates,
    extraire_noms,
    extraire_adresses,
)


# ========================================
# Configuration du modèle Claude
# ========================================

# Modèle Claude Sonnet 4.5 (excellent équilibre qualité/coût/vitesse)
# - Intelligence: Excellente pour extraction et analyse
# - Vitesse: ~100 tokens/sec
# - Coût: ~$3 input / $15 output par million tokens
# - Context: 200K tokens

CLAUDE_MODEL_ID = "claude-sonnet-4-5-20250929"

def get_claude_model():
    """
    Retourne une instance du modèle Claude configuré.

    Nécessite ANTHROPIC_API_KEY dans .env ou variable d'environnement.
    """
    # Passer explicitement la clé API depuis settings
    api_key = settings.anthropic_api_key
    if not api_key:
        logger.warning(
            "ANTHROPIC_API_KEY non configurée. "
            "Ajoutez ANTHROPIC_API_KEY=sk-ant-... dans backend/.env"
        )
        # Retourner quand même le modèle - Agno gérera l'erreur au moment de l'exécution
    return Claude(id=CLAUDE_MODEL_ID, api_key=api_key if api_key else None)


# ========================================
# Modèles Pydantic pour les réponses
# ========================================

class DocumentExtrait(BaseModel):
    """Données extraites d'un document"""
    nom_fichier: str
    texte: str
    montants: list[dict[str, Any]] = Field(default_factory=list)  # Les tools retournent des dicts
    dates: list[dict[str, Any]] = Field(default_factory=list)
    noms: list[dict[str, Any]] = Field(default_factory=list)
    adresses: list[dict[str, Any]] = Field(default_factory=list)


class DonneesExtraites(BaseModel):
    """Toutes les données extraites des documents"""
    documents: list[DocumentExtrait]


class Classification(BaseModel):
    """Classification de la transaction"""
    type_transaction: str = Field(
        ...,
        description="Type de transaction: vente|achat|hypotheque|testament|autre"
    )
    type_propriete: str = Field(
        ...,
        description="Type de propriété: residentielle|commerciale|terrain|copropriete"
    )
    documents_identifies: list[str] = Field(default_factory=list)
    documents_manquants: list[str] = Field(default_factory=list)


class Verification(BaseModel):
    """Résultats de vérification de cohérence"""
    coherence_dates: dict[str, Any]  # Accepte n'importe quel format
    coherence_montants: dict[str, Any]  # Accepte n'importe quel format
    completude: dict[str, Any]
    alertes: list[str] = Field(default_factory=list)
    score_verification: float


class ItemChecklist(BaseModel):
    """Un item de checklist"""
    item: str
    priorite: str  # haute|moyenne|basse
    complete: bool = False


class EtapeSuivante(BaseModel):
    """Une étape suivante recommandée"""
    etape: str
    delai: str
    responsable: str


class Checklist(BaseModel):
    """Checklist complète générée"""
    checklist: list[ItemChecklist]
    points_attention: list[str] = Field(default_factory=list)
    documents_a_obtenir: list[str] = Field(default_factory=list)
    prochaines_etapes: list[EtapeSuivante] = Field(default_factory=list)
    score_confiance: float
    commentaires: str


# ========================================
# Agents spécialisés
# ========================================
# Note: Les agents sont maintenant créés dynamiquement dans
# analyse_dossier_execution() avec le modèle spécifié dans session_state.
# Cela permet de supporter Ollama, Claude, MLX, etc.


# ========================================
# Fonctions utilitaires
# ========================================

def parser_json_safe(content: str) -> dict:
    """Parse le JSON de manière sécurisée."""
    try:
        # L'agent peut parfois retourner du markdown avec ```json
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())
    except Exception as e:
        logger.warning(f"Erreur de parsing JSON: {e}")
        return {"error": "Invalid JSON", "raw_content": content}


# ========================================
# Fonction d'exécution du workflow
# ========================================

async def analyse_dossier_execution(
    session_state: dict,
    fichiers_pdf: list[str] = None,
    metadata: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Exécute le workflow complet d'analyse de dossier notarial.

    Args:
        session_state: État de session partagé du workflow
        fichiers_pdf: Liste des chemins vers les PDFs à analyser
        metadata: Métadonnées du dossier (nom, type attendu, etc.)

    Returns:
        Dictionnaire avec:
        - success: True si succès, False si erreur
        - donnees_extraites: Données brutes extraites
        - classification: Type de transaction identifié
        - verification: Résultats de vérification
        - checklist: Checklist finale pour le notaire
        - score_confiance: Score de 0.0 à 1.0
        - requiert_validation: True si validation humaine nécessaire
    """

    # Validation des paramètres
    if not fichiers_pdf:
        return {
            "success": False,
            "erreur": "Aucun fichier PDF fourni",
        }

    if metadata is None:
        metadata = {}

    # Gérer le cas où session_state est None (Agno peut passer None)
    if session_state is None:
        session_state = {}

    # Récupérer le modèle depuis metadata (prioritaire) ou session_state
    # metadata est plus fiable car passé à chaque exécution
    model_spec = (
        metadata.get("_model")  # Modèle passé explicitement
        or session_state.get("model")  # Fallback session_state
    )

    # Convertir la spécification string en objet modèle Agno
    if model_spec and isinstance(model_spec, str):
        from services.model_factory import create_model
        model = create_model(model_spec)
        logger.info(f"Created model from spec: {model_spec}")
    elif model_spec:
        # Déjà un objet modèle
        model = model_spec
    else:
        # Défaut: utiliser Claude
        model = get_claude_model()

    # Récupérer le dossier_id pour les événements de progression
    # Note: Le callback passé via metadata ne fonctionne pas avec Agno
    # On utilise donc le ProgressManager singleton directement
    dossier_id = metadata.get("dossier_id")
    logger.info(f"Dossier ID for progress events: {dossier_id}")

    # Importer le ProgressManager pour émettre les événements directement
    from services.progress_service import get_progress_manager, ProgressEvent, ProgressEventType
    progress_manager = get_progress_manager() if dossier_id else None

    async def emit_progress(
        step: int,
        step_name: str,
        event_type: str,
        message: str,
        progress_percent: float,
        data: dict = None,
    ):
        """Émet un événement de progression via le ProgressManager singleton."""
        if progress_manager and dossier_id:
            try:
                event = ProgressEvent(
                    event_type=ProgressEventType(event_type),
                    step=step,
                    step_name=step_name,
                    message=message,
                    progress_percent=progress_percent,
                    data=data or {},
                )
                await progress_manager.emit(dossier_id, event)
                logger.info(f"Progress event emitted: {event_type} - {step_name}")
            except Exception as e:
                logger.warning(f"Failed to emit progress event: {e}")

    # Récupérer la méthode d'extraction depuis metadata ou session_state
    extraction_method = metadata.get("extraction_method", "pypdf") if metadata else "pypdf"
    use_ocr = metadata.get("use_ocr", False) if metadata else False

    logger.info(f"Extraction method: {extraction_method}, OCR: {use_ocr}")

    # Créer les agents avec le modèle spécifié
    # Cela permet de supporter Ollama, Claude, MLX, etc.
    agent_extracteur = Agent(
        name="ExtracteurDocuments",
        model=model,
        tools=[
            extraire_texte_pdf,
            extraire_texte_pdf_avance,  # Nouvelle fonction avec Docling
            extraire_montants,
            extraire_dates,
            extraire_noms,
            extraire_adresses
        ],
        description=dedent("""\
        Tu es un assistant notarial spécialisé dans l'analyse de transactions immobilières au Québec.
        """),
        instructions=dedent("""\
        CONTEXTE JURIDIQUE:
        - Droit civil québécois (Code civil du Québec)
        - Terminologie notariale française
        - Formats d'adresses québécoises (ville, province, code postal)
        - Montants en dollars canadiens ($)

        TA MISSION:
        Extraire avec PRÉCISION MAXIMALE les informations suivantes des documents fournis:

        1. PARTIES IMPLIQUÉES:
           - Vendeur(s): Nom complet, adresse, coordonnées
           - Acheteur(s): Nom complet, adresse, coordonnées
           - Courtier/Agent: Nom, agence, licence
           - Notaire instrumentant (si mentionné)

        2. IMMEUBLES:
           - Adresse civique complète
           - Désignation cadastrale (lot, cadastre, circonscription)
           - Type de propriété (résidentielle, commerciale, terrain, etc.)
           - Superficie (terrain et bâtiment)

        3. ASPECTS FINANCIERS:
           - Prix de vente total
           - Acompte/Dépôt
           - Hypothèque à obtenir
           - Taxes municipales et scolaires
           - Taxe de bienvenue (droits de mutation)
           - Frais notariaux

        4. DATES CRITIQUES:
           - Date de signature
           - Date d'occupation
           - Dates d'échéance (inspections, conditions)
           - Date de l'acte notarié

        INSTRUCTIONS D'EXTRACTION:
        1. Utilise les tools fournis pour chaque type de données
        2. Pour les montants: extrais le chiffre ET la devise
        3. Pour les dates: format ISO (YYYY-MM-DD) si possible
        4. Pour les noms: inclus les titres (M., Mme, Me)
        5. Pour les adresses: format complet avec code postal

        EXEMPLES:
        Montant: "Prix de vente: 485 000 $"
        → {"montant": 485000, "devise": "CAD", "type": "prix_vente"}

        Date: "Signature prévue le 20 décembre 2024"
        → {"date": "2024-12-20", "type": "signature"}

        Nom: "M. Jean-Pierre Tremblay et Mme Marie-Claude Gagnon"
        → [
          {"titre": "M.", "prenom": "Jean-Pierre", "nom": "Tremblay", "role": "vendeur"},
          {"titre": "Mme", "prenom": "Marie-Claude", "nom": "Gagnon", "role": "vendeur"}
        ]

        Adresse: "456 rue Champlain, Québec (Québec) G1K 4H2"
        → {
          "numero": "456",
          "rue": "rue Champlain",
          "ville": "Québec",
          "province": "Québec",
          "code_postal": "G1K 4H2",
          "type": "propriete"
        }

        PRIORITÉS:
        1. Prix de vente (CRITIQUE)
        2. Parties (vendeur/acheteur) (CRITIQUE)
        3. Adresse de la propriété (CRITIQUE)
        4. Dates clés (HAUTE)
        5. Cadastre (HAUTE)
        6. Conditions (MOYENNE)
        """),
        output_schema=DonneesExtraites,
        markdown=False,
    )

    agent_classificateur = Agent(
        name="ClassificateurTransactions",
        model=model,
        description=dedent("""\
        Tu es un notaire québécois spécialisé en droit immobilier.
        """),
        instructions=dedent("""\
        TA MISSION:
        Classifier avec PRÉCISION le type de transaction en analysant les documents fournis.

        TYPES DE TRANSACTIONS RECONNUS:
        1. VENTE IMMOBILIÈRE:
           - Vente résidentielle (maison, condo)
           - Vente commerciale
           - Vente de terrain
           Indices: "prix de vente", "acheteur/vendeur", "promesse d'achat"

        2. HYPOTHÈQUE/REFINANCEMENT:
           - Prêt hypothécaire
           - Refinancement
           Indices: "prêt", "créancier", "débiteur", "rang hypothécaire"

        3. DONATION:
           - Donation entre vifs
           - Donation testamentaire
           Indices: "donateur", "donataire", "sans contrepartie"

        4. SUCCESSION/TESTAMENT:
           - Testament notarié
           - Liquidation successorale
           Indices: "testateur", "légataire", "héritage"

        5. SERVITUDE:
           - Établissement de servitude
           - Extinction de servitude
           Indices: "fonds servant", "fonds dominant", "droit de passage"

        6. AUTRE:
           - Copropriété divise
           - Bail emphytéotique
           - Déclaration de copropriété

        DOCUMENTS ATTENDUS PAR TYPE:

        VENTE IMMOBILIÈRE:
        - Promesse d'achat-vente (REQUIS)
        - Certificat de localisation (REQUIS)
        - Certificat de recherche (REQUIS)
        - Titre de propriété (REQUIS)
        - Déclaration du vendeur (RECOMMANDÉ)
        - Rapport d'inspection (RECOMMANDÉ)
        - Preuve de zonage (SI COMMERCIAL)
        - Certificat d'arpentage (SI RÉCENT)

        HYPOTHÈQUE:
        - Offre de prêt (REQUIS)
        - Évaluation bancaire (REQUIS)
        - Contrat hypothécaire (REQUIS)
        - Assurance prêt (REQUIS)

        INSTRUCTIONS:
        1. Analyse le contenu complet des documents
        2. Identifie les mots-clés juridiques spécifiques
        3. Détermine le type de transaction
        4. Liste les documents présents
        5. Identifie les documents manquants

        EXEMPLE:
        Document contient: "prix de vente 485 000 $", "acheteur François Bélanger", "maison unifamiliale"
        → {
          "type_transaction": "vente",
          "type_propriete": "residentielle",
          "documents_identifies": ["promesse_achat_vente.pdf"],
          "documents_manquants": [
            "certificat_localisation.pdf",
            "titre_propriete.pdf",
            "certificat_recherche.pdf"
          ]
        }
        """),
        output_schema=Classification,
        markdown=False,
    )

    agent_verificateur = Agent(
        name="VerificateurCoherence",
        model=model,
        description=dedent("""\
        Tu es un notaire principal chargé de la révision qualité d'un dossier immobilier.
        """),
        instructions=dedent("""\
        TA MISSION:
        Effectuer une vérification RIGOUREUSE de la cohérence et complétude du dossier.

        VÉRIFICATIONS CRITIQUES:

        1. COHÉRENCE DES MONTANTS:
           ✓ Prix de vente = Acompte + Hypothèque + Mise de fonds
           ✓ Taxe de bienvenue calculée correctement:
             - 0-60 000$: 0.5%
             - 60 001-300 000$: 1.0%
             - 300 001$+: 1.5%
           ✓ Taxes municipales/scolaires proportionnelles au prix
           ✓ Pas de montant négatif ou aberrant

        2. COHÉRENCE TEMPORELLE:
           ✓ Date signature < Date conditions < Date acte notarié < Date occupation
           ✓ Délais raisonnables entre événements (15-60 jours typique)
           ✓ Dates dans le futur ou récentes (pas de dates aberrantes)

        3. COHÉRENCE DES PARTIES:
           ✓ Mêmes noms vendeur/acheteur dans tous les documents
           ✓ Orthographe cohérente des noms
           ✓ Adresses cohérentes

        4. COHÉRENCE DE LA PROPRIÉTÉ:
           ✓ Même adresse civique dans tous les documents
           ✓ Numéro cadastral cohérent
           ✓ Superficie cohérente si mentionnée plusieurs fois

        5. COMPLÉTUDE DU DOSSIER:
           Documents requis pour VENTE RÉSIDENTIELLE:
           - [ ] Promesse d'achat-vente
           - [ ] Certificat de localisation (< 10 ans)
           - [ ] Titre de propriété
           - [ ] Certificat de recherche au registre foncier
           - [ ] Déclaration du vendeur
           - [ ] Preuve paiement taxes municipales
           - [ ] Offre de prêt hypothécaire (si applicable)
           - [ ] Rapport d'inspection (recommandé)

        CALCULS AUTOMATIQUES:

        Taxe de bienvenue (Québec):
        - Si prix <= 60 000$: prix × 0.5%
        - Si prix <= 300 000$: 300$ + (prix - 60 000$) × 1.0%
        - Si prix > 300 000$: 2 700$ + (prix - 300 000$) × 1.5%

        SEUILS D'ALERTE:
        - Score < 0.5: ROUGE - Dossier incomplet, ne pas procéder
        - Score 0.5-0.7: ORANGE - Validation humaine requise
        - Score > 0.7: VERT - Dossier acceptable

        EXEMPLE D'ALERTE:
        Prix de vente: 485 000 $
        Taxe bienvenue déclarée: 5 000 $
        Taxe calculée: 7 425 $
        → ALERTE: "Écart de 2 425 $ dans la taxe de bienvenue (déclaré: 5 000 $, calculé: 7 425 $)"

        SCORE DE VÉRIFICATION:
        Calcule un score de 0.0 à 1.0 basé sur:
        - Cohérence des dates: 20%
        - Cohérence des montants: 30%
        - Complétude du dossier: 30%
        - Absence d'alertes critiques: 20%
        """),
        output_schema=Verification,
        markdown=False,
    )

    agent_generateur = Agent(
        name="GenerateurChecklist",
        model=model,
        description=dedent("""\
        Tu es le gestionnaire de dossiers d'une étude notariale québécoise.
        """),
        instructions=dedent("""\
        TA MISSION:
        Générer une checklist ACTIONNABLE et PRIORISÉE pour finaliser le dossier.

        STRUCTURE DE LA CHECKLIST:

        1. ITEMS PAR PRIORITÉ:
           - CRITIQUE (⚠️): Bloquant pour la signature
           - HAUTE (❗): Nécessaire avant finalisation
           - MOYENNE (ℹ️): Recommandé mais non-bloquant
           - BASSE (💡): Nice-to-have

        2. FORMAT CHECKLIST:
        Chaque item doit contenir:
        - Item: Description claire et actionnable
        - Priorité: critique|haute|moyenne|basse
        - Complete: false (par défaut)

        3. CATÉGORIES D'ITEMS:

        DOCUMENTS À OBTENIR:
        □ Certificat de localisation (< 10 ans) - Arpenteur
        □ Certificat de recherche - Bureau de la publicité des droits
        □ Preuve paiement taxes - Municipalité
        □ Rapport d'inspection - Inspecteur en bâtiment

        VÉRIFICATIONS À EFFECTUER:
        □ Vérifier titre de propriété (20 dernières années)
        □ Rechercher charges/hypothèques/privilèges
        □ Confirmer zonage et conformité
        □ Vérifier servitudes et restrictions

        CALCULS ET DOCUMENTS À PRÉPARER:
        □ Calculer taxe de bienvenue exacte
        □ Préparer état d'ajustement (taxes, huile, etc.)
        □ Rédiger acte de vente définitif
        □ Préparer quittances hypothécaires (si applicable)

        COORDINATION:
        □ Confirmer date signature avec toutes les parties
        □ Réserver salle de conférence
        □ Préparer copies pour toutes les parties
        □ Coordonner transfert de fonds

        4. POINTS D'ATTENTION SPÉCIFIQUES:

        BASÉ SUR VÉRIFICATIONS:
        - Si écart montants → "Valider calcul taxe de bienvenue avec client"
        - Si dates serrées → "Accélérer obtention certificat localisation"
        - Si document manquant → "Relancer [partie] pour [document]"
        - Si alerte servitude → "Obtenir acte de servitude détaillé"

        DÉLAIS TYPIQUES:
        - Certificat localisation: 1-2 semaines
        - Certificat recherche: 3-5 jours
        - Rapport inspection: 3-7 jours
        - Offre hypothèque: 5-10 jours

        5. SCORE DE CONFIANCE:
        Calcule un score de 0.0 à 1.0 basé sur:
        - Complétude des informations (40%)
        - Cohérence des données (30%)
        - Absence de drapeaux rouges (30%)
        - Score < 0.85 = validation humaine requise

        6. COMMENTAIRES FINAUX:
        Résume l'état global du dossier en incluant:
        - Niveau de complétude
        - Risques identifiés
        - Recommandation générale (procéder, attendre, compléter)
        - Délai estimé avant signature

        EXEMPLE:
        Pour un dossier manquant certificat localisation et avec écart taxe:

        {
          "checklist": [
            {
              "item": "Obtenir certificat de localisation récent (< 10 ans)",
              "priorite": "critique",
              "complete": false
            },
            {
              "item": "Valider calcul taxe de bienvenue avec client",
              "priorite": "haute",
              "complete": false
            },
            {
              "item": "Obtenir certificat de recherche au registre foncier",
              "priorite": "haute",
              "complete": false
            }
          ],
          "points_attention": [
            "⚠️ CRITIQUE: Aucun certificat de localisation au dossier",
            "❗ IMPORTANT: Taxe de bienvenue sous-évaluée de 2 425 $",
            "ℹ️ INFO: Délai serré (15 jours) - Accélérer processus"
          ],
          "documents_a_obtenir": [
            "Certificat de localisation",
            "Certificat de recherche",
            "Déclaration du vendeur signée"
          ],
          "prochaines_etapes": [
            {
              "etape": "Commander certificat de localisation",
              "delai": "Immédiat",
              "responsable": "Notaire"
            },
            {
              "etape": "Contacter client pour ajustement taxe bienvenue",
              "delai": "48 heures",
              "responsable": "Notaire"
            }
          ],
          "score_confiance": 0.45,
          "commentaires": "Dossier incomplet nécessitant documents critiques. Taxe de bienvenue à ajuster. Recommandation: Reporter signature de 2 semaines pour obtenir tous les documents requis."
        }
        """),
        output_schema=Checklist,
        markdown=False,
    )

    print(f"\n{'='*70}")
    print(f"WORKFLOW: Analyse de dossier notarial")
    print(f"Modèle: {model}")
    print(f"Dossier: {metadata.get('nom_dossier', 'N/A')}")
    print(f"Documents: {len(fichiers_pdf)} PDF(s)")
    print(f"{'='*70}\n")

    # État du workflow
    state = {
        "metadata": metadata,
        "fichiers": fichiers_pdf,
        "etapes_completees": []
    }

    # ========================================
    # ÉTAPE 1: Extraction des données
    # ========================================
    print("📄 Étape 1: Extraction des données des documents...")
    await emit_progress(
        step=1,
        step_name="Extraction des données",
        event_type="step_start",
        message="Extraction des informations des documents PDF...",
        progress_percent=5.0,
    )

    try:
        # Construire le prompt pour l'extraction
        prompt_extraction = f"""
        Extrais toutes les informations des {len(fichiers_pdf)} document(s) fourni(s).

        Fichiers à analyser:
        {json.dumps(fichiers_pdf, indent=2)}

        Pour chaque document, utilise les tools disponibles pour extraire:
        - Le texte complet
        - Les montants (prix, taxes, frais)
        - Les dates (signature, transfert, occupation)
        - Les noms (parties impliquées)
        - Les adresses (propriété, parties)

        Retourne un JSON avec la structure DonneesExtraites.
        """

        resultat_extraction = await agent_extracteur.arun(prompt_extraction)

        # Parser le résultat (peut être Pydantic, dict ou string)
        if hasattr(resultat_extraction, 'content'):
            content = resultat_extraction.content
            # Si c'est un objet Pydantic, le convertir en dict
            if hasattr(content, 'model_dump'):
                state["donnees_extraites"] = content.model_dump()
            elif isinstance(content, str):
                state["donnees_extraites"] = parser_json_safe(content)
            else:
                state["donnees_extraites"] = content
        else:
            state["donnees_extraites"] = resultat_extraction

        state["etapes_completees"].append("extraction")
        print("✓ Extraction complétée\n")
        await emit_progress(
            step=1,
            step_name="Extraction des données",
            event_type="step_end",
            message="Extraction terminée avec succès",
            progress_percent=25.0,
        )

    except Exception as e:
        logger.error(f"Erreur à l'étape extraction: {e}")
        return {
            "success": False,
            "erreur_etape": "extraction",
            "erreur_message": str(e),
            "etapes_completees": state.get("etapes_completees", []),
        }

    # ========================================
    # ÉTAPE 2: Classification
    # ========================================
    print("🏷️  Étape 2: Classification de la transaction...")
    await emit_progress(
        step=2,
        step_name="Classification",
        event_type="step_start",
        message="Classification du type de transaction...",
        progress_percent=30.0,
    )

    try:
        prompt_classification = f"""
        Basé sur les données extraites ci-dessous, classifie cette transaction.

        Données:
        {json.dumps(state["donnees_extraites"], indent=2, ensure_ascii=False)}

        Retourne un JSON avec la structure Classification.
        """

        resultat_classification = await agent_classificateur.arun(prompt_classification)

        # Parser le résultat (peut être Pydantic, dict ou string)
        if hasattr(resultat_classification, 'content'):
            content = resultat_classification.content
            if hasattr(content, 'model_dump'):
                state["classification"] = content.model_dump()
            elif isinstance(content, str):
                state["classification"] = parser_json_safe(content)
            else:
                state["classification"] = content
        else:
            state["classification"] = resultat_classification

        state["etapes_completees"].append("classification")
        print("✓ Classification complétée\n")
        await emit_progress(
            step=2,
            step_name="Classification",
            event_type="step_end",
            message="Classification terminée avec succès",
            progress_percent=50.0,
        )

    except Exception as e:
        logger.error(f"Erreur à l'étape classification: {e}")
        return {
            "success": False,
            "erreur_etape": "classification",
            "erreur_message": str(e),
            "etapes_completees": state.get("etapes_completees", []),
            "donnees_partielles": {"donnees_extraites": state.get("donnees_extraites")}
        }

    # ========================================
    # ÉTAPE 3: Vérification
    # ========================================
    print("✅ Étape 3: Vérification de cohérence...")
    await emit_progress(
        step=3,
        step_name="Vérification",
        event_type="step_start",
        message="Vérification de la cohérence des données...",
        progress_percent=55.0,
    )

    try:
        prompt_verification = f"""
        Vérifie la cohérence et complétude de ce dossier.

        Données extraites:
        {json.dumps(state["donnees_extraites"], indent=2, ensure_ascii=False)}

        Classification:
        {json.dumps(state["classification"], indent=2, ensure_ascii=False)}

        Retourne un JSON avec la structure Verification.
        """

        resultat_verification = await agent_verificateur.arun(prompt_verification)

        # Parser le résultat (peut être Pydantic, dict ou string)
        if hasattr(resultat_verification, 'content'):
            content = resultat_verification.content
            if hasattr(content, 'model_dump'):
                state["verification"] = content.model_dump()
            elif isinstance(content, str):
                state["verification"] = parser_json_safe(content)
            else:
                state["verification"] = content
        else:
            state["verification"] = resultat_verification

        state["etapes_completees"].append("verification")
        print("✓ Vérification complétée\n")
        await emit_progress(
            step=3,
            step_name="Vérification",
            event_type="step_end",
            message="Vérification terminée avec succès",
            progress_percent=75.0,
        )

    except Exception as e:
        logger.error(f"Erreur à l'étape verification: {e}")
        return {
            "success": False,
            "erreur_etape": "verification",
            "erreur_message": str(e),
            "etapes_completees": state.get("etapes_completees", []),
            "donnees_partielles": {
                "donnees_extraites": state.get("donnees_extraites"),
                "classification": state.get("classification")
            }
        }

    # ========================================
    # ÉTAPE 4: Génération de la checklist
    # ========================================
    print("📋 Étape 4: Génération de la checklist...")
    await emit_progress(
        step=4,
        step_name="Génération checklist",
        event_type="step_start",
        message="Génération de la checklist finale...",
        progress_percent=80.0,
    )

    try:
        prompt_checklist = f"""
        Génère une checklist complète pour le notaire.

        Toutes les analyses précédentes:
        {json.dumps({
            "donnees": state["donnees_extraites"],
            "classification": state["classification"],
            "verification": state["verification"]
        }, indent=2, ensure_ascii=False)}

        Retourne un JSON avec la structure Checklist.
        """

        resultat_checklist = await agent_generateur.arun(prompt_checklist)

        # Parser le résultat (peut être Pydantic, dict ou string)
        if hasattr(resultat_checklist, 'content'):
            content = resultat_checklist.content
            if hasattr(content, 'model_dump'):
                state["checklist"] = content.model_dump()
            elif isinstance(content, str):
                state["checklist"] = parser_json_safe(content)
            else:
                state["checklist"] = content
        else:
            state["checklist"] = resultat_checklist

        state["etapes_completees"].append("checklist")
        print("✓ Checklist générée\n")
        await emit_progress(
            step=4,
            step_name="Génération checklist",
            event_type="step_end",
            message="Checklist générée avec succès",
            progress_percent=95.0,
        )

    except Exception as e:
        logger.error(f"Erreur à l'étape checklist: {e}")
        return {
            "success": False,
            "erreur_etape": "checklist",
            "erreur_message": str(e),
            "etapes_completees": state.get("etapes_completees", []),
            "donnees_partielles": {
                "donnees_extraites": state.get("donnees_extraites"),
                "classification": state.get("classification"),
                "verification": state.get("verification")
            }
        }

    # ========================================
    # RÉSULTAT FINAL
    # ========================================
    score_confiance = state["checklist"].get("score_confiance", 0.0)

    print(f"{'='*70}")
    print(f"✨ ANALYSE COMPLÉTÉE")
    print(f"Score de confiance: {score_confiance:.2%}")
    print(f"Validation humaine requise: {'OUI' if score_confiance < 0.85 else 'NON'}")
    print(f"{'='*70}\n")

    # Émettre l'événement "complete" pour le frontend
    await emit_progress(
        step=4,
        step_name="Terminé",
        event_type="complete",
        message="Analyse terminée avec succès!",
        progress_percent=100.0,
        data={"score_confiance": score_confiance},
    )

    # Sauvegarder dans le session_state pour cache (si disponible)
    if session_state is not None:
        session_state["derniere_analyse"] = state

    return {
        "success": True,
        "donnees_extraites": state["donnees_extraites"],
        "classification": state["classification"],
        "verification": state["verification"],
        "checklist": state["checklist"],
        "score_confiance": score_confiance,
        "requiert_validation": score_confiance < 0.85,
        "etapes_completees": state["etapes_completees"]
    }


# ========================================
# Configuration SurrealDB pour le Workflow
# ========================================

# Utilisation de SurrealDB au lieu de SQLite pour:
# ✅ Une seule base de données pour toute l'application (cohérence)
# ✅ Support natif du JSON pour les états de workflow complexes
# ✅ Relations graphe natives (documents ↔ dossiers ↔ agents)
# ✅ Live queries pour le monitoring temps réel
# ✅ Recherche vectorielle intégrée (futur)

# Credentials SurrealDB
surreal_credentials = {
    "username": settings.surreal_username,
    "password": settings.surreal_password,
}

# Initialisation de la DB Agno avec SurrealDB
# Paramètres: client, url, credentials, namespace, database (positionnels)
workflow_db = SurrealDb(
    None,  # client - Agno créera le client automatiquement
    settings.surreal_url,
    surreal_credentials,
    settings.surreal_namespace,
    settings.surreal_database,
)

# ========================================
# Définition du Workflow
# ========================================

workflow_analyse_dossier = Workflow(
    name="AnalyseDossierNotarial",
    description="Workflow complet pour analyser un dossier notarial avec extraction, classification, vérification et génération de checklist",
    db=workflow_db,  # Utilise SurrealDB au lieu de SQLite
    steps=analyse_dossier_execution,
    session_state={},
)


# ========================================
# Fonction helper pour compatibilité
# ========================================

class WorkflowAnalyseDossier:
    """
    Classe wrapper pour compatibilité avec l'ancien code.
    Utilise le workflow Agno v2.0 en interne.

    Pattern officiel Agno:
    - Accepte un paramètre db (instance SurrealDb d'Agno)
    - Si fourni: crée un nouveau workflow avec persistance automatique
    - Si None: utilise le workflow par défaut (pour compatibilité)

    Modèles supportés:
    - "ollama:<model_name>" (ex: "ollama:qwen2.5:7b", "ollama:mistral")
    - "anthropic:<model_id>" (ex: "anthropic:claude-sonnet-4-5-20250929")
    - "openai:<model_id>" (ex: "openai:gpt-4o-mini")
    """

    def __init__(self, model: str = "ollama:qwen2.5:7b", db=None):
        """
        Initialise le wrapper.

        Args:
            model: Modèle LLM à utiliser (ex: "ollama:qwen2.5:7b")
                   Formats: "ollama:MODEL", "anthropic:MODEL", "openai:MODEL"
            db: Instance SurrealDb d'Agno pour persistance automatique
        """
        self.model = model  # Garde la spécification string

        # Si db fourni, créer un nouveau workflow avec persistance Agno
        if db is not None:
            self.workflow = Workflow(
                name="AnalyseDossierNotarial",
                description="Workflow complet pour analyser un dossier notarial avec extraction, classification, vérification et génération de checklist",
                db=db,  # ✅ Persistance automatique Agno
                steps=analyse_dossier_execution,
                session_state={"model": model},  # ✅ Passer le modèle aux agents
            )
        else:
            # Fallback: utiliser le workflow par défaut avec le modèle
            self.workflow = Workflow(
                name="AnalyseDossierNotarial",
                description="Workflow complet pour analyser un dossier notarial avec extraction, classification, vérification et génération de checklist",
                steps=analyse_dossier_execution,
                session_state={"model": model},
            )

    def run(
        self,
        fichiers_pdf: list[str],
        metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Exécute le workflow (version synchrone).

        Note: Cette méthode est fournie pour compatibilité.
        Utilisez directement workflow_analyse_dossier.arun() si possible.
        """
        import asyncio

        # Ajouter le modèle dans metadata pour que les agents l'utilisent
        metadata_with_model = {**metadata, "_model": self.model}

        # Exécuter de manière asynchrone
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.workflow.arun(
                fichiers_pdf=fichiers_pdf,
                metadata=metadata_with_model,
            )
        )

    async def arun(
        self,
        fichiers_pdf: list[str],
        metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Exécute le workflow (version asynchrone)."""
        # Ajouter le modèle dans metadata pour que les agents l'utilisent
        metadata_with_model = {**metadata, "_model": self.model}

        return await self.workflow.arun(
            fichiers_pdf=fichiers_pdf,
            metadata=metadata_with_model,
        )


# ========================================
# Tests
# ========================================

if __name__ == "__main__":
    import asyncio

    async def test_workflow():
        """Teste le workflow avec des données fictives."""

        print("🧪 Test du Workflow d'Analyse de Dossier")
        print("="*70)

        # Données de test
        fichiers_pdf = [
            "test_data/promesse_achat_vente.pdf",
            "test_data/certificat_localisation.pdf",
        ]

        metadata = {
            "nom_dossier": "Vente - 123 Rue Example",
            "type_attendu": "vente",
            "nb_documents": 2,
        }

        # Exécuter le workflow
        resultat = await workflow_analyse_dossier.arun(
            fichiers_pdf=fichiers_pdf,
            metadata=metadata,
        )

        # Afficher le résultat
        print("\n📊 RÉSULTAT:")
        print(json.dumps(resultat, indent=2, ensure_ascii=False))

    # Exécuter le test
    asyncio.run(test_workflow())
