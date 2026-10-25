"""Админка целиком: апдейты идут через диспетчер, Telegram и Диск подменены."""

import datetime
import itertools

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    EditMessageCaption,
    EditMessageText,
    SendMessage,
    SendPhoto,
)
from aiogram.types import Message, Update

from groupmates_bot.app import build_dispatcher, build_scanner
from groupmates_bot.config import Settings
from groupmates_bot.keyboards.admin import AdminDelete, AdminFolder, AdminPhoto
from groupmates_bot.services.dataset import DatasetService
from groupmates_bot.services.locks import KeyedLocks

ADMIN, USER = 100, 200


class FakeTelegram(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def make_request(self, bot, method, timeout=None):  # noqa: ASYNC109
        self.calls.append(method)
        if isinstance(method, AnswerCallbackQuery | DeleteMessage):
            return True
        return Message(
            message_id=1, date=datetime.datetime.now(), chat={"id": 1, "type": "private"}
        )

    def take(self, kind):
        found = [m for m in self.calls if isinstance(m, kind)]
        self.calls.clear()
        return found


class Harness:
    def __init__(self, drive, allowed_users=""):
        settings = Settings(bot_token="1:x", allowed_users=allowed_users, admin_users=str(ADMIN))
        locks = KeyedLocks()
        dataset = DatasetService(drive, locks, settings.image_size)
        scanner = build_scanner(drive, locks, dataset)
        self.dp = build_dispatcher(settings, drive, dataset, scanner)
        self.tg = FakeTelegram()
        self.bot = Bot("1:x", session=self.tg)
        self._ids = itertools.count(1)

    def _user(self, user_id):
        return {"id": user_id, "is_bot": False, "first_name": "x"}

    async def command(self, text, user=ADMIN):
        n = next(self._ids)
        message = {
            "message_id": n,
            "date": 0,
            "chat": {"id": user, "type": "private"},
            "from": self._user(user),
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": len(text)}],
        }
        await self.dp.feed_update(self.bot, Update(update_id=n, message=message))

    async def press(self, data, user=ADMIN):
        n = next(self._ids)
        query = {
            "id": str(n),
            "from": self._user(user),
            "chat_instance": "c",
            "data": data if isinstance(data, str) else data.pack(),
            "message": {
                "message_id": n,
                "date": 0,
                "chat": {"id": user, "type": "private"},
                "text": "menu",
            },
        }
        await self.dp.feed_update(self.bot, Update(update_id=n, callback_query=query))


def buttons(method):
    return [b for row in method.reply_markup.inline_keyboard for b in row]


def labels(method):
    return [b.text for b in buttons(method)]


@pytest.fixture
def folder(drive):
    folder = drive.add_folder("Андрей Ким")
    for i in range(1, 6):
        drive.add_file(folder.id, f"Andrei_Kim_{i}.jpg")
    return folder


async def test_non_admin_cannot_open_admin(drive, folder):
    h = Harness(drive)
    await h.command("/admin", user=USER)
    (reply,) = h.tg.take(SendMessage)
    assert "Нажми /start" in reply.text

    await h.press(AdminDelete(file_id=drive.file_by_name(folder.id, "Andrei_Kim_1.jpg").id), USER)
    assert len(drive.files) == 5


async def test_admin_is_allowed_even_if_missing_from_allowed_users(drive, folder):
    h = Harness(drive, allowed_users=str(USER))
    await h.command("/admin")
    (menu,) = h.tg.take(SendMessage)
    assert "📁 Андрей Ким" in labels(menu)


async def test_full_delete_flow(drive, folder):
    h = Harness(drive)

    await h.command("/admin")
    (menu,) = h.tg.take(SendMessage)
    assert labels(menu) == ["📁 Андрей Ким", "🔄 Проверить нумерацию на Диске"]

    await h.press(buttons(menu)[0].callback_data)
    (listing,) = h.tg.take(EditMessageText)
    assert "5 фото" in listing.text
    assert labels(listing) == ["1", "2", "3", "4", "5", "⬅️ К папкам"]

    await h.press(buttons(listing)[2].callback_data)  # фото №3
    (preview,) = h.tg.take(SendPhoto)
    assert preview.caption.startswith("Andrei_Kim_3.jpg")
    assert labels(preview) == ["🗑 Удалить", "Отмена"]

    await h.press(buttons(preview)[0].callback_data)
    calls = h.tg.calls[:]
    (done,) = [m for m in calls if isinstance(m, EditMessageCaption)]
    (fresh,) = [m for m in calls if isinstance(m, SendMessage)]
    assert "Andrei_Kim_3.jpg удалено" in done.caption
    assert "переименовано 2" in done.caption
    assert labels(fresh) == ["1", "2", "3", "4", "⬅️ К папкам"]
    assert drive.names(folder.id) == [f"Andrei_Kim_{i}.jpg" for i in range(1, 5)]


async def test_cancel_deletes_preview(drive, folder):
    h = Harness(drive)
    await h.press("adm_c")
    assert h.tg.take(DeleteMessage)
    assert len(drive.files) == 5


async def test_pagination(drive):
    folder = drive.add_folder("Большая")
    for i in range(1, 46):
        drive.add_file(folder.id, f"Bolshaia_{i}.jpg")
    h = Harness(drive)

    await h.press(AdminFolder(folder_id=folder.id))
    (page1,) = h.tg.take(EditMessageText)
    assert "стр. 1/2" in page1.text
    assert labels(page1)[:3] == ["1", "2", "3"]
    assert labels(page1)[-2:] == ["▶️", "⬅️ К папкам"]

    await h.press(AdminFolder(folder_id=folder.id, page=1))
    (page2,) = h.tg.take(EditMessageText)
    assert labels(page2) == [str(i) for i in range(41, 46)] + ["◀️", "⬅️ К папкам"]


async def test_rescan_button_fixes_external_gaps(drive):
    folder = drive.add_folder("Андрей Ким")
    for i in (1, 4):
        drive.add_file(folder.id, f"Andrei_Kim_{i}.jpg")
    h = Harness(drive)

    await h.press("adm_scan")

    assert drive.names(folder.id) == ["Andrei_Kim_1.jpg", "Andrei_Kim_2.jpg"]


def test_callback_data_fits_telegram_limit():
    long_id = "1" + "A" * 43  # id файлов и папок на Диске бывают до 44 символов
    for data in (
        AdminFolder(folder_id=long_id, page=999),
        AdminPhoto(file_id=long_id),
        AdminDelete(file_id=long_id),
    ):
        assert len(data.pack().encode()) <= 64
