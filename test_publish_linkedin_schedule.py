import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tools import publish_linkedin


class ScheduledArticleTests(unittest.TestCase):
    def test_selects_only_articles_due_on_the_requested_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            articles_dir = Path(temp_dir)
            due = articles_dir / "2026_11_30_article_109.html"
            future = articles_dir / "2026_12_03_article_110.html"
            invalid = articles_dir / "2026_11_31_article_999.html"
            for path in (due, future, invalid):
                path.write_text("", encoding="utf-8")

            self.assertEqual(
                publish_linkedin.scheduled_articles(date(2026, 11, 30), articles_dir),
                [due],
            )

    def test_schedule_stops_after_2026(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            articles_dir = Path(temp_dir)
            article = articles_dir / "2027_01_01_article_117.html"
            article.write_text("", encoding="utf-8")

            self.assertEqual(
                publish_linkedin.scheduled_articles(date(2027, 1, 1), articles_dir),
                [],
            )

    def test_push_selection_leaves_scheduled_articles_for_their_date(self) -> None:
        changed = (
            "docs/articles/2026_11_30_article_109.html\n"
            "docs/articles/2026_11_14_article_108.html\n"
        )
        result = subprocess.CompletedProcess(args=["git"], returncode=0, stdout=changed)
        with patch.object(publish_linkedin.subprocess, "run", return_value=result):
            self.assertEqual(
                publish_linkedin.added_articles(),
                [publish_linkedin.ROOT / "docs/articles/2026_11_14_article_108.html"],
            )

    def test_published_articles_are_excluded_unless_forced(self) -> None:
        published = publish_linkedin.ROOT / "docs/articles/2026_11_30_article_109.html"
        due = publish_linkedin.ROOT / "docs/articles/2026_12_03_article_110.html"
        ledger = {publish_linkedin.article_key(published): "2026-11-30T07:30:00Z"}

        self.assertEqual(
            publish_linkedin.unpublished_articles([published, due], ledger),
            [due],
        )
        self.assertEqual(
            publish_linkedin.unpublished_articles([published], ledger, force=True),
            [published],
        )


if __name__ == "__main__":
    unittest.main()
