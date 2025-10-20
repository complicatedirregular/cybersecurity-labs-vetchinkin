from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from typing import Iterable, List, Sequence
from .constants import DICTIONARY_FILENAME, ROOT_DIR


def normalize_token(value: str) -> str:
    """Нормалізує текст до нижнього регістру алфавітно-цифрових символів."""
    return "".join(ch for ch in value.lower() if ch.isalnum())


@lru_cache(maxsize=1)
def dictionary_words() -> List[str]:
    """Завантаження та кешування списку поширених паролів для перевірки за словником."""
    path = ROOT_DIR / DICTIONARY_FILENAME
    try:
        with path.open(encoding="utf-8") as handle:
            raw_words = [normalize_token(line.strip()) for line in handle]
    except OSError:
        return []
    filtered = [word for word in raw_words if len(word) >= 3]
    return list(dict.fromkeys(filtered))


@dataclass
class PersonalData:
    first_name: str
    last_name: str | None = None
    birth_date: date | None = None
    extra_words: Sequence[str] = field(default_factory=list)

    def tokens(self) -> List[str]:
        """Повертає унікальні токени, отримані на основі особистої інформації."""
        tokens: List[str] = []
        tokens.extend(self._normalized_strings())
        tokens.extend(self._birthdate_tokens())
        return list(dict.fromkeys(tokens))

    def _normalized_strings(self) -> Iterable[str]:
        for value in filter(None, [self.first_name, self.last_name, *self.extra_words]):
            token = normalize_token(value)
            if token:
                yield token

    def _birthdate_tokens(self) -> List[str]:
        if not self.birth_date:
            return []
        day = f"{self.birth_date.day:02d}"
        month = f"{self.birth_date.month:02d}"
        year = f"{self.birth_date.year}"
        return [
            year,
            month,
            day,
            f"{day}{month}",
            f"{month}{day}",
            f"{day}{month}{year}",
            f"{year}{month}{day}",
        ]


@dataclass
class PasswordAnalysisResult:
    password: str
    score: int
    strength: str
    personal_matches: List[str]
    dictionary_matches: List[str]
    issues: List[str]
    recommendations: List[str]
