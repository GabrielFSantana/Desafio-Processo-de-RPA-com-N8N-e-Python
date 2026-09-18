#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_workflow.py
-----------------
Gera workflow/monitoramento-servidor.json a partir de python/code_node_n8n.py.

Assim o codigo Python do Code node fica versionado em UM lugar so: se voce
editar as regras em python/code_node_n8n.py, basta rodar

    python3 docs/gerar_workflow.py

para o JSON importavel no N8N ficar sincronizado.
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_NODE = os.path.join(RAIZ, "python", "code_node_n8n.py")
DESTINO = os.path.join(RAIZ, "workflow", "monitoramento-servidor.json")

with open(CODE_NODE, "r", encoding="utf-8") as fh:
    python_code = fh.read()


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
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
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
            "position": [-80, 300],
            "webhookId": "b7f1c2d3-4e5a-4b6c-8d7e-9f0a1b2c3d4e",
        },
        # ------------------------------------------------------------------ 2
        {
            "parameters": {
                "language": "python",
                "pythonCode": python_code,
            },
            "id": "a1000000-0000-4000-8000-000000000002",
            "name": "Python - Analisar Servidor",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [160, 300],
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
            "position": [400, 300],
        },
        # ------------------------------------------------------------------ 4
        {
            "parameters": {
                "fromEmail": "monitoramento@suaempresa.com.br",
                "toEmail": "infraestrutura@suaempresa.com.br",
                "subject": "=[P1 - CRITICO] {{ $json.servidor }} - acao imediata necessaria",
                "emailFormat": "text",
                "text": "={{ $json.mensagem }}",
                "options": {"appendAttribution": False},
            },
            "id": "a1000000-0000-4000-8000-000000000004",
            "name": "Email - Alerta CRITICO",
            "type": "n8n-nodes-base.emailSend",
            "typeVersion": 2.1,
            "position": [700, 100],
        },
        # ------------------------------------------------------------------ 5
        {
            "parameters": {
                "fromEmail": "monitoramento@suaempresa.com.br",
                "toEmail": "infraestrutura@suaempresa.com.br",
                "subject": "=[P2 - ALERTA] {{ $json.servidor }} - recurso proximo do limite",
                "emailFormat": "text",
                "text": "={{ $json.mensagem }}",
                "options": {"appendAttribution": False},
            },
            "id": "a1000000-0000-4000-8000-000000000005",
            "name": "Email - Aviso ALERTA",
            "type": "n8n-nodes-base.emailSend",
            "typeVersion": 2.1,
            "position": [700, 280],
        },
        # ------------------------------------------------------------------ 6
        {
            "parameters": {},
            "id": "a1000000-0000-4000-8000-000000000006",
            "name": "Sem Acao - Servidor Normal",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [700, 460],
        },
        # ------------------------------------------------------------------ 7
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ JSON.stringify($json) }}",
                "options": {},
            },
            "id": "a1000000-0000-4000-8000-000000000007",
            "name": "Responder Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [980, 300],
        },
        # --------------------------------------------------------- anotacoes
        {
            "parameters": {
                "content": "## 1. Entrada\nPOST com JSON:\n```\n{\n  \"servidor\": \"SRV-PACS-01\",\n  \"cpu\": 72,\n  \"memoria\": 84,\n  \"disco\": 93,\n  \"servico\": \"online\"\n}\n```\nO payload chega em `$json.body`.",
                "height": 300,
                "width": 300,
                "color": 4,
            },
            "id": "a1000000-0000-4000-8000-000000000008",
            "name": "Nota - Entrada",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [-180, -60],
        },
        {
            "parameters": {
                "content": "## 2. Analise em Python\nCode node (Python Beta).\nRegras: >=80% ALERTA, >=90% CRITICO,\nservico != online -> CRITICO.\nO pior nivel encontrado vence.\n\nSaida inclui `status`, `motivo`,\n`acao_recomendada` e `mensagem`.",
                "height": 300,
                "width": 300,
                "color": 5,
            },
            "id": "a1000000-0000-4000-8000-000000000009",
            "name": "Nota - Python",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [160, -60],
        },
        {
            "parameters": {
                "content": "## 3. Roteamento e notificacao\nO Switch le `$json.status` e escolhe a saida.\nCRITICO e ALERTA disparam e-mail (SMTP).\nNORMAL segue direto para a resposta.\n\nConfigure a credencial SMTP nos dois\nnodes de e-mail antes de ativar.",
                "height": 300,
                "width": 360,
                "color": 3,
            },
            "id": "a1000000-0000-4000-8000-000000000010",
            "name": "Nota - Notificacao",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [660, -60],
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
        "Email - Alerta CRITICO": {
            "main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]
        },
        "Email - Aviso ALERTA": {
            "main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]
        },
        "Sem Acao - Servidor Normal": {
            "main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]
        },
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
