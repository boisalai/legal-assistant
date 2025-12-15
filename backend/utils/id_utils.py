"""
Utilitaires pour la normalisation des IDs SurrealDB.

Ces fonctions garantissent que les IDs sont formatés correctement
pour SurrealDB, que ce soit "course:", "document:", etc.
"""


def normalize_course_id(course_id: str) -> str:
    """
    Normalise un ID de cours au format SurrealDB "course:".

    Args:
        course_id: ID brut (peut être "course:xxx", "case:xxx", "judgment:xxx", ou "xxx")

    Returns:
        ID normalisé au format "course:xxx"

    Examples:
        >>> normalize_course_id("course:123")
        'course:123'
        >>> normalize_course_id("case:123")
        'course:123'
        >>> normalize_course_id("judgment:123")
        'course:123'
        >>> normalize_course_id("123")
        'course:123'
    """
    # Supprimer les préfixes existants (support legacy case: et judgment:)
    clean_id = course_id.replace("course:", "").replace("case:", "").replace("judgment:", "")
    return f"course:{clean_id}"


# Backward compatibility alias
normalize_case_id = normalize_course_id


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
        full_id: ID complet (ex: "course:123" ou "document:456")
        expected_prefix: Préfixe attendu pour validation (optionnel)

    Returns:
        UUID seul sans préfixe

    Examples:
        >>> extract_record_id("course:123")
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
