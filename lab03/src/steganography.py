from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Sequence, Tuple
from PIL import Image, ImageChops
from .bits import BitReader, bits_to_bytes, extract_lsb_bits
from .crypto import (
    HEADER_SIZE,
    build_payload,
    decrypt_payload,
    parse_header,
)
from .models import DiffReport, EmbedReport, ImageMetadata

# Константи конфігурації
DEFAULT_BITS_PER_CHANNEL: int = 1
MIN_BITS_PER_CHANNEL: int = 1
MAX_BITS_PER_CHANNEL: int = 2
ALPHA_BANDS: frozenset[str] = frozenset({"A"})


def _validate_bits_per_channel(value: int) -> int:
    """Валідує параметр bits_per_channel."""
    if not (MIN_BITS_PER_CHANNEL <= value <= MAX_BITS_PER_CHANNEL):
        raise ValueError(
            f"bits_per_channel повинен бути в межах від "
            f"{MIN_BITS_PER_CHANNEL} до {MAX_BITS_PER_CHANNEL}, "
            f"отримано {value}."
        )
    return value


def _prepare_image(image: Image.Image) -> Tuple[Image.Image, ImageMetadata]:
    """
    Підготовляє зображення для стеганографії.
    
    Конвертує в RGB/RGBA та визначає канали для вбудовування.
    """
    mode = "RGBA" if "A" in image.getbands() else "RGB"
    converted = image.convert(mode)
    
    embed_indexes = tuple(
        idx for idx, band in enumerate(converted.getbands())
        if band not in ALPHA_BANDS
    )
    
    metadata = ImageMetadata(
        width=converted.width,
        height=converted.height,
        mode=mode,
        embed_indexes=embed_indexes,
    )
    
    return converted, metadata


def hide_message(
    input_image: str | Path,
    output_image: str | Path,
    message: str,
    *,
    password: str | None = None,
    bits_per_channel: int = DEFAULT_BITS_PER_CHANNEL,
    progress_callback: Callable[[int, int], None] | None = None,
) -> EmbedReport:
    """
    Вбудовує повідомлення в зображення методом LSB.
    
    Args:
        input_image: Шлях до вхідного зображення
        output_image: Шлях для збереження результату
        message: Текст повідомлення для вбудовування
        password: Пароль для шифрування (опційно)
        bits_per_channel: Кількість молодших бітів на канал (1-2)
        progress_callback: Функція зворотного виклику для прогресу
        
    Returns:
        Звіт про вбудовування
        
    Raises:
        ValueError: Якщо повідомлення завелике для зображення
    """
    bits_per_channel = _validate_bits_per_channel(bits_per_channel)
    source = Path(input_image)
    target = Path(output_image)
    
    # Формуємо корисне навантаження
    payload = build_payload(message, password)
    bit_reader = BitReader(payload)
    payload_bits = bit_reader.total_bits
    
    with Image.open(source) as original:
        working, metadata = _prepare_image(original)
        
        if not metadata.embed_indexes:
            raise ValueError("У зображенні не знайдено записуваних кольорових каналів.")
        
        capacity = metadata.capacity_bits(bits_per_channel)
        
        if payload_bits > capacity:
            raise ValueError(
                f"Повідомлення перевищує ємність: потрібно {payload_bits} бітів, "
                f"але зображення може зберігати тільки {capacity} бітів."
            )
        
        # Вбудовуємо дані
        pixels: List[Sequence[int]] = list(working.getdata())
        pixels_touched = 0
        mask = (1 << bits_per_channel) - 1
        total_pixels = len(pixels)
        
        for idx, pixel in enumerate(pixels):
            if not bit_reader.has_bits:
                break
            
            if progress_callback and idx % 10000 == 0:
                progress_callback(idx, total_pixels)
            
            pixel_list = list(pixel)
            pixel_changed = False
            
            for channel_idx in metadata.embed_indexes:
                chunk = bit_reader.read(bits_per_channel)
                if chunk is None:
                    break
                
                new_value = (pixel_list[channel_idx] & ~mask) | chunk
                if new_value != pixel_list[channel_idx]:
                    pixel_changed = True
                pixel_list[channel_idx] = new_value
            
            if pixel_changed:
                pixels[idx] = tuple(pixel_list)
                pixels_touched += 1
        
        if bit_reader.has_bits:
            raise RuntimeError("Не вдалося вбудувати весь корисний вантаж.")
        
        # Зберігаємо результат
        encoded = Image.new(working.mode, working.size)
        encoded.putdata(pixels)
        encoded.save(target)
    
    return EmbedReport(
        payload_bits=payload_bits,
        capacity_bits=capacity,
        total_pixels=metadata.total_pixels,
        channels_used=metadata.channels_count,
        bits_per_channel=bits_per_channel,
        pixels_touched=pixels_touched,
        file_size_before=source.stat().st_size,
        file_size_after=target.stat().st_size,
    )


