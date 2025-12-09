from __future__ import annotations

from datetime import datetime, date
from typing import Sequence, Tuple
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from .analysis import analyze_password
from .constants import DATE_FORMATS
from .data import PersonalData, PasswordAnalysisResult

console = Console()


def _print_heading(text: str, style: str = "bold cyan") -> None:
    console.print(Panel.fit(Text(text, justify="center"), border_style=style))


def _prompt(message: str) -> str:
    return console.input(f"[bold cyan]{message}[/bold cyan] ")


def _format_items(items: Sequence[str], empty_label: str = "відсутні") -> str:
    return ", ".join(items) if items else empty_label


def _print_warning(message: str) -> None:
    console.print(f"[bold red]{message}[/bold red]")


def prompt_personal_data() -> Tuple[str, PersonalData]:
    """Збирає пароль і персональні дані користувача."""
    _print_heading("Аналіз безпеки пароля")
    password = _prompt("Введіть пароль для аналізу: ").rstrip("\n")
    first_name = _prompt("Введіть ім'я: ").strip()
    last_name = _prompt("Введіть прізвище (необов'язково): ").strip() or None
    birth_date = parse_birth_date(
        _prompt("Введіть дату народження (необов'язково): ").strip()
    )
    extra_raw = _prompt(
        "Перерахуйте додаткові персональні дані через кому (логін, місто, улюблені слова): "
    ).strip()
    extra_words = [item.strip() for item in extra_raw.split(",") if item.strip()]
    data = PersonalData(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        extra_words=extra_words,
    )
    return password, data


def parse_birth_date(value: str) -> date | None:
    """Розпізнає дату народження в декількох поширених форматах."""
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    _print_warning("Не вдалося розпізнати дату.")
    return None


def print_report(result: PasswordAnalysisResult) -> None:
    """Виводить результат аналізу у форматі Rich."""
    console.print()
    console.print(
        Panel.fit(Text("Результати аналізу", justify="center"), border_style="green")
    )
    table = Table(show_header=False, box=box.ROUNDED, expand=False)
    table.add_row(
        "Оцінка", f"[bold yellow]{result.score}/10[/bold yellow] ({result.strength})"
    )
    table.add_row("Персональні збіги", _format_items(result.personal_matches))
    table.add_row("Словникові збіги", _format_items(result.dictionary_matches))
    console.print(table)
    if result.issues:
        console.print("\n[bold red]Виявлені проблеми:[/bold red]")
        for issue in result.issues:
            console.print(f" • {issue}")
    if result.recommendations:
        console.print("\n[bold green]Рекомендації:[/bold green]")
        for advice in result.recommendations:
            console.print(f" • {advice}")


def run_cli() -> None:
    """Запускає повний сценарій роботи CLI."""
    password, personal_data = prompt_personal_data()
    result = analyze_password(password, personal_data)
    print_report(result)
