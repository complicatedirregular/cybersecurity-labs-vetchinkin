from __future__ import annotations

from typing import Dict, List, Tuple
from .alphabet import ALPHABETS, identify_alphabet


KeyInfo = Tuple[str, Dict[str, List[int]]]


def sanitize_key(raw_key: str) -> str:
    """Залишає лише літери в ключі та гарантує, що ключ не порожній."""
    sanitized = "".join(char for char in raw_key if char.isalpha())
    if not sanitized:
        raise ValueError("Ключ для шифру Віженера має містити щонайменше одну літеру.")
    return sanitized


def prepare_key(raw_key: str) -> KeyInfo:
    """Готує послідовності зсувів для кожної підтримуваної абетки."""
    sanitized = sanitize_key(raw_key)
    shift_map: Dict[str, List[int]] = {}
    for name, alphabet in ALPHABETS.items():
        shifts: List[int] = []
        for char in sanitized:
            upper_char = char.upper()
            if upper_char in alphabet.uppercase:
                shifts.append(alphabet.uppercase.index(upper_char))
        if shifts:
            shift_map[name] = shifts
    if not shift_map:
        # Резервний варіант: трактуємо ключ як латинку, аби не зривати процес шифрування.
        latin = ALPHABETS["latin"]
        shift_map["latin"] = [
            ord(char.upper()) % len(latin.uppercase) for char in sanitized
        ]
    return sanitized.upper(), shift_map


def _transform(text: str, key_info: KeyInfo, direction: int) -> str:
    sanitized_key, shift_map = key_info
    if not shift_map or not sanitized_key:
        return text
    counters = {name: 0 for name in shift_map}
    default_alphabet_name = next(iter(shift_map))
    transformed_chars = []
    for char in text:
        alphabet = identify_alphabet(char)
        if not alphabet:
            transformed_chars.append(char)
            continue
        alphabet_name = alphabet.name
        if alphabet_name not in shift_map:
            # Якщо символ належить абетці без налаштованих зсувів, користуємося першою доступною.
            alphabet_name = default_alphabet_name
        shifts = shift_map[alphabet_name]
        offset = shifts[counters[alphabet_name] % len(shifts)]
        counters[alphabet_name] += 1
        effective_shift = offset % len(alphabet.uppercase)
        if direction < 0:
            effective_shift = -effective_shift
        transformed_chars.append(alphabet.shift(char, effective_shift))
    return "".join(transformed_chars)


def encrypt(text: str, key_info: KeyInfo) -> str:
    """Шифрує текст за підготовленим ключем Віженера."""
    return _transform(text, key_info, direction=1)


def decrypt(text: str, key_info: KeyInfo) -> str:
    """Розшифровує текст за підготовленим ключем Віженера."""
    return _transform(text, key_info, direction=-1)
