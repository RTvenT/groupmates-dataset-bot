import asyncio
import io
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("drive-bot")

BOT_TOKEN = os.environ["BOT_TOKEN"]
# Папка, внутри которой бот показывает/создает папки. "root" = корень "Мой диск"
ROOT_FOLDER_ID = os.getenv("ROOT_FOLDER_ID", "root")
# Список разрешённых Telegram user id через запятую (пусто = доступ всем!)
ALLOWED_USERS = {int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip()}

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_FOLDERS = 30


# ---------------- Google Drive ----------------
def get_credentials() -> Credentials:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return creds


CREDS = None


def drive():
    # сервис создаём на каждый вызов — клиент не потокобезопасен
    return build("drive", "v3", credentials=CREDS, cache_discovery=False)


def list_folders() -> list[dict]:
    q = (
        f"mimeType='{FOLDER_MIME}' and '{ROOT_FOLDER_ID}' in parents and trashed=false"
    )
    res = (
        drive()
        .files()
        .list(q=q, fields="files(id,name)", orderBy="name", pageSize=MAX_FOLDERS)
        .execute()
    )
    return res.get("files", [])


def create_folder(name: str) -> dict:
    meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [ROOT_FOLDER_ID]}
    return drive().files().create(body=meta, fields="id,name").execute()


def get_folder_name(folder_id: str) -> str:
    return drive().files().get(fileId=folder_id, fields="name").execute()["name"]


def upload_file(data: bytes, filename: str, mime: str, folder_id: str) -> str:
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=False)
    meta = {"name": filename, "parents": [folder_id]}
    return drive().files().create(body=meta, media_body=media, fields="id").execute()["id"]


# ---------------- Telegram ----------------
def allowed(update: Update) -> bool:
    return not ALLOWED_USERS or (update.effective_user and update.effective_user.id in ALLOWED_USERS)


async def show_folders(target, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    folders = await asyncio.to_thread(list_folders)
    rows = [[InlineKeyboardButton(f"📁 {f['name']}", callback_data=f"pick:{f['id']}")] for f in folders]
    rows.append([InlineKeyboardButton("➕ Создать новую папку", callback_data="new")])
    text = "Выбери папку для загрузки фото:" if folders else "Папок пока нет. Создай новую:"
    markup = InlineKeyboardMarkup(rows)
    if edit:
        await target.edit_message_text(text, reply_markup=markup)
    else:
        await target.reply_text(text, reply_markup=markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    context.user_data.clear()
    await show_folders(update.message, context)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not allowed(update):
        return
    await q.answer()

    if q.data == "new":
        context.user_data["awaiting_name"] = True
        await q.edit_message_text("Напиши название новой папки:")
    elif q.data.startswith("pick:"):
        folder_id = q.data.split(":", 1)[1]
        name = await asyncio.to_thread(get_folder_name, folder_id)
        context.user_data["folder_id"] = folder_id
        context.user_data["folder_name"] = name
        await q.edit_message_text(
            f"✅ Папка «{name}» выбрана.\nПрисылай фото. Сменить папку — /folders"
        )


async def folders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await show_folders(update.message, context)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    if not context.user_data.get("awaiting_name"):
        await update.message.reply_text("Нажми /start, чтобы выбрать папку.")
        return
    name = update.message.text.strip()[:100]
    folder = await asyncio.to_thread(create_folder, name)
    context.user_data["awaiting_name"] = False
    context.user_data["folder_id"] = folder["id"]
    context.user_data["folder_name"] = folder["name"]
    await update.message.reply_text(
        f"✅ Папка «{folder['name']}» создана и выбрана.\nПрисылай фото."
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    folder_id = context.user_data.get("folder_id")
    if not folder_id:
        await update.message.reply_text("Сначала выбери папку — /start")
        return

    msg = update.message
    if msg.photo:
        tg_file = await msg.photo[-1].get_file()  # максимальное разрешение
        ext, mime = "jpg", "image/jpeg"
        uid = msg.photo[-1].file_unique_id
    else:  # фото, отправленное как файл (без сжатия)
        doc = msg.document
        tg_file = await doc.get_file()
        mime = doc.mime_type or "application/octet-stream"
        ext = (doc.file_name or "img.jpg").rsplit(".", 1)[-1]
        uid = doc.file_unique_id

    data = bytes(await tg_file.download_as_bytearray())
    filename = f"{datetime.now():%Y%m%d_%H%M%S}_{uid}.{ext}"
    try:
        await asyncio.to_thread(upload_file, data, filename, mime, folder_id)
        await msg.reply_text(f"☁️ Загружено в «{context.user_data['folder_name']}»")
    except Exception:
        log.exception("upload failed")
        await msg.reply_text("❌ Не удалось загрузить файл, попробуй ещё раз.")


def main():
    global CREDS
    CREDS = get_credentials()  # при первом запуске откроет браузер для входа в Google

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("folders", folders_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()
