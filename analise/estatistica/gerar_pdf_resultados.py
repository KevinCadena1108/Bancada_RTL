"""Gera o PDF "Resultados: como foram calculados e o que representam".

Junta, num documento só, cada resultado da seção Resultados do TCC, com o cálculo passo a passo
(exemplos com os dados reais) e o que cada número representa. Os mutantes vêm de PLANILHA_R1/R2
(pdf_comum.py) e as coberturas de coberturas.json; tudo é recalculado aqui, com arredondamento
ABNT (NBR 5891). Uso: python gerar_pdf_resultados.py [saida.pdf]
"""
import json
import os
import sys
from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether

from pdf_comum import (AMARELO, CIRCUITOS, ESTR, MODELOS, NOME_ESTR, NP, OCRE, RODADAS, VERDE,
                       VERDE_BORDA, caixa, construir, fonte, item, P, postos, saida, tabela)

getcontext().prec = 50
TITULO = "Resultados: como foram calculados e o que representam"
AQUI = os.path.dirname(os.path.abspath(__file__))
COB = json.load(open(os.path.join(AQUI, "coberturas.json"), encoding="utf-8"))
G, GM = MODELOS
CURTO = {G: "GPT", GM: "Gemini"}
MET = ["linha", "branch", "toggle"]
NOME_MET = {"linha": "Linha", "branch": "Desvio", "toggle": "Alternância"}

# Nome no TCC e ICV calculado pela bancada, por nome da planilha.
MODULOS = {
    "Fsm serialdp": ("Fsm serialdp", 2.2), "Exams/2012 q2fsm": ("Exams/2012 q2fsm", 1.4),
    "Cout Clock": ("Count clock", 1.0), "Cs450/gshare": ("Cs450/gshare", 1.8),
    "Lemmings1": ("Lemmings1", 1.0), "wbuart32": ("wbuart32", 2.5), "Cordic": ("CORDIC", 1.9),
    "Conwaylife": ("Conwaylife", 1.0), "fancytimer": ("Fancytimer", 1.9),
    "I2C Slave": ("SPI Master", 2.4),
}

NOME = [MODULOS[c][0] for c in CIRCUITOS]
ICV = [MODULOS[c][1] for c in CIRCUITOS]
ORDEM = sorted(range(10), key=lambda d: (ICV[d], NOME[d].lower()))   # módulos do mais simples ao mais complexo
D = {c: i for i, c in enumerate(CIRCUITOS)}


# --------------------------------------------------------------------------
# Arredondamento ABNT e formatação
# --------------------------------------------------------------------------
def dec(x):
    x = Fraction(x)
    return Decimal(x.numerator) / Decimal(x.denominator)


def arr(x, nd):
    """ABNT NBR 5891: se o que sobra é exatamente 5, o último algarismo mantido fica par."""
    return dec(x).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_EVEN)


def n(x, nd=1):
    return f"{arr(x, nd):f}".replace(".", ",")


def pct(x, nd=1):
    return n(x, nd) + "%"


def npos(p):
    """Posto médio com 2 casas, ou 3 quando o valor é exato com 3 casas (3,675)."""
    p = Fraction(p)
    return n(p, 3) if (p * 100).denominator != 1 and (p * 1000).denominator == 1 else n(p, 2)


def dif(x):
    s = n(abs(x))
    return ("+" if x > 0 else "−" if x < 0 else "") + s


# --------------------------------------------------------------------------
# Dados: um registro por testbench
# --------------------------------------------------------------------------
def mortos(c):
    return int(c.split("/")[0]) if "/" in c else 0


TB = []
for m in MODELOS:
    for r in (1, 2):
        for d in range(10):
            for e in range(6):
                cel = RODADAS[r][m][d][e]
                ok = "/" in cel
                cob = {k: COB[m][str(r)][d][k][e] for k in MET} if ok else None
                TB.append(dict(m=m, r=r, d=d, e=e, cel=cel, k=mortos(cel), ok=ok, cob=cob))


def _lista(v):
    return [v] if isinstance(v, (str, int)) else list(v)


def sel(m=MODELOS, r=(1, 2), d=range(10), e=range(6), ok=None):
    m, r, d, e = _lista(m), _lista(r), _lista(d), _lista(e)
    return [t for t in TB if t["m"] in m and t["r"] in r and t["d"] in d and t["e"] in e
            and (ok is None or t["ok"] == ok)]


