import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from PIL import UnidentifiedImageError

from groupmates_bot.services.dataset import DatasetService

log = logging.getLogger(__name__)


async def upload_photo(
    message: Message, state: FSMContext, bot: Bot, dataset: DatasetService
) -> None:
    data = await state.get_data()
    folder_id = data.get("folder_id")
    if not folder_id:
        await message.answer("Сначала выбери папку — /start")
        return

    # photo[-1] — максимальное разрешение; document — фото, отправленное файлом
    file = message.photo[-1] if message.photo else message.document
    try:
        buffer = await bot.download(file)
        filename = await dataset.add_photo(folder_id, buffer.getvalue())
    except UnidentifiedImageError:
        await message.answer("❌ Не удалось прочитать изображение, пришли его в JPG или PNG.")
        return
    except Exception:
        log.exception("upload failed")
        await message.answer("❌ Не удалось загрузить файл, попробуй ещё раз.")
        return
    await message.answer(f"☁️ Загружено в «{data['folder_name']}» как {filename}")


def create_router() -> Router:
    router = Router(name="photos")
    router.message.register(upload_photo, F.photo | F.document.mime_type.startswith("image/"))
    return router
