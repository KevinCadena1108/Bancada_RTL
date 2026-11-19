# -*- coding: utf-8 -*-
"""Gera o PDF "Posto médio das estratégias de prompt" (método, resultados e referência).

Os dados vêm do pdf_comum.py (PLANILHA_R1 e PLANILHA_R2), o mesmo lugar dos outros PDFs; o valor
analisado é a média das 2 rodadas. Os postos médios são os mesmos da seção Resultados do TCC
(3,675 e 3,625 aparecem com 3 casas porque são exatos).
Uso: python gera_pdf_posto.py [saida.pdf]   (padrão: documentacao/posto_medio_passo_a_passo.pdf)
"""
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_comum import MODELOS, abrev, br, celulas, saida, valores  # registra as fontes DejaVu

OUT = saida("posto_medio_passo_a_passo.pdf")
EST = ["ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"]
ESTLONG = ["Zero-shot", "Few-shot", "Especialista Zero-shot", "Especialista Few-shot",
           "Planning Zero-shot", "Planning Few-shot"]
# nomes curtos dos circuitos, na ordem de CIRCUITOS do pdf_comum
NOMES = ["Fsm serialdp", "Exams/2012 q2fsm", "Count clock", "Cs450/gshare", "Lemmings1",
         "wbuart32", "CORDIC", "Conwaylife", "Fancytimer", "SPI Master"]


def bloco(modelo):
    """{circuito: ([rodada 1], [rodada 2])} com os mutantes mortos (NP/Timeout = 0)."""
    return dict(zip(NOMES, zip(valores(modelo, 1), valores(modelo, 2))))


GPT, GEM = bloco(MODELOS[0]), bloco(MODELOS[1])


def medias(b):
    return {c: [(r1[i] + r2[i]) / 2 for i in range(6)] for c, (r1, r2) in b.items()}


def postos(vals):
    """Postos 1 (menor) a 6 (maior); empate = média das posições ocupadas."""
    ordem = sorted(range(6), key=lambda i: vals[i])
    p = [0.0] * 6
    i = 0
    while i < 6:
        j = i
        while j + 1 < 6 and vals[ordem[j + 1]] == vals[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            p[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return p


def f1(x):
    """Número com uma casa e vírgula: 1,5; 4,0."""
    return f"{x:.1f}".replace(".", ",")


def f2(x):
    """Posto médio: 2 casas, ou 3 quando o valor exato tem 3 casas (3,675 e 3,625), como no TCC.
    Com 2 casas fixas, 3,675 virava 3,67 e 3,625 virava 3,62."""
    s = f"{x:.3f}"
    if s.endswith("0"):
        s = s[:-1]
    return s.replace(".", ",")


# ---------- estilos ----------
AZUL = colors.HexColor("#123a5e")
VERDE = colors.HexColor("#1a7a4c")
CINZA = colors.HexColor("#eef1f4")
BORD = colors.HexColor("#c9d2da")
H0 = ParagraphStyle("H0", fontName="DVB", fontSize=17, textColor=AZUL, alignment=TA_CENTER,
                    leading=22, spaceAfter=6)
H1 = ParagraphStyle("H1", fontName="DVB", fontSize=12.5, textColor=colors.white, backColor=AZUL,
                    borderPadding=(5, 7, 5, 7), spaceBefore=12, spaceAfter=8, leading=16)
H2 = ParagraphStyle("H2", fontName="DVB", fontSize=11, textColor=AZUL, spaceBefore=8, spaceAfter=3,
                    leading=14)
BODY = ParagraphStyle("BODY", fontName="DV", fontSize=9.8, textColor=colors.HexColor("#1a2430"),
                      alignment=TA_JUSTIFY, leading=14, spaceAfter=6)
BULL = ParagraphStyle("BULL", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=2)
CAP = ParagraphStyle("CAP", fontName="DV", fontSize=8.5, textColor=colors.HexColor("#55636f"),
                     leading=11, spaceBefore=2, spaceAfter=10)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=9, leading=12.5)


def P(t, st=BODY):
    return Paragraph(t, st)


def B(t):
    return Paragraph(t, BULL, bulletText="•")


def estilo_tabela(cor, fonte=8.3):
    return [("BACKGROUND", (0, 0), (-1, 0), cor), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "DVB"), ("FONTNAME", (0, 1), (-1, -1), "DV"),
            ("FONTSIZE", (0, 0), (-1, -1), fonte), ("GRID", (0, 0), (-1, -1), 0.4, BORD),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]