def det(l):
    return sum(t["k"] for t in l)


def apr(l):
    return sum(t["ok"] for t in l)


def ef(l):
    return Fraction(100 * det(l), 4 * len(l))


def classif(m, d):
    """Uma classificação: média das 2 rodadas de cada estratégia e a posição (1 a 6)."""
    med = [Fraction(det(sel(m, (1, 2), d, e)), 2) for e in range(6)]
    return med, [Fraction(p) for p in postos(med)]


def posto_medio(mods, dd=range(10)):
    cl = [classif(m, d)[1] for m in mods for d in dd]
    return [sum(c[e] for c in cl) / len(cl) for e in range(6)], len(cl)


def cobmed(l, k):
    v = [Fraction(Decimal(str(t["cob"][k]))) for t in l]
    return sum(v) / len(v)


COM, SEM = [1, 3, 5], [0, 2, 4]
PM = {G: posto_medio([G])[0], GM: posto_medio([GM])[0], "J": posto_medio(MODELOS)[0]}
APROV = sel(ok=True)
assert all(all(isinstance(t["cob"][k], (int, float)) for k in MET) for t in APROV)
N_NP = sum(t["cel"] == NP for t in TB)
N_TO = sum(t["cel"] == "Timeout" for t in TB)


def cheio(k, mods=MODELOS, sem_cordic=False):
    l = [t for t in APROV if t["m"] in mods and t["cob"][k] >= 100
         and not (sem_cordic and CIRCUITOS[t["d"]] == "Cordic")]
    return len(l), sum(t["k"] < 4 for t in l)


# Conferência com os números do TCC (se a planilha mudar, estes asserts avisam).
assert len(TB) == 240 and len(APROV) == 175 and n(ef(TB)) == "54,1"
assert [npos(x) for x in PM["J"]] == ["2,35", "3,675", "3,30", "3,75", "3,625", "4,30"]
assert n(cobmed(sel(e=5, ok=True), "branch")) == "90,8"
assert cheio("linha") == (122, 63) and cheio("branch") == (116, 58) and cheio("toggle") == (56, 18)


def prop(par):
    """Proporção da Tabela 5 do TCC, com uma casa (ex.: 63 de 122 = 51,6%)."""
    t, v = par
    return pct(Fraction(100 * v, t))


# Tabela 5 do TCC (PDF de 19/11/2026): total, GPT, Gemini e sem o CORDIC.
assert [prop(cheio(k)) for k in ("linha", "branch", "toggle")] == ["51,6%", "50,0%", "32,1%"]
assert [prop(cheio(k, [G])) for k in ("linha", "branch", "toggle")] == ["32,3%", "38,7%", "25,8%"]
assert [prop(cheio(k, [GM])) for k in ("linha", "branch", "toggle")] == ["71,7%", "63,0%", "40,0%"]
assert [prop(cheio(k, sem_cordic=True)) for k in ("branch", "toggle")] == ["46,8%", "29,6%"]
# Tabela 4 do TCC: alternância média dos aprovados vai de 71,0% (ZS) a 74,1% (EspFS).
_alt = [pct(cobmed(sel(e=e, ok=True), "toggle")) for e in range(6)]
assert (_alt[0], _alt[3], min(_alt), max(_alt)) == ("71,0%", "74,1%", "71,0%", "74,1%"), _alt
assert all(p == 3.5 for p in classif(G, D["Lemmings1"])[1])          # citado na seção 5
assert max(t["k"] for t in sel(d=D["Cordic"])) == 3                   # mutante equivalente
assert max(t["k"] for t in sel(GM, d=D["Cs450/gshare"])) == 1 and apr(sel(d=D["Cs450/gshare"])) == 12
assert [CIRCUITOS[d] for d in range(10) if max(t["k"] for t in sel(d=d)) < 4] == ["Cs450/gshare",
                                                                                   "Cordic"]

# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------
story = []
st = story.append
FONTE_PLAN = "elaborado pelo autor a partir da planilha do experimento e das coberturas salvas."
LEG = ("ZS = <i>Zero-shot</i>, FS = <i>Few-shot</i>, Esp = Especialista e Pln = <i>Planning</i>.")
W7 = [34 * mm] + [23.3 * mm] * 6


def tab(titulo, cab, linhas, larg, destacar_ultima=False, nota=None, cor=AMARELO):
    blocos = [P(titulo, "legenda"),
              tabela(cab, linhas, larg, destacar_ultima=destacar_ultima, cor_ultima=cor)]
    if nota:
        blocos.append(P(nota, "nota"))
    blocos.append(fonte(FONTE_PLAN))
    st(KeepTogether(blocos))


