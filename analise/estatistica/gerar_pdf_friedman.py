"""Gera o PDF "Teste de Friedman - passo a passo" a partir da linha "Mutantes" da planilha.

O valor analisado e a media das 2 rodadas em cada celula. Todos os numeros do PDF sao calculados
aqui (nada digitado a mao) e conferidos contra scipy.stats.friedmanchisquare antes de gerar o
arquivo. Inclui o pos-teste (Nemenyi e Wilcoxon com Holm) para o caso em que o Friedman da
significativo.
Uso: python gerar_pdf_friedman.py [saida.pdf]   (padrao: documentacao/friedman_passo_a_passo.pdf)
"""
import itertools
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer, TableStyle
from scipy.stats import chi2, friedmanchisquare

from pdf_comum import (AMARELO, CIRCUITOS, CURTO, ESTR, MODELOS, NOME_ESTR, OCRE, Q_NEMENYI_6,
                       VERDE, VERDE_BORDA, W7, W8, abrev, br, caixa, celulas, construir, fonte,
                       holm, item, nemenyi_cd, P, postos, saida, secao_referencias, tabela,
                       valores, wilc)

TITULO = "Teste de Friedman — passo a passo"
EXTENSO = {2: "Os dois", 3: "Os três", 4: "Os quatro", 5: "Os cinco", 6: "Os seis"}


def chi2_sf_df5(x):
    """P(qui-quadrado com 5 g.l. >= x), forma fechada para g.l. impar."""
    s = math.sqrt(x)
    return math.erfc(s / math.sqrt(2)) + math.sqrt(2 / math.pi) * math.exp(-x / 2) * (s + s ** 3 / 3)


def calcular(vals):
    n, k = len(vals), len(vals[0])
    rk = [postos(v) for v in vals]
    R = [sum(rk[i][j] for i in range(n)) for j in range(k)]
    soma_quad = sum(x * x for x in R)
    q0 = 12 / (n * k * (k + 1)) * soma_quad - 3 * n * (k + 1)
    grupos = []      # por linha: [(valor, t, t^3 - t), ...] so empates (t >= 2)
    for v in vals:
        cont = Counter(v)
        grupos.append([(val, t, t ** 3 - t) for val, t in sorted(cont.items()) if t >= 2])
    T = sum(g[2] for linha in grupos for g in linha)
    C = 1 - T / (n * (k ** 3 - k))
    Q = q0 / C
    p = chi2_sf_df5(Q)
    # conferencia independente
    sp = friedmanchisquare(*[[vals[i][j] for i in range(n)] for j in range(k)])
    assert abs(sp.statistic - Q) < 1e-9 and abs(sp.pvalue - p) < 1e-9, (sp, Q, p)
    assert all(abs(sum(l) - k * (k + 1) / 2) < 1e-9 for l in rk)
    assert abs(sum(R) - n * k * (k + 1) / 2) < 1e-9
    return dict(valores=vals, postos=rk, R=R, medias=[x / n for x in R], soma_quad=soma_quad,
                q0=q0, grupos=grupos, T=T, C=C, Q=Q, p=p, n=n, k=k, W=Q / (n * (k - 1)))


def posteste(res):
    """Nemenyi (diferenca de postos medios > CD) e Wilcoxon exato par a par com Holm."""
    vals, med, n = res["valores"], res["medias"], res["n"]
    cd = nemenyi_cd(6, n)
    linhas = []
    for i, j in itertools.combinations(range(6), 2):
        a, b = (i, j) if med[i] >= med[j] else (j, i)          # a = melhor posto medio
        g, pe, e, T, p = wilc([l[b] for l in vals], [l[a] for l in vals])
        linhas.append(dict(a=a, b=b, dif=med[a] - med[b], ganha=g, perde=pe, empata=e, T=T, p=p))
    for l, ph in zip(linhas, holm([l["p"] for l in linhas])):
        l["holm"] = ph
        l["nem"] = l["dif"] > cd
    linhas.sort(key=lambda l: (l["p"], -l["dif"]))
    return cd, linhas


def grupos_posicoes(vals):
    """[(valor, [posicoes 1..k que ele ocupa na fila crescente]), ...]"""
    ordem = sorted(range(len(vals)), key=lambda i: vals[i])
    out, i = [], 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and vals[ordem[j + 1]] == vals[ordem[i]]:
            j += 1
        out.append((vals[ordem[i]], list(range(i + 1, j + 2))))
        i = j + 1
    return out


def lista(xs):
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " e " + xs[-1]


def nomes(idx):
    return lista([NOME_ESTR[ESTR[j]] for j in idx])


RES = {m: calcular(valores(m)) for m in MODELOS}
JUNTOS = calcular(valores(MODELOS[0]) + valores(MODELOS[1]))
CASOS = [(MODELOS[0], RES[MODELOS[0]]), (MODELOS[1], RES[MODELOS[1]]),
         ("Os dois juntos", JUNTOS)]
POR_RODADA = {r: {m: calcular(valores(m, r)) for m in MODELOS} for r in (1, 2)}
for r in (1, 2):
    POR_RODADA[r]["juntos"] = calcular(valores(MODELOS[0], r) + valores(MODELOS[1], r))
# a 1a rodada sozinha tem que dar os mesmos numeros do PDF anterior (so com ela)
assert (round(POR_RODADA[1][MODELOS[0]]["Q"], 2), round(POR_RODADA[1][MODELOS[1]]["Q"], 2),
        round(POR_RODADA[1]["juntos"]["Q"], 2)) == (6.12, 5.31, 10.01)
