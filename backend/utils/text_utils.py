"""
Utilitaires de traitement de texte.

Fonctions partagées pour le nettoyage et la manipulation de texte.
"""


def remove_yaml_frontmatter(content: str) -> str:
    """
    Retire le frontmatter YAML du contenu Markdown.

    Le frontmatter est délimité par --- au début et à la fin.
    Utilisé notamment par Docusaurus, Jekyll, Hugo, etc.

    Exemple:
    ---
    sidebar_position: 6
    custom_edit_url: null
    ---

    Args:
        content: Contenu du fichier (Markdown, texte, etc.)

    Returns:
        Contenu sans le frontmatter YAML
    """
    if not content.startswith("---"):
        return content

    lines = content.split("\n")
    end_index = -1

    # Trouver la ligne de fermeture ---
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break

    # Si on a trouvé la fermeture, retirer tout jusqu'à cette ligne incluse
    if end_index > 0:
        return "\n".join(lines[end_index + 1:]).strip()

    return content
