from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from groupmates_bot.services.drive import Folder


class PickFolder(CallbackData, prefix="pick"):
    folder_id: str


class NewFolder(CallbackData, prefix="new"):
    pass


def folders_keyboard(folders: list[Folder]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for folder in folders:
        builder.button(text=f"📁 {folder.name}", callback_data=PickFolder(folder_id=folder.id))
    builder.button(text="➕ Создать новую папку", callback_data=NewFolder())
    builder.adjust(1)
    return builder.as_markup()
