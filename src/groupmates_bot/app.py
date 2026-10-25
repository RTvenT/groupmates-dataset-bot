import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from groupmates_bot.config import Settings
from groupmates_bot.handlers import setup_routers
from groupmates_bot.middlewares.access import AccessMiddleware
from groupmates_bot.services.drive import DriveService
from groupmates_bot.services.google_auth import get_credentials

log = logging.getLogger(__name__)


def build_dispatcher(settings: Settings, drive: DriveService) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage(), drive=drive)
    access = AccessMiddleware(settings.allowed_users)
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)
    dp.include_router(setup_routers())
    return dp


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    if not settings.allowed_users:
        log.warning("ALLOWED_USERS пуст — бот доступен всем!")

    credentials = await asyncio.to_thread(
        get_credentials, settings.google_credentials_file, settings.google_token_file
    )
    drive = DriveService(credentials, settings.root_folder_id)

    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = build_dispatcher(settings, drive)
    await dp.start_polling(bot)
