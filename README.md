# groupmates-dataset-bot

Telegram-бот, который собирает датасет фото на Google Drive: каждое фото
приводится к квадрату 640x640 (вход YOLO) и сохраняется в выбранную папку
под именем `<Имя_Фамилия>_<n>.jpg`, например `Andrei_Kim_3.jpg` в папке «Андрей Ким».

## Как это работает

- **Подготовка фото.** Картинка растягивается ровно до `IMAGE_SIZE` x `IMAGE_SIZE`
  без полей и обрезки (пропорции не сохраняются). Поворот из EXIF применяется,
  результат всегда JPEG.
- **Имена.** Имя папки транслитерируется (ICAO, как в загранпаспорте), номер —
  следующий после максимального в папке. Загрузки в одну папку идут по очереди,
  поэтому номера не повторяются.
- **Сканирование Диска.** Раз в `SCAN_INTERVAL` секунд бот обходит все папки и
  закрывает пропуски в нумерации после удаления фото (1, 2, 4 → 1, 2, 3), а также
  чинит префикс, если папку переименовали. Посторонние картинки в папке тоже
  получают номер — в конце списка.
- Бот должен работать в **одном экземпляре**: очередь загрузок держится в памяти.

## Запуск

```bash
uv sync
cp .env.example .env   # заполнить BOT_TOKEN и ALLOWED_USERS
# положить OAuth-клиент Google (Desktop app) в credentials.json
uv run groupmates-bot
```

При первом запуске откроется браузер для входа в Google, после чего токен сохранится
в `token.json`. На сервере без браузера получите `token.json` локально и скопируйте его.

Если при запуске падает `TelegramNetworkError: Request timeout error`, значит
`api.telegram.org` недоступен напрямую: укажите прокси в `TELEGRAM_PROXY`
(например, локальный порт VPN-клиента: `socks5://127.0.0.1:1080`).

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
├── scanner/             # периодическое сканирование Диска
│   ├── base.py          # ScanTask — интерфейс задачи сканирования
│   ├── scanner.py       # CloudScanner — цикл обхода папок
│   └── tasks/renumber.py# восстановление нумерации
└── services/
    ├── google_auth.py   # OAuth для Google
    ├── drive.py         # асинхронная обёртка над Drive API
    ├── dataset.py       # добавление фото: подготовка + именование
    ├── images.py        # приведение к квадрату под YOLO
    ├── naming.py        # транслит, имена файлов, план перенумерации
    └── locks.py         # локи по папкам
```

### Новая задача сканирования

Унаследуйтесь от `ScanTask`, реализуйте `process_folder(snapshot)` (и при
необходимости `on_scan_complete(snapshots)`) и добавьте экземпляр в
`build_scanner` в `app.py`. Задачи выполняются по порядку под локом папки;
если задача меняет файлы, она возвращает обновлённый снимок для следующих.

## Разработка

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
```
