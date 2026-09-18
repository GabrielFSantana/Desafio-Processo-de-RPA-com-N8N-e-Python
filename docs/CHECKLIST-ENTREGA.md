# Checklist de entrega — Desafio DIO

Marque tudo antes de enviar o link do repositório na plataforma da DIO.

## 1. Ambiente e execução

- [ ] Microsserviço Python rodando (`iniciar-api.bat` / `./iniciar-api.sh`)
- [ ] `curl http://127.0.0.1:8000/saude` responde `{"status": "ok", ...}`
- [ ] N8N rodando (`http://localhost:5678`)
- [ ] Workflow `workflow/monitoramento-servidor.json` importado sem erro
- [ ] Node HTTP Request apontando para a URL correta da API
- [ ] Credencial **SMTP** criada e testada
- [ ] `From Email` e `To Email` ajustados nos dois nodes de e-mail
- [ ] Workflow **salvo** e com toggle **Active** ligado

## 2. Testes executados

- [ ] Cenário 1 — **NORMAL** (`SRV-APP-03`) → `status: NORMAL`, **nenhum e-mail**
- [ ] Cenário 2 — **ALERTA** (`SRV-BD-04`) → e-mail `[P2 - ALERTA]` recebido
- [ ] Cenário 3 — **CRÍTICO** (`SRV-CFTV-02`) → e-mail `[P1 - CRITICO]` recebido
- [ ] Cenário 4 — **serviço offline** (`SRV-PORTARIA-01`) → classificado como CRÍTICO
- [ ] Cenário 5 — **payload inválido** → `status: ERRO`, sem e-mail
- [ ] `python3 -m unittest discover -s python -v` → **14 testes OK**

## 3. Screenshots em `images/`

- [ ] `workflow-n8n.png` — canvas completo
- [ ] `node-webhook.png` — node Webhook configurado
- [ ] `node-http-request.png` — node HTTP Request chamando a API Python
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
git add .
git commit -m "feat: RPA de monitoramento de servidores com N8N e Python"
git push -u origin main
```

Se o repositório remoto já tiver um commit inicial (README criado pelo GitHub):

```bash
git pull origin main --allow-unrelated-histories
# resolva o conflito no README.md mantendo a versão deste projeto
git push -u origin main
```
