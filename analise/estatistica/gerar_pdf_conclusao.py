"""Gera o PDF "Conclusão da análise estatística" (Friedman + Wilcoxon juntos, 2 rodadas).

Os numeros sao recalculados com o SciPy a partir da linha "Mutantes" da planilha (os mesmos
valores dos PDFs de Friedman e Wilcoxon, que conferem seus calculos contra o SciPy). O valor
analisado e a media das 2 rodadas em cada celula.
Uso: python gerar_pdf_conclusao.py [saida.pdf]   (padrao: documentacao/conclusao_estatistica.pdf)
"""
import itertools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer, TableStyle
from scipy.stats import combine_pvalues, friedmanchisquare, rankdata, spearmanr

from pdf_comum import (AMARELO, CIRCUITOS, CURTO, ESTR, MODELOS, NOME_ESTR, OCRE, Q_NEMENYI_6,
                       VERDE, VERDE_BORDA, br, caixa, celulas, construir, fonte, holm, item,
                       nemenyi_cd, P, saida, secao_referencias, tabela, valores, wilc)

TITULO = "Conclusão da análise estatística"
ZS_FAM, FS_FAM = [0, 2, 4], [1, 3, 5]
VERMELHO = colors.HexColor("#FDECEA")
VERMELHO_BORDA = colors.HexColor("#C62828")
PARES_SHOT = [("ZS", "FS"), ("EspZS", "EspFS"), ("PlnZS", "PlnFS")]
PARES_REF = [("ZS", "EspZS"), ("ZS", "PlnZS"), ("FS", "EspFS"), ("FS", "PlnFS")]


def coluna(vals, j):
    return [linha[j] for linha in vals]


def familias(vals):
    return ([sum(l[j] for j in ZS_FAM) for l in vals], [sum(l[j] for j in FS_FAM) for l in vals])


def analisar(val):
    """Todos os testes para um conjunto de valores {modelo: [[...] x 10]}."""
    juntos = val[MODELOS[0]] + val[MODELOS[1]]
    casos = {**val, "juntos": juntos}
    fri = {}
    for nome, vals in casos.items():
        sp = friedmanchisquare(*[coluna(vals, j) for j in range(6)])
        rk = [rankdata(linha) for linha in vals]
        medios = [sum(r[j] for r in rk) / len(rk) for j in range(6)]
        fri[nome] = dict(Q=float(sp.statistic), p=float(sp.pvalue), medios=medios,
                         W=float(sp.statistic) / (len(vals) * 5))
    wil = {nome: wilc(*familias(vals)) for nome, vals in casos.items()}
    fisher = float(combine_pvalues([wil[m][4] for m in MODELOS], method="fisher").pvalue)
    # pos-teste do Friedman com os dois juntos: 15 pares, Nemenyi + Wilcoxon com Holm
    med, n = fri["juntos"]["medios"], len(juntos)
    pos = []
    for i, j in itertools.combinations(range(6), 2):
        a, b = (i, j) if med[i] >= med[j] else (j, i)
        g, pe, e, T, p = wilc(coluna(juntos, b), coluna(juntos, a))
        pos.append(dict(a=a, b=b, dif=med[a] - med[b], p=p, g=g, pe=pe))
    for l, h in zip(pos, holm([l["p"] for l in pos])):
        l["holm"], l["nem"] = h, l["dif"] > nemenyi_cd(6, n)
    pos.sort(key=lambda l: l["p"])
    # pares de um fator, juntos, com Holm dentro de cada grupo
    par = {}
    for grupo in (PARES_SHOT, PARES_REF):
        ws = [wilc(coluna(juntos, ESTR.index(a)), coluna(juntos, ESTR.index(b))) for a, b in grupo]
        for (a, b), w, h in zip(grupo, ws, holm([w[4] for w in ws])):
            par[(a, b)] = dict(g=w[0], pe=w[1], e=w[2], p=w[4], holm=h)
    return dict(fri=fri, wil=wil, fisher=fisher, pos=pos, par=par, cd=nemenyi_cd(6, n))


A = analisar({m: valores(m) for m in MODELOS})                                   # media das 2
R1 = analisar({m: valores(m, 1) for m in MODELOS})
R2 = analisar({m: valores(m, 2) for m in MODELOS})
A1E = analisar({m: valores(m, primeiro_envio=True) for m in MODELOS})            # robustez

# a 1a rodada sozinha tem que bater com os PDFs anteriores (so com ela)
assert round(R1["fri"][MODELOS[0]]["Q"], 2) == 6.12 and round(R1["fri"][MODELOS[1]]["Q"], 2) == 5.31
assert round(R1["wil"]["juntos"][4], 3) == 0.009 and round(R1["fisher"], 3) == 0.044

