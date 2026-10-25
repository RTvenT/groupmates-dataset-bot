import asyncio
import io
from dataclasses import dataclass
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_FOLDERS = 30
PAGE_SIZE = 1000


@dataclass(frozen=True, slots=True)
class Folder:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    created_time: datetime


class DriveService:
    """Асинхронная обёртка над Google Drive API v3.

    Клиент googleapiclient синхронный и не потокобезопасен, поэтому каждый
    вызов создаёт свой сервис и выполняется в отдельном потоке.
    """

    def __init__(self, credentials: Credentials, root_folder_id: str) -> None:
        self._credentials = credentials
        self.root_folder_id = root_folder_id

    def _client(self):
        return build("drive", "v3", credentials=self._credentials, cache_discovery=False)

    async def list_folders(self, limit: int | None = MAX_FOLDERS) -> list[Folder]:
        """Подпапки корневой папки по алфавиту; limit=None — все."""
        return await asyncio.to_thread(self._list_folders, limit)

    async def list_images(self, folder_id: str) -> list[DriveFile]:
        return await asyncio.to_thread(self._list_images, folder_id)

    async def create_folder(self, name: str) -> Folder:
        return await asyncio.to_thread(self._create_folder, name)

    async def get_folder(self, folder_id: str) -> Folder:
        return await asyncio.to_thread(self._get_folder, folder_id)

    async def upload_file(self, data: bytes, filename: str, mime: str, folder_id: str) -> str:
        return await asyncio.to_thread(self._upload_file, data, filename, mime, folder_id)

    async def rename_file(self, file_id: str, name: str) -> None:
        await asyncio.to_thread(self._rename_file, file_id, name)

    def _list(self, q: str, fields: str, order_by: str, limit: int | None) -> list[dict]:
        files = self._client().files()
        items: list[dict] = []
        page_token = None
        while True:
            page_size = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(items))
            res = files.list(
                q=q,
                fields=f"nextPageToken, files({fields})",
                orderBy=order_by,
                pageSize=page_size,
                pageToken=page_token,
            ).execute()
            items.extend(res.get("files", []))
            page_token = res.get("nextPageToken")
            if not page_token or (limit is not None and len(items) >= limit):
                return items

    def _list_folders(self, limit: int | None) -> list[Folder]:
        q = f"mimeType='{FOLDER_MIME}' and '{self.root_folder_id}' in parents and trashed=false"
        items = self._list(q, "id,name", "name", limit)
        return [Folder(id=f["id"], name=f["name"]) for f in items]

    def _list_images(self, folder_id: str) -> list[DriveFile]:
        q = f"mimeType contains 'image/' and '{folder_id}' in parents and trashed=false"
        items = self._list(q, "id,name,mimeType,createdTime", "createdTime", None)
        return [
            DriveFile(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                created_time=datetime.fromisoformat(f["createdTime"].replace("Z", "+00:00")),
            )
            for f in items
        ]

    def _create_folder(self, name: str) -> Folder:
        meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [self.root_folder_id]}
        res = self._client().files().create(body=meta, fields="id,name").execute()
        return Folder(id=res["id"], name=res["name"])

    def _get_folder(self, folder_id: str) -> Folder:
        res = self._client().files().get(fileId=folder_id, fields="id,name").execute()
        return Folder(id=res["id"], name=res["name"])

    def _upload_file(self, data: bytes, filename: str, mime: str, folder_id: str) -> str:
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=False)
        meta = {"name": filename, "parents": [folder_id]}
        return (
            self._client().files().create(body=meta, media_body=media, fields="id").execute()["id"]
        )

    def _rename_file(self, file_id: str, name: str) -> None:
        self._client().files().update(fileId=file_id, body={"name": name}).execute()
