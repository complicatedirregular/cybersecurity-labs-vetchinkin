from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from encryption import caesar, vigenere
from encryption.analysis import ComparativeReport, build_report, vowel_ratio
from encryption.alphabet import sanitize_text
from encryption.keygen import KeyMaterial, derive_keys

DEFAULT_TEXT = "Безпека програм та даних – важлива дисципліна"
DEFAULT_SURNAME = "Ветчінкін"
DEFAULT_BIRTHDATE = "13.05.2004"
OPERATION_LABELS = {"encrypt": "Шифрування", "decrypt": "Розшифрування"}


def build_bruteforce_preview(
    ciphertext: str, limit: Optional[int] = None, highlight_shift: Optional[int] = None
) -> List[Tuple[int, str, float, bool]]:
    attempts: List[Tuple[int, str, float]] = [
        (shift, suggestion, vowel_ratio(suggestion))
        for shift, suggestion in caesar.brute_force(ciphertext)
    ]
    if limit is not None:
        attempts_sorted = sorted(attempts, key=lambda item: item[2], reverse=True)
        attempts = attempts_sorted[:limit]
        if highlight_shift is not None and all(
            shift != highlight_shift for shift, _, _ in attempts
        ):
            highlight_entry = next(
                (
                    (shift, suggestion, score)
                    for shift, suggestion, score in attempts_sorted
                    if shift == highlight_shift
                ),
                None,
            )
            if highlight_entry:
                attempts.append(highlight_entry)
        # Повертаємо числовий порядок зсувів, щоб легше аналізувати послідовність.
        attempts.sort(key=lambda item: item[0])
    return [
        (
            shift,
            suggestion,
            score,
            highlight_shift is not None and shift == highlight_shift,
        )
        for shift, suggestion, score in attempts
    ]


@dataclass
class CipherOutcome:
    """Консолідовані результати шифрів для подальшого відображення."""

    caesar_cipher: str
    caesar_plain: str
    vigenere_cipher: str
    vigenere_plain: str
    original_plaintext: str


def execute_operation(
    sanitized_text: str,
    keys: KeyMaterial,
    prepared_key: vigenere.KeyInfo,
    operation: str,
) -> CipherOutcome:
    """Виконує обрану операцію та повертає усі проміжні рядки."""

    if operation == "encrypt":
        caesar_cipher = caesar.encrypt(sanitized_text, keys.caesar_shift)
        caesar_plain = caesar.decrypt(caesar_cipher, keys.caesar_shift)
        vigenere_cipher = vigenere.encrypt(sanitized_text, prepared_key)
        vigenere_plain = vigenere.decrypt(vigenere_cipher, prepared_key)
        original_plaintext = sanitized_text
    else:
        caesar_plain = caesar.decrypt(sanitized_text, keys.caesar_shift)
        caesar_cipher = caesar.encrypt(caesar_plain, keys.caesar_shift)
        vigenere_plain = vigenere.decrypt(sanitized_text, prepared_key)
        vigenere_cipher = vigenere.encrypt(vigenere_plain, prepared_key)
        original_plaintext = caesar_plain
    return CipherOutcome(
        caesar_cipher=caesar_cipher,
        caesar_plain=caesar_plain,
        vigenere_cipher=vigenere_cipher,
        vigenere_plain=vigenere_plain,
        original_plaintext=original_plaintext,
    )


def prompt_user(console: Console) -> tuple[str, str, str, str, bool]:
    console.print(
        Panel.fit(
            Text(
                "Демонстрація шифрів Цезаря та Віженера з автоматичною генерацією ключів.\nНатисніть Enter, щоб прийняти значення за замовчуванням.",
                justify="center",
            ),
            title="Порівняльний аналіз шифрів",
            border_style="bright_green",
        )
    )
    text = Prompt.ask("Текст для опрацювання", default=DEFAULT_TEXT)
    surname = Prompt.ask("Прізвище (ключ Віженера)", default=DEFAULT_SURNAME)
    birthdate = Prompt.ask(
        "Дата народження (YYYY-MM-DD / DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY)",
        default=DEFAULT_BIRTHDATE,
    )
    operation = Prompt.ask(
        "Операція", choices=["encrypt", "decrypt"], default="encrypt"
    )
    show_bruteforce = False
    if operation == "decrypt":
        show_bruteforce = Confirm.ask(
            "Показати brute force для шифру Цезаря?", default=True
        )
    return text, surname, birthdate, operation, show_bruteforce


def render_overview(
    console: Console,
    sanitized_text: str,
    keys: KeyMaterial,
    *,
    text: str,
    surname: str,
    birthdate: str,
    operation: str,
) -> None:
    operation_label = OPERATION_LABELS.get(operation, operation)
    details = f"[bold]Операція:[/] {operation_label}\n"
    details += f"[bold]Початковий текст:[/] {text}"
    if sanitized_text != text:
        details += f"\n[bold]Санітизований текст:[/] {sanitized_text}"
    details += f"\n[bold]Прізвище:[/] {surname} → {keys.vigenere_details}\n[bold]Дата народження:[/] {birthdate} → {keys.caesar_details}"
    console.print(
        Panel(
            details, title="Вхідні параметри", border_style="bright_green", expand=False
        )
    )


