"""
Utilitaires de traitement de texte.

Fonctions partagées pour le nettoyage et la manipulation de texte.
"""


def sanitize_text(text: str) -> str:
    """
    Nettoie le texte en retirant les caractères problématiques.

    Retire notamment les null bytes (\x00) qui causent des erreurs
    de sérialisation dans SurrealDB.

    Args:
        text: Texte à nettoyer

    Returns:
        Texte nettoyé, sans caractères null

    Examples:
        >>> sanitize_text("Hello\x00World")
        'HelloWorld'
        >>> sanitize_text("Normal text")
        'Normal text'
    """
    if not text:
        return text

    # Remove null bytes (causes SurrealDB serialization errors)
    cleaned = text.replace("\x00", "")

    # Optionally remove other problematic control characters (except newlines/tabs)
    # cleaned = ''.join(char for char in cleaned if char.isprintable() or char in '\n\r\t')

    return cleaned


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