story = []
st = story.append
st(P("Posto médio das estratégias de prompt — método, resultados e referência", H0))
st(P("Como a métrica é calculada, os resultados de todas as estratégias e modelos (um por um) e a "
     "fonte da fórmula. Valor analisado: mutantes mortos por circuito (média das 2 rodadas; "
     "“Não passou” e “Timeout” = 0).", SMALL))

# 1. o que é / fórmula
st(P("1. O que é e qual a fórmula", H1))
st(P("O posto médio (<i>average rank</i>) ordena as estratégias para apontar a melhor. Em cada "
     "circuito, as seis estratégias são ordenadas e recebem um posto de 1 (pior) a 6 (melhor); o "
     "posto médio de cada estratégia é a média de seus postos sobre os N circuitos. Quanto "
     "<b>maior</b> o posto médio, melhor a estratégia."))
st(P("Posto médio da estratégia j:  <b>R<sub>j</sub> = (1/N) · Σ<sub>i</sub> r<sub>i</sub><super>j</super></b>, "
     "onde r<sub>i</sub><super>j</super> é o posto da estratégia j no circuito i e N é o número de "
     "circuitos.", SMALL))
tb = Table([[P("<b>Fonte da fórmula:</b> o ranqueamento de métodos por posto médio sobre múltiplos "
               "conjuntos de dados é estabelecido por DEMŠAR (2006); o ranqueamento por postos vem "
               "de FRIEDMAN (1937). A prática de repetir as execuções de algoritmos aleatórios (os LLMs) "
               "e analisar a média é recomendada por ARCURI; BRIAND (2011).", SMALL)]],
           colWidths=[174 * mm])
tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eaf2fa")),
                        ("BOX", (0, 0), (-1, -1), 0.8, AZUL),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
st(tb)

# 2. passo a passo
st(P("2. Passo a passo do cálculo", H1))
st(B("<b>Passo 1</b> — valor de cada estratégia por circuito: mutantes mortos, média das 2 rodadas "
     "(“Não passou” e “Timeout” = 0)."))
st(B("<b>Passo 2</b> — em cada circuito, ordene as 6 estratégias e dê postos de 1 (pior) a 6 (melhor)."))
st(B("<b>Passo 3</b> — empates recebem a média dos postos (ex.: dois empatados nas posições 2 e 3 → "
     "2,5 cada)."))
st(B("<b>Passo 4</b> — repita para todos os circuitos (10 por modelo; 20 ao juntar os dois modelos)."))
st(B("<b>Passo 5</b> — posto médio = soma dos postos ÷ N. Maior posto médio = melhor. (Conferência: "
     "a soma dos 6 postos médios é sempre 21.)"))

# exemplo
IEX = NOMES.index("wbuart32")
m = medias(GPT)["wbuart32"]
p = postos(m)
ex = [["", *EST], ["média (R1 + R2) ÷ 2", *[f1(x) for x in m]],
      ["posto (1 pior … 6 melhor)", *[br(x) for x in p]]]
t = Table(ex, colWidths=[48 * mm] + [21 * mm] * 6)
t.setStyle(TableStyle(estilo_tabela(AZUL, 8.5) + [("BACKGROUND", (0, 1), (0, -1), CINZA)]))
grupos = {}
for i in sorted(range(6), key=lambda i: m[i]):
    grupos.setdefault(m[i], []).append(i)
expl = []
for v, idx in grupos.items():
    nomes = " e ".join(EST[i] for i in idx)
    if len(idx) == 1:
        expl.append(f"{nomes} ({f1(v)}) → posto {br(p[idx[0]])}")
    else:
        expl.append(f"{nomes} empatam em {f1(v)} → {br(p[idx[0]])} cada")
