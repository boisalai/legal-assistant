"""
Service de génération de mots de passe sécurisés.

Ce service fournit les fonctionnalités pour:
- Générer des mots de passe aléatoires cryptographiquement sûrs
- Évaluer la force des mots de passe générés
"""

import secrets
import string
from typing import List, Tuple
from dataclasses import dataclass

# Constantes
SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
AMBIGUOUS_CHARS = "0O1lI"


@dataclass
class PasswordResult:
    """Résultat de génération d'un mot de passe."""
    password: str
    length: int
    strength: str
    score: int
    remarks: List[str]


def generate_password(
    length: int = 16,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_symbols: bool = True,
    exclude_ambiguous: bool = False
) -> str:
    """
    Génère un mot de passe aléatoire sécurisé.

    Args:
        length: Longueur du mot de passe
        include_uppercase: Inclure les majuscules (A-Z)
        include_lowercase: Inclure les minuscules (a-z)
        include_digits: Inclure les chiffres (0-9)
        include_symbols: Inclure les symboles
        exclude_ambiguous: Exclure les caractères ambigus (0, O, l, 1, I)

    Returns:
        Le mot de passe généré

    Raises:
        ValueError: Si les paramètres sont invalides
    """
    # Préparation des jeux de caractères
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = SYMBOLS

    if exclude_ambiguous:
        uppercase = "".join(c for c in uppercase if c not in AMBIGUOUS_CHARS)
        lowercase = "".join(c for c in lowercase if c not in AMBIGUOUS_CHARS)
        digits = "".join(c for c in digits if c not in AMBIGUOUS_CHARS)

    # Mapping des types de caractères
    char_types = [
        (include_uppercase, uppercase, "majuscules"),
        (include_lowercase, lowercase, "minuscules"),
        (include_digits, digits, "chiffres"),
        (include_symbols, symbols, "symboles"),
    ]

    # Collecter les types actifs
    active_types = [(charset, name) for include, charset, name in char_types if include and charset]

    if not active_types:
        raise ValueError("Au moins un type de caractère doit être sélectionné")

    # Vérification dynamique de la longueur minimale
    min_length = len(active_types)
    if length < min_length:
        raise ValueError(
            f"Longueur insuffisante : {length} < {min_length} "
            f"(minimum requis pour inclure {', '.join(name for _, name in active_types)})"
        )

    # Garantir au moins un caractère de chaque type
    characters = ""
    required_chars = []

    for charset, _ in active_types:
        characters += charset
        required_chars.append(secrets.choice(charset))

    # Compléter avec des caractères aléatoires
    remaining_length = length - len(required_chars)
    password_chars = required_chars + [
        secrets.choice(characters) for _ in range(remaining_length)
    ]

    # Mélanger le mot de passe
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


def evaluate_strength(password: str) -> Tuple[str, int, List[str]]:
    """
    Évalue la force d'un mot de passe.

    Returns:
        Un tuple (description, score sur 100, liste de remarques)
    """
    score = 0
    remarks = []

    # Longueur
    if len(password) >= 8:
        score += 15
    else:
        remarks.append("Trop court (< 8 caractères)")

    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    if len(password) >= 20:
        score += 5

    # Diversité des caractères
    has_lower = any(c in string.ascii_lowercase for c in password)
    has_upper = any(c in string.ascii_uppercase for c in password)
    has_digit = any(c in string.digits for c in password)
    has_symbol = any(c in SYMBOLS for c in password)

    if has_lower:
        score += 10
    else:
        remarks.append("Pas de minuscules")

    if has_upper:
        score += 10
    else:
        remarks.append("Pas de majuscules")

    if has_digit:
        score += 10
    else:
        remarks.append("Pas de chiffres")

    if has_symbol:
        score += 15
    else:
        remarks.append("Pas de symboles")

    # Détection des patterns faibles
    password_lower = password.lower()

    # Répétitions (3+ caractères identiques consécutifs)
    for i in range(len(password) - 2):
        if password[i] == password[i + 1] == password[i + 2]:
            score -= 10
            remarks.append("Contient des répétitions")
            break

    # Suites logiques
    sequences = [
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789",
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ]

    for seq in sequences:
        for i in range(len(seq) - 3):
            if seq[i:i + 4] in password_lower:
                score -= 15
                remarks.append("Contient une suite logique")
                break
        else:
            continue
        break

    # Bonus pour haute entropie (caractères uniques)
    unique_ratio = len(set(password)) / len(password)
    if unique_ratio > 0.8:
        score += 15
    elif unique_ratio < 0.5:
        score -= 5
        remarks.append("Beaucoup de caractères répétés")

    # Normaliser le score
    score = max(0, min(100, score))

    # Évaluation
    if score >= 80:
        level = "Très fort"
    elif score >= 60:
        level = "Fort"
    elif score >= 40:
        level = "Moyen"
    else:
        level = "Faible"

    return level, score, remarks


def generate_passwords_batch(
    count: int = 20,
    length: int = 16,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_symbols: bool = True,
    exclude_ambiguous: bool = False
) -> List[PasswordResult]:
    """
    Génère un lot de mots de passe avec évaluation.

    Args:
        count: Nombre de mots de passe à générer
        length: Longueur de chaque mot de passe
        include_uppercase: Inclure les majuscules
        include_lowercase: Inclure les minuscules
        include_digits: Inclure les chiffres
        include_symbols: Inclure les symboles
        exclude_ambiguous: Exclure les caractères ambigus

    Returns:
        Liste de PasswordResult
    """
    results = []

    for _ in range(count):
        password = generate_password(
            length=length,
            include_uppercase=include_uppercase,
            include_lowercase=include_lowercase,
            include_digits=include_digits,
            include_symbols=include_symbols,
            exclude_ambiguous=exclude_ambiguous
        )

        strength, score, remarks = evaluate_strength(password)

        results.append(PasswordResult(
            password=password,
            length=len(password),
            strength=strength,
            score=score,
            remarks=remarks
        ))

    return results
