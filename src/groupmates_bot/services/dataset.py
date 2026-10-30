import asyncio
import dataclasses
import logging
from dataclasses import dataclass

from groupmates_bot.services import images, naming
from groupmates_bot.services.drive import DriveFile, DriveService, Folder
from groupmates_bot.services.locks import KeyedLocks

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeletedPhoto:
    name: str
    folder: Folder
    renamed: int  # сколько файлов перенумеровано после удаления


class DatasetService:
    """Операции с датасетом: добавление и удаление фото, поддержание нумерации.

    Всё, что меняет имена файлов в папке, выполняется под локом этой папки.
    """

    def __init__(self, drive: DriveService, folder_locks: KeyedLocks, image_size: int) -> None:
        self._drive = drive
        self._folder_locks = folder_locks
        self._image_size = image_size

    async def add_photo(self, folder_id: str, data: bytes) -> str:
        """Загружает фото в папку и возвращает имя, под которым оно сохранено."""
        prepared = await asyncio.to_thread(images.resize_square, data, self._image_size)
        # Под локом папки: иначе два параллельных фото получат один и тот же номер
        async with self._folder_locks(folder_id):
            folder = await self._drive.get_folder(folder_id)
            existing = await self._drive.list_images(folder_id)
            filename = naming.build_name(
                naming.folder_prefix(folder.name), naming.next_index(existing)
            )
            await self._drive.upload_file(prepared, filename, "image/jpeg", folder_id)
        return filename

    async def delete_photo(self, file_id: str) -> DeletedPhoto | None:
        """Удаляет фото (в корзину Диска) и закрывает пропуск в нумерации папки.

        Возвращает None, если файла уже нет.
        """
        file = await self._drive.get_file(file_id)
        if file is None or file.folder_id is None:
            return None
        async with self._folder_locks(file.folder_id):
            # пока ждали лок, файл могли удалить или переименовать
            file = await self._drive.get_file(file_id)
            if file is None or file.folder_id is None:
                return None
            await self._drive.trash_file(file.id)
            folder = await self._drive.get_folder(file.folder_id)
            remaining = await self._drive.list_images(folder.id)
            renamed = await self.renumber_unlocked(folder, remaining)
        log.info("deleted %s from %r, renamed %d", file.name, folder.name, len(renamed))
        return DeletedPhoto(name=file.name, folder=folder, renamed=len(renamed))

    async def renumber_unlocked(self, folder: Folder, files: list[DriveFile]) -> list[DriveFile]:
        """Делает нумерацию папки сплошной (1..N); возвращает переименованные файлы.

        Вызывающий код должен держать лок папки.
        """
        renamed = []
        for rename in naming.plan_renumbering(files, naming.folder_prefix(folder.name)):
            await self._drive.rename_file(rename.file.id, rename.new_name)
            renamed.append(dataclasses.replace(rename.file, name=rename.new_name))
        return renamed
