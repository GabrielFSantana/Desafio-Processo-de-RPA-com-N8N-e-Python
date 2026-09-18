# =============================================================================
# CODE NODE DO N8N  ->  "Python - Analisar Servidor"
# -----------------------------------------------------------------------------
# Onde colar:  node Code  >  Language: Python (Beta)  >  Mode: Run Once for All Items
# Este arquivo e uma versao AUTOCONTIDA de python/analisar_servidor.py.
# Nao ha import de arquivo local porque o Code node roda em sandbox (Pyodide).
#
# ENTRADA esperada (vinda do node Webhook):  $json.body  ->  { servidor, cpu, memoria, disco, servico }
# SAIDA: 1 item com o diagnostico completo, incluindo o campo "mensagem" ja formatado.
# =============================================================================

from datetime import datetime, timezone

LIMIARES = {
    "cpu": {"alerta": 80, "critico": 90},
    "memoria": {"alerta": 80, "critico": 90},
    "disco": {"alerta": 80, "critico": 90},
}

ESTADO_SERVICO = {
    "online": "NORMAL", "running": "NORMAL", "ativo": "NORMAL",
    "degradado": "ALERTA", "degraded": "ALERTA", "lento": "ALERTA",
    "offline": "CRITICO", "parado": "CRITICO", "stopped": "CRITICO",
    "error": "CRITICO", "falha": "CRITICO",
}

PESO_STATUS = {"NORMAL": 0, "ALERTA": 1, "CRITICO": 2}
ROTULO = {"cpu": "CPU", "memoria": "memoria RAM", "disco": "disco"}

ACOES = {
    "disco": {
        "CRITICO": "Verificar espaco disponivel e realizar limpeza do servidor (logs antigos, dumps, imagens temporarias). Avaliar expansao do volume.",
        "ALERTA": "Monitorar o crescimento do disco e agendar limpeza preventiva de logs e arquivos temporarios.",
    },
    "memoria": {
        "CRITICO": "Identificar os processos com maior consumo de RAM, avaliar restart do servico e revisar limites de memoria do container.",
        "ALERTA": "Acompanhar o consumo de memoria e revisar cache/pool de conexoes da aplicacao.",
    },
    "cpu": {
        "CRITICO": "Analisar processos em loop ou consultas pesadas, avaliar escalonamento horizontal e revisar jobs agendados no horario.",
        "ALERTA": "Acompanhar a carga de CPU e verificar se ha rotina/relatorio pesado em execucao no momento.",
    },
    "servico": {
        "CRITICO": "Servico indisponivel: reiniciar o servico, checar logs da aplicacao e abrir chamado de incidente imediatamente.",
        "ALERTA": "Servico degradado: verificar tempo de resposta, fila de requisicoes e dependencias externas.",
    },
}

CAMPOS = ("servidor", "cpu", "memoria", "disco", "servico")


def para_numero(valor, campo):
    if isinstance(valor, bool):
        raise ValueError("Campo '" + campo + "' nao pode ser booleano.")
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        limpo = str(valor).strip().replace("%", "").replace(",", ".")
        try:
            numero = float(limpo)
        except ValueError:
            raise ValueError("Campo '" + campo + "' nao e numerico: " + str(valor))
    if numero < 0 or numero > 100:
        raise ValueError("Campo '" + campo + "' deve estar entre 0 e 100.")
    return numero


def analisar(dados):
    faltando = [c for c in CAMPOS if c not in dados or dados[c] in (None, "")]
    if faltando:
        raise ValueError("Campos obrigatorios ausentes: " + ", ".join(faltando))

    metricas = {
        "servidor": str(dados["servidor"]).strip(),
        "cpu": para_numero(dados["cpu"], "cpu"),
        "memoria": para_numero(dados["memoria"], "memoria"),
        "disco": para_numero(dados["disco"], "disco"),
        "servico": str(dados["servico"]).strip().lower(),
    }

    ocorrencias = []
    for recurso in ("disco", "memoria", "cpu"):
        valor = metricas[recurso]
        lim = LIMIARES[recurso]
        if valor >= lim["critico"]:
            nivel, limite = "CRITICO", lim["critico"]
        elif valor >= lim["alerta"]:
            nivel, limite = "ALERTA", lim["alerta"]
        else:
            continue
        ocorrencias.append((nivel, recurso, "Utilizacao de " + ROTULO[recurso] +
                            " em " + str(int(valor)) + "% (limite " + nivel.lower() +
                            ": " + str(limite) + "%)"))

    nivel_servico = ESTADO_SERVICO.get(metricas["servico"], "CRITICO")
    if nivel_servico != "NORMAL":
        ocorrencias.append((nivel_servico, "servico",
                            "Servico reportado como '" + metricas["servico"] + "'"))

    if not ocorrencias:
        status = "NORMAL"
        motivo = "Todos os recursos monitorados estao dentro dos limites aceitaveis."
        acao = "Nenhuma acao necessaria. Manter o monitoramento de rotina."
        afetados = []
    else:
        status = max([o[0] for o in ocorrencias], key=lambda s: PESO_STATUS[s])
        piores = [o for o in ocorrencias if o[0] == status]
        motivo = "; ".join([o[2] for o in piores]) + "."
        acao = " ".join([ACOES[o[1]][status] for o in piores])
        afetados = [o[1] for o in piores]

    r = {
        "servidor": metricas["servidor"],
        "status": status,
        "motivo": motivo,
        "acao_recomendada": acao,
        "recursos_afetados": afetados,
        "prioridade": {"NORMAL": "P4", "ALERTA": "P2", "CRITICO": "P1"}[status],
        "notificar": status != "NORMAL",
        "metricas": metricas,
        "analisado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versao_regras": "1.0.0",
    }

    titulo = "ALERTA DE MONITORAMENTO" if status != "NORMAL" else "RELATORIO DE MONITORAMENTO"
    r["mensagem"] = (
        titulo + "\n"
        "Servidor: " + r["servidor"] + "\n"
        "Status: " + r["status"] + "\n"
        "CPU: " + str(int(metricas["cpu"])) + "%\n"
        "Memoria: " + str(int(metricas["memoria"])) + "%\n"
        "Disco: " + str(int(metricas["disco"])) + "%\n"
        "Servico: " + metricas["servico"] + "\n\n"
        "Problema identificado:\n" + r["motivo"] + "\n\n"
        "Acao recomendada:\n" + r["acao_recomendada"] + "\n\n"
        "Prioridade: " + r["prioridade"] + " | Analisado em (UTC): " + r["analisado_em"]
    )
    return r


# ---------------------------------------------------------------------------
# Ponte com o N8N
# ---------------------------------------------------------------------------
saida = []

for item in _input.all():
    dados = item.json.to_py()          # JsProxy -> dict Python
    corpo = dados.get("body", dados)   # o Webhook entrega o payload dentro de "body"
    try:
        saida.append({"json": analisar(corpo)})
    except Exception as erro:
        saida.append({"json": {
            "status": "ERRO",
            "servidor": corpo.get("servidor", "desconhecido"),
            "motivo": str(erro),
            "acao_recomendada": "Corrigir o payload enviado ao webhook e reenviar.",
            "notificar": False,
        }})

return saida
