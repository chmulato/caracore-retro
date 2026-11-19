import tempfile
import unittest
from pathlib import Path

from social_metadata import normalize, normalize_privacy_page


class SocialMetadataTests(unittest.TestCase):
    def test_article_normalization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            page = Path(temporary_directory) / "2027_01_01_article_01.html"
            page.write_text(
                """<!doctype html>
<html lang="pt-BR">
<head>
    <title>Artigo de teste — Cara Core</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Descrição antiga.">
    <script type="application/ld+json">{"@type":"Article"}</script>
</head>
<body><h1>Artigo de teste</h1></body>
</html>
""",
                encoding="utf-8",
            )

            normalize(page, home=False)
            first_generation = page.read_bytes()
            normalize(page, home=False)

            self.assertEqual(first_generation, page.read_bytes())

    def test_privacy_page_normalization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            page = Path(temporary_directory) / "privacidade.html"
            page.write_text(
                """<!doctype html>
<html lang="pt-BR">
<head>
    <title>Privacidade — Cara Core</title>
    <meta name="description" content="Política de privacidade.">
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"WebPage"}
    </script>
</head>
<body><h1>Privacidade</h1></body>
</html>
""",
                encoding="utf-8",
            )

            normalize_privacy_page(page)
            first_generation = page.read_bytes()
            normalize_privacy_page(page)

            self.assertEqual(first_generation, page.read_bytes())


if __name__ == "__main__":
    unittest.main()
