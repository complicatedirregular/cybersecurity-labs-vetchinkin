from __future__ import annotations

import hashlib
import time

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import NamedTuple
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


# ═══════════════════════════════════════════════════════════════════════════════
# КОНСТАНТИ
# ═══════════════════════════════════════════════════════════════════════════════

# Велике просте число Мерсенна (2^127 - 1) для модульної арифметики.
MERSENNE_PRIME = 170141183460469231731687303715884105727

SIGNATURE_SUFFIX = ".sig"
PRIVATE_KEY_FILE = "private.key"
PUBLIC_KEY_FILE = "public.key"

# Секретний сід для генерації ключів (у реальному застосуванні — безпечне сховище).
SECRET_SEED = "SECURE_RANDOM_SEED_2025"


# ═══════════════════════════════════════════════════════════════════════════════
# СТИЛІ ТА ТЕМИ
# ═══════════════════════════════════════════════════════════════════════════════

class Theme:
    """Централізовані стилі для консольного інтерфейсу."""
    
    PRIMARY = "bold cyan"
    SUCCESS = "bold green"
    WARNING = "bold yellow"
    ERROR = "bold red"
    ACCENT = "magenta"
    MUTED = "dim white"
    INFO = "blue"
    
    BORDER_SUCCESS = "green"
    BORDER_ERROR = "red"
    BORDER_WARNING = "yellow"
    BORDER_PRIMARY = "cyan"


class Icons:
    """Іконки для візуального оформлення."""
    
    KEY = "🔑"
    LOCK = "🔒"
    UNLOCK = "🔓"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    DOC = "📄"
    PEN = "✍️"
    SHIELD = "🛡️"
    ATTACK = "💥"
    USER = "👤"
    CALENDAR = "📅"


# ═══════════════════════════════════════════════════════════════════════════════
# МОДЕЛІ ДАНИХ
# ═══════════════════════════════════════════════════════════════════════════════

class KeyPair(NamedTuple):
    """Пара криптографічних ключів."""
    private: int
    public: int


@dataclass
class SignatureResult:
    """Результат операції підпису."""
    document_path: Path
    signature_path: Path
    document_hash: int
    signature_value: int


