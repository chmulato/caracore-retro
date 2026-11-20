import hashlib
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools import facebook_campaign as campaign
from tools import facebook_drafts, facebook_github


BASE = "a" * 40
TREE = "b" * 40
NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


class FakeGithub:
    repository = campaign.REPOSITORY

    def __init__(self, digest, events):
        self.digest = digest
        self.events = events
        self.refs = {}
        self.counter = 0

    def request(self, method, path, payload=None):
        self.events.append((method, path))
        if path.endswith("/approvals"):
            return 200, [{"environments": [{"name": "facebook"}], "state": "approved",
                          "user": {"id": 42}, "comment": "APROVO " + self.digest}]
        if method == "GET" and "/git/commits/" in path:
            return 200, {"tree": {"sha": TREE}}
        if method == "POST" and path.endswith("/git/commits"):
            self.counter += 1
            return 201, {"sha": str(self.counter) * 40}
        if method == "POST" and path.endswith("/git/refs"):
            ref = payload["ref"]
            if ref in self.refs:
                return 422, {}
            self.refs[ref] = payload["sha"]
            return 201, {"ref": ref, "object": {"sha": payload["sha"]}}
        if method == "PATCH" and "/git/refs/" in path:
            ref = "refs/" + path.split("/git/refs/", 1)[1]
            if ref not in self.refs or payload["force"]:
                return 422, {}
            self.refs[ref] = payload["sha"]
            return 200, {"ref": ref, "object": {"sha": payload["sha"]}}
        raise AssertionError((method, path))


