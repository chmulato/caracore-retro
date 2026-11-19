from __future__ import annotations

import html
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = "https://retro.caracore.com.br"
WEBSITE_ID = SITE + "/#website"
BLOG_ID = SITE + "/#blog"
ORGANIZATION_ID = "https://caracore.com.br/#organization"
META = [("description", "name"), ("author", "name"), ("og:title", "property"), ("og:description", "property"), ("og:type", "property"), ("og:url", "property"), ("og:image", "property"), ("og:image:width", "property"), ("og:image:height", "property"), ("og:site_name", "property"), ("twitter:card", "name"), ("twitter:title", "name"), ("twitter:description", "name"), ("twitter:image", "name")]
TAG = re.compile(r"<meta\b[^>]*>|<link\b[^>]*>", re.I | re.S)
SCRIPT = re.compile(r'<script\b(?=[^>]*\btype=["\']application/ld\+json["\'])[^>]*>(.*?)</script\s*>', re.I | re.S)
ATTR = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.I | re.S)
TITLE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
LANGUAGE = re.compile(r"<html\b[^>]*\blang\s*=\s*['\"]([^'\"]+)['\"]", re.I)
REFERENCE_FIELDS = ("author", "publisher", "isPartOf", "mainEntity", "mainEntityOfPage")


def attrs(tag: str) -> dict[str, str]:
    return {key.lower(): value for key, _, value in ATTR.findall(tag)}


def sitemap_pages() -> list[tuple[Path, str]]:
    try:
        root = ET.parse(DOCS / "sitemap.xml").getroot()
    except (OSError, ET.ParseError) as error:
        raise SystemExit(f"sitemap.xml inválido: {error}") from error

    urls = [
        node.text or ""
        for node in root.iter()
        if node.tag.endswith("loc")
    ]
    if not urls or len(urls) != len(set(urls)):
        raise SystemExit("sitemap.xml vazio ou com URLs duplicadas.")

    pages = []
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != urlparse(SITE).netloc:
            raise SystemExit(f"URL fora do host canônico: {url}")
        relative = parsed.path.lstrip("/")
        path = DOCS / relative if relative else DOCS / "index.html"
        if path.is_dir():
            path /= "index.html"
        try:
            path.resolve().relative_to(DOCS.resolve())
        except ValueError as error:
            raise SystemExit(f"URL fora de docs/: {url}") from error
        if not path.is_file():
            raise SystemExit(f"URL do sitemap sem arquivo local: {url}")
        pages.append((path, url))

    expected = {
        DOCS / "index.html",
        DOCS / "privacidade.html",
        *DOCS.joinpath("articles").glob("*.html"),
    }
    if {path for path, _ in pages} != expected:
        raise SystemExit("sitemap.xml não corresponde à home, privacidade e artigos locais.")
    return pages


def node_has_type(node: dict, expected: str) -> bool:
    value = node.get("@type")
    return value == expected or isinstance(value, list) and expected in value


def referenced_ids(value) -> list[str]:
    if isinstance(value, dict):
        identity = value.get("@id")
        if isinstance(identity, str) and len(value) == 1:
            return [identity]
        return [identity for item in value.values() for identity in referenced_ids(item)]
    if isinstance(value, list):
        return [identity for item in value for identity in referenced_ids(item)]
    return []


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None
    return struct.unpack(">II", data[16:24])


