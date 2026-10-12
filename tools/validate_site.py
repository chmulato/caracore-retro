from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import subprocess
import sys
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTICLE_PATH = re.compile(r"^articles/(\d{4})_(\d{2})_(\d{2})_article_(\d+)\.html$")
REQUIRED_CATEGORIES = {
    "PDV",
    "Identidade Digital",
    "Roadmap",
    "Circuito",
    "Mineração e ETE",
}
HTTP_TIMEOUT_SECONDS = 10


@dataclass
class ArticleCard:
    href: str = ""
    title: str = ""
    summary: str = ""


@dataclass
class IndexData:
    title: str = ""
    description: str = ""
    canonical: str = ""
    h1_count: int = 0
    main_count: int = 0
    stylesheets: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    categories: set[str] = field(default_factory=set)
    cards: list[ArticleCard] = field(default_factory=list)


class IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.data = IndexData()
        self._current_card: ArticleCard | None = None
        self._capture: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self._capture = "title"
            self._text = []
        elif tag == "h1":
            self.data.h1_count += 1
        elif tag == "main":
            self.data.main_count += 1
        elif tag == "meta" and attributes.get("name", "").lower() == "description":
            self.data.description = attributes.get("content") or ""
        elif tag == "link" and attributes.get("rel", "").lower() == "canonical":
            self.data.canonical = attributes.get("href") or ""
        elif tag == "link" and attributes.get("rel", "").lower() == "stylesheet":
            self.data.stylesheets.append(attributes.get("href") or "")
        elif tag == "script" and attributes.get("src"):
            self.data.scripts.append(attributes["src"] or "")
        elif tag == "button" and attributes.get("data-category-filter"):
            self.data.categories.add(attributes["data-category-filter"] or "")
        elif tag == "li" and "article-item" in attributes.get("class", "").split():
            self._current_card = ArticleCard(summary=attributes.get("data-summary") or "")
            self.data.cards.append(self._current_card)
        elif tag == "a" and self._current_card is not None and not self._current_card.href:
            self._current_card.href = attributes.get("href") or ""
            self._capture = "article-title"
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._capture == "title":
            self.data.title = "".join(self._text).strip()
            self._capture = None
            self._text = []
        elif tag == "a" and self._capture == "article-title" and self._current_card:
            self._current_card.title = " ".join("".join(self._text).split())
            self._capture = None
            self._text = []
        elif tag == "li" and self._current_card:
            self._current_card = None

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)


class QuietRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


