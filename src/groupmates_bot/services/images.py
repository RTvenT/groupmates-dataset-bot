"""Подготовка изображений под вход YOLO: квадрат size x size."""

import io

from PIL import Image, ImageOps

JPEG_QUALITY = 95


def resize_square(data: bytes, size: int = 640) -> bytes:
    """Растягивает картинку ровно до size x size, не сохраняя пропорции и без полей.

    Ориентация из EXIF применяется заранее, иначе фото с телефона, присланные
    файлом, оказались бы повёрнутыми. Результат — JPEG без метаданных.
    """
    with Image.open(io.BytesIO(data)) as src:
        image = ImageOps.exif_transpose(src).convert("RGB")

    out = io.BytesIO()
    image.resize((size, size), Image.Resampling.LANCZOS).save(
        out, format="JPEG", quality=JPEG_QUALITY
    )
    return out.getvalue()
