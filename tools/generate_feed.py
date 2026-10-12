"""Gera o feed.xml saudável, padronizado e com metadados visuais para leitores RSS."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import unicodedata
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX_PATH = DOCS / "index.html"
FEED_PATH = DOCS / "feed.xml"
SITE_URL = "https://retro.caracore.com.br"
AUTHOR_NAME = "Christian Mulato"
EDITOR_EMAIL = "suporte@caracore.com.br (Christian Mulato)"

ARTICLE_RE = re.compile(r"^articles/(\d{4})_(\d{2})_(\d{2})_article_(\d+)\.html$")

CATEGORY_RULES = [
    ("PDV", re.compile(r"\bpdv\b|ponto de venda|varejo|terminal de venda|checkout|caixa")),
    ("Identidade Digital", re.compile(r"identidade|oidc|oauth|pkce|autentic|credencial|seguran")),
    ("Mineração e ETE", re.compile(r"miner|ete\b|hidrometalurg|processo quimic|saneamento|terras raras")),
    ("Circuito", re.compile(r"circuito|educa|aprendiz|aluno|escola|formacao")),
    ("Roadmap", re.compile(r"roadmap|hub|logistic|estrateg|finops|planejamento|portfolio")),
]


def normalize(value: str) -> str:
    val = (value or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", val) if unicodedata.category(c) != "Mn")


def get_category(tags_str: str) -> str:
    norm = normalize(tags_str)
    for name, expr in CATEGORY_RULES:
        if expr.search(norm):
            return name
    return "Tecnologia"


class ArticleItem:
    def __init__(self) -> None:
        self.href = ""
        self.title = ""
        self.summary = ""
        self.tags: list[str] = []
        self.category = "Tecnologia"


class IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.articles: list[ArticleItem] = []
        self._cur: ArticleItem | None = None
        self._capture: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get("class") or "").split()
        if tag == "li" and "article-item" in classes:
            tags_raw = attrs_dict.get("data-tags") or ""
            summary_raw = attrs_dict.get("data-summary") or ""
            self._cur = ArticleItem()
            self._cur.tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            self._cur.summary = summary_raw.strip()
            self._cur.category = get_category(tags_raw)
            self.articles.append(self._cur)
        elif self._cur is not None:
            if tag == "a" and "article-title" in classes:
                self._cur.href = (attrs_dict.get("href") or "").strip()
                self._capture = "title"
                self._text = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture == "title" and self._cur:
            self._cur.title = " ".join("".join(self._text).split())
            self._capture = None
            self._text = []
        elif tag == "li" and self._cur:
            self._cur = None

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)


def clean_cdata(text: str) -> str:
    return text.replace("]]>", "]]&gt;")


def build_feed_xml(articles: list[ArticleItem]) -> str:
    if not articles:
        raise ValueError("Nenhum artigo encontrado para o feed.")

    latest_article = articles[0]
    match = ARTICLE_RE.match(latest_article.href)
    if not match:
        raise ValueError(f"URL de artigo inválida: {latest_article.href}")

    latest_dt = datetime(
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )
    last_build_date = format_datetime(latest_dt)

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xmlns:dc="http://purl.org/dc/elements/1.1/">',
        '  <channel>',
        '    <title><![CDATA[Artigos Retrô — Cara Core Informática]]></title>',
        f'    <link>{SITE_URL}/</link>',
        '    <description><![CDATA[Coleção de artigos publicados pela Cara Core nas redes, organizada por ano.]]></description>',
        '    <language>pt-BR</language>',
        '    <copyright><![CDATA[© Cara Core Informática. Todos os direitos reservados.]]></copyright>',
        f'    <managingEditor>{EDITOR_EMAIL}</managingEditor>',
        f'    <webMaster>{EDITOR_EMAIL}</webMaster>',
        f'    <lastBuildDate>{last_build_date}</lastBuildDate>',
        '    <category><![CDATA[Tecnologia]]></category>',
        '    <docs>https://www.rssboard.org/rss-specification</docs>',
        '    <generator>Cara Core RSS generator</generator>',
        f'    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />',
        '    <image>',
        f'      <url>{SITE_URL}/assets/img/logo.png</url>',
        '      <title><![CDATA[Artigos Retrô — Cara Core Informática]]></title>',
        f'      <link>{SITE_URL}/</link>',
        '    </image>',
    ]

    for article in articles:
        m = ARTICLE_RE.match(article.href)
        if not m:
            raise ValueError(f"Formato de link de artigo inválido: {article.href}")

        pub_dt = datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            12,
            0,
            0,
            tzinfo=timezone.utc,
        )
        pub_date_str = format_datetime(pub_dt)

        article_url = f"{SITE_URL}/{article.href}"
        img_rel = article.href.replace("articles/", "articles/assets/img/").replace(".html", "_01.png")
        img_file = DOCS / img_rel
        if not img_file.exists():
            raise FileNotFoundError(f"Imagem de capa não encontrada: {img_file}")

        file_size = os.path.getsize(img_file)
        with Image.open(img_file) as img:
            width, height = img.size

        img_url = f"{SITE_URL}/{img_rel}"

        lines.append("")
        lines.append("    <item>")
        lines.append(f"      <title><![CDATA[{clean_cdata(article.title)}]]></title>")
        lines.append(f"      <link>{article_url}</link>")
        lines.append(f'      <guid isPermaLink="true">{article_url}</guid>')
        lines.append(f"      <description><![CDATA[{clean_cdata(article.summary)}]]></description>")
        lines.append(f"      <dc:creator><![CDATA[{AUTHOR_NAME}]]></dc:creator>")
        lines.append(f"      <pubDate>{pub_date_str}</pubDate>")
        lines.append(f"      <category><![CDATA[{article.category}]]></category>")

        # Adiciona tags não duplicadas da categoria
        for tag in article.tags:
            tag_title = tag.title()
            if tag_title.lower() != article.category.lower() and tag_title.lower() != "cara core":
                lines.append(f"      <category><![CDATA[{clean_cdata(tag_title)}]]></category>")

        lines.append(f'      <enclosure url="{img_url}" length="{file_size}" type="image/png" />')
        lines.append(f'      <media:content url="{img_url}" medium="image" type="image/png" width="{width}" height="{height}">')
        lines.append(f'        <media:thumbnail url="{img_url}" width="{width}" height="{height}" />')
        lines.append("      </media:content>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    lines.append("")

    return "\n".join(lines)


def generate_feed() -> None:
    source = INDEX_PATH.read_text(encoding="utf-8")
    parser = IndexParser()
    parser.feed(source)

    feed_xml_content = build_feed_xml(parser.articles)
    FEED_PATH.write_text(feed_xml_content, encoding="utf-8", newline="\n")
    print(f"Sucesso: {len(parser.articles)} artigos gerados em {FEED_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    generate_feed()