class Validator:
    def __init__(self) -> None:
        self.passed_checks = 0
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def check(self, passed: bool, label: str, detail: str = "") -> None:
        if passed:
            self.passed_checks += 1
            return
        message = f"{label}: {detail}" if detail else label
        self.failures.append(message)
        print(f"  FAIL  {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"  WARN  {message}")


def parse_index(source: str) -> IndexData:
    parser = IndexParser()
    parser.feed(source)
    parser.close()
    return parser.data


def inspect_feed(validator: Validator, article_hrefs: list[str]) -> None:
    feed_path = DOCS / "feed.xml"
    try:
        root = ElementTree.parse(feed_path).getroot()
    except (ElementTree.ParseError, OSError) as error:
        validator.check(False, "RSS bem-formado", str(error))
        return

    validator.check(root.tag == "rss" and root.attrib.get("version") == "2.0", "RSS versão 2.0")
    channel = root.find("channel")
    validator.check(channel is not None, "Canal RSS presente")
    if channel is None:
        return

    channel_title = channel.findtext("title", default="").strip()
    channel_link = channel.findtext("link", default="").strip()
    channel_desc = channel.findtext("description", default="").strip()
    channel_lang = channel.findtext("language", default="").strip()
    channel_copy = channel.findtext("copyright", default="").strip()
    channel_atom = channel.find("{http://www.w3.org/2005/Atom}link")

    validator.check(bool(channel_title), "RSS título do canal")
    validator.check(channel_link == "https://retro.caracore.com.br/", "RSS link do canal")
    validator.check(bool(channel_desc), "RSS descrição do canal")
    validator.check(channel_lang == "pt-BR", "RSS idioma do canal", channel_lang)
    validator.check(bool(channel_copy), "RSS copyright do canal")
    validator.check(
        channel_atom is not None
        and channel_atom.attrib.get("rel") == "self"
        and channel_atom.attrib.get("type") == "application/rss+xml"
        and channel_atom.attrib.get("href") == "https://retro.caracore.com.br/feed.xml",
        "RSS atom:link canônico",
    )

    image = channel.find("image")
    image_url = image.findtext("url", default="").strip() if image is not None else ""
    image_file = local_path(urlparse(image_url).path) if image_url else None
    validator.check(
        image is not None and bool(image_url) and image_file is not None and image_file.exists(),
        "RSS imagem do canal",
        image_url,
    )

    items = channel.findall("item")
    expected_links = [f"https://retro.caracore.com.br/{href}" for href in article_hrefs]
    actual_links = [item.findtext("link", default="").strip() for item in items]
    validator.check(len(items) == len(article_hrefs), "Quantidade de itens RSS", str(len(items)))
    validator.check(actual_links == expected_links, "RSS corresponde à ordem e aos links do índice")

    invalid_dates = []
    missing_cats = []
    missing_enclosures = []
    missing_authors = []
    missing_descriptions = []

    for item in items:
        link = item.findtext("link", default="")
        published = item.findtext("pubDate", default="")
        match = ARTICLE_PATH.fullmatch(urlparse(link).path.lstrip("/"))
        try:
            feed_date = parsedate_to_datetime(published).date()
        except (TypeError, ValueError, OverflowError):
            invalid_dates.append(link)
            continue
        if not match or feed_date.isoformat() != "-".join(match.group(i) for i in (1, 2, 3)):
            invalid_dates.append(link)

        categories = [c.text.strip() for c in item.findall("category") if c.text]
        if not categories:
            missing_cats.append(link)

        enclosure = item.find("enclosure")
        if enclosure is None:
            missing_enclosures.append(link)
        else:
            enc_url = enclosure.attrib.get("url", "")
            enc_type = enclosure.attrib.get("type", "")
            enc_len = enclosure.attrib.get("length", "0")
            enc_file = local_path(urlparse(enc_url).path)
            if (
                not enc_url
                or enc_type != "image/png"
                or not enc_file
                or not enc_file.exists()
                or int(enc_len) != enc_file.stat().st_size
            ):
                missing_enclosures.append(link)

        creator = item.findtext("{http://purl.org/dc/elements/1.1/}creator", default="").strip()
        author = item.findtext("author", default="").strip()
        if not creator and not author:
            missing_authors.append(link)

        desc = item.findtext("description", default="").strip()
        if not desc:
            missing_descriptions.append(link)

    validator.check(not invalid_dates, "Datas RSS correspondem às datas dos artigos", ", ".join(invalid_dates[:5]))
    validator.check(not missing_cats, "Itens RSS possuem categorias válidas", ", ".join(missing_cats[:5]))
    validator.check(not missing_enclosures, "Itens RSS possuem capas/enclosures válidos", ", ".join(missing_enclosures[:5]))
    validator.check(not missing_authors, "Itens RSS possuem autor/criador", ", ".join(missing_authors[:5]))
    validator.check(not missing_descriptions, "Itens RSS possuem descrição não vazia", ", ".join(missing_descriptions[:5]))


def local_path(relative_path: str) -> Path | None:
    parsed = urlparse(relative_path)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    resolved = (DOCS / parsed.path.lstrip("/")).resolve()
    if not resolved.is_relative_to(DOCS.resolve()):
        return None
    return resolved


def inspect_index(validator: Validator) -> tuple[IndexData, str, str]:
    index_path = DOCS / "index.html"
    try:
        source = index_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        validator.check(False, "Lendo docs/index.html", str(error))
        return IndexData(), "", ""

    data = parse_index(source)
    validator.check(data.h1_count == 1, "Hierarquia do título principal", f"{data.h1_count} <h1>")
    validator.check(data.main_count == 1, "Landmark principal", f"{data.main_count} <main>")
    validator.check(bool(data.title), "Título da página")
    validator.check(bool(data.description.strip()), "Meta description")
    validator.check(bool(data.canonical.strip()), "URL canônica")
    validator.check(bool(data.cards), "Catálogo de artigos", f"{len(data.cards)} cards")
    validator.check(
        REQUIRED_CATEGORIES <= data.categories,
        "Categorias editoriais",
        ", ".join(sorted(data.categories)),
    )

    hrefs = [card.href for card in data.cards]
    valid_dates = [ARTICLE_PATH.match(href) for href in hrefs]
    validator.check(
        all(valid_dates),
        "Links dos artigos",
        f"{sum(match is not None for match in valid_dates)}/{len(hrefs)} URLs com data e número válidos",
    )
    if all(valid_dates) and valid_dates:
        dated_hrefs = [
            (
                (match.group(1), match.group(2), match.group(3), int(match.group(4))),
                href,
            )
            for match, href in zip(valid_dates, hrefs)
            if match
        ]
        latest_href = max(dated_hrefs, key=lambda item: item[0])[1]
        validator.check(
            hrefs[0] == latest_href,
            "Artigo em destaque é o mais recente",
            f"esperado {latest_href}; primeiro card {hrefs[0]}",
        )

    duplicate_hrefs = [href for href, count in Counter(hrefs).items() if count > 1]
    validator.check(not duplicate_hrefs, "Links de artigo sem duplicação", ", ".join(duplicate_hrefs))
    inspect_feed(validator, hrefs)
    print(
        f"  Catálogo: {len(data.cards)} artigos, "
        f"{len(data.categories)} categorias visuais e {len(set(hrefs))} links únicos."
    )

    covers: list[str] = []
    for card in data.cards:
        valid_path = ARTICLE_PATH.match(card.href)
        if not valid_path:
            continue

        validator.check(bool(card.title), f"Título do artigo {card.href}")
        validator.check(bool(card.summary.strip()), f"Resumo do artigo {card.href}")
        article_file = local_path(card.href)
        validator.check(
            article_file is not None and article_file.is_file(),
            f"Arquivo do artigo {card.href}",
        )
        if article_file is not None and article_file.is_file():
            try:
                article_data = parse_index(article_file.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError) as error:
                validator.check(False, f"Estrutura do artigo {card.href}", str(error))
            else:
                validator.check(
                    article_data.main_count == 1,
                    f"Landmark principal em {Path(card.href).name}",
                    f"{article_data.main_count} <main>",
                )
                validator.check(
                    article_data.h1_count == 1,
                    f"Título principal em {Path(card.href).name}",
                    f"{article_data.h1_count} <h1>",
                )
        cover_path = f"articles/assets/img/{Path(card.href).stem}_01.png"
        covers.append(cover_path)
        cover_file = local_path(cover_path)
        validator.check(
            cover_file is not None and cover_file.is_file(),
            f"Capa local {Path(cover_path).name}",
        )

    css_file = DOCS / "assets" / "css" / "editorial.css"
    js_file = DOCS / "assets" / "js" / "editorial-index.js"
    try:
        css = css_file.read_text(encoding="utf-8-sig")
        js = js_file.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        validator.check(False, "Arquivos do layout editorial", str(error))
        return data, "", covers[0] if covers else ""

    grid_rules = re.findall(
        r"\.sala-page\s+\.editorial-container\s+\.article-list\s*\{([^}]*)\}",
        css,
    )
    column_declarations = [
        re.search(r"grid-template-columns:\s*([^;]+)", rule)
        for rule in grid_rules
    ]
    columns = [match.group(1).strip() for match in column_declarations if match]
    responsive_grid = (
        any(re.search(r"repeat\(\s*3\s*,", value) for value in columns)
        and any(re.search(r"repeat\(\s*2\s*,", value) for value in columns)
        and any(re.fullmatch(r"1fr", value) for value in columns)
    )
    validator.check(responsive_grid, "Grade responsiva declarada", "3 desktop / 2 tablet / 1 mobile")
    validator.check(
        re.search(r"\.editorial-excerpt\s*\{[^}]*-webkit-line-clamp:\s*2", css, re.S) is not None,
        "Resumos limitados a duas linhas",
    )
    validator.check(
        "items.forEach((item, index) => decorate(item, index === 0))" in js,
        "Capa editorial montada para o artigo em destaque",
    )
    validator.check(
        "data-category-filter" in js and "editorialCategory" in js,
        "Interação de categorias ligada ao arquivo",
    )
    featured_href = data.cards[0].href if data.cards else ""
    featured_cover = f"articles/assets/img/{Path(featured_href).stem}_01.png" if featured_href else ""
    return data, featured_href, featured_cover


def request_url(url: str, method: str = "GET") -> bytes:
    request = Request(url, method=method, headers={"User-Agent": "CaraCoreSiteValidator/1.0"})
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        if response.status < 200 or response.status >= 400:
            raise HTTPError(url, response.status, "Unexpected HTTP status", response.headers, None)
        return response.read() if method == "GET" else b""


def http_smoke_test(
    validator: Validator,
    base_url: str,
    data: IndexData,
    featured_href: str,
    featured_cover: str,
) -> None:
    parsed_base = urlparse(base_url)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
        validator.check(False, "URL de preview", "informe uma URL HTTP ou HTTPS válida")
        return

    if not base_url.endswith("/"):
        base_url += "/"

    print(f"\nHTTP smoke test: {base_url}")
    try:
        page = request_url(urljoin(base_url, "index.html")).decode("utf-8-sig")
    except (HTTPError, URLError, TimeoutError, UnicodeError, OSError) as error:
        validator.check(False, "Carregamento HTTP do índice", str(error))
        return

    served_index = parse_index(page)
    validator.check(served_index.title == data.title, "Título servido por HTTP", served_index.title)
    validator.check(
        len(served_index.cards) == len(data.cards),
        "Quantidade de cards servida por HTTP",
        str(len(served_index.cards)),
    )

    required_resources = [*data.stylesheets, *data.scripts, "feed.xml", featured_href, featured_cover]
    checked: set[str] = set()
    for resource in required_resources:
        if not resource or resource in checked:
            continue
        checked.add(resource)
        try:
            content = request_url(urljoin(base_url, resource))
            validator.check(bool(content), f"Recurso HTTP {resource}")
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            validator.check(False, f"Recurso HTTP {resource}", str(error))


def run_integrity_suite(validator: Validator) -> None:
    print("\nIntegridade HTML e CSS existente:")
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "test_blog.py")],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        validator.check(False, "Executando python test_blog.py", str(error))
        return

    output = result.stdout + result.stderr
    summary = next(
        (line.strip() for line in output.splitlines() if "TEST SUMMARY" in line),
        "Resumo da suíte de integridade não encontrado.",
    )
    failures: list[str] = []
    include_failure_details = False
    for line in output.splitlines():
        if " - FAILED:" in line:
            include_failure_details = True
        elif include_failure_details and not line.startswith("   -"):
            include_failure_details = False
        if " - FAILED:" in line or (include_failure_details and line.startswith("   -")):
            failures.append(line.strip())
    suite_detail = summary
    if result.returncode != 0 and failures:
        suite_detail += " " + " | ".join(failures[:8])
    validator.check(result.returncode == 0, "python test_blog.py", suite_detail)
    warnings = [line.strip() for line in output.splitlines() if "[WARN]" in line]
    if warnings:
        validator.warn(
            f"Suíte de integridade registrou {len(warnings)} avisos SEO existentes; "
            f"exemplo: {warnings[0]}"
        )


