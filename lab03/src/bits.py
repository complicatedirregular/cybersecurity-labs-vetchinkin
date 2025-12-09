from __future__ import annotations

from typing import Iterator, Sequence


class BitReader:
    """
    Читач бітів з байтового масиву.
    
    Дозволяє послідовно читати біти з даних
    із заданою шириною (кількістю бітів за раз).
    """
    
    __slots__ = ("_data", "_bit_length", "_position")

    def __init__(self, data: bytes) -> None:
        """
        Ініціалізує читач бітів.
        
        Args:
            data: Байтовий масив для читання
        """
        self._data = data
        self._bit_length = len(data) * 8
        self._position = 0

    @property
    def total_bits(self) -> int:
        """Загальна кількість бітів у даних."""
        return self._bit_length

    @property
    def remaining_bits(self) -> int:
        """Кількість непрочитаних бітів."""
        return self._bit_length - self._position

    @property
    def has_bits(self) -> bool:
        """Чи є ще непрочитані біти."""
        return self._position < self._bit_length

    def read(self, width: int) -> int | None:
        """
        Читає задану кількість бітів.
        
        Args:
            width: Кількість бітів для читання
            
        Returns:
            Ціле число з прочитаних бітів або None,
            якщо недостатньо даних
        """
        if self.remaining_bits < width:
            return None
        
        value = 0
        for _ in range(width):
            byte_idx = self._position // 8
            bit_offset = 7 - (self._position % 8)
            bit = (self._data[byte_idx] >> bit_offset) & 1
            value = (value << 1) | bit
            self._position += 1
        
        return value


def bits_to_bytes(bit_iterator: Iterator[int], bit_count: int) -> bytes:
    """
    Конвертує потік бітів у байти.
    
    Args:
        bit_iterator: Ітератор, що повертає окремі біти
        bit_count: Кількість бітів для читання
        
    Returns:
        Байтовий масив
        
    Raises:
        ValueError: Якщо недостатньо бітів
    """
    if bit_count < 0:
        raise ValueError("bit_count повинен бути невід'ємним.")
    
    result = bytearray()
    accumulator = 0
    count = 0
    
    for _ in range(bit_count):
        try:
            bit = next(bit_iterator)
        except StopIteration:
            raise ValueError(
                "Несподіване закінчення даних під час читання вбудованих бітів."
            )
        
        accumulator = (accumulator << 1) | (bit & 1)
        count += 1
        
        if count == 8:
            result.append(accumulator)
            accumulator = 0
            count = 0
    
    # Якщо залишилися біти, доповнюємо нулями
    if count:
        accumulator <<= (8 - count)
        result.append(accumulator)
    
    return bytes(result)


def extract_lsb_bits(
    pixel_data: Sequence[Sequence[int]],
    channel_indexes: tuple[int, ...],
    bits_per_channel: int,
) -> Iterator[int]:
    """
    Витягує LSB біти з пікселів зображення.
    
    Args:
        pixel_data: Послідовність пікселів
        channel_indexes: Індекси каналів для читання
        bits_per_channel: Кількість молодших бітів на канал
        
    Yields:
        Окремі біти (0 або 1)
    """
    mask = (1 << bits_per_channel) - 1
    
    for pixel in pixel_data:
        for channel_idx in channel_indexes:
            chunk = pixel[channel_idx] & mask
            # Повертаємо біти від старшого до молодшого
            for shift in range(bits_per_channel - 1, -1, -1):
                yield (chunk >> shift) & 1
