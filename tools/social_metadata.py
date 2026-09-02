"""Normaliza metadados SEO e de compartilhamento do blog retro."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTICLES = DOCS / "articles"
IMAGES = ARTICLES / "assets" / "img"
SITE = "https://retro.caracore.com.br"
AUTHOR = "Christian Mulato"
SITE_NAME = "Artigos Retrô — Cara Core Informática"
DEFAULT_IMAGE = "social-default.png"
DEFAULT_DESCRIPTION = (
    "Artigos retrô da Cara Core Informática sobre engenharia de software, automação, "
    "soberania digital, produtos locais, arquitetura resiliente e decisões técnicas "
    "aplicadas a negócios reais."
)
TAG = re.compile(r"<meta\b[^>]*>|<link\b[^>]*>", re.I | re.S)
ATTR = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.I | re.S)
TITLE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
DATE = re.compile(r"^(\d{4}_\d{2}_\d{2})_")
TARGETS = {
    "description": "name", "author": "name", "og:title": "property",
    "og:description": "property", "og:type": "property", "og:url": "property",
    "og:image": "property", "og:image:width": "property", "og:image:height": "property",
    "og:site_name": "property", "twitter:card": "name", "twitter:title": "name",
    "twitter:description": "name", "twitter:image": "name",
}


def attrs(tag: str) -> dict[str, str]:
    return {key.lower(): value for key, _, value in ATTR.findall(tag)}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def value(source: str, key: str) -> str:
    attribute = TARGETS[key]
    for tag in TAG.findall(source):
        data = attrs(tag)
        if data.get(attribute) == key and data.get("content"):
            return html.unescape(data["content"])
    return ""


def title(source: str, home: bool) -> str:
    if home:
        return "Artigos Retrô — Cara Core Informática"
    match = H1.search(source) or TITLE.search(source)
    result = clean(match.group(1)) if match else SITE_NAME
    return re.sub(r"\s+[|—-]\s+(Cara Core|Cara Core Informática)$", "", result).strip()


def description(source: str, heading: str, home: bool) -> str:
    if home:
        return DEFAULT_DESCRIPTION
    current = clean(value(source, "description"))
    if len(current) >= 150:
        return current[:250].rstrip(" ,.;:")
    expanded = (
        f"{current.rstrip('.')} Este artigo de {AUTHOR} contextualiza {heading}, "
        "relacionando tecnologia, engenharia e decisões práticas para operações e negócios reais."
    )
    return (expanded + " A leitura combina experiência, fundamentos e visão de longo prazo.")[:250].rstrip(" ,.;:")


def image(path: Path, home: bool) -> tuple[str, int, int]:
    chosen = IMAGES / DEFAULT_IMAGE if home else IMAGES / f"{path.stem}_01.png"
    if not chosen.exists():
        chosen = IMAGES / DEFAULT_IMAGE
    width, height = 1200, 630
    try:
        from PIL import Image

        with Image.open(chosen) as opened:
            width, height = opened.size
    except (ImportError, OSError):
        pass
    return f"{SITE}/articles/assets/img/{chosen.name}", width, height


def strip_metadata(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        data = attrs(match.group(0))
        if data.get("rel", "").lower() == "canonical":
            return ""
        return "" if any(data.get(attribute) == key for key, attribute in TARGETS.items()) else match.group(0)

    return TAG.sub(replace, source)


def block(heading: str, desc: str, url: str, image_url: str, width: int, height: int, home: bool, date: str | None) -> str:
    page_type = "website" if home else "article"
    lines = [
        f'    <meta name="description" content="{html.escape(desc, quote=True)}">',
        f'    <meta name="author" content="{AUTHOR}">',
        f'    <meta property="og:title" content="{html.escape(heading, quote=True)}">',
        f'    <meta property="og:description" content="{html.escape(desc, quote=True)}">',
        f'    <meta property="og:type" content="{page_type}">',
        f'    <meta property="og:url" content="{url}">',
        f'    <meta property="og:image" content="{image_url}">',
        f'    <meta property="og:image:width" content="{width}">',
        f'    <meta property="og:image:height" content="{height}">',
        f'    <meta property="og:site_name" content="{SITE_NAME}">',
        '    <meta name="twitter:card" content="summary_large_image">',
        f'    <meta name="twitter:title" content="{html.escape(heading, quote=True)}">',
        f'    <meta name="twitter:description" content="{html.escape(desc, quote=True)}">',
        f'    <meta name="twitter:image" content="{image_url}">',
        f'    <link rel="canonical" href="{url}">',
    ]
    schema = {
        "@context": "https://schema.org", "@type": "Blog" if home else "BlogPosting",
        "name": SITE_NAME, "headline": heading, "description": desc, "image": image_url,
        "author": {"@type": "Person", "name": AUTHOR},
    }
    if date:
        lines.append(f'    <meta property="article:published_time" content="{date}">')
        schema["datePublished"] = date
        schema["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
    lines.extend(['    <script type="application/ld+json">', "    " + json.dumps(schema, ensure_ascii=False, indent=4), "    </script>"])
    return "\n".join(lines)


def normalize(path: Path, home: bool) -> None:
    source = path.read_bytes().decode("utf-8", errors="replace")
    heading = title(source, home)
    desc = description(source, heading, home)
    url = f"{SITE}/" if home else f"{SITE}/articles/{path.name}"
    date_match = DATE.match(path.stem)
    date = date_match.group(1).replace("_", "-") if date_match else None
    image_url, width, height = image(path, home)
    cleaned = strip_metadata(source)
    head = re.search(r"<head\b[^>]*>", cleaned, re.I)
    if not head:
        raise ValueError(f"<head> ausente: {path}")
    viewport = re.search(r'''<meta\b[^>]*\bname=["']viewport["'][^>]*>''', cleaned[head.end():], re.I)
    position = head.end() + viewport.end() if viewport else head.end()
    updated = cleaned[:position] + "\n" + block(heading, desc, url, image_url, width, height, home, date) + cleaned[position:]
    path.write_text(updated, encoding="utf-8", newline="")


def main() -> None:
    files = [DOCS / "index.html"] + sorted(ARTICLES.glob("*.html"))
    for path in files:
        if path.name != "README.html":
            normalize(path, path == DOCS / "index.html")
    print(f"Normalizadas {len(files) - 1} paginas de artigo e a home.")


if __name__ == "__main__":
    main()