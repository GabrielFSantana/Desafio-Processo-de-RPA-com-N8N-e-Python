#!/usr/bin/env bash
# Sobe a API de analise em Python (necessaria para o workflow).
# Deixe este terminal aberto enquanto usar o n8n.
cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 python/api_analise.py