def main() -> None:
    failures: list[str] = []
    pages = sitemap_pages()
    declared_ids: dict[str, str] = {}
    id_references: list[tuple[str, str]] = []
    article_count = page_count = 0

    robots = DOCS / "robots.txt"
    if not robots.is_file() or f"Sitemap: {SITE}/sitemap.xml" not in robots.read_text(encoding="utf-8-sig"):
        failures.append("robots.txt: sitemap canônico ausente")

    for path, canonical in pages:
        source = path.read_text(encoding="utf-8")
        tags = [attrs(tag) for tag in TAG.findall(source)]
        for key, attribute in META:
            if sum(data.get(attribute) == key for data in tags) != 1:
                failures.append(f"{path.name}: meta {key}")
        descriptions = [
            html.unescape(data.get("content", "")).strip()
            for data in tags
            if data.get("name", "").lower() == "description"
        ]
        if len(descriptions) != 1 or not 150 <= len(descriptions[0]) <= 250:
            failures.append(f"{path.name}: description length")
            description = ""
        else:
            description = descriptions[0]
        canonicals = [
            data.get("href")
            for data in tags
            if data.get("rel", "").lower() == "canonical"
        ]
        if canonicals != [canonical]:
            failures.append(f"{path.name}: canonical")

        if any(data.get("property", "").lower() == "og:url" and data.get("content") != canonical for data in tags):
            failures.append(f"{path.name}: og:url")
        og_images = [
            data.get("content", "")
            for data in tags
            if data.get("property", "").lower() == "og:image"
        ]
        twitter_images = [
            data.get("content", "")
            for data in tags
            if data.get("name", "").lower() == "twitter:image"
        ]
        if len(og_images) == 1 and len(twitter_images) == 1 and og_images[0] != twitter_images[0]:
            failures.append(f"{path.name}: OG/Twitter image mismatch")
        if len(og_images) == 1:
            image_url = urlparse(og_images[0])
            image_path = DOCS / image_url.path.lstrip("/")
            try:
                image_path.resolve().relative_to(DOCS.resolve())
            except ValueError:
                failures.append(f"{path.name}: og:image fora de docs/")
            else:
                if image_url.netloc != urlparse(SITE).netloc or not image_path.is_file():
                    failures.append(f"{path.name}: og:image inválida ou ausente")

        if any(
            data.get("name", "").lower() in {"robots", "googlebot"}
            and re.search(r"\bnoindex\b", data.get("content", ""), re.I)
            for data in tags
        ) or any(data.get("http-equiv", "").lower() == "refresh" for data in tags):
            failures.append(f"{path.name}: página não indexável está no sitemap")

        title_match = TITLE.search(source)
        language_match = LANGUAGE.search(source)
        title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else ""
        language = language_match.group(1) if language_match else ""
        if not title:
            failures.append(f"{path.name}: title ausente")
        if not language:
            failures.append(f"{path.name}: html lang ausente")

        try:
            scripts = SCRIPT.findall(source)
            if len(scripts) != 1:
                raise ValueError(f"esperado um JSON-LD, encontrados {len(scripts)}")
            schema = json.loads(scripts[0])
        except (ValueError, json.JSONDecodeError) as error:
            failures.append(f"{path.name}: JSON-LD inválido ({error})")
            continue
        graph = schema.get("@graph")
        if schema.get("@context") != "https://schema.org" or not isinstance(graph, list):
            failures.append(f"{path.name}: esperado grafo schema.org")
            continue
        if not all(isinstance(node, dict) and node.get("@type") for node in graph):
            failures.append(f"{path.name}: nó JSON-LD inválido")
            continue

        for node in graph:
            if "@context" in node:
                failures.append(f"{path.name}: @context deve ficar no grafo")
            identity = node.get("@id")
            if identity:
                if identity in declared_ids:
                    failures.append(f"{path.name}: @id duplicado ({identity})")
                else:
                    declared_ids[identity] = path.name
            for field in REFERENCE_FIELDS:
                id_references.extend(
                    (reference, path.name)
                    for reference in referenced_ids(node.get(field))
                )

        web_pages = [node for node in graph if node_has_type(node, "WebPage")]
        if len(web_pages) != 1:
            failures.append(f"{path.name}: esperado um nó WebPage")
        else:
            page_count += 1
            page_node = web_pages[0]
            expected_page = {
                "@id": canonical + "#webpage",
                "url": canonical,
                "name": title,
                "description": description,
                "inLanguage": language,
                "isPartOf": {"@id": WEBSITE_ID},
                "publisher": {"@id": ORGANIZATION_ID},
            }
            if any(page_node.get(key) != value for key, value in expected_page.items()):
                failures.append(f"{path.name}: nó WebPage não acompanha canonical/title/description")

        if path == DOCS / "index.html":
            websites = [node for node in graph if node_has_type(node, "WebSite")]
            blogs = [node for node in graph if node_has_type(node, "Blog")]
            if len(websites) != 1 or len(blogs) != 1:
                failures.append("index.html: esperado um WebSite e um Blog")
            elif websites[0].get("@id") != WEBSITE_ID or blogs[0].get("@id") != BLOG_ID:
                failures.append("index.html: identidade WebSite/Blog")
        elif path.parent == DOCS / "articles":
            article_count += 1
            postings = [node for node in graph if node_has_type(node, "BlogPosting")]
            dates = [
                data.get("content", "")
                for data in tags
                if data.get("property", "").lower() == "article:published_time"
            ]
            expected_date = "_".join(path.stem.split("_")[:3]).replace("_", "-")
            if len(postings) != 1 or len(dates) != 1 or dates[0] != expected_date:
                failures.append(f"{path.name}: BlogPosting/article:published_time")
            elif (
                postings[0].get("@id") != canonical + "#blogposting"
                or postings[0].get("datePublished") != expected_date
                or postings[0].get("mainEntityOfPage") != {"@id": canonical + "#webpage"}
                or postings[0].get("publisher") != {"@id": ORGANIZATION_ID}
                or postings[0].get("isPartOf") != {"@id": BLOG_ID}
                or postings[0].get("description") != description
                or postings[0].get("image") != og_images[0]
            ):
                failures.append(f"{path.name}: BlogPosting inconsistente")
            elif postings[0].get("author", {}).get("name") != "Christian Mulato":
                failures.append(f"{path.name}: author do BlogPosting")
        elif any(node_has_type(node, "BlogPosting") for node in graph):
            failures.append(f"{path.name}: BlogPosting fora de página de artigo")

    for identity, path_name in id_references:
        if identity not in declared_ids and identity != ORGANIZATION_ID:
            failures.append(f"{path_name}: referência @id sem nó correspondente ({identity})")

    social = ROOT / "docs" / "articles" / "assets" / "img" / "social-default.png"
    if png_size(social) != (1200, 630):
        failures.append("social-default.png: dimensions")
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"OK: {len(pages)} URLs; {article_count} BlogPosting; {page_count} WebPage; "
        "canonicals, metadados sociais, imagens e referências JSON-LD válidos."
    )


if __name__ == "__main__":
    main()