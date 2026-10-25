import io

import pytest
from PIL import Image

from groupmates_bot.services.images import PAD_COLOR, letterbox
from tests.conftest import make_image


def open_result(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    return image.convert("RGB")


def near(pixel, color, tol=8):
    return all(abs(a - b) <= tol for a, b in zip(pixel, color, strict=True))


def test_landscape_is_padded_top_and_bottom():
    image = open_result(letterbox(make_image(1280, 720), 640))
    assert image.size == (640, 640)
    assert near(image.getpixel((320, 5)), PAD_COLOR)  # поле сверху
    assert near(image.getpixel((320, 320)), (255, 0, 0))  # сама картинка
    assert near(image.getpixel((5, 320)), (255, 0, 0))  # по ширине без полей


def test_portrait_is_padded_left_and_right():
    image = open_result(letterbox(make_image(720, 1280), 640))
    assert image.size == (640, 640)
    assert near(image.getpixel((5, 320)), PAD_COLOR)
    assert near(image.getpixel((320, 5)), (255, 0, 0))


def test_small_image_is_upscaled_and_png_accepted():
    image = open_result(letterbox(make_image(100, 100, fmt="PNG"), 640))
    assert image.size == (640, 640)
    assert near(image.getpixel((5, 5)), (255, 0, 0))


def test_exif_orientation_is_applied():
    exif = Image.Exif()
    exif[0x0112] = 6  # повернуть на 90°: широкое фото на самом деле вертикальное
    image = open_result(letterbox(make_image(1280, 720, exif=exif), 640))
    assert near(image.getpixel((5, 320)), PAD_COLOR)
    assert near(image.getpixel((320, 5)), (255, 0, 0))


@pytest.mark.parametrize("size", [320, 640, 1024])
def test_custom_size(size):
    assert open_result(letterbox(make_image(300, 200), size)).size == (size, size)