g, m2 = MODELOS
fj, fg, fm = A["fri"]["juntos"], A["fri"][g], A["fri"][m2]
wj, wg, wm = A["wil"]["juntos"], A["wil"][g], A["wil"][m2]
POS_SIG = [l for l in A["pos"] if l["nem"] and l["holm"] < 0.05]
TOP = max(range(6), key=lambda j: fj["medios"][j])
ULT = min(range(6), key=lambda j: fj["medios"][j])
# o 1o colocado contra o 2o, 3o e 4o: o menor p, ainda sem correcao
VIZINHOS = sorted(range(6), key=lambda j: -fj["medios"][j])[1:4]
TOP_P = min(l["p"] for l in A["pos"] if {l["a"], l["b"]} in [{TOP, v} for v in VIZINHOS])
segundo = sorted(fj["medios"], reverse=True)[1]
DELTA = fj["medios"][TOP] - segundo
N_PRECISO = Q_NEMENYI_6 ** 2 * 42 / (6 * DELTA ** 2)        # blocos para a DC ficar < DELTA
REF_HOLM_MIN = min(A["par"][p]["holm"] for p in PARES_REF)
ZSFS = A["par"][("ZS", "FS")]


def sentido(vals):
    """+1 se a familia few-shot leva vantagem no Wilcoxon (W+ > W-), -1 se a zero-shot, 0 empate."""
    zs, fs = familias(vals)
    d = [b - a for a, b in zip(zs, fs) if b != a]
    s = float(sum(ri if x > 0 else -ri for ri, x in zip(rankdata([abs(x) for x in d]), d)))
    return (s > 0) - (s < 0)


CLARO = [CURTO[m] for m in MODELOS if A["wil"][m][4] < 0.05]
NAO_SIG = [CURTO[m] for m in MODELOS if A["wil"][m][4] >= 0.05]
MUDOU = [CURTO[m] for m in MODELOS if sentido(valores(m, 1)) != sentido(valores(m, 2))]
if CLARO and NAO_SIG:
    EFEITO = f"significativo no {' e no '.join(CLARO)} e não no {' e no '.join(NAO_SIG)}"
elif CLARO:
    EFEITO = "significativo também em cada modelo"
else:
    EFEITO = "sem significância em cada modelo isolado"


# descritivo: aprovados (de 20) e score efetivo (mortos / 80) somando as 2 rodadas
def descritivo(m):
    c = celulas(m, 1) + celulas(m, 2)
    v = valores(m, 1) + valores(m, 2)
    return {e: (sum(1 for l in c if l[j].endswith("/4")), 100 * sum(coluna(v, j)) / 80)
            for j, e in enumerate(ESTR)}


DESC = {m: descritivo(m) for m in MODELOS}


# estabilidade entre rodadas: celula a celula
def estabilidade(m):
    def cod(cel):
        return int(cel[0]) if cel.endswith("/4") else -1
    a = [cod(x) for l in celulas(m, 1) for x in l]
    b = [cod(x) for l in celulas(m, 2) for x in l]
    iguais = sum(x == y for x, y in zip(a, b))
    viradas = sum((x < 0 and y >= 3) or (y < 0 and x >= 3) for x, y in zip(a, b))
    rho = spearmanr([max(x, 0) for x in a], [max(y, 0) for y in b])[0]
    tot = (sum(max(x, 0) for x in a), sum(max(y, 0) for y in b))
    return dict(iguais=iguais, viradas=viradas, rho=float(rho), tot=tot)


EST = {m: estabilidade(m) for m in MODELOS}


def media_fam(medios, fam):
    return sum(medios[j] for j in fam) / 3


def p3(x):
    return br(x, 3)


story = []
st = story.append
st(P(TITULO, "titulo"))
st(P("O que os testes de Friedman e Wilcoxon dizem, juntos, sobre as estratégias de prompt na "
     "geração de testbenches por LLM — média das 2 rodadas", "sub"))
st(Spacer(1, 10))
st(caixa([
    "<b>Conclusão em uma frase:</b> usar exemplos no prompt (few-shot) faz os LLMs gerarem "
    f"testbenches que detectam significativamente mais defeitos (com os dois modelos analisados "
    f"juntos; {EFEITO}); as seis estratégias não são todas iguais, mas "
    "<b>nenhuma pode ser apontada como a melhor</b>: o que se comprova é a vantagem das versões com "
    "exemplos sobre o zero-shot.",
], fundo=VERDE, borda=VERDE_BORDA))