class FakeFacebook:
    def __init__(self, events, fail=False):
        self.events = events
        self.fail = fail
        self.sends = 0

    def check_page(self, page_id):
        self.events.append(("page", page_id))

    def schedule(self, content, timestamp):
        self.events.append(("send", timestamp))
        self.sends += 1
        if self.fail:
            raise OSError("resposta perdida")
        return "123_456"


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.articles = self.root / "docs" / "articles"
        self.images = self.articles / "assets" / "img"
        self.images.mkdir(parents=True)
        self.image = self.images / "capa.png"
        self.image.write_bytes(b"imagem")
        self.article = self.articles / "2026_11_30_article_109.html"
        self.article.write_text(
            "<html><head><meta property='og:title' content='Título'>"
            "<meta property='og:description' content='Descrição'>"
            "<meta property='og:url' content='https://retro.caracore.com.br/articles/2026_11_30_article_109.html'>"
            "<meta property='og:image' content='https://retro.caracore.com.br/articles/assets/img/capa.png'>"
            "<meta property='article:published_time' content='2026-11-30'></head></html>",
            encoding="utf-8")
        self.inputs = {"ARTICLE_NUMBER": "109", "FACEBOOK_PAGE_ID": "123",
                       "PUBLISH_AT": "2026-12-01T09:00", "FACEBOOK_MESSAGE": "Chamada do Facebook"}
        self.draft = campaign.draft_from_inputs(self.inputs, self.root)
        self.digest = self.draft["sha256_conteudo"]
        self.events = []
        self.api = FakeGithub(self.digest, self.events)
        self.graph = FakeFacebook(self.events)
        self.history({"147": "123_789"})

    def history(self, publications, page="123", checked=True):
        (self.root / "facebook_publication_history.json").write_text(json.dumps({
            "pagina_id": page, "conferido": checked, "publicacoes": publications,
        }), encoding="utf-8")

    def fetch(self, url):
        return self.image.read_bytes() if url.endswith("capa.png") else self.article.read_bytes()

    def run_publish(self, draft=None, digest=None, graph=None):
        with patch.object(campaign, "validate_run", return_value=("55", BASE, 42)):
            return campaign.publish(draft or self.draft, digest or self.digest, {}, self.api,
                                    graph or self.graph, self.root, self.fetch, NOW)

    def test_success_reserves_before_sending_and_records_id(self):
        self.assertEqual(self.run_publish(), "123_456")
        actions = [event[0] for event in self.events]
        self.assertLess(actions.index("page"), actions.index("send"))
        self.assertEqual(actions[:5], ["GET", "page", "GET", "POST", "POST"])
        self.assertEqual(actions[5:], ["send", "GET", "POST", "PATCH"])
        self.assertIn("refs/heads/facebook-reservas/p123/a109", self.api.refs)
        self.assertEqual(self.graph.sends, 1)

    def test_thursday_campaign_keeps_approval_and_schedules_once(self):
        draft = campaign.draft_from_inputs(dict(self.inputs, PUBLISH_AT="2026-12-03T09:00"), self.root)
        self.api.digest = draft["sha256_conteudo"]
        self.assertEqual(self.run_publish(draft=draft, digest=self.api.digest), "123_456")
        self.assertEqual(self.graph.sends, 1)
        self.assertIn(("send", int(datetime(2026, 12, 3, 12, tzinfo=timezone.utc).timestamp())), self.events)

    def test_automatic_campaign_skips_manual_approval_but_keeps_reservation(self):
        env = {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_REPOSITORY": campaign.REPOSITORY, "GITHUB_REF": "refs/heads/master",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "55", "GITHUB_SHA": BASE,
        }
        with patch.object(campaign, "validate_run", return_value=("55", BASE, None)):
            self.assertEqual(campaign.publish(
                self.draft, self.digest, env, self.api, self.graph, self.root,
                self.fetch, NOW, automatic=True,
            ), "123_456")
        self.assertFalse(any(
            isinstance(path, str) and path.endswith("/approvals")
            for _, path in self.events
        ))
        self.assertIn("refs/heads/facebook-reservas/p123/a109", self.api.refs)
        self.assertEqual(self.graph.sends, 1)

    def test_campaign_queue_selects_only_the_due_local_date(self):
        campaign_path = self.root / "facebook_campaign_article_109_20261201.json"
        campaign_path.write_text(json.dumps({
            **self.draft,
            "aviso": "NÃO APROVAR",
        }), encoding="utf-8")
        self.assertEqual(campaign.campaign_for_date(date(2026, 12, 1), self.root), campaign_path)
        self.assertIsNone(campaign.campaign_for_date(date(2026, 12, 3), self.root))
        loaded = campaign.draft_from_campaign_file(campaign_path, self.root)
        self.assertEqual(loaded, self.draft)

    def test_campaign_queue_rejects_ambiguous_dates(self):
        for number in ("109", "110"):
            path = self.root / f"facebook_campaign_article_{number}_20261201.json"
            path.write_text(json.dumps({
                **self.draft,
                "conteudo": {
                    **self.draft["conteudo"],
                    "artigo": f"docs/articles/2026_11_30_article_{number}.html",
                },
            }), encoding="utf-8")
        with self.assertRaisesRegex(campaign.CampaignError, "mais de uma campanha"):
            campaign.campaign_for_date(date(2026, 12, 1), self.root)

    def test_campaign_queue_rejects_duplicate_articles(self):
        first = self.root / "facebook_campaign_article_109_20261201.json"
        second_draft = campaign.draft_from_inputs(
            dict(self.inputs, PUBLISH_AT="2026-12-03T09:00"), self.root,
        )
        second = self.root / "facebook_campaign_article_109_20261203.json"
        first.write_text(json.dumps(self.draft), encoding="utf-8")
        second.write_text(json.dumps(second_draft), encoding="utf-8")
        with self.assertRaisesRegex(campaign.CampaignError, "aparece mais de uma vez"):
            campaign.load_campaign_queue(self.root)

    def test_fill_window_schedules_all_eligible_campaigns_and_leaves_later_ones(self):
        first = self.root / "facebook_campaign_article_109_20261201.json"
        later = self.root / "facebook_campaign_article_120_20270105.json"
        first.write_text("{}", encoding="utf-8")
        later.write_text("{}", encoding="utf-8")
        queue = [
            (first, self.draft, facebook_drafts.local_time("2026-12-01T09:00")),
            (later, self.draft, facebook_drafts.local_time("2027-01-05T09:00")),
        ]
        env = {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": campaign.REPOSITORY, "GITHUB_REF": "refs/heads/master",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "55", "GITHUB_SHA": BASE,
            "FACEBOOK_FILL_WINDOW": "true", "FACEBOOK_PAGE_TOKEN": "token",
            "GITHUB_TOKEN": "github-token",
        }
        with patch.object(campaign, "validate_run", return_value=("55", BASE, None)), \
                patch.object(campaign, "load_campaign_queue", return_value=queue), \
                patch.object(facebook_github, "reservation_status", return_value=None), \
                patch.object(campaign, "verify_published"), \
                patch.object(facebook_github, "GithubAPI", return_value=self.api), \
                patch.object(campaign, "FacebookAPI", return_value=self.graph):
            self.assertEqual(campaign.fill_campaign_window(env, self.root, NOW), 0)
        self.assertEqual(self.graph.sends, 1)
        self.assertIn("refs/heads/facebook-reservas/p123/a109", self.api.refs)

    def test_fill_window_skips_confirmed_posts_and_blocks_pending_reservations(self):
        path = self.root / "facebook_campaign_article_109_20261201.json"
        path.write_text("{}", encoding="utf-8")
        queue = [(path, self.draft, facebook_drafts.local_time("2026-12-01T09:00"))]
        env = {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_REPOSITORY": campaign.REPOSITORY, "GITHUB_REF": "refs/heads/master",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "55", "GITHUB_SHA": BASE,
            "FACEBOOK_PAGE_TOKEN": "token", "GITHUB_TOKEN": "github-token",
        }
        with patch.object(campaign, "validate_run", return_value=("55", BASE, None)), \
                patch.object(campaign, "load_campaign_queue", return_value=queue), \
                patch.object(facebook_github, "reservation_status", return_value={
                    "estado": "ID_RECEBIDO", "digest": self.digest, "remote_id": "123_456",
                }), \
                patch.object(facebook_github, "GithubAPI", return_value=self.api), \
                patch.object(campaign, "FacebookAPI", return_value=self.graph):
            self.assertEqual(campaign.fill_campaign_window(env, self.root, NOW), 0)
        self.assertEqual(self.graph.sends, 0)
        self.assertEqual(self.api.refs, {})

        with patch.object(campaign, "validate_run", return_value=("55", BASE, None)), \
                patch.object(campaign, "load_campaign_queue", return_value=queue), \
                patch.object(facebook_github, "reservation_status", return_value={
                    "estado": "RESERVADO", "digest": self.digest,
                }), \
                patch.object(facebook_github, "GithubAPI", return_value=self.api), \
                patch.object(campaign, "FacebookAPI", return_value=self.graph), \
                self.assertRaisesRegex(campaign.CampaignError, "reserva sem confirmacao"):
            campaign.fill_campaign_window(env, self.root, NOW)
        self.assertEqual(self.graph.sends, 0)

    def test_off_calendar_campaign_never_calls_github_or_meta(self):
        for when in ("2026-12-02T09:00", "2026-12-01T12:00"):
            with self.subTest(when=when):
                draft = json.loads(json.dumps(self.draft))
                content = draft["conteudo"]
                content["data_hora_local"] = when
                content["data_hora_utc"] = facebook_drafts.local_time(when).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                draft["sha256_conteudo"] = facebook_drafts.content_digest(content)
                self.events.clear()
                self.api = FakeGithub(draft["sha256_conteudo"], self.events)
                self.graph = FakeFacebook(self.events)
                with self.assertRaisesRegex(ValueError, "tercas e quintas"):
                    self.run_publish(draft=draft, digest=self.api.digest)
                self.assertEqual(self.events, [])
                self.assertEqual(self.graph.sends, 0)
                self.assertFalse(self.api.refs)

    def test_second_execution_cannot_repeat(self):
        self.run_publish()
        with self.assertRaises(facebook_github.GithubError):
            self.run_publish()
        self.assertEqual(self.graph.sends, 1)

    def test_two_simultaneous_executions_only_send_once(self):
        barrier = threading.Barrier(2)
        lock = threading.Lock()

        class RacingGithub(FakeGithub):
            def request(self, method, path, payload=None):
                if method == "POST" and path.endswith("/git/refs"):
                    barrier.wait(timeout=5)
                with lock:
                    return super().request(method, path, payload)

        api = RacingGithub(self.digest, self.events)

        def execute():
            try:
                return campaign.publish(self.draft, self.digest, {}, api, self.graph,
                                        self.root, self.fetch, NOW)
            except facebook_github.GithubError:
                return "bloqueado"

        with patch.object(campaign, "validate_run", return_value=("55", BASE, 42)):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda unused: execute(), range(2)))
        self.assertCountEqual(results, ["123_456", "bloqueado"])
        self.assertEqual(self.graph.sends, 1)

    def test_uncertain_meta_response_blocks_second_attempt(self):
        graph = FakeFacebook(self.events, fail=True)
        with self.assertRaisesRegex(campaign.CampaignError, "reserva permanece bloqueada"):
            self.run_publish(graph=graph)
        with self.assertRaises(facebook_github.GithubError):
            self.run_publish(graph=graph)
        self.assertEqual(graph.sends, 1)

    def test_failed_record_reports_identifier_without_repeating(self):
        with patch.object(facebook_github, "record_received", side_effect=facebook_github.GithubError("falha")):
            with self.assertRaisesRegex(campaign.CampaignError, "123_456"):
                self.run_publish()
        with self.assertRaises(facebook_github.GithubError):
            self.run_publish()
        self.assertEqual(self.graph.sends, 1)

    def test_changed_digest_or_approval_never_sends(self):
        with self.assertRaisesRegex(campaign.CampaignError, "diverge"):
            self.run_publish(digest="f" * 64)
        self.api.digest = "f" * 64
        with self.assertRaisesRegex(facebook_github.GithubError, "Aprovacao"):
            self.run_publish()
        self.assertEqual(self.graph.sends, 0)
        self.assertFalse(self.api.refs)

    def test_changed_article_or_live_image_never_sends(self):
        self.image.write_bytes(b"modificada")
        with self.assertRaises(ValueError):
            self.run_publish()
        self.image.write_bytes(b"imagem")
        with patch.object(campaign, "verify_published", side_effect=campaign.CampaignError("diverge")):
            with self.assertRaises(campaign.CampaignError):
                self.run_publish()
        self.assertEqual(self.graph.sends, 0)
        self.assertFalse(self.api.refs)

    def test_unchecked_incomplete_or_duplicate_history_never_sends(self):
        cases = [({}, "123", True), ({"147": "123_789"}, "456", True),
                 ({"147": "123_789"}, "123", False),
                 ({"147": "123_789", "109": "123_000"}, "123", True),
                 ({"147": "invalido"}, "123", True)]
        for publications, page, checked in cases:
            self.history(publications, page, checked)
            with self.subTest(publications=publications, page=page, checked=checked):
                with self.assertRaises(campaign.CampaignError):
                    self.run_publish()
        (self.root / "facebook_publication_history.json").unlink()
        with self.assertRaisesRegex(campaign.CampaignError, "Historico"):
            self.run_publish()
        self.assertEqual(self.graph.sends, 0)
        self.assertFalse(self.api.refs)

    def test_invalid_inputs_and_already_posted_article_147(self):
        for key, value in [("ARTICLE_NUMBER", "0147"), ("ARTICLE_NUMBER", "147"),
                           ("FACEBOOK_PAGE_ID", "00123"), ("FACEBOOK_MESSAGE", "  ")]:
            inputs = dict(self.inputs, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(campaign.CampaignError):
                campaign.draft_from_inputs(inputs, self.root)

    def test_empty_message_generates_a_suggestion_for_review(self):
        draft = campaign.draft_from_inputs(dict(self.inputs, FACEBOOK_MESSAGE=""), self.root)
        self.assertIn("E na sua rotina", draft["conteudo"]["mensagem"])
        self.assertEqual(draft["estado"], "RASCUNHO_NAO_APROVADO")

    def test_padded_article_filename_has_one_canonical_identity(self):
        source = self.article.read_text(encoding="utf-8")
        first = self.articles / "2026_11_30_article_01.html"
        first.write_text(source.replace(self.article.name, first.name), encoding="utf-8")
        draft = campaign.draft_from_inputs(dict(self.inputs, ARTICLE_NUMBER="1"), self.root)
        self.assertTrue(draft["conteudo"]["artigo"].endswith("_article_01.html"))
        duplicate = self.articles / "2026_11_30_article_001.html"
        duplicate.write_text(source.replace(self.article.name, duplicate.name), encoding="utf-8")
        with self.assertRaisesRegex(campaign.CampaignError, "duplicado"):
            campaign.draft_from_inputs(dict(self.inputs, ARTICLE_NUMBER="1"), self.root)

    def test_padded_filename_reserves_canonical_article_number(self):
        source = self.article.read_text(encoding="utf-8")
        first = self.articles / "2026_11_30_article_01.html"
        first.write_text(source.replace(self.article.name, first.name), encoding="utf-8")
        draft = campaign.draft_from_inputs(dict(self.inputs, ARTICLE_NUMBER="1"), self.root)
        self.api.digest = draft["sha256_conteudo"]
        def fetch(url):
            return self.image.read_bytes() if url.endswith("capa.png") else first.read_bytes()
        with patch.object(campaign, "validate_run", return_value=("55", BASE, 42)):
            campaign.publish(draft, draft["sha256_conteudo"], {}, self.api, self.graph,
                             self.root, fetch, NOW)
        self.assertIn("refs/heads/facebook-reservas/p123/a1", self.api.refs)

    def test_time_expiring_after_reservation_does_not_send(self):
        with patch.object(campaign, "validate_schedule", side_effect=[1, campaign.CampaignError("expirou")]):
            with self.assertRaisesRegex(campaign.CampaignError, "Nenhum envio foi feito"):
                self.run_publish()
        self.assertEqual(self.graph.sends, 0)
        self.assertIn("refs/heads/facebook-reservas/p123/a109", self.api.refs)

    def test_time_window(self):
        scheduled = datetime.strptime(self.draft["conteudo"]["data_hora_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        for difference in [timedelta(minutes=14), timedelta(days=30), timedelta(seconds=-1)]:
            with self.subTest(difference=difference), self.assertRaises(campaign.CampaignError):
                campaign.validate_schedule(self.draft, scheduled - difference)
        for difference in [timedelta(minutes=15), timedelta(days=29, hours=23, minutes=55)]:
            self.assertEqual(campaign.validate_schedule(self.draft, scheduled - difference), int(scheduled.timestamp()))
        with self.assertRaises(campaign.CampaignError):
            campaign.validate_schedule(self.draft, datetime(2026, 11, 20))

    def test_summary_escapes_call_and_contains_review_instruction(self):
        inputs = dict(self.inputs, FACEBOOK_MESSAGE="</pre><script>perigo</script>\nTexto")
        draft = campaign.draft_from_inputs(inputs, self.root)
        summary = campaign.review_summary(draft)
        self.assertIn("&lt;/pre&gt;&lt;script&gt;perigo&lt;/script&gt;", summary)
        self.assertNotIn("<script>", summary)
        self.assertIn("APROVO " + draft["sha256_conteudo"], summary)
        self.assertIn("prévia real do link no Facebook", summary)
        self.assertIn("2026-12-01T09:00", summary)
        self.assertIn(hashlib.sha256(self.image.read_bytes()).hexdigest(), summary)

    def test_live_site_content_matches_or_blocks(self):
        campaign.verify_published(self.draft, self.fetch)
        with self.assertRaisesRegex(campaign.CampaignError, "diverge"):
            campaign.verify_published(self.draft, lambda url: b"conteudo diferente")

    def test_run_context_rejects_reruns_non_master_and_wrong_sha(self):
        env = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
               "GITHUB_REPOSITORY": campaign.REPOSITORY, "GITHUB_REF": "refs/heads/master",
               "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "55", "GITHUB_SHA": BASE,
               "FACEBOOK_REVIEWER_ID": "42"}
        process = MagicMock(returncode=0, stdout=BASE + "\n")
        with patch.object(campaign.subprocess, "run", return_value=process):
            self.assertEqual(campaign.validate_run(env, self.root), ("55", BASE, 42))
            for key, value in [("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_REF", "refs/heads/outro"),
                               ("GITHUB_REPOSITORY", "outro/repo"), ("GITHUB_EVENT_NAME", "push"),
                               ("GITHUB_SHA", "f" * 40), ("FACEBOOK_REVIEWER_ID", "0")]:
                changed = dict(env, **{key: value})
                with self.subTest(key=key), self.assertRaises(campaign.CampaignError):
                    campaign.validate_run(changed, self.root)

    def test_scheduled_run_requires_schedule_event_but_not_reviewer(self):
        env = {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_REPOSITORY": campaign.REPOSITORY, "GITHUB_REF": "refs/heads/master",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "55", "GITHUB_SHA": BASE,
        }
        process = MagicMock(returncode=0, stdout=BASE + "\n")
        with patch.object(campaign.subprocess, "run", return_value=process):
            self.assertEqual(campaign.validate_run(env, self.root, automatic=True),
                             ("55", BASE, None))
            manual = dict(env, GITHUB_EVENT_NAME="workflow_dispatch")
            with self.assertRaises(campaign.CampaignError):
                campaign.validate_run(manual, self.root, automatic=True)
            self.assertEqual(campaign.validate_run(
                dict(manual, FACEBOOK_FILL_WINDOW="true"), self.root, automatic=True,
            ), ("55", BASE, None))


class FacebookTransportTests(unittest.TestCase):
    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_single_post_uses_header_and_expected_schedule(self, connect):
        response = MagicMock(status=200)
        response.read.return_value = b'{"id":"123_456"}'
        connect.return_value.getresponse.return_value = response
        api = campaign.FacebookAPI("segredo")
        content = {"pagina_id": "123", "mensagem": "Ola", "link": "https://example.com"}
        self.assertEqual(api.schedule(content, 1234567890), "123_456")
        self.assertEqual(connect.call_count, 1)
        args, kwargs = connect.return_value.request.call_args
        self.assertEqual(args, ("POST", "/v27.0/123/feed"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer segredo")
        self.assertNotIn(b"segredo", kwargs["body"])
        self.assertIn(b"published=false", kwargs["body"])
        self.assertIn(b"scheduled_publish_time=1234567890", kwargs["body"])

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_failures_do_not_expose_credentials(self, connect):
        api = campaign.FacebookAPI("segredo")
        connect.return_value.request.side_effect = ValueError("segredo")
        with self.assertRaises(campaign.CampaignError) as caught:
            api.request("GET", "/v27.0/me?fields=id")
        self.assertNotIn("segredo", str(caught.exception))
        with self.assertRaises(campaign.CampaignError) as caught:
            campaign.FacebookAPI("segredo\ninvalido")
        self.assertNotIn("segredo", str(caught.exception))

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_page_mismatch_and_redirect_fail_closed(self, connect):
        response = MagicMock(status=200)
        response.read.return_value = b'{"id":"999"}'
        connect.return_value.getresponse.return_value = response
        api = campaign.FacebookAPI("segredo")
        with self.assertRaises(campaign.CampaignError):
            api.check_page("123")
        response.status = 302
        response.read.return_value = b'{"id":"123"}'
        with self.assertRaises(campaign.CampaignError):
            api.check_page("123")
        self.assertEqual(connect.call_count, 2)


class FacebookDiagnosticTests(unittest.TestCase):
    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_identity_diagnosis_uses_one_get_and_never_prints_returned_id(self, connect):
        for status, body, matches in [
            (200, {"id": "123"}, True),
            (200, {"id": "999"}, False),
            (200, {"id": 123}, False),
            (200, {"id": "segredo"}, False),
            (200, [], False),
            (302, {"id": "123"}, False),
        ]:
            with self.subTest(status=status, body=body):
                connect.reset_mock()
                response = MagicMock(status=status)
                response.read.return_value = json.dumps(body).encode()
                connect.return_value.getresponse.return_value = response
                result = campaign.FacebookAPI("segredo").diagnose_page("123")
                self.assertEqual(result, {"http_status": status, "page_matches": matches,
                                         "error_code": None, "error_subcode": None})
                self.assertNotIn("segredo", json.dumps(result))
                connect.assert_called_once_with("graph.facebook.com", timeout=30)
                connect.return_value.request.assert_called_once()
                args, kwargs = connect.return_value.request.call_args
                self.assertEqual(args, ("GET", "/v27.0/me?fields=id"))
                self.assertIsNone(kwargs["body"])
                connect.return_value.close.assert_called_once()

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_error_diagnosis_only_includes_bounded_integer_codes(self, connect):
        for code, subcode, expected_code, expected_subcode in [
            (190, 463, 190, 463), (10, None, 10, None),
            ("segredo", "segredo", None, None),
            (True, False, None, None), (-1, 2 ** 40, None, None),
        ]:
            with self.subTest(code=code, subcode=subcode):
                response = MagicMock(status=400)
                response.read.return_value = json.dumps({"access_token": "segredo", "error": {
                    "code": code, "error_subcode": subcode, "message": "Bearer segredo",
                    "type": "segredo", "fbtrace_id": "segredo",
                }}).encode()
                connect.return_value.getresponse.return_value = response
                result = campaign.FacebookAPI("segredo").diagnose_page("123")
                self.assertEqual(result, {"http_status": 400, "page_matches": False,
                                         "error_code": expected_code, "error_subcode": expected_subcode})
                self.assertNotIn("segredo", json.dumps(result))

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_invalid_page_never_contacts_meta(self, connect):
        for page in ("", "0123", "123?access_token=segredo"):
            with self.subTest(page=page), self.assertRaises(campaign.CampaignError):
                campaign.FacebookAPI("segredo").diagnose_page(page)
        connect.assert_not_called()

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_diagnostic_command_bypasses_all_publication_paths(self, connect):
        response = MagicMock(status=200)
        response.read.return_value = b'{"id":"123","access_token":"segredo"}'
        connect.return_value.getresponse.return_value = response
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder) / "summary.txt"
            env = {"FACEBOOK_PAGE_TOKEN": "segredo", "FACEBOOK_PAGE_ID": "123",
                   "GITHUB_STEP_SUMMARY": str(summary)}
            with patch.dict(campaign.os.environ, env, clear=True), \
                    patch.object(campaign.sys, "argv", ["facebook_campaign", "diagnosticar"]), \
                    patch.object(campaign, "validate_run", return_value=("55", BASE, 42)) as validate, \
                    patch.object(campaign, "draft_from_inputs") as draft, \
                    patch.object(campaign, "publish") as publish, \
                    patch.object(facebook_github, "GithubAPI") as github, \
                    patch.object(campaign.sys, "stdout", new_callable=io.StringIO) as output:
                self.assertEqual(campaign.main(), 0)
                validate.assert_called_once()
                draft.assert_not_called()
                publish.assert_not_called()
                github.assert_not_called()
                self.assertNotIn("segredo", output.getvalue() + summary.read_text(encoding="utf-8"))
                self.assertIn('"page_matches": true', output.getvalue())
                self.assertEqual(connect.return_value.request.call_count, 1)
                self.assertEqual(connect.return_value.request.call_args.args[0], "GET")

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_diagnostic_command_returns_failure_with_safe_meta_codes(self, connect):
        response = MagicMock(status=400)
        response.read.return_value = b'{"error":{"code":190,"error_subcode":463,"message":"Bearer segredo"}}'
        connect.return_value.getresponse.return_value = response
        with patch.dict(campaign.os.environ, {"FACEBOOK_PAGE_TOKEN": "segredo", "FACEBOOK_PAGE_ID": "123"}, clear=True), \
                patch.object(campaign.sys, "argv", ["facebook_campaign", "diagnosticar"]), \
                patch.object(campaign, "validate_run", return_value=("55", BASE, 42)), \
                patch.object(campaign.sys, "stdout", new_callable=io.StringIO) as output:
            self.assertEqual(campaign.main(), 1)
            result = json.loads(output.getvalue().splitlines()[-1])
            self.assertEqual(result["error_code"], 190)
            self.assertEqual(result["error_subcode"], 463)
            self.assertFalse(result["page_matches"])
            self.assertNotIn("segredo", output.getvalue())

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_diagnostic_command_reports_failure_without_raw_exception(self, connect):
        connect.return_value.request.side_effect = ValueError("Bearer segredo")
        with patch.dict(campaign.os.environ, {"FACEBOOK_PAGE_TOKEN": "segredo", "FACEBOOK_PAGE_ID": "123"}, clear=True), \
                patch.object(campaign.sys, "argv", ["facebook_campaign", "diagnosticar"]), \
                patch.object(campaign, "validate_run", return_value=("55", BASE, 42)), \
                patch.object(campaign.sys, "stderr", new_callable=io.StringIO) as output:
            self.assertEqual(campaign.main(), 1)
            self.assertNotIn("segredo", output.getvalue())
            self.assertIn("Nao foi possivel confirmar", output.getvalue())
            self.assertEqual(connect.return_value.request.call_count, 1)

    @patch("tools.facebook_campaign.http.client.HTTPSConnection")
    def test_diagnostic_requires_official_run_before_accessing_token(self, connect):
        with patch.dict(campaign.os.environ, {}, clear=True), \
                patch.object(campaign.sys, "argv", ["facebook_campaign", "diagnosticar"]), \
                patch.object(campaign.sys, "stderr", new_callable=io.StringIO):
            self.assertEqual(campaign.main(), 1)
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