def representa(linhas):
    st(caixa(["<b>O que representa</b>"] + linhas, fundo=VERDE, borda=VERDE_BORDA, estilo="corpo"))


st(P(TITULO, "titulo"))
st(P("Cada resultado da seção Resultados do TCC, com o cálculo passo a passo e o que o número "
     "significa. GPT-5.6 Luna e Gemini 3.5 Flash-Lite, 10 módulos, 6 estratégias e 2 rodadas.",
     "sub"))

# ---- Visão geral
st(P("Visão geral", "h1"))
ef_e = [ef(sel(e=e)) for e in range(6)]
lin_cheio = cheio("linha")
tab("Tabela 1. O que cada resultado responde",
    ["Resultado", "Pergunta que responde", "Principal número"],
    [["Taxa de aprovação", "A estratégia gera <i>testbenches</i> que funcionam no circuito correto?",
      f"{apr(TB)} de {len(TB)} ({pct(Fraction(100 * apr(TB), len(TB)))})"],
     ["<i>Score</i> efetivo", "De todas as falhas possíveis, quantas foram detectadas?",
      f"{pct(ef(TB))} no geral; PlnFS {pct(ef_e[5])} e ZS {pct(ef_e[0])}"],
     ["Com e sem exemplos", "Colocar exemplos no <i>prompt</i> ajuda?",
      f"{pct(ef(sel(e=COM)))} contra {pct(ef(sel(e=SEM)))}"],
     ["Posto médio", "Qual estratégia fica à frente dentro de cada módulo?",
      f"PlnFS {npos(PM['J'][5])} (melhor) e ZS {npos(PM['J'][0])} (pior)"],
     ["Cobertura dos aprovados", "Quanto do circuito os <i>testbenches</i> exercitam?",
      "Linha e desvio acima de 89%, alternância entre 71,0% e 74,1%"],
     ["100% de cobertura com mutante vivo", "Cobertura completa garante detectar as falhas?",
      f"Não. {lin_cheio[1]} de {lin_cheio[0]} ({prop(lin_cheio)}) na linha"]],
    [40 * mm, 74 * mm, 60 * mm])

# ---- 1. Dados de partida
st(P("1. Os dados de partida", "h1"))
st(P(f"Cada estratégia gerou um <i>testbench</i> para cada módulo, em cada LLM e em cada rodada. "
     f"Isso dá 10 módulos × 6 estratégias × 2 LLMs × 2 rodadas = {len(TB)} <i>testbenches</i>."))
st(P(f"Cada <i>testbench</i> foi executado primeiro no circuito original, que está correto. Se ele "
     f"não compilou ou falhou, a planilha registra \"Não passou\" ({N_NP} casos). Se a simulação passou do tempo "
     f"limite, registra \"Timeout\" ({N_TO} caso). Se ele passou, foi executado contra os 4 mutantes "
     f"do módulo, e a planilha registra quantos ele detectou, de 0/4 a 4/4. Para os aprovados, a "
     f"ferramenta também salvou a cobertura de linha, de desvio e de alternância."))
dg = D["Cs450/gshare"]
ab = {NP: "NP", "Timeout": "TO"}
tab("Tabela 2. Exemplo da planilha, GPT no Cs450/gshare",
    ["Rodada", "ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"],
    [[f"Rodada {r}"] + [ab.get(RODADAS[r][G][dg][e], RODADAS[r][G][dg][e]) for e in range(6)]
     for r in (1, 2)],
    W7, nota="NP = Não passou. \"3/4\" significa que o <i>testbench</i> detectou 3 dos 4 mutantes. "
             + LEG)
st(P("Todos os resultados a seguir são calculados a partir dessas células. Eles são descritivos, "
     "ou seja, não foram aplicados testes estatísticos de hipótese."))

# ---- 2. Taxa de aprovação
st(P("2. Taxa de aprovação", "h1"))
st(P("<b>Como se calcula.</b> Conta-se quantos <i>testbenches</i> passaram no circuito original e "
     "divide-se pelo número de <i>testbenches</i> gerados."))