# ---- 1 ----
st(P("1. As perguntas e as respostas", "h1"))
st(tabela(["Teste", "Pergunta", "Resultado", "Resposta"], [
    ["Friedman (6 estratégias)", "Alguma das seis estratégias é diferente das outras?",
     f"GPT p = {p3(fg['p'])}<br/>Gemini p = {p3(fm['p'])}<br/>Juntos p = {p3(fj['p'])}",
     "<b>Sim</b>, com os dois modelos juntos" if fj["p"] < 0.05 else "<b>Não</b> dá para afirmar"],
    ["Pós-teste do Friedman (15 pares)", "Qual estratégia é a melhor?",
     (" ".join(f"{ESTR[l['a']]} &gt; {ESTR[l['b']]}: p corrigido = {p3(l['holm'])}" for l in POS_SIG)
      or "nenhum par") + "<br/>todos os outros: p corrigido ≥ "
     + p3(min(l["holm"] for l in A["pos"] if l not in POS_SIG)),
     "<b>Não dá para eleger</b> uma melhor"],
    ["Wilcoxon (família FS × ZS)", "Ter exemplos no prompt melhora o testbench?",
     f"GPT p = {p3(wg[4])}<br/>Gemini p = {p3(wm[4])}<br/>Juntos p = {p3(wj[4])}<br/>"
     f"Fisher p = {p3(A['fisher'])}",
     "<b>Sim</b>, com os dois modelos juntos" if wj[4] < 0.05 else "<b>Não</b> dá para afirmar"],
    ["Wilcoxon (pares do exemplo)", "O exemplo ajuda em cada estilo de prompt?",
     "<br/>".join(f"{a} × {b}: p corrigido = {p3(A['par'][(a, b)]['holm'])}" for a, b in PARES_SHOT),
     ("<b>Sim</b> no prompt simples (ZS × FS); nos outros, não dá para afirmar"
      if ZSFS["holm"] < 0.05 else "<b>Não</b> dá para afirmar")],
], [36 * mm, 46 * mm, 52 * mm, 40 * mm]))
st(P("Valor analisado: mutantes mortos por circuito (0 a 4), com “Não passou” e “Timeout” valendo "
     "0, na média das 2 rodadas. Nível de significância: 5%. “Juntos” = GPT e Gemini na mesma "
     "análise (20 circuitos-modelo). Detalhes de cada cálculo nos PDFs “Teste de Friedman — passo "
     "a passo” e “Teste de Wilcoxon pareado — passo a passo”.", "nota"))

# ---- 2 ----
st(P("2. O que a 2ª rodada mudou", "h1"))
st(P("Na 2ª rodada, cada estratégia gerou testbenches novos para os mesmos circuitos (mesmo RTL, "
     "mesmos 4 mutantes). Juntar as duas rodadas pela média reduz o efeito do acaso de cada "
     "execução do LLM, e os testes ficaram mais claros:"))
st(tabela(["Teste", "Só a rodada 1", "Só a rodada 2", "Média das 2 rodadas"], [
    ["Friedman, juntos", p3(R1["fri"]["juntos"]["p"]), p3(R2["fri"]["juntos"]["p"]),
     f"<b>{p3(fj['p'])}</b>"],
    ["Wilcoxon família, GPT", p3(R1["wil"][g][4]), p3(R2["wil"][g][4]), f"<b>{p3(wg[4])}</b>"],
    ["Wilcoxon família, Gemini", p3(R1["wil"][m2][4]), p3(R2["wil"][m2][4]), f"<b>{p3(wm[4])}</b>"],
    ["Wilcoxon família, juntos", p3(R1["wil"]["juntos"][4]), p3(R2["wil"]["juntos"][4]),
     f"<b>{p3(wj[4])}</b>"],
    ["Fisher (GPT + Gemini)", p3(R1["fisher"]), p3(R2["fisher"]), f"<b>{p3(A['fisher'])}</b>"],
], [56 * mm, 39 * mm, 40 * mm, 39 * mm]))
st(P("Valores: p-valor de cada teste.", "nota"))
st(P("As duas rodadas não concordam célula a célula", "h2"))
eg, em = EST[g], EST[m2]
st(tabela(["", "GPT-5.6 Luna", "Gemini 3.5 Flash-Lite"], [
    ["Células iguais nas duas rodadas", f"{eg['iguais']}/60", f"{em['iguais']}/60"],
    ["Células que trocaram entre “Não passou” e 3/4 ou 4/4", f"{eg['viradas']}/60", f"{em['viradas']}/60"],
    ["Correlação de Spearman entre as rodadas", br(eg["rho"], 2), br(em["rho"], 2)],
    ["Mutantes mortos no total (rodada 1 → rodada 2)", f"{eg['tot'][0]} → {eg['tot'][1]}",
     f"{em['tot'][0]} → {em['tot'][1]}"],
], [86 * mm, 44 * mm, 44 * mm]))
inst, est_m = (g, m2) if eg["viradas"] >= em["viradas"] else (m2, g)
st(P(f"O mesmo prompt, no mesmo circuito, pode gerar um testbench que passa e mata 4 mutantes numa "
     f"rodada e um que nem passa no circuito original na outra. Isso aconteceu em "
     f"{EST[inst]['viradas']} das 60 células do {CURTO[inst]} e em {EST[est_m]['viradas']} do "
     f"{CURTO[est_m]}: o <b>{CURTO[inst]} é bem menos estável</b>. Os totais mudaram entre as rodadas, "
     f"mas isso não é melhora das estratégias (os prompts e o RTL são os mesmos): é a variação "
     f"do próprio LLM. É por isso que se repete a execução e se analisa a média."))