CRITICO = chi2.ppf(0.95, 5)
SIG = [(nome, r) for nome, r in CASOS if r["p"] < 0.05]
POS = {nome: posteste(r) for nome, r in SIG}
gpt, gem = RES[MODELOS[0]], RES[MODELOS[1]]
ULT = {nome: [j for j in range(6) if r["medias"][j] == min(r["medias"])] for nome, r in CASOS}
PRI = {nome: [j for j in range(6) if r["medias"][j] == max(r["medias"])] for nome, r in CASOS}


def sig_txt(p):
    return "Sim (p < 0,05)" if p < 0.05 else "Não (p ≥ 0,05)"


story = []
st = story.append

st(P(TITULO, "titulo"))
st(P("Comparação das 6 estratégias de prompt nos testbenches gerados pelo GPT-5.6 Luna e pelo "
     "Gemini 3.5 Flash-Lite — média das 2 rodadas", "sub"))
st(Spacer(1, 10))

# ---- resumo ----
st(caixa([
    "<b>Resultado em uma linha:</b> "
    + (f"com os dois modelos juntos, as seis estratégias <b>diferem significativamente</b> "
       f"(p = {br(JUNTOS['p'], 3)}); " if JUNTOS["p"] < 0.05 else
       "nem com os dois modelos juntos a diferença é significativa; ")
    + "em cada modelo isolado, a diferença "
    + ("não é significativa. " if gpt["p"] >= 0.05 and gem["p"] >= 0.05 else "varia. ")
    + f"O {nomes(ULT['Os dois juntos'])} ficou em último. No pós-teste, só "
    + (lista([f"{NOME_ESTR[ESTR[l['a']]]} × {NOME_ESTR[ESTR[l['b']]]}"
              for l in POS["Os dois juntos"][1] if l["holm"] < 0.05]) or "nenhum par")
    + " difere: não dá para eleger uma única melhor.",
    f"<b>GPT-5.6 Luna:</b> χ<super>2</super>(5) = {br(gpt['Q'], 2)}; p = {br(gpt['p'], 3)}",
    f"<b>Gemini 3.5 Flash-Lite:</b> χ<super>2</super>(5) = {br(gem['Q'], 2)}; p = {br(gem['p'], 3)}",
    f"<b>Os dois juntos:</b> χ<super>2</super>(5) = {br(JUNTOS['Q'], 2)}; p = {br(JUNTOS['p'], 3)}",
], fundo=VERDE, borda=VERDE_BORDA))

st(P("1. O que o teste responde", "h1"))
st(P("O teste de Friedman responde a uma pergunta: <b>as seis estratégias de prompt produzem "
     "testbenches de qualidade diferente, ou as diferenças observadas poderiam ser obra do "
     "acaso?</b>"))
st(P("Pense num campeonato com <b>10 corridas</b> (os circuitos) e <b>6 corredores</b> (as "
     "estratégias). Em cada corrida, cada estratégia recebe uma posição, de 1 (pior) a 6 "
     "(melhor). No fim, calcula-se a posição média de cada uma. O teste verifica se essas "
     "médias estão afastadas o bastante para não serem explicadas por sorte."))
st(P("O cálculo é feito <b>para cada modelo</b> e também com os <b>dois modelos juntos</b> (20 "
     "corridas), sempre comparando as estratégias entre si. O teste <b>não compara</b> o GPT com "
     "o Gemini."))
st(P("<b>Duas rodadas.</b> Cada estratégia foi executada duas vezes em cada circuito: na 2ª rodada "
     "os testbenches foram gerados de novo, com o mesmo RTL e, portanto, os mesmos 4 mutantes. "
     "Como o LLM é aleatório, a mesma estratégia pode ir bem numa rodada e mal na outra; por isso o "
     "valor analisado é a <b>média das duas rodadas</b> em cada célula. As rodadas são repetições "
     "da mesma medida, e não circuitos novos: o número de corridas continua 10 por modelo."))
st(fonte("teste proposto por Friedman (1937); procedimento descrito em Siegel e Castellan Jr. "
         "(2006) como “análise de variância de dois fatores de Friedman por postos”. Uso para "
         "comparar vários métodos sobre vários casos: Demšar (2006). Repetir as execuções de "
         "algoritmos aleatórios: Arcuri e Briand (2011)."))
st(P("Notação usada no documento", "h2"))
st(tabela(["Símbolo", "Significado", "Valor"], [
    ["n", "número de circuitos (blocos)", "10 por modelo; 20 juntos"],
    ["k", "número de estratégias (tratamentos)", "6"],
    ["R<sub>j</sub>", "soma dos postos da estratégia j nos n circuitos", "calculado no passo 2"],
    ["t", "tamanho de um grupo de empate dentro de um circuito", "calculado no passo 4"],
], [22 * mm, 102 * mm, 50 * mm]))
st(P("Abreviações das estratégias: ZS = Zero-shot · FS = Few-shot · EspZS = Especialista "
     "Zero-shot · EspFS = Especialista Few-shot · PlnZS = Planning Zero-shot · PlnFS = "
     "Planning Few-shot.", "nota"))

# ---- passo 0: dados ----
st(P("2. Passo 0 — Converter a planilha em números e tirar a média das rodadas", "h1"))
st(P("Para cada circuito, usa-se a linha <b>“Mutantes”</b> da planilha, nas duas rodadas. Cada "
     "célula vira o número de mutantes mortos:"))
