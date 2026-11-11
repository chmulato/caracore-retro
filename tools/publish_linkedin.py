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
COMMENTARY_LIMIT = 3000
ARTICLE_RE = re.compile(r"^docs/articles/\d{4}_\d{2}_\d{2}_article_\d+\.html$")
TAG_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)


@dataclass
class Share:
    title: str
    description: str
    url: str
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


def build_commentary(title: str, description: str, url: str, hashtags: list[str]) -> str:
    tail = " ".join(hashtags)
    body = "\n".join(
        [title, "", description, "", url] + ([""] if tail else []) + ([tail] if tail else [])
    )
    if len(body) <= COMMENTARY_LIMIT:
        return body
    fixed = len(title) + len(url) + len(tail) + 6
    budget = max(80, COMMENTARY_LIMIT - fixed)
    cut = description[:budget].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return build_commentary(title, cut, url, hashtags)


def parse_article(path: Path) -> Share:
    source = path.read_text(encoding="utf-8")
    title = meta_content(source, "og:title", "property")
    description = meta_content(source, "og:description", "property")
    url = meta_content(source, "og:url", "property")
    if not description:
        description = meta_content(source, "description", "name")
    if not url:
        url = f"{SITE}/articles/{path.name}"
    keywords = meta_content(source, "keywords", "name")
    hashtags = hashtags_from_keywords(keywords)
    commentary = build_commentary(title, description, url, hashtags)
    return Share(title=title, description=description, url=url,
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


def post_article(share: Share, token: str, author_urn: str) -> tuple[bool, str]:
    payload = {
        "author": author_urn,
        "commentary": share.commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "article": {
                "source": share.url,
                "title": share.title,
                "description": share.description,
            }
        },
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
        print(f"\n{len(paths)} postagem(ns) simulada(s).")
        return 0

    failures = 0
    for path in paths:
        share = parse_article(path)
        ok, detail = post_article(share, token, author_urn)
        status = "PUBLICADO" if ok else "FALHOU"
        print(f"{status}: {share.url} {detail}".rstrip())
        if not ok:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
