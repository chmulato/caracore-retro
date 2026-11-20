"""Prepara a revisao individual e agenda uma campanha aprovada no Facebook."""
from __future__ import annotations

import hashlib
import html
import http.client
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from tools import facebook_drafts, facebook_github

REPOSITORY = "chmulato/caracore-retro"
ENVIRONMENT = "facebook"
API_VERSION = "v27.0"
MAX_SITE_BYTES = 20 * 1024 * 1024


class CampaignError(RuntimeError):
    pass


def draft_from_inputs(env: dict[str, str], root: Path = facebook_drafts.ROOT) -> dict:
    article_number = env.get("ARTICLE_NUMBER", "")
    page_id = env.get("FACEBOOK_PAGE_ID", "")
    if not re.fullmatch(r"[1-9][0-9]*", article_number):
        raise CampaignError("Informe o numero do artigo, sem zeros iniciais.")
    if not re.fullmatch(r"[1-9][0-9]*", page_id):
        raise CampaignError("Informe o identificador numerico da pagina, sem zeros iniciais.")
    if article_number == "147":
        raise CampaignError("Artigo 147 bloqueado: ja publicado no Facebook.")
    matches = []
    for path in (root / "docs" / "articles").glob("*_article_*.html"):
        match = facebook_drafts.ARTICLE_NAME.fullmatch(path.name)
        if match and str(int(match.group(4))) == article_number:
            matches.append(path)
    if len(matches) != 1:
        raise CampaignError("Artigo nao encontrado ou numero duplicado.")
    message = env.get("FACEBOOK_MESSAGE", "")
    if message and not message.strip():
        raise CampaignError("A chamada nao pode conter apenas espacos.")
    return facebook_drafts.prepare(matches[0], page_id, env.get("PUBLISH_AT", ""), message or None, root)


