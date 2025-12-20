import hashlib
import base64
from dataclasses import dataclass
from cryptography.fernet import Fernet

# --- ЧАСТИНА 1: ЦИФРОВИЙ ПІДПИС (з ЛР4) ---

# Велике просте число Мерсенна (2^127 - 1)
MERSENNE_PRIME = 170141183460469231731687303715884105727
SECRET_SEED = "LAB7_SECURE_SEED"

@dataclass
class KeyPair:
    private: int
    public: int

def compute_sha256_int(data: bytes) -> int:
    """Обчислює SHA-256 хеш даних як ціле число."""
    digest = hashlib.sha256(data).digest()
    return int.from_bytes(digest, byteorder="big")

def generate_rsa_keys(name: str, birthdate: str) -> KeyPair:
    """Генерує пару ключів (RSA-подібну) на основі даних користувача."""
    seed_material = f"{name}|{birthdate}|{SECRET_SEED}".encode("utf-8")
    private_key = compute_sha256_int(seed_material) % MERSENNE_PRIME
    
    if private_key == 0:
        private_key = 1
    
    # Публічний ключ: (private * public) ≡ 1 (mod MERSENNE_PRIME)
    public_key = pow(private_key, -1, MERSENNE_PRIME)
    return KeyPair(private=private_key, public=public_key)

def sign_data(data: bytes, private_key: int) -> str:
    """Створює цифровий підпис."""
    data_hash = compute_sha256_int(data) % MERSENNE_PRIME
    signature_value = (data_hash * private_key) % MERSENNE_PRIME
    return str(signature_value)

def verify_signature_data(data: bytes, signature_str: str, public_key: int) -> bool:
    """Перевіряє цифровий підпис."""
    try:
        signature_value = int(signature_str)
        current_hash = compute_sha256_int(data) % MERSENNE_PRIME
        
        # Декриптуємо підпис
        decrypted_hash = (signature_value * public_key) % MERSENNE_PRIME
        
        return current_hash == decrypted_hash
    except ValueError:
        return False

# --- ЧАСТИНА 2: ШИФРУВАННЯ AES (з ЛР5) ---

class AESCipher:
    def __init__(self, full_name: str, date_of_birth: str):
        # Генерація ключа з персональних даних
        key_material = f"{full_name}{date_of_birth}".encode("utf-8")
        digest = hashlib.sha256(key_material).digest()
        self.key = base64.urlsafe_b64encode(digest)
        self.fernet = Fernet(self.key)

    def encrypt(self, plaintext: str) -> str:
        """Шифрує рядок."""
        token = self.fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Розшифровує рядок."""
        token = self.fernet.decrypt(ciphertext.encode("utf-8"))
        return token.decode("utf-8")