st(fonte("repetir as execuções de algoritmos aleatórios e analisar o conjunto: Arcuri e Briand "
         "(2011); correlação de Spearman: Siegel e Castellan Jr. (2006)."))

# ---- 3 ----
st(P("3. Como os resultados se encaixam", "h1"))
st(item("O <b>Friedman</b> olha as seis estratégias ao mesmo tempo: com os dois modelos juntos, "
        "elas <b>não são todas iguais</b>."))
st(item(f"O <b>pós-teste</b> procura quais pares diferem, corrigindo para os 15 pares: só "
        + (" e ".join(f"{NOME_ESTR[ESTR[l['a']]]} &gt; {NOME_ESTR[ESTR[l['b']]]}" for l in POS_SIG)
           or "nenhum") + " passa. As estratégias do topo ficam próximas demais entre si."))
st(item("O <b>Wilcoxon</b> faz o confronto planejado com exemplos × sem exemplos, somando as três "
        "variantes de cada lado: nele a diferença aparece."))
st(P("A diferença está entre <b>ter ou não ter exemplos</b> (e, entre as seis, principalmente entre o "
     "zero-shot e as versões com exemplo); entre as estratégias do topo não há separação. Os postos "
     "médios do Friedman mostram isso:"))
linhas = []
for zs, fs in PARES_SHOT:
    jz, jf = ESTR.index(zs), ESTR.index(fs)
    lin = [f"{NOME_ESTR[zs]} → {NOME_ESTR[fs]}"]
    for nome in (g, m2, "juntos"):
        a, b = A["fri"][nome]["medios"][jz], A["fri"][nome]["medios"][jf]
        lin.append(f"{br(a, 2)} → {br(b, 2)}  {'✓' if b > a else '✗'}")
    linhas.append(lin)
linhas.append(["<b>Média da família: zero-shot → few-shot</b>"] + [
    f"<b>{br(media_fam(A['fri'][n]['medios'], ZS_FAM), 2)} → "
    f"{br(media_fam(A['fri'][n]['medios'], FS_FAM), 2)}</b>" for n in (g, m2, "juntos")])
st(tabela(["Sem exemplo → com exemplo (posto médio)", "GPT-5.6 Luna", "Gemini 3.5 Flash-Lite",
           "Juntos"], linhas, [68 * mm, 35 * mm, 36 * mm, 35 * mm], destacar_ultima=True))
st(Spacer(1, 4))
nao = [(n, zs, fs) for n in (g, m2) for zs, fs in PARES_SHOT
       if A["fri"][n]["medios"][ESTR.index(fs)] <= A["fri"][n]["medios"][ESTR.index(zs)]]
st(P(f"Em {6 - len(nao)} das 6 comparações por modelo, a versão com exemplo ficou à frente da versão "
     f"sem exemplo"
     + (". A exceção" + ("" if len(nao) == 1 else "s") + " ("
        + "; ".join(f"{CURTO[n]}: {NOME_ESTR[zs]} → {NOME_ESTR[fs]}" for n, zs, fs in nao)
        + ") mostra que o exemplo não ajuda sempre." if nao else ".")))
st(fonte("postos médios do teste de Friedman (FRIEDMAN, 1937; SIEGEL; CASTELLAN JR., 2006); "
         "pós-teste: Demšar (2006) e Holm (1979); contraste de famílias pelo teste de Wilcoxon "
         "(WILCOXON, 1945)."))

# ---- 4 ----
st(P("4. O que se pode concluir", "h1"))
st(KeepTogether([P("Pode afirmar (comprovado estatisticamente)", "h2"), caixa([
    f"• <b>A estratégia de prompt influencia a qualidade do testbench.</b> Com os dois modelos "
    f"juntos, o Friedman indicou diferença entre as seis estratégias (χ<super>2</super>(5) = "
    f"{br(fj['Q'], 2)}; p = {p3(fj['p'])}).",
    f"• <b>Exemplos no prompt melhoram o testbench.</b> A família few-shot matou mais mutantes que a "
    f"zero-shot (juntos: few-shot à frente em {wj[0]} e atrás em {wj[1]} dos 20 pares, "
    f"p = {p3(wj[4])}; Fisher p = {p3(A['fisher'])}). No Gemini o efeito é significativo sozinho "
    f"(p = {p3(wm[4])}).",
    f"• <b>No prompt simples, o exemplo faz diferença:</b> Few-shot &gt; Zero-shot (juntos: ganhou em "
    f"{ZSFS['g']} e perdeu em {ZSFS['pe']} dos 20 pares; p corrigido = {p3(ZSFS['holm'])}).",
], fundo=VERDE, borda=VERDE_BORDA, estilo="corpo")]))
dg, dm = DESC[g], DESC[m2]