def site_bytes(url: str) -> bytes:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "retro.caracore.com.br"
            or not parts.path.startswith("/articles/") or parts.query or parts.fragment):
        raise CampaignError("Endereco publicado invalido.")
    connection = http.client.HTTPSConnection("retro.caracore.com.br", timeout=20)
    try:
        connection.request("GET", parts.path, headers={"Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200:
            raise CampaignError("Nao foi possivel conferir o conteudo publicado do blog.")
        data = response.read(MAX_SITE_BYTES + 1)
        if len(data) > MAX_SITE_BYTES:
            raise CampaignError("Conteudo publicado excede o limite de verificacao.")
        return data
    except (OSError, http.client.HTTPException) as error:
        raise CampaignError("Falha ao conferir o conteudo publicado do blog.") from error
    finally:
        connection.close()


def verify_published(draft: dict, fetch=site_bytes) -> None:
    content = draft["conteudo"]
    for url_key, digest_key in (("link", "artigo_sha256"), ("imagem_url", "imagem_sha256")):
        if hashlib.sha256(fetch(content[url_key])).hexdigest() != content[digest_key]:
            raise CampaignError("O artigo ou a imagem no blog publicado diverge do rascunho.")


def review_summary(draft: dict) -> str:
    content = draft["conteudo"]
    digest = draft["sha256_conteudo"]
    text = html.escape(content["mensagem"])
    title = html.escape(content["titulo_previa"])
    description = html.escape(content["descricao_previa"])
    return (
        "## Revisão individual: Facebook\n\n"
        f"**Página:** {content['pagina_id']}  \n"
        f"**Artigo:** {content['artigo']}  \n"
        f"**Horário:** {content['data_hora_local']} ({content['fuso']})  \n"
        f"**UTC:** {content['data_hora_utc']}  \n"
        f"**Link:** {content['link']}  \n"
        f"**Título da prévia:** <pre>{title}</pre>\n"
        f"**Descrição da prévia:** <pre>{description}</pre>\n"
        f"**Imagem:** {content['imagem_url']}  \n"
        f"**SHA-256 da imagem:** `{content['imagem_sha256']}`  \n"
        f"**SHA-256 do artigo:** `{content['artigo_sha256']}`  \n"
        f"**SHA-256 da campanha:** `{digest}`\n\n"
        f"![Imagem informada pelo artigo]({content['imagem_url']})\n\n"
        f"### Chamada\n\n<pre>{text}</pre>\n\n"
        "A imagem acima é a do blog; confira também a prévia real do link no Facebook antes de aprovar, "
        "pois ela pode estar em cache. Se qualquer dado mudar, inicie uma nova revisão.\n\n"
        f"Para aprovar esta campanha, use no GitHub o comentário exato: `APROVO {digest}`\n"
    )


def validate_run(env: dict[str, str], root: Path) -> tuple[str, str, int]:
    if (env.get("GITHUB_ACTIONS") != "true" or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_REPOSITORY") != REPOSITORY
            or env.get("GITHUB_REF") != "refs/heads/master"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise CampaignError("Esta campanha exige uma nova execucao manual na master oficial.")
    run_id, sha, reviewer = (env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_SHA", ""),
                             env.get("FACEBOOK_REVIEWER_ID", ""))
    if (not re.fullmatch(r"[1-9][0-9]*", run_id)
            or not re.fullmatch(r"[0-9a-f]{40}", sha)
            or not re.fullmatch(r"[1-9][0-9]*", reviewer)):
        raise CampaignError("Dados da execucao ou do revisor estao ausentes ou invalidos.")
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                            text=True, check=False)
    if result.returncode != 0 or result.stdout.strip() != sha:
        raise CampaignError("O codigo da execucao diverge do commit apresentado para revisao.")
    return run_id, sha, int(reviewer)


def verify_history(page_id: str, article_number: str, root: Path) -> None:
    path = root / "facebook_publication_history.json"
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CampaignError("Historico da pagina ainda nao conferido; envio bloqueado.") from error
    if (not isinstance(history, dict) or history.get("pagina_id") != page_id
            or history.get("conferido") is not True
            or not isinstance(history.get("publicacoes"), dict)):
        raise CampaignError("Historico da pagina ainda nao conferido; envio bloqueado.")
    publications = history["publicacoes"]
    if ("147" not in publications or any(
            not isinstance(number, str) or not re.fullmatch(r"[1-9][0-9]*", number)
            or not isinstance(post_id, str) or not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", post_id)
            for number, post_id in publications.items())):
        raise CampaignError("Historico da pagina incompleto ou invalido; envio bloqueado.")
    if article_number in publications:
        raise CampaignError("Artigo ja consta no historico da pagina; envio bloqueado.")


def validate_schedule(draft: dict, now: datetime) -> int:
    scheduled = datetime.strptime(draft["conteudo"]["data_hora_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        raise CampaignError("Relogio da execucao sem fuso horario.")
    remaining = scheduled - now.astimezone(timezone.utc)
    if not timedelta(minutes=15) <= remaining <= timedelta(days=29, hours=23, minutes=55):
        raise CampaignError("O horario deve estar entre 15 minutos e menos de 30 dias no futuro.")
    return int(scheduled.timestamp())


class FacebookAPI:
    def __init__(self, token: str) -> None:
        if not token or not token.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in token):
            raise CampaignError("Credencial da pagina ausente ou invalida.")
        self.token = token

    def request(self, method: str, path: str, body: dict[str, str] | None = None) -> tuple[int, object]:
        connection = http.client.HTTPSConnection("graph.facebook.com", timeout=30)
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        payload = None
        if body is not None:
            payload = urlencode(body).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise CampaignError("Resposta da Meta excedeu o limite esperado.")
            try:
                result = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise CampaignError("Resposta da Meta nao pode ser confirmada.") from error
            return response.status, result
        except (OSError, http.client.HTTPException, ValueError) as error:
            raise CampaignError("Nao foi possivel confirmar a resposta da Meta.") from error
        finally:
            connection.close()

    def check_page(self, page_id: str) -> None:
        status, data = self.request("GET", f"/{API_VERSION}/me?fields=id")
        if status != 200 or not isinstance(data, dict) or data.get("id") != page_id:
            raise CampaignError("A credencial nao confirmou o acesso a pagina escolhida.")

    def diagnose_page(self, page_id: str) -> dict:
        if not re.fullmatch(r"[1-9][0-9]*", page_id):
            raise CampaignError("Identificador da pagina invalido.")
        status, data = self.request("GET", f"/{API_VERSION}/me?fields=id")
        data = data if isinstance(data, dict) else {}
        error = data.get("error")
        error = error if isinstance(error, dict) else {}
        code, subcode = error.get("code"), error.get("error_subcode")
        identity_present = isinstance(data.get("id"), str) and bool(re.fullmatch(r"[1-9][0-9]*", data["id"]))
        return {
            "http_status": status,
            "page_matches": status == 200 and identity_present and data["id"] == page_id,
            "error_code": code if type(code) is int and 0 <= code <= 2147483647 else None,
            "error_subcode": subcode if type(subcode) is int and 0 <= subcode <= 2147483647 else None,
        }

    def schedule(self, content: dict, timestamp: int) -> str:
        status, data = self.request("POST", f"/{API_VERSION}/{content['pagina_id']}/feed", {
            "message": content["mensagem"], "link": content["link"],
            "published": "false", "scheduled_publish_time": str(timestamp),
        })
        remote_id = data.get("id") if isinstance(data, dict) else None
        if status not in (200, 201) or not isinstance(remote_id, str) or not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", remote_id):
            raise CampaignError("A Meta nao confirmou o identificador da publicacao.")
        return remote_id


def publish(draft: dict, approved_digest: str, env: dict[str, str], api, graph,
            root: Path = facebook_drafts.ROOT, fetch=site_bytes,
            now: datetime | None = None) -> str:
    facebook_drafts.verify(draft, root)
    digest = draft["sha256_conteudo"]
    if approved_digest != digest:
        raise CampaignError("O conteudo diverge da versao apresentada para aprovacao.")
    run_id, sha, reviewer_id = validate_run(env, root)
    facebook_github.check_approval(api, run_id, ENVIRONMENT, reviewer_id, digest)
    validate_schedule(draft, now or datetime.now(timezone.utc))
    verify_published(draft, fetch)
    content = draft["conteudo"]
    article_match = facebook_drafts.ARTICLE_NAME.fullmatch(Path(content["artigo"]).name)
    if not article_match:
        raise CampaignError("Nome do artigo invalido.")
    article_number = str(int(article_match.group(4)))
    verify_history(content["pagina_id"], article_number, root)
    graph.check_page(content["pagina_id"])
    ref, reservation_sha = facebook_github.reserve(api, content["pagina_id"], article_number,
                                                    digest, run_id, sha)
    try:
        timestamp = validate_schedule(draft, now or datetime.now(timezone.utc))
    except CampaignError as error:
        raise CampaignError("Horario fora do intervalo. Nenhum envio foi feito; a reserva permanece bloqueada.") from error
    try:
        remote_id = graph.schedule(content, timestamp)
    except Exception as error:
        raise CampaignError("Resultado do envio incerto. A reserva permanece bloqueada; confira a pagina antes de qualquer nova tentativa.") from error
    try:
        facebook_github.record_received(api, ref, reservation_sha, remote_id)
    except Exception as error:
        raise CampaignError(f"A Meta informou o ID {remote_id}, mas o registro falhou. A reserva permanece bloqueada; confira antes de qualquer nova tentativa.") from error
    return remote_id


def main() -> int:
    env = dict(os.environ)
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in ("preview", "agendar", "diagnosticar"):
            raise CampaignError("Use preview, agendar ou diagnosticar na esteira do GitHub.")
        if sys.argv[1] == "diagnosticar":
            validate_run(env, facebook_drafts.ROOT)
            result = FacebookAPI(env.get("FACEBOOK_PAGE_TOKEN", "")).diagnose_page(env.get("FACEBOOK_PAGE_ID", ""))
            report = json.dumps(result, ensure_ascii=True, sort_keys=True)
            print("Diagnostico somente leitura; nenhum agendamento ou publicacao foi solicitado.")
            print(report)
            summary = env.get("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary, "a", encoding="utf-8") as file:
                    file.write("## Diagnostico Facebook: somente leitura\n\n```json\n" + report + "\n```\n")
            return 0 if result["page_matches"] else 1
        draft = draft_from_inputs(env)
        facebook_drafts.verify(draft)
        if sys.argv[1] == "preview":
            verify_published(draft)
            summary, output = env.get("GITHUB_STEP_SUMMARY"), env.get("GITHUB_OUTPUT")
            if not summary or not output:
                raise CampaignError("A revisao deve ser apresentada por uma execucao do GitHub.")
            with open(summary, "a", encoding="utf-8") as file:
                file.write(review_summary(draft))
            with open(output, "a", encoding="utf-8") as file:
                file.write(f"digest={draft['sha256_conteudo']}\n")
            print("Campanha preparada para revisao individual; nada foi enviado a Meta.")
        else:
            github_token = env.get("GITHUB_TOKEN", "")
            page_token = env.get("FACEBOOK_PAGE_TOKEN", "")
            if not github_token or not page_token:
                raise CampaignError("Credenciais de GitHub ou da pagina ausentes.")
            api = facebook_github.GithubAPI(REPOSITORY, github_token)
            remote_id = publish(draft, env.get("APPROVED_DIGEST", ""), env, api, FacebookAPI(page_token))
            print(f"A Meta retornou o ID {remote_id}. Confirme horario e previa na pagina; a publicacao ainda nao foi comprovada.")
    except (CampaignError, facebook_github.GithubError, ValueError, OSError, UnicodeError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
