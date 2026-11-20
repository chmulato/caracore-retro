"""Prepara e confere rascunhos para o Facebook; não aprova nem publica."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://retro.caracore.com.br"
ZONE = ZoneInfo("America/Sao_Paulo")
ARTICLE_NAME = re.compile(r"^(\d{4})_(\d{2})_(\d{2})_article_(\d+)\.html$")
IMAGE_NAME = re.compile(r"^[A-Za-z0-9_.-]+\.(?:png|jpe?g|webp)$", re.IGNORECASE)
METADATA_KEYS = {"og:title", "og:description", "og:url", "og:image", "article:published_time"}


class ArticleMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.values: dict[str, set[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "head":
            self.in_head = True
        if self.in_head and tag.lower() == "meta":
            attrs_dict = dict(attrs)
            key = attrs_dict.get("property")
            value = attrs_dict.get("content")
            if key in METADATA_KEYS and value and value.strip():
                self.values.setdefault(key, set()).add(value.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "head":
            self.in_head = False

    def get(self, key: str) -> str:
        values = self.values.get(key, set())
        if len(values) != 1:
            raise ValueError(f"Metadado ausente ou divergente: {key}")
        return next(iter(values))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_digest(content: dict) -> str:
    data = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(data.encode("utf-8"))


def local_time(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError as error:
        raise ValueError("Use data e hora no formato AAAA-MM-DDTHH:MM.") from error
    if parsed.strftime("%Y-%m-%dT%H:%M") != value:
        raise ValueError("Use data e hora no formato AAAA-MM-DDTHH:MM.")
    first = parsed.replace(tzinfo=ZONE, fold=0)
    second = parsed.replace(tzinfo=ZONE, fold=1)
    if first.utcoffset() != second.utcoffset() or first.astimezone(timezone.utc).astimezone(ZONE).replace(tzinfo=None) != parsed:
        raise ValueError("Data e hora ambiguas ou inexistentes no fuso de Sao Paulo.")
    return first


def prepare(article: Path, page_id: str, when: str, message: str | None = None,
            root: Path = ROOT, immediate: bool = False) -> dict:
    match = ARTICLE_NAME.fullmatch(article.name)
    articles_dir = (root / "docs" / "articles").resolve()
    if not match or article.resolve().parent != articles_dir:
        raise ValueError("Arquivo de artigo invalido.")
    if not re.fullmatch(r"[0-9]+", page_id):
        raise ValueError("O identificador da pagina deve conter apenas numeros.")
    if type(immediate) is not bool:
        raise ValueError("O modo de publicacao e invalido.")
    try:
        editorial_date = date(*(int(part) for part in match.groups()[:3]))
    except ValueError as error:
        raise ValueError("Data editorial invalida no nome do artigo.") from error
    scheduled = local_time(when)
    if not immediate and (scheduled.weekday() not in (1, 3) or (scheduled.hour, scheduled.minute) != (9, 0)):
        raise ValueError("Agende nas tercas e quintas, as 09:00 no horario de Brasilia (America/Sao_Paulo).")

    article_bytes = article.read_bytes()
    metadata = ArticleMetadata()
    metadata.feed(article_bytes.decode("utf-8"))
    title = metadata.get("og:title")
    description = metadata.get("og:description")
    url = metadata.get("og:url")
    image_url = metadata.get("og:image")
    if metadata.get("article:published_time") != editorial_date.isoformat():
        raise ValueError("A data editorial diverge dos metadados do artigo.")
    if url != f"{SITE}/articles/{article.name}":
        raise ValueError("O link do artigo nao corresponde ao arquivo selecionado.")

    image_parts = urlsplit(image_url)
    image_prefix = "/articles/assets/img/"
    image_name = image_parts.path.removeprefix(image_prefix)
    if (image_parts.scheme != "https" or image_parts.netloc != "retro.caracore.com.br"
            or not image_parts.path.startswith(image_prefix) or image_parts.query
            or image_parts.fragment or not IMAGE_NAME.fullmatch(image_name)):
        raise ValueError("A imagem deve ser um arquivo local do blog Retro.")
    images_dir = (articles_dir / "assets" / "img").resolve()
    image_path = images_dir / image_name
    if image_path.resolve().parent != images_dir:
        raise ValueError("Caminho da imagem invalido.")
    image_bytes = image_path.read_bytes()

    if message is None:
        message = (f"{description}\n\nE na sua rotina, esse assunto também faz diferença?\n\n"
                   f"Leia ‘{title}’ no blog Retrô:\n{url}")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("A chamada do Facebook nao pode ficar vazia.")

    content = {
        "versao": 1,
        "rede": "facebook-pagina",
        "pagina_id": page_id,
        "artigo": f"docs/articles/{article.name}",
        "data_editorial": editorial_date.isoformat(),
        "data_hora_local": when,
        "fuso": "America/Sao_Paulo",
        "data_hora_utc": scheduled.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mensagem": message,
        "link": url,
        "titulo_previa": title,
        "descricao_previa": description,
        "imagem_url": image_url,
        "imagem_sha256": sha256(image_bytes),
        "artigo_sha256": sha256(article_bytes),
    }
    if immediate:
        content["modo_publicacao"] = "imediata"
    return {
        "estado": "RASCUNHO_NAO_APROVADO",
        "conteudo": content,
        "sha256_conteudo": content_digest(content),
        "aviso": "A previa real no Facebook e o conteudo publicado no site nao foram conferidos.",
    }


def verify(draft: dict, root: Path = ROOT) -> None:
    if not isinstance(draft, dict) or draft.get("estado") != "RASCUNHO_NAO_APROVADO":
        raise ValueError("Arquivo nao e um rascunho nao aprovado.")
    content = draft.get("conteudo")
    if not isinstance(content, dict) or draft.get("sha256_conteudo") != content_digest(content):
        raise ValueError("O conteudo mudou desde a geracao do rascunho.")
    try:
        name = content["artigo"].removeprefix("docs/articles/")
        if content["artigo"] != f"docs/articles/{name}" or not ARTICLE_NAME.fullmatch(name):
            raise ValueError("Arquivo de artigo invalido.")
        mode = content.get("modo_publicacao")
        if mode not in (None, "imediata"):
            raise ValueError("Modo de publicacao invalido.")
        current = prepare(root / "docs" / "articles" / name, content["pagina_id"],
                          content["data_hora_local"], content["mensagem"], root,
                          immediate=mode == "imediata")
    except (KeyError, AttributeError, TypeError) as error:
        raise ValueError("Conteudo do rascunho invalido.") from error
    if current["conteudo"] != content:
        raise ValueError("O artigo, a imagem ou os dados do rascunho mudaram.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("preparar", help="gera JSON de rascunho na saida padrao")
    create.add_argument("--artigo", required=True, help="numero do artigo")
    create.add_argument("--pagina", required=True, help="identificador numerico da pagina")
    create.add_argument("--quando", required=True, help="tercas/quintas as 09:00 de Brasilia: AAAA-MM-DDTHH:MM")
    create.add_argument("--texto", type=Path, help="arquivo UTF-8 com a chamada personalizada")
    check = commands.add_parser("verificar", help="confere o rascunho e os arquivos locais")
    check.add_argument("arquivo", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "preparar":
            if not re.fullmatch(r"[0-9]+", args.artigo):
                raise ValueError("O numero do artigo deve conter apenas numeros.")
            matches = sorted((ROOT / "docs" / "articles").glob(f"*_article_{args.artigo}.html"))
            if len(matches) != 1:
                raise ValueError("Artigo nao encontrado ou numero duplicado.")
            message = args.texto.read_text(encoding="utf-8") if args.texto else None
            draft = prepare(matches[0], args.pagina, args.quando, message)
            print(json.dumps(draft, ensure_ascii=False, indent=2))
        else:
            draft = json.loads(args.arquivo.read_text(encoding="utf-8"))
            verify(draft)
            print("Rascunho consistente; ainda nao aprovado nem publicado. "
                  "Previa no Facebook e site publicado nao foram conferidos.")
    except (ValueError, OSError, UnicodeError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
