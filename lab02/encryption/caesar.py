from __future__ import annotations

from typing import List, Tuple
from .alphabet import apply_shift


def encrypt(text: str, shift: int) -> str:
    """Шифрує текст шляхом циклічного зсуву символів."""
    return "".join(apply_shift(char, shift) for char in text)


def decrypt(text: str, shift: int) -> str:
    """Розшифровує текст, виконаний шифром Цезаря."""
    return "".join(apply_shift(char, -shift) for char in text)


def brute_force(ciphertext: str, max_shift: int = 33) -> List[Tuple[int, str]]:
    """Генерує всі можливі варіанти шляхом повного перебору зсувів."""
    attempts: List[Tuple[int, str]] = []
    # Типове значення 33 відповідає кількості літер української абетки.
    for shift in range(1, max_shift + 1):
        attempts.append((shift, decrypt(ciphertext, shift)))
    return attempts