st(caixa("Taxa de aprovação = <i>testbenches</i> aprovados ÷ <i>testbenches</i> gerados × 100%"))
z = sel(e=0)
st(P(f"<b>Exemplo.</b> A <i>Zero-shot</i> gerou 40 <i>testbenches</i> e {apr(z)} foram aprovados, "
     f"então a taxa dela é {apr(z)} ÷ 40 = {pct(Fraction(100 * apr(z), 40))}."))
lin = []
for e in range(6):
    l = sel(e=e)
    lin.append([NOME_ESTR[ESTR[e]], f"{apr(sel(G, e=e))}/20", f"{apr(sel(GM, e=e))}/20",
                f"{apr(l)}/40", pct(Fraction(100 * apr(l), 40))])
lin.append(["Total", f"{apr(sel(G))}/120", f"{apr(sel(GM))}/120", f"{apr(TB)}/240",
            pct(Fraction(100 * apr(TB), 240))])
tab("Tabela 3. Testbenches aprovados por estratégia e LLM",
    ["Estratégia", "GPT", "Gemini", "Total", "Taxa"], lin,
    [58 * mm, 29 * mm, 29 * mm, 29 * mm, 29 * mm], destacar_ultima=True)
representa([
    "A taxa de aprovação mostra se a estratégia gera <i>testbenches</i> que funcionam. Como o "
    "circuito original está correto, um <i>testbench</i> reprovado tem um erro nele mesmo, como "
    "um valor esperado errado ou uma checagem no momento errado.",
    "Ela não diz nada sobre a detecção de falhas. Um <i>testbench</i> que não verifica nada também "
    "é aprovado. Por isso ela não é usada sozinha para comparar as estratégias."])

# ---- 3. Score efetivo
st(P("3. <i>Score</i> efetivo", "h1"))
st(P("<b>Como se calcula.</b> Soma-se o número de mutantes que cada <i>testbench</i> detectou e "
     "divide-se pelo total de falhas possível. Como cada <i>testbench</i> enfrenta 4 mutantes, o "
     "total possível é 4 vezes o número de <i>testbenches</i> gerados. Os reprovados e o "
     "<i>timeout</i> entram com zero, pois o teste de mutação não é executado para eles."))
st(caixa("<i>Score</i> efetivo = mutantes detectados ÷ (4 × <i>testbenches</i> gerados) × 100%"))
p5, p5g = sel(e=5), sel(G, e=5)
st(P(f"<b>Exemplo.</b> A <i>Planning Few-shot</i> gerou 40 <i>testbenches</i>, então poderia detectar "
     f"até 4 × 40 = 160 mutantes. Ela detectou {det(p5)}, e o <i>score</i> efetivo dela é "
     f"{det(p5)} ÷ 160 = {pct(ef(p5))}. Só no GPT, foram {det(p5g)} de 80, ou seja, "
     f"{n(ef(p5g), 2)}%, que arredondado fica {pct(ef(p5g))}."))
lin = []
for e in range(6):
    lg, lm, l = sel(G, e=e), sel(GM, e=e), sel(e=e)
    lin.append([NOME_ESTR[ESTR[e]], f"{det(lg)}/80", pct(ef(lg)), f"{det(lm)}/80", pct(ef(lm)),
                f"{det(l)}/160", pct(ef(l))])
lg, lm = sel(G), sel(GM)
lin.append(["Total", f"{det(lg)}/480", pct(ef(lg)), f"{det(lm)}/480", pct(ef(lm)),
            f"{det(TB)}/960", pct(ef(TB))])
tab("Tabela 4. Mutantes detectados e score efetivo",
    ["Estratégia", "GPT detectou", "GPT", "Gemini detectou", "Gemini", "Total detectou", "Total"],
    lin, [44 * mm, 22 * mm, 20 * mm, 22 * mm, 20 * mm, 24 * mm, 22 * mm], destacar_ultima=True)
st(caixa(["<b>Arredondamento (ABNT NBR 5891).</b> Quando o que sobra é exatamente 5, o último "
          "algarismo mantido fica par. Assim, 56,25 vira 56,2 (o 2 já é par), 33,75 vira 33,8 (o 7 "
          "vira 8) e 90,85 vira 90,8. Quando sobra menos que 5, o algarismo fica igual, como em "
          "38,125, que vira 38,1. Quando sobra mais que 5, arredonda-se para cima, como em "
          "66,875, que vira 66,9."], fundo=AMARELO, borda=OCRE,
         estilo="corpo"))
