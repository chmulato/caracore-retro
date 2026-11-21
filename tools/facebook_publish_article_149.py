"""Revisa e publica uma unica chamada imediata do artigo 149 no Facebook."""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from tools import facebook_campaign, facebook_drafts, facebook_github

ARTICLE_NUMBER = "149"
PAGE_ID = "1657316127663973"
MESSAGE = (
    "Feito, empacotado e instalado são três estados diferentes. Entenda como conferir "
    "o que um programa realmente faz na versão que você baixa hoje para a loja.\n\n"
    "E na sua rotina, esse assunto também faz diferença?\n\n"
    "Leia ‘O que tem dentro da caixa: como saber o que um sistema faz no dia em que você instala’ "
    "no blog Retrô:\n"
    "https://retro.caracore.com.br/articles/2027_09_15_article_149.html"
)
ARTICLE_PATH = "docs/articles/2027_09_15_article_149.html"
MAX_APPROVAL_AGE = timedelta(minutes=15)
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com"}


def build_draft(when: str, root: Path = facebook_drafts.ROOT) -> dict:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", when):
        raise facebook_campaign.CampaignError("Horario da revisao invalido.")
    matches = [
        path for path in (root / "docs" / "articles").glob("*_article_*.html")
        if (match := facebook_drafts.ARTICLE_NAME.fullmatch(path.name))
        and str(int(match.group(4))) == ARTICLE_NUMBER
    ]
    if len(matches) != 1:
        raise facebook_campaign.CampaignError("Artigo 149 nao encontrado ou numero duplicado.")
    try:
        draft = facebook_drafts.prepare(
            matches[0], PAGE_ID, when, MESSAGE, root, immediate=True,
        )
        facebook_drafts.verify(draft, root)
    except ValueError as error:
        raise facebook_campaign.CampaignError("Rascunho do artigo 149 invalido.") from error
    return draft


def validate_dispatch(env: dict[str, str], root: Path) -> tuple[str, str]:
    run_id, sha = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_SHA", "")
    if (env.get("GITHUB_ACTIONS") != "true"
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_REPOSITORY") != facebook_campaign.REPOSITORY
            or env.get("GITHUB_REF") != "refs/heads/master"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or not re.fullmatch(r"[1-9][0-9]*", run_id)
            or not re.fullmatch(r"[0-9a-f]{40}", sha)):
        raise facebook_campaign.CampaignError("Esta publicacao exige uma nova execucao na master oficial.")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0 or result.stdout.strip() != sha:
        raise facebook_campaign.CampaignError("O codigo diverge do commit apresentado para revisao.")
    return run_id, sha


def review_summary(draft: dict) -> str:
    content = draft["conteudo"]
    digest = draft["sha256_conteudo"]
    return (
        "## Revisao de publicacao imediata: Facebook\n\n"
        f"**Pagina:** Cara Core Informatica (`{PAGE_ID}`)  \n"
        f"**Artigo:** {ARTICLE_NUMBER}  \n"
        f"**Modo:** publicacao imediata, exclusivamente no Facebook  \n"
        f"**Link:** {content['link']}  \n"
        f"**Imagem da previa:** {content['imagem_url']}  \n"
        f"**SHA-256 da imagem:** `{content['imagem_sha256']}`  \n"
        f"**SHA-256 do artigo:** `{content['artigo_sha256']}`  \n"
        f"**SHA-256 da chamada:** `{digest}`\n\n"
        f"### Chamada\n\n<pre>{html.escape(content['mensagem'])}</pre>\n\n"
        "A publicacao sera enviada uma unica vez depois da aprovacao do ambiente protegido `facebook`.\n"
        f"Use o comentario exato `APROVO {digest}` nessa aprovacao.\n"
    )


def verify_not_already_published(graph, article_url: str) -> None:
    try:
        status, data = graph.request(
            "GET",
            f"/{facebook_campaign.API_VERSION}/{PAGE_ID}/published_posts"
            "?fields=id,message,permalink_url,attachments%7Burl%7D&limit=100",
        )
    except facebook_campaign.CampaignError as error:
        raise facebook_campaign.CampaignError(
            "Nao foi possivel consultar os posts recentes; envio bloqueado."
        ) from error
    records = data.get("data") if isinstance(data, dict) else None
    if status != 200 or not isinstance(records, list):
        raise facebook_campaign.CampaignError(
            "Nao foi possivel consultar os posts recentes; envio bloqueado."
        )
    for record in records:
        if not isinstance(record, dict):
            raise facebook_campaign.CampaignError(
                "A lista de posts recentes e invalida; envio bloqueado."
            )
        message = record.get("message")
        if isinstance(message, str) and article_url in message:
            raise facebook_campaign.CampaignError(
                "O artigo 149 ja aparece nos posts recentes do Facebook."
            )
        attachments = record.get("attachments")
        attachment_items = attachments.get("data") if isinstance(attachments, dict) else None
        if attachment_items is not None and not isinstance(attachment_items, list):
            raise facebook_campaign.CampaignError(
                "Os anexos dos posts recentes sao invalidos; envio bloqueado."
            )
        for attachment in attachment_items or []:
            if not isinstance(attachment, dict):
                raise facebook_campaign.CampaignError(
                    "Os anexos dos posts recentes sao invalidos; envio bloqueado."
                )
            if attachment.get("url") == article_url:
                raise facebook_campaign.CampaignError(
                    "O artigo 149 ja aparece nos posts recentes do Facebook."
                )


