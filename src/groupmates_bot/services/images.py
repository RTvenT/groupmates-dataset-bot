"""Подготовка изображений под вход YOLO: квадрат size x size с сохранением пропорций."""

import io

from PIL import Image, ImageOps

# Серый фон, которым Ultralytics дополняет изображения при letterbox
PAD_COLOR = (114, 114, 114)
JPEG_QUALITY = 95


def letterbox(data: bytes, size: int = 640) -> bytes:
    """Вписывает картинку в квадрат size x size без искажений, поля заливает серым.

    Ориентация из EXIF применяется заранее, иначе фото с телефона, присланные
    файлом, оказались бы повёрнутыми. Результат — JPEG без метаданных.
    """
    with Image.open(io.BytesIO(data)) as src:
        image = ImageOps.exif_transpose(src).convert("RGB")

    scale = size / max(image.size)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.resize(new_size, Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (size, size), PAD_COLOR)
    canvas.paste(image, ((size - image.width) // 2, (size - image.height) // 2))

    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=JPEG_QUALITY)
    return out.getvalue()