representa([
    "O <i>score</i> efetivo mostra quanto das falhas possíveis a estratégia detectou. Ele junta as "
    "duas coisas, gerar um <i>testbench</i> que funciona e esse <i>testbench</i> detectar falhas. "
    "Uma estratégia que gera muitos <i>testbenches</i> quebrados perde pontos, porque os 4 mutantes "
    "deles continuam no denominador.",
    f"É por isso que o Gemini teve mais aprovados ({apr(lm)} contra {apr(lg)}) e, mesmo assim, "
    f"<i>score</i> efetivo menor ({pct(ef(lm))} contra {pct(ef(lg))}). Os <i>testbenches</i> dele "
    f"passam mais, mas verificam menos."])

# ---- 4. Com e sem exemplos
st(P("4. Estratégias com e sem exemplos", "h1"))
st(P("<b>Como se calcula.</b> As estratégias foram separadas em dois grupos. Com exemplos ficam a "
     "<i>Few-shot</i>, a Especialista <i>Few-shot</i> e a <i>Planning Few-shot</i>. Sem exemplos ficam "
     "as três versões <i>Zero-shot</i>. O <i>score</i> efetivo de cada grupo junta os mutantes "
     "detectados pelas três estratégias. Como todas têm o mesmo número de <i>testbenches</i>, isso "
     "é igual à média dos três <i>scores</i>. Depois, o mesmo cálculo foi repetido para cada LLM."))
st(P(f"<b>Exemplo.</b> Com os dois LLMs juntos, o grupo com exemplos teve "
     f"({n(ef_e[1], 3)} + {n(ef_e[3], 3)} + {n(ef_e[5], 3)}) ÷ 3 = {pct(ef(sel(e=COM)))}."))
lin, fam = [], {}
for rot, kw in [("Os dois LLMs juntos", {}), ("GPT", {"m": G}), ("Gemini", {"m": GM})]:
    c, s = ef(sel(e=COM, **kw)), ef(sel(e=SEM, **kw))
    fam[rot] = (c, s)
    lin.append([rot, pct(c), pct(s), dif(c - s)])
assert [pct(x) for x in fam["Os dois LLMs juntos"]] == ["61,0%", "47,1%"]
tab("Tabela 5. Score efetivo com e sem exemplos",
    ["Recorte", "Com exemplos", "Sem exemplos", "Diferença (pontos)"], lin,
    [62 * mm, 37 * mm, 37 * mm, 38 * mm],
    nota="A diferença é calculada com os valores sem arredondar. Por isso, com os dois LLMs juntos, "
         "ela aparece como 14,0, embora 61,0 − 47,1 = 13,9. No TCC aparecem só os dois "
         "<i>scores</i>.")
representa([
    "Com os dois LLMs juntos, os exemplos ajudaram, e esse é o principal resultado do trabalho.",
    f"A vantagem apareceu nos dois LLMs e foi maior no Gemini, em que o grupo sem exemplos teve o "
    f"<i>score</i> mais baixo ({pct(fam['Gemini'][1])}). No GPT, a diferença foi menor "
    f"({pct(fam['GPT'][0])} contra {pct(fam['GPT'][1])}).",
    "Os resultados são descritivos. Eles mostram o que aconteceu neste experimento, sem um teste "
    "estatístico que prove a diferença."])

# ---- 5. Posto médio
st(P("5. Posto médio", "h1"))
st(P("<b>Como se calcula.</b> O posto médio é uma classificação feita dentro de cada módulo, em "
     "três passos."))
st(item("<b>Passo 1.</b> Em cada módulo e em cada LLM, calcula-se a média de mutantes detectados "
        "por cada estratégia nas duas rodadas. Um <i>testbench</i> reprovado conta como zero."))
st(item("<b>Passo 2.</b> As seis médias são ordenadas, e cada estratégia recebe uma posição de 1 "
        "(pior) a 6 (melhor). Se duas ou mais empatam, todas recebem a média das posições que "
        "ocupariam."))
st(item("<b>Passo 3.</b> O posto médio de cada estratégia é a média das posições que ela recebeu. "
        "Cada LLM tem 10 classificações, uma por módulo, e os dois juntos têm 20."))