st(item("“4/4” vira <b>4</b>, “3/4” vira <b>3</b>, e assim por diante;"))
st(item("“Não passou” e “Timeout” viram <b>0</b>: um testbench que reprova o circuito "
        "original não detecta defeito nenhum de forma válida;"))
st(item("o valor usado é a <b>média das duas rodadas</b>: (rodada 1 + rodada 2) ÷ 2. Por isso "
        "aparecem meios (0,5; 1,5; ...)."))
st(fonte("decisão metodológica deste trabalho (não é uma fórmula da literatura): é o mesmo "
         "critério do “score de mutação efetivo” usado na análise da planilha; a média das "
         "repetições segue a recomendação de repetir execuções de Arcuri e Briand (2011)."))
st(P("O EAS-28 fica de fora porque não tem resultados no Gemini; assim os dois modelos são "
     "comparados nos mesmos 10 circuitos.", "nota"))
for m in MODELOS:
    c1, c2 = celulas(m, 1), celulas(m, 2)
    linhas = []
    for i, nome in enumerate(CIRCUITOS):
        linhas.append([nome] + [f"{abrev(a)} · {abrev(b)}<br/><b>{br(v)}</b>"
                                for a, b, v in zip(c1[i], c2[i], RES[m]["valores"][i])])
    st(KeepTogether([P(f"Tabela 1{'a' if CURTO[m] == 'GPT' else 'b'} — {m}: rodada 1 · rodada 2 "
                       f"(em cima) e média usada (em negrito)", "legenda"),
                     tabela(["Circuito"] + ESTR, linhas, W7)]))
st(P("NP = Não passou; TO = Timeout.", "nota"))

# ---- passo 1: postos ----
st(PageBreak())
st(P("3. Passo 1 — Dar postos dentro de cada circuito", "h1"))
st(P("Em <b>cada circuito, separadamente</b>, as seis estratégias são ordenadas do menor para o "
     "maior número médio de mutantes mortos. O menor recebe posto 1 e o maior recebe posto 6."))
st(P("<b>Regra do empate:</b> estratégias com o mesmo valor ocupam várias posições da fila, e "
     "nenhuma delas foi pior que a outra. Por isso todas recebem a <b>média das posições que "
     "ocupam</b> (o “posto médio”)."))
st(fonte("ordenação por postos dentro de cada bloco e posto médio para empates: Friedman (1937); "
         "Siegel e Castellan Jr. (2006)."))

EX_M, EX_I = MODELOS[0], 1
ex_val = RES[EX_M]["valores"][EX_I]
ex_rk = RES[EX_M]["postos"][EX_I]
ordem = sorted(range(6), key=lambda i: ex_val[i])
st(P(f"Exemplo: {CIRCUITOS[EX_I]} no {CURTO[EX_M]}", "h2"))
st(P("Valores (média das 2 rodadas): " + ", ".join(f"{e} = {br(v)}" for e, v in zip(ESTR, ex_val))
     + ". Colocando em fila, do menor para o maior:"))
st(tabela(["", "1ª", "2ª", "3ª", "4ª", "5ª", "6ª"], [
    ["Valor"] + [br(ex_val[i]) for i in ordem],
    ["Estratégia"] + [ESTR[i] for i in ordem],
    ["Posto final"] + [f"<b>{br(ex_rk[i])}</b>" for i in ordem],
], W7, destacar_ultima=True))
st(Spacer(1, 4))
expl = []
for v, ps in grupos_posicoes(ex_val):
    if len(ps) == 1:
        expl.append(f"O <b>{br(v)}</b> fica sozinho na posição {ps[0]}  →  posto <b>{ps[0]}</b>")
    else:
        expl.append(f"{EXTENSO[len(ps)]} <b>{br(v)}</b> ocupam as posições {lista(ps)}  →  "
                    f"({' + '.join(map(str, ps))}) ÷ {len(ps)} = <b>{br(sum(ps) / len(ps))}</b> "
                    f"para cada um")
st(caixa(expl))
st(P("<b>Conferência:</b> em qualquer circuito, os seis postos somam sempre "
     "1 + 2 + 3 + 4 + 5 + 6 = k × (k + 1) ÷ 2 = <b>21</b>. No exemplo: "
     + " + ".join(br(x) for x in ex_rk) + " = 21."))
st(P("As tabelas abaixo mostram, em cada célula, o <b>valor → posto</b>. A última coluna confere "
     "que cada linha soma 21."))
for m in MODELOS:
    r = RES[m]
    linhas = []
    for nome, v, rk in zip(CIRCUITOS, r["valores"], r["postos"]):
        linhas.append([nome] + [f"{br(a)} → <b>{br(b)}</b>" for a, b in zip(v, rk)] + [br(sum(rk))])
    linhas.append(["<b>Soma (R<sub>j</sub>)</b>"] + [f"<b>{br(x)}</b>" for x in r["R"]]
                  + [f"<b>{br(sum(r['R']))}</b>"])
    st(KeepTogether([P(f"Tabela 2{'a' if CURTO[m] == 'GPT' else 'b'} — {m}: valor → posto",
                       "legenda"),
                     tabela(["Circuito"] + ESTR + ["Soma da linha"], linhas, W8,
                            destacar_ultima=True)]))

# ---- passo 2: posto medio ----
st(P("4. Passo 2 — Somar os postos e calcular o posto médio", "h1"))
st(P("Soma-se a coluna de cada estratégia (R<sub>j</sub>, última linha das tabelas 2a e 2b) e "
     "divide-se pelo número de circuitos. O resultado é o <b>posto médio</b>: quanto maior, melhor "
     "a estratégia se saiu na comparação com as outras. Com os dois modelos juntos, R<sub>j</sub> "
     "é a soma das duas tabelas e n = 20."))
