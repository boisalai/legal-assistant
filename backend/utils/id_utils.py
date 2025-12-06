"""
Utilitaires pour la normalisation des IDs SurrealDB.

Ces fonctions garantissent que les IDs sont formatés correctement
pour SurrealDB, que ce soit "case:", "judgment:", ou "document:".
"""


def normalize_case_id(case_id: str) -> str:
    """
    Normalise un ID de dossier au format SurrealDB "judgment:".

    Args:
        case_id: ID brut (peut être "case:xxx", "judgment:xxx", ou "xxx")

    Returns:
        ID normalisé au format "judgment:xxx"

    Examples:
        >>> normalize_case_id("case:123")
        'judgment:123'
        >>> normalize_case_id("judgment:123")
        'judgment:123'
        >>> normalize_case_id("123")
        'judgment:123'
    """
    # Supprimer les préfixes existants
    clean_id = case_id.replace("case:", "").replace("judgment:", "")
    return f"judgment:{clean_id}"


def normalize_document_id(doc_id: str) -> str:
    """
    Normalise un ID de document au format SurrealDB "document:".

    Args:
        doc_id: ID brut (peut être "document:xxx" ou "xxx")

    Returns:
        ID normalisé au format "document:xxx"

    Examples:
        >>> normalize_document_id("document:456")
        'document:456'
        >>> normalize_document_id("456")
        'document:456'
    """
    if doc_id.startswith("document:"):
        return doc_id
    return f"document:{doc_id}"


def extract_record_id(full_id: str, expected_prefix: str = None) -> str:
    """
    Extrait la partie UUID d'un ID SurrealDB complet.

    Args:
        full_id: ID complet (ex: "judgment:123" ou "document:456")
        expected_prefix: Préfixe attendu pour validation (optionnel)

    Returns:
        UUID seul sans préfixe

    Examples:
        >>> extract_record_id("judgment:123")
        '123'
        >>> extract_record_id("document:456", "document")
        '456'
        >>> extract_record_id("123")
        '123'
    """
    # Si pas de ":", retourner tel quel
    if ":" not in full_id:
        return full_id

    prefix, record_id = full_id.split(":", 1)

    # Validation optionnelle du préfixe
    if expected_prefix and prefix != expected_prefix:
        raise ValueError(
            f"Expected prefix '{expected_prefix}', got '{prefix}' in ID '{full_id}'"
        )

    return record_id