def ganho_reforco(d):
    sem = (d["EspZS"][1] + d["PlnZS"][1]) / 2 - d["ZS"][1]
    com = (d["EspFS"][1] + d["PlnFS"][1]) / 2 - d["FS"][1]
    return sem, com


sug = [
    f"• <b>O {NOME_ESTR[ESTR[TOP]]} ficou na frente:</b> maior posto médio ({br(fj['medios'][TOP], 2)}) "
    + (f"e único par significativo no pós-teste ({ESTR[TOP]} &gt; {ESTR[ULT]}, p corrigido = "
       f"{p3(POS_SIG[0]['holm'])}). Mas esse par depende de 2 células reenviadas: com o 1º envio "
       f"delas, o p corrigido vai a {p3(next(l['holm'] for l in A1E['pos'] if (l['a'], l['b']) == (TOP, ULT)))} "
       f"(seção 7)." if len(POS_SIG) == 1 and (POS_SIG[0]["a"], POS_SIG[0]["b"]) == (TOP, ULT) else "."),
    f"• <b>O {NOME_ESTR[ESTR[ULT]]} é o último:</b> menor posto médio com os dois modelos juntos "
    f"({br(fj['medios'][ULT], 2)}) e em cada modelo ({br(min(fg['medios']), 2)} no GPT e "
    f"{br(min(fm['medios']), 2)} no Gemini)." if ULT == min(range(6), key=lambda j: fg["medios"][j])
    == min(range(6), key=lambda j: fm["medios"][j]) else
    f"• <b>O {NOME_ESTR[ESTR[ULT]]} é o último</b> com os dois modelos juntos ({br(fj['medios'][ULT], 2)}).",
]
(sg, cg), (sm, cm) = ganho_reforco(dg), ganho_reforco(dm)
if sg > cg and sm > cm:
    sug.append(f"• <b>Persona e planejamento ajudam mais quando não há exemplos:</b> em média, somam "
               f"{br(sg, 1)} pontos de score efetivo sem exemplos e {br(cg, 1)} com exemplos no GPT; "
               f"{br(sm, 1)} e {br(cm, 1)} no Gemini. É uma observação descritiva.")
st(KeepTogether([P("Pode sugerir (tendência, ou resultado frágil)", "h2"),
                 caixa(sug, fundo=AMARELO, borda=OCRE, estilo="corpo")]))
st(KeepTogether([P("Não pode afirmar", "h2"), caixa([
    f"• <b>Qual é a melhor estratégia.</b> O {NOME_ESTR[ESTR[TOP]]} não se distingue do 2º, 3º e 4º "
    f"colocados ({', '.join(ESTR[v] for v in VIZINHOS)}; p ≥ {p3(TOP_P)} já sem correção).",
    f"• <b>Que a persona de especialista ou o planejamento melhoram o testbench.</b> Nenhuma "
    f"comparação com a versão base foi significativa (p corrigido ≥ {br(REF_HOLM_MIN, 2)}).",
    f"• <b>Que o efeito do exemplo vale para cada modelo isolado.</b> No "
    + " e no ".join(f"{CURTO[n]} (p = {p3(A['wil'][n][4])})" for n in (g, m2) if A["wil"][n][4] >= 0.05)
    + " ele não foi significativo."
    if any(A["wil"][n][4] >= 0.05 for n in (g, m2)) else
    "• <b>Que o efeito tem o mesmo tamanho nos dois modelos.</b>",
    "• <b>Que um modelo é melhor que o outro.</b> Os testes comparam estratégias dentro de cada "
    "modelo, não os modelos entre si. As diferenças entre GPT e Gemini (seção 6) são descritivas.",
], fundo=VERMELHO, borda=VERMELHO_BORDA, estilo="corpo"),
    fonte("“não significativo” indica evidência insuficiente, não ausência de efeito "
          "(WASSERSTEIN; LAZAR, 2016).")]))

