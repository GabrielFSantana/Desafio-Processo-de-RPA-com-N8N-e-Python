#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_workflow.py
-----------------
Gera workflow/monitoramento-servidor.json, o arquivo que voce importa no N8N.

Manter o workflow gerado por script evita JSON editado na mao (e quebrado na
mao). Se voce mudar a URL da API ou os e-mails, edite as constantes abaixo e
rode de novo:

    python3 docs/gerar_workflow.py
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "workflow", "monitoramento-servidor.json")

# --------------------------------------------------------------------------
# Configuracao
# --------------------------------------------------------------------------
URL_API = "http://127.0.0.1:8000/analisar"   # microsservico python/api_analise.py
# 127.0.0.1 em vez de localhost: no Windows o Node resolve "localhost" para o
# IPv6 ::1 e a API escuta em IPv4, o que gera ECONNREFUSED ::1:8000.
EMAIL_DE = "gabrielsantfelipe@gmail.com"     # remetente (mesma conta do SMTP)
EMAIL_PARA = "gabrielsantfelipe@gmail.com"   # equipe de infraestrutura


def cond(left, right, cid):
    return {
        "id": cid,
        "leftValue": left,
        "rightValue": right,
        "operator": {"type": "string", "operation": "equals", "name": "filter.operator.equals"},
    }


def regra(valor, cid):
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "",
                        "typeValidation": "strict", "version": 2},
            "conditions": [cond("={{ $json.status }}", valor, cid)],
            "combinator": "and",
        },
        "renameOutput": True,
        "outputKey": valor,
    }


