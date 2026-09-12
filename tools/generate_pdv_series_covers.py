from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1600
HEIGHT = 900
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "articles" / "assets" / "img"
FONT_DIR = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [FONT_DIR / name, Path("C:/Windows/Fonts/arial.ttf")]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


TITLE = font("segoeuib.ttf", 70)
SUBTITLE = font("segoeui.ttf", 26)
LABEL = font("segoeuib.ttf", 22)
SMALL = font("segoeui.ttf", 19)


def blend(color_a: tuple[int, int, int], color_b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return tuple(int(a + (b - a) * ratio) for a, b in zip(color_a, color_b))


def base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for y in range(HEIGHT):
        vertical = y / HEIGHT
        for x in range(WIDTH):
            horizontal = x / WIDTH
            left = blend((5, 12, 24), (8, 31, 56), vertical)
            right = blend((5, 12, 24), (18, 47, 70), vertical)
            pixels[x, y] = blend(left, right, horizontal)

    draw = ImageDraw.Draw(image, "RGBA")
    for x in range(-200, WIDTH + 200, 72):
        draw.line((x, 410, x + 430, HEIGHT), fill=(58, 129, 185, 75), width=2)
    for y in range(430, HEIGHT + 100, 54):
        draw.line((0, y, WIDTH, y), fill=(58, 129, 185, 55), width=2)
    draw.rectangle((0, 0, WIDTH, 150), fill=(3, 7, 15, 100))
    return image, draw


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, selected_font: ImageFont.FreeTypeFont, fill=(244, 248, 252, 255)) -> None:
    draw.text(xy, value, font=selected_font, fill=fill)


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill=(8, 24, 40, 235), outline=(81, 210, 232, 180)) -> None:
    draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=3)


def fiscal_scene(draw: ImageDraw.ImageDraw) -> None:
    rounded_panel(draw, (170, 420, 720, 770), fill=(7, 22, 38, 245), outline=(255, 143, 72, 210))
    text(draw, (215, 455), "AUDITORIA", LABEL, (255, 184, 107, 255))
    columns = [(230, "DATA", (84, 215, 232)), (380, "REGRA", (255, 184, 107)), (530, "STATUS", (126, 232, 181))]
    for x, label, color in columns:
        text(draw, (x, 525), label, SMALL, color)
    for row in range(4):
        y = 575 + row * 42
        draw.rounded_rectangle((220, y, 670, y + 20), radius=8, fill=(22, 52, 72, 230))
        draw.rectangle((235, y + 5, 300 + row * 12, y + 15), fill=(84, 215, 232, 200))
        draw.rectangle((390, y + 5, 470 + row * 15, y + 15), fill=(255, 143, 72, 180))
        draw.ellipse((610, y + 2, 626, y + 18), fill=(126, 232, 181, 240))


def pdv_scene(draw: ImageDraw.ImageDraw) -> None:
    rounded_panel(draw, (170, 405, 740, 775), fill=(7, 22, 38, 245), outline=(84, 215, 232, 220))
    draw.rectangle((215, 465, 695, 680), fill=(13, 47, 67, 255), outline=(117, 231, 240, 230), width=3)
    draw.rectangle((240, 500, 470, 535), fill=(27, 87, 109, 255))
    text(draw, (258, 506), "CARA CORE PDV", SMALL, (241, 250, 251, 255))
    for row in range(3):
        y = 570 + row * 34
        draw.rectangle((245, y, 450, y + 17), fill=(45, 105, 125, 230))
        draw.rectangle((485, y, 650, y + 17), fill=(255, 143, 72, 190))
    draw.rectangle((215, 700, 695, 735), fill=(255, 143, 72, 220))
    text(draw, (395, 704), "VENDA REGISTRADA", SMALL, (14, 26, 39, 255))


def architecture_scene(draw: ImageDraw.ImageDraw) -> None:
    rounded_panel(draw, (130, 450, 790, 750), fill=(7, 22, 38, 245), outline=(84, 215, 232, 220))
    boxes = [(185, 535, 350, 655, "RUST", (255, 143, 72)), (435, 535, 600, 655, "JAVA", (84, 215, 232))]
    for x1, y1, x2, y2, label, color in boxes:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=15, fill=(18, 50, 68, 255), outline=(*color, 255), width=4)
        text(draw, (x1 + 42, y1 + 32), label, LABEL, (*color, 255))
        draw.rectangle((x1 + 35, y1 + 78, x2 - 35, y1 + 88), fill=(*color, 155))
    draw.line((350, 595, 435, 595), fill=(126, 232, 181, 255), width=8)
    draw.polygon(((425, 580), (455, 595), (425, 610)), fill=(126, 232, 181, 255))
    draw.rounded_rectangle((235, 675, 560, 715), radius=12, fill=(126, 232, 181, 180))
    text(draw, (280, 682), "OPERAÇÃO LOCAL", SMALL, (6, 25, 32, 255))


def add_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, episode: str) -> None:
    text(draw, (100, 55), episode, LABEL, (126, 232, 181, 255))
    text(draw, (100, 95), title, TITLE)
    text(draw, (900, 106), subtitle, SUBTITLE, (174, 205, 219, 255))
    draw.line((100, 190, 1500, 190), fill=(84, 215, 232, 180), width=3)


def add_footer(draw: ImageDraw.ImageDraw, labels: Iterable[str]) -> None:
    x = 900
    for label in labels:
        draw.rounded_rectangle((x, 715, x + 210, 760), radius=12, fill=(12, 47, 65, 235), outline=(84, 215, 232, 150), width=2)
        text(draw, (x + 18, 726), label, SMALL, (214, 237, 242, 255))
        x += 235


def create(filename: str, title: str, subtitle: str, episode: str, scene: str, labels: Iterable[str]) -> None:
    image, draw = base()
    add_header(draw, title, subtitle, episode)
    if scene == "fiscal":
        fiscal_scene(draw)
    elif scene == "pdv":
        pdv_scene(draw)
    else:
        architecture_scene(draw)
    add_footer(draw, labels)
    draw.ellipse((1130, 350, 1450, 670), fill=(20, 103, 128, 35), outline=(84, 215, 232, 95), width=3)
    draw.ellipse((1200, 420, 1380, 600), fill=(255, 143, 72, 25), outline=(255, 184, 107, 85), width=3)
    image.save(OUTPUT / filename, format="PNG", optimize=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    create("2027_06_21_article_135_01.png", "Antes do Caixa", "Bagagem que virou engenharia", "EPISODIO 01  /  A BAGAGEM", "fiscal", ["SAP", "REGRAS", "AUDITORIA"])
    create("2027_06_28_article_136_01.png", "Quando virou produto", "A história do Cara Core PDV", "EPISODIO 02  /  O PRODUTO", "pdv", ["OPERADORES", "VENDAS", "COMPROVANTE"])
    create("2027_07_05_article_137_01.png", "O próximo balcão", "Java, Rust e continuidade", "EPISODIO 03  /  O FUTURO", "architecture", ["RUST", "JAVA", "OFFLINE-FIRST"])


if __name__ == "__main__":
    main()