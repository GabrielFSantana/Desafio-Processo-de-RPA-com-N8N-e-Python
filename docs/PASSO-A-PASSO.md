# Guia passo a passo — construindo o workflow node por node

Este documento ensina a montar o workflow **do zero**, na mão, no seu próprio N8N.
Se você só quer rodar, importe `workflow/monitoramento-servidor.json` e pule para a
[seção 9](#9-configurando-a-credencial-smtp).

Construir na mão é o que realmente fixa o conteúdo do desafio — e rende os prints
para o README.

---

## Índice

- [0. Antes de começar](#0-antes-de-começar)
- [1. Node — Webhook - Receber Metricas](#1-node--webhook---receber-metricas)
- [2. Node — Python - Analisar Servidor](#2-node--python---analisar-servidor)
- [3. Node — Switch - Classificar Status](#3-node--switch---classificar-status)
- [4. Node — Email - Alerta CRITICO](#4-node--email---alerta-critico)
- [5. Node — Email - Aviso ALERTA](#5-node--email---aviso-alerta)
- [6. Node — Sem Acao - Servidor Normal](#6-node--sem-acao---servidor-normal)
- [7. Node — Responder Webhook](#7-node--responder-webhook)
- [8. Sticky Notes (opcional, mas recomendado)](#8-sticky-notes-opcional-mas-recomendado)
- [9. Configurando a credencial SMTP](#9-configurando-a-credencial-smtp)
- [10. Testando os cenários](#10-testando-os-cenários)
- [11. Ativando em produção](#11-ativando-em-produção)
- [Anexo A — Alternativa com Execute Command](#anexo-a--alternativa-com-execute-command)
- [Anexo B — Referência rápida de expressions](#anexo-b--referência-rápida-de-expressions)
- [Anexo C — Solução de problemas](#anexo-c--solução-de-problemas)

---

## 0. Antes de começar

Suba o N8N:

```bash
docker volume create n8n_data
docker run -d --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e GENERIC_TIMEZONE="America/Sao_Paulo" -e TZ="America/Sao_Paulo" \
  docker.n8n.io/n8nio/n8n
```

Abra `http://localhost:5678` → **Create Workflow** → renomeie (canto superior
esquerdo) para **`RPA - Monitoramento de Saude de Servidores`**.

> 💡 Para adicionar um node: clique no **`+`** do canvas (ou no `+` na ponta da
> conexão anterior) e digite o nome do node na busca.

---

## 1. Node — `Webhook - Receber Metricas`

### 1.1 Nome do node
`Webhook - Receber Metricas`
*(renomeie com duplo clique no título dentro do node)*

### 1.2 Tipo do node
**Webhook** — `n8n-nodes-base.webhook` (typeVersion 2).
É um node **trigger**: ele inicia o workflow.

### 1.3 Para que ele serve
Expõe uma URL HTTP pública do N8N. Qualquer agente coletor (crontab, Zabbix,
health check, outro workflow) faz um `POST` nessa URL enviando as métricas do
servidor. É o **contrato de entrada** da automação — quem coleta não precisa
saber nada sobre as regras de análise.

### 1.4 Como configurá-lo
1. `+` → busque **Webhook** → selecione.
2. Ele já entra no canvas como primeiro node.
3. Preencha os campos da tabela abaixo.
4. Copie a **Test URL** que aparece no topo do painel — você vai usá-la nos testes.

### 1.5 Campos que precisam ser preenchidos

| Campo | Valor | Por quê |
|---|---|---|
| **HTTP Method** | `POST` | Métricas vão no corpo da requisição, não na URL |
| **Path** | `monitoramento-servidor` | Define a URL final `/webhook/monitoramento-servidor` |
| **Authentication** | `None` | Simplicidade no desafio. Em produção → `Header Auth` |
| **Respond** | `Using 'Respond to Webhook' Node` | Permite devolver o diagnóstico completo no fim do fluxo |

Deixe **Options** vazio.

### 1.6 Expressions do N8N
Nenhuma. Este node só recebe.

### 1.7 Dados que entram
O corpo da requisição HTTP:

```json
{ "servidor": "SRV-PACS-01", "cpu": 72, "memoria": 84, "disco": 93, "servico": "online" }
```

### 1.8 Dados que devem sair
⚠️ **Ponto que mais confunde iniciante:** o Webhook **não** entrega o JSON na
raiz. Ele o embrulha:

```json
{
  "headers": { "content-type": "application/json", "...": "..." },
  "params": {},
  "query": {},
  "body": {
    "servidor": "SRV-PACS-01",
    "cpu": 72,
    "memoria": 84,
    "disco": 93,
    "servico": "online"
  },
  "webhookUrl": "http://localhost:5678/webhook/monitoramento-servidor",
  "executionMode": "test"
}
```

Ou seja: o payload útil está em **`$json.body`**, não em `$json`.

> **Test URL vs Production URL**
> - `…/webhook-test/monitoramento-servidor` → só responde **enquanto** você
>   clicou em *Execute workflow*. Serve para ver os dados no canvas.
> - `…/webhook/monitoramento-servidor` → exige o workflow **salvo e ativo**.

---

## 2. Node — `Python - Analisar Servidor`

### 2.1 Nome do node
`Python - Analisar Servidor`

### 2.2 Tipo do node
**Code** — `n8n-nodes-base.code` (typeVersion 2), com **Language: Python (Beta)**.

> O N8N roda Python via **Pyodide** (CPython compilado para WebAssembly). Roda
> dentro do próprio N8N, sem instalar nada, e funciona inclusive no N8N Cloud.
> Limitação: só a biblioteca padrão e alguns pacotes suportados pelo Pyodide —
> mais que suficiente aqui, porque a análise é lógica pura.

### 2.3 Para que ele serve
É o **cérebro** do RPA. Recebe o payload bruto, valida, aplica as regras de
capacity planning, classifica em `NORMAL` / `ALERTA` / `CRITICO`, monta o motivo,
a ação recomendada e a mensagem já formatada para a notificação.

### 2.4 Como configurá-lo
1. `+` na saída do Webhook → busque **Code**.
2. Em **Language**, escolha **`Python (Beta)`**.
3. Em **Mode**, deixe **`Run Once for All Items`**.
4. Apague o código de exemplo e **cole o conteúdo de
   [`python/code_node_n8n.py`](../python/code_node_n8n.py)** — o arquivo inteiro,
   incluindo o bloco final que monta o `return`.

### 2.5 Campos que precisam ser preenchidos

| Campo | Valor |
|---|---|
| **Language** | `Python (Beta)` |
| **Mode** | `Run Once for All Items` |
| **Python Code** | conteúdo de `python/code_node_n8n.py` |

### 2.6 Expressions do N8N
Dentro do Code node não se usa a sintaxe `{{ }}`. O acesso aos dados é pela API
Python do N8N:

| Expressão | O que faz |
|---|---|
| `_input.all()` | Lista de todos os itens que chegaram do node anterior |
| `_input.first()` | Apenas o primeiro item |
| `item.json` | O JSON do item — é um **JsProxy**, não um dict Python |
| `item.json.to_py()` | 🔑 **Converte o JsProxy em dict Python de verdade** |
| `return [{"json": {...}}]` | Formato obrigatório de saída do Code node |

O trecho que faz a ponte (final do arquivo):

```python
saida = []
for item in _input.all():
    dados = item.json.to_py()          # JsProxy -> dict Python
    corpo = dados.get("body", dados)   # o Webhook entrega o payload em "body"
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
```

> ⚠️ **Esquecer o `.to_py()` é o erro nº 1** ao usar Python no N8N. Sem ele,
> `dados["cpu"]` estoura com `TypeError: 'JsProxy' object is not subscriptable`.

> 💡 O `try/except` garante que payload inválido não derruba o workflow: vira
> `status: "ERRO"` e é tratado na saída de fallback do Switch.

### 2.7 Dados que entram
A saída do Webhook (com `body` dentro).

### 2.8 Dados que devem sair
Um único item com o diagnóstico completo:

```json
{
  "servidor": "SRV-PACS-01",
  "status": "CRITICO",
  "motivo": "Utilizacao de disco em 93% (limite critico: 90%).",
  "acao_recomendada": "Verificar espaco disponivel e realizar limpeza do servidor ...",
  "recursos_afetados": ["disco"],
  "prioridade": "P1",
  "notificar": true,
  "metricas": { "cpu": 72.0, "memoria": 84.0, "disco": 93.0, "servico": "online" },
  "analisado_em": "2026-09-18T00:40:10+00:00",
  "versao_regras": "1.0.0",
  "mensagem": "ALERTA DE MONITORAMENTO\nServidor: SRV-PACS-01\n..."
}
```

O campo **`mensagem`** é o pulo do gato: com ele pronto aqui, os nodes de e-mail
viram uma expression de uma linha só.

---

## 3. Node — `Switch - Classificar Status`

### 3.1 Nome do node
`Switch - Classificar Status`

### 3.2 Tipo do node
**Switch** — `n8n-nodes-base.switch` (typeVersion 3.2).

> **Switch ou IF?** O `IF` tem só 2 saídas (true/false) e exigiria dois nodes
> encadeados para três status. O `Switch` resolve com um node só, com saídas
> nomeadas — mais legível no canvas e mais fácil de estender.

### 3.3 Para que ele serve
Lê o campo `status` produzido pelo Python e manda o item pelo caminho certo:
e-mail P1, e-mail P2, sem ação, ou tratamento de erro.

### 3.4 Como configurá-lo
1. `+` na saída do Code node → busque **Switch**.
2. **Mode**: `Rules` (padrão).
3. Crie **3 regras** com **Add Routing Rule**.
4. Em cada regra, ative **Rename Output** e dê o nome da saída.
5. Em **Options → Add option → Fallback Output**, escolha **`Extra Output`** e
   nomeie como `ERRO`.

### 3.5 Campos que precisam ser preenchidos

| Regra | Left Value (expression) | Operação | Right Value | Rename Output |
|---|---|---|---|---|
| 1 | `{{ $json.status }}` | String → *is equal to* | `CRITICO` | `CRITICO` |
| 2 | `{{ $json.status }}` | String → *is equal to* | `ALERTA` | `ALERTA` |
| 3 | `{{ $json.status }}` | String → *is equal to* | `NORMAL` | `NORMAL` |
| *fallback* | — | — | — | `ERRO` |

Resultado: 4 saídas, nesta ordem → `CRITICO` (0), `ALERTA` (1), `NORMAL` (2), `ERRO` (3).

### 3.6 Expressions do N8N

```
{{ $json.status }}
```

Para colocar uma expression no campo **Left Value**, passe o mouse sobre ele e
clique na abinha **Expression** (ao lado de *Fixed*).

> 💡 **Alternativa ainda mais simples** — como o Python já devolve o booleano
> `notificar`, dá para usar um `IF` com `{{ $json.notificar }}` *is true*. Mas aí
> você perde a distinção entre P1 e P2 no assunto do e-mail.

### 3.7 Dados que entram
O item do Code node (com o campo `status`).

### 3.8 Dados que devem sair
**O mesmo item, sem alteração** — o Switch só decide *por onde* ele sai. Isso é
importante: todos os campos (`mensagem`, `servidor`, `prioridade`…) continuam
disponíveis nos nodes seguintes.

---

## 4. Node — `Email - Alerta CRITICO`

### 4.1 Nome do node
`Email - Alerta CRITICO`

### 4.2 Tipo do node
**Send Email** — `n8n-nodes-base.emailSend` (typeVersion 2.1).

### 4.3 Para que ele serve
Dispara o e-mail de prioridade máxima para a equipe de infraestrutura quando o
servidor está em estado crítico.

### 4.4 Como configurá-lo
1. `+` na **primeira saída** do Switch (`CRITICO`) → busque **Send Email**.
2. Em **Credential to connect with**, crie/selecione a credencial SMTP
   (veja a [seção 9](#9-configurando-a-credencial-smtp)).
3. Em **Resource / Operation**, deixe **Send** (padrão).
4. Preencha os campos abaixo.

### 4.5 Campos que precisam ser preenchidos

| Campo | Valor |
|---|---|
| **From Email** | `monitoramento@suaempresa.com.br` |
| **To Email** | `infraestrutura@suaempresa.com.br` |
| **Subject** | *(expression)* `[P1 - CRITICO] {{ $json.servidor }} - acao imediata necessaria` |
| **Email Format** | `Text` |
| **Text** | *(expression)* `{{ $json.mensagem }}` |

> 💡 Em **Options → Append n8n Attribution**, desmarque para o e-mail não sair com
> o rodapé "Automated with n8n".

### 4.6 Expressions do N8N

```
Subject: [P1 - CRITICO] {{ $json.servidor }} - acao imediata necessaria
Text:    {{ $json.mensagem }}
```

Se quiser montar o corpo aqui em vez de usar `mensagem` (útil para entender as
expressions), o equivalente seria:

```
ALERTA DE MONITORAMENTO
Servidor: {{ $json.servidor }}
Status: {{ $json.status }}
CPU: {{ $json.metricas.cpu }}%
Memoria: {{ $json.metricas.memoria }}%
Disco: {{ $json.metricas.disco }}%

Problema identificado:
{{ $json.motivo }}

Acao recomendada:
{{ $json.acao_recomendada }}
```

> ⚠️ Cuidado ao referenciar dados de nodes anteriores: se precisar do payload
> original, use `{{ $('Webhook - Receber Metricas').item.json.body.servidor }}`.
> Aqui não é necessário, porque o Python já ecoou tudo que interessa.

### 4.7 Dados que entram
Item com `status: "CRITICO"`.

### 4.8 Dados que devem sair
A resposta do servidor SMTP, por exemplo:

```json
{ "accepted": ["infraestrutura@suaempresa.com.br"], "rejected": [], "messageId": "<...>" }
```

> ⚠️ **Atenção:** a partir daqui `$json` é a resposta do SMTP, **não** o
> diagnóstico. Por isso o node de resposta precisa buscar os dados no node do
> Python — veja a [seção 7](#7-node--responder-webhook).

---

## 5. Node — `Email - Aviso ALERTA`

Idêntico ao anterior, mudando apenas a origem e o assunto.

| Item | Valor |
|---|---|
| **Nome** | `Email - Aviso ALERTA` |
| **Tipo** | `n8n-nodes-base.emailSend` (2.1) |
| **Serve para** | Avisar sobre recurso próximo do limite, sem urgência de plantão |
| **Conectado à** | **segunda** saída do Switch (`ALERTA`) |
| **Subject** | `[P2 - ALERTA] {{ $json.servidor }} - recurso proximo do limite` |
| **Text** | `{{ $json.mensagem }}` |
| **Entra** | Item com `status: "ALERTA"` |
| **Sai** | Resposta do SMTP |

> 💡 Em produção, é comum enviar o P2 para uma lista diferente (ou só para o canal
> do time), reservando o P1 para quem está de plantão.

---

## 6. Node — `Sem Acao - Servidor Normal`

### 6.1 Nome do node
`Sem Acao - Servidor Normal`

### 6.2 Tipo do node
**No Operation, do nothing** — `n8n-nodes-base.noOp` (typeVersion 1).

### 6.3 Para que ele serve
Fecha o caminho do status `NORMAL` **sem notificar ninguém** — esse é o ponto
central do combate à fadiga de alerta. Ele existe para deixar o fluxo explícito
no canvas (fica óbvio que o caso normal foi tratado) e para dar um ponto de
extensão futuro (gravar em banco, contar métrica, etc.).

### 6.4 Como configurá-lo
`+` na **terceira saída** do Switch (`NORMAL`) → busque **No Operation**.
Não há nada para preencher.

### 6.5 Campos
Nenhum.

### 6.6 Expressions
Nenhuma.

### 6.7 / 6.8 Dados que entram e saem
Entra e sai **o mesmo item**, sem alteração.

---

## 7. Node — `Responder Webhook`

### 7.1 Nome do node
`Responder Webhook`

### 7.2 Tipo do node
**Respond to Webhook** — `n8n-nodes-base.respondToWebhook` (typeVersion 1.1).

### 7.3 Para que ele serve
Devolve o resultado da análise para quem chamou o webhook, fechando o ciclo
HTTP. Isso transforma o RPA também em uma **API de diagnóstico**: o coletor
recebe o veredito de volta e pode gravar em log, exibir num painel ou decidir
outra ação.

### 7.4 Como configurá-lo
1. `+` na saída do `Email - Alerta CRITICO` → busque **Respond to Webhook**.
2. **Arraste** as saídas dos outros três caminhos (`Email - Aviso ALERTA`,
   `Sem Acao - Servidor Normal` e a saída `ERRO` do Switch) para a **entrada
   deste mesmo node**. Um node pode receber várias conexões.

### 7.5 Campos que precisam ser preenchidos

| Campo | Valor |
|---|---|
| **Respond With** | `JSON` |
| **Response Body** | *(expression)* `{{ JSON.stringify($json) }}` |

### 7.6 Expressions do N8N

```
{{ JSON.stringify($json) }}
```

⚠️ **Muito importante:** nos caminhos `CRITICO` e `ALERTA`, `$json` é a resposta
do SMTP. Para devolver sempre o diagnóstico, troque a expression por:

```
{{ JSON.stringify($('Python - Analisar Servidor').item.json) }}
```

`$('Nome do Node').item.json` busca o item correspondente em **qualquer** node
anterior do fluxo — é a expression mais útil do N8N.

> No JSON pronto deste repositório a expression está como `{{ JSON.stringify($json) }}`
> para manter o exemplo simples. Se quiser a resposta sempre uniforme, aplique a
> troca acima — é um bom ponto para comentar no README como decisão consciente.

### 7.7 Dados que entram
Resposta do SMTP (caminhos 1 e 2) ou o próprio diagnóstico (caminhos 3 e 4).

### 7.8 Dados que devem sair
A resposta HTTP 200 para o coletor:

```json
{
  "servidor": "SRV-PACS-01",
  "status": "CRITICO",
  "motivo": "Utilizacao de disco em 93% (limite critico: 90%).",
  "acao_recomendada": "Verificar espaco disponivel e realizar limpeza do servidor ...",
  "prioridade": "P1"
}
```

---

## 8. Sticky Notes (opcional, mas recomendado)

Adicione 3 notas (`+` → **Sticky Note**) sobre os blocos do canvas: entrada,
análise em Python e notificação. Custa 2 minutos, deixa o print do README
profissional e mostra cuidado com documentação — o tipo de detalhe que pesa num
projeto de portfólio.

---

## 9. Configurando a credencial SMTP

1. Menu lateral → **Credentials** → **Add credential** → busque **SMTP**.
2. Preencha:

| Campo | Gmail | Outlook / Office 365 | Mailtrap (teste) |
|---|---|---|---|
| **User** | seu e-mail | seu e-mail | usuário do inbox |
| **Password** | **senha de app** (16 chars) | senha de app | senha do inbox |
| **Host** | `smtp.gmail.com` | `smtp.office365.com` | `sandbox.smtp.mailtrap.io` |
| **Port** | `465` | `587` | `2525` |
| **SSL/TLS** | ativado | desativado (usa STARTTLS) | desativado |

3. **Save** e teste com o botão da própria tela de credencial.

> 🔐 **Senha de app do Gmail:** exige 2FA ativo. Vá em
> *Conta Google → Segurança → Verificação em duas etapas → Senhas de app*.
> A senha da conta **não funciona** no SMTP.

> 🔐 **Nunca comite credenciais.** Ao exportar o workflow
> (**⋯ → Download**), o N8N exporta apenas a *referência* à credencial (id e
> nome), nunca a senha. Ainda assim, confira o JSON antes do `git push`.

> 🧪 **Sem SMTP à mão?** Use o [Mailtrap](https://mailtrap.io) (gratuito): ele
> captura os e-mails numa caixa de teste e rende ótimos prints para o README.

---

## 10. Testando os cenários

1. Clique em **Execute workflow** (o webhook de teste passa a escutar).
2. Copie a **Test URL** do node Webhook.
3. Dispare os cenários:

```bash
chmod +x examples/testar-webhook.sh
./examples/testar-webhook.sh http://localhost:5678/webhook-test/monitoramento-servidor
```

Ou um por vez:

```bash
# Cenário 1 — NORMAL (não deve enviar e-mail)
curl -X POST http://localhost:5678/webhook-test/monitoramento-servidor \
  -H "Content-Type: application/json" -d @examples/servidor_normal.json

# Cenário 2 — ALERTA
curl -X POST http://localhost:5678/webhook-test/monitoramento-servidor \
  -H "Content-Type: application/json" -d @examples/servidor_alerta.json

# Cenário 3 — CRÍTICO
curl -X POST http://localhost:5678/webhook-test/monitoramento-servidor \
  -H "Content-Type: application/json" -d @examples/servidor_critico.json
```

**O que verificar em cada execução:**

| Cenário | Caminho aceso no canvas | E-mail | Resposta HTTP |
|---|---|---|---|
| Normal | Switch → `NORMAL` → NoOp | não | `status: "NORMAL"` |
| Alerta | Switch → `ALERTA` → e-mail P2 | sim | `status: "ALERTA"` |
| Crítico | Switch → `CRITICO` → e-mail P1 | sim | `status: "CRITICO"` |
| Serviço offline | Switch → `CRITICO` → e-mail P1 | sim | `status: "CRITICO"` |
| Payload inválido | Switch → `ERRO` → resposta | não | `status: "ERRO"` |

> 📸 Aproveite para tirar os prints do README: canvas com o caminho verde de cada
> cenário e a aba **Executions**.

---

## 11. Ativando em produção

1. **Save** no workflow.
2. Ligue o toggle **Active** (canto superior direito).
3. A URL passa a ser `http://localhost:5678/webhook/monitoramento-servidor`
   (sem o `-test`).

Exemplo de coletor real — um `cron` de três linhas no servidor monitorado:

```bash
#!/usr/bin/env bash
# /usr/local/bin/coletar-metricas.sh  —  crontab: */5 * * * *

CPU=$(top -bn1 | awk '/Cpu\(s\)/{printf "%.0f", $2+$4}')
MEM=$(free | awk '/Mem:/{printf "%.0f", $3/$2*100}')
DSK=$(df / | awk 'NR==2{gsub("%","",$5); print $5}')
SVC=$(systemctl is-active nginx >/dev/null 2>&1 && echo online || echo offline)

curl -s -X POST http://n8n.interno:5678/webhook/monitoramento-servidor \
  -H "Content-Type: application/json" \
  -d "{\"servidor\":\"$(hostname)\",\"cpu\":$CPU,\"memoria\":$MEM,\"disco\":$DSK,\"servico\":\"$SVC\"}"
```

---

## Anexo A — Alternativa com Execute Command

Se você usa **N8N self-hosted** e prefere rodar o script `.py` como arquivo
(em vez do Code node), substitua o node ② por dois nodes:

**A.1 — `Execute Command`** (`n8n-nodes-base.executeCommand`)

| Campo | Valor |
|---|---|
| **Command** | *(expression)* `python3 /data/scripts/analisar_servidor.py '{{ JSON.stringify($json.body) }}'` |

Saída do node: `{ "exitCode": 0, "stdout": "{...json...}", "stderr": "" }`.

**A.2 — `Code` (JavaScript)** para converter o `stdout` (texto) em objeto:

```javascript
return $input.all().map(item => ({
  json: JSON.parse(item.json.stdout)
}));
```

**Pré-requisitos desta abordagem:**

1. Python instalado no container do N8N — a imagem oficial **não traz**.
   Você precisa de uma imagem customizada:

   ```dockerfile
   FROM docker.n8n.io/n8nio/n8n
   USER root
   RUN apk add --no-cache python3
   USER node
   ```

2. O script montado como volume:

   ```bash
   docker run -d --name n8n -p 5678:5678 \
     -v n8n_data:/home/node/.n8n \
     -v "$(pwd)/python:/data/scripts:ro" \
     -e NODE_FUNCTION_ALLOW_EXTERNAL=* \
     n8n-com-python
   ```

3. **Não funciona no N8N Cloud.**

> ⚠️ Risco de segurança: montar valores do payload direto na linha de comando
> abre espaço para *command injection*. O script deste repositório valida a
> entrada, mas em produção prefira passar o JSON via **stdin** ou usar o Code node.

---

## Anexo B — Referência rápida de expressions

| Expression | O que faz |
|---|---|
| `{{ $json.campo }}` | Campo do item vindo do node imediatamente anterior |
| `{{ $json.metricas.cpu }}` | Campo aninhado |
| `{{ $json.body.servidor }}` | Payload dentro do envelope do Webhook |
| `{{ $('Nome do Node').item.json.campo }}` | Campo de **qualquer** node anterior |
| `{{ JSON.stringify($json) }}` | Serializa o item inteiro |
| `{{ $now.format('dd/MM/yyyy HH:mm') }}` | Data/hora atual formatada (Luxon) |
| `{{ $json.status === 'CRITICO' ? '🔴' : '🟡' }}` | Condicional inline |
| `{{ $execution.id }}` | ID da execução — ótimo para correlacionar logs |
| `{{ $workflow.name }}` | Nome do workflow |

E, dentro do **Code node (Python)**:

| Expressão | O que faz |
|---|---|
| `_input.all()` | Todos os itens de entrada |
| `_input.first().json.to_py()` | Primeiro item já convertido para dict |
| `_('Nome do Node').all()` | Itens de outro node |
| `return [{"json": {...}}]` | Formato de saída obrigatório |

---

## Anexo C — Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `TypeError: 'JsProxy' object is not subscriptable` | Faltou `.to_py()` | Use `item.json.to_py()` |
| `KeyError: 'servidor'` | Leu `$json` em vez de `$json.body` | Use `dados.get("body", dados)` |
| Webhook responde `404` | Workflow não está ativo, ou usou a URL errada | Test URL exige *Execute workflow*; Production URL exige *Active* |
| Webhook fica “pendurado” sem responder | `Respond` = `Using Respond to Webhook Node`, mas algum caminho não chega nesse node | Conecte **todas** as saídas do Switch ao `Responder Webhook` |
| `Invalid login: 535` no e-mail | Senha da conta em vez de senha de app | Gere uma senha de app (Gmail exige 2FA) |
| E-mail sai vazio | `Text` em modo *Fixed* em vez de *Expression* | Clique na aba **Expression** do campo |
| Switch manda tudo para a mesma saída | `Left Value` em modo *Fixed* (texto literal) | Troque para **Expression**: `{{ $json.status }}` |
| `ModuleNotFoundError` no Code node | Pacote não suportado pelo Pyodide | Use só a stdlib, ou migre para o Anexo A |
| Python não classifica como esperado | Valor veio como string com `%` | O script já normaliza — confira nos dados de entrada do node |

---

<sub>Parte do projeto **RPA de Monitoramento e Análise Automática de Saúde de Servidores** — Desafio DIO / Bootcamp Santander Automação com N8N.</sub>
