"""Aprovação e reserva durável no GitHub, sem publicar no Facebook."""
from __future__ import annotations

import http.client
import json
import re


class GithubError(RuntimeError):
    """Falha segura na comunicação ou na validação do GitHub."""


_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}\Z")
_DIGITS = re.compile(r"[0-9]+\Z")
_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
_DIGEST = re.compile(r"[0-9a-fA-F]{64}\Z")
_REF = re.compile(r"heads/facebook-reservas/p([0-9]+)/a([0-9]+)\Z")
_REMOTE_ID = re.compile(r"[0-9]+(?:_[0-9]+)*\Z")


def _valid(pattern: re.Pattern, value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _repository(value: object) -> str:
    if not _valid(_REPOSITORY, value) or ".." in value or value.endswith("."):
        raise GithubError("Repositorio invalido.")
    return value


class GithubAPI:
    def __init__(self, repository: str, token: str):
        self.repository = _repository(repository)
        if not isinstance(token, str) or not token or not token.isascii() or any(ord(c) <= 32 or ord(c) == 127 for c in token):
            raise GithubError("Credencial invalida.")
        self._token = token

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, object]:
        if method not in {"GET", "POST", "PATCH"} or not isinstance(path, str) or not path.startswith("/") or path.startswith("//") or any(ord(c) <= 32 or ord(c) == 127 for c in path):
            raise GithubError("Requisicao invalida.")
        if payload is not None and not isinstance(payload, dict):
            raise GithubError("Requisicao invalida.")
        connection = None
        try:
            body = json.dumps(payload, ensure_ascii=True) if payload is not None else None
            connection = http.client.HTTPSConnection("api.github.com", timeout=15)
            connection.request(method, path, body=body, headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self._token,
                "Content-Type": "application/json",
                "User-Agent": "caracore-retro-facebook",
                "X-GitHub-Api-Version": "2022-11-28",
            })
            response = connection.getresponse()
            raw = response.read()
            result = json.loads(raw.decode("utf-8"))
            return response.status, result
        except (OSError, http.client.HTTPException, UnicodeError, ValueError, TypeError, OverflowError):
            raise GithubError("Falha na comunicacao com o GitHub.") from None
        finally:
            if connection is not None:
                connection.close()


def _root(api) -> str:
    return "/repos/" + _repository(getattr(api, "repository", None))


def check_approval(api, run_id: str, environment: str, reviewer_id: int, digest: str) -> None:
    if not _valid(_DIGITS, run_id) or not _valid(_DIGEST, digest) or not isinstance(environment, str) or not environment or not isinstance(reviewer_id, int) or isinstance(reviewer_id, bool) or reviewer_id <= 0:
        raise GithubError("Dados de aprovacao invalidos.")
    status, records = api.request("GET", f"{_root(api)}/actions/runs/{run_id}/approvals")
    if status != 200 or not isinstance(records, list):
        raise GithubError("Aprovacao nao comprovada.")
    matches = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("environments"), list):
            raise GithubError("Aprovacao nao comprovada.")
        environments = record["environments"]
        if any(not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in environments):
            raise GithubError("Aprovacao nao comprovada.")
        if any(item["name"] == environment for item in environments):
            matches.append(record)
    if len(matches) != 1:
        raise GithubError("Aprovacao nao comprovada.")
    record = matches[0]
    user = record.get("user")
    comment = record.get("comment")
    if (record.get("state") != "approved" or not isinstance(user, dict)
            or type(user.get("id")) is not int or user["id"] != reviewer_id
            or not isinstance(comment, str) or comment.strip() != "APROVO " + digest):
        raise GithubError("Aprovacao nao comprovada.")


def _tree(api, sha: str) -> str:
    status, data = api.request("GET", f"{_root(api)}/git/commits/{sha}")
    tree = data.get("tree") if isinstance(data, dict) else None
    tree_sha = tree.get("sha") if isinstance(tree, dict) else None
    if status != 200 or not _valid(_SHA, tree_sha):
        raise GithubError("Commit de origem nao comprovado.")
    return tree_sha


def _commit(api, tree: str, parent: str, message: dict) -> str:
    status, data = api.request("POST", f"{_root(api)}/git/commits", {
        "message": json.dumps(message, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        "tree": tree,
        "parents": [parent],
    })
    sha = data.get("sha") if isinstance(data, dict) else None
    if status != 201 or not _valid(_SHA, sha):
        raise GithubError("Commit nao comprovado.")
    return sha


def _confirmed(data: object, ref: str, sha: str) -> bool:
    if not isinstance(data, dict) or data.get("ref") != "refs/" + ref:
        return False
    obj = data.get("object")
    return isinstance(obj, dict) and obj.get("sha") == sha


def reserve(api, page_id: str, article_number: str, digest: str, run_id: str, base_sha: str) -> tuple[str, str]:
    if (not _valid(_DIGITS, page_id) or not _valid(_DIGITS, article_number)
            or not _valid(_DIGEST, digest) or not _valid(_DIGITS, run_id)
            or not _valid(_SHA, base_sha)):
        raise GithubError("Dados de reserva invalidos.")
    if (len(page_id) > 1 and page_id.startswith("0")) or (len(article_number) > 1 and article_number.startswith("0")):
        raise GithubError("Dados de reserva invalidos.")
    if article_number == "147":
        raise GithubError("Artigo bloqueado.")
    ref = f"heads/facebook-reservas/p{page_id}/a{article_number}"
    tree = _tree(api, base_sha)
    sha = _commit(api, tree, base_sha, {
        "estado": "RESERVADO", "rede": "facebook", "page_id": page_id,
        "article_number": article_number, "digest": digest, "run_id": run_id,
    })
    status, data = api.request("POST", f"{_root(api)}/git/refs", {"ref": "refs/" + ref, "sha": sha})
    if status != 201 or not _confirmed(data, ref, sha):
        raise GithubError("Reserva nao comprovada; nao repetir automaticamente.")
    return ref, sha


def record_received(api, ref: str, reservation_sha: str, remote_id: str) -> None:
    match = _REF.fullmatch(ref) if isinstance(ref, str) else None
    if (not match or (len(match.group(1)) > 1 and match.group(1).startswith("0"))
            or (len(match.group(2)) > 1 and match.group(2).startswith("0"))
            or match.group(2) == "147" or not _valid(_SHA, reservation_sha)
            or not _valid(_REMOTE_ID, remote_id)):
        raise GithubError("Dados de agendamento invalidos.")
    tree = _tree(api, reservation_sha)
    sha = _commit(api, tree, reservation_sha, {"estado": "ID_RECEBIDO", "remote_id": remote_id})
    status, data = api.request("PATCH", f"{_root(api)}/git/refs/{ref}", {"sha": sha, "force": False})
    if status != 200 or not _confirmed(data, ref, sha):
        raise GithubError("Registro do ID nao comprovado; reserva permanece bloqueada.")