def run_local_http_test(
    validator: Validator,
    data: IndexData,
    featured_href: str,
    featured_cover: str,
) -> None:
    class DocsRequestHandler(QuietRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(DOCS), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), DocsRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        http_smoke_test(
            validator,
            f"http://127.0.0.1:{server.server_port}/",
            data,
            featured_href,
            featured_cover,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=HTTP_TIMEOUT_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida o catálogo editorial do blog, recursos locais e publicação HTTP estática."
    )
    parser.add_argument(
        "--url",
        help="Valida também um preview ou site já publicado; sem esta opção, inicia um servidor local temporário.",
    )
    args = parser.parse_args()

    validator = Validator()
    print("Validação estática do blog:")
    data, featured_href, featured_cover = inspect_index(validator)

    if args.url:
        http_smoke_test(validator, args.url, data, featured_href, featured_cover)
    else:
        run_local_http_test(validator, data, featured_href, featured_cover)

    run_integrity_suite(validator)

    print("\nResultado:")
    print(f"  Verificações aprovadas: {validator.passed_checks}")
    if validator.failures:
        print(f"REPROVADO — {len(validator.failures)} verificação(ões) falharam.")
        return 1
    if validator.warnings:
        print(f"APROVADO COM RESSALVAS — {len(validator.warnings)} aviso(s); revise antes da publicação.")
        return 0
    print("APROVADO — as verificações automatizadas foram concluídas sem avisos.")
    print("Nota: interação JavaScript, aparência visual e acessibilidade exigem inspeção em navegador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
