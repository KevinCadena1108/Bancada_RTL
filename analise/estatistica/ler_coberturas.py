"""Le as coberturas (linha, desvio, alternancia, FSM) da planilha colada como texto e grava
o coberturas.json; confere celula a celula que a linha Mutantes bate com o pdf_comum.

Uso: python ler_coberturas.py planilha_colada.txt [saida.json]
"""
import json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from pdf_comum import MODELOS, PLANILHA_R1, PLANILHA_R2

METRICAS = {"Linha": "linha", "Desvio": "branch", "Alternancia": "toggle", "Máquina Esta": "fsm", "Mutantes": "mut"}


def num(c):
    c = c.strip()
    if c in ("Sem FSM", ""):
        return None
    if "/" in c or c in ("Não passou", "Timeout"):
        return c
    return float(c.replace(",", "."))


linhas = open(sys.argv[1], encoding="utf-8").read().split("\n")
blocos = []  # cada bloco: {rodada: {metrica: [6 valores]}}
atual = None
for l in linhas:
    col = l.split("\t")
    if "Zero-shot" in l:
        atual = {1: {}, 2: {}}
        blocos.append(atual)
        continue
    if atual is None:
        continue
    idx = [i for i, c in enumerate(col) if c.strip() in METRICAS]
    for n, i in enumerate(idx[:2]):
        atual[n + 1][METRICAS[col[i].strip()]] = [num(c) for c in col[i + 1:i + 7]]

blocos = [b for b in blocos if any(b[1].get("mut") or [None])]
print("blocos:", len(blocos))
assert len(blocos) == 20
dados = {}
for m, modelo in enumerate(MODELOS):
    dados[modelo] = {}
    for r, plan in ((1, PLANILHA_R1), (2, PLANILHA_R2)):
        lista = []
        for d in range(10):
            b = blocos[m * 10 + d][r]
            if b["mut"] != plan[modelo][d]:
                print("DIFERE", modelo, r, d, b["mut"], plan[modelo][d])
            lista.append({k: v for k, v in b.items() if k != "mut"})
        dados[modelo][r] = lista
saida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, "coberturas.json")
json.dump(dados, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
