"""Имена файлов датасета: <Префикс>_<n>.jpg, где префикс — транслит имени папки."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from groupmates_bot.services.drive import DriveFile

EXTENSION = "jpg"

# Транслитерация по ICAO 9303 (как в загранпаспортах РФ): Андрей Ким -> Andrei Kim
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "ie", "ы": "y", "ь": "", "э": "e",
    "ю": "iu", "я": "ia",
}  # fmt: skip

_INDEXED_NAME = re.compile(rf"^(?P<prefix>.+)_(?P<index>\d+)\.{EXTENSION}$", re.IGNORECASE)


def transliterate(text: str) -> str:
    out = []
    for ch in text:
        latin = _TRANSLIT.get(ch.lower())
        if latin is None:
            out.append(ch)
        elif ch.isupper():
            out.append(latin.capitalize())
        else:
            out.append(latin)
    return "".join(out)


def folder_prefix(folder_name: str) -> str:
    """'Андрей Ким' -> 'Andrei_Kim'."""
    latin = transliterate(folder_name)
    prefix = re.sub(r"[^A-Za-z0-9]+", "_", latin).strip("_")
    return prefix or "photo"


def build_name(prefix: str, index: int) -> str:
    return f"{prefix}_{index}.{EXTENSION}"


def parse_index(filename: str) -> int | None:
    """Номер из имени вида <что угодно>_<n>.jpg, иначе None."""
    match = _INDEXED_NAME.match(filename)
    return int(match["index"]) if match else None


def next_index(files: Sequence[DriveFile]) -> int:
    """Следующий свободный номер. Берём max+1, а не count+1: пока пропуски после
    удаления не закрыты пересканированием, count+1 совпал бы с существующим номером."""
    indices = [i for f in files if (i := parse_index(f.name)) is not None]
    return max(indices, default=0) + 1


@dataclass(frozen=True, slots=True)
class Rename:
    file: DriveFile
    new_name: str


def sort_by_index(files: Sequence[DriveFile]) -> list[DriveFile]:
    """Сначала файлы с номером (по возрастанию), затем остальные (по дате создания)."""

    def order(f: DriveFile) -> tuple[int, int, datetime, str]:
        index = parse_index(f.name)
        if index is None:
            return (1, 0, f.created_time, f.id)
        return (0, index, f.created_time, f.id)

    return sorted(files, key=order)


def plan_renumbering(files: Sequence[DriveFile], prefix: str) -> list[Rename]:
    """Какие файлы переименовать, чтобы получилась сплошная нумерация 1..N.

    Порядок сохраняется (см. sort_by_index). Заодно исправляется префикс,
    если папку переименовали.
    """
    renames = []
    for position, file in enumerate(sort_by_index(files), start=1):
        expected = build_name(prefix, position)
        if file.name != expected:
            renames.append(Rename(file=file, new_name=expected))
    return renames
