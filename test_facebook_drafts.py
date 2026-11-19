import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import facebook_drafts


class FacebookDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.articles = self.root / "docs" / "articles"
        self.images = self.articles / "assets" / "img"
        self.images.mkdir(parents=True)
        self.article = self.articles / "2026_11_30_article_109.html"
        self.image = self.images / "capa.png"
        self.image.write_bytes(b"imagem de teste")
        self.article.write_text(
            "<!doctype html><html><head>"
            "<meta property='og:title' content='Título &amp; contexto'>"
            "<meta property='og:description' content='Uma explicação prática.'>"
            "<meta property='og:url' content='https://retro.caracore.com.br/articles/2026_11_30_article_109.html'>"
            "<meta property='og:image' content='https://retro.caracore.com.br/articles/assets/img/capa.png'>"
            "<meta property='article:published_time' content='2026-11-30'>"
            "</head><body>Conteúdo</body></html>",
            encoding="utf-8",
        )

    def draft(self, page: str = "123456", when: str = "2026-12-01T09:00",
              message: str | None = None) -> dict:
        return facebook_drafts.prepare(self.article, page, when, message, self.root)

    def test_suggests_a_facebook_message_and_keeps_it_unapproved(self) -> None:
        draft = self.draft()
        content = draft["conteudo"]
        self.assertEqual(draft["estado"], "RASCUNHO_NAO_APROVADO")
        self.assertIn("E na sua rotina", content["mensagem"])
        self.assertIn("Título & contexto", content["mensagem"])
        self.assertIn(content["link"], content["mensagem"])
        self.assertEqual(content["data_hora_utc"], "2026-12-01T12:00:00Z")
        self.assertIn("nao foram conferidos", draft["aviso"])
        facebook_drafts.verify(draft, self.root)

    def test_same_content_has_same_digest_and_custom_text_changes_it(self) -> None:
        first = self.draft()
        self.assertEqual(first["sha256_conteudo"], self.draft()["sha256_conteudo"])
        custom = self.draft(message="Uma chamada escrita para o Facebook.")
        self.assertNotEqual(first["sha256_conteudo"], custom["sha256_conteudo"])
        facebook_drafts.verify(custom, self.root)

    def test_digest_covers_message_image_link_page_channel_and_time(self) -> None:
        for field in ("mensagem", "imagem_url", "imagem_sha256", "link", "pagina_id",
                      "rede", "data_hora_local", "data_hora_utc", "data_editorial", "fuso"):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.draft())
                changed["conteudo"][field] += "x"
                with self.assertRaisesRegex(ValueError, "conteudo mudou"):
                    facebook_drafts.verify(changed, self.root)

    def test_recalculated_digest_does_not_hide_change_of_channel(self) -> None:
        draft = self.draft()
        draft["conteudo"]["rede"] = "linkedin"
        draft["sha256_conteudo"] = facebook_drafts.content_digest(draft["conteudo"])
        with self.assertRaisesRegex(ValueError, "dados do rascunho mudaram"):
            facebook_drafts.verify(draft, self.root)

    def test_article_change_invalidates_draft(self) -> None:
        draft = self.draft()
        with self.article.open("a", encoding="utf-8") as file:
            file.write("Atualização")
        with self.assertRaisesRegex(ValueError, "artigo, a imagem"):
            facebook_drafts.verify(draft, self.root)

    def test_image_change_invalidates_draft(self) -> None:
        draft = self.draft()
        self.image.write_bytes(b"imagem diferente")
        with self.assertRaisesRegex(ValueError, "artigo, a imagem"):
            facebook_drafts.verify(draft, self.root)

    def test_a_draft_cannot_be_marked_as_approved(self) -> None:
        draft = self.draft()
        draft["estado"] = "APROVADO"
        with self.assertRaisesRegex(ValueError, "nao e um rascunho"):
            facebook_drafts.verify(draft, self.root)

    def test_accepts_tuesdays_and_thursdays_at_nine_in_brasilia(self) -> None:
        for day in ("2026-12-01", "2026-12-03", "2027-01-05", "2027-01-07"):
            with self.subTest(day=day):
                draft = self.draft(when=f"{day}T09:00")
                self.assertEqual(draft["conteudo"]["fuso"], "America/Sao_Paulo")
                self.assertEqual(draft["conteudo"]["data_hora_utc"], f"{day}T12:00:00Z")
                self.assertEqual(draft["estado"], "RASCUNHO_NAO_APROVADO")
                facebook_drafts.verify(draft, self.root)

    def test_rejects_other_weekdays_and_times(self) -> None:
        for when in ("2026-11-30T09:00", "2026-12-02T09:00", "2026-12-04T09:00",
                     "2026-12-05T09:00", "2026-12-06T09:00", "2026-12-01T08:59",
                     "2026-12-01T09:01", "2026-12-03T12:00"):
            with self.subTest(when=when), self.assertRaisesRegex(ValueError, "tercas e quintas"):
                self.draft(when=when)

    def test_rejects_date_before_article_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "antecede"):
            self.draft(when="2026-11-26T09:00")

    def test_rejects_invalid_page_time_and_empty_message(self) -> None:
        for arguments in ({"page": "pagina"}, {"when": "2026-11-30T7:30"},
                          {"when": "2026-12-01T09:00Z"}, {"message": "   "}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.draft(**arguments)

    def test_rejects_ambiguous_or_nonexistent_local_time(self) -> None:
        for value in ("2018-02-17T23:30", "2018-11-04T00:30"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                facebook_drafts.local_time(value)

    def test_rejects_conflicting_metadata(self) -> None:
        source = self.article.read_text(encoding="utf-8")
        source = source.replace("</head>", "<meta property='og:title' content='Outro título'></head>")
        self.article.write_text(source, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "og:title"):
            self.draft()

    def test_allows_identical_metadata_repeated_in_head(self) -> None:
        source = self.article.read_text(encoding="utf-8")
        source = source.replace("</head>", "<meta property='article:published_time' content='2026-11-30'></head>")
        self.article.write_text(source, encoding="utf-8")
        facebook_drafts.verify(self.draft(), self.root)

    def test_rejects_external_or_unsafe_image_paths(self) -> None:
        original = self.article.read_text(encoding="utf-8")
        valid = "https://retro.caracore.com.br/articles/assets/img/capa.png"
        for url in ("https://example.com/capa.png",
                    "https://retro.caracore.com.br/articles/assets/img/../capa.png",
                    "https://retro.caracore.com.br/articles/assets/img/capa.png?versao=2",
                    "https://retro.caracore.com.br.evil.example/articles/assets/img/capa.png"):
            with self.subTest(url=url):
                self.article.write_text(original.replace(valid, url), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "imagem deve"):
                    self.draft()

    def test_rejects_article_url_pointing_elsewhere(self) -> None:
        source = self.article.read_text(encoding="utf-8")
        source = source.replace("2026_11_30_article_109.html'", "outro.html'")
        self.article.write_text(source, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "link do artigo"):
            self.draft()

    def test_command_prepares_a_real_article_without_publishing(self) -> None:
        result = subprocess.run(
            [sys.executable, str(facebook_drafts.ROOT / "tools" / "facebook_drafts.py"),
             "preparar", "--artigo", "109", "--pagina", "123456", "--quando", "2026-12-01T09:00"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        draft = json.loads(result.stdout)
        self.assertEqual(draft["estado"], "RASCUNHO_NAO_APROVADO")
        self.assertEqual(draft["conteudo"]["pagina_id"], "123456")
        facebook_drafts.verify(draft)
        saved = self.root / "rascunho.json"
        saved.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, str(facebook_drafts.ROOT / "tools" / "facebook_drafts.py"),
                   "verificar", str(saved)]
        checked = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(checked.returncode, 0)
        self.assertIn("ainda nao aprovado nem publicado", checked.stdout)
        draft["conteudo"]["mensagem"] += " Texto alterado."
        saved.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        changed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn("conteudo mudou", changed.stderr)


if __name__ == "__main__":
    unittest.main()
