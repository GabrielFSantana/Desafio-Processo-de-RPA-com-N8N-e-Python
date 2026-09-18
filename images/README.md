# Screenshots

Imagens usadas no README principal.

| Arquivo | O que mostra |
|---|---|
| `workflow-n8n.png` | Canvas completo do N8N, com os 7 nodes e as 3 sticky notes |
| `node-webhook.png` | Node Webhook: método POST, path, Respond e as URLs de Test/Production |
| `node-http-request.png` | Node HTTP Request chamando `http://127.0.0.1:8000/analisar` |
| `node-switch.png` | Switch com a regra sobre `$json.status` e o fallback `ERRO` |
| `execucao-normal.png` | Execução real do cenário NORMAL (caminho verde até o NoOp) |
| `execucoes.png` | Execução real do cenário de payload inválido (caminho ERRO) |
| `email-alerta.png` | **Pendente** — print do e-mail de alerta crítico recebido |

Para gerar `email-alerta.png`: configure a credencial SMTP nos dois nodes de
e-mail, dispare o cenário crítico (`examples/servidor_critico.json`) e tire o
print do e-mail na caixa de entrada. Depois descomente a linha da imagem na
seção 8 do README.

Antes de commitar qualquer print novo, confira que não há dados sensíveis
visíveis (e-mails reais, hostnames internos, tokens).