workflow = {
    "name": "RPA - Monitoramento de Saude de Servidores",
    "nodes": [
        # ------------------------------------------------------------------ 1
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "monitoramento-servidor",
                "responseMode": "responseNode",
                "options": {},
            },
            "id": "a1000000-0000-4000-8000-000000000001",
            "name": "Webhook - Receber Metricas",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [-160, 300],
            "webhookId": "b7f1c2d3-4e5a-4b6c-8d7e-9f0a1b2c3d4e",
        },
        # ------------------------------------------------------------------ 2
        {
            "parameters": {
                "method": "POST",
                "url": URL_API,
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.body) }}",
                "options": {"response": {"response": {"neverError": True}}},
            },
            "id": "a1000000-0000-4000-8000-000000000002",
            "name": "Python - Analisar Servidor",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [100, 300],
            "onError": "continueRegularOutput",
        },
        # ------------------------------------------------------------------ 3
        {
            "parameters": {
                "rules": {
                    "values": [
                        regra("CRITICO", "c1000000-0000-4000-8000-000000000001"),
                        regra("ALERTA", "c1000000-0000-4000-8000-000000000002"),
                        regra("NORMAL", "c1000000-0000-4000-8000-000000000003"),
                    ]
                },
                "options": {"fallbackOutput": "extra", "renameFallbackOutput": "ERRO"},
            },
            "id": "a1000000-0000-4000-8000-000000000003",
            "name": "Switch - Classificar Status",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.2,
            "position": [360, 300],
        },
        # ------------------------------------------------------------------ 4
        {
            "parameters": {
                "fromEmail": EMAIL_DE,
                "toEmail": EMAIL_PARA,
                "subject": "=[P1 - CRITICO] {{ $json.servidor }} - acao imediata necessaria",
                "emailFormat": "text",
                "text": "={{ $json.mensagem }}",
                "options": {"appendAttribution": False},
            },
            "id": "a1000000-0000-4000-8000-000000000004",
            "name": "Email - Alerta CRITICO",
            "type": "n8n-nodes-base.emailSend",
            "typeVersion": 2.1,
            "position": [660, 100],
        },
        # ------------------------------------------------------------------ 5
        {
            "parameters": {
                "fromEmail": EMAIL_DE,
                "toEmail": EMAIL_PARA,
                "subject": "=[P2 - ALERTA] {{ $json.servidor }} - recurso proximo do limite",
                "emailFormat": "text",
                "text": "={{ $json.mensagem }}",
                "options": {"appendAttribution": False},
            },
            "id": "a1000000-0000-4000-8000-000000000005",
            "name": "Email - Aviso ALERTA",
            "type": "n8n-nodes-base.emailSend",
            "typeVersion": 2.1,
            "position": [660, 280],
        },
        # ------------------------------------------------------------------ 6
        {
            "parameters": {},
            "id": "a1000000-0000-4000-8000-000000000006",
            "name": "Sem Acao - Servidor Normal",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [660, 460],
        },
        # ------------------------------------------------------------------ 7
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ JSON.stringify($('Python - Analisar Servidor').item.json) }}",
                "options": {},
            },
            "id": "a1000000-0000-4000-8000-000000000007",
            "name": "Responder Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [940, 300],
        },
        # --------------------------------------------------------- anotacoes
        {
            "parameters": {
                "content": "## 1. Entrada\nPOST com JSON:\n```\n{\n  \"servidor\": \"SRV-CFTV-02\",\n  \"cpu\": 72,\n  \"memoria\": 84,\n  \"disco\": 93,\n  \"servico\": \"online\"\n}\n```\nO payload chega em `$json.body`.",
                "height": 300, "width": 300, "color": 4,
            },
            "id": "a1000000-0000-4000-8000-000000000008",
            "name": "Nota - Entrada",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [-260, -60],
        },
        {
            "parameters": {
                "content": "## 2. Analise em Python\nChama o microsservico\n`python/api_analise.py`\n(POST /analisar).\n\nRegras: >=80% ALERTA, >=90% CRITICO,\nservico != online -> CRITICO.\nO pior nivel encontrado vence.\n\n**A API precisa estar rodando.**",
                "height": 300, "width": 320, "color": 5,
            },
            "id": "a1000000-0000-4000-8000-000000000009",
            "name": "Nota - Python",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [80, -60],
        },
        {
            "parameters": {
                "content": "## 3. Roteamento e notificacao\nO Switch le `$json.status` e escolhe a saida.\nCRITICO e ALERTA disparam e-mail (SMTP).\nNORMAL segue direto para a resposta.\n\nConfigure a credencial SMTP nos dois\nnodes de e-mail antes de ativar.",
                "height": 300, "width": 360, "color": 3,
            },
            "id": "a1000000-0000-4000-8000-000000000010",
            "name": "Nota - Notificacao",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [620, -60],
        },
    ],
    "connections": {
        "Webhook - Receber Metricas": {
            "main": [[{"node": "Python - Analisar Servidor", "type": "main", "index": 0}]]
        },
        "Python - Analisar Servidor": {
            "main": [[{"node": "Switch - Classificar Status", "type": "main", "index": 0}]]
        },
        "Switch - Classificar Status": {
            "main": [
                [{"node": "Email - Alerta CRITICO", "type": "main", "index": 0}],
                [{"node": "Email - Aviso ALERTA", "type": "main", "index": 0}],
                [{"node": "Sem Acao - Servidor Normal", "type": "main", "index": 0}],
                [{"node": "Responder Webhook", "type": "main", "index": 0}],
            ]
        },
        "Email - Alerta CRITICO": {"main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]},
        "Email - Aviso ALERTA": {"main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]},
        "Sem Acao - Servidor Normal": {"main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]},
    },
    "settings": {"executionOrder": "v1"},
    "pinData": {},
    "meta": {"instanceId": "rpa-monitoramento-dio"},
    "tags": [],
}

os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
with open(DESTINO, "w", encoding="utf-8") as fh:
    json.dump(workflow, fh, ensure_ascii=False, indent=2)
    fh.write("\n")

print(f"OK -> {DESTINO} ({os.path.getsize(DESTINO)} bytes, {len(workflow['nodes'])} nodes)")
