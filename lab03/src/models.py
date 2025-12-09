from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(slots=True, frozen=True)
class EmbedReport:
    """Звіт про вбудовування повідомлення в зображення."""
    
    payload_bits: int
    capacity_bits: int
    total_pixels: int
    channels_used: int
    bits_per_channel: int
    pixels_touched: int
    file_size_before: int
    file_size_after: int

    @property
    def utilization(self) -> float:
        """Відсоток використаної ємності зображення."""
        if self.capacity_bits == 0:
            return 0.0
        return self.payload_bits / self.capacity_bits

    @property
    def payload_bytes(self) -> int:
        """Розмір корисного навантаження в байтах."""
        return self.payload_bits // 8

    @property
    def file_size_diff(self) -> int:
        """Різниця розмірів файлів у байтах."""
        return self.file_size_after - self.file_size_before


@dataclass(slots=True, frozen=True)
class DiffReport:
    """Звіт про аналіз відмінностей між зображеннями."""
    
    total_channels: int
    changed_channels: int
    avg_abs_diff: float
    max_abs_diff: int
    file_size_before: int
    file_size_after: int

    @property
    def change_ratio(self) -> float:
        """Відсоток змінених каналів."""
        if self.total_channels == 0:
            return 0.0
        return self.changed_channels / self.total_channels

    @property
    def file_size_diff(self) -> int:
        """Різниця розмірів файлів у байтах."""
        return self.file_size_after - self.file_size_before


@dataclass(slots=True)
class ImageMetadata:
    """Метадані зображення для стеганографії."""
    
    width: int
    height: int
    mode: str
    embed_indexes: Tuple[int, ...]
    
    @property
    def total_pixels(self) -> int:
        return self.width * self.height
    
    @property
    def channels_count(self) -> int:
        return len(self.embed_indexes)
    
    def capacity_bits(self, bits_per_channel: int) -> int:
        """Обчислює ємність для вбудовування в бітах."""
        return self.total_pixels * self.channels_count * bits_per_channel
