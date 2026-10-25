import dataclasses
import logging

from groupmates_bot.scanner.base import FolderSnapshot, ScanTask
from groupmates_bot.services import naming
from groupmates_bot.services.drive import DriveService

log = logging.getLogger(__name__)


class RenumberTask(ScanTask):
    """Закрывает пропуски в нумерации после удаления фото: 1, 2, 4, 5 -> 1, 2, 3, 4.

    Номера только уменьшаются, а порядок файлов сохраняется, поэтому если
    переименование оборвётся на середине, следующий проход просто доделает его.
    """

    name = "renumber"

    def __init__(self, drive: DriveService) -> None:
        self._drive = drive

    async def process_folder(self, snapshot: FolderSnapshot) -> FolderSnapshot | None:
        prefix = naming.folder_prefix(snapshot.folder.name)
        renames = naming.plan_renumbering(snapshot.files, prefix)
        if not renames:
            return None

        new_names = {}
        for rename in renames:
            await self._drive.rename_file(rename.file.id, rename.new_name)
            new_names[rename.file.id] = rename.new_name
        log.info("folder %r: renamed %d files", snapshot.folder.name, len(new_names))

        files = [dataclasses.replace(f, name=new_names.get(f.id, f.name)) for f in snapshot.files]
        return dataclasses.replace(snapshot, files=files)