st(caixa("Posto médio = soma das posições da estratégia ÷ número de classificações"))
med, pos = classif(G, dg)
assert [float(x) for x in med] == [1.5, 3, 1.5, 1, 1.5, 1.5]
assert [float(x) for x in pos] == [3.5, 6, 3.5, 1, 3.5, 3.5]
tab("Tabela 6. Exemplo de uma classificação, GPT no Cs450/gshare",
    ["Estratégia", "Rodada 1", "Rodada 2", "Média", "Posição"],
    [[NOME_ESTR[ESTR[e]], mortos(RODADAS[1][G][dg][e]), mortos(RODADAS[2][G][dg][e]),
      n(med[e], 1), n(pos[e], 1)] for e in range(6)],
    [58 * mm, 29 * mm, 29 * mm, 29 * mm, 29 * mm],
    nota="Os reprovados (NP na Tabela 2) aparecem como 0.")
st(P("A Especialista <i>Few-shot</i> teve a menor média (1) e ficou com a posição 1. Quatro "
     "estratégias empataram com 1,5 e ocupariam as posições 2, 3, 4 e 5, por isso todas recebem a "
     "média delas, que é 3,5. A <i>Few-shot</i> teve a maior média (3) e ficou com a posição 6. A "
     "soma das posições é sempre 21, então a média das seis posições é sempre 3,5."))
for m, num in ((G, 7), (GM, 8)):
    lin = [[NOME[d]] + [n(classif(m, d)[1][e], 1) for e in range(6)] for d in ORDEM]
    lin.append(["<b>Posto médio</b>"] + [f"<b>{npos(x)}</b>" for x in PM[m]])
    tab(f"Tabela {num}. Posições de cada estratégia em cada módulo, {CURTO[m]}",
        ["Módulo", "ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"], lin, W7,
        destacar_ultima=True, nota="A última linha é a média da coluna. " + LEG)
tab("Tabela 9. Posto médio por LLM e com os dois juntos",
    ["Estratégia", "GPT (10 classificações)", "Gemini (10 classificações)",
     "Juntos (20 classificações)"],
    [[NOME_ESTR[ESTR[e]], npos(PM[G][e]), npos(PM[GM][e]), npos(PM["J"][e])] for e in range(6)],
    [52 * mm, 40 * mm, 41 * mm, 41 * mm],
    nota="Com os dois juntos, o posto médio é a média das 20 posições. Como cada LLM tem 10, isso "
         "é igual à média dos postos do GPT e do Gemini. Os valores 3,675 e 3,625 são exatos e "
         "ficam com três casas.")
representa([
    "O posto médio mostra qual estratégia costuma ficar à frente das outras dentro de um mesmo "
    "módulo. Quanto maior, melhor, e 3,5 é o valor de quem fica sempre no meio.",
    "Como a comparação é feita dentro de cada módulo, um módulo fácil, em que todas detectaram "
    "tudo, não pesa mais que os outros. No Lemmings1 do GPT, por exemplo, todas empataram e "
    "receberam 3,5.",
    "Ele mostra a ordem, mas não o tamanho da diferença em mutantes. Por isso ele é usado junto "
    "com o <i>score</i> efetivo."])

# ---- 6. Cobertura dos aprovados
st(P("6. Cobertura dos <i>testbenches</i> aprovados", "h1"))
st(P("A cobertura mede quanto do circuito o <i>testbench</i> exercitou, e o Verilator mede três "
     "tipos."))
st(item("<b>Linha.</b> Porcentagem das linhas do código que foram executadas pelo menos uma vez."))
st(item("<b>Desvio.</b> Porcentagem dos caminhos de <font name='DVM'>if</font> e "
        "<font name='DVM'>case</font> que foram percorridos. Num <font name='DVM'>if</font>, é "
        "preciso passar tanto pelo lado verdadeiro quanto pelo falso."))
st(item("<b>Alternância.</b> Porcentagem dos bits dos sinais que mudaram de 0 para 1 e de 1 para "
        "0. É a mais difícil de completar, porque cada bit de um sinal largo precisa mudar."))
st(P("<b>Como se calcula.</b> Faz-se a média de cada tipo de cobertura só entre os "
     "<i>testbenches</i> aprovados. Os reprovados ficam de fora, porque têm erro neles mesmos e "
     "muitos param a simulação no primeiro erro. Para comparar com a detecção nos mesmos "
     "<i>testbenches</i>, calcula-se também o <i>score</i> dos aprovados."))