class VerificationStatus(Enum):
    """Статус верифікації підпису."""
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Результат верифікації підпису."""
    status: VerificationStatus
    expected_hash: int
    actual_hash: int
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# КРИПТОГРАФІЧНІ ФУНКЦІЇ
# ═══════════════════════════════════════════════════════════════════════════════

def compute_sha256_int(data: bytes) -> int:
    """
    Обчислює SHA-256 хеш даних та повертає його як ціле число.
    
    Args:
        data: Байтові дані для хешування.
        
    Returns:
        SHA-256 хеш як велике ціле число.
    """
    digest = hashlib.sha256(data).digest()
    return int.from_bytes(digest, byteorder="big")


def generate_key_pair(name: str, birthdate: str) -> KeyPair:
    """
    Генерує пару ключів на основі персональних даних.
    
    Приватний ключ виводиться з SHA-256 хешу комбінації імені,
    дати народження та секретного сіду. Публічний ключ є
    мультиплікативною оберненою приватного по модулю простого числа.
    
    Args:
        name: Повне ім'я користувача.
        birthdate: Дата народження у форматі ДД.ММ.РРРР.
        
    Returns:
        KeyPair з приватним та публічним ключами.
    """
    seed_material = f"{name}|{birthdate}|{SECRET_SEED}".encode("utf-8")
    private_key = compute_sha256_int(seed_material) % MERSENNE_PRIME
    
    # Гарантуємо, що приватний ключ ≠ 0 для існування оберненого.
    if private_key == 0:
        private_key = 1
    
    # Публічний ключ: (private * public) ≡ 1 (mod MERSENNE_PRIME)
    public_key = pow(private_key, -1, MERSENNE_PRIME)
    
    return KeyPair(private=private_key, public=public_key)


def save_keys_to_files(keys: KeyPair, directory: Path | None = None) -> tuple[Path, Path]:
    """
    Зберігає ключі у файли.
    
    Args:
        keys: Пара ключів для збереження.
        directory: Директорія для збереження (за замовчуванням — поточна).
        
    Returns:
        Кортеж шляхів до файлів приватного та публічного ключів.
    """
    base = directory or Path.cwd()
    
    private_path = base / PRIVATE_KEY_FILE
    public_path = base / PUBLIC_KEY_FILE
    
    private_path.write_text(str(keys.private), encoding="utf-8")
    public_path.write_text(str(keys.public), encoding="utf-8")
    
    return private_path, public_path


def create_signature(document_path: Path, private_key: int) -> SignatureResult:
    """
    Створює цифровий підпис для документа.
    
    Підпис обчислюється як: (hash(document) × private_key) mod MERSENNE_PRIME.
    
    Args:
        document_path: Шлях до документа для підпису.
        private_key: Приватний ключ для підпису.
        
    Returns:
        SignatureResult з деталями підпису.
        
    Raises:
        FileNotFoundError: Якщо документ не існує.
    """
    if not document_path.exists():
        raise FileNotFoundError(f"Документ не знайдено: {document_path}")
    
    document_bytes = document_path.read_bytes()
    document_hash = compute_sha256_int(document_bytes) % MERSENNE_PRIME
    signature_value = (document_hash * private_key) % MERSENNE_PRIME
    
    signature_path = document_path.with_suffix(document_path.suffix + SIGNATURE_SUFFIX)
    signature_path.write_text(str(signature_value), encoding="utf-8")
    
    return SignatureResult(
        document_path=document_path,
        signature_path=signature_path,
        document_hash=document_hash,
        signature_value=signature_value,
    )


def verify_signature(
    document_path: Path,
    signature_path: Path,
    public_key: int,
) -> VerificationResult:
    """
    Верифікує цифровий підпис документа.
    
    Перевірка: (signature × public_key) mod MERSENNE_PRIME == hash(document).
    
    Args:
        document_path: Шлях до документа.
        signature_path: Шлях до файлу підпису.
        public_key: Публічний ключ для верифікації.
        
    Returns:
        VerificationResult зі статусом та деталями.
    """
    try:
        if not document_path.exists():
            return VerificationResult(
                status=VerificationStatus.ERROR,
                expected_hash=0,
                actual_hash=0,
                message=f"Документ не знайдено: {document_path}",
            )
        
        if not signature_path.exists():
            return VerificationResult(
                status=VerificationStatus.ERROR,
                expected_hash=0,
                actual_hash=0,
                message=f"Файл підпису не знайдено: {signature_path}",
            )
        
        # Обчислюємо поточний хеш документа.
        current_hash = compute_sha256_int(document_path.read_bytes()) % MERSENNE_PRIME
        
        # Читаємо та декриптуємо підпис.
        signature_value = int(signature_path.read_text(encoding="utf-8").strip())
        decrypted_hash = (signature_value * public_key) % MERSENNE_PRIME
        
        if current_hash == decrypted_hash:
            return VerificationResult(
                status=VerificationStatus.VALID,
                expected_hash=decrypted_hash,
                actual_hash=current_hash,
                message="Підпис дійсний: документ автентичний і не змінений.",
            )
        else:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                expected_hash=decrypted_hash,
                actual_hash=current_hash,
                message="Підпис недійсний: документ було змінено.",
            )
            
    except ValueError as e:
        return VerificationResult(
            status=VerificationStatus.ERROR,
            expected_hash=0,
            actual_hash=0,
            message=f"Помилка читання підпису: {e}",
        )


def simulate_tampering(document_path: Path) -> bytes:
    """
    Симулює атаку на документ шляхом зміни одного біта.
    
    Args:
        document_path: Шлях до документа.
        
    Returns:
        Оригінальні байти документа (для можливого відновлення).
    """
    original_bytes = document_path.read_bytes()
    
    if original_bytes:
        tampered = bytearray(original_bytes)
        tampered[0] ^= 0b00000001  # Інвертуємо молодший біт першого байта.
        document_path.write_bytes(tampered)
    
    return original_bytes


# ═══════════════════════════════════════════════════════════════════════════════
# ІНТЕРФЕЙС КОРИСТУВАЧА
# ═══════════════════════════════════════════════════════════════════════════════

class SignatureUI:
    """Клас для управління консольним інтерфейсом."""
    
    def __init__(self) -> None:
        self.console = Console()
    
    def show_banner(self) -> None:
        """Виводить привітальний банер програми."""
        banner_text = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🔐  ПЕРСОНАЛЬНИЙ ЦИФРОВИЙ ПІДПИС  🔐                        ║
║                                                               ║
║   Демонстрація цілісності та автентичності документів         ║
║   за допомогою асиметричної криптографії                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """.strip()
        
        self.console.print()
        self.console.print(
            Panel(
                Align.center(Text(banner_text, style=Theme.PRIMARY)),
                border_style=Theme.BORDER_PRIMARY,
                padding=(1, 2),
            )
        )
        self.console.print()
    
    def show_section(self, title: str, icon: str = "") -> None:
        """Виводить заголовок секції."""
        self.console.print()
        self.console.print(Rule(f" {icon} {title} ", style=Theme.ACCENT))
        self.console.print()
    
    def prompt_nonempty(self, message: str, icon: str = "") -> str:
        """Запитує введення, поки не буде отримано непорожнє значення."""
        prompt_text = f"{icon} {message}" if icon else message
        
        while True:
            value = Prompt.ask(f"[{Theme.PRIMARY}]{prompt_text}[/]").strip()
            if value:
                return value
            self.console.print(
                f"  [{Theme.ERROR}]Поле не може бути порожнім. Спробуйте ще раз.[/]"
            )
    
    def prompt_birthdate(self) -> str:
        """Запитує дату народження з валідацією формату."""
        while True:
            date_str = Prompt.ask(
                f"[{Theme.PRIMARY}]{Icons.CALENDAR} Дата народження (ДД.ММ.РРРР)[/]"
            ).strip()
            
            try:
                parsed = datetime.strptime(date_str, "%d.%m.%Y")
                # Перевірка на реалістичність дати.
                if parsed.year < 1900 or parsed > datetime.now():
                    self.console.print(
                        f"  [{Theme.WARNING}]Введіть коректну дату народження.[/]"
                    )
                    continue
                return date_str
            except ValueError:
                self.console.print(
                    f"  [{Theme.ERROR}]Неправильний формат. "
                    f"Використовуйте ДД.ММ.РРРР (наприклад, 15.03.1990).[/]"
                )
    
    def show_progress_task(self, description: str, duration: float = 0.5) -> None:
        """Показує анімований індикатор виконання завдання."""
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn(f"[{Theme.INFO}]{description}[/]"),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task("", total=None)
            time.sleep(duration)
    
    def show_keys_info(self, keys: KeyPair, user_name: str) -> None:
        """Виводить інформацію про згенеровані ключі."""
        # Скорочуємо ключі для відображення.
        private_short = f"{str(keys.private)[:20]}...{str(keys.private)[-10:]}"
        public_short = f"{str(keys.public)[:20]}...{str(keys.public)[-10:]}"
        
        table = Table(
            show_header=True,
            header_style=Theme.PRIMARY,
            border_style=Theme.MUTED,
            title=f"{Icons.KEY} Ключі для {user_name}",
            title_style=Theme.SUCCESS,
        )
        
        table.add_column("Тип ключа", style=Theme.ACCENT, width=20)
        table.add_column("Значення (скорочено)", style="white")
        table.add_column("Файл", style=Theme.INFO)
        
        table.add_row(
            f"{Icons.LOCK} Приватний",
            private_short,
            PRIVATE_KEY_FILE,
        )
        table.add_row(
            f"{Icons.UNLOCK} Публічний",
            public_short,
            PUBLIC_KEY_FILE,
        )
        
        self.console.print(table)
    
    def show_signature_info(self, result: SignatureResult) -> None:
        """Виводить інформацію про створений підпис."""
        sig_short = f"{str(result.signature_value)[:30]}..."
        
        content = Group(
            Text(f"{Icons.DOC} Документ: ", style=Theme.MUTED) + 
            Text(str(result.document_path), style="white"),
            Text(f"{Icons.PEN} Підпис:   ", style=Theme.MUTED) + 
            Text(str(result.signature_path), style="white"),
            Text(f"{Icons.SHIELD} Значення: ", style=Theme.MUTED) + 
            Text(sig_short, style=Theme.INFO),
        )
        
        self.console.print(
            Panel(
                content,
                title=f"{Icons.CHECK} Документ успішно підписано",
                title_align="left",
                border_style=Theme.BORDER_SUCCESS,
                padding=(1, 2),
            )
        )
    
    def show_verification_result(
        self,
        result: VerificationResult,
        title: str = "Результат верифікації",
    ) -> None:
        """Виводить результат верифікації підпису."""
        status_config = {
            VerificationStatus.VALID: (
                Icons.CHECK,
                Theme.SUCCESS,
                Theme.BORDER_SUCCESS,
            ),
            VerificationStatus.INVALID: (
                Icons.CROSS,
                Theme.ERROR,
                Theme.BORDER_ERROR,
            ),
            VerificationStatus.ERROR: (
                Icons.WARNING,
                Theme.WARNING,
                Theme.BORDER_WARNING,
            ),
        }
        
        icon, style, border = status_config[result.status]
        
        self.console.print(
            Panel(
                Text(f"{icon} {result.message}", style=style),
                title=title,
                title_align="left",
                border_style=border,
                padding=(0, 2),
            )
        )
    
    def show_attack_simulation(self) -> None:
        """Виводить повідомлення про симуляцію атаки."""
        self.console.print()
        self.console.print(
            Panel(
                Text(
                    f"{Icons.ATTACK} СИМУЛЯЦІЯ АТАКИ\n\n"
                    "Змінено 1 біт у документі для демонстрації "
                    "виявлення порушення цілісності.",
                    style=Theme.WARNING,
                ),
                border_style=Theme.BORDER_WARNING,
                padding=(1, 2),
            )
        )
    
    def show_summary(
        self,
        initial_result: VerificationResult,
        tampered_result: VerificationResult,
    ) -> None:
        """Виводить підсумкову таблицю результатів."""
        self.console.print()
        
        table = Table(
            title=f"{Icons.SHIELD} ПІДСУМОК ДЕМОНСТРАЦІЇ",
            title_style=Theme.PRIMARY,
            show_header=True,
            header_style=Theme.PRIMARY,
            border_style=Theme.BORDER_PRIMARY,
            show_lines=True,
            padding=(0, 2),
        )
        
        table.add_column("Етап", style=Theme.ACCENT, width=25)
        table.add_column("Статус", justify="center", width=15)
        table.add_column("Опис", style="white", width=35)
        
        # Початкова верифікація.
        initial_status = (
            f"[{Theme.SUCCESS}]{Icons.CHECK} ДІЙСНИЙ[/]"
            if initial_result.status == VerificationStatus.VALID
            else f"[{Theme.ERROR}]{Icons.CROSS} НЕДІЙСНИЙ[/]"
        )
        table.add_row(
            "Оригінальний документ",
            initial_status,
            "Підпис відповідає документу",
        )
        
        # Після атаки.
        tampered_status = (
            f"[{Theme.ERROR}]{Icons.CROSS} НЕДІЙСНИЙ[/]"
            if tampered_result.status == VerificationStatus.INVALID
            else f"[{Theme.WARNING}]{Icons.WARNING} ДІЙСНИЙ[/]"
        )
        expected_desc = (
            "Зміну виявлено (очікувано)"
            if tampered_result.status == VerificationStatus.INVALID
            else "Зміну НЕ виявлено (неочікувано!)"
        )
        table.add_row(
            "Після модифікації",
            tampered_status,
            expected_desc,
        )
        
        self.console.print(table)
        
        # Висновок.
        if (
            initial_result.status == VerificationStatus.VALID
            and tampered_result.status == VerificationStatus.INVALID
        ):
            conclusion = (
                f"{Icons.CHECK} Демонстрація успішна: система коректно виявляє "
                "будь-які зміни в підписаному документі."
            )
            conclusion_style = Theme.SUCCESS
        else:
            conclusion = (
                f"{Icons.WARNING} Увага: результати відрізняються від очікуваних."
            )
            conclusion_style = Theme.WARNING
        
        self.console.print()
        self.console.print(
            Panel(
                Text(conclusion, style=conclusion_style, justify="center"),
                border_style=Theme.BORDER_PRIMARY,
            )
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Головна функція демонстрації цифрового підпису."""
    ui = SignatureUI()
    
    # Привітання.
    ui.show_banner()
    
    # ─── КРОК 1: Збір даних користувача ───
    ui.show_section("ІДЕНТИФІКАЦІЯ КОРИСТУВАЧА", Icons.USER)
    
    user_name = ui.prompt_nonempty("Повне ім'я", Icons.USER)
    user_birthdate = ui.prompt_birthdate()
    
    # ─── КРОК 2: Створення контракту ───
    ui.show_section("СТВОРЕННЯ ДОКУМЕНТА", Icons.DOC)
    
    contract_path_str = ui.prompt_nonempty(
        "Шлях для збереження контракту",
        Icons.DOC,
    )
    contract_path = Path(contract_path_str).expanduser()
    
    contract_text = ui.prompt_nonempty("Текст контракту", Icons.PEN)
    contract_path.write_text(contract_text, encoding="utf-8")
    
    ui.console.print(
        f"  [{Theme.SUCCESS}]{Icons.CHECK} Контракт збережено: {contract_path}[/]"
    )
    
    # ─── КРОК 3: Генерація ключів ───
    ui.show_section("ГЕНЕРАЦІЯ КЛЮЧІВ", Icons.KEY)
    
    ui.show_progress_task("Генерація криптографічних ключів...")
    keys = generate_key_pair(user_name, user_birthdate)
    save_keys_to_files(keys)
    
    ui.show_keys_info(keys, user_name)
    
    # ─── КРОК 4: Підписання документа ───
    ui.show_section("ПІДПИСАННЯ ДОКУМЕНТА", Icons.PEN)
    
    ui.show_progress_task("Створення цифрового підпису...")
    signature_result = create_signature(contract_path, keys.private)
    
    ui.show_signature_info(signature_result)
    
    # ─── КРОК 5: Верифікація оригіналу ───
    ui.show_section("ВЕРИФІКАЦІЯ ОРИГІНАЛУ", Icons.SHIELD)
    
    ui.show_progress_task("Перевірка підпису...")
    initial_verification = verify_signature(
        contract_path,
        signature_result.signature_path,
        keys.public,
    )
    
    ui.show_verification_result(initial_verification, "Перевірка оригінального документа")
    
    # ─── КРОК 6: Симуляція атаки ───
    ui.show_section("СИМУЛЯЦІЯ АТАКИ", Icons.ATTACK)
    
    simulate_tampering(contract_path)
    ui.show_attack_simulation()
    
    # ─── КРОК 7: Верифікація після атаки ───
    ui.show_section("ВЕРИФІКАЦІЯ ПІСЛЯ АТАКИ", Icons.SHIELD)
    
    ui.show_progress_task("Перевірка підпису модифікованого документа...")
    tampered_verification = verify_signature(
        contract_path,
        signature_result.signature_path,
        keys.public,
    )
    
    ui.show_verification_result(tampered_verification, "Перевірка після модифікації")
    
    # ─── ПІДСУМОК ───
    ui.show_section("РЕЗУЛЬТАТИ", Icons.SHIELD)
    ui.show_summary(initial_verification, tampered_verification)
    
    ui.console.print()


if __name__ == "__main__":
    main()
