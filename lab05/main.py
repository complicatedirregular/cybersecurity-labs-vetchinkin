import base64
import hashlib
import time

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from cryptography.fernet import Fernet, InvalidToken
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# ══════════════════════════════════════════════════════════════════════════════
#                              КОНСТАНТИ ТА СТИЛІ
# ══════════════════════════════════════════════════════════════════════════════

BANNER = r"""
   _____ _____ _____ _   _ ____  _____   __  __    _    ___ _     
  / ____| ____/ ____| | | |  _ \| ____| |  \/  |  / \  |_ _| |    
  \___ \|  _|| |    | | | | |_) |  _|   | |\/| | / _ \  | || |    
   ___) | |__| |____| |_| |  _ <| |___  | |  | |/ ___ \ | || |___ 
  |____/|_____\_____|\___/|_| \_\_____| |_|  |_/_/   \_\___|_____|
                                                                  
        🔒 Симулятор захищеного листування 🔒
"""

CUSTOM_THEME = Theme({
    "title": "bold white on blue",
    "subtitle": "bold cyan",
    "accent": "bold magenta",
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bright_cyan",
    "key": "bold bright_yellow on grey23",
    "cipher": "dim cyan",
    "sender": "bold bright_green",
    "receiver": "bold bright_blue",
    "highlight": "bold white on dark_green",
})


# ══════════════════════════════════════════════════════════════════════════════
#                              МОДЕЛІ ДАНИХ
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class UserCredentials:
    """Облікові дані користувача для генерації ключа."""
    full_name: str
    date_of_birth: str

    def generate_key(self) -> bytes:
        """
        Генерує симетричний ключ із персональних даних.
        
        Алгоритм:
            1. Конкатенація ПІБ і дати народження
            2. Хешування SHA-256 → 32 байти
            3. Кодування в URL-безпечний Base64 (для Fernet)
        """
        combined = f"{self.full_name}{self.date_of_birth}".encode("utf-8")
        digest = hashlib.sha256(combined).digest()
        return base64.urlsafe_b64encode(digest)


@dataclass
class EncryptedPackage:
    """Зашифрований пакет даних."""
    message_cipher: str
    attachment_cipher: Optional[str] = None
    original_filename: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
#                           КЛАС КРИПТОГРАФІЇ
# ══════════════════════════════════════════════════════════════════════════════

class CryptoEngine:
    """Механізм шифрування/дешифрування на основі Fernet."""

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)
        self._key = key

    @property
    def key_display(self) -> str:
        """Повертає ключ у читабельному форматі."""
        return self._key.decode("utf-8")

    def encrypt_text(self, plaintext: str) -> str:
        """Шифрує текстове повідомлення."""
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt_text(self, ciphertext: str) -> Tuple[bool, str]:
        """Розшифровує текстове повідомлення."""
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return True, plaintext.decode("utf-8")
        except InvalidToken:
            return False, "❌ Невірний ключ або пошкоджені дані"

    def encrypt_file(self, filepath: Path) -> Tuple[bool, str]:
        """Шифрує файл."""
        try:
            data = filepath.read_bytes()
            token = self._fernet.encrypt(data)
            return True, token.decode("utf-8")
        except OSError as e:
            return False, f"❌ Помилка читання файлу: {e}"

    def decrypt_file(self, ciphertext: str, destination: Path) -> Tuple[bool, str]:
        """Розшифровує файл та зберігає його."""
        try:
            data = self._fernet.decrypt(ciphertext.encode("utf-8"))
            destination.write_bytes(data)
            return True, f"✅ Файл збережено: {destination}"
        except InvalidToken:
            return False, "❌ Невірний ключ або пошкоджені дані"
        except OSError as e:
            return False, f"❌ Помилка збереження: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#                          КЛАС ІНТЕРФЕЙСУ
# ══════════════════════════════════════════════════════════════════════════════