# ---- 5 ----
st(P("5. Respostas diretas para o TCC", "h1"))
st(tabela(["Pergunta", "Resposta"], [
    ["A estratégia de prompt influencia a qualidade dos testbenches gerados por LLM?",
     "<b>Sim.</b> O componente com efeito comprovado é o uso de exemplos (few-shot)."],
    ["Qual estratégia usar?",
     f"<b>Uma com exemplos.</b> O {NOME_ESTR[ESTR[TOP]]} teve o melhor posto médio, mas não se "
     f"distingue das outras do topo com estes dados."],
    ["Persona de especialista e planejamento valem a pena?",
     "<b>Não há evidência estatística.</b> Se existe ganho, ele é secundário e aparece mais quando "
     "o prompt não tem exemplos."],
    ["Duas rodadas bastam?",
     f"<b>Ajudaram:</b> o Friedman passou de p = {p3(R1['fri']['juntos']['p'])} para "
     f"{p3(fj['p'])}. Mas o {CURTO[inst]} oscila muito entre rodadas; mais rodadas dariam "
     f"resultados mais firmes."],
    ["Basta o testbench “passar” para ser bom?",
     "<b>Não.</b> A análise usa mutantes mortos: um testbench pode passar e verificar pouco "
     "(ver seção 6)."],
], [78 * mm, 96 * mm]))

# ---- 6 ----
st(P("6. Números de apoio (descritivos)", "h1"))
st(P("Para a discussão. Somando as 2 rodadas: score efetivo = mutantes mortos ÷ 80 possíveis "
     "(10 circuitos × 4 × 2 rodadas), com “Não passou” valendo 0; aprovados = testbenches que "
     "passaram no circuito original, de 20."))
linhas = []
for e in ESTR:
    linhas.append([NOME_ESTR[e], f"{dg[e][0]}/20", f"{br(dg[e][1], 1)}%", f"{dm[e][0]}/20",
                   f"{br(dm[e][1], 1)}%"])
fam = {}
for m in MODELOS:
    d = DESC[m]
    fam[m] = [(sum(d[ESTR[j]][0] for j in f), sum(d[ESTR[j]][1] for j in f) / 3) for f in (ZS_FAM, FS_FAM)]
linhas.append(["<b>Família zero-shot</b>", f"<b>{fam[g][0][0]}/60</b>", f"<b>{br(fam[g][0][1], 1)}%</b>",
               f"<b>{fam[m2][0][0]}/60</b>", f"<b>{br(fam[m2][0][1], 1)}%</b>"])
linhas.append(["<b>Família few-shot</b>", f"<b>{fam[g][1][0]}/60</b>", f"<b>{br(fam[g][1][1], 1)}%</b>",
               f"<b>{fam[m2][1][0]}/60</b>", f"<b>{br(fam[m2][1][1], 1)}%</b>"])
t = tabela(["Estratégia", "GPT: aprovados", "GPT: score efetivo", "Gemini: aprovados",
            "Gemini: score efetivo"], linhas, [54 * mm, 28 * mm, 32 * mm, 28 * mm, 32 * mm])
t.setStyle(TableStyle([("BACKGROUND", (0, -2), (-1, -1), AMARELO)]))
st(t)
aprov = {m: sum(DESC[m][e][0] for e in ESTR) for m in MODELOS}
mortos = {m: EST[m]["tot"][0] + EST[m]["tot"][1] for m in MODELOS}
qual = {m: 100 * mortos[m] / (4 * aprov[m]) for m in MODELOS}
caso = max(((m, e) for m in MODELOS for e in ESTR),
           key=lambda me: 5 * DESC[me[0]][me[1]][0] - DESC[me[0]][me[1]][1])
st(Spacer(1, 6))
st(KeepTogether([
    P("Passar não é o mesmo que verificar bem", "h2"),
    P(f"O GPT teve {aprov[g]}/120 testbenches aprovados e o Gemini, {aprov[m2]}/120. Mas, entre os "
      f"aprovados, os do GPT mataram {br(qual[g], 0)}% dos mutantes e os do Gemini, "
      f"{br(qual[m2], 0)}%. O caso mais claro é o {NOME_ESTR[caso[1]]} do {CURTO[caso[0]]}: "
      f"{DESC[caso[0]][caso[1]][0]} de 20 aprovados, mas score efetivo de "
      f"{br(DESC[caso[0]][caso[1]][1], 1)}%. Ou seja, “passou” sozinho premiaria testbenches que "
      f"verificam pouco; por isso a conclusão se apoia nos mutantes mortos."),
    P("Esta comparação entre modelos é <b>descritiva</b>: não foi feito teste estatístico entre GPT e "
      "Gemini, e eles são de categorias diferentes (o Flash-Lite é a versão leve do Gemini).", "nota"),
]))

# ---- 7 ----
st(PageBreak())
st(P("7. Verificação de robustez: testbenches reenviados", "h1"))
st(P("Na 2ª rodada, algumas células foram avaliadas mais de uma vez. Quase sempre o reenvio "
     "corrigia um testbench colado na estratégia errada. Em <b>2 células</b>, porém, o reenvio usou "
     "um testbench novo e mudou o resultado, e a planilha ficou com o 2º: Exams/2012 q2fsm2, Planning "
     "Zero-shot, no GPT (Não passou → 4/4) e Conwaylife2_gemini, Planning Few-shot, no Gemini "
     "(0/4 → 4/4). A tabela refaz os testes com o <b>1º envio</b> dessas duas células:"))
