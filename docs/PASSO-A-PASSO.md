# Guia passo a passo — construindo o workflow node por node

Este documento ensina a montar o workflow **do zero**, na mão, no seu próprio N8N.
Se você só quer rodar, importe `workflow/monitoramento-servidor.json` e pule para a
[seção 8](#8-configurando-a-credencial-smtp).

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
- [8. Configurando a credencial SMTP](#8-configurando-a-credencial-smtp)
- [9. Testando os cenários](#9-testando-os-cenários)
- [10. Ativando em produção](#10-ativando-em-produção)
- [Anexo A — Por que microsserviço e não Code node em Python](#anexo-a--por-que-microsserviço-e-não-code-node-em-python)
- [Anexo B — Referência rápida de expressions](#anexo-b--referência-rápida-de-expressions)
- [Anexo C — Solução de problemas](#anexo-c--solução-de-problemas)

---

## 0. Antes de começar

**Primeiro, suba o microsserviço Python.** Ele precisa estar rodando antes do
workflow, porque é ele que faz a análise:

```bash
# Windows
iniciar-api.bat

# Linux / macOS
./iniciar-api.sh
```

Confira:

```bash
curl http://127.0.0.1:8000/saude
# {"status": "ok", "servico": "API de analise de saude de servidores", ...}
```

**Depois, suba o N8N:**

```bash
npx n8n
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
Expõe uma URL HTTP do N8N. Qualquer agente coletor (crontab, Zabbix, health
check, outro workflow) faz um `POST` nessa URL enviando as métricas do servidor.
É o **contrato de entrada** da automação — quem coleta não precisa saber nada
sobre as regras de análise.

### 1.4 Como configurá-lo
1. `+` → busque **Webhook** → selecione.
2. Ele entra no canvas como primeiro node.
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
{ "servidor": "SRV-CFTV-02", "cpu": 72, "memoria": 84, "disco": 93, "servico": "online" }
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
    "servidor": "SRV-CFTV-02",
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
>   clicou em *Execute workflow*, e para **uma** chamada.
> - `…/webhook/monitoramento-servidor` → exige o workflow **salvo e ativo**.

---

## 2. Node — `Python - Analisar Servidor`

### 2.1 Nome do node
`Python - Analisar Servidor`

### 2.2 Tipo do node
**HTTP Request** — `n8n-nodes-base.httpRequest` (typeVersion 4.2).

> Por que este node e não o Code node em Python? Veja o
> [Anexo A](#anexo-a--por-que-microsserviço-e-não-code-node-em-python) —
> resumo: o Python do Code node, a partir do N8N 2.x, depende de um virtualenv
> gerenciado que não vem pronto em várias instalações, e o Execute Command foi
> retirado do conjunto padrão. O HTTP Request funciona em qualquer versão.

### 2.3 Para que ele serve
É a ponte para o **cérebro** do RPA. Envia as métricas para o microsserviço
Python (`python/api_analise.py`), que valida, aplica as regras de capacity
planning, classifica em `NORMAL` / `ALERTA` / `CRITICO`, monta o motivo, a ação
recomendada e a mensagem já formatada para a notificação.

### 2.4 Como configurá-lo
1. `+` na saída do Webhook → busque **HTTP Request**.
2. Preencha os campos abaixo.
3. Em **Settings → On Error**, escolha **`Continue (using regular output)`** —
   assim, se a API estiver fora do ar, o erro segue pelo caminho `ERRO` em vez
   de derrubar a execução.

### 2.5 Campos que precisam ser preenchidos

| Campo | Valor |
|---|---|
| **Method** | `POST` |
| **URL** | `http://127.0.0.1:8000/analisar` |
| **Send Body** | ativado |
| **Body Content Type** | `JSON` |
| **Specify Body** | `Using JSON` |
| **JSON** | *(expression)* `{{ JSON.stringify($json.body) }}` |
| **Settings → On Error** | `Continue (using regular output)` |

> ⚠️ **Use `127.0.0.1`, não `localhost`.** No Windows o Node.js resolve
> `localhost` para o IPv6 `::1`, mas a API Python escuta em IPv4 — dá
> `ECONNREFUSED ::1:8000`. Com `127.0.0.1` o problema não existe.
>
> ⚠️ **N8N em Docker + API no host:** troque por `http://host.docker.internal:8000`.
> Dentro do container, `127.0.0.1` é o próprio container.

### 2.6 Expressions do N8N

```
{{ JSON.stringify($json.body) }}
```

Repare que é `$json.body`, não `$json`: estamos repassando **só o payload**
enviado pelo coletor, sem os headers e metadados que o Webhook adiciona.
(A API também aceita o envelope completo, mas mandar só o essencial é mais limpo.)

### 2.7 Dados que entram
A saída do Webhook (com `body` dentro).

### 2.8 Dados que devem sair
Um único item com o diagnóstico completo — a resposta da API:

```json
{
  "servidor": "SRV-CFTV-02",
  "status": "CRITICO",
  "motivo": "Utilizacao de disco em 93% (limite critico: 90%).",
  "acao_recomendada": "Verificar espaco disponivel e realizar limpeza do servidor ...",
  "recursos_afetados": ["disco"],
  "prioridade": "P1",
  "notificar": true,
  "metricas": { "cpu": 72.0, "memoria": 84.0, "disco": 93.0, "servico": "online" },
  "analisado_em": "2026-09-18T01:03:38+00:00",
  "versao_regras": "1.0.0",
  "mensagem": "ALERTA DE MONITORAMENTO\nServidor: SRV-CFTV-02\n..."
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
1. `+` na saída do HTTP Request → busque **Switch**.
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

> 💡 **Alternativa mais simples** — como o Python já devolve o booleano
> `notificar`, dá para usar um `IF` com `{{ $json.notificar }}` *is true*. Mas aí
> você perde a distinção entre P1 e P2 no assunto do e-mail.

### 3.7 Dados que entram
O item do HTTP Request (com o campo `status`).

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
   (veja a [seção 8](#8-configurando-a-credencial-smtp)).
3. Em **Resource / Operation**, deixe **Send** (padrão).
4. Preencha os campos abaixo.

### 4.5 Campos que precisam ser preenchidos

| Campo | Valor |
|---|---|
| **From Email** | o e-mail da sua conta SMTP |
| **To Email** | o e-mail da equipe de infraestrutura |
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

Se quiser montar o corpo aqui em vez de usar `mensagem` (útil para treinar as
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

### 4.7 Dados que entram
Item com `status: "CRITICO"`.

### 4.8 Dados que devem sair
A resposta do servidor SMTP, por exemplo:

```json
{ "accepted": ["infra@exemplo.com"], "rejected": [], "messageId": "<...>" }
```

> ⚠️ **Atenção:** a partir daqui `$json` é a resposta do SMTP, **não** o
> diagnóstico. Por isso o node de resposta busca os dados no node do HTTP
> Request — veja a [seção 7](#7-node--responder-webhook).

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
| **Response Body** | *(expression)* `{{ JSON.stringify($('Python - Analisar Servidor').item.json) }}` |

### 7.6 Expressions do N8N

```
{{ JSON.stringify($('Python - Analisar Servidor').item.json) }}
```

⚠️ **Por que não simplesmente `$json`?** Porque nos caminhos `CRITICO` e
`ALERTA` o item que chega aqui é a resposta do servidor SMTP, não o diagnóstico.
`$('Nome do Node').item.json` busca o item correspondente em **qualquer** node
anterior do fluxo — é a expression mais útil do N8N, e garante que a resposta
HTTP seja sempre o diagnóstico, venha o item pelo caminho que vier.

### 7.7 Dados que entram
Resposta do SMTP (caminhos 1 e 2) ou o próprio diagnóstico (caminhos 3 e 4).

### 7.8 Dados que devem sair
A resposta HTTP 200 para o coletor:

```json
{
  "servidor": "SRV-CFTV-02",
  "status": "CRITICO",
  "motivo": "Utilizacao de disco em 93% (limite critico: 90%).",
  "acao_recomendada": "Verificar espaco disponivel e realizar limpeza do servidor ...",
  "prioridade": "P1"
}
```

---

## 8. Configurando a credencial SMTP

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

## 9. Testando os cenários

Confirme que a API Python está de pé:

```bash
curl http://127.0.0.1:8000/saude
```

Depois:

1. Clique em **Execute workflow** (o webhook de teste passa a escutar).
2. Dispare os cenários:

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

> ⚠️ Em modo de teste, o webhook responde a **uma** chamada por clique em
> *Execute workflow*. Clique de novo antes de cada cenário.

**O que verificar em cada execução:**

| Cenário | Caminho aceso no canvas | E-mail | Resposta HTTP |
|---|---|---|---|
| Normal | Switch → `NORMAL` → NoOp | não | `status: "NORMAL"` |
| Alerta | Switch → `ALERTA` → e-mail P2 | sim | `status: "ALERTA"` |
| Crítico | Switch → `CRITICO` → e-mail P1 | sim | `status: "CRITICO"` |
| Serviço offline | Switch → `CRITICO` → e-mail P1 | sim | `status: "CRITICO"` |
| Payload inválido | Switch → `ERRO` → resposta | não | `status: "ERRO"` |

Na janela da API Python você vê o log de cada chamada:

```text
[22:03:38] SRV-CFTV-02 -> CRITICO
[22:03:38] "POST /analisar HTTP/1.1" 200 -
```

> 📸 Aproveite para tirar os prints do README: canvas com o caminho verde de cada
> cenário e a aba **Executions**.

---

## 10. Ativando em produção

1. **Save** no workflow.
2. Ligue o toggle **Active** (canto superior direito).
3. A URL passa a ser `http://localhost:5678/webhook/monitoramento-servidor`
   (sem o `-test`).
4. Garanta que a API Python suba junto com a máquina (serviço do Windows,
   `systemd` no Linux ou um container).

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

## Anexo A — Por que microsserviço e não Code node em Python

As três formas de rodar Python a partir do N8N foram testadas numa instalação
real (N8N 2.31.4, instalado via npm no Windows):

| Abordagem | Resultado | Motivo |
|---|---|---|
| **Code node — `Language: Python`** | ❌ `Python runner unavailable: Virtual environment is missing from this system` | A partir do N8N 2.x o Python do Code node roda em um *task runner* externo que exige o pacote `@n8n/task-runner-python` e um virtualenv gerenciado. Em instalações npm (principalmente no Windows) ele não é criado — é um bug conhecido do projeto |
| **Execute Command** | ❌ `Unrecognized node type: n8n-nodes-base.executeCommand` | O node foi retirado do conjunto padrão no N8N 2.0 por motivos de segurança. Só volta definindo `N8N_NODES_INCLUDE=["n8n-nodes-base.executeCommand"]`, com relatos de que nem sempre funciona em instalação npm |
| **Microsserviço HTTP + HTTP Request** | ✅ | O `HTTP Request` é o node mais universal do N8N. Existe em todas as versões, em todos os modos de instalação, sem flag nenhuma |

Vantagens que a solução escolhida trouxe de brinde:

- **Python de verdade**, com o interpretador do sistema e acesso a qualquer
  biblioteca (`psutil`, `pandas`, `requests`), em vez de um sandbox limitado.
- **Testável isoladamente** — `curl` contra a API, sem abrir o N8N.
- **Reaproveitável** — o mesmo serviço atende outros workflows e outros sistemas.
- **Deploy independente** — dá para containerizar a API e escalar sem tocar no N8N.

O custo é ter um processo a mais rodando. Para uma automação de infraestrutura,
é um preço baixo — e é assim que integrações de verdade costumam ser feitas.

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

---

## Anexo C — Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `ECONNREFUSED ::1:8000` no HTTP Request | O Node resolveu `localhost` para IPv6; a API escuta em IPv4 | Troque a URL do node para `http://127.0.0.1:8000/analisar` |
| `ECONNREFUSED 127.0.0.1:8000` no HTTP Request | A API Python não está rodando | Rode `iniciar-api.bat` / `./iniciar-api.sh` e confira `curl http://127.0.0.1:8000/saude` |
| `ECONNREFUSED` com o N8N em Docker | Dentro do container, `localhost` é o container | Troque a URL para `http://host.docker.internal:8000` |
| Webhook responde `404` | Workflow não está ativo, ou usou a URL errada | Test URL exige *Execute workflow* a cada chamada; Production URL exige *Active* |
| Webhook fica “pendurado” sem responder | Algum caminho do Switch não chega ao `Responder Webhook` | Conecte **todas** as saídas do Switch (inclusive `ERRO`) a esse node |
| Resposta HTTP traz dados do SMTP | `Response Body` usando `$json` | Use `{{ JSON.stringify($('Python - Analisar Servidor').item.json) }}` |
| `Invalid login: 535` no e-mail | Senha da conta em vez de senha de app | Gere uma senha de app (Gmail exige 2FA) |
| E-mail sai vazio | `Text` em modo *Fixed* em vez de *Expression* | Clique na aba **Expression** do campo |
| Switch manda tudo para a mesma saída | `Left Value` em modo *Fixed* (texto literal) | Troque para **Expression**: `{{ $json.status }}` |
| `status: ERRO` em toda chamada | Payload incompleto ou campo com nome errado | A resposta traz o motivo; confira os 5 campos obrigatórios |
| API não sobe: `Address already in use` | Porta 8000 ocupada | `python3 python/api_analise.py --porta 8080` e ajuste a URL no node |

---

<sub>Parte do projeto **RPA de Monitoramento e Análise Automática de Saúde de Servidores** — Desafio DIO / Bootcamp Santander Automação com N8N.</sub>
