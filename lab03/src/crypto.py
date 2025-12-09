from __future__ import annotations

import hashlib
import struct

# Магічний заголовок для ідентифікації вбудованих даних
HEADER_MAGIC: bytes = b"LSBMSG1"
HEADER_SIZE: int = len(HEADER_MAGIC) + 4  # magic + 4 bytes for length


def derive_key_stream(password: str, length: int) -> bytes:
    """
    Генерує потік ключів на основі пароля.
    
    Використовує SHA-256 з лічильником для створення
    криптографічно стійкого потоку байтів.
    
    Args:
        password: Пароль для генерації потоку
        length: Необхідна довжина потоку в байтах
        
    Returns:
        Потік байтів заданої довжини
    """
    seed = password.encode("utf-8")
    stream = bytearray()
    counter = 0
    
    while len(stream) < length:
        counter_bytes = counter.to_bytes(4, "big")
        digest = hashlib.sha256(seed + counter_bytes).digest()
        stream.extend(digest)
        counter += 1
    
    return bytes(stream[:length])


def xor_encrypt(data: bytes, password: str | None) -> bytes:
    """
    Шифрує/дешифрує дані за допомогою XOR з потоком ключів.
    
    Args:
        data: Дані для шифрування/дешифрування
        password: Пароль (None = без шифрування)
        
    Returns:
        Зашифровані/розшифровані дані
    """
    if not password:
        return data
    
    key_stream = derive_key_stream(password, len(data))
    return bytes(a ^ b for a, b in zip(data, key_stream))


def build_payload(message: str, password: str | None) -> bytes:
    """
    Формує корисне навантаження для вбудовування.
    
    Структура: [MAGIC][LENGTH:4 bytes][ENCRYPTED_MESSAGE]
    
    Args:
        message: Текстове повідомлення
        password: Пароль для шифрування (опційно)
        
    Returns:
        Готовий до вбудовування байтовий масив
    """
    body = message.encode("utf-8")
    encrypted = xor_encrypt(body, password)
    length_bytes = struct.pack(">I", len(encrypted))
    
    return HEADER_MAGIC + length_bytes + encrypted


def parse_header(header_bytes: bytes) -> int:
    """
    Парсить заголовок і повертає довжину повідомлення.
    
    Args:
        header_bytes: Байти заголовка (мінімум HEADER_SIZE)
        
    Returns:
        Довжина зашифрованого повідомлення
        
    Raises:
        ValueError: Якщо магічний заголовок не збігається
    """
    magic = header_bytes[:len(HEADER_MAGIC)]
    
    if magic != HEADER_MAGIC:
        raise ValueError("Вбудований корисний вантаж не виявлено.")
    
    return struct.unpack(">I", header_bytes[len(HEADER_MAGIC):HEADER_SIZE])[0]


def decrypt_payload(payload: bytes, password: str | None) -> str:
    """
    Розшифровує корисне навантаження.
    
    Args:
        payload: Зашифровані байти
        password: Пароль для дешифрування
        
    Returns:
        Розшифроване текстове повідомлення
    """
    decrypted = xor_encrypt(payload, password)
    return decrypted.decode("utf-8")
