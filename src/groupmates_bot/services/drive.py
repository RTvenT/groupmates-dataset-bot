import asyncio
import io
from dataclasses import dataclass

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_FOLDERS = 30


@dataclass(frozen=True, slots=True)
class Folder:
    id: str
    name: str


class DriveService:
    """Асинхронная обёртка над Google Drive API v3.

    Клиент googleapiclient синхронный и не потокобезопасен, поэтому каждый
    вызов создаёт свой сервис и выполняется в отдельном потоке.
    """

    def __init__(self, credentials: Credentials, root_folder_id: str) -> None:
        self._credentials = credentials
        self._root_folder_id = root_folder_id

    def _client(self):
        return build("drive", "v3", credentials=self._credentials, cache_discovery=False)

    async def list_folders(self) -> list[Folder]:
        return await asyncio.to_thread(self._list_folders)

    async def create_folder(self, name: str) -> Folder:
        return await asyncio.to_thread(self._create_folder, name)

    async def get_folder(self, folder_id: str) -> Folder:
        return await asyncio.to_thread(self._get_folder, folder_id)

    async def upload_file(self, data: bytes, filename: str, mime: str, folder_id: str) -> str:
        return await asyncio.to_thread(self._upload_file, data, filename, mime, folder_id)

    def _list_folders(self) -> list[Folder]:
        q = f"mimeType='{FOLDER_MIME}' and '{self._root_folder_id}' in parents and trashed=false"
        res = (
            self._client()
            .files()
            .list(q=q, fields="files(id,name)", orderBy="name", pageSize=MAX_FOLDERS)
            .execute()
        )
        return [Folder(id=f["id"], name=f["name"]) for f in res.get("files", [])]

    def _create_folder(self, name: str) -> Folder:
        meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [self._root_folder_id]}
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
