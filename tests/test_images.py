import io

import pytest
from PIL import Image

from groupmates_bot.services.images import resize_square
from tests.conftest import make_image

RED, BLUE = (255, 0, 0), (0, 0, 255)


def open_result(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    return image.convert("RGB")


def near(pixel, color, tol=8):
    return all(abs(a - b) <= tol for a, b in zip(pixel, color, strict=True))


def half_red_half_blue(width: int, height: int, exif=None) -> bytes:
    """Левая половина красная, правая синяя."""
    image = Image.new("RGB", (width, height), RED)
    image.paste(BLUE, (width // 2, 0, width, height))
    out = io.BytesIO()
    image.save(out, format="JPEG", **({"exif": exif} if exif is not None else {}))
    return out.getvalue()


@pytest.mark.parametrize(("width", "height"), [(1280, 720), (720, 1280), (100, 100)])
def test_stretched_to_square_without_padding(width, height):
    image = open_result(resize_square(make_image(width, height), 640))
    assert image.size == (640, 640)
    # картинка занимает весь квадрат: и углы, и центр — её цвет, а не поля
    for xy in [(2, 2), (637, 2), (2, 637), (637, 637), (320, 320)]:
        assert near(image.getpixel(xy), RED), xy


def test_proportions_are_stretched_not_cropped():
    image = open_result(resize_square(half_red_half_blue(1280, 720), 640))
    # граница цветов осталась посередине: ничего не обрезано по краям
    assert near(image.getpixel((300, 320)), RED)
    assert near(image.getpixel((340, 320)), BLUE)


def test_exif_orientation_is_applied():
    exif = Image.Exif()
    exif[0x0112] = 6  # повернуть на 90° по часовой: левая (красная) половина уходит вверх
    image = open_result(resize_square(half_red_half_blue(1280, 720, exif=exif), 640))
    assert near(image.getpixel((320, 100)), RED)
    assert near(image.getpixel((320, 540)), BLUE)


def test_png_is_accepted():
    assert open_result(resize_square(make_image(300, 200, fmt="PNG"), 640)).size == (640, 640)


@pytest.mark.parametrize("size", [320, 640, 1024])
def test_custom_size(size):
    assert open_result(resize_square(make_image(300, 200), size)).size == (size, size)
