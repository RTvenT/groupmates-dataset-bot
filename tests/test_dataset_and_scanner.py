import asyncio
import io

from PIL import Image

from groupmates_bot.scanner import CloudScanner, FolderSnapshot, ScanTask
from groupmates_bot.scanner.tasks import RenumberTask
from groupmates_bot.services.dataset import DatasetService
from groupmates_bot.services.locks import KeyedLocks
from tests.conftest import make_image


def make_services(drive):
    locks = KeyedLocks()
    dataset = DatasetService(drive, locks, image_size=640)
    scanner = CloudScanner(drive, locks, [RenumberTask(drive)], interval=60)
    return dataset, scanner


async def test_parallel_uploads_get_unique_sequential_names(drive):
    folder = drive.add_folder("Андрей Ким")
    dataset, _ = make_services(drive)

    names = await asyncio.gather(
        *(dataset.add_photo(folder.id, make_image(800, 600)) for _ in range(5))
    )

    assert sorted(names) == [f"Andrei_Kim_{i}.jpg" for i in range(1, 6)]
    assert sorted(drive.names(folder.id)) == sorted(names)


async def test_upload_after_deletion_does_not_reuse_taken_number(drive):
    folder = drive.add_folder("Андрей Ким")
    for i in (1, 3, 4):  # №2 удалили, сканер ещё не прошёл
        drive.add_file(folder.id, f"Andrei_Kim_{i}.jpg")
    dataset, _ = make_services(drive)

    assert await dataset.add_photo(folder.id, make_image(10, 10)) == "Andrei_Kim_5.jpg"


async def test_scanner_renumbers_after_deletion(drive):
    folder = drive.add_folder("Андрей Ким")
    for i in (1, 3, 4, 7):
        drive.add_file(folder.id, f"Andrei_Kim_{i}.jpg")
    other = drive.add_folder("Мария")
    drive.add_file(other.id, "Mariia_1.jpg")
    _, scanner = make_services(drive)

    await scanner.scan_once()

    assert drive.names(folder.id) == [f"Andrei_Kim_{i}.jpg" for i in range(1, 5)]
    assert drive.names(other.id) == ["Mariia_1.jpg"]


async def test_uploaded_photo_is_resized_to_square(drive):
    folder = drive.add_folder("Андрей Ким")
    dataset, _ = make_services(drive)
    await dataset.add_photo(folder.id, make_image(1920, 1080))

    (data,) = drive.uploads.values()
    assert Image.open(io.BytesIO(data)).size == (640, 640)


class Boom(ScanTask):
    name = "boom"

    async def process_folder(self, snapshot):
        raise RuntimeError("boom")


class Recorder(ScanTask):
    name = "recorder"

    def __init__(self):
        self.seen: list[list[str]] = []
        self.completed: list[FolderSnapshot] = []

    async def process_folder(self, snapshot):
        self.seen.append([f.name for f in snapshot.files])

    async def on_scan_complete(self, snapshots):
        self.completed = list(snapshots)


async def test_failing_task_does_not_stop_others_and_tasks_see_fresh_snapshot(drive):
    folder = drive.add_folder("Андрей Ким")
    drive.add_file(folder.id, "Andrei_Kim_2.jpg")
    recorder = Recorder()
    scanner = CloudScanner(drive, KeyedLocks(), [Boom(), RenumberTask(drive), recorder], 60)

    await scanner.scan_once()

    # Boom упал, но RenumberTask отработал, а Recorder увидел уже новые имена
    assert recorder.seen == [["Andrei_Kim_1.jpg"]]
    assert [s.folder.id for s in recorder.completed] == [folder.id]


async def test_scanner_start_stop(drive):
    drive.add_folder("Пусто")
    _, scanner = make_services(drive)
    await scanner.start()
    await asyncio.sleep(0.01)
    await scanner.stop()
