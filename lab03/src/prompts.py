from __future__ import annotations

from pathlib import Path
from typing import Literal
from rich.prompt import Confirm, Prompt
from .ui import console, print_error


def prompt_bits_per_channel() -> int:
    """Запитує кількість бітів на канал."""
    while True:
        raw = Prompt.ask(
            "[cyan]🔢 Кількість молодших бітів на канал[/cyan]",
            choices=["1", "2"],
            default="1",
            show_default=True,
        )
        return int(raw)


def prompt_positive_int(message: str, default: int) -> int:
    """Запитує додатне ціле число."""
    while True:
        raw = Prompt.ask(
            f"[cyan]{message}[/cyan]",
            default=str(default),
            show_default=True,
        )
        try:
            value = int(raw)
            if value > 0:
                return value
            print_error("Число має бути більшим за нуль.")
        except ValueError:
            print_error("Потрібно ввести додатне число.")


def prompt_password() -> str | None:
    """Запитує пароль (опційно)."""
    password = Prompt.ask(
        "[cyan]🔑 Пароль[/cyan] [dim](Enter для пропуску)[/dim]",
        default="",
        show_default=False,
        password=True,
    )
    return password or None


def prompt_path(
    message: str,
    *,
    must_exist: bool = False,
    expect_file: bool = True,
    require_suffix: bool = False,
) -> Path:
    """
    Запитує шлях до файлу або каталогу.
    
    Args:
        message: Повідомлення для користувача
        must_exist: Чи файл повинен існувати
        expect_file: Чи очікується файл (не каталог)
        require_suffix: Чи потрібне розширення файлу
        
    Returns:
        Валідний шлях
    """
    while True:
        raw_value = Prompt.ask(f"[cyan]📁 {message}[/cyan]").strip()
        
        if not raw_value:
            print_error("Шлях не може бути порожнім.")
            continue
        
        path = Path(raw_value).expanduser()
        
        if must_exist and not path.exists():
            print_error("Файл не знайдено. Спробуйте ще раз.")
            continue
        
        if must_exist and expect_file and path.is_dir():
            print_error("Очікується шлях до файлу, а не каталогу.")
            continue
        
        if not must_exist and expect_file and path.exists() and path.is_dir():
            print_error("Ви вказали каталог, а очікується файл.")
            continue
        
        if expect_file and not must_exist:
            parent = path.parent if path.parent != Path("") else Path(".")
            if not parent.exists():
                print_error("Каталог для файлу не існує.")
                continue
        
        if require_suffix and not path.suffix:
            print_error("Додайте розширення файлу (наприклад, .png).")
            continue
        
        return path


def prompt_message_source() -> Literal["text", "file"]:
    """Запитує джерело повідомлення."""
    return Prompt.ask(
        "[cyan]📝 Як надати повідомлення?[/cyan]",
        choices=["text", "file"],
        default="text",
    )


def prompt_message_text() -> str:
    """Запитує текст повідомлення."""
    return console.input("[cyan]✏️  Введіть текст повідомлення:[/cyan]\n")


def load_message_from_file() -> str:
    """Завантажує повідомлення з файлу."""
    while True:
        file_path = prompt_path("Шлях до текстового файлу", must_exist=True)
        try:
            return file_path.read_text(encoding="utf-8")
        except OSError as exc:
            print_error(f"Не вдалося прочитати файл: {exc}")


def prompt_message() -> str:
    """Запитує повідомлення (текст або файл)."""
    source = prompt_message_source()
    if source == "text":
        return prompt_message_text()
    return load_message_from_file()


def confirm(message: str, default: bool = False) -> bool:
    """Запитує підтвердження."""
    return Confirm.ask(f"[cyan]{message}[/cyan]", default=default)


def prompt_menu_choice() -> str:
    """Запитує вибір пункту меню."""
    choice = Prompt.ask(
        "[bold]➤ Ваш вибір[/bold]",
        choices=["1", "2", "3", "q", "Q"],
        default="1",
        show_default=True,
    )
    return choice.lower()
