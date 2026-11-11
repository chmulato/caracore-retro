"""Publica os artigos novos do blog Retrô no LinkedIn.

Roda na esteira no job publish-linkedin de .github/workflows/deploy.yml, depois
do deploy. Detecta os artigos adicionados no push com
`git diff --diff-filter=A HEAD^ HEAD` e posta um "article share" por artigo
na API REST do LinkedIn (escopo w_member_social).

Credenciais por variável de ambiente (secrets do repositório):
  LINKEDIN_ACCESS_TOKEN — token OAuth 2.0 com escopo w_member_social
  LINKEDIN_AUTHOR_URN   — urn:li:person:<id> (ou urn:li:organization:<id>)

Sem credenciais roda em DRY-RUN: mostra exatamente o que seria postado e sai 0.
É assim que a esteira fica verde até os secrets serem cadastrados no GitHub.

Modos:
  (padrão)     artigos adicionados em HEAD^..HEAD (uso na esteira)
  --latest     artigo mais recente do acervo (uso manual)
  --article N  artigo número N do acervo (uso manual)
  --dry-run    força o dry-run mesmo com credenciais
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTICLES = DOCS / "articles"
SITE = "https://retro.caracore.com.br"
API = "https://api.linkedin.com/rest/posts"
IMAGES_API = "https://api.linkedin.com/rest/images?action=initializeUpload"
COMMENTARY_LIMIT = 3000
ARTICLE_RE = re.compile(r"^docs/articles/\d{4}_\d{2}_\d{2}_article_\d+\.html$")
TAG_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)
LINKEDIN_SPECIAL_CHARS = re.compile(r"([\\*_~()\[\]<>{}@|])")


@dataclass
class Share:
    title: str
    description: str
    url: str
    image_url: str
    hashtags: list[str]
    commentary: str


def meta_content(source: str, key: str, attribute: str) -> str:
    for tag in TAG_RE.findall(source):
        name = re.search(rf'{attribute}="([^"]+)"', tag)
        content = re.search(r'content="([^"]*)"', tag)
        if name and content and name.group(1) == key:
            return content.group(1).strip()
    return ""


def hashtags_from_keywords(keywords: str, limit: int = 3) -> list[str]:
    result = []
    for tag in keywords.split(","):
        words = re.findall(
            r"[A-Za-z0-9]+",
            unicodedata.normalize("NFKD", tag).encode("ascii", "ignore").decode(),
        )
        if not words:
            continue
        marker = "#" + "".join(word.capitalize() for word in words)
        if marker not in result:
            result.append(marker)
        if len(result) >= limit:
            break
    return result


def escape_linkedin_text(text: str) -> str:
    """Escapa caracteres reservados do 'Little Text Format' do LinkedIn.

    Sem isso, sequencias como par de "_" sao interpretadas como marcacao
    (ex.: italico) e o texto sai corrompido.
    """
    return LINKEDIN_SPECIAL_CHARS.sub(r"\\\1", text)


def build_commentary(title: str, description: str, hashtags: list[str]) -> str:
    """Monta o comentario do post.

    A URL nao entra como texto solto: o card de artigo (content.article.source)
    ja exibe o link, e URLs com "_" no commentary sao corrompidas pelo parser
    de marcacao do LinkedIn.
    """
    safe_title = escape_linkedin_text(title)
    safe_tail = " ".join(escape_linkedin_text(tag) for tag in hashtags)

    def assemble(safe_description: str) -> str:
        return "\n".join(
            [safe_title, "", safe_description]
            + ([""] if safe_tail else [])
            + ([safe_tail] if safe_tail else [])
        )

    safe_description = escape_linkedin_text(description)
    body = assemble(safe_description)
    if len(body) <= COMMENTARY_LIMIT:
        return body
    fixed = len(safe_title) + len(safe_tail) + 5
    budget = max(80, COMMENTARY_LIMIT - fixed)
    cut = safe_description[:budget].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return assemble(cut)


def parse_article(path: Path) -> Share:
    source = path.read_text(encoding="utf-8")
    title = meta_content(source, "og:title", "property")
    description = meta_content(source, "og:description", "property")
    url = meta_content(source, "og:url", "property")
    if not description:
        description = meta_content(source, "description", "name")
    if not url:
        url = f"{SITE}/articles/{path.name}"
    image_url = meta_content(source, "og:image", "property")
    keywords = meta_content(source, "keywords", "name")
    hashtags = hashtags_from_keywords(keywords)
    commentary = build_commentary(title, description, hashtags)
    return Share(title=title, description=description, url=url, image_url=image_url,
                 hashtags=hashtags, commentary=commentary)


def added_articles() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "diff", "--diff-filter=A", "--name-only", "HEAD^", "HEAD",
             "--", "docs/articles/"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = sorted(line.strip() for line in out.splitlines() if line.strip())
    return [ROOT / f for f in files if ARTICLE_RE.match(f)]


def latest_article() -> Path | None:
    candidates = sorted(ARTICLES.glob("*_article_*.html"))
    return candidates[-1] if candidates else None


def upload_thumbnail(image_url: str, token: str, author_urn: str) -> tuple[str | None, str]:
    """Sobe a imagem do artigo para o LinkedIn e devolve o image URN.

    O LinkedIn nao faz scraping de URL: o thumbnail do card de artigo precisa
    ser um urn:li:image: obtido pelo fluxo em duas etapas da Images API
    (initializeUpload -> PUT dos bytes). Falha devolve (None, motivo) — o post
    segue sem thumbnail.
    """
    try:
        with urllib.request.urlopen(image_url, timeout=30) as response:
            image_bytes = response.read()
    except (urllib.error.URLError, OSError) as error:
        return None, f"download da imagem falhou: {error}"

    init_request = urllib.request.Request(
        IMAGES_API,
        data=json.dumps(
            {"initializeUploadRequest": {"owner": author_urn}}
        ).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202601",
        },
    )
    try:
        with urllib.request.urlopen(init_request, timeout=30) as response:
            init = json.loads(response.read().decode("utf-8"))["value"]
        upload_request = urllib.request.Request(
            init["uploadUrl"],
            data=image_bytes,
            method="PUT",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            },
        )
        with urllib.request.urlopen(upload_request, timeout=60):
            pass
        return init["image"], ""
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:200]
        return None, f"upload da imagem falhou: HTTP {error.code}: {detail}"
    except urllib.error.URLError as error:
        return None, f"upload da imagem falhou: {error.reason}"


def post_article(share: Share, token: str, author_urn: str,
                 image_urn: str | None = None) -> tuple[bool, str]:
    article = {
        "source": share.url,
        "title": share.title,
        "description": share.description,
    }
    if image_urn:
        article["thumbnail"] = image_urn
    payload = {
        "author": author_urn,
        "commentary": share.commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {"article": article},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202601",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            post_id = response.headers.get("x-restli-id", "")
            return True, post_id
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            return False, (
                f"HTTP {error.code}: token inválido/expirado ou sem escopo "
                "w_member_social. Tokens de membro expiram em 60 dias; "
                "renove no LinkedIn Developer Portal."
            )
        detail = error.read().decode("utf-8", "replace")[:200]
        return False, f"HTTP {error.code}: {detail}"
    except urllib.error.URLError as error:
        return False, f"falha de rede: {error.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latest", action="store_true",
                        help="publica o artigo mais recente em vez do diff do push")
    parser.add_argument("--article", metavar="N",
                        help="publica o artigo número N em vez do diff do push")
    parser.add_argument("--dry-run", action="store_true",
                        help="força o dry-run mesmo com credenciais")
    args = parser.parse_args()

    if args.article:
        candidates = sorted(ARTICLES.glob(f"*_article_{args.article}.html"))
        paths = candidates[:1]
    elif args.latest:
        article = latest_article()
        paths = [article] if article else []
    else:
        paths = added_articles()

    if not paths:
        print("Nenhum artigo novo detectado; nada a publicar.")
        return 0

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author_urn = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()
    dry_run = args.dry_run or not (token and author_urn)

    if dry_run:
        print("MODO DRY-RUN — cadastre os secrets LINKEDIN_ACCESS_TOKEN e "
              "LINKEDIN_AUTHOR_URN no GitHub para publicar de verdade.")
        for path in paths:
            share = parse_article(path)
            print(f"\n=== {path.name} ===")
            print(share.commentary)
            print(f"[thumbnail] {share.image_url or '(sem og:image)'}")
        print(f"\n{len(paths)} postagem(ns) simulada(s).")
        return 0

    failures = 0
    for path in paths:
        share = parse_article(path)
        image_urn = None
        if share.image_url:
            image_urn, image_detail = upload_thumbnail(share.image_url, token, author_urn)
            if not image_urn:
                print(f"AVISO: {share.url} segue sem thumbnail — {image_detail}")
        ok, detail = post_article(share, token, author_urn, image_urn)
        status = "PUBLICADO" if ok else "FALHOU"
        suffix = " [com thumbnail]" if ok and image_urn else ""
        print(f"{status}{suffix}: {share.url} {detail}".rstrip())
        if not ok:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
