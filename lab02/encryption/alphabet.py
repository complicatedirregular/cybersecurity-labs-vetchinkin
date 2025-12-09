from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Alphabet:
    """Описує абетку та надає сервісні методи для роботи з індексами."""

    name: str
    uppercase: str

    @property
    def lowercase(self) -> str:
        return self.uppercase.lower()

    def index(self, char: str) -> Optional[int]:
        if char in self.uppercase:
            return self.uppercase.index(char)
        if char in self.lowercase:
            return self.lowercase.index(char)
        return None

    def shift(self, char: str, offset: int) -> str:
        idx = self.index(char)
        if idx is None:
            return char
        target = self.uppercase if char.isupper() else self.lowercase
        return target[(idx + offset) % len(target)]


ALPHABETS: Dict[str, Alphabet] = {
    "latin": Alphabet("latin", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    "cyrillic": Alphabet("cyrillic", "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ"),
}


def identify_alphabet(char: str) -> Optional[Alphabet]:
    """Повертає конфігурацію абетки для переданого символу."""
    if not char or not char.isalpha():
        return None
    upper_char = char.upper()
    for alphabet in ALPHABETS.values():
        if upper_char in alphabet.uppercase:
            return alphabet
    return None


def char_index(char: str) -> Optional[int]:
    """Повертає позицію символу в межах його абетки (якщо підтримується)."""
    alphabet = identify_alphabet(char)
    if not alphabet:
        return None
    return alphabet.index(char.upper())


def normalize_shift(shift: int, alphabet: Alphabet) -> int:
    """Нормалізує зміщення до розміру відповідної абетки."""
    return shift % len(alphabet.uppercase)


def apply_shift(char: str, shift: int) -> str:
    """Здійснює циклічне зсування символу в межах його абетки."""
    alphabet = identify_alphabet(char)
    if not alphabet:
        return char
    normalized_shift = normalize_shift(shift, alphabet)
    return alphabet.shift(char, normalized_shift)


def sanitize_text(text: str) -> str:
    """Зрізає зайві пропуски з країв, не змінюючи внутрішніх пробілів."""
    return text.strip()
