from __future__ import annotations

import math

from collections import Counter
from dataclasses import dataclass
from typing import Dict

CAESAR_LABEL = "Шифр Цезаря"
VIGENERE_LABEL = "Шифр Віженера"

VOWELS_LATIN = set("AEIOUY")
VOWELS_CYRILLIC = set("АЕЄИІЇОУЮЯ")


@dataclass(frozen=True)
class CipherMetrics:
    algorithm: str
    ciphertext: str
    length: int
    unique_symbols: int
    vowel_ratio: float
    entropy: float
    key_complexity: str
    frequency: Dict[str, int]


@dataclass(frozen=True)
class ComparativeReport:
    original_text: str
    caesar: CipherMetrics
    vigenere: CipherMetrics
    conclusion: str


def shannon_entropy(text: str) -> float:
    letters = [char.upper() for char in text if char.isalpha()]
    if not letters:
        return 0.0
    counts = Counter(letters)
    total = sum(counts.values())
    entropy = -sum(
        (count / total) * math.log2(count / total) for count in counts.values()
    )
    return round(entropy, 4)


def vowel_ratio(text: str) -> float:
    letters = [char.upper() for char in text if char.isalpha()]
    if not letters:
        return 0.0
    vowels = VOWELS_LATIN.union(VOWELS_CYRILLIC)
    vowel_count = sum(1 for char in letters if char in vowels)
    return round(vowel_count / len(letters), 4)


def frequency_distribution(text: str) -> Dict[str, int]:
    letters = [char.upper() for char in text if char.isalpha()]
    return dict(sorted(Counter(letters).items()))


def build_metrics(
    algorithm: str, ciphertext: str, key_complexity: str
) -> CipherMetrics:
    letters = [char for char in ciphertext if char.isalpha()]
    return CipherMetrics(
        algorithm=algorithm,
        ciphertext=ciphertext,
        length=len(ciphertext),
        unique_symbols=len(set(letters)),
        vowel_ratio=vowel_ratio(ciphertext),
        entropy=shannon_entropy(ciphertext),
        key_complexity=key_complexity,
        frequency=frequency_distribution(ciphertext),
    )


def formulate_conclusion(
    caesar_metrics: CipherMetrics, vigenere_metrics: CipherMetrics
) -> str:
    if vigenere_metrics.entropy > caesar_metrics.entropy:
        return "Шифр Віженера має вищу ентропію та різноманітність символів, тому його складніше зламати частотним аналізом порівняно з шифром Цезаря."
    return "Ентропія шифрів подібна, отже варто збільшувати довжину ключа або комбінувати методи для отримання кращої стійкості."


def build_report(
    original_text: str,
    caesar_cipher: str,
    vigenere_cipher: str,
    caesar_shift: int,
    vigenere_key: str,
) -> ComparativeReport:
    caesar_metrics = build_metrics(CAESAR_LABEL, caesar_cipher, f"Зсув: {caesar_shift}")
    vigenere_metrics = build_metrics(
        VIGENERE_LABEL,
        vigenere_cipher,
        f"Ключ: {vigenere_key} (довжина {len(vigenere_key)})",
    )
    conclusion = formulate_conclusion(caesar_metrics, vigenere_metrics)
    return ComparativeReport(
        original_text=original_text,
        caesar=caesar_metrics,
        vigenere=vigenere_metrics,
        conclusion=conclusion,
    )
