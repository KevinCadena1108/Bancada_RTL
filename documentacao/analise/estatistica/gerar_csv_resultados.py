"""Grava documentacao/resultados/resultados_testbenches.csv: uma linha por testbench do experimento (240).

Os dados são os mesmos da planilha do experimento, já copiados no repositório: a linha
"Mutantes" de cada bloco em PLANILHA_R1/R2 (pdf_comum.py) e as coberturas em coberturas.json
(conferidos célula a célula contra a planilha em 15/11/2026, zero diferenças).

O CSV usa ponto e vírgula como separador e vírgula decimal, para abrir direto no Excel em
português. Uso: python3 documentacao/analise/estatistica/gerar_csv_resultados.py
"""
import csv
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from pdf_comum import CIRCUITOS, ESTR, MODELOS, NOME_ESTR, RODADAS  # noqa: E402

COB = json.load(open(os.path.join(AQUI, "coberturas.json"), encoding="utf-8"))
NOME_TCC = {"Fsm serialdp": "Fsm serialdp", "Exams/2012 q2fsm": "Exams/2012 q2fsm",
            "Cout Clock": "Count clock", "Cs450/gshare": "Cs450/gshare", "Lemmings1": "Lemmings1",
            "wbuart32": "wbuart32", "Cordic": "CORDIC", "Conwaylife": "Conwaylife",
            "fancytimer": "Fancytimer", "I2C Slave": "SPI Master"}
RESULTADO = {"Não passou": "reprovado", "Timeout": "tempo esgotado"}


def num(v):
    return "" if v is None or isinstance(v, str) else f"{v:.1f}".replace(".", ",")


linhas = []
for m in MODELOS:
    for r in (1, 2):
        for d, circ in enumerate(CIRCUITOS):
            for e, sigla in enumerate(ESTR):
                cel = RODADAS[r][m][d][e]
                ok = "/" in cel
                cob = {k: COB[m][str(r)][d][k][e] for k in ("linha", "branch", "toggle")}
                linhas.append({
                    "llm": m, "rodada": r, "modulo": NOME_TCC[circ], "estrategia": NOME_ESTR[sigla],
                    "resultado": "aprovado" if ok else RESULTADO[cel],
                    "mutantes_detectados": int(cel.split("/")[0]) if ok else 0,
                    "cobertura_linha": num(cob["linha"]), "cobertura_desvio": num(cob["branch"]),
                    "cobertura_alternancia": num(cob["toggle"]),
                })

# conferência com os números do TCC
assert len(linhas) == 240
assert sum(l["resultado"] == "aprovado" for l in linhas) == 175
assert sum(l["mutantes_detectados"] for l in linhas) == 519

doc = os.path.normpath(os.path.join(AQUI, "..", ".."))
os.makedirs(os.path.join(doc, "resultados"), exist_ok=True)
caminho = os.path.join(doc, "resultados", "resultados_testbenches.csv")
with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=";")
    w.writeheader()
    w.writerows(linhas)
print("ok", caminho, len(linhas), "linhas")