st(caixa("<b>Posto médio da estratégia j = R<sub>j</sub> ÷ n</b>"))
st(fonte("Demšar (2006), que apresenta o teste de Friedman a partir dos postos médios."))
linhas = []
for j, e in enumerate(ESTR):
    lin = [NOME_ESTR[e]]
    for _, r in CASOS:
        lin += [br(r["R"][j]), f"<b>{br(r['medias'][j], 2)}</b>"]
    linhas.append(lin)
linhas.append(["<b>Total</b>"] + sum([[f"<b>{br(sum(r['R']))}</b>", ""] for _, r in CASOS], []))
st(tabela(["Estratégia", "GPT: R<sub>j</sub>", "GPT: posto médio", "Gemini: R<sub>j</sub>",
           "Gemini: posto médio", "Juntos: R<sub>j</sub>", "Juntos: posto médio"],
          linhas, [40 * mm] + [22.3 * mm] * 6, destacar_ultima=True))
st(Spacer(1, 4))
st(P("<b>Conferência:</b> a soma de todos os postos tem que ser n × k × (k + 1) ÷ 2: "
     "10 × 6 × 7 ÷ 2 = <b>210</b> em cada modelo e 20 × 6 × 7 ÷ 2 = <b>420</b> juntos, como na "
     "linha Total. Se nenhuma estratégia fosse melhor, todos os postos médios ficariam perto de "
     "(k + 1) ÷ 2 = <b>3,5</b>."))

# ---- passo 3: Q sem correcao ----
st(PageBreak())
st(P("5. Passo 3 — Calcular a estatística Q (sem correção)", "h1"))
st(P("A estatística de Friedman mede o quanto as somas de postos se afastam do que se "
     "esperaria se todas as estratégias fossem iguais:"))
st(caixa("<b>Q<sub>0</sub> = [ 12 ÷ (n · k · (k + 1)) ] × ΣR<sub>j</sub><super>2</super>  −  "
         "3 · n · (k + 1)</b>"))
st(fonte("Friedman (1937); Siegel e Castellan Jr. (2006). A mesma estatística escrita com os "
         "postos médios aparece em Demšar (2006)."))
st(P("Com k = 6: para cada modelo (n = 10), 12 ÷ (10 × 6 × 7) = <b>12 ÷ 420</b> e "
     "3 × 10 × 7 = <b>210</b>; juntos (n = 20), <b>12 ÷ 840</b> e <b>420</b>."))


def num(x):
    return br(x, 2 if x % 1 else 0)


for nome, r in CASOS:
    den, sub = r["n"] * 42, 3 * r["n"] * 7
    quad = " + ".join(f"{br(x)}<super>2</super>" for x in r["R"])
    termos = " + ".join(num(x * x) for x in r["R"])
    sq = num(r["soma_quad"])
    st(KeepTogether([P(nome, "h2"), caixa([
        f"ΣR<sub>j</sub><super>2</super> = {quad}",
        f"ΣR<sub>j</sub><super>2</super> = {termos} = <b>{sq}</b>",
        f"Q<sub>0</sub> = 12 ÷ {den} × {sq} − {sub} = "
        f"{br(12 / den * r['soma_quad'], 4)} − {sub} = <b>{br(r['q0'], 4)}</b>",
    ])]))

# ---- passo 4: empates ----
st(P("6. Passo 4 — Corrigir os empates", "h1"))
st(P("Como há muitos empates (várias estratégias com a mesma média no mesmo circuito), o "
     "Q<sub>0</sub> é corrigido. Para cada grupo de valores iguais dentro de um circuito, calcula-se "
     "<b>t<super>3</super> − t</b>, onde t é quantas estratégias empataram naquele valor. "
     "Valores que aparecem uma só vez não contam (1<super>3</super> − 1 = 0)."))
st(caixa(["<b>C = 1 − ΣT ÷ (n · (k<super>3</super> − k))</b>     com     n · (k<super>3</super> − k) "
          "= 10 × (216 − 6) = <b>2.100</b> (por modelo) ou 20 × 210 = <b>4.200</b> (juntos)",
          "<b>Q = Q<sub>0</sub> ÷ C</b>"]))
st(fonte("correção para empates do teste de Friedman em Hollander, Wolfe e Chicken (2014); é a "
         "mesma correção aplicada pela função <i>friedmanchisquare</i> do SciPy (VIRTANEN et al., "
         "2020), usada para conferir os números deste documento."))
for m in MODELOS:
    r = RES[m]
    linhas = []
    for nome, gr in zip(CIRCUITOS, r["grupos"]):
        desc = "; ".join(f"valor {br(val)}: t = {t} → {t}<super>3</super> − {t} = {tt}"
                         for val, t, tt in gr)
        linhas.append([nome, desc or "sem empates", str(sum(g[2] for g in gr))])
    linhas.append(["<b>Total (ΣT)</b>", "", f"<b>{r['T']}</b>"])
    st(KeepTogether([
        P(f"Tabela 3{'a' if CURTO[m] == 'GPT' else 'b'} — {m}: empates por circuito", "legenda"),
        tabela(["Circuito", "Grupos de empate", "Σ(t<super>3</super> − t)"], linhas,
               [34 * mm, 112 * mm, 28 * mm], destacar_ultima=True),
        Spacer(1, 4),
        caixa([f"C = 1 − {r['T']} ÷ 2.100 = 1 − {br(r['T'] / 2100, 4)} = <b>{br(r['C'], 4)}</b>",
               f"Q = {br(r['q0'], 4)} ÷ {br(r['C'], 4)} = <b>{br(r['Q'], 2)}</b>"]),
    ]))
