from __future__ import annotations

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from src import (
    DiffReport,
    EmbedReport,
    analyze_images,
    extract_message,
    hide_message,
    visualize_diff,
)

console = Console()


def _print_embed_report(report: EmbedReport) -> None:
    table = Table(title="Звіт про вбудовування", title_style="bold green")
    table.add_column("Параметр", style="cyan")
    table.add_column("Значення", style="white")
    table.add_row("Корисне навантаження", f"{report.payload_bits // 8} байт")
    table.add_row("Використано бітів/канал", str(report.bits_per_channel))
    table.add_row("Заповненість місткості", f"{report.utilization * 100:.2f}%")
    table.add_row("Змінені пікселі", f"{report.pixels_touched} з {report.total_pixels}")
    table.add_row(
        "Розмір файлу", f"{report.file_size_before} ➜ {report.file_size_after} байт"
    )
    console.print(table)


def _print_diff_report(diff: DiffReport) -> None:
    table = Table(title="Аналіз змін", title_style="bold blue")
    table.add_column("Параметр", style="magenta")
    table.add_column("Значення", style="white")
    table.add_row(
        "Канали зі змінами", f"{diff.changed_channels} з {diff.total_channels}"
    )
    table.add_row("Сер. модуль різниці", f"{diff.avg_abs_diff:.3f}")
    table.add_row("Максимальна різниця", str(diff.max_abs_diff))
    table.add_row(
        "Розмір файлу", f"{diff.file_size_before} ➜ {diff.file_size_after} байт"
    )
    console.print(table)


def _prompt_bits_per_channel() -> int:
    while True:
        raw = Prompt.ask(
            "Кількість молодших бітів на канал [1-2]", default="1", show_default=True
        )
        try:
            value = int(raw)
        except ValueError:
            console.print("[bold red]Введіть число 1 або 2.[/]")
            continue
        if value in (1, 2):
            return value
        console.print("[bold red]Допустимі значення: 1 або 2.[/]")


def _prompt_positive_int(message: str, default: int) -> int:
    while True:
        raw = Prompt.ask(message, default=str(default), show_default=True)
        try:
            value = int(raw)
        except ValueError:
            console.print("[bold red]Потрібно ввести додатнє число.[/]")
            continue
        if value > 0:
            return value
        console.print("[bold red]Число має бути більшим за нуль.[/]")


def _prompt_password() -> str | None:
    password = Prompt.ask(
        "Пароль (Enter, якщо без пароля)", default="", show_default=False, password=True
    )
    return password or None


def _prompt_path(
    message: str,
    *,
    must_exist: bool = False,
    expect_file: bool = True,
    require_suffix: bool = False,
) -> Path:
    while True:
        raw_value = Prompt.ask(message).strip()
        if not raw_value:
            console.print("[bold red]Шлях не може бути порожнім.[/]")
            continue
        path = Path(raw_value).expanduser()
        if must_exist and not path.exists():
            console.print("[bold red]Файл не знайдено. Спробуйте ще раз.[/]")
            continue
        if must_exist and expect_file and path.is_dir():
            console.print("[bold red]Очікується шлях до файлу, а не каталогу.[/]")
            continue
        if not must_exist and expect_file and path.exists() and path.is_dir():
            console.print("[bold red]Ви вказали каталог, а очікується файл.[/]")
            continue
        if expect_file and not must_exist:
            parent = path.parent if path.parent != Path("") else Path(".")
            if not parent.exists():
                console.print("[bold red]Каталог для файлу не існує.[/]")
                continue
        if require_suffix and not path.suffix:
            console.print("[bold red]Додайте розширення файлу (наприклад, .png).[/]")
            continue
        return path


def _load_message_from_file() -> str:
    while True:
        file_path = _prompt_path("Шлях до текстового файлу", must_exist=True)
        try:
            return file_path.read_text(encoding="utf-8")
        except OSError as exc:
            console.print(f"[bold red]Не вдалося прочитати файл: {exc}[/]")


def _prompt_message() -> str:
    mode = Prompt.ask(
        "Як ви хочете надати повідомлення?", choices=["text", "file"], default="text"
    )
    if mode == "text":
        return console.input("Введіть текст повідомлення:\n")
    return _load_message_from_file()


