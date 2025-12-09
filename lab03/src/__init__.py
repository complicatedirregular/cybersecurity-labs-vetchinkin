from .models import DiffReport, EmbedReport
from .steganography import (
    DEFAULT_BITS_PER_CHANNEL,
    MAX_BITS_PER_CHANNEL,
    MIN_BITS_PER_CHANNEL,
    analyze_images,
    extract_message,
    hide_message,
    visualize_diff,
)

__version__ = "2.0.0"
__author__ = "Artem Vetchinkin"

__all__ = [
    # Моделі
    "EmbedReport",
    "DiffReport",
    # Основні функції
    "hide_message",
    "extract_message",
    "analyze_images",
    "visualize_diff",
    # Константи
    "DEFAULT_BITS_PER_CHANNEL",
    "MIN_BITS_PER_CHANNEL",
    "MAX_BITS_PER_CHANNEL",
]