assert JUNTOS["T"] == gpt["T"] + gem["T"]
st(KeepTogether([P("Os dois juntos", "h2"), caixa([
    f"Os 20 circuitos são os das tabelas 3a e 3b: ΣT = {gpt['T']} + {gem['T']} = <b>{JUNTOS['T']}</b>",
    f"C = 1 − {JUNTOS['T']} ÷ 4.200 = 1 − {br(JUNTOS['T'] / 4200, 4)} = <b>{br(JUNTOS['C'], 4)}</b>",
    f"Q = {br(JUNTOS['q0'], 4)} ÷ {br(JUNTOS['C'], 4)} = <b>{br(JUNTOS['Q'], 2)}</b>"])]))

# ---- passo 5: p-valor ----
st(PageBreak())
st(P("7. Passo 5 — Calcular o p-valor", "h1"))
st(P("O Q é comparado com a distribuição <b>qui-quadrado (χ<super>2</super>)</b> com "
     "<b>k − 1 = 5 graus de liberdade</b>. O p-valor é a chance de obter um Q desse tamanho "
     "ou maior <b>se as seis estratégias fossem todas iguais</b>."))
st(caixa("<b>p = P( χ<super>2</super> com k − 1 graus de liberdade ≥ Q )</b>"))
st(fonte("aproximação qui-quadrado com k − 1 graus de liberdade: Friedman (1937); Siegel e "
         "Castellan Jr. (2006), que também trazem a tabela de valores críticos. Função do Excel: "
         "Microsoft (2026)."))
st(caixa(["No Excel em português:"]
         + [f"=DIST.QUIQUA.CD({br(r['Q'], 2)}; 5)   →   {br(r['p'], 3)}   ({nome})"
            for nome, r in CASOS], estilo="codigo"))
st(P(f"<b>Referências para ler o Q:</b> se as estratégias fossem iguais, o Q ficaria em torno "
     f"de <b>5</b> (o valor médio de um χ<super>2</super> é igual ao seu número de graus de "
     f"liberdade). Para ser significativo a 5%, o Q precisaria passar de <b>{br(CRITICO, 2)}</b> "
     f"(valor crítico do χ<super>2</super> com 5 graus de liberdade)."))
st(tabela(["Caso", "Q = χ<super>2</super>(5)", "Valor crítico (5%)", "p-valor", "Significativo?"],
          [[nome, br(r["Q"], 2), br(CRITICO, 2), br(r["p"], 3), sig_txt(r["p"])]
           for nome, r in CASOS], [44 * mm, 30 * mm, 34 * mm, 26 * mm, 40 * mm]))
st(P("Tamanho do efeito: W de Kendall", "h2"))
st(P("O p-valor diz se a diferença pode ser acaso; o <b>W de Kendall</b> diz o quanto os circuitos "
     "concordam na ordem das estratégias. Vai de 0 (cada circuito ordena de um jeito) a 1 (todos "
     "os circuitos dão exatamente a mesma ordem)."))
st(caixa(["<b>W = Q ÷ (n · (k − 1))</b>"] + [
    f"{CURTO.get(nome, 'Juntos')}: W = {br(r['Q'], 2)} ÷ ({r['n']} × 5) = <b>{br(r['W'], 3)}</b>"
    for nome, r in CASOS]))
st(fonte("coeficiente de concordância de Kendall e sua relação com a estatística de Friedman: "
         "Siegel e Castellan Jr. (2006)."))

# ---- resultado ----
st(P("8. Resultado final", "h1"))
linhas = []
for j, e in enumerate(ESTR):
    linhas.append([NOME_ESTR[e]] + [br(r["medias"][j], 2) for _, r in CASOS])
linhas.append(["<b>χ<super>2</super>(5)</b>"] + [f"<b>{br(r['Q'], 2)}</b>" for _, r in CASOS])
linhas.append(["<b>p-valor</b>"] + [f"<b>{br(r['p'], 3)}</b>" for _, r in CASOS])
linhas.append(["<b>W de Kendall</b>"] + [f"<b>{br(r['W'], 3)}</b>" for _, r in CASOS])
t = tabela(["Estratégia", "GPT-5.6 Luna<br/>(posto médio)", "Gemini 3.5 Flash-Lite<br/>(posto médio)",
            "Os dois juntos<br/>(posto médio)"], linhas, [56 * mm, 39 * mm, 40 * mm, 39 * mm])
t.setStyle(TableStyle([("BACKGROUND", (0, -3), (-1, -1), AMARELO)]))
st(t)
st(P("Posto médio: quanto maior, melhor. Valores calculados com a média das 2 rodadas. Fonte: "
     "elaborado pelo autor a partir da planilha do experimento.", "nota"))

st(KeepTogether([
    P("Uma rodada × duas rodadas", "h2"),
    tabela(["Caso", "Só a rodada 1", "Só a rodada 2", "Média das 2 rodadas"], [
        [nome, f"p = {br(POR_RODADA[1][ch]['p'], 3)}", f"p = {br(POR_RODADA[2][ch]['p'], 3)}",
         f"<b>p = {br(r['p'], 3)}</b>"]
        for (nome, r), ch in zip(CASOS, MODELOS + ["juntos"])], [56 * mm, 39 * mm, 40 * mm, 39 * mm]),
    P("A média das rodadas reduz o ruído de cada execução do LLM: com os dois modelos juntos, o p "
      f"cai de {br(POR_RODADA[1]['juntos']['p'], 3)} (só a rodada 1) para {br(JUNTOS['p'], 3)}.",
      "nota")]))


