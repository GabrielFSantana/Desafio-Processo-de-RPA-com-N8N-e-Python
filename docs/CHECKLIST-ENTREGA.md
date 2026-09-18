# Checklist de entrega — Desafio DIO

Marque tudo antes de enviar o link do repositório na plataforma da DIO.

## 1. Ambiente e execução

- [ ] N8N rodando (`http://localhost:5678`)
- [ ] Workflow `workflow/monitoramento-servidor.json` importado sem erro
- [ ] Code node aberto e confirmado com **Language: Python (Beta)**
- [ ] Credencial **SMTP** criada e testada
- [ ] `From Email` e `To Email` ajustados nos dois nodes de e-mail
- [ ] Workflow **salvo** e com toggle **Active** ligado

## 2. Testes executados

- [ ] Cenário 1 — **NORMAL** → retorna `status: NORMAL`, **nenhum e-mail**
- [ ] Cenário 2 — **ALERTA** → e-mail `[P2 - ALERTA]` recebido
- [ ] Cenário 3 — **CRÍTICO** → e-mail `[P1 - CRITICO]` recebido
- [ ] Cenário 4 — **serviço offline** → classificado como CRÍTICO
- [ ] Cenário 5 — **payload inválido** → `status: ERRO`, sem e-mail
- [ ] `python3 -m unittest discover -s python -v` → **14 testes OK**

## 3. Screenshots em `images/`

- [ ] `workflow-n8n.png` — canvas completo
- [ ] `node-webhook.png` — node Webhook configurado
- [ ] `node-python.png` — Code node com o Python
- [ ] `node-switch.png` — Switch com as 4 saídas nomeadas
- [ ] `email-alerta.png` — e-mail recebido
- [ ] `execucoes.png` — aba Executions com os cenários
- [ ] Nenhum dado sensível visível nos prints (e-mails reais, hostnames internos, tokens)

## 4. README

- [ ] Todos os 6 marcadores `📸 Screenshot` substituídos pelas imagens reais
- [ ] Links internos funcionando (clique em todos no GitHub)
- [ ] Badges renderizando
- [ ] Seu nome e link do GitHub corretos no rodapé

## 5. Segurança antes do `git push`

- [ ] `workflow/monitoramento-servidor.json` **sem** senha/host de SMTP real
- [ ] Nenhum `.env` ou arquivo de credencial commitado (`git status` limpo)
- [ ] `git log -p | grep -i -E "senha|password|smtp|token"` não retorna nada sensível
- [ ] Endereços de e-mail no JSON são genéricos (`@suaempresa.com.br`)

## 6. Repositório no GitHub

- [ ] Repositório criado e **público**
- [ ] `git push -u origin main` concluído
- [ ] README aparece renderizado na home do repositório
- [ ] Descrição curta preenchida nas configurações do repo
- [ ] Topics adicionados: `n8n`, `python`, `rpa`, `automation`, `webhook`, `dio`, `monitoring`
- [ ] Estrutura de pastas visível e correta

## 7. Entrega na DIO

- [ ] Link do repositório enviado na plataforma
- [ ] Link testado em aba anônima (confirma que está público)

---

### Comandos de push

```bash
cd rpa-monitoramento-n8n-python

git init
git add .
git commit -m "feat: RPA de monitoramento de servidores com N8N e Python"
git branch -M main
git remote add origin https://github.com/GabrielFSantana/Desafio-Processo-de-RPA-com-N8N-e-Python.git
git push -u origin main
```

Se o repositório já tiver um commit inicial (README criado pelo GitHub):

```bash
git pull origin main --allow-unrelated-histories
# resolva o conflito no README.md mantendo a versão deste projeto
git push -u origin main
```
