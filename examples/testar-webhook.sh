#!/usr/bin/env bash
# =============================================================================
# testar-webhook.sh - dispara os cenarios de teste contra o webhook do N8N
#
# Uso:
#   ./testar-webhook.sh                              # usa a URL de TESTE local
#   ./testar-webhook.sh http://localhost:5678/webhook/monitoramento-servidor
#
# Lembre-se: a URL de "Test" so responde enquanto o botao "Execute workflow"
# estiver ativo no editor do N8N. A URL de "Production" (/webhook/...) exige
# o workflow salvo e ATIVO.
# =============================================================================
set -euo pipefail

URL="${1:-http://localhost:5678/webhook-test/monitoramento-servidor}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

enviar() {
  local nome="$1" arquivo="$2"
  echo "──────────────────────────────────────────────────────────────"
  echo "▶ Cenario: ${nome}"
  echo "  Payload: $(basename "${arquivo}")"
  echo "──────────────────────────────────────────────────────────────"
  curl -s -S -X POST "${URL}" \
       -H "Content-Type: application/json" \
       -d @"${arquivo}"
  echo -e "\n"
}

enviar "1 - NORMAL"                 "${DIR}/servidor_normal.json"
enviar "2 - ALERTA"                 "${DIR}/servidor_alerta.json"
enviar "3 - CRITICO (disco 93%)"    "${DIR}/servidor_critico.json"
enviar "4 - CRITICO (servico off)"  "${DIR}/servidor_servico_offline.json"
enviar "5 - Payload invalido"       "${DIR}/payload_invalido.json"

echo "✔ Todos os cenarios foram enviados para ${URL}"
