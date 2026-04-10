#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sala de Notícias — Script 1: Iniciar o trabalho do dia.
Abre a sala no navegador, apresenta o trabalho do dia e as horas a executar,
e atualiza a planilha (início da sessão) de forma transparente.

Uso: python sala/scripts/iniciar_trabalho.py
Mensagens de erro são amigáveis para reportar via WhatsApp, Telegram ou e-mail da Cara Core.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permite importar sala_common
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sala_common import (
    PLANILHA_HEADER,
    abrir_sala_no_navegador,
    agora_iso,
    garantir_planilha_existe,
    hoje,
    ler_linhas_planilha,
    ler_trabalho_do_dia,
    mensagem_amigavel_erro,
    ultimo_acumulado_cc,
    escrever_planilha,
)


def main() -> int:
    script_nome = "iniciar_trabalho.py (Script 1 — Iniciar trabalho)"
    try:
        tarefa = ler_trabalho_do_dia()
        horas_previstas = "1"  # padrão; pode vir de config depois
        acumulado = ultimo_acumulado_cc()

        # Nova linha na planilha: início da sessão
        linhas = ler_linhas_planilha()
        nova_linha = {k: "" for k in PLANILHA_HEADER}
        nova_linha["data"] = hoje()
        nova_linha["tarefa_do_dia"] = tarefa
        nova_linha["horas_previstas"] = horas_previstas
        nova_linha["acumulado_cc"] = str(acumulado).replace(".", ",")
        nova_linha["inicio_sessao"] = agora_iso()
        linhas.append(nova_linha)
        escrever_planilha(linhas)

        # Abre a sala no navegador
        abrir_sala_no_navegador()

        print("=" * 60)
        print("SALA DE NOTÍCIAS — Início do trabalho registrado")
        print("=" * 60)
        print()
        print("Trabalho do dia:")
        print("  ", tarefa[:200] + "..." if len(tarefa) > 200 else "  " + tarefa)
        print()
        print("Horas a executar (previstas):", horas_previstas)
        print("Início da sessão:", nova_linha["inicio_sessao"])
        print("Acumulado CC até agora:", acumulado)
        print()
        print("A planilha foi atualizada. A sala foi aberta no navegador.")
        print("Ao terminar, use o script que valida e encerra o trabalho.")
        print("=" * 60)
        return 0

    except FileNotFoundError as e:
        msg = mensagem_amigavel_erro(
            "Arquivo não encontrado.",
            str(e),
            script_nome,
        )
        print(msg, file=sys.stderr)
        return 1
    except PermissionError as e:
        msg = mensagem_amigavel_erro(
            "Sem permissão para escrever na planilha ou abrir a pasta.",
            str(e),
            script_nome,
        )
        print(msg, file=sys.stderr)
        return 1
    except Exception as e:
        msg = mensagem_amigavel_erro(
            "Algo inesperado aconteceu ao iniciar o trabalho.",
            str(e),
            script_nome,
        )
        print(msg, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
