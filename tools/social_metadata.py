"""Normaliza metadados SEO e de compartilhamento do blog retro."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTICLES = DOCS / "articles"
IMAGES = ARTICLES / "assets" / "img"
SITE = "https://retro.caracore.com.br"
WEBSITE_ID = SITE + "/#website"
BLOG_ID = SITE + "/#blog"
ORGANIZATION_ID = "https://caracore.com.br/#organization"
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
LANGUAGE = re.compile(r"<html\b[^>]*\blang\s*=\s*['\"]([^'\"]+)['\"]", re.I)
JSONLD_SCRIPT = re.compile(
    r'<script\b(?=[^>]*\btype=["\']application/ld\+json["\'])[^>]*>.*?</script\s*>',
    re.I | re.S,
)
TARGETS = {
    "description": "name", "author": "name", "og:title": "property",
    "og:description": "property", "og:type": "property", "og:url": "property",
    "og:image": "property", "og:image:width": "property", "og:image:height": "property",
    "og:site_name": "property", "twitter:card": "name", "twitter:title": "name",
    "twitter:description": "name", "twitter:image": "name",
    "article:published_time": "property",
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


def image(path: Path, home: bool, source: str) -> tuple[str, int, int]:
    existing = value(source, "og:image")
    parsed = urlparse(existing)
    chosen = DOCS / parsed.path.lstrip("/")
    if parsed.scheme != "https" or parsed.netloc != urlparse(SITE).netloc or not chosen.is_file():
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
    image_url = existing if chosen == DOCS / urlparse(existing).path.lstrip("/") else (
        f"{SITE}/articles/assets/img/{chosen.name}"
    )
    return image_url, width, height


def page_title(source: str) -> str:
    match = TITLE.search(source)
    return clean(match.group(1)) if match else SITE_NAME


def page_language(source: str) -> str:
    match = LANGUAGE.search(source)
    return match.group(1) if match else "pt-BR"


def webpage(url: str, name: str, desc: str, language: str, main_entity: dict | None = None) -> dict:
    node = {
        "@id": url + "#webpage",
        "@type": "WebPage",
        "url": url,
        "name": name,
        "description": desc,
        "inLanguage": language,
        "isPartOf": {"@id": WEBSITE_ID},
        "publisher": {"@id": ORGANIZATION_ID},
    }
    if main_entity:
        node["mainEntity"] = main_entity
    return node


def strip_empty_head_lines(source: str) -> str:
    head = re.search(r"<head\b[^>]*>(.*?)</head\s*>", source, re.I | re.S)
    if not head:
        return source
    content = re.sub(r"(?m)^[ \t]*\r?\n", "", head.group(1))
    return source[:head.start(1)] + content + source[head.end(1):]


def strip_metadata(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        data = attrs(match.group(0))
        if data.get("rel", "").lower() == "canonical":
            return ""
        return "" if any(data.get(attribute) == key for key, attribute in TARGETS.items()) else match.group(0)

    cleaned = TAG.sub(replace, JSONLD_SCRIPT.sub("", source))
    return strip_empty_head_lines(cleaned)


def block(
    heading: str,
    page_name: str,
    desc: str,
    url: str,
    image_url: str,
    width: int,
    height: int,
    language: str,
    home: bool,
    date: str | None,
) -> str:
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
    graph = []
    if home:
        graph.extend([
            {
                "@id": WEBSITE_ID,
                "@type": "WebSite",
                "url": f"{SITE}/",
                "name": SITE_NAME,
                "description": desc,
                "inLanguage": language,
                "publisher": {"@id": ORGANIZATION_ID},
            },
            {
                "@id": BLOG_ID,
                "@type": "Blog",
                "url": f"{SITE}/",
                "name": SITE_NAME,
                "description": desc,
                "author": {"@type": "Person", "name": AUTHOR},
                "publisher": {"@id": ORGANIZATION_ID},
                "isPartOf": {"@id": WEBSITE_ID},
            },
        ])
    if date:
        lines.append(f'    <meta property="article:published_time" content="{date}">')
        posting = {
            "@id": url + "#blogposting",
            "@type": "BlogPosting",
            "url": url,
            "name": heading,
            "headline": heading,
            "description": desc,
            "image": image_url,
            "inLanguage": language,
            "author": {"@type": "Person", "name": AUTHOR},
            "datePublished": date,
            "mainEntityOfPage": {"@id": url + "#webpage"},
            "publisher": {"@id": ORGANIZATION_ID},
            "isPartOf": {"@id": BLOG_ID},
        }
        graph.append(posting)
        graph.append(webpage(url, page_name, desc, language, {"@id": posting["@id"]}))
    else:
        graph.append(webpage(url, page_name, desc, language, {"@id": BLOG_ID}))
    schema = {"@context": "https://schema.org", "@graph": graph}
    lines.extend([
        '    <script type="application/ld+json">',
        "    " + json.dumps(schema, ensure_ascii=False, indent=4),
        "    </script>",
    ])
    return "\n".join(lines)


def normalize(path: Path, home: bool) -> None:
    source = path.read_bytes().decode("utf-8", errors="replace")
    heading = title(source, home)
    page_name = page_title(source)
    desc = description(source, heading, home)
    url = f"{SITE}/" if home else f"{SITE}/articles/{path.name}"
    date_match = DATE.match(path.stem)
    date = date_match.group(1).replace("_", "-") if date_match else None
    image_url, width, height = image(path, home, source)
    cleaned = strip_metadata(source)
    head = re.search(r"<head\b[^>]*>", cleaned, re.I)
    if not head:
        raise ValueError(f"<head> ausente: {path}")
    viewport = re.search(r'''<meta\b[^>]*\bname=["']viewport["'][^>]*>''', cleaned[head.end():], re.I)
    position = head.end() + viewport.end() if viewport else head.end()
    newline = "\r\n" if "\r\n" in source else "\n"
    metadata = block(
        heading, page_name, desc, url, image_url, width, height,
        page_language(source), home, date,
    ).replace("\n", newline)
    updated = cleaned[:position] + newline + metadata + cleaned[position:]
    path.write_text(updated, encoding="utf-8", newline="")


def normalize_privacy_page(path: Path) -> None:
    source = path.read_bytes().decode("utf-8")
    scripts = JSONLD_SCRIPT.findall(source)
    existing = json.loads(re.search(r">([\s\S]*?)</script\s*>", scripts[0], re.I).group(1)) if scripts else {}
    old_graph = existing.get("@graph", [existing])
    old_page = next(
        (node for node in old_graph if isinstance(node, dict) and node.get("@type") == "WebPage"),
        {},
    )
    canonical = f"{SITE}/privacidade.html"
    node = webpage(
        canonical,
        page_title(source),
        value(source, "description"),
        page_language(source),
    )
    node["author"] = {"@type": "Person", "name": AUTHOR}
    if old_page.get("dateModified"):
        node["dateModified"] = old_page["dateModified"]
    schema = {"@context": "https://schema.org", "@graph": [node]}
    block = (
        '    <script type="application/ld+json">\n'
        f'    {json.dumps(schema, ensure_ascii=False, indent=4)}\n'
        "    </script>"
    )
    cleaned = strip_empty_head_lines(JSONLD_SCRIPT.sub("", source))
    head = re.search(r"</head\s*>", cleaned, re.I)
    if not head:
        raise ValueError(f"</head> ausente: {path}")
    newline = "\r\n" if "\r\n" in source else "\n"
    block = block.replace("\n", newline)
    path.write_bytes((cleaned[:head.start()] + block + newline + cleaned[head.start():]).encode("utf-8"))


def main() -> None:
    files = [DOCS / "index.html"] + sorted(ARTICLES.glob("*.html"))
    for path in files:
        if path.name != "README.html":
            normalize(path, path == DOCS / "index.html")
    normalize_privacy_page(DOCS / "privacidade.html")
    print(f"Normalizados {len(files) - 1} artigos, a home e a política de privacidade.")


if __name__ == "__main__":
    main()