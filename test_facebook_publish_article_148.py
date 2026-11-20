import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tools import facebook_campaign, facebook_drafts, facebook_github
from tools import facebook_publish_article_148 as publication


BASE = "a" * 40
NOW = datetime(2026, 11, 20, 11, 0, tzinfo=timezone.utc)


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
        articles = self.root / "docs" / "articles"
        images = articles / "assets" / "img"
        images.mkdir(parents=True)
        self.image = images / "capa.png"
        self.image.write_bytes(b"imagem publicada")
        self.article = articles / "2027_09_07_article_148.html"
        self.article.write_text(
            "<html><head><meta property='og:title' content='Os Quatro Trabalhoes'>"
            "<meta property='og:description' content='Quatro ajudantes, uma oficina e uma regra.'>"
            "<meta property='og:url' content='https://retro.caracore.com.br/articles/2027_09_07_article_148.html'>"
            "<meta property='og:image' content='https://retro.caracore.com.br/articles/assets/img/capa.png'>"
            "<meta property='article:published_time' content='2027-09-07'></head></html>",
            encoding="utf-8",
        )
        self.draft = publication.build_draft("2026-11-20T07:57", self.root)
        self.events = []
        self.graph = FakeFacebook(self.events)
        self.api = FakeGithub()
        (self.root / "facebook_publication_history.json").write_text(json.dumps({
            "pagina_id": publication.PAGE_ID,
            "conferido": True,
            "publicacoes": {"147": "123_789"},
        }), encoding="utf-8")
        self.env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": facebook_campaign.REPOSITORY,
            "GITHUB_REF": "refs/heads/master",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "55",
            "GITHUB_SHA": BASE,
            "FACEBOOK_REVIEWER_ID": "42",
        }

    def publish(self, graph=None, api=None, draft=None, digest=None):
        with (patch.object(facebook_campaign, "validate_run", return_value=("55", BASE, 42)),
              patch.object(facebook_campaign, "verify_published"),
              patch.object(facebook_github, "check_approval") as approval,
              patch.object(facebook_github, "reserve", return_value=("heads/facebook-reservas/p1657316127663973/a148", "b" * 40)) as reserve,
              patch.object(facebook_github, "record_received") as record):
            result = publication.publish(
                draft or self.draft,
                digest or self.draft["sha256_conteudo"],
                self.env,
                api or self.api,
                graph or self.graph,
                self.root,
                NOW,
            )
        return result, approval, reserve, record

    def test_builds_immediate_draft_outside_schedule_and_publishes_only_to_facebook(self):
        draft = self.draft
        self.assertEqual(draft["conteudo"]["modo_publicacao"], "imediata")
        self.assertEqual(draft["conteudo"]["pagina_id"], publication.PAGE_ID)
        self.assertEqual(draft["conteudo"]["link"],
                         "https://retro.caracore.com.br/articles/2027_09_07_article_148.html")
        result, approval, reserve, record = self.publish()
        self.assertEqual(result, ("123_456", "https://www.facebook.com/123/posts/456"))
        approval.assert_called_once()
        reserve.assert_called_once()
        record.assert_called_once()
        post = next(event for event in self.events if event[0] == "POST")
        self.assertEqual(post[1], f"/{facebook_campaign.API_VERSION}/{publication.PAGE_ID}/feed")
        self.assertEqual(post[2]["published"], "true")
        self.assertEqual(post[2]["message"], publication.MESSAGE)
        self.assertEqual(post[2]["link"], draft["conteudo"]["link"])

    def test_duplicate_history_blocks_before_page_check_or_post(self):
        history = self.root / "facebook_publication_history.json"
        data = json.loads(history.read_text(encoding="utf-8"))
        data["publicacoes"]["148"] = "123_456"
        history.write_text(json.dumps(data), encoding="utf-8")
        with patch.object(facebook_campaign, "validate_run", return_value=("55", BASE, 42)), \
                patch.object(facebook_campaign, "verify_published"), \
                patch.object(facebook_github, "check_approval"), \
                patch.object(facebook_github, "reserve") as reserve:
            with self.assertRaisesRegex(facebook_campaign.CampaignError, "historico"):
                publication.publish(
                    self.draft, self.draft["sha256_conteudo"], self.env,
                    self.api, self.graph, self.root, NOW,
                )
        reserve.assert_not_called()
        self.assertFalse(any(event[0] == "POST" for event in self.events))

    def test_recent_page_posts_are_checked_before_reserving(self):
        graph = FakeFacebook(self.events, posts=[{
            "id": "123_455",
            "message": "Leia o artigo " + self.draft["conteudo"]["link"],
        }])
        with patch.object(facebook_campaign, "validate_run", return_value=("55", BASE, 42)), \
                patch.object(facebook_campaign, "verify_published"), \
                patch.object(facebook_github, "check_approval"), \
                patch.object(facebook_github, "reserve") as reserve:
            with self.assertRaisesRegex(facebook_campaign.CampaignError, "posts recentes"):
                publication.publish(
                    self.draft, self.draft["sha256_conteudo"], self.env,
                    self.api, graph, self.root, NOW,
                )
        reserve.assert_not_called()
        self.assertFalse(any(event[0] == "POST" for event in self.events))

    def test_uncertain_meta_response_is_not_retried(self):
        self.graph = FakeFacebook(self.events, post_response=(500, {"error": "uncertain"}))
        with patch.object(facebook_campaign, "validate_run", return_value=("55", BASE, 42)), \
                patch.object(facebook_campaign, "verify_published"), \
                patch.object(facebook_github, "check_approval"), \
                patch.object(facebook_github, "reserve", return_value=("heads/facebook-reservas/p1657316127663973/a148", "b" * 40)):
            with self.assertRaisesRegex(facebook_campaign.CampaignError, "reserva bloqueia repeticoes"):
                publication.publish(
                    self.draft, self.draft["sha256_conteudo"], self.env,
                    self.api, self.graph, self.root, NOW,
                )
        self.assertEqual(sum(event[0] == "POST" for event in self.events), 1)

    def test_expired_review_stops_before_meta_or_reservation(self):
        expired = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
        with patch.object(facebook_campaign, "validate_run", return_value=("55", BASE, 42)), \
                patch.object(facebook_github, "check_approval"), \
                patch.object(facebook_github, "reserve") as reserve:
            with self.assertRaisesRegex(facebook_campaign.CampaignError, "revisao expirou"):
                publication.publish(
                    self.draft, self.draft["sha256_conteudo"], self.env,
                    self.api, self.graph, self.root, expired,
                )
        reserve.assert_not_called()
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
