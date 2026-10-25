import asyncio
import io
import itertools
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

from groupmates_bot.services.drive import DriveFile, Folder


class FakeDrive:
    """In-memory замена DriveService с теми же async-методами."""

    def __init__(self) -> None:
        self.folders: dict[str, Folder] = {}
        self.files: dict[str, tuple[str, DriveFile]] = {}  # id -> (folder_id, file)
        self.uploads: dict[str, bytes] = {}
        self._ids = itertools.count(1)
        self._clock = datetime(2026, 1, 1, tzinfo=UTC)

    def add_folder(self, name: str) -> Folder:
        folder = Folder(id=f"folder{next(self._ids)}", name=name)
        self.folders[folder.id] = folder
        return folder

    def add_file(self, folder_id: str, name: str) -> DriveFile:
        self._clock += timedelta(seconds=1)
        file = DriveFile(f"file{next(self._ids)}", name, "image/jpeg", self._clock)
        self.files[file.id] = (folder_id, file)
        return file

    def names(self, folder_id: str) -> list[str]:
        files = [f for fid, f in self.files.values() if fid == folder_id]
        return [f.name for f in sorted(files, key=lambda f: f.created_time)]

    async def list_folders(self, limit=None):
        return sorted(self.folders.values(), key=lambda f: f.name)[:limit]

    async def list_images(self, folder_id):
        await asyncio.sleep(0)  # даём другим корутинам вклиниться, как при реальном I/O
        files = [f for fid, f in self.files.values() if fid == folder_id]
        return sorted(files, key=lambda f: f.created_time)

    async def get_folder(self, folder_id):
        return self.folders[folder_id]

    async def upload_file(self, data, filename, mime, folder_id):
        # загрузка дольше листинга: без лока параллельные фото успели бы взять один номер
        await asyncio.sleep(0.01)
        file = self.add_file(folder_id, filename)
        self.uploads[file.id] = data
        return file.id

    async def rename_file(self, file_id, name):
        folder_id, file = self.files[file_id]
        self.files[file_id] = (
            folder_id,
            DriveFile(file.id, name, file.mime_type, file.created_time),
        )


@pytest.fixture
def drive() -> FakeDrive:
    return FakeDrive()


def make_image(width: int, height: int, color=(255, 0, 0), fmt="JPEG", exif=None) -> bytes:
    out = io.BytesIO()
    kwargs = {"exif": exif} if exif is not None else {}
    Image.new("RGB", (width, height), color).save(out, format=fmt, **kwargs)
    return out.getvalue()
