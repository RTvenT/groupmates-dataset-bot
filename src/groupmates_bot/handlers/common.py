from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from groupmates_bot.handlers.folders import send_folders
from groupmates_bot.services.drive import DriveService


async def start(message: Message, state: FSMContext, drive: DriveService) -> None:
    await state.clear()
    await send_folders(message, drive)


async def folders_cmd(message: Message, drive: DriveService) -> None:
    await send_folders(message, drive)


async def fallback_text(message: Message) -> None:
    await message.answer("Нажми /start, чтобы выбрать папку.")


def create_router() -> Router:
    router = Router(name="common")
    router.message.register(start, CommandStart())
    router.message.register(folders_cmd, Command("folders"))
    router.message.register(fallback_text, F.text)
    return router
