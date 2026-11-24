"""Gera os gráficos das Figuras 3 e 4 do TCC a partir dos dados do experimento.

- grafico_exemplos.png (Figura 3): score efetivo das estratégias com e sem exemplos, com os dois
  LLMs juntos e em cada LLM.
- grafico_cobertura100.png (Figura 4): testbenches aprovados com 100% de cobertura (linha, desvio e
  alternância) que deixaram ao menos um mutante sem detectar, por LLM e no total.

Os valores são calculados de PLANILHA_R1/R2 (pdf_comum.py) e de coberturas.json, com arredondamento
ABNT, e conferidos com os números do TCC (assert). Sem argumento, grava em documentacao/figuras/.
Uso (WSL): python3 documentacao/analise/figuras/graficos_resultados.py [pasta_de_saida]
Precisa de matplotlib e reportlab (o pdf_comum.py importa o reportlab).
"""
import json
import os
import sys
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
EST = os.path.join(AQUI, "..", "estatistica")
sys.path.insert(0, EST)
from pdf_comum import MODELOS, RODADAS  # noqa: E402

DOC = os.path.normpath(os.path.join(AQUI, "..", ".."))
SAIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DOC, "figuras")
COB = json.load(open(os.path.join(EST, "coberturas.json"), encoding="utf-8"))
G, GM = MODELOS
COM, SEM = [1, 3, 5], [0, 2, 4]          # versões Few-shot e Zero-shot

AZUL, LARANJA, CINZA, CINZA_CLARO = "#1F4E79", "#E07B00", "#7F7F7F", "#A6A6A6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "hatch.linewidth": 1.2})


def arr(x, nd=1):
    """Arredondamento ABNT (NBR 5891), com vírgula decimal."""
    x = Fraction(x)
    d = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(
        Decimal(1).scaleb(-nd), rounding=ROUND_HALF_EVEN)
    return f"{d:f}".replace(".", ",")


def mortos(cel):
    return int(cel.split("/")[0]) if "/" in cel else 0


def score_efetivo(modelos, estrategias):
    det = n = 0
    for m in modelos:
        for r in (1, 2):
            for linha in RODADAS[r][m]:
                for e in estrategias:
                    det += mortos(linha[e])
                    n += 1
    return Fraction(100 * det, 4 * n)


def cheio(k, modelos):
    """(com 100% no tipo k, desses os que deixaram mutante sem detectar), só aprovados."""
    total = vivos = 0
    for m in modelos:
        for r in (1, 2):
            for d, linha in enumerate(RODADAS[r][m]):
                for e, cel in enumerate(linha):
                    v = COB[m][str(r)][d][k][e]
                    if "/" in cel and isinstance(v, (int, float)) and v >= 100:
                        total += 1
                        vivos += mortos(cel) < 4
    return total, vivos


def estilo(ax, ylabel):
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel(ylabel)
    ax.yaxis.grid(True, color="#DDDDDD", linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


# ---------------------------------------------------------------- Figura 3
grupos = [("Total", MODELOS), ("GPT-5.6 Luna", [G]), ("Gemini 3.5\nFlash-Lite", [GM])]
sem = [score_efetivo(ms, SEM) for _, ms in grupos]
com = [score_efetivo(ms, COM) for _, ms in grupos]
assert [arr(x) for x in sem] == ["47,1", "53,8", "40,4"], [arr(x) for x in sem]
assert [arr(x) for x in com] == ["61,0", "62,1", "60,0"], [arr(x) for x in com]

fig, ax = plt.subplots(figsize=(6.0, 4.4))
x = range(len(grupos))
w = 0.34
b1 = ax.bar([i - w / 2 for i in x], [float(v) for v in sem], w, color=CINZA_CLARO,
            edgecolor="black", linewidth=0.6, hatch="//", label="Sem exemplos (Zero-shot)")
b2 = ax.bar([i + w / 2 for i in x], [float(v) for v in com], w, color=AZUL,
            edgecolor="black", linewidth=0.6, label="Com exemplos (Few-shot)")
for barras, vals in ((b1, sem), (b2, com)):
    for b, v in zip(barras, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, arr(v),
                ha="center", va="bottom", fontsize=9)
ax.set_xticks(list(x))
ax.set_xticklabels([g for g, _ in grupos])
estilo(ax, "Score efetivo (%)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2, frameon=False, fontsize=9)
fig.tight_layout()
os.makedirs(SAIDA, exist_ok=True)
fig.savefig(os.path.join(SAIDA, "grafico_exemplos.png"), dpi=300)
plt.close(fig)

# ---------------------------------------------------------------- Figura 4
tipos = [("linha", "Linha"), ("branch", "Desvio"), ("toggle", "Alternância")]
series = [("GPT-5.6 Luna", [G], AZUL, None), ("Gemini 3.5 Flash-Lite", [GM], LARANJA, "//"),
          ("Total", MODELOS, CINZA, "..")]
dados = {nome: [cheio(k, ms) for k, _ in tipos] for nome, ms, _, _ in series}
assert dados["Total"] == [(122, 63), (116, 58), (56, 18)], dados["Total"]
assert dados["GPT-5.6 Luna"] == [(62, 20), (62, 24), (31, 8)], dados["GPT-5.6 Luna"]
assert dados["Gemini 3.5 Flash-Lite"] == [(60, 43), (54, 34), (25, 10)], dados

fig, ax = plt.subplots(figsize=(6.6, 4.4))
w = 0.27
for j, (nome, _, cor, hachura) in enumerate(series):
    pos = [i + (j - 1) * w for i in range(len(tipos))]
    vals = [Fraction(100 * v, t) for t, v in dados[nome]]
    barras = ax.bar(pos, [float(v) for v in vals], w, color=cor, edgecolor="black",
                    linewidth=0.6, hatch=hachura, label=nome)
    for b, v, (t, vv) in zip(barras, vals, dados[nome]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{arr(v)}\n({vv}/{t})",
                ha="center", va="bottom", fontsize=7.5, linespacing=1.1)
ax.set_xticks(range(len(tipos)))
ax.set_xticklabels([t for _, t in tipos])
estilo(ax, "Testbenches com 100% de cobertura que\ndeixaram mutante sem detectar (%)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(SAIDA, "grafico_cobertura100.png"), dpi=300)
plt.close(fig)
print("ok", SAIDA)
