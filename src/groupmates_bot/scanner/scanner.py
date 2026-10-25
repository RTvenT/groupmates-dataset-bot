import asyncio
import contextlib
import logging
from collections.abc import Sequence

from groupmates_bot.scanner.base import FolderSnapshot, ScanTask
from groupmates_bot.services.drive import DriveService, Folder
from groupmates_bot.services.locks import KeyedLocks

log = logging.getLogger(__name__)


class CloudScanner:
    """Периодически обходит папки датасета на Диске и прогоняет по ним задачи."""

    def __init__(
        self,
        drive: DriveService,
        folder_locks: KeyedLocks,
        tasks: Sequence[ScanTask],
        interval: float,
    ) -> None:
        self._drive = drive
        self._folder_locks = folder_locks
        self._tasks = list(tasks)
        self._interval = interval
        self._runner: asyncio.Task | None = None

    async def start(self) -> None:
        if self._runner is None:
            self._runner = asyncio.create_task(self._run_forever(), name="cloud-scanner")

    async def stop(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._runner
            self._runner = None

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

    async def _run_forever(self) -> None:
        while True:
            try:
                snapshots = await self.scan_once()
                log.info("cloud scan finished: %d folders", len(snapshots))
            except Exception:
                log.exception("cloud scan failed")
            await asyncio.sleep(self._interval)
