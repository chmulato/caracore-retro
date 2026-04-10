#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sala de Notícias — Script 6: Validar a entrega dentro da sala retro (LinkedIn).
Verifica se os articles em retro/articles/ estão no padrão (LinkedIn depois do 86).
Mensagens amigáveis para reportar via WhatsApp, Telegram ou e-mail.

Uso: python sala/scripts/validar_entrega_retro.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validar_sala
from sala_common import mensagem_amigavel_erro, mensagem_amigavel_ok

SCRIPT_NOME = "validar_entrega_retro.py (Script 6 — Validar entrega Retro)"


def main() -> int:
    try:
        validar_sala.ERRORS.clear()
        validar_sala.WARNINGS.clear()
        validar_sala.check_retro()

        if validar_sala.ERRORS:
            print()
            msg = mensagem_amigavel_erro(
                "A validação da sala Retro (LinkedIn) encontrou erros.",
                " ".join(validar_sala.ERRORS[:2]),
                SCRIPT_NOME,
            )
            print(msg, file=sys.stderr)
            return 1
        print(mensagem_amigavel_ok("Entrega Retro (LinkedIn) OK.", "Articles e nomes no padrão."))
        return 0
    except Exception as e:
        print(mensagem_amigavel_erro("Erro ao validar entrega Retro.", str(e), SCRIPT_NOME), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
