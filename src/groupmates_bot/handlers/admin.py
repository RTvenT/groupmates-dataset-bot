"""Админка: просмотр папок и удаление фото с перенумерацией."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from groupmates_bot.filters.admin import IsAdmin
from groupmates_bot.keyboards.admin import (
    AdminCancel,
    AdminDelete,
    AdminFolder,
    AdminMenu,
    AdminPhoto,
    AdminRescan,
    admin_menu_keyboard,
    confirm_delete_keyboard,
    folder_photos_keyboard,
    page_count,
)
from groupmates_bot.scanner import CloudScanner
from groupmates_bot.services import naming
from groupmates_bot.services.dataset import DatasetService
from groupmates_bot.services.drive import DriveService

MENU_TEXT = "🛠 Админка. Выбери папку, чтобы посмотреть и удалить фото:"


async def render_menu(drive: DriveService) -> tuple[str, InlineKeyboardMarkup]:
    folders = await drive.list_folders(limit=None)
    return MENU_TEXT, admin_menu_keyboard(folders)


async def render_folder(
    drive: DriveService, folder_id: str, page: int
) -> tuple[str, InlineKeyboardMarkup]:
    folder = await drive.get_folder(folder_id)
    files = naming.sort_by_index(await drive.list_images(folder_id))
    pages = page_count(len(files))
    page = min(max(page, 0), pages - 1)

    if not files:
        text = f"📁 {folder.name}: фото нет."
    else:
        text = f"📁 {folder.name}: {len(files)} фото"
        if pages > 1:
            text += f", стр. {page + 1}/{pages}"
        text += ".\nНажми на номер, чтобы посмотреть фото и удалить его."
    return text, folder_photos_keyboard(folder, files, page)


async def admin_cmd(message: Message, drive: DriveService) -> None:
    text, markup = await render_menu(drive)
    await message.answer(text, reply_markup=markup)


async def show_menu(callback: CallbackQuery, drive: DriveService) -> None:
    await callback.answer()
    text, markup = await render_menu(drive)
    await callback.message.edit_text(text, reply_markup=markup)


async def show_folder(
    callback: CallbackQuery, callback_data: AdminFolder, drive: DriveService
) -> None:
    await callback.answer()
    text, markup = await render_folder(drive, callback_data.folder_id, callback_data.page)
    await callback.message.edit_text(text, reply_markup=markup)


async def show_photo(
    callback: CallbackQuery, callback_data: AdminPhoto, drive: DriveService
) -> None:
    file = await drive.get_file(callback_data.file_id)
    if file is None:
        await callback.answer("Это фото уже удалено, обнови список.", show_alert=True)
        return
    await callback.answer()
    data = await drive.download_file(file.id)
    await callback.message.answer_photo(
        BufferedInputFile(data, filename=file.name),
        caption=f"{file.name}\nУдалить это фото?",
        reply_markup=confirm_delete_keyboard(file),
    )


async def delete_photo(
    callback: CallbackQuery,
    callback_data: AdminDelete,
    dataset: DatasetService,
    drive: DriveService,
) -> None:
    await callback.answer("Удаляю…")
    deleted = await dataset.delete_photo(callback_data.file_id)
    if deleted is None:
        await callback.message.edit_caption(caption="Это фото уже удалено.")
        return

    caption = f"🗑 {deleted.name} удалено из «{deleted.folder.name}»."
    if deleted.renamed:
        caption += f"\nНомера обновлены: переименовано {deleted.renamed} фото."
    await callback.message.edit_caption(caption=caption)

    text, markup = await render_folder(drive, deleted.folder.id, page=0)
    await callback.message.answer(text, reply_markup=markup)


async def cancel_delete(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.delete()


async def rescan(callback: CallbackQuery, scanner: CloudScanner, drive: DriveService) -> None:
    await callback.answer("Проверяю Диск…")
    await callback.message.edit_text("🔄 Проверяю нумерацию на Диске…")
    snapshots = await scanner.scan_once()
    text, markup = await render_menu(drive)
    await callback.message.edit_text(
        f"✅ Проверено папок: {len(snapshots)}, нумерация исправлена.\n\n{text}",
        reply_markup=markup,
    )


def create_router() -> Router:
    router = Router(name="admin")
    router.message.filter(IsAdmin())
    router.callback_query.filter(IsAdmin())
    router.message.register(admin_cmd, Command("admin"))
    router.callback_query.register(show_menu, AdminMenu.filter())
    router.callback_query.register(show_folder, AdminFolder.filter())
    router.callback_query.register(show_photo, AdminPhoto.filter())
    router.callback_query.register(delete_photo, AdminDelete.filter())
    router.callback_query.register(cancel_delete, AdminCancel.filter())
    router.callback_query.register(rescan, AdminRescan.filter())
    return router