l_top = next(l for l in A["pos"] if (l["a"], l["b"]) == (TOP, ULT))
l_top1 = next(l for l in A1E["pos"] if {l["a"], l["b"]} == {TOP, ULT})
st(tabela(["Teste", "Planilha (2º envio)", "1º envio", "Conclusão muda?"], [
    ["Friedman, juntos", p3(fj["p"]), p3(A1E["fri"]["juntos"]["p"]),
     "Não" if (fj["p"] < 0.05) == (A1E["fri"]["juntos"]["p"] < 0.05) else "<b>Sim</b>"],
    ["Wilcoxon família, juntos", p3(wj[4]), p3(A1E["wil"]["juntos"][4]),
     "Não" if (wj[4] < 0.05) == (A1E["wil"]["juntos"][4] < 0.05) else "<b>Sim</b>"],
    ["Fisher (GPT + Gemini)", p3(A["fisher"]), p3(A1E["fisher"]),
     "Não" if (A["fisher"] < 0.05) == (A1E["fisher"] < 0.05) else "<b>Sim</b>"],
    ["ZS × FS, juntos (p corrigido)", p3(ZSFS["holm"]), p3(A1E["par"][("ZS", "FS")]["holm"]),
     "Não" if (ZSFS["holm"] < 0.05) == (A1E["par"][("ZS", "FS")]["holm"] < 0.05) else "<b>Sim</b>"],
    [f"{ESTR[TOP]} × {ESTR[ULT]}, pós-teste (p corrigido)", p3(l_top["holm"]), p3(l_top1["holm"]),
     "Não" if (l_top["holm"] < 0.05) == (l_top1["holm"] < 0.05) else "<b>Sim</b>"],
], [64 * mm, 36 * mm, 30 * mm, 44 * mm]))
st(P("Valores: p-valor de cada teste, com a média das 2 rodadas.", "nota"))
st(P("As conclusões principais (as estratégias diferem; few-shot &gt; zero-shot) não dependem dessas "
     "duas células. O par do pós-teste é o resultado mais frágil, e por isso está em “pode "
     "sugerir”. Para o TCC, vale fixar a regra antes de escrever: <b>vale o primeiro testbench "
     "que o LLM gerou</b>, e um reenvio só é aceito para corrigir um erro de colagem."))

# ---- 8 ----
st(P("8. Limitações que acompanham a conclusão", "h1"))
for txt in [
    f"<b>Duas execuções por estratégia e circuito.</b> Melhor que uma, mas o {CURTO[inst]} mudou "
    f"muito de uma rodada para a outra; mais rodadas dariam médias mais estáveis (ARCURI; BRIAND, "
    f"2011).",
    "<b>Quatro mutantes por circuito.</b> A nota de cada rodada só varia de 25 em 25%, com muitos "
    "empates; a média das rodadas ajuda, mas a resolução continua baixa.",
    f"<b>Dez circuitos por modelo.</b> Para a diferença crítica do pós-teste ficar menor que a "
    f"distância entre o 1º e o 2º colocados ({br(DELTA, 2)} no posto médio), seriam precisos uns "
    f"{math.ceil(N_PRECISO / 2)} circuitos por modelo, supondo que as distâncias continuem as mesmas "
    f"(estimativa pela fórmula de Nemenyi; DEMŠAR, 2006).",
    "<b>Agrupamento dos modelos.</b> Os mesmos circuitos aparecem nos dois modelos; os 20 pares não "
    "são totalmente independentes. A combinação de Fisher, que não depende disso, chega à mesma "
    "conclusão.",
    "<b>Reenvios na 2ª rodada</b> (seção 7): não mudam as conclusões principais.",
    "<b>EAS-28 fora da comparação</b> (sem dados no Gemini; no GPT, todas as estratégias empataram "
    "com 4/4).",
    "<b>Mutantes gerados por regex</b>, sem parser de Verilog, e cobertura com tetos estruturais em "
    "alguns circuitos (ex.: Cordic em 50% de linha).",
]:
    st(item(txt))

st(P("9. Trabalhos futuros", "h1"))
for txt in [
    "Mais rodadas por célula (3 a 5) e mais circuitos, para separar as estratégias do topo.",
    "Usar 8 a 10 mutantes por circuito, para dar mais resolução aos testes.",
    "Comparar os modelos com um teste próprio, em modelos da mesma categoria.",
    "Incluir no ICV um componente de complexidade temporal (contadores longos, protocolos).",
]:
    st(item(txt))

