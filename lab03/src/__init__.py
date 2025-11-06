from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple
from PIL import Image, ImageChops

HEADER_MAGIC = b"LSBMSG1"
DEFAULT_BITS_PER_CHANNEL = 1
MIN_BITS_PER_CHANNEL = 1
MAX_BITS_PER_CHANNEL = 2
_ALPHA_BANDS = {"A"}


class _BitCursor:
    __slots__ = ("_data", "_bit_length", "_bit_index")

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._bit_length = len(data) * 8
        self._bit_index = 0

    @property
    def total_bits(self) -> int:
        return self._bit_length

    @property
    def remaining_bits(self) -> int:
        return self._bit_length - self._bit_index

    @property
    def has_bits(self) -> bool:
        return self._bit_index < self._bit_length

    def take(self, width: int) -> int | None:
        if self.remaining_bits < width:
            return None
        value = 0
        for _ in range(width):
            byte_index = self._bit_index // 8
            bit_offset = 7 - (self._bit_index % 8)
            bit = (self._data[byte_index] >> bit_offset) & 1
            value = (value << 1) | bit
            self._bit_index += 1
        return value


@dataclass(slots=True)
class EmbedReport:
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
        if self.capacity_bits == 0:
            return 0.0
        return self.payload_bits / self.capacity_bits


@dataclass(slots=True)
class DiffReport:
    total_channels: int
    changed_channels: int
    avg_abs_diff: float
    max_abs_diff: int
    file_size_before: int
    file_size_after: int


def hide_message(
    input_image: str | Path,
    output_image: str | Path,
    message: str,
    *,
    password: str | None = None,
    bits_per_channel: int = DEFAULT_BITS_PER_CHANNEL,
) -> EmbedReport:
    bits_per_channel = _validate_bits(bits_per_channel)
    source = Path(input_image)
    target = Path(output_image)
    payload = _build_payload(message, password)
    bit_cursor = _BitCursor(payload)
    payload_bit_length = bit_cursor.total_bits
    with Image.open(source) as original:
        working, embed_indexes = _prepare_image(original)
        if not embed_indexes:
            raise ValueError("У зображенні не знайдено записуваних колірних каналів.")
        width, height = working.size
        channels_used = len(embed_indexes)
        total_pixels = width * height
        capacity_bits = total_pixels * channels_used * bits_per_channel
        if payload_bit_length > capacity_bits:
            raise ValueError(
                f"Повідомлення перевищує ємність: потрібно {payload_bit_length} бітів, але зображення може зберігати тільки {capacity_bits} бітів."
            )
        pixels: List[Sequence[int]] = list(working.getdata())
        pixels_touched = 0
        mask = (1 << bits_per_channel) - 1
        exhausted = False
        for idx, pixel in enumerate(pixels):
            if not bit_cursor.has_bits:
                break
            pixel_list = list(pixel)
            pixel_changed = False
            for channel_idx in embed_indexes:
                chunk = bit_cursor.take(bits_per_channel)
                if chunk is None:
                    exhausted = True
                    break
                new_value = (pixel_list[channel_idx] & ~mask) | chunk
                if new_value != pixel_list[channel_idx]:
                    pixel_changed = True
                pixel_list[channel_idx] = new_value
            if pixel_changed:
                pixels[idx] = tuple(pixel_list)
                pixels_touched += 1
            if exhausted:
                break
        if bit_cursor.has_bits:
            raise RuntimeError(
                "Не вдалося вбудувати весь корисний вантаж в зображення."
            )
        encoded = Image.new(working.mode, working.size)
        encoded.putdata(pixels)
        encoded.save(target)
    file_size_before = source.stat().st_size
    file_size_after = target.stat().st_size
    return EmbedReport(
        payload_bits=payload_bit_length,
        capacity_bits=capacity_bits,
        total_pixels=total_pixels,
        channels_used=channels_used,
        bits_per_channel=bits_per_channel,
        pixels_touched=pixels_touched,
        file_size_before=file_size_before,
        file_size_after=file_size_after,
    )


def extract_message(
    encoded_image: str | Path,
    *,
    password: str | None = None,
    bits_per_channel: int = DEFAULT_BITS_PER_CHANNEL,
) -> str:
    bits_per_channel = _validate_bits(bits_per_channel)
    source = Path(encoded_image)
    with Image.open(source) as encoded:
        working, embed_indexes = _prepare_image(encoded)
        if not embed_indexes:
            raise ValueError("У зображенні не знайдено читабельних колірних каналів.")
        bit_stream = iter(_read_bits(working, embed_indexes, bits_per_channel))
        header_size_bytes = len(HEADER_MAGIC) + 4
        header_bits_needed = header_size_bytes * 8
        header_bytes = _read_bits_to_bytes(bit_stream, header_bits_needed)
        magic = header_bytes[: len(HEADER_MAGIC)]
        if magic != HEADER_MAGIC:
            raise ValueError("Вбудований корисний вантаж не виявлено.")
        payload_len = struct.unpack(">I", header_bytes[len(HEADER_MAGIC) :])[0]
        payload_bits_needed = payload_len * 8
        payload_bytes = _read_bits_to_bytes(bit_stream, payload_bits_needed)
        decrypted = _xor_with_stream(payload_bytes, password)
        return decrypted.decode("utf-8")


