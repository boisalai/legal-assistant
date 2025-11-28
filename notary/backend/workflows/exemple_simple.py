"""
Exemple simple de workflow Agno pour comprendre les concepts de base.

Ce workflow démontre:
1. Comment créer un agent simple
2. Comment utiliser des tools (fonctions)
3. Comment gérer l'état entre les étapes
4. Comment chaîner plusieurs agents

Cas d'usage: Analyser un texte simple et en extraire des informations
"""

from agno import Agent, Workflow


# ========================================
# ÉTAPE 1: Définir les "Tools" (fonctions)
# ========================================
# Les tools sont des fonctions que les agents peuvent utiliser
# pour effectuer des actions concrètes

def compter_mots(texte: str) -> dict:
    """
    Tool simple: compte les mots dans un texte.

    Args:
        texte: Le texte à analyser

    Returns:
        Dictionnaire avec les statistiques
    """
    mots = texte.split()
    return {
        "nombre_mots": len(mots),
        "nombre_caracteres": len(texte),
        "mots_uniques": len(set(mots))
    }


def extraire_nombres(texte: str) -> list[str]:
    """
    Tool: extrait tous les nombres d'un texte.

    Args:
        texte: Le texte à analyser

    Returns:
        Liste des nombres trouvés
    """
    import re
    nombres = re.findall(r'\d+', texte)
    return nombres


# ========================================
# ÉTAPE 2: Créer les Agents
# ========================================
# Chaque agent a un rôle spécifique et des instructions claires

def creer_agent_analyseur():
    """
    Agent qui analyse les caractéristiques d'un texte.

    Il a accès aux tools définis ci-dessus et sait comment les utiliser
    grâce à ses instructions.
    """
    return Agent(
        name="AnalyseurTexte",

        # Role: définit l'identité de l'agent
        role="Analyste de texte",

        # Instructions: comment l'agent doit se comporter
        instructions=[
            "Tu es un expert en analyse de texte",
            "Tu dois extraire des statistiques précises",
            "Utilise les tools disponibles pour analyser le texte",
            "Sois concis et factuel dans tes réponses"
        ],

        # Tools: fonctions que l'agent peut utiliser
        tools=[compter_mots, extraire_nombres],

        # Markdown: format de sortie
        markdown=True,

        # Show tool calls: pour le débogage
        show_tool_calls=True
    )


def creer_agent_resume():
    """
    Agent qui crée un résumé basé sur les analyses précédentes.

    Cet agent n'a pas de tools, il se concentre sur la synthèse.
    """
    return Agent(
        name="Resumeur",
        role="Créateur de résumés",
        instructions=[
            "Tu es un expert en synthèse d'information",
            "À partir des analyses fournies, crée un résumé clair",
            "Structure ton résumé en points importants",
            "Sois concis et précis"
        ],
        markdown=True
    )


# ========================================
# ÉTAPE 3: Créer le Workflow
# ========================================
# Le workflow orchestre les agents dans un ordre logique

class WorkflowAnalyseSimple(Workflow):
    """
    Workflow qui analyse un texte en deux étapes:
    1. Analyse statistique (Agent Analyseur)
    2. Création d'un résumé (Agent Resumeur)
    """

    def __init__(self, model: str = "openai:gpt-4"):
        """
        Initialise le workflow.

        Args:
            model: Le modèle LLM à utiliser (sera remplacé par MLX plus tard)
        """
        super().__init__(
            name="AnalyseTexteSimple",
            model=model,
        )

        # Créer les agents
        self.agent_analyseur = creer_agent_analyseur()
        self.agent_resumeur = creer_agent_resume()

    def run(self, texte_a_analyser: str) -> dict:
        """
        Exécute le workflow complet.

        Args:
            texte_a_analyser: Le texte à analyser

        Returns:
            Dictionnaire avec les résultats de l'analyse
        """
        print(f"\n{'='*60}")
        print(f"WORKFLOW: Analyse de texte simple")
        print(f"{'='*60}\n")

        # ---- ÉTAPE 1: Analyse statistique ----
        print("📊 Étape 1: Analyse statistique du texte...")

        # L'agent analyseur va utiliser les tools pour extraire des stats
        resultat_analyse = self.agent_analyseur.run(
            f"""
            Analyse ce texte et fournis-moi des statistiques détaillées:

            Texte:
            {texte_a_analyser}

            Utilise les tools disponibles pour extraire:
            - Nombre de mots
            - Nombre de caractères
            - Mots uniques
            - Nombres présents dans le texte
            """
        )

        print(f"\nRésultat de l'analyse:")
        print(f"{resultat_analyse.content}\n")

        # ---- ÉTAPE 2: Création du résumé ----
        print("📝 Étape 2: Création d'un résumé...")

        # L'agent resumeur utilise les résultats de l'étape 1
        resultat_resume = self.agent_resumeur.run(
            f"""
            Basé sur cette analyse de texte, crée un résumé concis:

            Texte original:
            {texte_a_analyser}

            Analyse:
            {resultat_analyse.content}

            Crée un résumé structuré avec les points clés.
            """
        )

        print(f"\nRésumé:")
        print(f"{resultat_resume.content}\n")

        # ---- RETOUR DES RÉSULTATS ----
        return {
            "texte_original": texte_a_analyser,
            "analyse": resultat_analyse.content,
            "resume": resultat_resume.content,
            "success": True
        }


# ========================================
# ÉTAPE 4: Fonction de test
# ========================================

def tester_workflow():
    """
    Fonction de test pour essayer le workflow.

    NOTE: Ce test nécessite un LLM configuré.
    Pour l'instant, on va juste définir la structure.
    Plus tard, on intégrera MLX ou Hugging Face.
    """
    texte_exemple = """
    L'acte de vente immobilière porte sur une propriété située au 123 rue Principale.
    Le prix de vente est de 450000 dollars. L'acheteur dispose de 30 jours pour
    compléter la transaction. Il y a 5 conditions préalables à respecter.
    """

    # NOTE: Pour l'instant, on ne peut pas exécuter car on n'a pas configuré le LLM
    # workflow = WorkflowAnalyseSimple(model="mlx:local")
    # resultat = workflow.run(texte_exemple)
    # print(resultat)

    print("⚠️  Workflow défini mais pas encore exécutable.")
    print("📌 Prochaine étape: Intégrer MLX ou Hugging Face")


if __name__ == "__main__":
    """
    Point d'entrée si on exécute ce fichier directement.
    """
    tester_workflow()
