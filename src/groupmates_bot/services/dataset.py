import asyncio

from groupmates_bot.services import images, naming
from groupmates_bot.services.drive import DriveService
from groupmates_bot.services.locks import KeyedLocks


class DatasetService:
    """Добавление фото в датасет: подготовка под YOLO и именование по папке."""

    def __init__(self, drive: DriveService, folder_locks: KeyedLocks, image_size: int) -> None:
        self._drive = drive
        self._folder_locks = folder_locks
        self._image_size = image_size

    async def add_photo(self, folder_id: str, data: bytes) -> str:
        """Загружает фото в папку и возвращает имя, под которым оно сохранено."""
        prepared = await asyncio.to_thread(images.letterbox, data, self._image_size)
        # Под локом папки: иначе два параллельных фото получат один и тот же номер
        async with self._folder_locks(folder_id):
            folder = await self._drive.get_folder(folder_id)
            existing = await self._drive.list_images(folder_id)
            filename = naming.build_name(
                naming.folder_prefix(folder.name), naming.next_index(existing)
            )
            await self._drive.upload_file(prepared, filename, "image/jpeg", folder_id)
        return filename
