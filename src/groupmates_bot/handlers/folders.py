from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from groupmates_bot.keyboards.folders import NewFolder, PickFolder, folders_keyboard
from groupmates_bot.services.drive import DriveService
from groupmates_bot.states import FolderStates

router = Router(name="folders")

MAX_FOLDER_NAME = 100


async def send_folders(message: Message, drive: DriveService) -> None:
    folders = await drive.list_folders()
    text = "Выбери папку для загрузки фото:" if folders else "Папок пока нет. Создай новую:"
    await message.answer(text, reply_markup=folders_keyboard(folders))


@router.callback_query(NewFolder.filter())
async def ask_folder_name(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FolderStates.waiting_for_name)
    await callback.message.edit_text("Напиши название новой папки:")


@router.callback_query(PickFolder.filter())
async def pick_folder(
    callback: CallbackQuery, callback_data: PickFolder, state: FSMContext, drive: DriveService
) -> None:
    await callback.answer()
    folder = await drive.get_folder(callback_data.folder_id)
    await state.set_state(None)
    await state.update_data(folder_id=folder.id, folder_name=folder.name)
    await callback.message.edit_text(
        f"✅ Папка «{folder.name}» выбрана.\nПрисылай фото. Сменить папку — /folders"
    )


@router.message(FolderStates.waiting_for_name, F.text)
async def create_folder(message: Message, state: FSMContext, drive: DriveService) -> None:
    name = message.text.strip()[:MAX_FOLDER_NAME]
    if not name:
        await message.answer("Название не может быть пустым, напиши ещё раз:")
        return
    folder = await drive.create_folder(name)
    await state.set_state(None)
    await state.update_data(folder_id=folder.id, folder_name=folder.name)
    await message.answer(f"✅ Папка «{folder.name}» создана и выбрана.\nПрисылай фото.")