def ponta(qual, f):
    """'o X ficou em ... nos dois modelos (a no GPT e b no Gemini)' ou um por modelo."""
    a, b = qual[MODELOS[0]], qual[MODELOS[1]]
    va, vb = br(f(gpt["medias"]), 2), br(f(gem["medias"]), 2)
    if a == b:
        return f"o {nomes(a)} nos dois modelos ({va} no GPT e {vb} no Gemini)"
    return f"o {nomes(a)} no GPT ({va}) e o {nomes(b)} no Gemini ({vb})"


bloco = [P("Como interpretar", "h2")]
bloco.append(item(
    f"<b>A ordem:</b> em último ficou {ponta(ULT, min)}. Em primeiro ficou {ponta(PRI, max)}"
    + (": a melhor muda de um modelo para o outro." if PRI[MODELOS[0]] != PRI[MODELOS[1]] else ".")))
bloco.append(item(
    f"<b>O veredito:</b> com os dois modelos juntos, p = {br(JUNTOS['p'], 3)}"
    + (" &lt; 0,05: <b>as estratégias não são todas iguais</b>." if JUNTOS["p"] < 0.05 else
       " ≥ 0,05: não dá para afirmar que as estratégias diferem.")
    + f" Em cada modelo isolado, p = {br(gpt['p'], 3)} (GPT) e {br(gem['p'], 3)} (Gemini)"
    + (": ainda acima de 0,05, então a afirmação vale para os dois modelos juntos, não para cada "
       "um." if gpt["p"] >= 0.05 and gem["p"] >= 0.05 else ".")))
bloco.append(item(
    f"<b>O tamanho:</b> W = {br(JUNTOS['W'], 3)} juntos. A concordância entre os circuitos é baixa: "
    f"a ordem das estratégias muda bastante de um circuito para outro, e a diferença existe, mas "
    f"é pequena perto dessa variação."))
bloco.append(item(
    "<b>O que o Friedman não diz:</b> ele só diz que <b>alguma</b> estratégia difere de alguma "
    "outra. Quais são, quem diz é o pós-teste da próxima seção."))
st(KeepTogether(bloco))

# ---- pos-teste ----
st(PageBreak())
st(P("9. Pós-teste — quais estratégias diferem", "h1"))
st(P("Quando o Friedman dá significativo, compara-se cada par de estratégias. Com 6 estratégias "
     "são <b>15 pares</b>, e fazer 15 testes aumenta a chance de achar uma diferença por acaso. Por "
     "isso os dois métodos abaixo controlam esse risco. O pós-teste só se aplica onde o Friedman "
     "deu significativo: "
     + (lista([nome.lower() if nome.startswith("Os") else f"no {nome}" for nome, _ in SIG])
        if SIG else "em nenhum caso") + "."))
st(fonte("pós-teste depois do Friedman e diferença crítica de Nemenyi: Demšar (2006); correção de "
         "Holm: Holm (1979); teste de Wilcoxon pareado: Wilcoxon (1945)."))
st(P("Método 1 — Nemenyi (diferença crítica)", "h2"))
st(P("Duas estratégias diferem se os seus postos médios estiverem afastados mais do que a "
     "<b>diferença crítica (DC)</b>:"))
for nome, r in SIG:
    cd, _ = POS[nome]
    st(caixa([f"<b>DC = q<sub>α</sub> × √( k(k + 1) ÷ (6n) )</b>     com q<sub>0,05</sub> = "
              f"{br(Q_NEMENYI_6, 3)} para k = 6",
              f"{nome}: DC = {br(Q_NEMENYI_6, 3)} × √( 6 × 7 ÷ (6 × {r['n']}) ) = "
              f"{br(Q_NEMENYI_6, 3)} × {br(math.sqrt(42 / (6 * r['n'])), 4)} = <b>{br(cd, 3)}</b>"]))
st(P("Método 2 — Wilcoxon par a par com correção de Holm", "h2"))
st(P("Cada par é comparado pelo teste de Wilcoxon pareado (o mesmo do outro PDF), circuito a "
     "circuito. Depois os 15 p-valores são corrigidos por Holm: ordena-se do menor para o maior, "
     "multiplica-se o 1º por 15, o 2º por 14, e assim por diante; um p corrigido nunca fica menor "
     "que o anterior, e o máximo é 1."))
for nome, r in SIG:
    cd, lp = POS[nome]
    st(caixa([f"{i + 1}º menor p: {br(l['p'], 5)} × {15 - i} = {br(min(1, l['p'] * (15 - i)), 5)}"
              f"  →  p corrigido = <b>{br(l['holm'], 4)}</b>" for i, l in enumerate(lp[:3])]
             + ["... e assim até o 15º."]))