def extract_message(
    encoded_image: str | Path,
    *,
    password: str | None = None,
    bits_per_channel: int = DEFAULT_BITS_PER_CHANNEL,
) -> str:
    """
    Витягує приховане повідомлення із зображення.
    
    Args:
        encoded_image: Шлях до зображення з прихованим повідомленням
        password: Пароль для дешифрування (опційно)
        bits_per_channel: Кількість молодших бітів на канал
        
    Returns:
        Витягнуте текстове повідомлення
        
    Raises:
        ValueError: Якщо повідомлення не знайдено або пошкоджено
    """
    bits_per_channel = _validate_bits_per_channel(bits_per_channel)
    source = Path(encoded_image)
    
    with Image.open(source) as encoded:
        working, metadata = _prepare_image(encoded)
        
        if not metadata.embed_indexes:
            raise ValueError("У зображенні не знайдено читабельних кольорових каналів.")
        
        # Читаємо біти
        bit_stream = iter(extract_lsb_bits(
            list(working.getdata()),
            metadata.embed_indexes,
            bits_per_channel,
        ))
        
        # Читаємо заголовок
        header_bits = HEADER_SIZE * 8
        header_bytes = bits_to_bytes(bit_stream, header_bits)
        payload_length = parse_header(header_bytes)
        
        # Читаємо повідомлення
        payload_bits = payload_length * 8
        payload_bytes = bits_to_bytes(bit_stream, payload_bits)
        
        return decrypt_payload(payload_bytes, password)


def analyze_images(
    original_path: str | Path,
    modified_path: str | Path,
) -> DiffReport:
    """
    Аналізує відмінності між двома зображеннями.
    
    Args:
        original_path: Шлях до оригінального зображення
        modified_path: Шлях до модифікованого зображення
        
    Returns:
        Звіт про відмінності
        
    Raises:
        ValueError: Якщо зображення мають різні розміри
    """
    original_file = Path(original_path)
    modified_file = Path(modified_path)
    
    with Image.open(original_file) as original, Image.open(modified_file) as modified:
        if original.size != modified.size:
            raise ValueError("Для аналізу зображення повинні мати однакові розміри.")
        
        original_rgb = original.convert("RGB")
        modified_rgb = modified.convert("RGB")
        
        changed_channels = 0
        total_diff = 0
        max_diff = 0
        
        for orig_pixel, mod_pixel in zip(original_rgb.getdata(), modified_rgb.getdata()):
            for orig_val, mod_val in zip(orig_pixel, mod_pixel):
                diff = abs(orig_val - mod_val)
                if diff:
                    changed_channels += 1
                    total_diff += diff
                    max_diff = max(max_diff, diff)
        
        width, height = original_rgb.size
        total_channels = width * height * len(original_rgb.getbands())
        avg_diff = total_diff / changed_channels if changed_channels else 0.0
    
    return DiffReport(
        total_channels=total_channels,
        changed_channels=changed_channels,
        avg_abs_diff=avg_diff,
        max_abs_diff=max_diff,
        file_size_before=original_file.stat().st_size,
        file_size_after=modified_file.stat().st_size,
    )


def visualize_diff(
    original_path: str | Path,
    modified_path: str | Path,
    output_path: str | Path,
    *,
    amplify: int = 16,
) -> None:
    """
    Створює візуалізацію відмінностей між зображеннями.
    
    Args:
        original_path: Шлях до оригіналу
        modified_path: Шлях до модифікованого зображення
        output_path: Шлях для збереження візуалізації
        amplify: Коефіцієнт підсилення різниці
    """
    with Image.open(original_path) as orig_img, Image.open(modified_path) as mod_img:
        original = orig_img.convert("RGB")
        modified = mod_img.convert("RGB")
        
        diff = ImageChops.difference(original, modified)
        
        if amplify > 1:
            diff = diff.point(lambda x: min(255, x * amplify))
        
        diff.save(output_path)