st(KeepTogether([
    P("Exemplo trabalhado: wbuart32 (GPT)", H2),
    P("Mutantes — rodada 1: " + ", ".join(abrev(c) for c in celulas(MODELOS[0], 1)[IEX])
      + ";  rodada 2: " + ", ".join(abrev(c) for c in celulas(MODELOS[0], 2)[IEX])
      + " (NP = Não passou).", SMALL),
    t,
    P("Do menor para o maior: " + "; ".join(expl) + ".", CAP),
]))


# ---------- tabela detalhada por modelo ----------
def tabela_modelo(titulo, b, cor):
    med = medias(b)
    rows = [["Circuito", *EST]]
    somas = [0.0] * 6
    for c, v in med.items():
        pp = postos(v)
        for i in range(6):
            somas[i] += pp[i]
        rows.append([c, *[f"{f1(v[i])} ({br(pp[i])})" for i in range(6)]])
    pm = [s / len(med) for s in somas]
    rows.append(["Posto médio", *[f2(x) for x in pm]])
    t = Table(rows, colWidths=[34 * mm] + [23.3 * mm] * 6, repeatRows=1)
    sty = estilo_tabela(cor) + [
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, CINZA]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dff0e6")),
        ("FONTNAME", (0, -1), (-1, -1), "DVB")]
    ib = pm.index(max(pm))
    sty.append(("TEXTCOLOR", (ib + 1, -1), (ib + 1, -1), VERDE))
    t.setStyle(TableStyle(sty))
    ordem = sorted(range(6), key=lambda i: -pm[i])
    st(KeepTogether([
        P(titulo, H2),
        P("Cada célula mostra a média das 2 rodadas e, entre parênteses, o posto naquele circuito. "
          "A última linha é o posto médio (soma dos postos ÷ 10).", SMALL),
        t,
        P("Ranking: " + " &gt; ".join(f"{EST[i]} ({f2(pm[i])})" for i in ordem), CAP)]))
    return pm


st(PageBreak())
st(P("3. Resultados por modelo (um por um)", H1))
st(P("As tabelas a seguir trazem os 10 circuitos de cada modelo, com a média e o posto de cada "
     "estratégia, e o posto médio final. O verde marca o maior posto médio."))
pm_gpt = tabela_modelo("3.1 GPT-5.6 Luna", GPT, AZUL)
pm_gem = tabela_modelo("3.2 Gemini 3.5 Flash-Lite", GEM, colors.HexColor("#5b3a8e"))

# ---------- juntos ----------
st(PageBreak())
st(P("4. Resultado com os dois modelos juntos (20 blocos)", H1))
st(P("Ao juntar os modelos, cada combinação circuito × modelo vira um bloco (20 no total). As "
     "estratégias são ranqueadas <b>dentro</b> de cada bloco, do mesmo modo; o posto médio é a média "
     "sobre os 20. O modelo nunca é ranqueado — ele apenas dobra o número de blocos."))
JUNTOS = {**{f"GPT {k}": v for k, v in GPT.items()}, **{f"Gemini {k}": v for k, v in GEM.items()}}
medJ = medias(JUNTOS)
rows = [["Circuito (modelo)", *EST]]
somas = [0.0] * 6
for c, v in medJ.items():
    pp = postos(v)
    for i in range(6):
        somas[i] += pp[i]
    rows.append([c, *[br(pp[i]) for i in range(6)]])
