from __future__ import annotations

from pathlib import Path

MIN_SCORE = 1
MAX_SCORE = 10
MIN_RECOMMENDED_LENGTH = 12
PERSONAL_MATCH_PENALTY = 2
DICTIONARY_PENALTY = 1
SEQUENCE_PENALTY = 1
LONG_DIVERSE_BONUS = 1
DICTIONARY_FILENAME = "100k-most-used-passwords-NCSC.txt"

CHAR_CLASS_ISSUES = {
    "lower": "Відсутні малі літери.",
    "upper": "Відсутні великі літери.",
    "digit": "Відсутні цифри.",
    "special": "Відсутні спеціальні символи.",
}

CHAR_CLASS_LABELS = {
    "lower": "малі літери",
    "upper": "великі літери",
    "digit": "цифри",
    "special": "спеціальні символи",
}

SEQUENCE_PATTERNS = (
    "0123456789",
    "9876543210",
    "abcdefghijklmnopqrstuvwxyz",
    "zyxwvutsrqponmlkjihgfedcba",
    "йцукенгшщзхїфівапролджє",
)

DATE_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")

ROOT_DIR = Path(__file__).resolve().parent.parent