class SecureMailUI:
    """Інтерфейс користувача для симулятора."""

    def __init__(self):
        self.console = Console(theme=CUSTOM_THEME)

    def show_banner(self) -> None:
        """Відображає привітальний банер."""
        banner_text = Text(BANNER, style="bold cyan")
        self.console.print(Align.center(banner_text))
        self.console.print()

    def show_info_panel(self) -> None:
        """Показує інформаційну панель про принцип роботи."""
        info_table = Table(
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            expand=True,
        )
        info_table.add_column(justify="center")
        info_table.add_row("[info]🔑 Ключ генерується з ПІБ + дати народження[/info]")
        info_table.add_row("[info]🔒 Алгоритм: SHA-256 → Fernet (AES-128-CBC)[/info]")
        info_table.add_row("[info]📎 Підтримка текстових повідомлень та файлів[/info]")

        panel = Panel(
            info_table,
            title="[title] ℹ️  Як це працює [/title]",
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def section_header(self, text: str, style: str = "cyan") -> None:
        """Створює заголовок секції."""
        self.console.print()
        self.console.rule(f"[bold {style}]{text}[/bold {style}]", style=style)
        self.console.print()

    def ask_credentials(self, role: str, role_style: str) -> UserCredentials:
        """Запитує облікові дані користувача."""
        role_panel = Panel(
            f"[{role_style}]Введіть дані для {role}[/{role_style}]",
            box=box.ROUNDED,
            border_style=role_style.split()[-1] if " " in role_style else role_style,
        )
        self.console.print(role_panel)

        full_name = Prompt.ask("  [bold]📝 Повне ім'я (ПІБ)[/bold]")
        dob = self._ask_date("  [bold]📅 Дата народження[/bold]")

        return UserCredentials(full_name=full_name, date_of_birth=dob)

    def _ask_date(self, prompt_text: str) -> str:
        """Запитує та валідує дату."""
        while True:
            dob_input = Prompt.ask(f"{prompt_text} [dim](ДД.ММ.РРРР)[/dim]").strip()
            try:
                parsed = datetime.strptime(dob_input, "%d.%m.%Y")
                return parsed.strftime("%d.%m.%Y")
            except ValueError:
                self.console.print(
                    "     [error]⚠️  Невірний формат! Використовуйте ДД.ММ.РРРР[/error]"
                )

    def ask_message(self) -> str:
        """Запитує текст повідомлення."""
        return Prompt.ask("  [bold]✉️  Текст листа[/bold]")

    def show_key(self, key: str) -> None:
        """Відображає згенерований ключ."""
        key_display = Text()
        key_display.append("🔑 ", style="bold yellow")
        key_display.append(key, style="key")

        panel = Panel(
            Align.center(key_display),
            title="[subtitle] Згенерований ключ [/subtitle]",
            border_style="yellow",
            box=box.HEAVY,
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_cipher(self, ciphertext: str, title: str = "Зашифроване повідомлення") -> None:
        """Відображає шифротекст."""
        # Розбиваємо довгий шифротекст на рядки
        wrapped = "\n".join(
            ciphertext[i:i+70] for i in range(0, len(ciphertext), 70)
        )

        panel = Panel(
            f"[cipher]{wrapped}[/cipher]",
            title=f"[accent] 🔐 {title} [/accent]",
            border_style="magenta",
            box=box.DOUBLE,
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_decrypted(self, plaintext: str) -> None:
        """Відображає розшифроване повідомлення."""
        panel = Panel(
            f"[success]{plaintext}[/success]",
            title="[highlight] ✅ Розшифровано успішно! [/highlight]",
            border_style="green",
            box=box.HEAVY,
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_error(self, message: str, title: str = "Помилка") -> None:
        """Відображає повідомлення про помилку."""
        panel = Panel(
            f"[error]{message}[/error]",
            title=f"[error] ❌ {title} [/error]",
            border_style="red",
            box=box.HEAVY,
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_success(self, message: str, title: str = "Успіх") -> None:
        """Відображає повідомлення про успіх."""
        panel = Panel(
            f"[success]{message}[/success]",
            title=f"[success] ✅ {title} [/success]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_warning(self, message: str) -> None:
        """Відображає попередження."""
        panel = Panel(
            f"[warning]{message}[/warning]",
            title="[warning] ⚠️  Увага [/warning]",
            border_style="yellow",
            box=box.ROUNDED,
        )
        self.console.print(panel)

    def progress_operation(self, description: str, duration: float = 0.5) -> None:
        """Показує анімований прогрес операції."""
        with Progress(
            SpinnerColumn("dots12", style="cyan"),
            TextColumn("[info]{task.description}[/info]"),
            BarColumn(bar_width=30, style="cyan", complete_style="green"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task(description, total=100)
            for _ in range(100):
                time.sleep(duration / 100)
                progress.advance(task)

    def ask_attachment(self) -> Optional[Path]:
        """Запитує про вкладення."""
        if Confirm.ask("  [bold]📎 Додати файл-вкладення?[/bold]", default=False):
            path_str = Prompt.ask("     [bold]Шлях до файлу[/bold]")
            return Path(path_str).expanduser()
        return None

    def ask_save_path(self) -> Path:
        """Запитує шлях для збереження."""
        path_str = Prompt.ask("  [bold]💾 Куди зберегти файл?[/bold]")
        return Path(path_str).expanduser()

    def show_comparison(self, sender: UserCredentials, receiver: UserCredentials) -> None:
        """Показує порівняння даних відправника та отримувача."""
        table = Table(
            title="[subtitle]Порівняння введених даних[/subtitle]",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold white",
            show_lines=True,
        )
        table.add_column("Параметр", style="bold")
        table.add_column("Відправник (Аліса)", style="sender")
        table.add_column("Отримувач (Боб)", style="receiver")

        name_match = "✅" if sender.full_name == receiver.full_name else "❌"
        dob_match = "✅" if sender.date_of_birth == receiver.date_of_birth else "❌"

        table.add_row("ПІБ", sender.full_name, f"{receiver.full_name} {name_match}")
        table.add_row(
            "Дата народження",
            sender.date_of_birth,
            f"{receiver.date_of_birth} {dob_match}",
        )

        self.console.print()
        self.console.print(table)
        self.console.print()


# ══════════════════════════════════════════════════════════════════════════════
#                              ГОЛОВНА ЛОГІКА
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Точка входу в програму."""
    ui = SecureMailUI()

    try:
        # Привітання
        ui.show_banner()
        ui.show_info_panel()

        # ─────────────────────────────────────────────────────────────────────
        # ЕТАП 1: Відправник (Аліса)
        # ─────────────────────────────────────────────────────────────────────
        ui.section_header("👩 ВІДПРАВНИК (Аліса)", "green")

        sender = ui.ask_credentials("відправника", "sender")
        message = ui.ask_message()

        # Генерація ключа та шифрування
        ui.progress_operation("🔑 Генерація ключа...")
        crypto = CryptoEngine(sender.generate_key())
        ui.show_key(crypto.key_display)

        ui.progress_operation("🔒 Шифрування повідомлення...")
        cipher_message = crypto.encrypt_text(message)
        ui.show_cipher(cipher_message, "Лист для Боба")

        # Вкладення
        package = EncryptedPackage(message_cipher=cipher_message)
        attachment_path = ui.ask_attachment()

        if attachment_path:
            ui.progress_operation("📎 Шифрування вкладення...")
            success, result = crypto.encrypt_file(attachment_path)
            if success:
                package.attachment_cipher = result
                package.original_filename = attachment_path.name
                ui.show_success(
                    f"Файл '{attachment_path.name}' зашифровано",
                    "Вкладення готове",
                )
            else:
                ui.show_error(result, "Помилка вкладення")

        # ─────────────────────────────────────────────────────────────────────
        # ЕТАП 2: Отримувач (Боб)
        # ─────────────────────────────────────────────────────────────────────
        ui.section_header("👨 ОТРИМУВАЧ (Боб)", "blue")

        receiver = ui.ask_credentials("отримувача", "receiver")

        # Порівняння даних
        ui.show_comparison(sender, receiver)

        # Спроба розшифрування
        ui.progress_operation("🔓 Спроба розшифрування...")
        receiver_crypto = CryptoEngine(receiver.generate_key())

        success, result = receiver_crypto.decrypt_text(package.message_cipher)

        if success:
            ui.show_decrypted(result)
        else:
            ui.show_error(result, "Розшифрування не вдалося")

        # Розшифрування вкладення
        if package.attachment_cipher:
            ui.section_header("📎 РОЗШИФРУВАННЯ ВКЛАДЕННЯ", "magenta")

            save_path = ui.ask_save_path()
            ui.progress_operation("💾 Збереження файлу...")

            ok, msg = receiver_crypto.decrypt_file(package.attachment_cipher, save_path)
            if ok:
                ui.show_success(msg, "Вкладення збережено")
            else:
                ui.show_error(msg, "Помилка розшифрування вкладення")
        else:
            ui.console.print()
            ui.show_warning("Вкладення не було передано")

        # Завершення
        ui.console.print()
        ui.console.rule("[bold green]✨ Симуляція завершена ✨[/bold green]", style="green")
        ui.console.print()

    except KeyboardInterrupt:
        ui.console.print()
        ui.show_warning("Програму перервано користувачем")
    except Exception as e:
        ui.show_error(f"Непередбачена помилка: {e}", "Критична помилка")
        raise


if __name__ == "__main__":
    main()
