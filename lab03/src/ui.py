from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from .models import DiffReport, EmbedReport

# Кольорова тема
THEME = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "accent": "bold magenta",
    "muted": "dim white",
    "highlight": "bold cyan",
})

# ASCII-арт логотип
LOGO = r"""
[bold cyan]
  ╦  ╔═╗╔╗   ╔═╗╔╦╗╔═╗╔═╗╔═╗
  ║  ╚═╗╠╩╗  ╚═╗ ║ ║╣ ║ ╦║ ║
  ╩═╝╚═╝╚═╝  ╚═╝ ╩ ╚═╝╚═╝╚═╝
[/bold cyan]
[dim]Стеганографія методом найменш значущого біта[/dim]
"""

console = Console(theme=THEME)


def print_logo() -> None:
    """Виводить логотип програми."""
    console.print(LOGO, justify="center")


def print_success(message: str) -> None:
    """Виводить повідомлення про успіх."""
    console.print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    """Виводить повідомлення про помилку."""
    console.print(f"[error]✗[/error] {message}")


def print_warning(message: str) -> None:
    """Виводить попередження."""
    console.print(f"[warning]⚠[/warning] {message}")


def print_info(message: str) -> None:
    """Виводить інформаційне повідомлення."""
    console.print(f"[info]ℹ[/info] {message}")


def format_bytes(size: int) -> str:
    """Форматує розмір у байтах у зручний вигляд."""
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}" if unit != "Б" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"


def format_percentage(value: float) -> str:
    """Форматує відсоток."""
    return f"{value * 100:.2f}%"


def create_embed_report_table(report: EmbedReport) -> Table:
    """Створює таблицю звіту про вбудовування."""
    table = Table(
        title="📊 Звіт про вбудовування",
        title_style="bold green",
        border_style="green",
        header_style="bold cyan",
        show_lines=True,
    )
    
    table.add_column("Параметр", style="cyan", width=25)
    table.add_column("Значення", style="white", width=30)
    
    # Основні показники
    table.add_row(
        "📦 Корисне навантаження",
        f"{report.payload_bytes} байт ({report.payload_bits} біт)"
    )
    table.add_row(
        "🔧 Бітів на канал",
        str(report.bits_per_channel)
    )
    table.add_row(
        "📈 Заповненість ємності",
        _colorize_utilization(report.utilization)
    )
    table.add_row(
        "🎨 Змінені пікселі",
        f"{report.pixels_touched:,} з {report.total_pixels:,}"
    )
    table.add_row(
        "📁 Розмір файлу",
        f"{format_bytes(report.file_size_before)} → {format_bytes(report.file_size_after)}"
    )
    
    diff = report.file_size_diff
    diff_str = f"+{format_bytes(diff)}" if diff >= 0 else format_bytes(diff)
    table.add_row("📊 Різниця розміру", diff_str)
    
    return table


def _colorize_utilization(value: float) -> str:
    """Кольорове форматування використання ємності."""
    percentage = format_percentage(value)
    if value < 0.3:
        return f"[green]{percentage}[/green] ▪▪▪▪▪▪▪▪▪▪"
    elif value < 0.6:
        return f"[yellow]{percentage}[/yellow] ▪▪▪▪▪▪▪▪▪▪"
    elif value < 0.9:
        return f"[orange1]{percentage}[/orange1] ▪▪▪▪▪▪▪▪▪▪"
    else:
        return f"[red]{percentage}[/red] ▪▪▪▪▪▪▪▪▪▪"


def create_diff_report_table(diff: DiffReport) -> Table:
    """Створює таблицю звіту про аналіз відмінностей."""
    table = Table(
        title="🔍 Аналіз змін",
        title_style="bold blue",
        border_style="blue",
        header_style="bold magenta",
        show_lines=True,
    )
    
    table.add_column("Параметр", style="magenta", width=25)
    table.add_column("Значення", style="white", width=30)
    
    table.add_row(
        "🎨 Канали зі змінами",
        f"{diff.changed_channels:,} з {diff.total_channels:,}"
    )
    table.add_row(
        "📊 Відсоток змін",
        format_percentage(diff.change_ratio)
    )
    table.add_row(
        "📈 Середня різниця",
        f"{diff.avg_abs_diff:.4f}"
    )
    table.add_row(
        "📉 Максимальна різниця",
        str(diff.max_abs_diff)
    )
    table.add_row(
        "📁 Розмір файлу",
        f"{format_bytes(diff.file_size_before)} → {format_bytes(diff.file_size_after)}"
    )
    
    return table


def create_menu_panel() -> Panel:
    """Створює панель головного меню."""
    menu_text = Text()
    menu_text.append("  1 ", style="bold cyan")
    menu_text.append("│ ", style="dim")
    menu_text.append("🔒 Сховати повідомлення\n", style="white")
    menu_text.append("  2 ", style="bold cyan")
    menu_text.append("│ ", style="dim")
    menu_text.append("🔓 Витягнути повідомлення\n", style="white")
    menu_text.append("  3 ", style="bold cyan")
    menu_text.append("│ ", style="dim")
    menu_text.append("🔍 Аналізувати різницю\n", style="white")
    menu_text.append("  Q ", style="bold red")
    menu_text.append("│ ", style="dim")
    menu_text.append("🚪 Вийти", style="white")
    
    return Panel(
        menu_text,
        title="[bold]📋 Меню[/bold]",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )


def create_message_panel(message: str, title: str = "Повідомлення") -> Panel:
    """Створює панель для відображення повідомлення."""
    return Panel(
        message,
        title=f"[bold cyan]📝 {title}[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )


def create_progress() -> Progress:
    """Створює індикатор прогресу."""
    return Progress(
        SpinnerColumn("dots", style="cyan"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40, style="cyan", complete_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def create_spinner_progress() -> Progress:
    """Створює простий спіннер без смуги прогресу."""
    return Progress(
        SpinnerColumn("dots", style="cyan"),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )
