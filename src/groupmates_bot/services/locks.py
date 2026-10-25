import asyncio
from collections import defaultdict


class KeyedLocks:
    """Набор asyncio.Lock по ключу (например, по id папки).

    Загрузка фото и пересканирование папки меняют нумерацию одних и тех же
    файлов, поэтому работают под общим локом папки. Локи живут в памяти
    процесса: бот должен быть запущен в одном экземпляре.
    """

    def __init__(self) -> None:
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __call__(self, key: str) -> asyncio.Lock:
        return self._locks[key]
