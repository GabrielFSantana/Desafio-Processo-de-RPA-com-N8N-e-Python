#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api_analise.py
--------------
Microsservico HTTP que expoe o motor de analise de analisar_servidor.py.

E este servico que o node "HTTP Request" do N8N chama. Assim o Python roda
como um processo proprio, independente da versao ou do modo de instalacao do
N8N - nao depende do Code node em Python (task runner) nem do Execute Command.

Usa SOMENTE a biblioteca padrao do Python: nada para instalar.

Como executar
-------------
    python api_analise.py                 # escuta em 127.0.0.1:8000
    python api_analise.py --porta 8080    # outra porta
    python api_analise.py --host 0.0.0.0  # aceita conexoes externas (cuidado)

Endpoints
---------
    GET  /saude     -> {"status": "ok", ...}          teste rapido / health check
    POST /analisar  -> diagnostico completo do servidor

Exemplo
-------
    curl -X POST http://127.0.0.1:8000/analisar \
         -H "Content-Type: application/json" \
         -d '{"servidor":"SRV-PORTARIA-01","cpu":72,"memoria":84,"disco":93,"servico":"online"}'

Observacao de seguranca
-----------------------
Por padrao escuta apenas em 127.0.0.1 (localhost). O servico nao tem
autenticacao, entao so exponha para a rede se colocar um proxy reverso com
autenticacao na frente.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analisar_servidor import __version__, analisar, PayloadInvalido  # noqa: E402

LIMITE_CORPO = 64 * 1024  # 64 KB: metricas sao pequenas; evita corpo absurdo


class Handler(BaseHTTPRequestHandler):
    server_version = "AnaliseServidor/" + __version__

    # ------------------------------------------------------------------ util
    def _responder(self, codigo: int, corpo: dict) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, formato, *args):
        """Log enxuto, com horario local, em vez do formato padrao do modulo."""
        agora = datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"[{agora}] {formato % args}\n")

    # ------------------------------------------------------------------- GET
    def do_GET(self):  # noqa: N802 (nome exigido pela BaseHTTPRequestHandler)
        if self.path.rstrip("/") in ("/saude", "/health", ""):
            self._responder(200, {
                "status": "ok",
                "servico": "API de analise de saude de servidores",
                "versao_regras": __version__,
                "endpoints": {"GET /saude": "health check", "POST /analisar": "analisa metricas"},
                "hora": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
        else:
            self._responder(404, {"erro": "Rota nao encontrada", "detalhe": self.path})

    # ------------------------------------------------------------------ POST
    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/analisar":
            self._responder(404, {"erro": "Rota nao encontrada", "detalhe": self.path})
            return

        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > LIMITE_CORPO:
            self._responder(413, {"erro": "Corpo da requisicao muito grande"})
            return

        bruto = self.rfile.read(tamanho).decode("utf-8", errors="replace")

        try:
            payload = json.loads(bruto)
        except json.JSONDecodeError as exc:
            self._responder(200, self._erro("JSON invalido", str(exc)))
            return

        # Aceita tanto o JSON puro quanto o envelope do webhook do N8N
        if isinstance(payload, dict) and isinstance(payload.get("body"), dict):
            payload = payload["body"]

        try:
            resultado = analisar(payload)
        except PayloadInvalido as exc:
            self._responder(200, self._erro("Payload invalido", str(exc),
                                            servidor=self._nome(payload)))
            return
        except Exception as exc:  # rede de seguranca: nunca derrubar o servico
            self._responder(200, self._erro("Falha inesperada na analise", repr(exc),
                                            servidor=self._nome(payload)))
            return

        self.log_message("%s -> %s", resultado["servidor"], resultado["status"])
        self._responder(200, resultado)

    # ------------------------------------------------------------- auxiliares
    @staticmethod
    def _nome(payload) -> str:
        if isinstance(payload, dict) and payload.get("servidor"):
            return str(payload["servidor"])
        return "desconhecido"

    @staticmethod
    def _erro(erro: str, detalhe: str, servidor: str = "desconhecido") -> dict:
        """
        Erro tambem volta com HTTP 200 e um campo 'status'.

        Motivo: assim o N8N trata tudo pelo mesmo caminho (o Switch roteia pela
        saida ERRO) em vez de o workflow quebrar por causa de um 4xx.
        """
        return {
            "servidor": servidor,
            "status": "ERRO",
            "motivo": f"{erro}: {detalhe}",
            "acao_recomendada": "Corrigir o payload enviado ao webhook e reenviar.",
            "recursos_afetados": [],
            "prioridade": "P3",
            "notificar": False,
            "analisado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "versao_regras": __version__,
        }


def main() -> int:
    p = argparse.ArgumentParser(description="API HTTP de analise de saude de servidores.")
    p.add_argument("--host", default="127.0.0.1", help="Endereco de escuta (padrao: 127.0.0.1)")
    p.add_argument("--porta", type=int, default=8000, help="Porta de escuta (padrao: 8000)")
    args = p.parse_args()

    servidor = ThreadingHTTPServer((args.host, args.porta), Handler)
    print("=" * 62)
    print("  API de analise de saude de servidores")
    print(f"  Escutando em    http://{args.host}:{args.porta}")
    print(f"  Health check    http://{args.host}:{args.porta}/saude")
    print(f"  Analise (POST)  http://{args.host}:{args.porta}/analisar")
    print("  Ctrl+C para encerrar")
    print("=" * 62)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