st(caixa("<i>Score</i> dos aprovados = mutantes detectados ÷ (4 × <i>testbenches</i> aprovados) × 100%"))
a5 = sel(e=5, ok=True)
st(P(f"<b>Exemplo.</b> A <i>Planning Few-shot</i> teve {len(a5)} aprovados, que detectaram "
     f"{det(a5)} mutantes. O <i>score</i> dos aprovados é {det(a5)} ÷ (4 × {len(a5)}) = "
     f"{pct(ef(a5))}. A cobertura de desvio média desses {len(a5)} é "
     f"{n(cobmed(a5, 'branch'), 2)}%, que pela ABNT fica {pct(cobmed(a5, 'branch'))}."))
lin = []
for rot, l in ([(NOME_ESTR[ESTR[e]], sel(e=e, ok=True)) for e in range(6)]
               + [(m, sel(m, ok=True)) for m in MODELOS]):
    lin.append([rot, len(l)] + [pct(cobmed(l, k)) for k in MET] + [pct(ef(l))])
tab("Tabela 10. Cobertura média e score dos aprovados",
    ["Estratégia ou LLM", "Aprovados", "Linha", "Desvio", "Alternância",
     "<i>Score</i> dos aprovados"],
    lin, [50 * mm, 22 * mm, 24 * mm, 24 * mm, 26 * mm, 28 * mm])
faixa = {k: (min(cobmed(sel(e=e, ok=True), k) for e in range(6)),
             max(cobmed(sel(e=e, ok=True), k) for e in range(6))) for k in MET}
sc = [ef(sel(e=e, ok=True)) for e in range(6)]
NA = {"linha": "na linha", "branch": "no desvio", "toggle": "na alternância"}
representa([
    "Entre as estratégias, a cobertura quase não mudou. A diferença entre a maior e a menor foi de "
    + ", ".join(f"{n(faixa[k][1] - faixa[k][0])} pontos {NA[k]}" for k in MET[:-1])
    + f" e {n(faixa[MET[-1]][1] - faixa[MET[-1]][0])} pontos {NA[MET[-1]]}"
    + f". Já o <i>score</i> dos aprovados variou mais, de {pct(min(sc))} a {pct(max(sc))}.",
    "Entre os LLMs, a cobertura de linha foi parecida, mas o <i>score</i> dos aprovados foi muito "
    "diferente. Ou seja, exercitar o código não é o mesmo que verificar as saídas.",
    "Cada estratégia teve um número diferente de aprovados, em módulos diferentes. Por isso essas "
    "médias devem ser comparadas com cautela."])

# ---- 7. 100% de cobertura com mutante vivo
st(P("7. 100% de cobertura com mutante vivo", "h1"))
st(P("<b>Como se calcula.</b> Para cada tipo de cobertura, pegam-se os <i>testbenches</i> aprovados "
     "que chegaram a 100% e conta-se quantos deixaram pelo menos um mutante sem detectar, ou seja, "
     "detectaram menos de 4."))
st(caixa("Proporção = <i>testbenches</i> com 100% e algum mutante vivo ÷ <i>testbenches</i> com "
         "100% × 100%"))
lin = []
for k in MET:
    t, v = cheio(k)
    tg, vg = cheio(k, [G])
    tm, vm = cheio(k, [GM])
    ts, vs = cheio(k, sem_cordic=True)
    lin.append([NOME_MET[k], f"{v} de {t}", prop((t, v)),
                f"{vg} de {tg} ({prop((tg, vg))})",
                f"{vm} de {tm} ({prop((tm, vm))})",
                f"{vs} de {ts} ({prop((ts, vs))})"])
tab("Tabela 11. Testbenches aprovados com 100% de cobertura e algum mutante vivo",
    ["Cobertura", "Vivos de 100%", "Proporção", "GPT", "Gemini", "Sem o CORDIC"], lin,
    [24 * mm, 26 * mm, 22 * mm, 34 * mm, 34 * mm, 34 * mm],
    nota="Um mutante do CORDIC é equivalente e não pode ser detectado, então todo "
         "<i>testbench</i> dele deixa um mutante vivo. Na linha, nenhum do CORDIC chegou a 100%.")
representa([
    "Ter 100% de cobertura não garantiu detectar todas as falhas. A cobertura só mostra que o "
    "código foi executado, e não se o <i>testbench</i> conferiu a saída.",
    "O problema foi bem maior no Gemini, o que bate com o <i>score</i> dos aprovados menor. Esse "
    "resultado justifica usar o teste de mutação como métrica principal do trabalho."])

construir(saida("resultados_explicados.pdf"), story, TITULO)
print("ok:", saida("resultados_explicados.pdf"))
