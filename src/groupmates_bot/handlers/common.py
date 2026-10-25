from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from groupmates_bot.handlers.folders import send_folders
from groupmates_bot.services.drive import DriveService

router = Router(name="common")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, drive: DriveService) -> None:
    await state.clear()
    await send_folders(message, drive)


@router.message(Command("folders"))
async def folders_cmd(message: Message, drive: DriveService) -> None:
    await send_folders(message, drive)


@router.message(F.text)
async def fallback_text(message: Message) -> None:
    await message.answer("Нажми /start, чтобы выбрать папку.")
