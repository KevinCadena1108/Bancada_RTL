"""Gera o PDF "Teste de Wilcoxon pareado - passo a passo" (familia few-shot x familia zero-shot).

Todos os numeros sao calculados aqui a partir da linha "Mutantes" da planilha e conferidos
contra scipy.stats.wilcoxon (p exato por permutacao) antes de gerar o arquivo.
Uso: python gerar_pdf_wilcoxon.py <saida.pdf>
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
from scipy.stats import PermutationMethod, combine_pvalues
from scipy.stats import wilcoxon as sp_wilcoxon

from pdf_comum import (AMARELO, CIRCUITOS, CURTO, ESTR, NOME_ESTR, OCRE, PLANILHA, VERDE,
                       VERDE_BORDA, br, caixa, construir, fonte, item, P, postos,
                       secao_referencias, tabela, valores)

TITULO = "Teste de Wilcoxon pareado — passo a passo"
ZS_FAM, FS_FAM = [0, 2, 4], [1, 3, 5]      # ZS+EspZS+PlnZS  x  FS+EspFS+PlnFS


def wilcoxon_exato(x, y, nomes):
    """Wilcoxon pareado bicaudal exato, d = y - x, zeros descartados (metodo de Wilcoxon)."""
    d_all = [b - a for a, b in zip(x, y)]
    idx = [i for i, d in enumerate(d_all) if d != 0]
    d = [d_all[i] for i in idx]
    r = postos([abs(v) for v in d])
    wp = sum(ri for ri, di in zip(r, d) if di > 0)
    wm = sum(ri for ri, di in zip(r, d) if di < 0)
    n1 = len(d)
    media = n1 * (n1 + 1) / 4
    dist = Counter()
    for sinais in itertools.product([0, 1], repeat=n1):
        dist[sum(ri for ri, s in zip(r, sinais) if s)] += 1
    obs = abs(wp - media)
    extremos = sum(c for w, c in dist.items() if abs(w - media) >= obs - 1e-9)
    T = min(wp, wm)
    lado = sum(c for w, c in dist.items() if w <= T + 1e-9)
    p = extremos / 2 ** n1
    if n1:
        # so as diferencas nao nulas: com 2^n1 <= n_resamples o SciPy enumera todas (p exato)
        sp = sp_wilcoxon([y[i] for i in idx], [x[i] for i in idx], zero_method="wilcox",
                         method=PermutationMethod(n_resamples=max(10 ** 6, 2 ** n1)))
        assert abs(sp.statistic - T) < 1e-9 and abs(sp.pvalue - p) < 1e-9, (sp, T, p)
    assert abs(wp + wm - n1 * (n1 + 1) / 2) < 1e-9
    return dict(d_all=d_all, idx=idx, d=d, r=r, wp=wp, wm=wm, n1=n1, media=media, T=T,
                extremos=extremos, lado=lado, p=p, nomes=nomes,
                ganha=sum(v > 0 for v in d_all), perde=sum(v < 0 for v in d_all),
                empata=sum(v == 0 for v in d_all))


def critico(n, alfa=0.05):
    """Maior T com P(W <= T) <= alfa/2 sem empates (postos 1..n): o valor da tabela classica."""
    ways = [1] + [0] * (n * (n + 1) // 2)
    for k in range(1, n + 1):
        for s in range(len(ways) - 1, k - 1, -1):
            ways[s] += ways[s - k]
    acum, tcrit = 0, None
    for t, w in enumerate(ways):
        acum += w
        if acum / 2 ** n <= alfa / 2:
            tcrit = t
    return tcrit


def sd(v):
    """Inteiro com sinal: +3, −1 (sinal de menos tipografico), 0."""
    return f"+{v}" if v > 0 else (f"−{-v}" if v < 0 else "0")


def mil(v):
    return f"{v:,}".replace(",", ".")


def familias(vals):
    zs = [sum(l[j] for j in ZS_FAM) for l in vals]
    fs = [sum(l[j] for j in FS_FAM) for l in vals]
    return zs, fs


MODELOS = list(PLANILHA)
VAL = {m: valores(m) for m in MODELOS}
FAM = {m: familias(VAL[m]) for m in MODELOS}
RES = {m: wilcoxon_exato(FAM[m][0], FAM[m][1], CIRCUITOS) for m in MODELOS}
nomes_junt = [f"{c} ({CURTO[m]})" for m in MODELOS for c in CIRCUITOS]
JUNTOS = wilcoxon_exato(FAM[MODELOS[0]][0] + FAM[MODELOS[1]][0],
                        FAM[MODELOS[0]][1] + FAM[MODELOS[1]][1], nomes_junt)
X_FISHER = -2 * sum(math.log(RES[m]["p"]) for m in MODELOS)
P_FISHER = math.exp(-X_FISHER / 2) * (1 + X_FISHER / 2)          # qui-quadrado com 4 g.l.
_cf = combine_pvalues([RES[m]["p"] for m in MODELOS], method="fisher")
assert abs(_cf.statistic - X_FISHER) < 1e-9 and abs(_cf.pvalue - P_FISHER) < 1e-9
CRIT = {n: critico(n) for n in {RES[m]["n1"] for m in MODELOS} | {JUNTOS["n1"]}}

PARES = [("ZS", "FS"), ("EspZS", "EspFS"), ("PlnZS", "PlnFS"),
         ("ZS", "EspZS"), ("ZS", "PlnZS"), ("FS", "EspFS"), ("FS", "PlnFS")]
PAR = {m: [wilcoxon_exato([l[ESTR.index(a)] for l in VAL[m]], [l[ESTR.index(b)] for l in VAL[m]],
                          CIRCUITOS) for a, b in PARES] for m in MODELOS}

gpt, gem = RES[MODELOS[0]], RES[MODELOS[1]]
story = []
st = story.append

st(P(TITULO, "titulo"))
st(P("Família few-shot × família zero-shot nos testbenches gerados pelo GPT-5.6 Luna e pelo "
     "Gemini 3.5 Flash-Lite", "sub"))
st(Spacer(1, 10))
st(caixa([
    "<b>Resultado em uma linha:</b> a família few-shot matou mais mutantes que a zero-shot nos "
    "dois modelos. Em cada modelo isolado é uma <b>tendência</b>; com os dois modelos juntos, a "
    "diferença é <b>estatisticamente significativa</b>.",
    f"<b>GPT-5.6 Luna:</b> T = {br(gpt['T'])}; p = {br(gpt['p'], 3)}",
    f"<b>Gemini 3.5 Flash-Lite:</b> T = {br(gem['T'])}; p = {br(gem['p'], 3)}",
    f"<b>Os dois juntos:</b> T = {br(JUNTOS['T'])}; p = {br(JUNTOS['p'], 3)}",
], fundo=VERDE, borda=VERDE_BORDA))

# ---- 1. o que responde ----
st(P("1. O que o teste responde", "h1"))
st(P("O teste de Wilcoxon pareado compara <b>duas condições aplicadas aos mesmos casos</b>. Aqui "
     "a pergunta é: <b>os testbenches gerados com exemplos (few-shot) matam mais mutantes do que "
     "os gerados sem exemplos (zero-shot), nos mesmos circuitos?</b>"))
st(P("É um <b>confronto direto</b>: em cada circuito, vê-se quem ganhou e por quanto. Se uma das "
     "condições ganha quase sempre, e por margens grandes, o teste conclui que a diferença não é "
     "sorte."))
st(P("<b>Por que comparar famílias.</b> O experimento é um fatorial 2 × 3: o fator “shot” "
     "(zero-shot ou few-shot) cruzado com o fator “reforço” (base, especialista, planning). Para "
     "medir o efeito do shot, somam-se, em cada circuito, as três variantes de cada nível:"))
st(item("<b>família zero-shot</b> = ZS + EspZS + PlnZS;"))
st(item("<b>família few-shot</b> = FS + EspFS + PlnFS."))
st(P("Essa é a hipótese principal do trabalho, definida antes de olhar os resultados. Por isso "
     "ela é testada diretamente, sem depender do teste de Friedman."))
st(fonte("teste proposto por Wilcoxon (1945); procedimento descrito em Siegel e Castellan Jr. "
         "(2006) como “prova de Wilcoxon” para duas amostras relacionadas. A soma das variantes "
         "de cada nível é uma decisão do desenho fatorial deste trabalho."))
st(P("Notação usada no documento", "h2"))
st(tabela(["Símbolo", "Significado"], [
    ["d", "diferença no circuito: família few-shot − família zero-shot"],
    ["n′", "número de circuitos com diferença diferente de zero"],
    ["W<super>+</super>", "soma dos postos das diferenças positivas (few-shot ganhou)"],
    ["W<super>−</super>", "soma dos postos das diferenças negativas (few-shot perdeu)"],
    ["T", "o menor entre W<super>+</super> e W<super>−</super>"],
], [22 * mm, 152 * mm]))

# ---- 2. passo 0 ----
st(P("2. Passo 0 — Montar as duas famílias", "h1"))
st(P("Os valores são os mesmos do teste de Friedman: cada célula da linha “Mutantes” vira o "
     "número de mutantes mortos (“4/4” → 4), e “Não passou” ou “Timeout” valem 0. Em cada "
     "circuito somam-se as três variantes de cada família e calcula-se a diferença "
     "<b>d = few-shot − zero-shot</b>."))
st(fonte("conversão: decisão metodológica deste trabalho (score de mutação efetivo)."))
W10 = [30 * mm] + [15 * mm] * 8 + [24 * mm]
for m in MODELOS:
    zs, fs = FAM[m]
    linhas = []
    for i, nome in enumerate(CIRCUITOS):
        v = VAL[m][i]
        linhas.append([nome] + [str(v[j]) for j in ZS_FAM] + [f"<b>{zs[i]}</b>"]
                      + [str(v[j]) for j in FS_FAM] + [f"<b>{fs[i]}</b>"]
                      + [f"<b>{sd(fs[i] - zs[i])}</b>"])
    linhas.append(["<b>Total</b>", "", "", "", f"<b>{sum(zs)}</b>", "", "", "", f"<b>{sum(fs)}</b>",
                   f"<b>{sd(sum(fs) - sum(zs))}</b>"])
    st(KeepTogether([
        P(f"Tabela 1{'a' if CURTO[m] == 'GPT' else 'b'} — {m}: famílias e diferença", "legenda"),
        tabela(["Circuito", "ZS", "EspZS", "PlnZS", "Soma ZS", "FS", "EspFS", "PlnFS", "Soma FS",
                "d = FS − ZS"], linhas, W10, destacar_ultima=True)]))

# ---- 3. passo 1 ----
st(PageBreak())
st(P("3. Passo 1 — Descartar os empates (d = 0)", "h1"))
st(P("Circuitos em que as duas famílias mataram o mesmo número de mutantes (d = 0) não indicam "
     "vantagem para nenhum lado e saem da conta. O teste continua com os n′ circuitos restantes."))
st(fonte("descarte das diferenças nulas: método original de Wilcoxon (1945), que é o padrão "
         "(<i>zero_method = “wilcox”</i>) do SciPy. Pratt (1959) discute uma alternativa que "
         "mantém os zeros na ordenação; ela não foi usada aqui."))
st(tabela(["Modelo", "Circuitos descartados (d = 0)", "n′"], [
    [m, ", ".join(CIRCUITOS[i] for i, v in enumerate(RES[m]["d_all"]) if v == 0) or "nenhum",
     str(RES[m]["n1"])] for m in MODELOS
], [44 * mm, 110 * mm, 20 * mm]))

# ---- 4. passo 2 ----
st(P("4. Passo 2 — Dar postos às diferenças, sem olhar o sinal", "h1"))
st(P("Ordenam-se as diferenças pelo <b>tamanho</b> (o valor absoluto |d|), da menor para a maior. "
     "A menor recebe posto 1. Empates recebem a <b>média das posições</b> que ocupam, como no "
     "Friedman. Depois, cada posto recebe de volta o sinal da sua diferença."))
st(fonte("postos das diferenças absolutas com sinal: Wilcoxon (1945); posto médio para empates: "
         "Siegel e Castellan Jr. (2006)."))


def tabela_postos(r, rotulo):
    ordem = sorted(range(r["n1"]), key=lambda q: (abs(r["d"][q]), r["idx"][q]))
    linhas = []
    for q in ordem:
        dv, rk = r["d"][q], r["r"][q]
        sinal = "+" if dv > 0 else "−"
        linhas.append([r["nomes"][r["idx"][q]], f"{'+' if dv > 0 else '−'}{abs(dv)}", str(abs(dv)),
                       br(rk), sinal, f"<b>{sinal}{br(rk)}</b>"])
    return KeepTogether([
        P(rotulo, "legenda"),
        tabela(["Circuito", "d", "|d|", "Posto de |d|", "Sinal", "Posto com sinal"], linhas,
               [52 * mm, 20 * mm, 20 * mm, 28 * mm, 20 * mm, 34 * mm])])


r = gpt
iguais = Counter(abs(v) for v in r["d"])
ex = [v for v, c in sorted(iguais.items()) if c >= 2][0]
pos = [q + 1 for q, v in enumerate(sorted(abs(x) for x in r["d"])) if v == ex]
st(tabela_postos(gpt, f"Tabela 2a — {MODELOS[0]}: postos das diferenças, da menor para a maior"))
st(Spacer(1, 4))
st(caixa(f"Exemplo de empate: há {iguais[ex]} diferenças de tamanho <b>{ex}</b>, nas "
         f"posições {' e '.join(map(str, pos))}  →  ({' + '.join(map(str, pos))}) ÷ {len(pos)} = "
         f"<b>{br(sum(pos) / len(pos))}</b> para cada uma"))
st(tabela_postos(gem, f"Tabela 2b — {MODELOS[1]}: postos das diferenças, da menor para a maior"))

# ---- 5. passo 3 ----
st(KeepTogether([
    P("5. Passo 3 — Somar os postos de cada lado", "h1"),
    caixa(["<b>W<super>+</super> = soma dos postos com sinal positivo</b>",
           "<b>W<super>−</super> = soma dos postos com sinal negativo</b>",
           "<b>T = menor entre W<super>+</super> e W<super>−</super></b>",
           "Conferência: W<super>+</super> + W<super>−</super> = n′ × (n′ + 1) ÷ 2"]),
    fonte("Wilcoxon (1945); Siegel e Castellan Jr. (2006)."),
]))
for m in MODELOS:
    r = RES[m]
    pos_txt = " + ".join(br(rk) for rk, dv in sorted(zip(r["r"], r["d"])) if dv > 0)
    neg_txt = " + ".join(br(rk) for rk, dv in sorted(zip(r["r"], r["d"])) if dv < 0)
    st(P(m, "h2"))
    st(caixa([
        f"W<super>+</super> = {pos_txt} = <b>{br(r['wp'])}</b>",
        f"W<super>−</super> = {neg_txt} = <b>{br(r['wm'])}</b>",
        f"Conferência: {br(r['wp'])} + {br(r['wm'])} = {br(r['wp'] + r['wm'])} = "
        f"{r['n1']} × {r['n1'] + 1} ÷ 2 ✓      T = <b>{br(r['T'])}</b>",
    ]))
st(P("As vitórias do few-shot são muitas e grandes (W<super>+</super> alto); as derrotas são "
     "poucas e pequenas (W<super>−</super> baixo). Quanto mais desequilibrado, mais forte a "
     "evidência."))

# ---- 6. passo 4 ----
st(PageBreak())
st(P("6. Passo 4 — Calcular o p-valor exato", "h1"))
st(P("<b>A ideia:</b> se o few-shot não fizesse diferença nenhuma, cada diferença teria a mesma "
     "chance de sair positiva ou negativa, como uma moeda. Com n′ diferenças existem "
     "<b>2<super>n′</super></b> combinações de sinais, todas igualmente prováveis. O p-valor é a "
     "fração dessas combinações que dá um resultado <b>tão desequilibrado quanto o observado, ou "
     "mais</b>, para qualquer um dos lados (teste bicaudal)."))
st(caixa("<b>p = (nº de combinações com W<super>+</super> ≤ T ou W<super>+</super> ≥ "
         "n′(n′+1)/2 − T) ÷ 2<super>n′</super></b>"))
st(fonte("distribuição exata por troca de sinais: Wilcoxon (1945); com empates, a distribuição "
         "exata é calculada sobre os próprios postos médios (distribuição condicional), conforme "
         "Pratt (1959) e Hollander, Wolfe e Chicken (2014). Conferido com o SciPy "
         "(VIRTANEN et al., 2020)."))

r = gpt
st(P(f"Exemplo completo: GPT (n′ = {r['n1']})", "h2"))
st(P(f"São 2<super>{r['n1']}</super> = <b>{2 ** r['n1']}</b> combinações. O resultado observado "
     f"foi T = {br(r['T'])}. Pela simetria da distribuição, basta contar de um lado e dobrar. "
     f"Estas são <b>todas</b> as escolhas de postos “positivos” cuja soma é ≤ {br(r['T'])}:"))
rotulo = {q: f"{r['nomes'][r['idx'][q]]} ({br(r['r'][q])})" for q in range(r["n1"])}
subconj = []
for tam in range(r["n1"] + 1):
    for comb in itertools.combinations(range(r["n1"]), tam):
        s = sum(r["r"][q] for q in comb)
        if s <= r["T"] + 1e-9:
            subconj.append((s, comb))
subconj.sort(key=lambda x: (x[0], len(x[1])))
assert len(subconj) == r["lado"]
st(tabela(["#", "Postos que seriam positivos", "W<super>+</super>"],
          [[str(i + 1), ", ".join(rotulo[q] for q in comb) or "nenhum (todos negativos)", br(s)]
           for i, (s, comb) in enumerate(subconj)], [12 * mm, 136 * mm, 26 * mm], primeira_esq=False))
st(Spacer(1, 4))
st(caixa([f"Um lado: <b>{r['lado']}</b> combinações; o outro lado (W<super>+</super> ≥ "
          f"{br(r['n1'] * (r['n1'] + 1) / 2 - r['T'])}) tem o mesmo número por simetria.",
          f"p = ({r['lado']} + {r['extremos'] - r['lado']}) ÷ {2 ** r['n1']} = {r['extremos']} ÷ "
          f"{2 ** r['n1']} = <b>{br(r['p'], 4)}</b>"]))

st(P("Os outros casos, com a mesma conta", "h2"))
linhas = []
for nome, rr in [(MODELOS[1], gem), ("Os dois juntos (20 pares)", JUNTOS)]:
    linhas.append([nome, str(rr["n1"]), mil(2 ** rr["n1"]), br(rr["T"]), mil(rr["extremos"]),
                   f"{mil(rr['extremos'])} ÷ {mil(2 ** rr['n1'])} = <b>{br(rr['p'], 4)}</b>"])
st(tabela(["Caso", "n′", "2<super>n′</super>", "T", "Combinações extremas", "p"], linhas,
          [46 * mm, 12 * mm, 22 * mm, 14 * mm, 30 * mm, 50 * mm]))

st(P("Alternativa: tabela de valores críticos", "h2"))
st(P("Os livros trazem uma tabela com o <b>T crítico</b>: se o T observado for <b>menor ou "
     "igual</b> a ele, o resultado é significativo a 5% (bicaudal). A tabela supõe que não há "
     "empates, então com postos médios ela é apenas aproximada; por isso aqui se usou o p exato."))
st(tabela(["Caso", "n′", "T observado", "T crítico (5%)", "Conclusão"], [
    [m, str(RES[m]["n1"]), br(RES[m]["T"]), str(CRIT[RES[m]["n1"]]),
     "significativo" if RES[m]["T"] <= CRIT[RES[m]["n1"]] else "não significativo"] for m in MODELOS
] + [["Os dois juntos", str(JUNTOS["n1"]), br(JUNTOS["T"]), str(CRIT[JUNTOS["n1"]]),
      "significativo" if JUNTOS["T"] <= CRIT[JUNTOS["n1"]] else "não significativo"]],
    [46 * mm, 14 * mm, 30 * mm, 34 * mm, 50 * mm]))
st(fonte("tabela de valores críticos do teste de Wilcoxon: Siegel e Castellan Jr. (2006). Os "
         "valores acima foram recalculados pela distribuição exata sem empates."))

# ---- 7. juntos ----
st(PageBreak())
st(P("7. Os dois modelos juntos", "h1"))
st(P("Juntando GPT e Gemini, cada par (circuito, modelo) vira um caso: são 20 pares em vez de "
     "10. Com mais casos, uma diferença consistente fica mais fácil de distinguir do acaso."))
st(tabela_postos(JUNTOS, "Tabela 3 — Os dois modelos juntos: postos das diferenças"))
st(Spacer(1, 4))
st(caixa([f"W<super>+</super> = <b>{br(JUNTOS['wp'])}</b>;  W<super>−</super> = "
          f"<b>{br(JUNTOS['wm'])}</b>;  T = <b>{br(JUNTOS['T'])}</b>",
          f"Conferência: {br(JUNTOS['wp'])} + {br(JUNTOS['wm'])} = {br(JUNTOS['wp'] + JUNTOS['wm'])} "
          f"= {JUNTOS['n1']} × {JUNTOS['n1'] + 1} ÷ 2 ✓",
          f"p = {mil(JUNTOS['extremos'])} ÷ {mil(2 ** JUNTOS['n1'])} = <b>{br(JUNTOS['p'], 4)}</b>"]))
st(P("<b>Cuidado ao reportar:</b> os mesmos circuitos aparecem nos dois modelos, então os 20 pares "
     "não são totalmente independentes. Vale declarar isso no texto e mostrar a verificação "
     "abaixo, que não depende de juntar os pares."))
st(P("Verificação de robustez: método de Fisher", "h2"))
st(P("Em vez de juntar os pares, combinam-se os dois p-valores de cada modelo, que vêm de amostras "
     "independentes (cada modelo gerou os seus testbenches):"))
st(caixa([
    "<b>X = −2 × Σ ln(p<sub>i</sub>)</b>, comparado com χ<super>2</super> com 2 × (nº de testes) "
    "= 4 graus de liberdade",
    f"X = −2 × (ln {br(gpt['p'], 4)} + ln {br(gem['p'], 4)}) = <b>{br(X_FISHER, 2)}</b>  →  "
    f"p = <b>{br(P_FISHER, 3)}</b>      (Excel: =DIST.QUIQUA.CD({br(X_FISHER, 2)}; 4))",
]))
st(fonte("método de combinação de p-valores de Fisher (1932). Conferido com a função "
         "<i>combine_pvalues</i> do SciPy (VIRTANEN et al., 2020)."))
st(P("As duas formas chegam à mesma conclusão: abaixo de 0,05."))

# ---- 8. resultado ----
st(PageBreak())
st(P("8. Resultado final", "h1"))
linhas = []
for nome, rr in [(MODELOS[0], gpt), (MODELOS[1], gem), ("Os dois juntos (20 pares)", JUNTOS)]:
    linhas.append([nome, str(rr["n1"]), f"{rr['ganha']} / {rr['perde']} / {rr['empata']}",
                   br(rr["wp"]), br(rr["wm"]), f"<b>{br(rr['p'], 3)}</b>",
                   "Sim" if rr["p"] < 0.05 else "Não (tendência)"])
linhas.append(["Fisher (GPT + Gemini)", "—", "—", "—", "—", f"<b>{br(P_FISHER, 3)}</b>",
               "Sim" if P_FISHER < 0.05 else "Não"])
st(tabela(["Caso", "n′", "FS ganha / perde / empata", "W<super>+</super>", "W<super>−</super>",
           "p", "Significativo?"], linhas,
          [44 * mm, 10 * mm, 34 * mm, 16 * mm, 16 * mm, 18 * mm, 36 * mm]))
st(P("Fonte: elaborado pelo autor a partir da planilha do experimento.", "nota"))
bloco = [P("Como interpretar", "h2"),
         item(f"<b>Em cada modelo:</b> o few-shot ganhou em {gpt['ganha']} (GPT) e {gem['ganha']} "
              f"(Gemini) dos 10 circuitos, mas p = {br(gpt['p'], 3)} nos dois: há cerca de "
              f"{br(100 * gpt['p'], 0)}% de chance de um desequilíbrio desse tamanho aparecer por "
              f"acaso. É uma <b>tendência</b>, ainda não significativa a 5%."),
         item(f"<b>Com os dois modelos:</b> o few-shot ganha em {JUNTOS['ganha']} e perde em "
              f"{JUNTOS['perde']} dos 20 pares, com p = {br(JUNTOS['p'], 3)}: menos de 1% de chance "
              f"de ser acaso. <b>A diferença é significativa.</b> O método de Fisher confirma "
              f"(p = {br(P_FISHER, 3)})."),
         item("<b>Conclusão:</b> testbenches gerados com exemplos matam significativamente mais "
              "mutantes do que os gerados sem exemplos, de forma consistente nos dois modelos.")]
st(KeepTogether(bloco))

# ---- 9. pares ----
st(PageBreak())
st(P("9. Complemento: comparações par a par", "h1"))
st(P("O mesmo teste, aplicado a pares de estratégias que diferem em <b>um único fator</b>. Os "
     "três primeiros pares medem o efeito do exemplo dentro de cada estilo; os quatro últimos, o "
     "efeito do reforço (especialista ou planning) sem e com exemplos."))
linhas = []
for k, (a, b) in enumerate(PARES):
    lin = [f"{a} × {b}"]
    for m in MODELOS:
        rr = PAR[m][k]
        lin += [f"{rr['ganha']} / {rr['perde']} / {rr['empata']}", br(rr["p"], 3)]
    linhas.append(lin)
st(tabela(["Par (o segundo ganha?)", "GPT: ganha / perde / empata", "GPT: p",
           "Gemini: ganha / perde / empata", "Gemini: p"], linhas,
          [40 * mm, 42 * mm, 20 * mm, 50 * mm, 22 * mm]))
menor = min(rr["p"] for m in MODELOS for rr in PAR[m])
st(P(f"<b>Nenhuma comparação par a par é significativa</b>, nem antes de qualquer correção para "
     f"múltiplas comparações (o menor p foi {br(menor, 3)}). Exemplo: no GPT, ZS × FS deu 4 vitórias "
     f"do few-shot e nenhuma derrota, mas com só 4 diferenças existem 2<super>4</super> = 16 "
     f"combinações, e o menor p possível é 2 ÷ 16 = 0,125. Não falta efeito, falta "
     f"resolução: por isso o efeito só aparece somando as três variantes de cada família."))

# ---- 10. reproduzir ----
st(P("10. Como reproduzir", "h1"))
st(P("No Excel (português)", "h2"))
st(P("Coloque a soma da família zero-shot na coluna B e a da few-shot na coluna C, com os "
     "circuitos nas linhas 2 a 11 (Tabela 1). Depois:"))
st(caixa([
    "1) Diferença (coluna D):          =C2-B2",
    "2) |d| sem os zeros (coluna E):   =SE(D2=0;\"\";ABS(D2))",
    "3) Posto (coluna F):              =SE(E2=\"\";\"\";ORDEM.MÉD(E2;$E$2:$E$11;1))",
    "4) W+:   =SOMASE(D2:D11;\">0\";F2:F11)        W−:   =SOMASE(D2:D11;\"<0\";F2:F11)",
    "5) T:    =MÍNIMO(W+; W−)  e compare com a tabela de valores críticos",
], estilo="codigo"))
st(P("O Excel não calcula o p exato do Wilcoxon. Para ele, use a tabela de valores críticos "
     "(seção 6) ou o Python.", "nota"))
st(fonte("funções SE, ABS, ORDEM.MÉD, SOMASE e MÍNIMO: Microsoft (2026)."))
st(P("Em Python", "h2"))
zs, fs = FAM[MODELOS[0]]
st(caixa([
    "from scipy.stats import wilcoxon, PermutationMethod",
    f"zs = {zs}   # GPT: ZS + EspZS + PlnZS",
    f"fs = {fs}   # GPT: FS + EspFS + PlnFS",
    "wilcoxon(fs, zs, zero_method=\"wilcox\", method=PermutationMethod(n_resamples=10**6))",
    f"# -> statistic = {gpt['T']}, pvalue = {gpt['p']:.4f}",
    "# Para os 20 pares juntos, passe só os pares com d diferente de 0: com eles o",
    "# SciPy enumera todas as combinações; com os zeros, passa de 10**6 e vira sorteio.",
], estilo="codigo"))
st(fonte("biblioteca SciPy (VIRTANEN et al., 2020). <i>PermutationMethod</i> calcula o p exato "
         "pela troca de sinais, inclusive com empates."))

# ---- 11. fontes ----
st(P("11. De onde vem cada fórmula", "h1"))
st(tabela(["Passo", "Fórmula ou procedimento", "Fonte"], [
    ["0", "Família = soma das 3 variantes; Não passou / Timeout = 0", "Decisão metodológica do trabalho"],
    ["1", "Descartar as diferenças nulas (d = 0)", "Wilcoxon (1945); alternativa: Pratt (1959)"],
    ["2", "Postos de |d|; empate = média das posições; posto recebe o sinal de d",
     "Wilcoxon (1945); Siegel e Castellan Jr. (2006)"],
    ["3", "W<super>+</super>, W<super>−</super>, T = mín(W<super>+</super>, W<super>−</super>); "
          "W<super>+</super> + W<super>−</super> = n′(n′+1)/2",
     "Wilcoxon (1945); Siegel e Castellan Jr. (2006)"],
    ["4", "p exato = combinações extremas ÷ 2<super>n′</super> (com postos médios)",
     "Wilcoxon (1945); Pratt (1959); Hollander, Wolfe e Chicken (2014)"],
    ["4", "Tabela de T crítico", "Siegel e Castellan Jr. (2006)"],
    ["7", "Fisher: X = −2 Σ ln p<sub>i</sub>, χ<super>2</super> com 2m g.l.", "Fisher (1932)"],
    ["—", "Funções do Excel", "Microsoft (2026)"],
    ["—", "Conferência dos cálculos", "SciPy (VIRTANEN et al., 2020)"],
], [14 * mm, 96 * mm, 64 * mm], primeira_esq=False))

# ---- 12. texto TCC ----
st(P("12. Texto sugerido para o TCC", "h1"))
st(caixa([
    "<b>Metodologia.</b> Para avaliar o efeito do uso de exemplos, os mutantes mortos das três "
    "variantes de cada nível do fator shot foram somados por circuito, formando as famílias "
    "zero-shot e few-shot, comparadas pelo teste de Wilcoxon pareado (WILCOXON, 1945; SIEGEL; "
    "CASTELLAN JR., 2006), bicaudal, com p-valor exato. Diferenças nulas foram descartadas e "
    "empates receberam o posto médio. A análise foi feita para cada modelo e para os dois modelos "
    "agrupados; como verificação, os p-valores dos dois modelos foram combinados pelo método de "
    "Fisher (FISHER, 1932).",
    "",
    f"<b>Resultados.</b> A família few-shot matou mais mutantes que a zero-shot nos dois modelos "
    f"(GPT: {gpt['ganha']} vitórias e {gpt['perde']} derrotas, T = {br(gpt['T'])}, "
    f"p = {br(gpt['p'], 3)}; Gemini: {gem['ganha']} vitórias e {gem['perde']} derrotas, "
    f"T = {br(gem['T'])}, p = {br(gem['p'], 3)}). Com os dois modelos agrupados (n = 20 pares), a "
    f"diferença foi estatisticamente significativa (T = {br(JUNTOS['T'])}, p = {br(JUNTOS['p'], 3)}), "
    f"resultado confirmado pela combinação de Fisher (p = {br(P_FISHER, 3)}). Nenhuma comparação par "
    f"a par entre estratégias que diferem em um único fator foi significativa (p ≥ {br(menor, 3)}).",
], fundo=colors.white, estilo="corpo"))

secao_referencias(story, ["FISHER", "HOLLANDER", "MICROSOFT", "PRATT", "SIEGEL", "VIRTANEN",
                          "WILCOXON"])
st(P("Antes de entregar, confira cada referência pelo DOI ou no Google Acadêmico e ajuste ao "
     "padrão ABNT exigido pela sua instituição.", "nota"))

construir(sys.argv[1], story, TITULO)
for nome, rr in [(MODELOS[0], gpt), (MODELOS[1], gem), ("juntos", JUNTOS)]:
    print(nome, "n'=%d W+=%s W-=%s T=%s p=%.5f extremos=%d" % (rr["n1"], rr["wp"], rr["wm"], rr["T"],
                                                             rr["p"], rr["extremos"]))
print("Fisher X=%.4f p=%.4f | criticos %s | menor p par a par %.4f" % (X_FISHER, P_FISHER, CRIT, menor))
print("PDF:", sys.argv[1])