def build_results_table(
    caesar_cipher: str, caesar_plain: str, vigenere_cipher: str, vigenere_plain: str
) -> Table:
    table = Table(
        title="Результати",
        box=box.DOUBLE_EDGE,
        border_style="bright_green",
        header_style="bold bright_green",
    )
    table.add_column("Алгоритм", style="cyan", no_wrap=True)
    table.add_column("Ciphertext", style="green")
    table.add_column("Plaintext", style="magenta")
    table.add_row("Шифр Цезаря", caesar_cipher, caesar_plain)
    table.add_row("Шифр Віженера", vigenere_cipher, vigenere_plain)
    return table


def build_analysis_table(report: ComparativeReport) -> Table:
    table = Table(
        title="Порівняльний аналіз",
        box=box.MINIMAL_DOUBLE_HEAD,
        border_style="bright_cyan",
        header_style="bold bright_cyan",
    )
    table.add_column("Метрика", style="cyan", no_wrap=True)
    table.add_column("Цезар", style="green")
    table.add_column("Віженер", style="magenta")
    table.add_row("Довжина", str(report.caesar.length), str(report.vigenere.length))
    table.add_row(
        "Унікальні символи",
        str(report.caesar.unique_symbols),
        str(report.vigenere.unique_symbols),
    )
    table.add_row(
        "Частка голосних",
        str(report.caesar.vowel_ratio),
        str(report.vigenere.vowel_ratio),
    )
    table.add_row("Ентропія", str(report.caesar.entropy), str(report.vigenere.entropy))
    table.add_row("Ключ", report.caesar.key_complexity, report.vigenere.key_complexity)
    return table


def build_frequency_table(title: str, data: dict[str, int]) -> Table:
    table = Table(
        title=title,
        box=box.SIMPLE_HEAVY,
        border_style="bright_green",
        header_style="bold bright_green",
    )
    table.add_column("Символ", style="cyan", no_wrap=True)
    table.add_column("Кількість", style="green")
    if not data:
        # Якщо розподіл порожній, виводимо заглушку, щоб таблиця не була пустою.
        table.add_row("—", "0")
    else:
        for char, count in data.items():
            table.add_row(char, str(count))
    return table


def build_bruteforce_table(attempts: List[Tuple[int, str, float, bool]]) -> Table:
    table = Table(
        title="Brute force для шифру Цезаря",
        box=box.SQUARE,
        border_style="bright_yellow",
        header_style="bold bright_yellow",
    )
    table.add_column("Зсув", style="yellow", justify="right", no_wrap=True)
    table.add_column("Частка голосних", style="green", justify="right")
    table.add_column("Текст", style="white")
    for shift, suggestion, score, is_highlighted in attempts:
        shift_label = f"{shift}"
        if is_highlighted:
            # Виділяємо правильний зсув, щоб студенту легше було його помітити.
            shift_label = f"[bold bright_cyan]{shift}★[/]"
        table.add_row(shift_label, f"{score:.4f}", suggestion)
    return table


def main() -> int:
    console = Console()
    try:
        text, surname, birthdate, operation, show_bruteforce = prompt_user(console)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]Вихід без обробки.[/]")
        return 1
    sanitized_text = sanitize_text(text)
    if not sanitized_text:
        console.print("[bold red]Помилка:[/] введіть текст для опрацювання.")
        return 1
    try:
        keys = derive_keys(birthdate, surname)
    except ValueError as exc:
        console.print(f"[bold red]Помилка:[/] {exc}")
        return 1
    prepared_key = vigenere.prepare_key(keys.vigenere_key)
    outcome = execute_operation(sanitized_text, keys, prepared_key, operation)
    bruteforce_attempts: List[Tuple[int, str, float, bool]] = []
    if operation == "decrypt" and show_bruteforce:
        # Показуємо всі варіанти зсуву, щоб продемонструвати повний перебір ключового простору.
        bruteforce_attempts = build_bruteforce_preview(
            sanitized_text, limit=None, highlight_shift=keys.caesar_shift
        )
    report = build_report(
        original_text=outcome.original_plaintext,
        caesar_cipher=outcome.caesar_cipher,
        vigenere_cipher=outcome.vigenere_cipher,
        caesar_shift=keys.caesar_shift,
        vigenere_key=prepared_key[0],
    )
    console.rule("[bold bright_green]Параметри")
    render_overview(
        console,
        sanitized_text,
        keys,
        text=text,
        surname=surname,
        birthdate=birthdate,
        operation=operation,
    )
    console.rule("[bold bright_green]Результати")
    console.print(
        build_results_table(
            outcome.caesar_cipher,
            outcome.caesar_plain,
            outcome.vigenere_cipher,
            outcome.vigenere_plain,
        )
    )
    console.rule("[bold bright_green]Аналіз")
    console.print(build_analysis_table(report))
    console.print(
        Panel(
            Text(report.conclusion, style="bold"),
            title="Висновок",
            border_style="bright_cyan",
        )
    )
    freq_layout = Table.grid(padding=2)
    freq_layout.add_row(
        build_frequency_table("Частоти (Цезар)", report.caesar.frequency),
        build_frequency_table("Частоти (Віженер)", report.vigenere.frequency),
    )
    console.print(freq_layout)
    if bruteforce_attempts:
        console.rule("[bold bright_yellow]Brute Force")
        console.print(build_bruteforce_table(bruteforce_attempts))
    console.rule("[bold bright_green]Готово")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
