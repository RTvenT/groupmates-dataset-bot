import dataclasses
import logging

from groupmates_bot.scanner.base import FolderSnapshot, ScanTask
from groupmates_bot.services.dataset import DatasetService

log = logging.getLogger(__name__)


class RenumberTask(ScanTask):
    """Закрывает пропуски в нумерации, например после удаления фото прямо на Диске:
    1, 2, 4, 5 -> 1, 2, 3, 4.

    Номера только уменьшаются, а порядок файлов сохраняется, поэтому если
    переименование оборвётся на середине, следующий проход просто доделает его.
    """

    name = "renumber"

    def __init__(self, dataset: DatasetService) -> None:
        self._dataset = dataset

    async def process_folder(self, snapshot: FolderSnapshot) -> FolderSnapshot | None:
        renamed = await self._dataset.renumber_unlocked(snapshot.folder, snapshot.files)
        if not renamed:
            return None
        log.info("folder %r: renamed %d files", snapshot.folder.name, len(renamed))

        new_names = {f.id: f.name for f in renamed}
        files = [dataclasses.replace(f, name=new_names.get(f.id, f.name)) for f in snapshot.files]
        return dataclasses.replace(snapshot, files=files)
