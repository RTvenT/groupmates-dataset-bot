from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from groupmates_bot.services import naming
from groupmates_bot.services.drive import DriveFile, Folder

PHOTOS_PER_PAGE = 40
PHOTOS_PER_ROW = 5


class AdminMenu(CallbackData, prefix="adm"):
    pass


class AdminRescan(CallbackData, prefix="adm_scan"):
    pass


class AdminFolder(CallbackData, prefix="adm_f"):
    folder_id: str
    page: int = 0


class AdminPhoto(CallbackData, prefix="adm_p"):
    file_id: str


class AdminDelete(CallbackData, prefix="adm_d"):
    file_id: str


class AdminCancel(CallbackData, prefix="adm_c"):
    pass


def admin_menu_keyboard(folders: list[Folder]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for folder in folders:
        builder.button(text=f"📁 {folder.name}", callback_data=AdminFolder(folder_id=folder.id))
    builder.button(text="🔄 Проверить нумерацию на Диске", callback_data=AdminRescan())
    builder.adjust(1)
    return builder.as_markup()


def page_count(total: int) -> int:
    return max(1, -(-total // PHOTOS_PER_PAGE))


def folder_photos_keyboard(
    folder: Folder, files: list[DriveFile], page: int
) -> InlineKeyboardMarkup:
    """Сетка номеров фото (files уже отсортированы по номеру) с листанием."""
    builder = InlineKeyboardBuilder()
    chunk = files[page * PHOTOS_PER_PAGE : (page + 1) * PHOTOS_PER_PAGE]
    for file in chunk:
        index = naming.parse_index(file.name)
        builder.button(
            text=str(index) if index is not None else file.name[:12],
            callback_data=AdminPhoto(file_id=file.id),
        )
    rows = [PHOTOS_PER_ROW] * -(-len(chunk) // PHOTOS_PER_ROW)

    nav = 0
    if page > 0:
        builder.button(text="◀️", callback_data=AdminFolder(folder_id=folder.id, page=page - 1))
        nav += 1
    if page < page_count(len(files)) - 1:
        builder.button(text="▶️", callback_data=AdminFolder(folder_id=folder.id, page=page + 1))
        nav += 1
    if nav:
        rows.append(nav)

    builder.button(text="⬅️ К папкам", callback_data=AdminMenu())
    rows.append(1)
    builder.adjust(*rows)
    return builder.as_markup()


def confirm_delete_keyboard(file: DriveFile) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить", callback_data=AdminDelete(file_id=file.id))
    builder.button(text="Отмена", callback_data=AdminCancel())
    return builder.as_markup()
