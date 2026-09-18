#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes unitarios do motor de analise.

Executar:  python3 -m unittest discover -s python -v
       ou:  python3 python/test_analisar_servidor.py
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analisar_servidor import analisar, normalizar, PayloadInvalido  # noqa: E402


class TestClassificacao(unittest.TestCase):

    def test_cenario_1_normal(self):
        r = analisar({"servidor": "SRV-APP-02", "cpu": 35, "memoria": 48,
                      "disco": 61, "servico": "online"})
        self.assertEqual(r["status"], "NORMAL")
        self.assertEqual(r["prioridade"], "P4")
        self.assertFalse(r["notificar"])
        self.assertEqual(r["recursos_afetados"], [])

    def test_cenario_2_alerta_memoria(self):
        r = analisar({"servidor": "SRV-LIS-03", "cpu": 66, "memoria": 84,
                      "disco": 72, "servico": "online"})
        self.assertEqual(r["status"], "ALERTA")
        self.assertEqual(r["prioridade"], "P2")
        self.assertIn("memoria", r["recursos_afetados"])
        self.assertTrue(r["notificar"])

    def test_cenario_3_critico_disco(self):
        r = analisar({"servidor": "SRV-PACS-01", "cpu": 72, "memoria": 84,
                      "disco": 93, "servico": "online"})
        self.assertEqual(r["status"], "CRITICO")
        self.assertEqual(r["prioridade"], "P1")
        self.assertEqual(r["recursos_afetados"], ["disco"])
        self.assertIn("disco", r["motivo"])

    def test_servico_offline_gera_critico(self):
        r = analisar({"servidor": "SRV-INT-05", "cpu": 10, "memoria": 20,
                      "disco": 30, "servico": "offline"})
        self.assertEqual(r["status"], "CRITICO")
        self.assertEqual(r["recursos_afetados"], ["servico"])

    def test_servico_desconhecido_e_tratado_como_critico(self):
        r = analisar({"servidor": "SRV-X", "cpu": 1, "memoria": 1,
                      "disco": 1, "servico": "sei-la"})
        self.assertEqual(r["status"], "CRITICO")

    def test_pior_nivel_vence(self):
        # memoria em ALERTA e disco em CRITICO -> status final CRITICO,
        # e o motivo deve citar somente as ocorrencias criticas.
        r = analisar({"servidor": "SRV-MIX", "cpu": 85, "memoria": 82,
                      "disco": 97, "servico": "online"})
        self.assertEqual(r["status"], "CRITICO")
        self.assertEqual(r["recursos_afetados"], ["disco"])

    def test_multiplos_criticos_sao_agregados(self):
        r = analisar({"servidor": "SRV-MIX-2", "cpu": 95, "memoria": 91,
                      "disco": 99, "servico": "online"})
        self.assertEqual(r["status"], "CRITICO")
        self.assertEqual(sorted(r["recursos_afetados"]), ["cpu", "disco", "memoria"])

    def test_limites_de_fronteira(self):
        self.assertEqual(analisar({"servidor": "s", "cpu": 79, "memoria": 0,
                                   "disco": 0, "servico": "online"})["status"], "NORMAL")
        self.assertEqual(analisar({"servidor": "s", "cpu": 80, "memoria": 0,
                                   "disco": 0, "servico": "online"})["status"], "ALERTA")
        self.assertEqual(analisar({"servidor": "s", "cpu": 89, "memoria": 0,
                                   "disco": 0, "servico": "online"})["status"], "ALERTA")
        self.assertEqual(analisar({"servidor": "s", "cpu": 90, "memoria": 0,
                                   "disco": 0, "servico": "online"})["status"], "CRITICO")


class TestEntrada(unittest.TestCase):

    def test_aceita_percentual_como_string(self):
        m = normalizar({"servidor": "s", "cpu": "72%", "memoria": "84",
                        "disco": "93,5", "servico": "ONLINE"})
        self.assertEqual(m["cpu"], 72.0)
        self.assertEqual(m["disco"], 93.5)
        self.assertEqual(m["servico"], "online")

    def test_campo_ausente(self):
        with self.assertRaises(PayloadInvalido):
            analisar({"servidor": "s", "cpu": 10, "memoria": 10})

    def test_valor_fora_do_intervalo(self):
        with self.assertRaises(PayloadInvalido):
            analisar({"servidor": "s", "cpu": 150, "memoria": 10,
                      "disco": 10, "servico": "online"})

    def test_valor_nao_numerico(self):
        with self.assertRaises(PayloadInvalido):
            analisar({"servidor": "s", "cpu": "muito", "memoria": 10,
                      "disco": 10, "servico": "online"})


class TestSaida(unittest.TestCase):

    def test_saida_e_serializavel_e_tem_campos_do_desafio(self):
        r = analisar({"servidor": "SRV-PACS-01", "cpu": 72, "memoria": 84,
                      "disco": 93, "servico": "online"})
        json.dumps(r)  # nao pode levantar excecao
        for campo in ("servidor", "status", "motivo", "acao_recomendada"):
            self.assertIn(campo, r)

    def test_mensagem_tem_o_formato_do_desafio(self):
        r = analisar({"servidor": "SRV-PACS-01", "cpu": 72, "memoria": 84,
                      "disco": 93, "servico": "online"})
        msg = r["mensagem"]
        self.assertIn("ALERTA DE MONITORAMENTO", msg)
        self.assertIn("Servidor: SRV-PACS-01", msg)
        self.assertIn("Status: CRITICO", msg)
        self.assertIn("CPU: 72%", msg)
        self.assertIn("Memoria: 84%", msg)
        self.assertIn("Disco: 93%", msg)
        self.assertIn("Problema identificado:", msg)
        self.assertIn("Acao recomendada:", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
