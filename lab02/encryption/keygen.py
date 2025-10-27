from __future__ import annotations

import datetime as dt

from dataclasses import dataclass
from typing import Iterable
from .vigenere import sanitize_key

# Перелік форматів вводу дати, що допускаються у формі.
SUPPORTED_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y")


@dataclass(frozen=True)
class KeyMaterial:
    caesar_shift: int
    caesar_details: str
    vigenere_key: str
    vigenere_details: str


def _parse_birthdate(raw_value: str) -> dt.date:
    """Парсить дату народження, підтримуючи кілька поширених форматів."""
    cleaned = raw_value.strip()
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            return dt.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError("Невірний формат дати. Використовуйте YYYY-MM-DD або DD.MM.YYYY.")


def _sum_digits(values: Iterable[int]) -> int:
    """Обчислює суму цифр для формування зсуву Цезаря."""
    return sum(values)


def derive_caesar_shift(birthdate: str) -> tuple[int, str]:
    """Формує зсув Цезаря як суму цифр дати народження."""
    date_value = _parse_birthdate(birthdate)
    digits = [int(char) for char in date_value.strftime("%d%m%Y")]
    shift = _sum_digits(digits)
    explanation = f"Сума цифр {digits} = {shift}"
    return max(shift, 1), explanation


def derive_vigenere_key(surname: str) -> tuple[str, str]:
    """Санітує прізвище та повертає літерний ключ для шифру Віженера."""
    sanitized = sanitize_key(surname)
    explanation = f"Прізвище '{surname.strip()}' → ключ '{sanitized.upper()}'"
    return sanitized.upper(), explanation


def derive_keys(birthdate: str, surname: str) -> KeyMaterial:
    """Комплексно обчислює ключові параметри обох класичних шифрів."""
    shift, caesar_details = derive_caesar_shift(birthdate)
    key, vigenere_details = derive_vigenere_key(surname)
    return KeyMaterial(
        caesar_shift=shift,
        caesar_details=caesar_details,
        vigenere_key=key,
        vigenere_details=vigenere_details,
    )
