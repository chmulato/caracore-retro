import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tools import facebook_campaign, facebook_drafts, facebook_github
from tools import facebook_publish_article as publication


BASE = "a" * 40
NOW = datetime(2026, 11, 20, 11, 0, tzinfo=timezone.utc)
ARTICLE_URL = "https://retro.caracore.com.br/articles/2027_09_15_article_149.html"
RESERVATION = "heads/facebook-reservas/p1657316127663973/a149"


class FakeGithub:
    def __init__(self):
        self.events = []


class FakeFacebook:
    def __init__(self, events, post_response=None, posts=None):
        self.events = events
        self.post_response = post_response or (200, {"id": "123_456"})
        self.posts = posts or []

    def check_page(self, page_id):
        self.events.append(("page", page_id))

    def request(self, method, path, body=None):
        self.events.append((method, path, body))
        if method == "POST":
            return self.post_response
        if "published_posts" in path:
            return 200, {"data": self.posts}
        return 200, {"permalink_url": "https://www.facebook.com/123/posts/456"}


class ImmediateFacebookPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        images = self.root / "docs" / "articles" / "assets" / "img"
        images.mkdir(parents=True)
        (images / "capa.png").write_bytes(b"imagem publicada")
        (self.root / "docs" / "articles" / "2027_09_15_article_149.html").write_text(
            "<html><head><meta property='og:title' content='O que tem dentro da caixa'>"
            "<meta property='og:description' content='Feito, empacotado e instalado sao tres estados.'>"
            f"<meta property='og:url' content='{ARTICLE_URL}'>"
            "<meta property='og:image' content='https://retro.caracore.com.br/articles/assets/img/capa.png'>"
            "<meta property='article:published_time' content='2027-09-15'></head></html>",
            encoding="utf-8",
        )
        self.env = {
            "ARTICLE_NUMBER": "149",
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": facebook_campaign.REPOSITORY,
            "GITHUB_REF": "refs/heads/master",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "55",
            "GITHUB_SHA": BASE,
            "FACEBOOK_REVIEWER_ID": "42",
        }
        self.draft = publication.build_draft("2026-11-20T07:57", "149", None, self.root)
        self.events = []
        self.graph = FakeFacebook(self.events)
        self.api = FakeGithub()
        (self.root / "facebook_publication_history.json").write_text(json.dumps({
            "pagina_id": publication.PAGE_ID,
            "conferido": True,
            "publicacoes": {"147": "123_789", "148": "123_999"},
        }), encoding="utf-8")
        self.approval = self.start(patch.object(facebook_github, "check_approval"))
        self.reserve = self.start(patch.object(
            facebook_github, "reserve", return_value=(RESERVATION, "b" * 40)))
        self.record = self.start(patch.object(facebook_github, "record_received"))
        self.start(patch.object(facebook_campaign, "validate_run", return_value=("55", BASE, 42)))
        self.start(patch.object(facebook_campaign, "verify_published"))

    def start(self, guard):
        mock = guard.start()
        self.addCleanup(guard.stop)
        return mock

    def publish(self, graph=None, draft=None, digest=None, now=NOW, env=None):
        return publication.publish(
            draft or self.draft,
            self.draft["sha256_conteudo"] if digest is None else digest,
            env or self.env,
            self.api,
            graph or self.graph,
            self.root,
            now,
        )

    def test_the_article_number_comes_from_the_execution(self):
        draft = publication.build_draft("2026-11-20T07:57", "149", None, self.root)
        self.assertEqual(draft["conteudo"]["modo_publicacao"], "imediata")
        self.assertEqual(draft["conteudo"]["pagina_id"], publication.PAGE_ID)
        self.assertEqual(draft["conteudo"]["artigo"], "docs/articles/2027_09_15_article_149.html")
        self.assertEqual(draft["conteudo"]["link"], ARTICLE_URL)

    def test_the_call_text_is_suggested_by_the_article_itself(self):
        message = self.draft["conteudo"]["mensagem"]
        self.assertIn("Feito, empacotado e instalado sao tres estados.", message)
        self.assertIn("O que tem dentro da caixa", message)
        self.assertEqual(message.rstrip().splitlines()[-1], ARTICLE_URL)

    def test_immediate_post_goes_only_to_the_page_and_publishes_once(self):
        result = self.publish()
        self.assertEqual(result, ("123_456", "https://www.facebook.com/123/posts/456"))
        self.approval.assert_called_once()
        self.reserve.assert_called_once()
        self.record.assert_called_once()
        post = next(event for event in self.events if event[0] == "POST")
        self.assertEqual(post[1], f"/{facebook_campaign.API_VERSION}/{publication.PAGE_ID}/feed")
        self.assertEqual(post[2]["published"], "true")
        self.assertEqual(post[2]["message"], self.draft["conteudo"]["mensagem"])
        self.assertEqual(post[2]["link"], ARTICLE_URL)

    def test_unknown_article_or_missing_number_stops_before_any_call(self):
        for provided, value in ((False, ""), (True, "0149"), (True, "148")):
            env = {k: v for k, v in self.env.items() if k != "ARTICLE_NUMBER"}
            if provided:
                env["ARTICLE_NUMBER"] = value
            with self.subTest(article=value or "ausente"):
                with self.assertRaises(facebook_campaign.CampaignError):
                    publication.publish(self.draft, self.draft["sha256_conteudo"], env,
                                        self.api, self.graph, self.root, NOW)
        self.assertEqual(self.events, [])
        self.reserve.assert_not_called()

    def test_blank_call_text_is_refused(self):
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "apenas espacos"):
            publication.article_message({"FACEBOOK_MESSAGE": "   "})
        self.assertIsNone(publication.article_message({"FACEBOOK_MESSAGE": ""}))

    def test_duplicate_history_blocks_before_page_check_or_post(self):
        history = self.root / "facebook_publication_history.json"
        data = json.loads(history.read_text(encoding="utf-8"))
        data["publicacoes"]["149"] = "123_456"
        history.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "historico"):
            self.publish()
        self.assertFalse(any(event[0] == "POST" for event in self.events))

    def test_recent_page_posts_are_checked_before_reserving(self):
        graph = FakeFacebook(self.events, posts=[{"id": "123_455", "message": "Leia " + ARTICLE_URL}])
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "posts recentes"):
            self.publish(graph=graph)
        self.assertFalse(any(event[0] == "POST" for event in self.events))

    def test_uncertain_meta_response_is_not_retried(self):
        graph = FakeFacebook(self.events, post_response=(500, {"error": "uncertain"}))
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "reserva bloqueia repeticoes"):
            self.publish(graph=graph)
        self.assertEqual(sum(event[0] == "POST" for event in self.events), 1)

    def test_expired_review_stops_before_meta_or_reservation(self):
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "revisao expirou"):
            self.publish(now=datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc))
        self.reserve.assert_not_called()
        self.assertEqual(self.events, [])

    def test_approved_digest_must_match_the_draft(self):
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "diverge da publicacao autorizada"):
            self.publish(digest="f" * 64)
        self.reserve.assert_not_called()
        self.assertEqual(self.events, [])

    def test_a_scheduled_campaign_is_refused_by_the_immediate_path(self):
        scheduled = facebook_drafts.prepare(
            self.root / "docs" / "articles" / "2027_09_15_article_149.html",
            publication.PAGE_ID, "2026-11-24T09:00",
            self.draft["conteudo"]["mensagem"], self.root,
        )
        self.assertNotIn("modo_publicacao", scheduled["conteudo"])
        with self.assertRaisesRegex(facebook_campaign.CampaignError, "diverge da publicacao autorizada"):
            self.publish(draft=scheduled, digest=scheduled["sha256_conteudo"])
        self.assertEqual(self.events, [])

    def test_the_summary_carries_the_exact_line_to_paste(self):
        digest = self.draft["sha256_conteudo"]
        summary = publication.review_summary(self.draft)
        self.assertIn(f"APROVO {digest}", summary)
        self.assertIn("campo de comentario", summary)
        self.assertIn("2026-11-20 08:12", summary)


if __name__ == "__main__":
    unittest.main()
