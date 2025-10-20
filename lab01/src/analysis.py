from __future__ import annotations

from typing import Iterable, List, Sequence
from .constants import (
    CHAR_CLASS_ISSUES,
    CHAR_CLASS_LABELS,
    DICTIONARY_PENALTY,
    LONG_DIVERSE_BONUS,
    MAX_SCORE,
    MIN_RECOMMENDED_LENGTH,
    MIN_SCORE,
    PERSONAL_MATCH_PENALTY,
    SEQUENCE_PATTERNS,
    SEQUENCE_PENALTY,
)
from .data import PersonalData, PasswordAnalysisResult, dictionary_words


def find_matches(
    password_lower: str, tokens: Iterable[str], *, exact: bool = False
) -> List[str]:
    """Повертає список токенів, що збігаються з паролем."""
    if exact:
        return [
            token for token in tokens if len(token) >= 3 and token == password_lower
        ]
    return [token for token in tokens if len(token) >= 3 and token in password_lower]


def character_classes(password: str) -> dict[str, bool]:
    """Визначає, які типи символів присутні у паролі."""
    return {
        "lower": any(ch.islower() for ch in password),
        "upper": any(ch.isupper() for ch in password),
        "digit": any(ch.isdigit() for ch in password),
        "special": any(not ch.isalnum() for ch in password),
    }


def length_score(length: int) -> int:
    """Нараховує базові бали за довжину пароля."""
    if length < 6:
        return 0
    if length < 8:
        return 1
    if length < 12:
        return 3
    if length < 16:
        return 4
    return 5


def has_repeating_sequences(password_lower: str) -> bool:
    """Перевіряє пароль на повтори або знайомі послідовності символів."""
    if any(ch * 3 in password_lower for ch in set(password_lower)):
        return True
    return any(
        pattern[idx : idx + 3] in password_lower
        for pattern in SEQUENCE_PATTERNS
        for idx in range(len(pattern) - 2)
    )


def calculate_score(
    length: int,
    char_classes: dict[str, bool],
    personal_match_count: int,
    dictionary_match_count: int,
    has_sequences: bool,
) -> int:
    """Обчислює підсумковий бал з урахуванням бонусів і штрафів."""
    length_points = length_score(length)
    diversity_points = sum(1 for present in char_classes.values() if present)
    bonus = (
        LONG_DIVERSE_BONUS
        if length >= MIN_RECOMMENDED_LENGTH and diversity_points >= 3
        else 0
    )
    penalty = PERSONAL_MATCH_PENALTY * personal_match_count
    penalty += DICTIONARY_PENALTY * dictionary_match_count
    if has_sequences:
        penalty += SEQUENCE_PENALTY
    raw_score = length_points + diversity_points + bonus - penalty
    return max(MIN_SCORE, min(MAX_SCORE, raw_score))


def collect_issues(
    personal_matches: Sequence[str],
    dictionary_matches: Sequence[str],
    char_classes: dict[str, bool],
    length: int,
    has_sequences: bool,
) -> List[str]:
    """Формує перелік проблем, виявлених під час аналізу."""
    issues: List[str] = []
    if personal_matches:
        issues.append("Пароль містить персональні дані.")
    if dictionary_matches:
        issues.append("Виявлено поширені словникові паролі.")
    if has_sequences:
        issues.append("Знайдено послідовності або повтори символів.")
    for key, message in CHAR_CLASS_ISSUES.items():
        if not char_classes[key]:
            issues.append(message)
    if length < MIN_RECOMMENDED_LENGTH:
        issues.append("Довжина пароля менша за 12 символів.")
    return issues


def build_recommendations(
    personal_matches: Sequence[str],
    dictionary_matches: Sequence[str],
    char_classes: dict[str, bool],
    length: int,
    has_sequences: bool,
) -> List[str]:
    """Генерує рекомендації щодо посилення пароля."""
    advice: List[str] = []
    if personal_matches:
        advice.append("Приберіть персональні дані з пароля.")
    if dictionary_matches:
        sample = ", ".join(dictionary_matches[:3])
        advice.append(f"Уникайте поширених паролів (наприклад: {sample}).")
    if length < MIN_RECOMMENDED_LENGTH:
        advice.append("Збільште довжину пароля щонайменше до 12 символів.")
    missing_classes = [
        CHAR_CLASS_LABELS[key] for key, present in char_classes.items() if not present
    ]
    if missing_classes:
        advice.append(f"Додайте символи різних типів ({', '.join(missing_classes)}).")
    if has_sequences:
        advice.append("Уникайте очевидних послідовностей та повторів символів.")
    if not advice:
        advice.append(
            "Пароль виглядає надійним. Продовжуйте дотримуватися таких практик."
        )
    return advice


def strength_label(score: int) -> str:
    if score <= 3:
        return "Слабкий"
    if score <= 6:
        return "Середній"
    if score <= 8:
        return "Сильний"
    return "Дуже сильний"


def analyze_password(
    password: str, personal_data: PersonalData
) -> PasswordAnalysisResult:
    """Запускає повний аналіз пароля та повертає результат."""
    password_lower = password.lower()
    personal_matches = find_matches(password_lower, personal_data.tokens())
    dictionary_matches = find_matches(password_lower, dictionary_words(), exact=True)
    char_classes = character_classes(password)
    length = len(password)
    has_sequences = has_repeating_sequences(password_lower)
    score = calculate_score(
        length,
        char_classes,
        len(personal_matches),
        len(dictionary_matches),
        has_sequences,
    )
    issues = collect_issues(
        personal_matches, dictionary_matches, char_classes, length, has_sequences
    )
    recommendations = build_recommendations(
        personal_matches, dictionary_matches, char_classes, length, has_sequences
    )
    return PasswordAnalysisResult(
        password=password,
        score=score,
        strength=strength_label(score),
        personal_matches=personal_matches,
        dictionary_matches=dictionary_matches,
        issues=issues,
        recommendations=recommendations,
    )