def analyze_images(original_path: str | Path, modified_path: str | Path) -> DiffReport:
    original_file = Path(original_path)
    modified_file = Path(modified_path)
    with Image.open(original_file) as original, Image.open(modified_file) as modified:
        if original.size != modified.size:
            raise ValueError("Для аналізу зображення повинні мати однакові розміри.")
        base_mode = "RGB"
        original_rgb = original.convert(base_mode)
        modified_rgb = modified.convert(base_mode)
        changed_channels = 0
        total_diff = 0
        max_diff = 0
        for a, b in zip(original_rgb.getdata(), modified_rgb.getdata()):
            for channel_a, channel_b in zip(a, b):
                diff = abs(channel_a - channel_b)
                if diff:
                    changed_channels += 1
                    total_diff += diff
                    if diff > max_diff:
                        max_diff = diff
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
    with Image.open(original_path) as original_img, Image.open(
        modified_path
    ) as modified_img:
        original = original_img.convert("RGB")
        modified = modified_img.convert("RGB")
        diff = None
        try:
            diff = ImageChops.difference(original, modified)
            if amplify > 1:
                diff = diff.point(lambda x: min(255, x * amplify))
            diff.save(output_path)
        finally:
            original.close()
            modified.close()
            if diff is not None:
                diff.close()


def _build_payload(message: str, password: str | None) -> bytes:
    body = message.encode("utf-8")
    encrypted = _xor_with_stream(body, password)
    return HEADER_MAGIC + struct.pack(">I", len(encrypted)) + encrypted


def _xor_with_stream(data: bytes, password: str | None) -> bytes:
    if not password:
        return data
    seed = password.encode("utf-8")
    stream = bytearray()
    counter = 0
    while len(stream) < len(data):
        counter_bytes = counter.to_bytes(4, "big")
        stream.extend(hashlib.sha256(seed + counter_bytes).digest())
        counter += 1
    return bytes(a ^ b for a, b in zip(data, stream))


def _prepare_image(image: Image.Image) -> Tuple[Image.Image, Tuple[int, ...]]:
    mode = "RGBA" if "A" in image.getbands() else "RGB"
    converted = image.convert(mode)
    embed_indexes = tuple(
        idx for idx, band in enumerate(converted.getbands()) if band not in _ALPHA_BANDS
    )
    return converted, embed_indexes


def _read_bits_to_bytes(bit_iter: Iterator[int], bit_count: int) -> bytes:
    if bit_count < 0:
        raise ValueError("bit_count повинен бути невід'ємним.")
    out = bytearray()
    accumulator = 0
    count = 0
    for _ in range(bit_count):
        try:
            bit = next(bit_iter)
        except StopIteration:
            raise ValueError(
                "Несподіване закінчення даних під час читання вбудованих бітів."
            )
        accumulator = (accumulator << 1) | (bit & 1)
        count += 1
        if count == 8:
            out.append(accumulator)
            accumulator = 0
            count = 0
    if count:
        accumulator <<= 8 - count
        out.append(accumulator)
    return bytes(out)


def _read_bits(
    image: Image.Image, embed_indexes: Tuple[int, ...], bits_per_channel: int
) -> Iterable[int]:
    mask = (1 << bits_per_channel) - 1
    for pixel in image.getdata():
        for channel_idx in embed_indexes:
            chunk = pixel[channel_idx] & mask
            for shift in range(bits_per_channel - 1, -1, -1):
                yield (chunk >> shift) & 1


def _validate_bits(bits_per_channel: int) -> int:
    if not (MIN_BITS_PER_CHANNEL <= bits_per_channel <= MAX_BITS_PER_CHANNEL):
        raise ValueError(
            f"bits_per_channel повинен бути в межах від {MIN_BITS_PER_CHANNEL} до {MAX_BITS_PER_CHANNEL}, отримано {bits_per_channel}."
        )
    return bits_per_channel


__all__ = [
    "hide_message",
    "extract_message",
    "analyze_images",
    "visualize_diff",
    "EmbedReport",
    "DiffReport",
]