pm_jun = [s / 20 for s in somas]
rows.append(["Posto médio", *[f2(x) for x in pm_jun]])
t = Table(rows, colWidths=[42 * mm] + [22 * mm] * 6, repeatRows=1)
sty = estilo_tabela(VERDE, 7.8) + [
    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, CINZA]),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dff0e6")),
    ("FONTNAME", (0, -1), (-1, -1), "DVB"), ("TOPPADDING", (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
ib = pm_jun.index(max(pm_jun))
sty.append(("TEXTCOLOR", (ib + 1, -1), (ib + 1, -1), VERDE))
t.setStyle(TableStyle(sty))
st(P("Nesta tabela as células mostram só o posto (as médias estão nas tabelas por modelo).", CAP))
st(t)
ordem = sorted(range(6), key=lambda i: -pm_jun[i])
st(Spacer(1, 3 * mm))
rk = [["Posição", "Estratégia", "Posto médio"]]
for pos, i in enumerate(ordem, 1):
    rk.append([f"{pos}º", ESTLONG[i], f2(pm_jun[i])])
t = Table(rk, colWidths=[20 * mm, 70 * mm, 30 * mm])
t.setStyle(TableStyle(estilo_tabela(AZUL, 9.5) + [
    ("ALIGN", (1, 1), (1, -1), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA]),
    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
ig, ie = pm_gpt.index(max(pm_gpt)), pm_gem.index(max(pm_gem))
ug, ue = pm_gpt.index(min(pm_gpt)), pm_gem.index(min(pm_gem))
st(KeepTogether([t, P(
    f"Juntos: {EST[ordem[0]]} em 1º e {EST[ordem[-1]]} em último. Por modelo, o 1º é {EST[ig]} no "
    f"GPT ({f2(pm_gpt[ig])}) e {EST[ie]} no Gemini ({f2(pm_gem[ie])}); o último é "
    + (f"{EST[ug]} nos dois." if ug == ue else f"{EST[ug]} no GPT e {EST[ue]} no Gemini."), CAP)]))

# 5. como obter
st(P("5. Como os resultados foram obtidos", H1))
st(B("Os valores vêm da planilha do experimento (linha “Mutantes” de cada circuito), nas 2 rodadas."))
st(B("Para cada circuito calcula-se a média das 2 rodadas, os postos (passos 2 e 3) e, ao final, o "
     "posto médio."))
st(B("O cálculo é reproduzível por script (analise/estatistica/gera_pdf_posto.py), e os postos "
     "médios são os mesmos da seção Resultados do TCC."))

# 6. interpretação
st(KeepTogether([P("6. Interpretação e ressalvas", H1), P(f"O posto médio <b>ordena</b> as estratégias (aponta {ESTLONG[ordem[0]]} em 1º e "
     f"{ESTLONG[ordem[-1]]} em último), mas, sozinho, não prova que uma estratégia é "
     "significativamente melhor que outra. No TCC, ele é usado de forma descritiva, junto com o "
     "score efetivo. Com os dois modelos juntos, as três variantes few-shot ocupam as primeiras "
     "posições e o Zero-shot fica em último.")]))
st(P("O posto médio é uma comparação <b>entre estratégias</b>, interna a cada modelo (a soma dos postos "
     "médios é sempre 21, no GPT e no Gemini). Por isso ele <b>não</b> compara GPT × Gemini: para "
     "comparar os modelos usam-se métricas absolutas (score efetivo, taxa de aprovação), e essa "
     "comparação é apenas descritiva. Ao juntar os modelos, declara-se que os mesmos circuitos "
     "aparecem nos dois (os 20 blocos não são totalmente independentes)."))

# referências
st(P("Referências", H1))
for r in [
    "ARCURI, Andrea; BRIAND, Lionel. A practical guide for using statistical tests to assess "
    "randomized algorithms in software engineering. In: INTERNATIONAL CONFERENCE ON SOFTWARE "
    "ENGINEERING, 33., 2011, Honolulu. <b>Proceedings</b> [...]. New York: ACM, 2011. p. 1-10. "
    "DOI: 10.1145/1985793.1985795.",
    "DEMŠAR, Janez. Statistical comparisons of classifiers over multiple data sets. <b>Journal of "
    "Machine Learning Research</b>, v. 7, p. 1-30, 2006.",
    "FRIEDMAN, Milton. The use of ranks to avoid the assumption of normality implicit in the "
    "analysis of variance. <b>Journal of the American Statistical Association</b>, v. 32, n. 200, "
    "p. 675-701, 1937. DOI: 10.1080/01621459.1937.10503522.",
]:
    st(P(r, SMALL))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm,
                        bottomMargin=15 * mm, title="Posto médio — passo a passo", author="veriweb")
doc.build(story)
print("PDF salvo em", OUT)
print("Conferencia postos medios juntos:", {EST[i]: round(pm_jun[i], 2) for i in ordem})
