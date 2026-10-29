"""Gera o PDF "Teste de Wilcoxon pareado - passo a passo" (familia few-shot x familia zero-shot).

O valor analisado e a media das 2 rodadas em cada celula. Todos os numeros sao calculados aqui a
partir da linha "Mutantes" da planilha e conferidos contra scipy.stats.wilcoxon (p exato por
permutacao) antes de gerar o arquivo.
Uso: python gerar_pdf_wilcoxon.py [saida.pdf]   (padrao: documentacao/wilcoxon_passo_a_passo.pdf)
"""
import itertools
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer
from scipy.stats import PermutationMethod, combine_pvalues
from scipy.stats import wilcoxon as sp_wilcoxon

from pdf_comum import (AMARELO, CIRCUITOS, CURTO, ESTR, MODELOS, OCRE, VERDE, VERDE_BORDA, br,
                       caixa, construir, fonte, holm, item, P, postos, saida, secao_referencias,
                       tabela, valores)

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
    """Numero com sinal: +3, −1,5 (sinal de menos tipografico), 0."""
    return f"+{br(v)}" if v > 0 else (f"−{br(-v)}" if v < 0 else "0")


def mil(v):
    return f"{v:,}".replace(",", ".")


def familias(vals):
    zs = [sum(l[j] for j in ZS_FAM) for l in vals]
    fs = [sum(l[j] for j in FS_FAM) for l in vals]
    return zs, fs


def analise(vals_por_modelo):
    """Wilcoxon da familia em cada modelo, juntos, e o Fisher dos dois."""
    fam = {m: familias(vals_por_modelo[m]) for m in MODELOS}
    res = {m: wilcoxon_exato(fam[m][0], fam[m][1], CIRCUITOS) for m in MODELOS}
    nomes_junt = [f"{c} ({CURTO[m]})" for m in MODELOS for c in CIRCUITOS]
    junt = wilcoxon_exato(fam[MODELOS[0]][0] + fam[MODELOS[1]][0],
                          fam[MODELOS[0]][1] + fam[MODELOS[1]][1], nomes_junt)
    return fam, res, junt, combine_pvalues([res[m]["p"] for m in MODELOS], method="fisher").pvalue


VAL = {m: valores(m) for m in MODELOS}
FAM, RES, JUNTOS, _ = analise(VAL)
X_FISHER = -2 * sum(math.log(RES[m]["p"]) for m in MODELOS)
P_FISHER = math.exp(-X_FISHER / 2) * (1 + X_FISHER / 2)          # qui-quadrado com 4 g.l.
_cf = combine_pvalues([RES[m]["p"] for m in MODELOS], method="fisher")
assert abs(_cf.statistic - X_FISHER) < 1e-9 and abs(_cf.pvalue - P_FISHER) < 1e-9
CRIT = {n: critico(n) for n in {RES[m]["n1"] for m in MODELOS} | {JUNTOS["n1"]}}
RODADA = {r: analise({m: valores(m, r) for m in MODELOS}) for r in (1, 2)}
# a 1a rodada sozinha tem que dar os mesmos numeros do PDF anterior (so com ela)
assert (RODADA[1][1][MODELOS[0]]["T"], RODADA[1][1][MODELOS[1]]["T"], RODADA[1][2]["T"]) == (5.5, 8, 23)

PARES_SHOT = [("ZS", "FS"), ("EspZS", "EspFS"), ("PlnZS", "PlnFS")]
PARES_REF = [("ZS", "EspZS"), ("ZS", "PlnZS"), ("FS", "EspFS"), ("FS", "PlnFS")]
PARES = PARES_SHOT + PARES_REF


def par(vals, a, b):
    return wilcoxon_exato([l[ESTR.index(a)] for l in vals], [l[ESTR.index(b)] for l in vals],
                          CIRCUITOS)


