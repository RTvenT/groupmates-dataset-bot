# groupmates-dataset-bot

Telegram-бот, который складывает присланные фото в выбранную папку Google Drive.

## Запуск

```bash
uv sync
cp .env.example .env   # заполнить BOT_TOKEN и ALLOWED_USERS
# положить OAuth-клиент Google (Desktop app) в credentials.json
uv run groupmates-bot
```

При первом запуске откроется браузер для входа в Google, после чего токен сохранится
в `token.json`. На сервере без браузера получите `token.json` локально и скопируйте его.

## Структура

```
src/groupmates_bot/
├── __init__.py          # main() — точка входа (uv run groupmates-bot)
├── __main__.py          # python -m groupmates_bot
├── app.py               # сборка Bot/Dispatcher и запуск polling
├── config.py            # настройки из .env (pydantic-settings)
├── states.py            # FSM-состояния
├── handlers/            # роутеры aiogram
│   ├── common.py        # /start, /folders, fallback
│   ├── folders.py       # выбор и создание папки
│   └── photos.py        # загрузка фото
├── keyboards/folders.py # inline-клавиатура и CallbackData
├── middlewares/access.py# белый список пользователей
└── services/
    ├── google_auth.py   # OAuth для Google
    └── drive.py         # асинхронная обёртка над Drive API
```

## Разработка

```bash
uv run ruff check . && uv run ruff format .
```
