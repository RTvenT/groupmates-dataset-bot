import logging
from collections.abc import Sequence

from groupmates_bot.scanner.base import FolderSnapshot, ScanTask
from groupmates_bot.services.drive import DriveService, Folder
from groupmates_bot.services.locks import KeyedLocks

log = logging.getLogger(__name__)


class CloudScanner:
    """Обходит папки датасета на Диске и прогоняет по ним задачи (запуск по требованию)."""

    def __init__(
        self,
        drive: DriveService,
        folder_locks: KeyedLocks,
        tasks: Sequence[ScanTask],
    ) -> None:
        self._drive = drive
        self._folder_locks = folder_locks
        self._tasks = list(tasks)

    async def scan_once(self) -> list[FolderSnapshot]:
        folders = await self._drive.list_folders(limit=None)
        snapshots = []
        for folder in folders:
            try:
                snapshots.append(await self._scan_folder(folder))
            except Exception:
                log.exception("scan of folder %r failed", folder.name)

        for task in self._tasks:
            try:
                await task.on_scan_complete(snapshots)
            except Exception:
                log.exception("task %s failed on scan completion", task.name)
        return snapshots

    async def _scan_folder(self, folder: Folder) -> FolderSnapshot:
        async with self._folder_locks(folder.id):
            snapshot = FolderSnapshot(folder=folder, files=await self._drive.list_images(folder.id))
            for task in self._tasks:
                try:
                    snapshot = await task.process_folder(snapshot) or snapshot
                except Exception:
                    log.exception("task %s failed on folder %r", task.name, folder.name)
        return snapshot