# ---- 10 ----
st(PageBreak())
st(P("10. Texto sugerido para o TCC", "h1"))
st(P("Discussão dos resultados", "h2"))
st(caixa([
    f"Cada estratégia foi executada em duas rodadas, e a análise usou a média de mutantes mortos "
    f"das duas. Com os dois modelos agrupados, o teste de Friedman indicou que as seis estratégias "
    f"não são equivalentes (χ<super>2</super>(5) = {br(fj['Q'], 2)}; p = {p3(fj['p'])}; W de Kendall "
    f"= {br(fj['W'], 2)}), embora a diferença não tenha sido significativa em cada modelo isolado "
    f"(GPT: p = {p3(fg['p'])}; Gemini: p = {p3(fm['p'])}). O contraste planejado entre as famílias "
    f"few-shot e zero-shot, avaliado pelo teste de Wilcoxon pareado, foi significativo com os dois "
    f"modelos agrupados (T = {br(wj[3])}; p = {p3(wj[4])}), resultado confirmado pela combinação dos "
    f"p-valores de cada modelo pelo método de Fisher (p = {p3(A['fisher'])}). Por modelo, o efeito "
    f"foi {EFEITO} (GPT: p = {p3(wg[4])}; Gemini: p = {p3(wm[4])})"
    + (f"; no {' e no '.join(MUDOU)}, o sentido do efeito mudou entre as rodadas" if MUDOU else "")
    + f". No pós-teste (Nemenyi e Wilcoxon com correção de Holm), apenas o "
    f"{NOME_ESTR[ESTR[TOP]]} diferiu do {NOME_ESTR[ESTR[ULT]]}; as estratégias com melhor desempenho "
    f"ficaram próximas demais para serem separadas. A persona de especialista e o planejamento não "
    f"apresentaram efeito estatisticamente comprovado (p corrigido ≥ {br(REF_HOLM_MIN, 2)}), embora "
    f"os dados descritivos sugiram ganho maior quando o prompt não contém exemplos. Por fim, as duas "
    f"rodadas divergiram em muitas células, o que reforça a necessidade de repetir as execuções ao "
    f"avaliar LLMs.",
], fundo=colors.white, estilo="corpo"))
st(P("Conclusão", "h2"))
st(caixa([
    "Este trabalho avaliou seis estratégias de prompt na geração de testbenches por LLM, medindo a "
    "qualidade da verificação por meio de teste de mutação, em duas rodadas de execução. Conclui-se "
    "que a estratégia de prompt influencia a qualidade dos testbenches e que o componente com efeito "
    "comprovado é o uso de exemplos (few-shot): testbenches gerados com exemplos detectaram "
    "significativamente mais defeitos quando os dois modelos avaliados foram analisados em conjunto. "
    "Não foi possível eleger uma única estratégia superior: as variantes com exemplos ficaram "
    "próximas entre si, e persona de especialista e planejamento não mostraram ganho comprovado. Os "
    "resultados também mostram que avaliar um testbench apenas por sua aprovação é insuficiente, e "
    "que a mesma estratégia pode produzir resultados bem diferentes entre execuções. Como "
    "limitações, destacam-se o número reduzido de rodadas, de mutantes e de circuitos; trabalhos "
    "futuros devem ampliar esses três fatores para separar as estratégias de melhor desempenho.",
], fundo=colors.white, estilo="corpo"))

secao_referencias(story, ["ARCURI", "DEMSAR", "FISHER", "FRIEDMAN", "HOLM", "SIEGEL", "WASSERSTEIN",
                          "WILCOXON"])

OUT = saida("conclusao_estatistica.pdf")
construir(OUT, story, TITULO)
print("Friedman", {k: (round(v["Q"], 4), round(v["p"], 4)) for k, v in A["fri"].items()})
print("Wilcoxon", {k: round(v[4], 4) for k, v in A["wil"].items()}, "Fisher", round(A["fisher"], 4))
print("pos-teste sig", [(ESTR[l["a"]], ESTR[l["b"]], round(l["holm"], 4)) for l in POS_SIG],
      "| TOP", ESTR[TOP], "TOP_P", round(TOP_P, 4), "| delta", round(DELTA, 3), "n", round(N_PRECISO, 1))
print("1o envio: Friedman", round(A1E["fri"]["juntos"]["p"], 4), "Wilcoxon", round(A1E["wil"]["juntos"][4], 4),
      "Fisher", round(A1E["fisher"], 4), "top", round(l_top1["holm"], 4))
print("estabilidade", EST, "| aprovados", aprov, "qualidade", {k: round(v, 1) for k, v in qual.items()},
      "| caso", caso)
print("reforco", ganho_reforco(dg), ganho_reforco(dm), "| excecoes", nao)
print("PDF:", OUT)
