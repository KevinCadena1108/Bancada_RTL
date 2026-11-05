"""Correlacao de Spearman entre cobertura e score de mutacao, so com TBs que passaram.

Para cada metrica (linha, desvio, alternancia, FSM): rho geral; rho dentro do design (tira a
media de cada modelo x circuito, p por permutacao dentro do grupo); e quantos TBs com 100% de
cobertura deixaram mutante vivo. Uso: python cobertura_mutacao.py [coberturas.json]
"""
import json, os, sys
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from pdf_comum import MODELOS, RODADAS

cob = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "coberturas.json"), encoding="utf-8"))
rng = np.random.default_rng(1)
pontos = []  # (modelo, design, metrica->valor, mut)
for modelo in MODELOS:
    for r in (1, 2):
        for d in range(10):
            for e in range(6):
                c = RODADAS[r][modelo][d][e]
                if "/" not in c:
                    continue  # nao passou / timeout: nao tem score de mutacao
                m = cob[modelo][str(r)][d]
                pontos.append((modelo, d, {k: m[k][e] for k in m}, int(c.split("/")[0]) / 4))

print("TBs que passaram:", len(pontos))
for k in ("linha", "branch", "toggle", "fsm"):
    p = [(mo, d, v[k], mu) for mo, d, v, mu in pontos if v[k] is not None]
    x = np.array([a[2] for a in p]); y = np.array([a[3] for a in p])
    rho, pv = spearmanr(x, y)
    # dentro do design: tira a media de cada (modelo, design) e permuta so dentro do grupo
    g = defaultdict(list)
    for i, a in enumerate(p):
        g[(a[0], a[1])].append(i)
    def centrado(yy):
        xc, yc = x.copy(), yy.copy()
        for idx in g.values():
            xc[idx] -= x[idx].mean(); yc[idx] -= yy[idx].mean()
        return spearmanr(xc, yc)[0]
    rw = centrado(y)
    perm = []
    for _ in range(5000):
        yy = y.copy()
        for idx in g.values():
            yy[idx] = rng.permutation(y[idx])
        perm.append(centrado(yy))
    pw = (np.sum(np.abs(np.nan_to_num(perm)) >= abs(rw)) + 1) / 5001
    cheio = x >= 100
    print(f"{k:7s} n={len(p):3d}  rho={rho:+.3f} p={pv:.4f} | dentro do design rho={rw:+.3f} p={pw:.4f}"
          f" | cob=100%: {cheio.sum():3d} TBs, {np.sum(cheio & (y < 1)):3d} com mutante vivo"
          f" | cob<100%: {np.sum(~cheio):3d}, {np.sum(~cheio & (y == 1)):3d} matam 4/4")
for modelo in MODELOS:
    p = [a for a in pontos if a[0] == modelo]
    x = [a[2]["linha"] for a in p]; y = [a[3] for a in p]
    print(modelo, "linha: rho=%.3f p=%.4f n=%d" % (*spearmanr(x, y), len(p)))
