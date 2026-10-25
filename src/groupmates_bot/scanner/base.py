from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from groupmates_bot.services.drive import DriveFile, Folder


@dataclass(frozen=True, slots=True)
class FolderSnapshot:
    """Состояние папки на момент сканирования."""

    folder: Folder
    files: list[DriveFile]


class ScanTask(ABC):
    """Задача, которую сканер выполняет над каждой папкой датасета.

    Чтобы добавить новую проверку облака, унаследуйтесь от ScanTask и
    передайте экземпляр в CloudScanner (см. app.build_scanner). Сейчас
    сканирование запускает админ кнопкой в /admin.
    """

    name: str

    @abstractmethod
    async def process_folder(self, snapshot: FolderSnapshot) -> FolderSnapshot | None:
        """Обработать одну папку.

        Вызывается под локом папки, так что загрузки в неё в это время ждут.
        Если задача изменила файлы, она возвращает обновлённый снимок, и
        следующие задачи получат уже его; иначе — None.
        """

    async def on_scan_complete(self, snapshots: Sequence[FolderSnapshot]) -> None:
        """Вызывается после обхода всех папок (для сводных проверок и отчётов)."""
        return None
