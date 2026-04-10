# -*- coding: utf-8 -*-
"""
Sala de Notícias — Código compartilhado pelos 6 scripts (robôs).
Caminhos, planilha, mensagens amigáveis para reportar via WhatsApp/Telegram/e-mail.
"""
from __future__ import annotations

import csv
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SALA_DIR = SCRIPT_DIR.parent
REPO_ROOT = SALA_DIR.parent

FACE_DIR = REPO_ROOT / "face"
GRAM_DIR = REPO_ROOT / "gram"
RETRO_DIR = REPO_ROOT / "retro"
SALA_ASSETS_IMG = SALA_DIR / "assets" / "img"

PLANILHA_PATH = SALA_DIR / "planilha_sala.csv"
TRABALHO_DO_DIA_PATH = SALA_DIR / "regis" / "trabalho_do_dia.txt"
CONFIG_PATH = SALA_DIR / "regis" / "config_sala.txt"

ENCODING = "utf-8"
CSV_DELIM = ";"

# Cabeçalho da planilha (descrição da tarefa, trabalho feito, horas, total, acumulado CC)
PLANILHA_HEADER = [
    "data",
    "tarefa_do_dia",
    "trabalho_feito",
    "horas_previstas",
    "horas_trabalhadas",
    "valor_sessao_cc",
    "acumulado_cc",
    "inicio_sessao",
    "fim_sessao",
]


def mensagem_amigavel_erro(titulo: str, detalhe: str, script: str) -> str:
    """Mensagem pronta para copiar e enviar no WhatsApp, Telegram ou e-mail da Cara Core."""
    return (
        f"[Sala de Notícias]\n"
        f"Script: {script}\n"
        f"O que aconteceu: {titulo}\n"
        f"Detalhe: {detalhe}\n"
        f"Por favor, verifique ou avise a equipe."
    )


def mensagem_amigavel_ok(titulo: str, detalhe: str) -> str:
    """Mensagem de sucesso para reportar na sala."""
    return f"[Sala de Notícias] {titulo}\n{detalhe}"


def garantir_planilha_existe() -> None:
    """Cria planilha com cabeçalho se não existir."""
    if not PLANILHA_PATH.exists():
        PLANILHA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PLANILHA_PATH, "w", encoding=ENCODING, newline="") as f:
            w = csv.writer(f, delimiter=CSV_DELIM)
            w.writerow(PLANILHA_HEADER)


def ler_linhas_planilha() -> list[dict]:
    """Lê todas as linhas da planilha como lista de dicionários."""
    garantir_planilha_existe()
    with open(PLANILHA_PATH, "r", encoding=ENCODING, newline="") as f:
        r = csv.DictReader(f, delimiter=CSV_DELIM)
        return list(r)


def escrever_planilha(linhas: list[dict]) -> None:
    """Escreve a planilha com as linhas (cada dict com chaves = PLANILHA_HEADER)."""
    garantir_planilha_existe()
    with open(PLANILHA_PATH, "w", encoding=ENCODING, newline="") as f:
        w = csv.DictWriter(f, fieldnames=PLANILHA_HEADER, delimiter=CSV_DELIM)
        w.writeheader()
        for row in linhas:
            w.writerow({k: row.get(k, "") for k in PLANILHA_HEADER})


def ultimo_acumulado_cc() -> float:
    """Retorna o último valor de acumulado_cc da planilha (0 se vazio)."""
    linhas = ler_linhas_planilha()
    if not linhas:
        return 0.0
    for row in reversed(linhas):
        try:
            return float(str(row.get("acumulado_cc", "0")).replace(",", "."))
        except ValueError:
            continue
    return 0.0


def abrir_sala_no_navegador() -> None:
    """Abre a Sala de Notícias (index ou opera-sala) no navegador padrão."""
    url = SALA_DIR / "opera-sala.html"
    if not url.exists():
        url = SALA_DIR / "index.htm"
    webbrowser.open(url.as_uri())


def ler_trabalho_do_dia() -> str:
    """Lê a descrição do trabalho do dia em regis/trabalho_do_dia.txt."""
    if TRABALHO_DO_DIA_PATH.exists():
        return TRABALHO_DO_DIA_PATH.read_text(encoding=ENCODING).strip()
    return "Publicar artefatos conforme plano da semana (Face, Gram ou Retro). Copiar texto, gerar imagens na IA, salvar com nome correto."


def ler_valor_hora_cc() -> float:
    """Lê valor por hora em dinheiro CC em regis/config_sala.txt (linha valor_hora_cc=...)."""
    if not CONFIG_PATH.exists():
        return 0.0
    for line in CONFIG_PATH.read_text(encoding=ENCODING).splitlines():
        line = line.strip()
        if line.startswith("valor_hora_cc="):
            try:
                return float(line.split("=", 1)[1].strip().replace(",", "."))
            except ValueError:
                return 0.0
    return 0.0


def agora_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def hoje() -> str:
    return datetime.now().strftime("%Y-%m-%d")
