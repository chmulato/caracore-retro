from __future__ import annotations

import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIR = ROOT / "docs" / "articles"
IMAGE_DIR = ARTICLE_DIR / "assets" / "img"
MAX_WIDTHS = (720, 1600)

IMAGE_PATTERN = re.compile(
    r'<img\b(?=[^>]*\bsrc=["\']assets/img/(\d{4}_\d{2}_\d{2}_article_\d+_\d+\.png)["\'])[^>]*>',
    re.IGNORECASE,
)
ARTICLE_IMAGE_PATTERN = re.compile(
    r'<img\b[^>]*\bsrc=["\']assets/img/(\d{4}_\d{2}_\d{2}_article_\d+_\d+\.png)["\']',
    re.IGNORECASE,
)
STYLE_PATTERN = re.compile(r'\s+style=["\']([^"\']*)["\']', re.IGNORECASE)
CLASS_PATTERN = re.compile(r'\s+class=["\']([^"\']*)["\']', re.IGNORECASE)


def create_webp_variants(source: Path) -> tuple[str, str]:
    with Image.open(source) as original:
        original.load()
        width, height = original.size
        original = original.convert("RGBA" if "A" in original.getbands() else "RGB")
        paths = tuple(source.with_name(f"{source.stem}_{size}.webp") for size in MAX_WIDTHS)

        for max_width, destination in zip(MAX_WIDTHS, paths):
            if destination.exists() and destination.stat().st_mtime_ns >= source.stat().st_mtime_ns:
                continue
            resized = original.copy()
            resized.thumbnail((max_width, max_width * height // width), Image.Resampling.LANCZOS)
            resized.save(destination, format="WEBP", quality=82, method=6)

    return paths[0].name, paths[1].name


def make_picture(
    image_tag: str,
    mobile_name: str,
    desktop_name: str,
    indent: str,
    existing_hero_picture: bool = False,
) -> str:
    float_cover = existing_hero_picture or bool(
        re.search(r"\bfloat\s*:\s*right\b", image_tag, re.IGNORECASE)
    ) or bool(
        re.search(r'\bclass=["\'][^"\']*\barticle-hero\b', image_tag, re.IGNORECASE)
    )
    if float_cover:
        image_tag = STYLE_PATTERN.sub("", image_tag)
        class_match = CLASS_PATTERN.search(image_tag)
        if class_match:
            remaining_classes = [
                name for name in class_match.group(1).split() if name != "article-hero"
            ]
            if remaining_classes:
                image_tag = CLASS_PATTERN.sub(
                    f' class="{" ".join(remaining_classes)}"',
                    image_tag,
                    count=1,
                )
            else:
                image_tag = CLASS_PATTERN.sub("", image_tag, count=1)
    else:
        image_tag = re.sub(
            r"(max-width\s*:\s*)(\d+(?:\.\d+)?)px",
            r"\1min(\2px, 100%)",
            image_tag,
            flags=re.IGNORECASE,
        )

    picture_class = ' class="article-hero"' if float_cover else ""
    inner_indent = indent + "    "
    return (
        f"<picture{picture_class}>\n"
        f'{inner_indent}<source type="image/webp" media="(max-width: 680px)" '
        f'srcset="assets/img/{mobile_name}">\n'
        f'{inner_indent}<source type="image/webp" srcset="assets/img/{desktop_name}">\n'
        f"{inner_indent}{image_tag}\n"
        f"{indent}</picture>"
    )


def update_article(article: Path) -> bool:
    content = article.read_text(encoding="utf-8")
    matches = list(IMAGE_PATTERN.finditer(content))
    updated = content
    for match in reversed(matches):
        source = IMAGE_DIR / match.group(1)
        if not source.is_file():
            raise FileNotFoundError(f"Article image not found: {source}")

        mobile_name, desktop_name = create_webp_variants(source)
        picture_start = updated.rfind("<picture", 0, match.start())
        picture_close = updated.rfind("</picture>", 0, match.start())
        already_in_picture = picture_start > picture_close
        if already_in_picture:
            picture_end = updated.find("</picture>", match.end())
            if picture_end == -1:
                raise ValueError(f"{article.relative_to(ROOT)}: unclosed <picture> around {source.name}")
            picture_end += len("</picture>")
            start = picture_start
            picture_markup = updated[picture_start:picture_end]
            existing_sources = re.findall(
                r'<source\b[^>]*\bsrcset=["\']([^"\']+)["\'][^>]*>',
                picture_markup,
                re.IGNORECASE,
            )
            if [Path(name).name for name in existing_sources] == [mobile_name, desktop_name]:
                continue
            existing_hero_picture = bool(
                re.search(r'<picture\b[^>]*\bclass=["\'][^"\']*\barticle-hero\b', picture_markup, re.IGNORECASE)
            )
        else:
            start = match.start()
            picture_end = match.end()
            existing_hero_picture = False
        indent = updated[updated.rfind("\n", 0, start) + 1:start]

        replacement = make_picture(
            match.group(0),
            mobile_name,
            desktop_name,
            indent,
            existing_hero_picture,
        )
        updated = updated[:start] + replacement + updated[picture_end:]

    if updated != content:
        article.write_text(updated, encoding="utf-8", newline="")
        return True
    return False


def main() -> None:
    articles = sorted(ARTICLE_DIR.glob("20*_article_*.html"))
    image_names = set()
    for article in articles:
        content = article.read_text(encoding="utf-8")
        image_names.update(ARTICLE_IMAGE_PATTERN.findall(content))

    image_assets = [IMAGE_DIR / name for name in sorted(image_names)]
    for source in image_assets:
        if not source.is_file():
            raise FileNotFoundError(f"Article image not found: {source}")
        create_webp_variants(source)

    updated = sum(update_article(article) for article in articles)
    print(
        f"Generated responsive variants for {len(image_assets)} referenced images; "
        f"updated {updated} article pages ({len(articles)} scanned)."
    )


if __name__ == "__main__":
    main()
