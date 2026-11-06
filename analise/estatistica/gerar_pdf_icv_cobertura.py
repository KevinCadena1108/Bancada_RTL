"""Gera o PDF "ICV e cobertura: como foi feito e resultados".

Duas análises descritivas, sem teste de hipótese, para a apresentação dos resultados do TCC:
  A) desempenho por classe de complexidade (ICV): aprovação, score efetivo e posto médio;
  B) métricas de cobertura (linha, desvio, alternância e FSM) dos testbenches aprovados.
Os mutantes vêm de PLANILHA_R1/R2 (pdf_comum.py) e as coberturas de coberturas.json; tudo é
calculado aqui. O ICV de cada módulo é o que a bancada calculou (resultado.json das avaliações).
Uso: python gerar_pdf_icv_cobertura.py [saida.pdf]   (padrão: documentacao/icv_cobertura_resultados.pdf)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer

from pdf_comum import (CIRCUITOS, CURTO, ESTR, MODELOS, REFS, RODADAS, VERDE, VERDE_BORDA, br,
                       caixa, construir, fonte, item, P, postos, saida, tabela)

TITULO = "ICV e cobertura: como foi feito e resultados"
AQUI = os.path.dirname(os.path.abspath(__file__))
COB = json.load(open(os.path.join(AQUI, "coberturas.json"), encoding="utf-8"))

# Nome no TCC, origem e ICV calculado pela bancada, na ordem de CIRCUITOS (nomes da planilha).
MODULOS = {
    "Fsm serialdp": ("Fsm serialdp", "HDLBits", 2.2),
    "Exams/2012 q2fsm": ("Exams/2012 q2fsm", "HDLBits", 1.4),
    "Cout Clock": ("Count clock", "HDLBits", 1.0),
    "Cs450/gshare": ("Cs450/gshare", "HDLBits", 1.8),
    "Lemmings1": ("Lemmings1", "HDLBits", 1.0),
    "wbuart32": ("wbuart32", "OpenCores", 2.5),
    "Cordic": ("CORDIC", "OpenCores", 1.9),
    "Conwaylife": ("Conwaylife", "HDLBits", 1.0),
    "fancytimer": ("Fancytimer", "HDLBits", 1.9),
    "I2C Slave": ("SPI Master", "OpenCores", 2.4),
}
CLASSES = ["Fácil", "Média", "Alta", "Muito Alta"]
MET = ["linha", "branch", "toggle", "fsm"]
NOME_MET = {"linha": "Linha", "branch": "Desvio", "toggle": "Alternância", "fsm": "FSM"}


def classe(icv):
    return "Fácil" if icv <= 1.2 else "Média" if icv <= 1.9 else "Alta" if icv <= 2.3 else "Muito Alta"


CL = [classe(MODULOS[c][2]) for c in CIRCUITOS]


def mortos(cel):
    return int(cel.split("/")[0]) if "/" in cel else 0


def passou(cel):
    return "/" in cel


def pct(x, nd=1):
    return br(x, nd) + "%"


# --------------------------------------------------------------------------
# A) por classe de ICV
# --------------------------------------------------------------------------
def resumo_classe(cls, modelos=MODELOS):
    """TBs, aprovados, mortos e mortos por estratégia (as 2 rodadas)."""
    n = ap = mt = 0
    por_e = [0] * 6
    n_e = [0] * 6
    for m in modelos:
        for r in (1, 2):
            for d in range(10):
                if cls != "Total" and CL[d] != cls:
                    continue
                for e in range(6):
                    cel = RODADAS[r][m][d][e]
                    n += 1
                    ap += passou(cel)
                    mt += mortos(cel)
                    por_e[e] += mortos(cel)
                    n_e[e] += 1
    return {"n": n, "ap": ap, "mt": mt, "ef": 100 * mt / (4 * n),
            "ef_e": [100 * por_e[e] / (4 * n_e[e]) for e in range(6)]}


def posto_classe(cls):
    """Posto médio das 6 estratégias na classe (média das 2 rodadas; bloco = módulo × modelo)."""
    blocos = []
    for m in MODELOS:
        for d in range(10):
            if cls != "Total" and CL[d] != cls:
                continue
            v = [(mortos(RODADAS[1][m][d][e]) + mortos(RODADAS[2][m][d][e])) / 2 for e in range(6)]
            blocos.append(postos(v))
    return [sum(b[e] for b in blocos) / len(blocos) for e in range(6)], len(blocos)


RES = {k: resumo_classe(k) for k in CLASSES + ["Total"]}
RES_M = {m: {k: resumo_classe(k, [m]) for k in CLASSES + ["Total"]} for m in MODELOS}
POSTO = {k: posto_classe(k) for k in CLASSES + ["Total"]}


def extremos(pm, maior=True):
    alvo = max(pm) if maior else min(pm)
    nomes = [ESTR[e] for e in range(6) if abs(pm[e] - alvo) < 1e-9]
    return " e ".join(nomes) + f" ({br(alvo, 2)})"


# --------------------------------------------------------------------------
# B) cobertura dos aprovados
# --------------------------------------------------------------------------
APROV = []  # (modelo, circuito, estratégia, {métrica: valor}, mortos)
for m in MODELOS:
    for r in (1, 2):
        for d in range(10):
            for e in range(6):
                cel = RODADAS[r][m][d][e]
                if passou(cel):
                    c = COB[m][str(r)][d]
                    APROV.append((m, d, e, {k: c[k][e] for k in MET}, mortos(cel)))


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def media_cob(sel):
    out = {}
    for k in MET:
        vals = [l[3][k] for l in sel if num(l[3][k])]
        out[k] = (sum(vals) / len(vals), len(vals)) if vals else (None, 0)
    out["score"] = 100 * sum(l[4] for l in sel) / (4 * len(sel))
    out["n"] = len(sel)
    return out


COB_E = [media_cob([l for l in APROV if l[2] == e]) for e in range(6)]
COB_M = {m: media_cob([l for l in APROV if l[0] == m]) for m in MODELOS}
CHEIO = {}
for k in MET:
    sel = [l for l in APROV if num(l[3][k])]
    cheio = [l for l in sel if l[3][k] >= 100]
    CHEIO[k] = (len(sel), len(cheio), sum(1 for l in cheio if l[4] < 4))
MOD_FSM = sorted({MODULOS[CIRCUITOS[l[1]]][0] for l in APROV if num(l[3]["fsm"])})

# Conferência com os números já passados ao autor (se a planilha mudar, estes asserts avisam).
assert RES["Total"]["n"] == 240 and len(APROV) == 175
assert round(RES["Total"]["ef"], 1) == 54.1 and round(RES["Fácil"]["ef"], 1) == 72.2
assert round(RES["Média"]["ef"], 1) == 42.4 and round(RES["Muito Alta"]["ef"], 1) == 47.9
assert CHEIO["linha"][1:] == (122, 63) and CHEIO["branch"][1:] == (116, 58)
assert round(COB_E[0]["score"], 1) == 69.3 and round(COB_E[5]["score"], 1) == 78.7
assert len(MOD_FSM) == 5

# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------
story = []
st = story.append
LEG = "ZS = Zero-shot; FS = Few-shot; EspZS/EspFS = Especialista Zero/Few-shot; " \
      "PlnZS/PlnFS = Planning Zero/Few-shot."
FONTE_PLAN = "elaborado pelo autor a partir da planilha do experimento (2 modelos, 2 rodadas)."


def tab(titulo, cab, linhas, larg, destacar_ultima=False, nota=None):
    blocos = [P(titulo, "legenda"), tabela(cab, linhas, larg, destacar_ultima=destacar_ultima)]
    if nota:
        blocos.append(P(nota, "nota"))
    blocos.append(fonte(FONTE_PLAN))
    st(KeepTogether(blocos))


st(P(TITULO, "titulo"))
st(P("Desempenho por classe de complexidade (ICV) e métricas de cobertura dos testbenches — "
     "GPT-5.6 Luna e Gemini 3.5 Flash-Lite, duas rodadas", "sub"))
st(Spacer(1, 10))

# ---- 1. o que responde ----
st(P("1. O que este documento responde", "h1"))
st(item("<b>Pergunta A:</b> o desempenho dos testbenches muda com a complexidade do módulo, "
        "medida pelo ICV?"))
st(item("<b>Pergunta B:</b> o que as métricas de cobertura mostram, e uma cobertura alta garante "
        "que o testbench detecta erros?"))
f, md, ma = RES["Fácil"], RES["Média"], RES["Muito Alta"]
st(Spacer(1, 4))
st(caixa([
    "<b>Resposta curta</b>",
    f"<b>A:</b> os módulos fáceis tiveram o melhor resultado (score efetivo {pct(f['ef'])}), mas o "
    f"desempenho não cai junto com o ICV: os de complexidade média tiveram o pior "
    f"({pct(md['ef'])}), abaixo dos de complexidade muito alta ({pct(ma['ef'])}). A melhor "
    "estratégia muda conforme a classe, e a Zero-shot fica em último na maioria delas.",
    f"<b>B:</b> a cobertura quase não diferencia as estratégias, e "
    f"{CHEIO['linha'][2]} dos {CHEIO['linha'][1]} testbenches com 100% de cobertura de linha "
    f"({pct(100 * CHEIO['linha'][2] / CHEIO['linha'][1], 0)}) deixaram mutante vivo. A cobertura "
    "mostra o que foi exercitado, não o que foi verificado.",
], fundo=VERDE, borda=VERDE_BORDA, estilo="corpo"))
st(P("As duas análises são <b>descritivas</b> (contagens, porcentagens, médias e posto médio). "
     "Não há teste de hipótese: os textos dizem “obteve o maior”, “ficou acima”, e nunca "
     "“significativamente”.", "nota"))

# ---- 2. dados ----
st(P("2. Dados utilizados", "h1"))
st(P("Foram usados os 240 testbenches do experimento: 10 módulos × 6 estratégias × 2 modelos × "
     "2 rodadas. De cada um, a planilha traz o resultado da mutação (“k/4” = k mutantes mortos, ou "
     "“Não passou”/“Timeout”) e as quatro coberturas (linha, desvio, alternância e FSM). Testbench "
     "<b>aprovado</b> é o que tem resultado “k/4” (inclusive 0/4): compilou, terminou dentro do "
     "tempo e não acusou erro no circuito original. Foram 175 aprovados."))
lin = []
for c in sorted(CIRCUITOS, key=lambda c: (MODULOS[c][2], MODULOS[c][0].lower())):
    nome, orig, icv = MODULOS[c]
    lin.append([nome, c if c != nome else "—", orig, br(icv, 1), classe(icv)])
tab("Tabela 1 — Módulos, ICV e classe de complexidade",
    ["Módulo (nome no TCC)", "Nome na planilha", "Origem", "ICV", "Classe"], lin,
    [42 * mm, 40 * mm, 30 * mm, 24 * mm, 38 * mm],
    nota="O ICV de cada módulo foi calculado pela Bancada RTL a partir do código do módulo. "
         "Classes: Fácil (até 1,2), Média (até 1,9), Alta (até 2,3) e Muito Alta (acima de 2,3).")

# ---- 3. parte A ----
st(PageBreak())
st(P("3. Parte A — Resultados por classe de ICV", "h1"))
st(P("3.1 Como é feito", "h2"))
st(P("Os módulos são separados nas quatro classes do ICV (Tabela 1) e, em cada classe, juntam-se os "
     "testbenches dos dois modelos e das duas rodadas. Para cada classe são calculadas três "
     "medidas:"))
st(item("<b>Taxa de aprovação:</b> testbenches aprovados ÷ testbenches da classe."))
st(item("<b>Score efetivo:</b> mutantes mortos ÷ (4 × testbenches da classe). Os testbenches que "
        "não compilaram, não passaram ou estouraram o tempo entram com zero mortos, então a "
        "medida junta “gerou um testbench que funciona” e “o testbench detecta erros”."))
st(item("<b>Posto médio:</b> o mesmo cálculo da análise principal, feito só com os módulos da "
        "classe. Em cada bloco (um módulo em um modelo), as 6 estratégias recebem postos de 1 a 6 "
        "pela média das 2 rodadas de mutantes mortos (6 = melhor; empate = média das posições), "
        "e o posto médio é a média desses postos nos blocos da classe."))
st(caixa(["<b>Score efetivo da classe</b> = mutantes mortos ÷ (4 × testbenches da classe)",
          "<b>Posto médio da estratégia j</b> = (1/N) × Σ<sub>i</sub> r<sub>ij</sub>, "
          "com r<sub>ij</sub> = posto da estratégia j no bloco i e N = blocos da classe"]))
st(P(f"<b>Exemplo (classe Fácil):</b> são 3 módulos × 6 estratégias × 2 modelos × 2 rodadas = "
     f"{f['n']} testbenches. Somando os mutantes mortos dá {f['mt']}, então o score efetivo é "
     f"{f['mt']} ÷ (4 × {f['n']}) = {f['mt']} ÷ {4 * f['n']} = <b>{pct(f['ef'])}</b>. "
     f"Para o posto médio, a classe tem N = {POSTO['Fácil'][1]} blocos (3 módulos × 2 modelos)."))
st(fonte("posto médio: Friedman (1937); Demšar (2006), que usa 1 = melhor (aqui é o contrário). "
         "Score efetivo e taxa de aprovação: definições deste trabalho."))

st(P("3.2 Resultados", "h2"))
lin = []
for k in CLASSES + ["Total"]:
    r = RES[k]
    nmod = sum(1 for x in CL if x == k) if k != "Total" else 10
    lin.append([k, nmod, r["n"], f"{r['ap']} ({pct(100 * r['ap'] / r['n'], 0)})", pct(r["ef"]),
                extremos(POSTO[k][0]), extremos(POSTO[k][0], maior=False)])
tab("Tabela 2 — Resumo por classe de ICV (os dois modelos juntos)",
    ["Classe", "Módulos", "TBs", "Aprovados", "Score efetivo", "Maior posto médio",
     "Menor posto médio"], lin,
    [24 * mm, 17 * mm, 14 * mm, 25 * mm, 22 * mm, 36 * mm, 36 * mm], destacar_ultima=True,
    nota=LEG)

lin = [[k] + [pct(x) for x in RES[k]["ef_e"]] + [pct(RES[k]["ef"])] for k in CLASSES + ["Total"]]
tab("Tabela 3 — Score efetivo por estratégia em cada classe (os dois modelos juntos)",
    ["Classe"] + ESTR + ["Classe toda"], lin,
    [33 * mm] + [20 * mm] * 6 + [21 * mm], destacar_ultima=True, nota=LEG)

lin = [[k] + [br(x, 2) for x in POSTO[k][0]] + [POSTO[k][1]] for k in CLASSES + ["Total"]]
tab("Tabela 4 — Posto médio de cada estratégia por classe (6 = melhor)",
    ["Classe"] + ESTR + ["N (blocos)"], lin,
    [33 * mm] + [20 * mm] * 6 + [21 * mm], destacar_ultima=True,
    nota="N = módulos da classe × 2 modelos. Com poucos blocos, um único módulo muda bastante a "
         "ordem (a classe Alta tem N = 2).")

g, ge = RES_M[MODELOS[0]], RES_M[MODELOS[1]]
lin = [[k, f"{g[k]['ap']}/{g[k]['n']}", pct(g[k]["ef"]), f"{ge[k]['ap']}/{ge[k]['n']}",
        pct(ge[k]["ef"])] for k in CLASSES + ["Total"]]
tab("Tabela 5 — Por modelo: aprovados e score efetivo em cada classe",
    ["Classe", "GPT: aprovados", "GPT: score efetivo", "Gemini: aprovados",
     "Gemini: score efetivo"], lin, [34 * mm] + [35 * mm] * 4, destacar_ultima=True)

st(P("3.3 Leitura", "h2"))
pm_f, pm_md, pm_ma = POSTO["Fácil"][0], POSTO["Média"][0], POSTO["Muito Alta"][0]
st(item(f"<b>Fácil é a melhor classe:</b> maior aprovação "
        f"({pct(100 * f['ap'] / f['n'], 0)}) e maior score efetivo ({pct(f['ef'])})."))
st(item(f"<b>O desempenho não acompanha o ICV:</b> a classe Média teve o menor score efetivo "
        f"({pct(md['ef'])}), abaixo da Muito Alta ({pct(ma['ef'])}). O ICV mede características "
        "do código (tamanho, estados, portas, tipo de lógica), não a dificuldade de verificar o "
        "módulo."))
st(item(f"<b>A melhor estratégia muda com a classe:</b> {extremos(pm_f)} nos fáceis, "
        f"{extremos(pm_md)} nos médios e {extremos(pm_ma)} nos de complexidade muito alta."))
st(item("<b>A Zero-shot fica em último</b> em três das quatro classes (na Muito Alta, empatada "
        "com a Few-shot). Na classe Alta, o último é a Planning Zero-shot."))
st(item("<b>A classe Alta tem um só módulo</b> (Fsm serialdp): seus números descrevem esse "
        "módulo, não uma classe. Não generalizar."))

# ---- 4. parte B ----
st(PageBreak())
st(P("4. Parte B — Métricas de cobertura", "h1"))
st(P("4.1 Como é feito", "h2"))
st(P("Durante a simulação, o Verilator conta quantas vezes cada ponto instrumentado do circuito "
     "foi exercitado. A Bancada RTL usa só os pontos do DUT, considera coberto o ponto exercitado "
     "ao menos uma vez e calcula a porcentagem de pontos cobertos:"))
st(item("<b>Linha:</b> trechos de código executados."))
st(item("<b>Desvio:</b> lados das decisões (<i>if</i>/<i>case</i>) percorridos."))
st(item("<b>Alternância:</b> bits de sinais que mudaram de 0 para 1 e de 1 para 0."))
st(item(f"<b>FSM:</b> aproximação da bancada (o Verilator não tem essa métrica): ramos exercitados "
        f"das estruturas <i>case</i> cujo seletor é um registrador, ou seja, estados visitados. Só "
        f"se aplica a {len(MOD_FSM)} módulos ({', '.join(MOD_FSM)})."))
st(P("Para resumir:"))
st(item("<b>Só os testbenches aprovados entram.</b> Um testbench reprovado para no primeiro "
        "<i>$fatal</i>, então a cobertura dele fica incompleta e não representa o que ele faria."))
st(item("<b>Cobertura média:</b> média simples das porcentagens dos aprovados, por estratégia e por "
        "modelo. Cada estratégia tem um número diferente de aprovados (coluna “Aprovados”)."))
st(item("<b>Score dos aprovados:</b> mutantes mortos ÷ (4 × aprovados), para comparar a cobertura "
        "com a detecção de erros nos mesmos testbenches."))
st(item("<b>Cobertura de 100% com mutante vivo:</b> entre os aprovados com 100% em uma métrica, "
        "quantos deixaram pelo menos um dos 4 mutantes vivo (mortos menor que 4)."))

st(P("4.2 Resultados", "h2"))


def linha_cob(rot, c):
    return [rot, c["n"]] + [pct(c[k][0]) for k in MET] + [pct(c["score"])]


CAB_COB = ["", "Aprovados", "Linha", "Desvio", "Alternância", "FSM*", "Score dos aprovados"]
LARG_COB = [26 * mm, 21 * mm, 22 * mm, 22 * mm, 26 * mm, 22 * mm, 35 * mm]
NOTA_FSM = f"*FSM: só nos {len(MOD_FSM)} módulos em que a métrica se aplica. "
tab("Tabela 6 — Cobertura média dos testbenches aprovados, por estratégia",
    ["Estratégia"] + CAB_COB[1:], [linha_cob(ESTR[e], COB_E[e]) for e in range(6)], LARG_COB,
    nota=NOTA_FSM + LEG)
tab("Tabela 7 — Cobertura média dos testbenches aprovados, por modelo",
    ["Modelo"] + CAB_COB[1:], [linha_cob(CURTO[m], COB_M[m]) for m in MODELOS], LARG_COB,
    nota=NOTA_FSM)
lin = [[NOME_MET[k], CHEIO[k][0], CHEIO[k][1], CHEIO[k][2],
        pct(100 * CHEIO[k][2] / CHEIO[k][1], 0)] for k in MET]
tab("Tabela 8 — Testbenches com 100% de cobertura que deixaram mutante vivo",
    ["Métrica", "Aprovados com a métrica", "Com 100% de cobertura", "Deixaram mutante vivo",
     "Proporção"], lin, [34 * mm, 36 * mm, 36 * mm, 36 * mm, 32 * mm])

st(P("4.3 Leitura", "h2"))


def faixa(k):
    v = [c[k][0] for c in COB_E]
    return f"{br(min(v), 1)}% a {br(max(v), 1)}%"


sc = [c["score"] for c in COB_E]
z = COB_E[0]
gp, gm = COB_M[MODELOS[0]], COB_M[MODELOS[1]]
st(item(f"<b>A cobertura quase não distingue as estratégias:</b> linha de {faixa('linha')}, "
        f"desvio de {faixa('branch')} e alternância de {faixa('toggle')}, enquanto o score dos "
        f"aprovados vai de {br(min(sc), 1)}% a {br(max(sc), 1)}%."))
st(item(f"<b>Zero-shot:</b> uma das maiores coberturas de desvio ({pct(z['branch'][0])}) e o "
        f"menor score dos aprovados ({pct(z['score'])})."))
st(item(f"<b>Modelos:</b> o GPT teve cobertura de linha pouco maior ({pct(gp['linha'][0])} contra "
        f"{pct(gm['linha'][0])}), mas score dos aprovados bem maior ({pct(gp['score'])} contra "
        f"{pct(gm['score'])})."))
st(item("<b>100% de cobertura não garante detecção:</b> " + "; ".join(
    f"{NOME_MET[k] if k == 'fsm' else NOME_MET[k].lower()}: {CHEIO[k][2]} de {CHEIO[k][1]} "
    f"({pct(100 * CHEIO[k][2] / CHEIO[k][1], 0)})" for k in MET) + " deixaram mutante vivo."))
st(item("<b>Por quê:</b> a cobertura mede se o circuito foi exercitado; a mutação mede se o "
        "testbench <b>comparou</b> as saídas. Um testbench pode passar por todas as linhas sem "
        "conferir nenhum resultado."))

# ---- 5. texto para o TCC ----
st(PageBreak())
st(P("5. Texto para a apresentação dos resultados", "h1"))
st(P("Pronto para adaptar. Troque “Tabela X/Y” pelas referências das tabelas no seu documento "
     "(as tabelas em LaTeX foram enviadas no chat).", "nota"))
st(P("<b>Resultados por classe de complexidade</b>", "h2"))
st(P(f"A Tabela X apresenta os resultados agrupados pelas classes do ICV. Os módulos de "
     f"complexidade fácil tiveram a maior taxa de aprovação ({pct(100 * f['ap'] / f['n'], 0)}) e o "
     f"maior <i>score</i> efetivo ({pct(f['ef'])}). O desempenho, porém, não diminuiu de forma "
     f"contínua com o aumento do ICV: os módulos de complexidade média obtiveram o menor "
     f"<i>score</i> efetivo ({pct(md['ef'])}), inferior ao dos módulos de complexidade muito alta "
     f"({pct(ma['ef'])}). Isso indica que o ICV, que mede características estruturais do código, "
     f"não reflete diretamente a dificuldade de verificação dos módulos. A estratégia com maior "
     f"posto médio também variou entre as classes: Planning Few-shot nos módulos fáceis, Planning "
     f"Zero-shot nos médios e Especialista Few-shot nos de complexidade muito alta, enquanto a "
     f"Zero-shot obteve o menor posto médio em três das quatro classes. Como a classe Alta contém "
     f"apenas um módulo, seus resultados não permitem generalização."))
st(P("<b>Métricas de cobertura</b>", "h2"))
st(P(f"A Tabela Y apresenta a cobertura média dos <i>testbenches</i> aprovados. As médias "
     f"variaram pouco entre as estratégias: de {faixa('linha')} na cobertura de linha, de "
     f"{faixa('branch')} na de desvio e de {faixa('toggle')} na de alternância, enquanto o "
     f"<i>score</i> de mutação dos aprovados variou de {br(min(sc), 1)}% a {br(max(sc), 1)}%. A "
     f"estratégia Zero-shot, por exemplo, obteve uma das maiores coberturas de desvio "
     f"({pct(z['branch'][0])}) e o menor <i>score</i> de mutação entre os aprovados "
     f"({pct(z['score'])}). Na comparação entre os modelos, o GPT-5.6 Luna apresentou cobertura de "
     f"linha pouco superior à do Gemini 3.5 Flash-Lite ({pct(gp['linha'][0])} e "
     f"{pct(gm['linha'][0])}), mas <i>score</i> de mutação dos aprovados muito maior "
     f"({pct(gp['score'])} e {pct(gm['score'])}). Além disso, dos {CHEIO['linha'][1]} "
     f"<i>testbenches</i> com 100% de cobertura de linha, {CHEIO['linha'][2]} "
     f"({pct(100 * CHEIO['linha'][2] / CHEIO['linha'][1], 0)}) deixaram ao menos um mutante "
     f"sobrevivente; o mesmo ocorreu em {pct(100 * CHEIO['branch'][2] / CHEIO['branch'][1], 0)} "
     f"dos que tiveram 100% de cobertura de desvio, em "
     f"{pct(100 * CHEIO['fsm'][2] / CHEIO['fsm'][1], 0)} dos com 100% de cobertura de FSM e em "
     f"{pct(100 * CHEIO['toggle'][2] / CHEIO['toggle'][1], 0)} dos com 100% de cobertura de "
     f"alternância. Esses resultados mostram que a cobertura indica quanto do circuito foi "
     f"exercitado, mas não se as saídas foram verificadas, o que justifica o uso do teste de "
     f"mutação como métrica principal."))

st(P("6. Cuidados ao escrever", "h1"))
st(item("São resultados <b>descritivos</b>: escreva “obteve o maior posto médio”, “ficou acima”, "
        "nunca “significativamente melhor”."))
st(item("A classe Alta tem um módulo e o posto médio por classe usa poucos blocos (de 2 a 8): "
        "diferenças pequenas entre estratégias dentro de uma classe não devem ser destacadas."))
st(item("A cobertura média usa só os aprovados, e cada estratégia tem um conjunto diferente de "
        "aprovados; ela descreve os testbenches que funcionaram, não todos os gerados."))
st(item("A cobertura de FSM só reconhece máquinas de estados escritas com <i>case</i>: por isso o "
        "wbuart32 e o Fancytimer, que têm estados contados no ICV, ficam sem essa métrica, e o "
        "Conwaylife a tem mesmo sem estados no ICV."))

st(P("7. Como reproduzir", "h1"))
st(P("No WSL, na raiz do repositório, com reportlab e scipy instalados: "
     "<font name='DVM'>python analise/estatistica/gerar_pdf_icv_cobertura.py</font>. Os mutantes "
     "vêm de <font name='DVM'>PLANILHA_R1/R2</font> (<font name='DVM'>pdf_comum.py</font>) e as "
     "coberturas de <font name='DVM'>coberturas.json</font>; o script confere os números "
     "principais antes de gerar o PDF."))
st(KeepTogether([P("Referências", "h1")] + [P(REFS[k], "ref") for k in ("DEMSAR", "FRIEDMAN")]))

construir(saida("icv_cobertura_resultados.pdf"), story, TITULO)
print("ok", saida("icv_cobertura_resultados.pdf"))