for nome, r in SIG:
    cd, lp = POS[nome]
    linhas = []
    for l in lp:
        sig = l["nem"] or l["holm"] < 0.05
        linhas.append([f"{'<b>' if sig else ''}{ESTR[l['a']]} &gt; {ESTR[l['b']]}{'</b>' if sig else ''}",
                       br(l["dif"], 2), "Sim" if l["nem"] else "Não",
                       f"{l['ganha']} / {l['perde']} / {l['empata']}", br(l["p"], 4),
                       f"<b>{br(l['holm'], 4)}</b>" if l["holm"] < 0.05 else br(l["holm"], 4)])
    st(KeepTogether([
        P(f"Tabela 4 — {nome}: os 15 pares, do menor para o maior p", "legenda"),
        tabela(["Par (posto maior &gt; menor)", "Diferença de postos médios",
                f"Nemenyi: passa da DC ({br(cd, 2)})?", "Ganha / perde / empata",
                "Wilcoxon: p", "p corrigido (Holm)"], linhas,
               [38 * mm, 26 * mm, 30 * mm, 28 * mm, 24 * mm, 28 * mm], primeira_esq=False)]))
    ok = [l for l in lp if l["nem"] and l["holm"] < 0.05]
    st(Spacer(1, 4))
    st(caixa([
        "<b>Resultado:</b> "
        + (lista([f"{NOME_ESTR[ESTR[l['a']]]} &gt; {NOME_ESTR[ESTR[l['b']]]}" for l in ok])
           + (" é o único par" if len(ok) == 1 else " são os pares") + " que difere pelos dois "
           "métodos." if ok else "nenhum par difere pelos dois métodos.")
        + " Todos os outros pares ficam abaixo da DC e com p corrigido acima de 0,05.",
        f"<b>Por isso não dá para eleger uma única melhor estratégia:</b> o {nomes(PRI[nome])} tem "
        f"o maior posto médio ({br(max(r['medias']), 2)}), mas não se distingue das outras "
        f"estratégias do topo. O que se comprova é a distância até o "
        f"{nomes(ULT[nome])}, o último colocado.",
    ], fundo=AMARELO, borda=OCRE))
st(P("Ganha / perde / empata: em quantos dos circuitos a estratégia de posto maior matou mais, "
     "menos ou o mesmo número médio de mutantes que a outra.", "nota"))

# ---- reproduzir ----
st(P("10. Como reproduzir", "h1"))
st(P("No Excel (português)", "h2"))
st(P("Monte uma tabela com os circuitos nas linhas 2 a 11 e as estratégias nas colunas B a G, já "
     "com a média das duas rodadas em cada célula (=MÉDIA(rodada 1; rodada 2), os valores em "
     "negrito da Tabela 1). Para os dois modelos juntos, use as linhas 2 a 21 e troque 10 por 20. "
     "Depois:"))
st(caixa([
    "1) Postos (colunas H a M), na célula H2, arrastando para a direita e para baixo:",
    "   =ORDEM.MÉD(B2;$B2:$G2;1)",
    "2) Soma dos postos de cada estratégia (linha 12):   =SOMA(H2:H11)",
    "3) Q sem correção:   =12/(10*6*7)*SOMAQUAD(H12:M12)-3*10*7",
    "4) Empates de cada circuito (coluna N):   =SOMARPRODUTO(CONT.SE(B2:G2;B2:G2)^2-1)",
    "5) C:   =1-SOMA(N2:N11)/(10*(6^3-6))",
    "6) Q corrigido: divida a célula do passo 3 pela célula do passo 5",
    "7) p-valor:   =DIST.QUIQUA.CD(Q;5)   (Q = célula do passo 6)",
], estilo="codigo"))
st(P("O passo 4 usa um atalho: contar, para cada célula, quantas vezes o seu valor aparece na "
     "linha (t), e somar t<super>2</super> − 1. Um grupo com t células contribui "
     "t × (t<super>2</super> − 1) = t<super>3</super> − t, que é exatamente o termo do passo 4.",
     "nota"))
st(fonte("funções MÉDIA, ORDEM.MÉD, SOMAQUAD, SOMARPRODUTO, CONT.SE e DIST.QUIQUA.CD: Microsoft "
         "(2026)."))
st(P("Em Python", "h2"))
col = lambda j: "[" + ", ".join(f"{v:g}" for v in [l[j] for l in gpt["valores"]]) + "]"
st(caixa([
    "from scipy.stats import friedmanchisquare",
    f"zs = {col(0)}   # GPT, média",
    f"fs = {col(1)}",
    "# ... uma lista de 10 valores para cada estratégia, na ordem dos circuitos",
    "friedmanchisquare(zs, fs, esp_zs, esp_fs, pln_zs, pln_fs)",
    f"# GPT -> statistic = {gpt['Q']:.4f}, pvalue = {gpt['p']:.4f}",
], estilo="codigo"))
st(fonte("biblioteca SciPy (VIRTANEN et al., 2020); a função já aplica a correção de empates. "
         "Os valores deste documento foram conferidos contra ela."))