def preview(env: dict[str, str], root: Path = facebook_drafts.ROOT) -> int:
    validate_dispatch(env, root)
    now = datetime.now(facebook_drafts.ZONE).replace(second=0, microsecond=0)
    when = now.strftime("%Y-%m-%dT%H:%M")
    draft = build_draft(when, root)
    facebook_campaign.verify_published(draft)
    summary, output = env.get("GITHUB_STEP_SUMMARY"), env.get("GITHUB_OUTPUT")
    if not summary or not output:
        raise facebook_campaign.CampaignError("A revisao precisa ser apresentada no GitHub Actions.")
    with open(summary, "a", encoding="utf-8") as file:
        file.write(review_summary(draft))
    with open(output, "a", encoding="utf-8") as file:
        file.write(f"digest={draft['sha256_conteudo']}\nwhen={when}\n")
    print("Previa conferida; nada foi enviado a Meta.")
    return 0


def publish(
    draft: dict,
    approved_digest: str,
    env: dict[str, str],
    api,
    graph,
    root: Path = facebook_drafts.ROOT,
    now: datetime | None = None,
) -> tuple[str, str]:
    facebook_drafts.verify(draft, root)
    content = draft["conteudo"]
    digest = draft["sha256_conteudo"]
    if (approved_digest != digest or content.get("modo_publicacao") != "imediata"
            or content.get("rede") != "facebook-pagina" or content.get("pagina_id") != PAGE_ID
            or content.get("artigo") != ARTICLE_PATH
            or content.get("mensagem") != MESSAGE):
        raise facebook_campaign.CampaignError("A campanha diverge da publicacao autorizada.")

    run_id, sha, reviewer_id = facebook_campaign.validate_run(env, root)
    if reviewer_id is None:
        raise facebook_campaign.CampaignError("Revisor ausente na aprovacao.")
    facebook_github.check_approval(api, run_id, facebook_campaign.ENVIRONMENT, reviewer_id, digest)

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise facebook_campaign.CampaignError("Relogio da execucao sem fuso horario.")
    prepared = facebook_drafts.local_time(content["data_hora_local"]).astimezone(timezone.utc)
    age = current_time.astimezone(timezone.utc) - prepared
    if age < timedelta(seconds=-120) or age > MAX_APPROVAL_AGE:
        raise facebook_campaign.CampaignError(
            "A revisao expirou; gere uma nova antes de qualquer publicacao."
        )

    facebook_campaign.verify_published(draft)
    facebook_campaign.verify_history(PAGE_ID, ARTICLE_NUMBER, root)
    graph.check_page(PAGE_ID)
    verify_not_already_published(graph, content["link"])
    ref, reservation_sha = facebook_github.reserve(
        api, PAGE_ID, ARTICLE_NUMBER, digest, run_id, sha,
    )
    try:
        status, data = graph.request(
            "POST",
            f"/{facebook_campaign.API_VERSION}/{PAGE_ID}/feed",
            {"message": content["mensagem"], "link": content["link"], "published": "true"},
        )
    except facebook_campaign.CampaignError as error:
        raise facebook_campaign.CampaignError(
            "Resultado do envio incerto; a reserva bloqueia repeticoes. Confira a Pagina antes de tentar novamente."
        ) from error
    remote_id = data.get("id") if isinstance(data, dict) else None
    if (status not in (200, 201) or not isinstance(remote_id, str)
            or not re.fullmatch(r"[0-9]+(?:_[0-9]+)*", remote_id)):
        raise facebook_campaign.CampaignError(
            "A Meta nao confirmou o post; a reserva bloqueia repeticoes. Confira a Pagina antes de tentar novamente."
        )
    try:
        facebook_github.record_received(api, ref, reservation_sha, remote_id)
    except facebook_github.GithubError as error:
        raise facebook_campaign.CampaignError(
            f"A Meta aceitou o post ID {remote_id}, mas o registro falhou. A reserva permanece bloqueada."
        ) from error

    try:
        status, data = graph.request(
            "GET", f"/{facebook_campaign.API_VERSION}/{remote_id}?fields=permalink_url",
        )
    except facebook_campaign.CampaignError as error:
        raise facebook_campaign.CampaignError(
            f"Post publicado com ID {remote_id}, mas a Meta nao retornou o permalink."
        ) from error
    permalink = data.get("permalink_url") if isinstance(data, dict) else None
    parts = urlsplit(permalink) if isinstance(permalink, str) else None
    if (status != 200 or parts is None or parts.scheme != "https"
            or parts.netloc not in FACEBOOK_HOSTS or not parts.path):
        raise facebook_campaign.CampaignError(
            f"Post publicado com ID {remote_id}, mas o permalink nao pode ser confirmado."
        )

    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write(f"\n## Publicacao confirmada\n\nID: `{remote_id}`  \nPermalink: {permalink}\n")
    return remote_id, permalink


def main() -> int:
    env = dict(os.environ)
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in ("preview", "publicar"):
            raise facebook_campaign.CampaignError("Use preview ou publicar no workflow dedicado.")
        if sys.argv[1] == "preview":
            return preview(env)

        when = env.get("PUBLISH_AT", "")
        draft = build_draft(when)
        github_token = env.get("GITHUB_TOKEN", "")
        page_token = env.get("FACEBOOK_PAGE_TOKEN", "")
        if not github_token or not page_token:
            raise facebook_campaign.CampaignError("Credenciais de GitHub ou da Pagina ausentes.")
        api = facebook_github.GithubAPI(facebook_campaign.REPOSITORY, github_token)
        remote_id, permalink = publish(
            draft, env.get("APPROVED_DIGEST", ""), env, api,
            facebook_campaign.FacebookAPI(page_token),
        )
        print(f"Post publicado no Facebook: {remote_id}\n{permalink}")
    except (facebook_campaign.CampaignError, facebook_github.GithubError,
            ValueError, OSError, UnicodeError, KeyError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
