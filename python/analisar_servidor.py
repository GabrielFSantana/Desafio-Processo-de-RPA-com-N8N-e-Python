#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_servidor.py
--------------------
Motor de analise de saude de servidores usado pelo RPA de monitoramento (N8N + Python).

Recebe um JSON com as metricas coletadas de um servidor, aplica as regras de
negocio de infraestrutura e devolve um JSON classificando o servidor em
NORMAL, ALERTA ou CRITICO, com motivo e acao recomendada.

Modos de uso
------------
1) Argumento na linha de comando (usado pelo node "Execute Command" do N8N):
       python3 analisar_servidor.py '{"servidor":"SRV-PACS-01","cpu":72,...}'

2) Entrada padrao (stdin) - util para pipes e testes locais:
       cat examples/servidor_critico.json | python3 analisar_servidor.py

3) Como biblioteca (usado pelos testes e pelo Code node do N8N):
       from analisar_servidor import analisar
       resultado = analisar({"servidor": "SRV-PACS-01", "cpu": 72, ...})

Codigos de saida
----------------
0 = analise concluida (independente do status do servidor)
1 = payload invalido (JSON malformado ou campos obrigatorios ausentes)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# 1. Limiares (thresholds) - centralizados para facilitar tunning por ambiente
# ---------------------------------------------------------------------------
# Regra geral de mercado para capacity planning:
#   < 80%  -> operacao saudavel
#   >= 80% -> zona de atencao (o recurso tende a saturar)
#   >= 90% -> saturacao iminente / degradacao ja perceptivel
LIMIARES = {
    "cpu": {"alerta": 80, "critico": 90},
    "memoria": {"alerta": 80, "critico": 90},
    "disco": {"alerta": 80, "critico": 90},
}

# Como cada valor do campo "servico" e interpretado.
# Qualquer valor nao mapeado e tratado como CRITICO (fail-safe).
ESTADO_SERVICO = {
    "online": "NORMAL",
    "running": "NORMAL",
    "ativo": "NORMAL",
    "degradado": "ALERTA",
    "degraded": "ALERTA",
    "lento": "ALERTA",
    "offline": "CRITICO",
    "parado": "CRITICO",
    "stopped": "CRITICO",
    "error": "CRITICO",
    "falha": "CRITICO",
}

# Peso de cada status, usado para descobrir o "pior" nivel encontrado.
PESO_STATUS = {"NORMAL": 0, "ALERTA": 1, "CRITICO": 2}

# Acao recomendada para o operador, por recurso e por severidade.
ACOES = {
    "disco": {
        "CRITICO": "Verificar espaco disponivel e realizar limpeza do servidor "
                   "(logs antigos, dumps, imagens temporarias). Avaliar expansao do volume.",
        "ALERTA": "Monitorar o crescimento do disco e agendar limpeza preventiva "
                  "de logs e arquivos temporarios.",
    },
    "memoria": {
        "CRITICO": "Identificar os processos com maior consumo de RAM, avaliar "
                   "restart do servico e revisar limites de memoria do container.",
        "ALERTA": "Acompanhar o consumo de memoria e revisar cache/pool de conexoes "
                  "da aplicacao.",
    },
    "cpu": {
        "CRITICO": "Analisar processos em loop ou consultas pesadas, avaliar escalonamento "
                   "horizontal e revisar jobs agendados no horario.",
        "ALERTA": "Acompanhar a carga de CPU e verificar se ha rotina/relatorio pesado "
                  "em execucao no momento.",
    },
    "servico": {
        "CRITICO": "Servico indisponivel: reiniciar o servico, checar logs da aplicacao "
                   "e abrir chamado de incidente imediatamente.",
        "ALERTA": "Servico degradado: verificar tempo de resposta, fila de requisicoes "
                  "e dependencias externas.",
    },
}

ACAO_NORMAL = "Nenhuma acao necessaria. Manter o monitoramento de rotina."

CAMPOS_OBRIGATORIOS = ("servidor", "cpu", "memoria", "disco", "servico")

ROTULO_RECURSO = {"cpu": "CPU", "memoria": "memoria RAM", "disco": "disco"}


# ---------------------------------------------------------------------------
# 2. Validacao e normalizacao da entrada
# ---------------------------------------------------------------------------
class PayloadInvalido(ValueError):
    """Erro de payload: campo ausente ou valor fora do formato esperado."""


def _para_numero(valor, campo: str) -> float:
    """Converte para float aceitando '93', '93%', 93 e 93.4."""
    if isinstance(valor, bool):
        raise PayloadInvalido(f"Campo '{campo}' nao pode ser booleano.")
    if isinstance(valor, (int, float)):
        numero = float(valor)
    elif isinstance(valor, str):
        limpo = valor.strip().replace("%", "").replace(",", ".")
        try:
            numero = float(limpo)
        except ValueError:
            raise PayloadInvalido(f"Campo '{campo}' nao e numerico: {valor!r}")
    else:
        raise PayloadInvalido(f"Campo '{campo}' tem tipo invalido: {type(valor).__name__}")

    if not 0 <= numero <= 100:
        raise PayloadInvalido(f"Campo '{campo}' deve estar entre 0 e 100 (recebido: {numero})")
    return numero


