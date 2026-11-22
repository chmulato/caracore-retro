"""Revisa e publica uma chamada imediata de um artigo do Retro no Facebook."""
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

PAGE_ID = "1657316127663973"
MAX_APPROVAL_AGE = timedelta(minutes=15)
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com"}


def article_number(env: dict[str, str]) -> str:
    value = env.get("ARTICLE_NUMBER", "")
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise facebook_campaign.CampaignError("Informe o numero do artigo, sem zeros iniciais.")
    return value


def article_message(env: dict[str, str]) -> str | None:
    message = env.get("FACEBOOK_MESSAGE", "")
    if message and not message.strip():
        raise facebook_campaign.CampaignError("A chamada nao pode conter apenas espacos.")
    return message or None


def build_draft(when: str, number: str, message: str | None,
                root: Path = facebook_drafts.ROOT) -> dict:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", when):
        raise facebook_campaign.CampaignError("Horario da revisao invalido.")
    matches = [
        path for path in (root / "docs" / "articles").glob("*_article_*.html")
        if (match := facebook_drafts.ARTICLE_NAME.fullmatch(path.name))
        and str(int(match.group(4))) == number
    ]
    if len(matches) != 1:
        raise facebook_campaign.CampaignError(f"Artigo {number} nao encontrado ou numero duplicado.")
    try:
        draft = facebook_drafts.prepare(matches[0], PAGE_ID, when, message, root, immediate=True)
        facebook_drafts.verify(draft, root)
    except ValueError as error:
        raise facebook_campaign.CampaignError(f"Rascunho do artigo {number} invalido.") from error
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
    number = facebook_drafts.ARTICLE_NAME.fullmatch(Path(content["artigo"]).name).group(4)
    return (
        "## Revisao de publicacao imediata: Facebook\n\n"
        f"**Pagina:** Cara Core Informatica (`{PAGE_ID}`)  \n"
        f"**Artigo:** {int(number)}  \n"
        f"**Modo:** publicacao imediata, exclusivamente no Facebook  \n"
        f"**Link:** {content['link']}  \n"
        f"**Imagem da previa:** {content['imagem_url']}  \n"
        f"**SHA-256 da imagem:** `{content['imagem_sha256']}`  \n"
        f"**SHA-256 do artigo:** `{content['artigo_sha256']}`  \n"
        f"**SHA-256 da chamada:** `{digest}`\n\n"
        f"### Chamada\n\n<pre>{html.escape(content['mensagem'])}</pre>\n\n"
        "A publicacao sera enviada uma unica vez depois da aprovacao do ambiente protegido `facebook`.\n\n"
        "Na tela **Review pending deployments**: escolha o ambiente `facebook`, **apague** o texto "
        "que ja estiver escrito no campo de comentario e cole a linha inteira abaixo. Qualquer outro "
        "texto, inclusive um ok sem o codigo, e recusado antes de qualquer envio.\n\n"
        f"```\nAPROVO {digest}\n```\n\n"
        f"Validade: ate `{expiry(content)}` (hora de Brasilia). Depois disso, gere uma nova execucao.\n"
    )


def expiry(content: dict) -> str:
    prepared = facebook_drafts.local_time(content["data_hora_local"])
    return (prepared + MAX_APPROVAL_AGE).strftime("%Y-%m-%d %H:%M")


def verify_not_already_published(graph, article_url: str, number: str) -> None:
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
                f"O artigo {number} ja aparece nos posts recentes do Facebook."
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
                    f"O artigo {number} ja aparece nos posts recentes do Facebook."
                )


def preview(env: dict[str, str], root: Path = facebook_drafts.ROOT) -> int:
    number = article_number(env)
    message = article_message(env)
    validate_dispatch(env, root)
    now = datetime.now(facebook_drafts.ZONE).replace(second=0, microsecond=0)
    when = now.strftime("%Y-%m-%dT%H:%M")
    draft = build_draft(when, number, message, root)
    facebook_campaign.verify_published(draft)
    summary, output = env.get("GITHUB_STEP_SUMMARY"), env.get("GITHUB_OUTPUT")
    if not summary or not output:
        raise facebook_campaign.CampaignError("A revisao precisa ser apresentada no GitHub Actions.")
    with open(summary, "a", encoding="utf-8") as file:
        file.write(review_summary(draft))
    with open(output, "a", encoding="utf-8") as file:
        file.write(f"digest={draft['sha256_conteudo']}\nwhen={when}\n")
    digest = draft["sha256_conteudo"]
    print("Previa conferida no blog publicado; nada foi enviado a Meta.")
    print("Para aprovar, abra a execucao, clique em Review pending deployments, escolha o ambiente")
    print("facebook, apague o texto do campo de comentario e cole exatamente esta linha:")
    print(f"APROVO {digest}")
    print(f"Validade da aprovacao: ate {expiry(draft['conteudo'])} (hora de Brasilia).")
    print("Passado o prazo ou alterado o artigo, gere uma nova execucao; o digest muda a cada minuto.")
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
    number = article_number(env)
    match = facebook_drafts.ARTICLE_NAME.fullmatch(Path(content["artigo"]).name)
    if (approved_digest != digest or content.get("modo_publicacao") != "imediata"
            or content.get("rede") != "facebook-pagina" or content.get("pagina_id") != PAGE_ID
            or not match or str(int(match.group(4))) != number):
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
    facebook_campaign.verify_history(PAGE_ID, number, root)
    graph.check_page(PAGE_ID)
    verify_not_already_published(graph, content["link"], number)
    ref, reservation_sha = facebook_github.reserve(
        api, PAGE_ID, number, digest, run_id, sha,
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

        number = article_number(env)
        draft = build_draft(env.get("PUBLISH_AT", ""), number, article_message(env))
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
