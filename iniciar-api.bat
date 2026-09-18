@echo off
REM ============================================================
REM  Sobe a API de analise em Python (necessaria para o workflow)
REM  Deixe esta janela aberta enquanto usar o n8n.
REM ============================================================
cd /d "%~dp0"
py python\api_analise.py
pause
