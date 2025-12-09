from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict
from rich.panel import Panel
from src import (
    analyze_images,
    extract_message,
    hide_message,
    visualize_diff,
)
from src.prompts import (
    confirm,
    prompt_bits_per_channel,
    prompt_menu_choice,
    prompt_message,
    prompt_password,
    prompt_path,
    prompt_positive_int,
)
from src.ui import (
    console,
    create_diff_report_table,
    create_embed_report_table,
    create_menu_panel,
    create_message_panel,
    create_spinner_progress,
    print_error,
    print_info,
    print_logo,
    print_success,
    print_warning,
)


def _interactive_hide() -> None:
    """Інтерактивний режим вбудовування повідомлення."""
    console.print()
    console.print(Panel.fit(
        "[bold]🔒 Режим вбудовування повідомлення[/bold]",
        border_style="green",
    ))
    console.print()
    
    # Збір параметрів
    input_image = prompt_path(
        "Шлях до оригінального зображення",
        must_exist=True,
    )
    output_image = prompt_path(
        "Шлях для збереження результату",
        expect_file=True,
        require_suffix=True,
    )
    message = prompt_message()
    password = prompt_password()
    bits = prompt_bits_per_channel()
    
    console.print()
    
    # Виконання з індикатором прогресу
    with create_spinner_progress() as progress:
        task = progress.add_task("Вбудовування повідомлення...", total=None)
        
        report = hide_message(
            input_image,
            output_image,
            message,
            password=password,
            bits_per_channel=bits,
        )
        
        progress.update(task, completed=True)
    
    console.print()
    print_success("Повідомлення успішно вбудовано!")
    console.print()
    console.print(create_embed_report_table(report))
    console.print()
    
    # Опціональний аналіз
    if confirm("Показати аналіз відмінностей?"):
        diff = analyze_images(input_image, output_image)
        console.print()
        console.print(create_diff_report_table(diff))
    
    console.print()
    _maybe_render_diff_image(
        input_image,
        output_image,
        confirm_prompt="Зберегти зображення різниць?",
    )


def _interactive_extract() -> None:
    """Інтерактивний режим витягування повідомлення."""
    console.print()
    console.print(Panel.fit(
        "[bold]🔓 Режим відновлення повідомлення[/bold]",
        border_style="blue",
    ))
    console.print()
    
    # Збір параметрів
    encoded_path = prompt_path(
        "Шлях до зображення з повідомленням",
        must_exist=True,
    )
    password = prompt_password()
    bits = prompt_bits_per_channel()
    
    console.print()
    
    # Витягування
    with create_spinner_progress() as progress:
        task = progress.add_task("Витягування повідомлення...", total=None)
        
        message = extract_message(
            encoded_path,
            password=password,
            bits_per_channel=bits,
        )
        
        progress.update(task, completed=True)
    
    console.print()
    print_success("Повідомлення успішно витягнуто!")
    console.print()
    
    # Відображення або збереження
    if confirm("Зберегти текст у файл?"):
        output = prompt_path("Шлях до файлу для збереження", expect_file=True)
        output.write_text(message, encoding="utf-8")
        console.print()
        print_info(f"Текст записано у {output}")
    else:
        console.print()
        console.print(create_message_panel(message, "Зміст повідомлення"))
    
    console.print()


def _interactive_diff() -> None:
    """Інтерактивний режим аналізу різниць."""
    console.print()
    console.print(Panel.fit(
        "[bold]🔍 Аналіз двох зображень[/bold]",
        border_style="magenta",
    ))
    console.print()
    
    # Збір шляхів
    original = prompt_path(
        "Шлях до оригінального зображення",
        must_exist=True,
    )
    modified = prompt_path(
        "Шлях до модифікованого зображення",
        must_exist=True,
    )
    
    console.print()
    
    # Аналіз
    with create_spinner_progress() as progress:
        task = progress.add_task("Аналіз зображень...", total=None)
        diff = analyze_images(original, modified)
        progress.update(task, completed=True)
    
    console.print()
    console.print(create_diff_report_table(diff))
    console.print()
    
    _maybe_render_diff_image(
        original,
        modified,
        confirm_prompt="Створити візуалізацію різниць?",
    )


def _maybe_render_diff_image(
    original: Path,
    modified: Path,
    *,
    confirm_prompt: str,
) -> None:
    """Опціонально створює візуалізацію різниць."""
    if not confirm(confirm_prompt):
        return
    
    output = prompt_path(
        "Шлях до diff-зображення",
        expect_file=True,
        require_suffix=True,
    )
    amplify = prompt_positive_int(
        "🔊 Коефіцієнт підсилення (наприклад, 16)",
        default=16,
    )
    
    console.print()
    
    with create_spinner_progress() as progress:
        task = progress.add_task("Створення візуалізації...", total=None)
        visualize_diff(original, modified, output, amplify=amplify)
        progress.update(task, completed=True)
    
    console.print()
    print_success(f"Візуалізацію збережено у {output}")
    console.print()


def _show_menu() -> str:
    """Відображає головне меню та повертає вибір."""
    console.print()
    console.print(create_menu_panel())
    console.print()
    return prompt_menu_choice()


def main() -> None:
    """Головна точка входу програми."""
    # Очищення та вітання
    console.clear()
    print_logo()
    
    actions: Dict[str, Callable[[], None]] = {
        "1": _interactive_hide,
        "2": _interactive_extract,
        "3": _interactive_diff,
    }
    
    while True:
        choice = _show_menu()
        
        if choice == "q":
            console.print()
            console.print(Panel.fit(
                "[bold green]👋 До побачення![/bold green]",
                border_style="green",
            ))
            console.print()
            break
        
        action = actions.get(choice)
        
        if not action:
            print_warning("Невідомий пункт меню.")
            continue
        
        try:
            action()
        except KeyboardInterrupt:
            console.print()
            print_warning("Операцію перервано.")
        except (OSError, ValueError) as exc:
            console.print()
            print_error(f"Помилка: {exc}")
        except Exception as exc:
            console.print()
            print_error(f"Непередбачена критична помилка: {exc}")
            raise


if __name__ == "__main__":
    main()