def normalizar(dados: dict) -> dict:
    """Valida os campos obrigatorios e devolve o payload normalizado."""
    if not isinstance(dados, dict):
        raise PayloadInvalido("O payload precisa ser um objeto JSON.")

    faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in dados or dados[c] in (None, "")]
    if faltando:
        raise PayloadInvalido("Campos obrigatorios ausentes: " + ", ".join(faltando))

    return {
        "servidor": str(dados["servidor"]).strip(),
        "cpu": _para_numero(dados["cpu"], "cpu"),
        "memoria": _para_numero(dados["memoria"], "memoria"),
        "disco": _para_numero(dados["disco"], "disco"),
        "servico": str(dados["servico"]).strip().lower(),
    }


# ---------------------------------------------------------------------------
# 3. Regras de classificacao
# ---------------------------------------------------------------------------
def _classificar_recurso(recurso: str, valor: float) -> str:
    limites = LIMIARES[recurso]
    if valor >= limites["critico"]:
        return "CRITICO"
    if valor >= limites["alerta"]:
        return "ALERTA"
    return "NORMAL"


def _classificar_servico(servico: str) -> str:
    return ESTADO_SERVICO.get(servico, "CRITICO")


def analisar(dados: dict) -> dict:
    """
    Recebe o payload bruto do webhook e devolve o diagnostico completo.

    Estrategia: cada dimensao (cpu, memoria, disco, servico) e classificada
    isoladamente; o status final do servidor e o PIOR nivel encontrado, e o
    motivo agrega todas as ocorrencias daquele nivel.
    """
    metricas = normalizar(dados)

    ocorrencias = []  # [(status, recurso, texto_do_motivo)]

    for recurso in ("disco", "memoria", "cpu"):  # ordem = prioridade de exibicao
        valor = metricas[recurso]
        status_recurso = _classificar_recurso(recurso, valor)
        if status_recurso != "NORMAL":
            limite = LIMIARES[recurso]["critico" if status_recurso == "CRITICO" else "alerta"]
            ocorrencias.append((
                status_recurso,
                recurso,
                f"Utilizacao de {ROTULO_RECURSO[recurso]} em {valor:.0f}% "
                f"(limite {status_recurso.lower()}: {limite}%)",
            ))

    status_servico = _classificar_servico(metricas["servico"])
    if status_servico != "NORMAL":
        ocorrencias.append((
            status_servico,
            "servico",
            f"Servico reportado como '{metricas['servico']}'",
        ))

    if not ocorrencias:
        status_final = "NORMAL"
        motivo = "Todos os recursos monitorados estao dentro dos limites aceitaveis."
        acao = ACAO_NORMAL
        recursos_afetados = []
    else:
        status_final = max((o[0] for o in ocorrencias), key=lambda s: PESO_STATUS[s])
        criticas = [o for o in ocorrencias if o[0] == status_final]
        motivo = "; ".join(o[2] for o in criticas) + "."
        acao = " ".join(ACOES[o[1]][status_final] for o in criticas)
        recursos_afetados = [o[1] for o in criticas]

    resultado = {
        "servidor": metricas["servidor"],
        "status": status_final,
        "motivo": motivo,
        "acao_recomendada": acao,
        "recursos_afetados": recursos_afetados,
        "prioridade": {"NORMAL": "P4", "ALERTA": "P2", "CRITICO": "P1"}[status_final],
        "notificar": status_final != "NORMAL",
        "metricas": {
            "cpu": metricas["cpu"],
            "memoria": metricas["memoria"],
            "disco": metricas["disco"],
            "servico": metricas["servico"],
        },
        "analisado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versao_regras": __version__,
    }
    resultado["mensagem"] = montar_mensagem(resultado)
    return resultado


# ---------------------------------------------------------------------------
# 4. Mensagem pronta para notificacao (e-mail / Telegram)
# ---------------------------------------------------------------------------
def montar_mensagem(r: dict) -> str:
    """Monta o texto da notificacao exatamente no formato exigido pelo desafio."""
    m = r["metricas"]
    titulo = "ALERTA DE MONITORAMENTO" if r["status"] != "NORMAL" else "RELATORIO DE MONITORAMENTO"
    return (
        f"{titulo}\n"
        f"Servidor: {r['servidor']}\n"
        f"Status: {r['status']}\n"
        f"CPU: {m['cpu']:.0f}%\n"
        f"Memoria: {m['memoria']:.0f}%\n"
        f"Disco: {m['disco']:.0f}%\n"
        f"Servico: {m['servico']}\n\n"
        f"Problema identificado:\n{r['motivo']}\n\n"
        f"Acao recomendada:\n{r['acao_recomendada']}\n\n"
        f"Prioridade: {r['prioridade']} | Analisado em (UTC): {r['analisado_em']}"
    )


# ---------------------------------------------------------------------------
# 5. CLI
# ---------------------------------------------------------------------------
def _ler_entrada(argv) -> str:
    if len(argv) > 1 and argv[1].strip():
        return argv[1]
    return sys.stdin.read()


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    bruto = _ler_entrada(argv)

    try:
        payload = json.loads(bruto)
    except (json.JSONDecodeError, TypeError) as exc:
        print(json.dumps({"erro": "JSON invalido", "detalhe": str(exc)}, ensure_ascii=False))
        return 1

    # Aceita tanto {"servidor": ...} quanto o formato do N8N {"body": {"servidor": ...}}
    if isinstance(payload, dict) and "body" in payload and isinstance(payload["body"], dict):
        payload = payload["body"]

    try:
        resultado = analisar(payload)
    except PayloadInvalido as exc:
        print(json.dumps({"erro": "Payload invalido", "detalhe": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
