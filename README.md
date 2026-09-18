# RPA de Monitoramento e Análise Automática de Saúde de Servidores

> Processo de RPA construído com **N8N + Python** para receber métricas de servidores via Webhook, classificar automaticamente a criticidade e notificar a equipe de infraestrutura por e-mail.
>
> Projeto desenvolvido como entrega do desafio **“Criando um Processo de RPA com N8N e Python”** — Bootcamp **Santander – Automação com N8N** (DIO).

<p align="left">
  <img alt="N8N" src="https://img.shields.io/badge/n8n-1.x-EA4B71?style=flat-square&logo=n8n&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Licença" src="https://img.shields.io/badge/licen%C3%A7a-MIT-blue?style=flat-square">
  <img alt="Testes" src="https://img.shields.io/badge/testes-14%20passando-brightgreen?style=flat-square">
</p>

---

## Índice

1. [Descrição](#1-descrição)
2. [Objetivo](#2-objetivo)
3. [Problema que a automação resolve](#3-problema-que-a-automação-resolve)
4. [Tecnologias utilizadas](#4-tecnologias-utilizadas)
5. [Arquitetura da solução](#5-arquitetura-da-solução)
6. [Explicação do workflow](#6-explicação-do-workflow)
7. [Explicação da utilização do Python](#7-explicação-da-utilização-do-python)
8. [Exemplos de entrada e saída](#8-exemplos-de-entrada-e-saída)
9. [Cenários de teste](#9-cenários-de-teste)
10. [Como executar o projeto](#10-como-executar-o-projeto)
11. [Estrutura do repositório](#11-estrutura-do-repositório)
12. [Melhorias futuras](#12-melhorias-futuras)
13. [Conclusão](#13-conclusão)

---

## 1. Descrição

Este projeto implementa um **RPA (Robotic Process Automation)** que automatiza uma
das tarefas mais repetitivas — e mais críticas — de uma equipe de infraestrutura:
**olhar métricas de servidor, decidir se aquilo é problema e avisar alguém.**

O N8N expõe um **Webhook HTTP** que recebe as métricas coletadas de um servidor
(CPU, memória, disco e status do serviço). Um **Code node executando Python**
aplica as regras de capacity planning, classifica o servidor em
`NORMAL`, `ALERTA` ou `CRITICO`, monta o motivo e a ação recomendada, e devolve
um JSON estruturado. Um **Switch** roteia o resultado e dispara a notificação por
**e-mail (SMTP)** apenas quando existe um problema real.

O agente que coleta as métricas pode ser qualquer coisa: um script de crontab,
um `curl` no fim de um job, Zabbix, Prometheus Alertmanager, um health check de
aplicação ou até outro workflow do N8N. O contrato é apenas o JSON do webhook.

> 📸 **Screenshot 1 — visão geral do workflow**
> Insira aqui o print do canvas completo do N8N (todos os nodes conectados).
> `![Workflow completo no N8N](images/workflow-n8n.png)`

---

## 2. Objetivo

- Demonstrar, na prática, a integração **N8N ↔ Python** dentro de um processo de RPA.
- Centralizar em **um único ponto** a regra de negócio que define o que é
  “servidor saudável”, “servidor em atenção” e “servidor em incidente”.
- Eliminar a triagem manual: a equipe só é acionada quando existe algo a fazer.
- Entregar uma automação **reprodutível**, versionada e documentada, que sirva
  tanto como entrega educacional quanto como peça de portfólio.

---

## 3. Problema que a automação resolve

Em ambientes de produção — especialmente em plataformas que armazenam grande
volume de arquivos, como sistemas de imagem médica (PACS/RIS/LIS) — o disco
enche silenciosamente. Quando o alerta chega, normalmente já chegou tarde.

O cenário manual típico:

| Dor | Consequência |
|---|---|
| Métricas espalhadas em dashboards diferentes | Ninguém olha todos os dias |
| Triagem manual (“isso é grave?”) | Depende da experiência de quem está de plantão |
| Critério informal de severidade | Duas pessoas classificam o mesmo evento de formas diferentes |
| Aviso por WhatsApp/verbal | Sem rastro, sem histórico, sem SLA |
| Alerta para tudo | Fadiga de alerta — o time passa a ignorar |

O que esta automação entrega:

- **Critério objetivo e versionado.** O limiar está no código, não na cabeça do analista.
- **Triagem em milissegundos**, 24×7, sem intervenção humana.
- **Ação recomendada junto do alerta** — o e-mail já diz o que fazer.
- **Notificação só quando importa.** Servidor `NORMAL` não gera e-mail.
- **Priorização automática** (P1 / P2 / P4) pronta para virar chamado.

---

## 4. Tecnologias utilizadas

| Tecnologia | Papel no projeto |
|---|---|
| **N8N 1.x** | Orquestração do RPA: webhook, roteamento, notificação e resposta HTTP |
| **Python 3.10+** | Motor de análise e classificação (regras de negócio) |
| **Code node (Python / Pyodide)** | Executa o Python **dentro** do N8N, sem dependência externa |
| **Node Send Email (SMTP)** | Canal de notificação da equipe de infraestrutura |
| **Webhook / HTTP POST** | Contrato de entrada — desacopla o coletor de métricas do analisador |
| **unittest** | 14 testes automatizados cobrindo as regras e as bordas |
| **Docker (opcional)** | Forma recomendada de subir o N8N localmente |

---

## 5. Arquitetura da solução

```text
┌──────────────────────┐
│  Agente coletor      │   crontab / Zabbix / health check / script de deploy
│  (fora deste repo)   │
└──────────┬───────────┘
           │  HTTP POST  { servidor, cpu, memoria, disco, servico }
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                 N8N                                     │
│                                                                         │
│  ① Webhook ──▶ ② Code node (PYTHON) ──▶ ③ Switch ──┬──▶ ④ E-mail P1     │
│   recebe        analisa e classifica     roteia    ├──▶ ⑤ E-mail P2     │
│                                                    ├──▶ ⑥ NoOp (normal) │
│                                                    └──▶ (fallback ERRO) │
│                                                          │              │
│                                    ⑦ Respond to Webhook ◀┘              │
└─────────────────────────────────────────────────────────────────────────┘
           │  HTTP 200  { servidor, status, motivo, acao_recomendada, ... }
           ▼
   Resposta ao coletor (log / auditoria)          ✉  Caixa da equipe de infra
```

**Fluxo em uma linha:**
`Webhook → N8N → Python → Análise → Classificação → N8N → Notificação/Relatório`

**Decisão de arquitetura — por que o Code node e não o Execute Command?**

| Critério | Code node (Python/Pyodide) ✅ | Execute Command (`python3 script.py`) |
|---|---|---|
| Funciona no N8N Cloud | Sim | Não |
| Funciona na imagem Docker oficial | Sim | Não (a imagem não traz Python) |
| Precisa montar volume / instalar pacote | Não | Sim |
| Código versionado junto do workflow | Sim (vai no JSON exportado) | Não (fica fora) |
| Bibliotecas externas (psutil, pandas) | Limitado ao Pyodide | Livre |

Para este desafio, o **Code node vence em simplicidade e reprodutibilidade** —
qualquer pessoa importa o JSON e roda. A alternativa com `Execute Command` está
documentada em [`docs/PASSO-A-PASSO.md`](docs/PASSO-A-PASSO.md) para quem usa
N8N self-hosted e quer rodar o script como arquivo.

---

## 6. Explicação do workflow

O workflow tem **7 nodes funcionais** (+ 3 sticky notes de documentação).
O guia completo, node por node — com todos os campos, expressions, dados de
entrada e dados de saída — está em **[`docs/PASSO-A-PASSO.md`](docs/PASSO-A-PASSO.md)**.

Resumo:

| # | Node | Tipo | Para que serve |
|---|---|---|---|
| ① | `Webhook - Receber Metricas` | `Webhook` | Expõe a URL `POST /webhook/monitoramento-servidor` e entrega o payload em `$json.body` |
| ② | `Python - Analisar Servidor` | `Code` (Python) | Valida, classifica e monta motivo, ação recomendada e mensagem |
| ③ | `Switch - Classificar Status` | `Switch` | Lê `$json.status` e escolhe a saída: CRITICO / ALERTA / NORMAL / ERRO |
| ④ | `Email - Alerta CRITICO` | `Send Email` | Dispara o e-mail P1 com assunto `[P1 - CRITICO] ...` |
| ⑤ | `Email - Aviso ALERTA` | `Send Email` | Dispara o e-mail P2 com assunto `[P2 - ALERTA] ...` |
| ⑥ | `Sem Acao - Servidor Normal` | `No Operation` | Caminho “tudo certo” — não notifica, só segue para a resposta |
| ⑦ | `Responder Webhook` | `Respond to Webhook` | Devolve o diagnóstico completo em JSON para quem chamou |

> 📸 **Screenshot 2 — node Webhook configurado**
> Print mostrando método `POST`, path `monitoramento-servidor`, `Respond: Using 'Respond to Webhook' Node` e as URLs de Test/Production.
> `![Node Webhook](images/node-webhook.png)`

> 📸 **Screenshot 3 — Code node com o Python**
> Print do Code node com `Language: Python (Beta)` e o código visível.
> `![Code node Python](images/node-python.png)`

> 📸 **Screenshot 4 — Switch com as saídas renomeadas**
> Print mostrando as quatro saídas: CRITICO, ALERTA, NORMAL e ERRO.
> `![Node Switch](images/node-switch.png)`

---

## 7. Explicação da utilização do Python

Todo o **cérebro** da automação está em Python. O N8N cuida do transporte
(receber, rotear, enviar); o Python cuida da **decisão**.

O mesmo motor existe em duas formas, mantidas em paridade (há um teste que
compara as duas saídas):

| Arquivo | Onde roda | Uso |
|---|---|---|
| [`python/analisar_servidor.py`](python/analisar_servidor.py) | Terminal / CI | Versão CLI e importável. Aceita JSON por argumento ou stdin |
| [`python/code_node_n8n.py`](python/code_node_n8n.py) | Dentro do N8N | Versão autocontida colada no Code node (Pyodide não importa arquivos locais) |

### Regras de classificação

```text
Recursos (cpu, memoria, disco), em %:
    valor < 80    →  NORMAL
    80 ≤ valor < 90 →  ALERTA
    valor ≥ 90    →  CRITICO

Status do serviço:
    online / running / ativo        →  NORMAL
    degradado / degraded / lento    →  ALERTA
    offline / parado / error / ...  →  CRITICO
    valor desconhecido              →  CRITICO   (fail-safe)

Status final do servidor = PIOR nível encontrado entre as 4 dimensões.
O campo "motivo" agrega TODAS as ocorrências daquele nível.
```

Exemplo de agregação: CPU 85% (`ALERTA`) + disco 97% (`CRITICO`) → status final
`CRITICO`, e o motivo cita apenas o disco. Já CPU 95% + disco 99% → `CRITICO`
com os dois recursos no motivo.

### O que o Python devolve

Além dos 4 campos exigidos pelo desafio (`servidor`, `status`, `motivo`,
`acao_recomendada`), a saída traz campos que tornam a automação utilizável de
verdade:

| Campo | Para que serve |
|---|---|
| `recursos_afetados` | Lista os recursos que dispararam o status — útil para métricas |
| `prioridade` | `P1` / `P2` / `P4`, pronto para abrir chamado |
| `notificar` | Booleano — permite um IF simples em vez de comparar strings |
| `metricas` | Ecoa os valores normalizados (aceita `72`, `"72"` e `"72%"`) |
| `analisado_em` | Timestamp UTC ISO-8601, para auditoria |
| `versao_regras` | Versão do motor que gerou aquele diagnóstico |
| `mensagem` | Texto do alerta **já formatado** — o e-mail vira uma expression de 1 linha |

### Tratamento de erro

Payload inválido não derruba o workflow: o Code node captura a exceção e devolve
`status: "ERRO"`, que cai na saída de *fallback* do Switch e retorna ao chamador
com a descrição do problema — sem gerar e-mail falso-positivo.

---

## 8. Exemplos de entrada e saída

### Entrada (POST no webhook)

```json
{
  "servidor": "SRV-PACS-01",
  "cpu": 72,
  "memoria": 84,
  "disco": 93,
  "servico": "online"
}
```

### Saída (resposta HTTP do workflow)

```json
{
  "servidor": "SRV-PACS-01",
  "status": "CRITICO",
  "motivo": "Utilizacao de disco em 93% (limite critico: 90%).",
  "acao_recomendada": "Verificar espaco disponivel e realizar limpeza do servidor (logs antigos, dumps, imagens temporarias). Avaliar expansao do volume.",
  "recursos_afetados": ["disco"],
  "prioridade": "P1",
  "notificar": true,
  "metricas": { "cpu": 72.0, "memoria": 84.0, "disco": 93.0, "servico": "online" },
  "analisado_em": "2026-09-18T00:40:10+00:00",
  "versao_regras": "1.0.0",
  "mensagem": "ALERTA DE MONITORAMENTO\nServidor: SRV-PACS-01\n..."
}
```

### E-mail recebido pela equipe

**Assunto:** `[P1 - CRITICO] SRV-PACS-01 - acao imediata necessaria`

```text
ALERTA DE MONITORAMENTO
Servidor: SRV-PACS-01
Status: CRITICO
CPU: 72%
Memoria: 84%
Disco: 93%
Servico: online

Problema identificado:
Utilizacao de disco em 93% (limite critico: 90%).

Acao recomendada:
Verificar espaco disponivel e realizar limpeza do servidor (logs antigos,
dumps, imagens temporarias). Avaliar expansao do volume.

Prioridade: P1 | Analisado em (UTC): 2026-09-18T00:40:10+00:00
```

> 📸 **Screenshot 5 — e-mail recebido**
> Print do e-mail de alerta crítico na caixa de entrada.
> `![E-mail de alerta](images/email-alerta.png)`

---

## 9. Cenários de teste

Os payloads estão em [`examples/`](examples/) e podem ser disparados de uma vez
com [`examples/testar-webhook.sh`](examples/testar-webhook.sh).

### Cenário 1 — NORMAL

Servidor operando dentro dos limites. **Não gera e-mail.**

```json
{ "servidor": "SRV-APP-02", "cpu": 35, "memoria": 48, "disco": 61, "servico": "online" }
```

**Esperado:** `status: NORMAL` · `prioridade: P4` · `notificar: false` · saída ③ do Switch → NoOp.

### Cenário 2 — ALERTA

Memória em 84% — acima do limiar de atenção, abaixo do crítico.

```json
{ "servidor": "SRV-LIS-03", "cpu": 66, "memoria": 84, "disco": 72, "servico": "online" }
```

**Esperado:** `status: ALERTA` · `prioridade: P2` · e-mail `[P2 - ALERTA]`.

### Cenário 3 — CRÍTICO (disco)

Disco em 93%, acima do limiar crítico.

```json
{ "servidor": "SRV-PACS-01", "cpu": 72, "memoria": 84, "disco": 93, "servico": "online" }
```

**Esperado:** `status: CRITICO` · `prioridade: P1` · e-mail `[P1 - CRITICO]`.
Note que a memória em 84% (ALERTA) é *ofuscada* pelo disco: o pior nível vence.

### Cenário 4 — CRÍTICO (serviço indisponível) *(bônus)*

Recursos saudáveis, mas o serviço caiu.

```json
{ "servidor": "SRV-INT-05", "cpu": 12, "memoria": 22, "disco": 40, "servico": "offline" }
```

**Esperado:** `status: CRITICO` por causa do serviço, mesmo com métricas baixas.

### Cenário 5 — Payload inválido *(bônus)*

```json
{ "servidor": "SRV-ERRO-09", "cpu": 55, "memoria": 60 }
```

**Esperado:** `status: ERRO`, motivo `Campos obrigatorios ausentes: disco, servico`,
saída de fallback do Switch, **sem e-mail**.

### Testes automatizados

```bash
python3 -m unittest discover -s python -v
```

```text
Ran 14 tests in 0.001s
OK
```

> 📸 **Screenshot 6 — execução do workflow no N8N**
> Print da aba *Executions* mostrando os três cenários com os caminhos verdes diferentes.
> `![Execuções](images/execucoes.png)`

---

## 10. Como executar o projeto

### Pré-requisitos

- **N8N 1.x** (Docker, npm ou Cloud)
- **Python 3.10+** (apenas para rodar os testes e a versão CLI — o workflow não precisa)
- Uma conta **SMTP** (Gmail com senha de app, Outlook, Mailtrap, etc.)

### Passo 1 — Subir o N8N

```bash
docker volume create n8n_data

docker run -d --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e GENERIC_TIMEZONE="America/Sao_Paulo" \
  -e TZ="America/Sao_Paulo" \
  docker.n8n.io/n8nio/n8n
```

Acesse `http://localhost:5678`.

> Alternativa sem Docker: `npx n8n`

### Passo 2 — Importar o workflow

1. No N8N: menu **⋯ (canto superior direito) → Import from File**
2. Selecione `workflow/monitoramento-servidor.json`
3. O canvas aparece com os 7 nodes já conectados

### Passo 3 — Configurar a credencial SMTP

1. **Credentials → Add credential → SMTP**
2. Preencha (exemplo Gmail):

   | Campo | Valor |
   |---|---|
   | User | `seu-email@gmail.com` |
   | Password | senha de app (16 caracteres) — **não** a senha da conta |
   | Host | `smtp.gmail.com` |
   | Port | `465` |
   | SSL/TLS | ativado |

3. Abra os nodes **`Email - Alerta CRITICO`** e **`Email - Aviso ALERTA`**, selecione
   a credencial criada e ajuste `From Email` / `To Email`.

> ⚠️ Nunca comite credenciais. Exporte o workflow **sem** credenciais antes de subir ao Git.

### Passo 4 — Testar

1. Clique em **Execute workflow** (o webhook de teste fica escutando)
2. Copie a **Test URL** do node Webhook
3. Dispare os cenários:

```bash
chmod +x examples/testar-webhook.sh
./examples/testar-webhook.sh http://localhost:5678/webhook-test/monitoramento-servidor
```

Ou um por vez:

```bash
curl -X POST http://localhost:5678/webhook-test/monitoramento-servidor \
     -H "Content-Type: application/json" \
     -d @examples/servidor_critico.json
```

### Passo 5 — Ativar em produção

Salve o workflow e ligue o toggle **Active**. A URL de produção passa a ser
`http://localhost:5678/webhook/monitoramento-servidor` (sem o `-test`).

### Rodar o motor Python fora do N8N

```bash
# via argumento
python3 python/analisar_servidor.py '{"servidor":"SRV-PACS-01","cpu":72,"memoria":84,"disco":93,"servico":"online"}'

# via stdin
cat examples/servidor_critico.json | python3 python/analisar_servidor.py

# testes
python3 -m unittest discover -s python -v
```

### Regenerar o workflow após alterar as regras

O JSON do workflow é gerado a partir de `python/code_node_n8n.py`:

```bash
python3 docs/gerar_workflow.py
```

---

## 11. Estrutura do repositório

```text
rpa-monitoramento-n8n-python/
│
├── README.md                          # Esta documentação
├── LICENSE                            # Licença MIT
├── .gitignore
│
├── workflow/
│   └── monitoramento-servidor.json    # Workflow pronto para importar no N8N
│
├── python/
│   ├── analisar_servidor.py           # Motor de análise (CLI + biblioteca)
│   ├── code_node_n8n.py               # Mesma lógica, para colar no Code node
│   └── test_analisar_servidor.py      # 14 testes unitários
│
├── examples/
│   ├── servidor_normal.json           # Cenário 1
│   ├── servidor_alerta.json           # Cenário 2
│   ├── servidor_critico.json          # Cenário 3
│   ├── servidor_servico_offline.json  # Cenário 4 (bônus)
│   ├── payload_invalido.json          # Cenário 5 (bônus)
│   └── testar-webhook.sh              # Dispara todos os cenários de uma vez
│
├── docs/
│   ├── PASSO-A-PASSO.md               # Guia node por node (construção manual)
│   └── gerar_workflow.py              # Gera o JSON do workflow a partir do Python
│
└── images/
    ├── workflow-n8n.png               # Screenshot 1 — canvas completo
    ├── node-webhook.png               # Screenshot 2
    ├── node-python.png                # Screenshot 3
    ├── node-switch.png                # Screenshot 4
    ├── email-alerta.png               # Screenshot 5
    └── execucoes.png                  # Screenshot 6
```

---

## 12. Melhorias futuras

**Curto prazo**

- Persistir cada análise em banco (PostgreSQL/MySQL) para histórico e SLA.
- Adicionar canal Telegram/Slack em paralelo ao e-mail.
- Abrir chamado automaticamente no GLPI/Jira quando o status for `CRITICO`.
- Autenticar o webhook (Header Auth) para impedir POST não autorizado.

**Médio prazo**

- **Deduplicação de alertas**: não reenviar o mesmo alerta antes de N minutos.
- **Limiares por servidor**, vindos de uma tabela de configuração — um servidor de
  banco tolera memória alta; um servidor de arquivos, não.
- **Alerta de tendência**: disparar quando o disco cresce X% ao dia, antes de
  chegar a 90%.
- Dashboard (Grafana/Metabase) sobre o histórico gravado.

**Longo prazo**

- Detecção de anomalia por baseline estatístico em vez de limiar fixo.
- **Auto-remediação**: para casos seguros e conhecidos (rotacionar log, limpar
  `/tmp`), executar a ação e só então notificar o que foi feito.
- Agente coletor próprio (`psutil`) empacotado para instalação na frota.

---

## 13. Conclusão

O projeto mostra, de ponta a ponta, o padrão que torna o N8N poderoso em
automações de infraestrutura: **o N8N orquestra, o Python decide.**

O N8N resolve com zero código o que é chato de escrever — servidor HTTP,
roteamento condicional, envio de e-mail, retries, logging de execução. O Python
resolve o que ferramenta visual faz mal — regra de negócio com condições
compostas, priorização e texto dinâmico. Cada camada faz o que faz melhor, e o
resultado é uma automação que dá para ler, testar e evoluir.

Do ponto de vista operacional, o ganho é direto: a triagem que antes dependia de
alguém olhar um dashboard passa a acontecer em milissegundos, com critério
uniforme e ação recomendada junto do alerta. E, por ser um contrato simples de
webhook, o mesmo motor atende qualquer coletor — de um `cron` de três linhas a
um Prometheus completo.

---

## Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE).

## Autor

**Gabriel Felipe Santana Belarmino**
Desenvolvedor Backend · Especialista em Suporte de Sistemas

[![GitHub](https://img.shields.io/badge/GitHub-GabrielFSantana-181717?style=flat-square&logo=github)](https://github.com/GabrielFSantana)

---

<sub>Desafio de projeto — Bootcamp Santander Automação com N8N · Digital Innovation One (DIO)</sub>
