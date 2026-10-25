import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from groupmates_bot.config import Settings
from groupmates_bot.handlers import setup_routers
from groupmates_bot.middlewares.access import AccessMiddleware
from groupmates_bot.scanner import CloudScanner
from groupmates_bot.scanner.tasks import RenumberTask
from groupmates_bot.services.dataset import DatasetService
from groupmates_bot.services.drive import DriveService
from groupmates_bot.services.google_auth import get_credentials
from groupmates_bot.services.locks import KeyedLocks

log = logging.getLogger(__name__)


def build_dispatcher(
    settings: Settings, drive: DriveService, dataset: DatasetService
) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage(), drive=drive, dataset=dataset)
    access = AccessMiddleware(settings.allowed_users)
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)
    dp.include_router(setup_routers())
    return dp


def build_scanner(
    settings: Settings, drive: DriveService, folder_locks: KeyedLocks
) -> CloudScanner:
    # Новые проверки облака добавляются сюда
    tasks = [RenumberTask(drive)]
    return CloudScanner(drive, folder_locks, tasks, interval=settings.scan_interval)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    if not settings.allowed_users:
        log.warning("ALLOWED_USERS пуст — бот доступен всем!")

    credentials = await asyncio.to_thread(
        get_credentials, settings.google_credentials_file, settings.google_token_file
    )
    drive = DriveService(credentials, settings.root_folder_id)
    folder_locks = KeyedLocks()
    dataset = DatasetService(drive, folder_locks, settings.image_size)

    session = AiohttpSession(proxy=settings.telegram_proxy) if settings.telegram_proxy else None
    bot = Bot(token=settings.bot_token.get_secret_value(), session=session)
    dp = build_dispatcher(settings, drive, dataset)

    if settings.scan_interval > 0:
        scanner = build_scanner(settings, drive, folder_locks)
        dp.startup.register(scanner.start)
        dp.shutdown.register(scanner.stop)

    await dp.start_polling(bot)
