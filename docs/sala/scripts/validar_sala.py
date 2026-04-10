#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sala de Notícias — Script único de validação.
Verifica se o trabalho foi executado com sucesso: face (F), gram (G), retro (LinkedIn depois do 86).
Usar Python baseline (versão correta do Windows Store). Rodar no final da sessão.

Uso: python scripts/validar_sala.py   ou   py scripts/validar_sala.py
      (a partir da raiz do repositório onde estão sala/, face/, gram/, retro/)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Raiz do repositório: pasta que contém sala/, face/, gram/, retro/
SCRIPT_DIR = Path(__file__).resolve().parent
SALA_DIR = SCRIPT_DIR.parent
REPO_ROOT = SALA_DIR.parent

# Pastas por rede (automação)
FACE_DIR = REPO_ROOT / "face"
GRAM_DIR = REPO_ROOT / "gram"
RETRO_DIR = REPO_ROOT / "retro"
SALA_ASSETS_IMG = SALA_DIR / "assets" / "img"

# Padrões de nome
RE_DATE = re.compile(r"^\d{4}_\d{2}_\d{2}_")
RE_FACE_HTML = re.compile(r"^\d{4}_\d{2}_\d{2}_.+_\(\d+\)_F\.html$")
RE_GRAM_HTML = re.compile(r"^\d{4}_\d{2}_\d{2}_.+_\(\d+\)_G\.html$")
RE_ARTICLE_HTML = re.compile(r"^\d{4}_\d{2}_\d{2}_article_(\d+)\.html$")
RE_LINKEDIN_L_HTML = re.compile(r"^\d{4}_\d{2}_\d{2}_.+_\((\d+)\)_L\.html$")
RE_IMG_PNG = re.compile(r"^\d{4}_\d{2}_\d{2}_.+_\(\d+\)_\(\d+\)\.png$")
RE_ARTICLE_IMG = re.compile(r"^\d{4}_\d{2}_\d{2}_.+_\((\d+)\)_\(\d+\)\.png$")

ERRORS: list[str] = []
WARNINGS: list[str] = []


def log_err(msg: str) -> None:
    ERRORS.append(msg)
    print(f"  [ERRO] {msg}", file=sys.stderr)


def log_warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"  [AVISO] {msg}", file=sys.stderr)


def check_face() -> None:
    """Facebook (F): face/artefatos/ com *_F.html; imagens em sala/assets/img/."""
    if not FACE_DIR.is_dir():
        log_err(f"Pasta face não encontrada: {FACE_DIR}")
        return
    artefatos_dir = FACE_DIR / "artefatos"
    if not artefatos_dir.is_dir():
        log_warn(f"Pasta face/artefatos/ não existe: {artefatos_dir}")
        return
    htmls = list(artefatos_dir.glob("*.html"))
    for p in htmls:
        if not RE_FACE_HTML.match(p.name):
            log_err(f"Face: nome fora do padrão (esperado YYYY_MM_DD_*_(nn)_F.html): {p.name}")
    # Listagem face/facebook.html existe
    listagem = FACE_DIR / "facebook.html"
    if not listagem.is_file():
        log_warn(f"Face: listagem não encontrada: {listagem}")


def check_gram() -> None:
    """Instagram (G): gram/artefatos/ com *_G.html."""
    if not GRAM_DIR.is_dir():
        log_err(f"Pasta gram não encontrada: {GRAM_DIR}")
        return
    artefatos_dir = GRAM_DIR / "artefatos"
    if not artefatos_dir.is_dir():
        log_warn(f"Pasta gram/artefatos/ não existe: {artefatos_dir}")
        return
    htmls = list(artefatos_dir.glob("*.html"))
    for p in htmls:
        if not RE_GRAM_HTML.match(p.name):
            log_err(f"Gram: nome fora do padrão (esperado YYYY_MM_DD_*_(nn)_G.html): {p.name}")
    listagem = GRAM_DIR / "instagram.html"
    if not listagem.is_file():
        log_warn(f"Gram: listagem não encontrada: {listagem}")


def check_retro() -> None:
    """LinkedIn (retro): retro/articles/ com article_87 em diante."""
    if not RETRO_DIR.is_dir():
        log_err(f"Pasta retro não encontrada: {RETRO_DIR}")
        return
    articles_dir = RETRO_DIR / "articles"
    if not articles_dir.is_dir():
        log_warn(f"Pasta retro/articles/ não existe: {articles_dir}")
        return
    htmls = list(articles_dir.glob("*.html"))
    for p in htmls:
        m = RE_ARTICLE_HTML.match(p.name)
        if m:
            num = int(m.group(1))
            # article 11–86 e 87+ são válidos; 87+ é continuidade LinkedIn
        # Nomes tipo 2026_02_12_article_72.html são válidos
    listagem = RETRO_DIR / "articles.html"
    if not listagem.is_file():
        log_warn(f"Retro: listagem não encontrada: {listagem}")


def check_sala_assets() -> None:
    """Pasta sala/assets/img/ existe para imagens geradas pela IA."""
    if not SALA_ASSETS_IMG.is_dir():
        log_warn(f"Pasta de imagens não existe: {SALA_ASSETS_IMG}")


def check_html_prompt_box(html_path: Path) -> bool:
    """Verifica se o HTML contém caixa de prompt (Texto para colar na IA ou prompt-box)."""
    try:
        text = html_path.read_text(encoding="utf-8", errors="replace")
        return (
            "Texto para colar na IA" in text
            or "texto para colar na ia" in text.lower()
            or "prompt-box" in text
            or 'class="prompt-box"' in text
        )
    except Exception:
        return False


def main() -> int:
    print("Sala de Notícias — Validação face (F), gram (G), retro (LinkedIn depois do 86)")
    print(f"Repositório: {REPO_ROOT}")
    print()

    check_face()
    check_gram()
    check_retro()
    check_sala_assets()

    # Opcional: verificar presença de caixa de prompt em HTMLs de artefato
    for artefatos_dir, pattern in [
        (FACE_DIR / "artefatos", "*_F.html"),
        (GRAM_DIR / "artefatos", "*_G.html"),
    ]:
        if artefatos_dir.is_dir():
            for p in artefatos_dir.glob(pattern):
                if not check_html_prompt_box(p):
                    log_warn(f"Artefato sem caixa 'Texto para colar na IA': {p.name}")

    if ERRORS:
        print()
        print("Corrija os erros acima e rode o script novamente.")
        return 1
    if WARNINGS:
        print()
        print("Validação concluída com avisos (nenhum erro bloqueante).")
        return 0
    print()
    print("Validação OK. Trabalho executado com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