# ---- de onde vem cada formula ----
st(P("11. De onde vem cada fórmula", "h1"))
st(tabela(["Passo", "Fórmula ou procedimento", "Fonte"], [
    ["0", "Não passou / Timeout = 0 mutantes mortos", "Decisão metodológica do trabalho"],
    ["0", "Valor = média das 2 rodadas", "Decisão do trabalho; repetir execuções: Arcuri e "
                                         "Briand (2011)"],
    ["1", "Postos dentro de cada circuito; empate = média das posições",
     "Friedman (1937); Siegel e Castellan Jr. (2006)"],
    ["2", "Posto médio = R<sub>j</sub> ÷ n", "Demšar (2006)"],
    ["3", "Q<sub>0</sub> = 12 ÷ (n·k·(k+1)) × ΣR<sub>j</sub><super>2</super> − 3·n·(k+1)",
     "Friedman (1937); Siegel e Castellan Jr. (2006)"],
    ["4", "C = 1 − Σ(t<super>3</super> − t) ÷ (n·(k<super>3</super> − k)); Q = Q<sub>0</sub> ÷ C",
     "Hollander, Wolfe e Chicken (2014)"],
    ["5", f"p = P(χ<super>2</super><sub>k−1</sub> ≥ Q); valor crítico {br(CRITICO, 2)}",
     "Friedman (1937); Siegel e Castellan Jr. (2006)"],
    ["5", "W de Kendall = Q ÷ (n·(k − 1))", "Siegel e Castellan Jr. (2006)"],
    ["9", "DC de Nemenyi = q<sub>α</sub> √(k(k+1) ÷ 6n); q<sub>0,05</sub> = 2,850 (k = 6)",
     "Demšar (2006)"],
    ["9", "Wilcoxon par a par com correção de Holm", "Wilcoxon (1945); Holm (1979)"],
    ["—", "Funções do Excel", "Microsoft (2026)"],
    ["—", "Conferência dos cálculos", "SciPy (VIRTANEN et al., 2020)"],
], [14 * mm, 96 * mm, 64 * mm], primeira_esq=False))

# ---- texto TCC ----
cd_j, lp_j = POS.get("Os dois juntos", (None, []))
ok_j = [l for l in lp_j if l["nem"] and l["holm"] < 0.05]
pares_j = lista([f"o par {NOME_ESTR[ESTR[l['a']]]} × {NOME_ESTR[ESTR[l['b']]]}" for l in ok_j]) if ok_j else ""
st(PageBreak())
st(P("12. Texto sugerido para o TCC", "h1"))
st(caixa([
    "<b>Metodologia.</b> Cada estratégia de prompt foi executada em duas rodadas independentes por "
    "circuito (na segunda, os testbenches foram gerados novamente, mantendo o RTL e, portanto, os "
    "mesmos mutantes), e a variável analisada foi a média de mutantes mortos nas duas rodadas (0 a "
    "4), atribuindo-se zero aos casos em que o testbench não passou no circuito original ou excedeu "
    "o tempo limite (ARCURI; BRIAND, 2011). Para avaliar se as seis estratégias diferem, aplicou-se "
    "o teste de Friedman (FRIEDMAN, 1937; SIEGEL; CASTELLAN JR., 2006) com correção para empates "
    "(HOLLANDER; WOLFE; CHICKEN, 2014), para cada modelo e para os dois modelos agrupados, tratando "
    "cada circuito como um bloco, ao nível de significância de 5%. Quando o teste indicou "
    "diferença, aplicou-se o pós-teste de Nemenyi (DEMŠAR, 2006) e comparações par a par pelo teste "
    "de Wilcoxon com correção de Holm (HOLM, 1979).",
    "",
    f"<b>Resultados.</b> Com os dois modelos agrupados, o teste de Friedman "
    + ("indicou diferença estatisticamente significativa" if JUNTOS["p"] < 0.05 else
       "não indicou diferença estatisticamente significativa")
    + f" entre as estratégias (χ<super>2</super>(5) = {br(JUNTOS['Q'], 2)}; p = {br(JUNTOS['p'], 3)}; "
    f"W de Kendall = {br(JUNTOS['W'], 2)}). Em cada modelo isolado, a diferença "
    + ("não foi significativa" if gpt["p"] >= 0.05 and gem["p"] >= 0.05 else "variou")
    + f" (GPT: χ<super>2</super>(5) = {br(gpt['Q'], 2)}, p = {br(gpt['p'], 3)}; Gemini: "
    f"χ<super>2</super>(5) = {br(gem['Q'], 2)}, p = {br(gem['p'], 3)}). O "
    f"{nomes(ULT['Os dois juntos'])} obteve o menor posto médio "
    f"({br(min(JUNTOS['medias']), 2)}) e o {nomes(PRI['Os dois juntos'])}, o maior "
    f"({br(max(JUNTOS['medias']), 2)}). "
    + (f"No pós-teste, apenas {pares_j} "
       f"diferiu significativamente (Nemenyi: diferença de postos "
       f"{lista([br(l['dif'], 2) for l in ok_j])} &gt; DC = {br(cd_j, 2)}; Wilcoxon com correção de "
       f"Holm: p = {lista([br(l['holm'], 3) for l in ok_j])}); as demais comparações não foram "
       f"significativas, de modo que não é possível apontar uma única estratégia superior."
       if ok_j else "No pós-teste, nenhum par diferiu significativamente."),
], fundo=colors.white, estilo="corpo"))

secao_referencias(story, ["ARCURI", "DEMSAR", "FRIEDMAN", "HOLLANDER", "HOLM", "MICROSOFT", "SIEGEL",
                          "VIRTANEN", "WILCOXON"])
st(P("Antes de entregar, confira cada referência pelo DOI ou no Google Acadêmico e ajuste ao "
     "padrão ABNT exigido pela sua instituição.", "nota"))

OUT = saida("friedman_passo_a_passo.pdf")
construir(OUT, story, TITULO)
for nome, r in CASOS:
    print(nome, "Q=%.4f p=%.4f W=%.4f medias=%s" % (r["Q"], r["p"], r["W"],
                                                     [round(x, 2) for x in r["medias"]]))
for nome, (cd, lp) in POS.items():
    print("pos-teste", nome, "CD=%.3f" % cd,
          [(ESTR[l["a"]], ESTR[l["b"]], round(l["p"], 4), round(l["holm"], 4), l["nem"]) for l in lp[:4]])
print("PDF:", OUT)
