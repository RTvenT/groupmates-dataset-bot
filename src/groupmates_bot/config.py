from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    # Папка, внутри которой бот показывает/создает папки. "root" = корень "Мой диск"
    root_folder_id: str = "root"
    # Разрешённые Telegram user id через запятую (пусто = доступ всем!)
    allowed_users: Annotated[frozenset[int], NoDecode] = frozenset()
    # Telegram user id админов через запятую: им доступна /admin (удаление фото)
    admin_users: Annotated[frozenset[int], NoDecode] = frozenset()
    # Прокси для Telegram API, например socks5://127.0.0.1:1080 или http://127.0.0.1:8080
    telegram_proxy: str | None = None

    # Сторона квадрата, к которому приводятся фото (вход YOLO)
    image_size: int = Field(default=640, gt=0)

    google_credentials_file: Path = Path("credentials.json")
    google_token_file: Path = Path("token.json")

    @field_validator("allowed_users", "admin_users", mode="before")
    @classmethod
    def _split_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return frozenset(int(x) for x in value.split(",") if x.strip())
        return value
