#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sala de Notícias — Script 5: Validar a entrega dentro da sala gram (Instagram).
Verifica se os artefatos em gram/artefatos/ estão no padrão e com nomes corretos.
Mensagens amigáveis para reportar via WhatsApp, Telegram ou e-mail.

Uso: python sala/scripts/validar_entrega_gram.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validar_sala
from sala_common import mensagem_amigavel_erro, mensagem_amigavel_ok

SCRIPT_NOME = "validar_entrega_gram.py (Script 5 — Validar entrega Gram)"


def main() -> int:
    try:
        validar_sala.ERRORS.clear()
        validar_sala.WARNINGS.clear()
        validar_sala.check_gram()

        if validar_sala.ERRORS:
            print()
            msg = mensagem_amigavel_erro(
                "A validação da sala Gram (Instagram) encontrou erros.",
                " ".join(validar_sala.ERRORS[:2]),
                SCRIPT_NOME,
            )
            print(msg, file=sys.stderr)
            return 1
        print(mensagem_amigavel_ok("Entrega Gram (Instagram) OK.", "Artefatos e nomes no padrão."))
        return 0
    except Exception as e:
        print(mensagem_amigavel_erro("Erro ao validar entrega Gram.", str(e), SCRIPT_NOME), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
