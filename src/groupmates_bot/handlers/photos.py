import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from groupmates_bot.services.drive import DriveService

router = Router(name="photos")
log = logging.getLogger(__name__)


@router.message(F.photo | F.document.mime_type.startswith("image/"))
async def upload_photo(message: Message, state: FSMContext, bot: Bot, drive: DriveService) -> None:
    data = await state.get_data()
    folder_id = data.get("folder_id")
    if not folder_id:
        await message.answer("Сначала выбери папку — /start")
        return

    if message.photo:
        file = message.photo[-1]  # максимальное разрешение
        ext, mime = "jpg", "image/jpeg"
    else:  # фото, отправленное как файл (без сжатия)
        file = message.document
        mime = file.mime_type or "application/octet-stream"
        name = file.file_name or "img.jpg"
        ext = name.rsplit(".", 1)[-1] if "." in name else "jpg"

    buffer = await bot.download(file)
    filename = f"{datetime.now():%Y%m%d_%H%M%S}_{file.file_unique_id}.{ext}"
    try:
        await drive.upload_file(buffer.getvalue(), filename, mime, folder_id)
    except Exception:
        log.exception("upload failed")
        await message.answer("❌ Не удалось загрузить файл, попробуй ещё раз.")
        return
    await message.answer(f"☁️ Загружено в «{data['folder_name']}»")
