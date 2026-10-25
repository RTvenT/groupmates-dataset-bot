from datetime import UTC, datetime, timedelta

import pytest

from groupmates_bot.services.drive import DriveFile
from groupmates_bot.services.naming import (
    build_name,
    folder_prefix,
    next_index,
    parse_index,
    plan_renumbering,
)


@pytest.mark.parametrize(
    ("folder", "prefix"),
    [
        ("Андрей Ким", "Andrei_Kim"),
        ("Юлия Щербакова", "Iuliia_Shcherbakova"),
        ("Артём Хачатрян", "Artem_Khachatrian"),
        ("  Мария   Царёва-Шульц ", "Mariia_Tsareva_Shults"),
        ("John Smith", "John_Smith"),
        ("Илья 2", "Ilia_2"),
        ("???", "photo"),
    ],
)
def test_folder_prefix(folder, prefix):
    assert folder_prefix(folder) == prefix


def test_build_and_parse_roundtrip():
    assert build_name("Andrei_Kim", 7) == "Andrei_Kim_7.jpg"
    assert parse_index("Andrei_Kim_7.jpg") == 7
    assert parse_index("Old_Name_12.JPG") == 12
    assert parse_index("IMG_0001.png") is None
    assert parse_index("photo.jpg") is None


def files(*names: str) -> list[DriveFile]:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        DriveFile(f"id{i}", name, "image/jpeg", t0 + timedelta(seconds=i))
        for i, name in enumerate(names)
    ]


def test_next_index_uses_max_not_count():
    # после удаления №2 файлов три, но номер 3 занят — следующий должен быть 5
    assert next_index(files("A_1.jpg", "A_3.jpg", "A_4.jpg")) == 5
    assert next_index([]) == 1
    assert next_index(files("random.jpg")) == 1


def as_dict(renames):
    return {r.file.name: r.new_name for r in renames}


def test_renumbering_closes_gaps_and_keeps_order():
    plan = plan_renumbering(files("A_4.jpg", "A_1.jpg", "A_7.jpg"), "A")
    assert as_dict(plan) == {"A_4.jpg": "A_2.jpg", "A_7.jpg": "A_3.jpg"}


def test_renumbering_noop_when_consistent():
    assert plan_renumbering(files("A_1.jpg", "A_2.jpg", "A_3.jpg"), "A") == []


def test_renumbering_fixes_prefix_and_appends_foreign_files():
    plan = plan_renumbering(files("IMG_9999.png", "Old_2.jpg", "Old_1.jpg"), "New")
    assert as_dict(plan) == {
        "Old_1.jpg": "New_1.jpg",
        "Old_2.jpg": "New_2.jpg",
        "IMG_9999.png": "New_3.jpg",
    }