PAR = {m: [par(VAL[m], a, b) for a, b in PARES] for m in MODELOS}
PAR_J = [par(VAL[MODELOS[0]] + VAL[MODELOS[1]], a, b) for a, b in PARES]
HOLM_J = (holm([w["p"] for w in PAR_J[:3]]) + holm([w["p"] for w in PAR_J[3:]]))

gpt, gem = RES[MODELOS[0]], RES[MODELOS[1]]
CASOS = [(MODELOS[0], gpt), (MODELOS[1], gem), ("Os dois juntos (20 pares)", JUNTOS)]


def lado_txt(rr):
    return "few-shot" if rr["wp"] > rr["wm"] else "zero-shot"


story = []
st = story.append

st(P(TITULO, "titulo"))
st(P("Família few-shot × família zero-shot nos testbenches gerados pelo GPT-5.6 Luna e pelo "
     "Gemini 3.5 Flash-Lite — média das 2 rodadas", "sub"))
st(Spacer(1, 10))
st(caixa([
    "<b>Resultado em uma linha:</b> com os dois modelos juntos, a família few-shot matou "
    + ("<b>significativamente mais</b> mutantes que a zero-shot" if JUNTOS["p"] < 0.05 else
       "mais mutantes que a zero-shot, sem significância")
    + f" (p = {br(JUNTOS['p'], 3)}). Por modelo, o efeito "
    + " e ".join(f"{'é significativo' if rr['p'] < 0.05 else 'não é significativo'} no "
                 f"{CURTO[m]} (p = {br(rr['p'], 3)})" for m, rr in RES.items()) + ".",
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
st(P("<b>Duas rodadas.</b> Cada estratégia foi executada duas vezes em cada circuito (na 2ª rodada, "
     "testbenches gerados de novo, com os mesmos 4 mutantes). O valor de cada estratégia é a "
     "<b>média das duas rodadas</b>, como no teste de Friedman."))
st(fonte("teste proposto por Wilcoxon (1945); procedimento descrito em Siegel e Castellan Jr. "
         "(2006) como “prova de Wilcoxon” para duas amostras relacionadas. A soma das variantes "
         "de cada nível é uma decisão do desenho fatorial deste trabalho. Repetir as execuções: "
         "Arcuri e Briand (2011)."))
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
     "número de mutantes mortos (“4/4” → 4), “Não passou” ou “Timeout” valem 0, e usa-se a média "
     "das duas rodadas (a Tabela 1 do PDF do Friedman mostra as duas rodadas lado a lado). Em cada "
     "circuito somam-se as três variantes de cada família e calcula-se a diferença "
     "<b>d = few-shot − zero-shot</b>."))
st(fonte("conversão e média das rodadas: decisão metodológica deste trabalho (score de mutação "
         "efetivo)."))
W10 = [30 * mm] + [15 * mm] * 8 + [24 * mm]
for m in MODELOS:
    zs, fs = FAM[m]
    linhas = []
    for i, nome in enumerate(CIRCUITOS):
        v = VAL[m][i]
        linhas.append([nome] + [br(v[j]) for j in ZS_FAM] + [f"<b>{br(zs[i])}</b>"]
                      + [br(v[j]) for j in FS_FAM] + [f"<b>{br(fs[i])}</b>"]
                      + [f"<b>{sd(fs[i] - zs[i])}</b>"])
    linhas.append(["<b>Total</b>", "", "", "", f"<b>{br(sum(zs))}</b>", "", "", "",
                   f"<b>{br(sum(fs))}</b>", f"<b>{sd(sum(fs) - sum(zs))}</b>"])
    st(KeepTogether([
        P(f"Tabela 1{'a' if CURTO[m] == 'GPT' else 'b'} — {m}: famílias e diferença (média das "
          f"2 rodadas)", "legenda"),
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
        linhas.append([r["nomes"][r["idx"][q]], sd(dv), br(abs(dv)), br(rk), sinal,
                       f"<b>{sinal}{br(rk)}</b>"])
    return KeepTogether([
        P(rotulo, "legenda"),
        tabela(["Circuito", "d", "|d|", "Posto de |d|", "Sinal", "Posto com sinal"], linhas,
               [52 * mm, 20 * mm, 20 * mm, 28 * mm, 20 * mm, 34 * mm])])


st(tabela_postos(gpt, f"Tabela 2a — {MODELOS[0]}: postos das diferenças, da menor para a maior"))
st(Spacer(1, 4))
for rr in (gpt, gem, JUNTOS):
    iguais = Counter(abs(v) for v in rr["d"])
    rep = [v for v, c in sorted(iguais.items()) if c >= 2]
    if rep:
        ex = rep[-1]
        pos = [q + 1 for q, v in enumerate(sorted(abs(x) for x in rr["d"])) if v == ex]
        st(caixa(f"Exemplo de empate: há {iguais[ex]} diferenças de tamanho <b>{br(ex)}</b>, nas "
                 f"posições {', '.join(map(str, pos[:-1]))} e {pos[-1]}  →  "
                 f"({' + '.join(map(str, pos))}) ÷ {len(pos)} = <b>{br(sum(pos) / len(pos))}</b> "
                 f"para cada uma"))
        break
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
    pos_txt = " + ".join(br(rk) for rk, dv in sorted(zip(r["r"], r["d"])) if dv > 0) or "nenhum"
    neg_txt = " + ".join(br(rk) for rk, dv in sorted(zip(r["r"], r["d"])) if dv < 0) or "nenhum"
    st(KeepTogether([P(m, "h2"), caixa([
        f"W<super>+</super> = {pos_txt} = <b>{br(r['wp'])}</b>",
        f"W<super>−</super> = {neg_txt} = <b>{br(r['wm'])}</b>",
        f"Conferência: {br(r['wp'])} + {br(r['wm'])} = {br(r['wp'] + r['wm'])} = "
        f"{r['n1']} × {r['n1'] + 1} ÷ 2 ✓      T = <b>{br(r['T'])}</b>",
    ])]))
st(Spacer(1, 4))
st(P("Quanto mais desequilibrado W<super>+</super> × W<super>−</super>, mais forte a evidência. "
     + " ".join(
         f"No {CURTO[m]}, " + ("todas as diferenças são a favor do few-shot (W<super>−</super> = 0)."
                               if rr["wm"] == 0 else
                               f"o few-shot soma {br(rr['wp'])} contra {br(rr['wm'])}.")
         for m, rr in RES.items())))

# ---- 6. passo 4 ----
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

EX = min(MODELOS, key=lambda m: RES[m]["lado"])
r = RES[EX]
st(P(f"Exemplo completo: {CURTO[EX]} (n′ = {r['n1']})", "h2"))
st(P(f"São 2<super>{r['n1']}</super> = <b>{mil(2 ** r['n1'])}</b> combinações. O resultado "
     f"observado foi T = {br(r['T'])}. Pela simetria da distribuição, basta contar de um lado e "
     f"dobrar. Estas são <b>todas</b> as escolhas de postos “positivos” cuja soma é ≤ {br(r['T'])}:"))
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
st(caixa([f"Um lado: <b>{r['lado']}</b> combinação{'ões' if r['lado'] > 1 else ''}; o outro lado "
          f"(W<super>+</super> ≥ {br(r['n1'] * (r['n1'] + 1) / 2 - r['T'])}) tem o mesmo número "
          f"por simetria.",
          f"p = ({r['lado']} + {r['extremos'] - r['lado']}) ÷ {mil(2 ** r['n1'])} = "
          f"{r['extremos']} ÷ {mil(2 ** r['n1'])} = <b>{br(r['p'], 4)}</b>"]))
if r["T"] == 0:
    st(Spacer(1, 4))
    st(P("Aqui o T é 0: todas as diferenças foram a favor do few-shot. Só existe uma combinação "
         "assim de cada lado (todos os sinais positivos, ou todos negativos), e é por isso que o "
         "p é o menor possível para esse n′: 2 ÷ 2<super>n′</super>."))

linhas = []
for nome, rr in [(m, RES[m]) for m in MODELOS if m != EX] + [("Os dois juntos (20 pares)", JUNTOS)]:
    linhas.append([nome, str(rr["n1"]), mil(2 ** rr["n1"]), br(rr["T"]), mil(rr["extremos"]),
                   f"{mil(rr['extremos'])} ÷ {mil(2 ** rr['n1'])} = <b>{br(rr['p'], 4)}</b>"])
st(KeepTogether([P("Os outros casos, com a mesma conta", "h2"),
                 tabela(["Caso", "n′", "2<super>n′</super>", "T", "Combinações extremas", "p"], linhas,
                        [46 * mm, 12 * mm, 22 * mm, 14 * mm, 30 * mm, 50 * mm])]))

st(P("Alternativa: tabela de valores críticos", "h2"))
st(P("Os livros trazem uma tabela com o <b>T crítico</b>: se o T observado for <b>menor ou "
     "igual</b> a ele, o resultado é significativo a 5% (bicaudal). A tabela supõe que não há "
     "empates, então com postos médios ela é apenas aproximada; por isso aqui se usou o p exato."))
st(tabela(["Caso", "n′", "T observado", "T crítico (5%)", "Conclusão"], [
    [nome.replace(" (20 pares)", ""), str(rr["n1"]), br(rr["T"]), str(CRIT[rr["n1"]]),
     "significativo" if rr["T"] <= CRIT[rr["n1"]] else "não significativo"] for nome, rr in CASOS],
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
st(KeepTogether([
    P("Verificação de robustez: método de Fisher", "h2"),
    P("Em vez de juntar os pares, combinam-se os dois p-valores de cada modelo, que vêm de amostras "
      "independentes (cada modelo gerou os seus testbenches):"),
    caixa([
        "<b>X = −2 × Σ ln(p<sub>i</sub>)</b>, comparado com χ<super>2</super> com 2 × (nº de testes) "
        "= 4 graus de liberdade",
        f"X = −2 × (ln {br(gpt['p'], 4)} + ln {br(gem['p'], 4)}) = <b>{br(X_FISHER, 2)}</b>  →  "
        f"p = <b>{br(P_FISHER, 3)}</b>      (Excel: =DIST.QUIQUA.CD({br(X_FISHER, 2)}; 4))",
    ]),
    fonte("método de combinação de p-valores de Fisher (1932). Conferido com a função "
          "<i>combine_pvalues</i> do SciPy (VIRTANEN et al., 2020)."),
    P("As duas formas chegam à mesma conclusão: " + (
        "abaixo de 0,05." if JUNTOS["p"] < 0.05 and P_FISHER < 0.05 else
        "acima de 0,05." if JUNTOS["p"] >= 0.05 and P_FISHER >= 0.05 else
        "não; ver o texto.")),
]))

# ---- 8. resultado ----
st(PageBreak())
st(P("8. Resultado final", "h1"))
linhas = []
for nome, rr in CASOS:
    linhas.append([nome, str(rr["n1"]), f"{rr['ganha']} / {rr['perde']} / {rr['empata']}",
                   br(rr["wp"]), br(rr["wm"]), f"<b>{br(rr['p'], 3)}</b>",
                   "Sim" if rr["p"] < 0.05 else "Não"])
linhas.append(["Fisher (GPT + Gemini)", "—", "—", "—", "—", f"<b>{br(P_FISHER, 3)}</b>",
               "Sim" if P_FISHER < 0.05 else "Não"])
st(tabela(["Caso", "n′", "FS ganha / perde / empata", "W<super>+</super>", "W<super>−</super>",
           "p", "Significativo?"], linhas,
          [44 * mm, 10 * mm, 34 * mm, 16 * mm, 16 * mm, 18 * mm, 36 * mm]))
st(P("Valores calculados com a média das 2 rodadas. Fonte: elaborado pelo autor a partir da "
     "planilha do experimento.", "nota"))

st(KeepTogether([
    P("Uma rodada × duas rodadas", "h2"),
    tabela(["Caso", "Só a rodada 1", "Só a rodada 2", "Média das 2 rodadas"], [
        [nome.replace(" (20 pares)", ""),
         f"p = {br(a['p'], 3)} ({lado_txt(a)} à frente)", f"p = {br(b['p'], 3)} ({lado_txt(b)} à frente)",
         f"<b>p = {br(c['p'], 3)}</b> ({lado_txt(c)} à frente)"]
        for nome, a, b, c in [
            (MODELOS[0], RODADA[1][1][MODELOS[0]], RODADA[2][1][MODELOS[0]], gpt),
            (MODELOS[1], RODADA[1][1][MODELOS[1]], RODADA[2][1][MODELOS[1]], gem),
            ("Os dois juntos", RODADA[1][2], RODADA[2][2], JUNTOS)]
    ] + [["Fisher (GPT + Gemini)", f"p = {br(RODADA[1][3], 3)}", f"p = {br(RODADA[2][3], 3)}",
          f"<b>p = {br(P_FISHER, 3)}</b>"]], [44 * mm, 43 * mm, 43 * mm, 44 * mm]),
]))

g1, g2 = RODADA[1][1][MODELOS[0]], RODADA[2][1][MODELOS[0]]
bloco = [P("Como interpretar", "h2")]
for m, rr in RES.items():
    a, b = RODADA[1][1][m], RODADA[2][1][m]
    estavel = lado_txt(a) == lado_txt(b)
    bloco.append(item(
        f"<b>{m}:</b> o few-shot ganhou em {rr['ganha']}, perdeu em {rr['perde']} e empatou em "
        f"{rr['empata']} dos 10 circuitos (p = {br(rr['p'], 3)}): "
        + ("<b>significativo</b>." if rr["p"] < 0.05 else "não significativo.")
        + (" O few-shot ficou à frente nas duas rodadas." if estavel and lado_txt(a) == "few-shot"
           else f" O resultado mudou entre as rodadas: na 1ª o {lado_txt(a)} ficou à frente; na 2ª, "
                f"o {lado_txt(b)}." if not estavel else "")))
bloco.append(item(
    f"<b>Com os dois modelos:</b> o few-shot ganha em {JUNTOS['ganha']} e perde em "
    f"{JUNTOS['perde']} dos 20 pares, com p = {br(JUNTOS['p'], 3)}"
    + (": <b>a diferença é significativa</b>." if JUNTOS["p"] < 0.05 else ": não significativo.")
    + f" O método de Fisher {'confirma' if (P_FISHER < 0.05) == (JUNTOS['p'] < 0.05) else 'discorda'} "
    f"(p = {br(P_FISHER, 3)})."))
bloco.append(item(
    "<b>Conclusão:</b> testbenches gerados com exemplos matam "
    + ("significativamente mais mutantes do que os gerados sem exemplos quando os dois modelos são "
       "analisados juntos" if JUNTOS["p"] < 0.05 else "mais mutantes, sem significância")
    + ("; o efeito é claro no " + " e no ".join(CURTO[m] for m, rr in RES.items() if rr["p"] < 0.05)
       + " e instável no " + " e no ".join(CURTO[m] for m, rr in RES.items() if rr["p"] >= 0.05)
       if any(rr["p"] < 0.05 for rr in RES.values()) and any(rr["p"] >= 0.05 for rr in RES.values())
       else "") + "."))
st(KeepTogether(bloco))

# ---- 9. pares ----
st(PageBreak())
st(P("9. Complemento: comparações par a par", "h1"))
st(P("O mesmo teste, aplicado a pares de estratégias que diferem em <b>um único fator</b>. Os "
     "três primeiros pares medem o efeito do exemplo dentro de cada estilo; os quatro últimos, o "
     "efeito do reforço (especialista ou planning) sem e com exemplos. Nos dois modelos juntos, os "
     "p-valores são corrigidos por Holm dentro de cada grupo (3 pares do exemplo; 4 do reforço): "
     "ordena-se do menor para o maior e multiplica-se o 1º pelo número de pares do grupo, o 2º por "
     "um a menos, e assim por diante."))
st(fonte("correção para comparações múltiplas: Holm (1979)."))
linhas = []
for k, (a, b) in enumerate(PARES):
    rj = PAR_J[k]
    linhas.append([f"{a} × {b}", br(PAR[MODELOS[0]][k]["p"], 3), br(PAR[MODELOS[1]][k]["p"], 3),
                   f"{rj['ganha']} / {rj['perde']} / {rj['empata']}", br(rj["p"], 4),
                   f"<b>{br(HOLM_J[k], 4)}</b>" if HOLM_J[k] < 0.05 else br(HOLM_J[k], 4)])
st(tabela(["Par (o segundo ganha?)", "GPT: p", "Gemini: p", "Juntos: ganha / perde / empata",
           "Juntos: p", "Juntos: p corrigido (Holm)"], linhas,
          [38 * mm, 20 * mm, 20 * mm, 38 * mm, 24 * mm, 34 * mm]))
SIG_PAR = [f"{a} × {b}" for k, (a, b) in enumerate(PARES) if HOLM_J[k] < 0.05]
menor_mod = min(PAR[m][k]["p"] for m in MODELOS for k in range(len(PARES)))
st(Spacer(1, 4))
st(P((f"<b>Em cada modelo, nenhum par é significativo</b> (o menor p foi {br(menor_mod, 3)}): com "
      f"poucas diferenças por par, falta resolução. " if menor_mod >= 0.05 else
      f"Em cada modelo, o menor p foi {br(menor_mod, 3)}, ainda sem correção. ")
     + "Com os dois modelos juntos, "
     + (f"<b>{SIG_PAR[0]}</b> continua significativo depois da correção." if len(SIG_PAR) == 1 else
        f"<b>{' e '.join(SIG_PAR)}</b> continuam significativos depois da correção." if SIG_PAR else
        "nenhum par é significativo depois da correção.")
     + " O efeito do exemplo aparece com mais força somando as três variantes de cada família, "
       "que é o contraste planejado (um teste só, sem necessidade de correção)."))

# ---- 10. reproduzir ----
st(P("10. Como reproduzir", "h1"))
st(P("No Excel (português)", "h2"))
st(P("Coloque a soma da família zero-shot na coluna B e a da few-shot na coluna C, com os "
     "circuitos nas linhas 2 a 11 (Tabela 1, já com a média das rodadas). Depois:"))
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
lst = lambda xs: "[" + ", ".join(f"{v:g}" for v in xs) + "]"
st(caixa([
    "from scipy.stats import wilcoxon, PermutationMethod",
    f"zs = {lst(zs)}   # GPT: ZS + EspZS + PlnZS",
    f"fs = {lst(fs)}   # GPT: FS + EspFS + PlnFS",
    "wilcoxon(fs, zs, zero_method=\"wilcox\", method=PermutationMethod(n_resamples=10**6))",
    f"# -> statistic = {gpt['T']:g}, pvalue = {gpt['p']:.4f}",
    "# Para os 20 pares juntos, passe só os pares com d diferente de 0: com eles o",
    "# SciPy enumera todas as combinações; com os zeros, passa de 10**6 e vira sorteio.",
], estilo="codigo"))
st(fonte("biblioteca SciPy (VIRTANEN et al., 2020). <i>PermutationMethod</i> calcula o p exato "
         "pela troca de sinais, inclusive com empates."))

# ---- 11. fontes ----
st(KeepTogether([P("11. De onde vem cada fórmula", "h1"), tabela(["Passo", "Fórmula ou procedimento", "Fonte"], [
    ["0", "Família = soma das 3 variantes; Não passou / Timeout = 0; média das 2 rodadas",
     "Decisão metodológica do trabalho; repetir execuções: Arcuri e Briand (2011)"],
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
    ["9", "Correção de Holm nas comparações par a par", "Holm (1979)"],
    ["—", "Funções do Excel", "Microsoft (2026)"],
    ["—", "Conferência dos cálculos", "SciPy (VIRTANEN et al., 2020)"],
], [14 * mm, 96 * mm, 64 * mm], primeira_esq=False)]))

# ---- 12. texto TCC ----
st(PageBreak())
st(P("12. Texto sugerido para o TCC", "h1"))
st(caixa([
    "<b>Metodologia.</b> Para avaliar o efeito do uso de exemplos, os mutantes mortos (média das "
    "duas rodadas) das três variantes de cada nível do fator shot foram somados por circuito, "
    "formando as famílias zero-shot e few-shot, comparadas pelo teste de Wilcoxon pareado "
    "(WILCOXON, 1945; SIEGEL; CASTELLAN JR., 2006), bicaudal, com p-valor exato. Diferenças nulas "
    "foram descartadas e empates receberam o posto médio. A análise foi feita para cada modelo e "
    "para os dois modelos agrupados; como verificação, os p-valores dos dois modelos foram "
    "combinados pelo método de Fisher (FISHER, 1932).",
    "",
    f"<b>Resultados.</b> Com os dois modelos agrupados (n = 20 pares), a família few-shot matou "
    + ("significativamente mais mutantes que a zero-shot" if JUNTOS["p"] < 0.05 else
       "mais mutantes que a zero-shot, sem significância estatística")
    + f" (few-shot à frente em {JUNTOS['ganha']} pares e atrás em {JUNTOS['perde']}; "
    f"T = {br(JUNTOS['T'])}, p = {br(JUNTOS['p'], 3)}), resultado "
    + ("confirmado" if (P_FISHER < 0.05) == (JUNTOS["p"] < 0.05) else "não confirmado")
    + f" pela combinação de Fisher (p = {br(P_FISHER, 3)}). Por modelo, "
    + "; ".join(f"no {CURTO[m]} o few-shot ganhou em {rr['ganha']} e perdeu em {rr['perde']} "
                f"circuitos (T = {br(rr['T'])}, p = {br(rr['p'], 3)})" for m, rr in RES.items())
    + ". "
    + ("No GPT, o sentido do efeito mudou entre as rodadas (few-shot à frente na primeira e "
       "zero-shot na segunda), o que indica instabilidade das execuções desse modelo."
       if lado_txt(g1) != lado_txt(g2) else ""),
], fundo=colors.white, estilo="corpo"))

secao_referencias(story, ["ARCURI", "FISHER", "HOLLANDER", "HOLM", "MICROSOFT", "PRATT", "SIEGEL",
                          "VIRTANEN", "WILCOXON"])
st(P("Antes de entregar, confira cada referência pelo DOI ou no Google Acadêmico e ajuste ao "
     "padrão ABNT exigido pela sua instituição.", "nota"))

OUT = saida("wilcoxon_passo_a_passo.pdf")
construir(OUT, story, TITULO)
for nome, rr in CASOS:
    print(nome, "n'=%d W+=%s W-=%s T=%s p=%.5f extremos=%d" % (rr["n1"], rr["wp"], rr["wm"], rr["T"],
                                                             rr["p"], rr["extremos"]))
print("Fisher X=%.4f p=%.4f | criticos %s" % (X_FISHER, P_FISHER, CRIT))
print("pares juntos", [(f"{a}x{b}", round(w["p"], 4), round(h, 4)) for (a, b), w, h in zip(PARES, PAR_J, HOLM_J)])
print("PDF:", OUT)