def _interactive_hide() -> None:
    console.print(Panel.fit("Режим вбудовування повідомлення", title="LSB Hide"))
    input_image = _prompt_path(
        "Вкажіть шлях до оригінального зображення", must_exist=True
    )
    output_image = _prompt_path(
        "Вкажіть шлях для збереження результату", expect_file=True, require_suffix=True
    )
    message = _prompt_message()
    password = _prompt_password()
    bits = _prompt_bits_per_channel()
    report = hide_message(
        input_image, output_image, message, password=password, bits_per_channel=bits
    )
    console.print("[bold green]Повідомлення успішно вбудовано![/]")
    _print_embed_report(report)
    if Confirm.ask("Показати аналіз відмінностей?", default=False):
        diff = analyze_images(input_image, output_image)
        _print_diff_report(diff)
    _maybe_render_diff_image(
        input_image,
        output_image,
        confirm_prompt="Зберегти зображення різниць?",
        success_template="[bold yellow]Зображення різниць збережено у {path}[/]",
    )


def _interactive_extract() -> None:
    console.print(Panel.fit("Режим відновлення повідомлення", title="LSB Extract"))
    encoded_path = _prompt_path("Шлях до зображення з повідомленням", must_exist=True)
    password = _prompt_password()
    bits = _prompt_bits_per_channel()
    message = extract_message(encoded_path, password=password, bits_per_channel=bits)
    console.print("[bold green]Повідомлення успішно витягнуто![/]")
    if Confirm.ask("Зберегти текст у файл?", default=False):
        output = _prompt_path("Шлях до файлу для збереження", expect_file=True)
        output.write_text(message, encoding="utf-8")
        console.print(f"[bold cyan]Текст записано у {output}[/]")
    else:
        console.print(Panel(message, title="Зміст повідомлення", style="bold cyan"))


def _interactive_diff() -> None:
    console.print(Panel.fit("Аналіз двох зображень", title="LSB Diff"))
    original = _prompt_path("Шлях до оригінального зображення", must_exist=True)
    modified = _prompt_path("Шлях до модифікованого зображення", must_exist=True)
    diff = analyze_images(original, modified)
    _print_diff_report(diff)
    _maybe_render_diff_image(
        original,
        modified,
        confirm_prompt="Створити візуалізацію різниць?",
        success_template="[bold yellow]Візуалізацію збережено у {path}[/]",
    )


def _maybe_render_diff_image(
    original: Path, modified: Path, *, confirm_prompt: str, success_template: str
) -> None:
    if not Confirm.ask(confirm_prompt, default=False):
        return
    output = _prompt_path(
        "Шлях до diff-зображення", expect_file=True, require_suffix=True
    )
    amplify = _prompt_positive_int("Коефіцієнт підсилення (наприклад, 16)", default=16)
    visualize_diff(original, modified, output, amplify=amplify)
    console.print(success_template.format(path=output))


def _show_menu() -> str:
    console.print(
        Panel(
            "1 — Сховати повідомлення\n"
            "2 — Витягнути повідомлення\n"
            "3 — Аналізувати різницю\n"
            "Q — Вийти",
            title="Меню",
            title_align="left",
        )
    )
    choice = Prompt.ask(
        "Ваш вибір", choices=["1", "2", "3", "q", "Q"], default="1", show_default=True
    )
    return choice.lower()


def main() -> None:
    actions = {
        "1": _interactive_hide,
        "2": _interactive_extract,
        "3": _interactive_diff,
    }
    while True:
        choice = _show_menu()
        if choice == "q":
            console.print("[bold green]До побачення![/]")
            break
        action = actions.get(choice)
        if not action:
            console.print("[bold red]Невідомий пункт меню.[/]")
            continue
        try:
            action()
        except (OSError, ValueError) as exc:
            console.print(f"[bold red]Сталася помилка: {exc}[/]")
        except Exception:
            console.print("[bold red]Непередбачена критична помилка. Завершення.[/]")
            raise


if __name__ == "__main__":
    main()
