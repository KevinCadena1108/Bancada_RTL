"""Gera o PDF "Teste de Friedman - passo a passo" a partir da linha "Mutantes" da planilha.

Todos os numeros do PDF sao calculados aqui (nada digitado a mao) e conferidos
contra scipy.stats.friedmanchisquare antes de gerar o arquivo.
Uso: python gerar_pdf_friedman.py <saida.pdf>
"""
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer, TableStyle
from scipy.stats import chi2, friedmanchisquare

from pdf_comum import (AMARELO, CIRCUITOS, CURTO, ESTR, NOME_ESTR, OCRE, PLANILHA, VERDE,
                       VERDE_BORDA, W7, W8, br, caixa, construir, fonte, item, P, postos,
                       secao_referencias, tabela, valores)

TITULO = "Teste de Friedman — passo a passo"


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
                q0=q0, grupos=grupos, T=T, C=C, Q=Q, p=p, n=n, k=k)


RES = {m: calcular(valores(m)) for m in PLANILHA}
AGRUPADO = calcular(valores("GPT-5.6 Luna") + valores("Gemini 3.5 Flash-Lite"))
CRITICO = chi2.ppf(0.95, 5)

story = []
st = story.append
gpt, gem = RES["GPT-5.6 Luna"], RES["Gemini 3.5 Flash-Lite"]

st(P(TITULO, "titulo"))
st(P("Comparação das 6 estratégias de prompt nos testbenches gerados pelo "
     "GPT-5.6 Luna e pelo Gemini 3.5 Flash-Lite", "sub"))
st(Spacer(1, 10))

# ---- resumo ----
st(caixa([
    "<b>Resultado em uma linha:</b> nos dois modelos, o Zero-shot ficou em último e o "
    "Especialista Few-shot em primeiro, mas as diferenças entre as 6 estratégias "
    "<b>não são estatisticamente significativas</b>.",
    f"<b>GPT-5.6 Luna:</b> χ<super>2</super>(5) = {br(gpt['Q'], 2)}; p = {br(gpt['p'], 3)}",
    f"<b>Gemini 3.5 Flash-Lite:</b> χ<super>2</super>(5) = {br(gem['Q'], 2)}; p = {br(gem['p'], 3)}",
], fundo=VERDE, borda=VERDE_BORDA))

st(P("1. O que o teste responde", "h1"))
st(P("O teste de Friedman responde a uma pergunta: <b>as seis estratégias de prompt produzem "
     "testbenches de qualidade diferente, ou as diferenças observadas poderiam ser obra do "
     "acaso?</b>"))
st(P("Pense num campeonato com <b>10 corridas</b> (os circuitos) e <b>6 corredores</b> (as "
     "estratégias). Em cada corrida, cada estratégia recebe uma posição, de 1 (pior) a 6 "
     "(melhor). No fim, calcula-se a posição média de cada uma. O teste verifica se essas "
     "médias estão afastadas o bastante para não serem explicadas por sorte."))
st(P("O cálculo é feito <b>separadamente para cada modelo</b>, sempre comparando as estratégias "
     "entre si. O teste <b>não compara</b> o GPT com o Gemini."))
st(fonte("teste proposto por Friedman (1937); procedimento descrito em Siegel e Castellan Jr. "
         "(2006) como “análise de variância de dois fatores de Friedman por postos”. Uso para "
         "comparar vários métodos sobre vários casos: Demšar (2006)."))
st(P("Notação usada no documento", "h2"))
st(tabela(["Símbolo", "Significado", "Valor"], [
    ["n", "número de circuitos (blocos)", "10"],
    ["k", "número de estratégias (tratamentos)", "6"],
    ["R<sub>j</sub>", "soma dos postos da estratégia j nos 10 circuitos", "calculado no passo 2"],
    ["t", "tamanho de um grupo de empate dentro de um circuito", "calculado no passo 4"],
], [22 * mm, 102 * mm, 50 * mm]))
st(P("Abreviações das estratégias: ZS = Zero-shot · FS = Few-shot · EspZS = Especialista "
     "Zero-shot · EspFS = Especialista Few-shot · PlnZS = Planning Zero-shot · PlnFS = "
     "Planning Few-shot.", "nota"))

# ---- passo 0: dados ----
st(P("2. Passo 0 — Converter a planilha em números", "h1"))
st(P("Para cada circuito, usa-se a linha <b>“Mutantes”</b> da planilha. Cada célula vira o "
     "número de mutantes mortos:"))
st(item("“4/4” vira <b>4</b>, “3/4” vira <b>3</b>, e assim por diante;"))
st(item("“Não passou” e “Timeout” viram <b>0</b>: um testbench que reprova o circuito "
        "original não detecta defeito nenhum de forma válida."))
st(fonte("decisão metodológica deste trabalho (não é uma fórmula da literatura): é o mesmo "
         "critério do “score de mutação efetivo” usado na análise da planilha."))
st(P("O EAS-28 fica de fora porque não tem resultados no Gemini; assim os dois modelos são "
     "comparados nos mesmos 10 circuitos.", "nota"))
for m, curto in CURTO.items():
    linhas = []
    for nome, txt, val in zip(CIRCUITOS, PLANILHA[m], RES[m]["valores"]):
        linhas.append([nome] + [f"{c}<br/><b>{v}</b>" for c, v in zip(txt, val)])
    st(KeepTogether([P(f"Tabela 1{'a' if curto == 'GPT' else 'b'} — {m}: planilha (em cima) e "
                       f"valor usado (em negrito)", "legenda"),
                     tabela(["Circuito"] + ESTR, linhas, W7)]))

# ---- passo 1: postos ----
st(PageBreak())
st(P("3. Passo 1 — Dar postos dentro de cada circuito", "h1"))
st(P("Em <b>cada circuito, separadamente</b>, as seis estratégias são ordenadas do menor para o "
     "maior número de mutantes mortos. O menor recebe posto 1 e o maior recebe posto 6."))
st(P("<b>Regra do empate:</b> estratégias com o mesmo valor ocupam várias posições da fila, e "
     "nenhuma delas foi pior que a outra. Por isso todas recebem a <b>média das posições que "
     "ocupam</b> (o “posto médio”)."))
st(fonte("ordenação por postos dentro de cada bloco e posto médio para empates: Friedman (1937); "
         "Siegel e Castellan Jr. (2006)."))

ex_val = gem["valores"][0]
ex_rk = gem["postos"][0]
ordem = sorted(range(6), key=lambda i: ex_val[i])
st(P("Exemplo: Fsm serialdp no Gemini", "h2"))
st(P("Valores: " + ", ".join(f"{e} = {v}" for e, v in zip(ESTR, ex_val)) + ". Colocando em fila, "
     "do menor para o maior:"))
st(tabela(["", "1ª", "2ª", "3ª", "4ª", "5ª", "6ª"], [
    ["Valor"] + [str(ex_val[i]) for i in ordem],
    ["Estratégia"] + [ESTR[i] for i in ordem],
    ["Posto final"] + [f"<b>{br(ex_rk[i])}</b>" for i in ordem],
], W7, destacar_ultima=True))
st(Spacer(1, 4))
st(caixa([
    "Os dois <b>0</b> ocupam as posições 1 e 2  →  (1 + 2) ÷ 2 = <b>1,5</b> para cada um",
    "Os quatro <b>4</b> ocupam as posições 3, 4, 5 e 6  →  (3 + 4 + 5 + 6) ÷ 4 = 18 ÷ 4 = <b>4,5</b> "
    "para cada um",
]))
st(P("<b>Conferência:</b> em qualquer circuito, os seis postos somam sempre "
     "1 + 2 + 3 + 4 + 5 + 6 = k × (k + 1) ÷ 2 = <b>21</b>. No exemplo: "
     "1,5 + 4,5 + 4,5 + 4,5 + 1,5 + 4,5 = 21."))
st(P("As tabelas abaixo mostram, em cada célula, o <b>valor → posto</b>. A última coluna confere "
     "que cada linha soma 21."))
for m, curto in CURTO.items():
    r = RES[m]
    linhas = []
    for nome, v, rk in zip(CIRCUITOS, r["valores"], r["postos"]):
        linhas.append([nome] + [f"{a} → <b>{br(b)}</b>" for a, b in zip(v, rk)] + [br(sum(rk))])
    linhas.append(["<b>Soma (R<sub>j</sub>)</b>"] + [f"<b>{br(x)}</b>" for x in r["R"]]
                  + [f"<b>{br(sum(r['R']))}</b>"])
    st(KeepTogether([P(f"Tabela 2{'a' if curto == 'GPT' else 'b'} — {m}: valor → posto",
                       "legenda"),
                     tabela(["Circuito"] + ESTR + ["Soma da linha"], linhas, W8,
                            destacar_ultima=True)]))

# ---- passo 2: posto medio ----
st(P("4. Passo 2 — Somar os postos e calcular o posto médio", "h1"))
st(P("Soma-se a coluna de cada estratégia (R<sub>j</sub>, última linha das tabelas 2a e 2b) e "
     "divide-se pelo número de circuitos (n = 10). O resultado é o <b>posto médio</b>: quanto "
     "maior, melhor a estratégia se saiu na comparação com as outras."))
st(caixa("<b>Posto médio da estratégia j = R<sub>j</sub> ÷ n</b>"))
st(fonte("Demšar (2006), que apresenta o teste de Friedman a partir dos postos médios."))
linhas = []
for j, e in enumerate(ESTR):
    linhas.append([NOME_ESTR[e],
                   br(gpt["R"][j]), f"{br(gpt['R'][j])} ÷ 10 = <b>{br(gpt['medias'][j], 2)}</b>",
                   br(gem["R"][j]), f"{br(gem['R'][j])} ÷ 10 = <b>{br(gem['medias'][j], 2)}</b>"])
linhas.append(["<b>Total</b>", f"<b>{br(sum(gpt['R']))}</b>", "",
               f"<b>{br(sum(gem['R']))}</b>", ""])
st(tabela(["Estratégia", "GPT: R<sub>j</sub>", "GPT: posto médio",
           "Gemini: R<sub>j</sub>", "Gemini: posto médio"],
          linhas, [46 * mm, 22 * mm, 42 * mm, 22 * mm, 42 * mm], destacar_ultima=True))
st(P("<b>Conferência:</b> a soma de todos os postos tem que ser n × k × (k + 1) ÷ 2 = "
     "10 × 6 × 7 ÷ 2 = <b>210</b>, como na linha Total. Se nenhuma estratégia fosse melhor, "
     "todos os postos médios ficariam perto de (k + 1) ÷ 2 = <b>3,5</b>."))

# ---- passo 3: Q sem correcao ----
st(PageBreak())
st(P("5. Passo 3 — Calcular a estatística Q (sem correção)", "h1"))
st(P("A estatística de Friedman mede o quanto as somas de postos se afastam do que se "
     "esperaria se todas as estratégias fossem iguais:"))
st(caixa("<b>Q<sub>0</sub> = [ 12 ÷ (n · k · (k + 1)) ] × ΣR<sub>j</sub><super>2</super>  −  "
         "3 · n · (k + 1)</b>"))
st(fonte("Friedman (1937); Siegel e Castellan Jr. (2006). A mesma estatística escrita com os "
         "postos médios aparece em Demšar (2006)."))
st(P("Com n = 10 e k = 6: 12 ÷ (10 × 6 × 7) = <b>12 ÷ 420</b> e 3 × 10 × 7 = <b>210</b>."))
for m, curto in CURTO.items():
    r = RES[m]
    quad = " + ".join(f"{br(x)}<super>2</super>" for x in r["R"])
    termos = " + ".join(br(x * x) for x in r["R"])
    sq = br(r["soma_quad"], 2 if r["soma_quad"] % 1 else 0)
    st(P(m, "h2"))
    st(caixa([
        f"ΣR<sub>j</sub><super>2</super> = {quad}",
        f"ΣR<sub>j</sub><super>2</super> = {termos} = <b>{sq}</b>",
        f"Q<sub>0</sub> = 12 ÷ 420 × {sq} − 210 = "
        f"{br(12 / 420 * r['soma_quad'], 4)} − 210 = <b>{br(r['q0'], 4)}</b>",
    ]))

# ---- passo 4: empates ----
st(P("6. Passo 4 — Corrigir os empates", "h1"))
st(P("Como há muitos empates (vários “4/4” e vários “Não passou” no mesmo circuito), o Q<sub>0</sub> "
     "é corrigido. Para cada grupo de valores iguais dentro de um circuito, calcula-se "
     "<b>t<super>3</super> − t</b>, onde t é quantas estratégias empataram naquele valor. "
     "Valores que aparecem uma só vez não contam (1<super>3</super> − 1 = 0)."))
st(caixa(["<b>C = 1 − ΣT ÷ (n · (k<super>3</super> − k))</b>     com     n · (k<super>3</super> − k) "
          "= 10 × (216 − 6) = <b>2.100</b>",
          "<b>Q = Q<sub>0</sub> ÷ C</b>"]))
st(fonte("correção para empates do teste de Friedman em Hollander, Wolfe e Chicken (2014); é a "
         "mesma correção aplicada pela função <i>friedmanchisquare</i> do SciPy (VIRTANEN et al., "
         "2020), usada para conferir os números deste documento."))
for m, curto in CURTO.items():
    r = RES[m]
    linhas = []
    for nome, gr in zip(CIRCUITOS, r["grupos"]):
        desc = "; ".join(f"valor {val}: t = {t} → {t}<super>3</super> − {t} = {tt}" for val, t, tt in gr)
        linhas.append([nome, desc or "sem empates", str(sum(g[2] for g in gr))])
    linhas.append(["<b>Total (ΣT)</b>", "", f"<b>{r['T']}</b>"])
    st(KeepTogether([
        P(f"Tabela 3{'a' if curto == 'GPT' else 'b'} — {m}: empates por circuito", "legenda"),
        tabela(["Circuito", "Grupos de empate", "Σ(t<super>3</super> − t)"], linhas,
               [34 * mm, 112 * mm, 28 * mm], destacar_ultima=True),
        Spacer(1, 4),
        caixa([f"C = 1 − {r['T']} ÷ 2.100 = 1 − {br(r['T'] / 2100, 4)} = <b>{br(r['C'], 4)}</b>",
               f"Q = {br(r['q0'], 4)} ÷ {br(r['C'], 4)} = <b>{br(r['Q'], 2)}</b>"]),
    ]))

# ---- passo 5: p-valor ----
st(P("7. Passo 5 — Calcular o p-valor", "h1"))
st(P("O Q é comparado com a distribuição <b>qui-quadrado (χ<super>2</super>)</b> com "
     "<b>k − 1 = 5 graus de liberdade</b>. O p-valor é a chance de obter um Q desse tamanho "
     "ou maior <b>se as seis estratégias fossem todas iguais</b>."))
st(caixa("<b>p = P( χ<super>2</super> com k − 1 graus de liberdade ≥ Q )</b>"))
st(fonte("aproximação qui-quadrado com k − 1 graus de liberdade: Friedman (1937); Siegel e "
         "Castellan Jr. (2006), que também trazem a tabela de valores críticos. Função do Excel: "
         "Microsoft (2026)."))
st(caixa(["No Excel em português:",
          f"=DIST.QUIQUA.CD({br(gpt['Q'], 2)}; 5)   →   {br(gpt['p'], 3)}   (GPT)",
          f"=DIST.QUIQUA.CD({br(gem['Q'], 2)}; 5)   →   {br(gem['p'], 3)}   (Gemini)"],
         estilo="codigo"))
st(P(f"<b>Referências para ler o Q:</b> se as estratégias fossem iguais, o Q ficaria em torno "
     f"de <b>5</b> (o valor médio de um χ<super>2</super> é igual ao seu número de graus de "
     f"liberdade). Para ser significativo a 5%, o Q precisaria passar de <b>{br(CRITICO, 2)}</b> "
     f"(valor crítico do χ<super>2</super> com 5 graus de liberdade)."))
st(tabela(["Modelo", "Q = χ<super>2</super>(5)", "Valor crítico (5%)", "p-valor", "Significativo?"], [
    ["GPT-5.6 Luna", br(gpt["Q"], 2), br(CRITICO, 2), br(gpt["p"], 3), "Não (p ≥ 0,05)"],
    ["Gemini 3.5 Flash-Lite", br(gem["Q"], 2), br(CRITICO, 2), br(gem["p"], 3), "Não (p ≥ 0,05)"],
], [44 * mm, 30 * mm, 34 * mm, 26 * mm, 40 * mm]))

# ---- resultado ----
st(P("8. Resultado final", "h1"))
linhas = []
for j, e in enumerate(ESTR):
    linhas.append([NOME_ESTR[e], br(gpt["medias"][j], 2), br(gem["medias"][j], 2)])
linhas.append(["<b>χ<super>2</super>(5)</b>", f"<b>{br(gpt['Q'], 2)}</b>", f"<b>{br(gem['Q'], 2)}</b>"])
linhas.append(["<b>p-valor</b>", f"<b>{br(gpt['p'], 3)}</b>", f"<b>{br(gem['p'], 3)}</b>"])
t = tabela(["Estratégia", "GPT-5.6 Luna<br/>(posto médio)", "Gemini 3.5 Flash-Lite<br/>(posto médio)"],
           linhas, [70 * mm, 52 * mm, 52 * mm])
t.setStyle(TableStyle([("BACKGROUND", (0, -2), (-1, -1), AMARELO)]))
st(t)
st(P("Posto médio: quanto maior, melhor. Fonte: elaborado pelo autor a partir da planilha do "
     "experimento.", "nota"))

bloco = []
bloco.append(P("Como interpretar", "h2"))
bloco.append(item("<b>A ordem:</b> o Zero-shot ficou em último nos dois modelos (2,70). O "
                  "Especialista Few-shot ficou em primeiro nos dois (4,00 no GPT, empatado com o "
                  "Planning Few-shot, e 4,20 no Gemini)."))
bloco.append(item(f"<b>O veredito:</b> os p-valores ({br(gpt['p'], 3)} e {br(gem['p'], 3)}) são "
                  f"maiores que 0,05. Há {br(100 * gpt['p'], 1)}% (GPT) e {br(100 * gem['p'], 1)}% "
                  f"(Gemini) de chance de ver diferenças desse tamanho só por acaso. Por isso "
                  f"<b>não se pode afirmar</b> que alguma das seis estratégias é diferente das outras."))
bloco.append(item(f"<b>Por quê:</b> os Q ({br(gpt['Q'], 2)} e {br(gem['Q'], 2)}) estão perto de 5, "
                  f"o valor típico do acaso, e longe de {br(CRITICO, 2)}. Com 10 circuitos e uma "
                  f"execução por estratégia, as diferenças entre as posições médias ainda são "
                  f"pequenas demais."))
bloco.append(item("<b>Não significativo não quer dizer sem efeito:</b> a ordem se repete nos dois "
                  "modelos (variantes few-shot à frente das zero-shot). O teste só diz que, com "
                  "esta amostra, isso ainda não basta para descartar o acaso."))
bloco.append(item(f"<b>Os dois modelos juntos</b> (20 blocos): χ<super>2</super>(5) = "
                  f"{br(AGRUPADO['Q'], 2)}; p = {br(AGRUPADO['p'], 3)}. Com mais dados o p cai, mas "
                  f"continua acima de 0,05."))
bloco.append(Spacer(1, 4))
bloco.append(caixa("<b>Próximo passo:</b> o contraste específico “família few-shot × família "
                   "zero-shot” é avaliado com o teste de Wilcoxon pareado, onde a diferença "
                   "aparece com clareza.", fundo=AMARELO, borda=OCRE))
st(KeepTogether(bloco))

# ---- reproduzir ----
st(PageBreak())
st(P("9. Como reproduzir", "h1"))
st(P("No Excel (português)", "h2"))
st(P("Monte uma tabela com os circuitos nas linhas 2 a 11 e as estratégias nas colunas B a G "
     "(os valores da Tabela 1). Depois:"))
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
st(fonte("funções ORDEM.MÉD, SOMAQUAD, SOMARPRODUTO, CONT.SE e DIST.QUIQUA.CD: Microsoft (2026)."))
st(P("Em Python", "h2"))
st(caixa([
    "from scipy.stats import friedmanchisquare",
    "zs, fs = [4, 3, 4, 0, 4, 0, 0, 0, 0, 0], [4, 3, 4, 3, 4, 2, 3, 0, 0, 3]   # GPT",
    "# ... uma lista de 10 valores para cada estratégia, na ordem dos circuitos",
    "friedmanchisquare(zs, fs, esp_zs, esp_fs, pln_zs, pln_fs)",
    f"# GPT -> statistic = {br(gpt['Q'], 4).replace(',', '.')}, pvalue = {br(gpt['p'], 4).replace(',', '.')}",
], estilo="codigo"))
st(fonte("biblioteca SciPy (VIRTANEN et al., 2020); a função já aplica a correção de empates. "
         "Os valores deste documento foram conferidos contra ela."))

# ---- de onde vem cada formula ----
st(P("10. De onde vem cada fórmula", "h1"))
st(tabela(["Passo", "Fórmula ou procedimento", "Fonte"], [
    ["0", "Não passou / Timeout = 0 mutantes mortos", "Decisão metodológica do trabalho"],
    ["1", "Postos dentro de cada circuito; empate = média das posições",
     "Friedman (1937); Siegel e Castellan Jr. (2006)"],
    ["2", "Posto médio = R<sub>j</sub> ÷ n", "Demšar (2006)"],
    ["3", "Q<sub>0</sub> = 12 ÷ (n·k·(k+1)) × ΣR<sub>j</sub><super>2</super> − 3·n·(k+1)",
     "Friedman (1937); Siegel e Castellan Jr. (2006)"],
    ["4", "C = 1 − Σ(t<super>3</super> − t) ÷ (n·(k<super>3</super> − k)); Q = Q<sub>0</sub> ÷ C",
     "Hollander, Wolfe e Chicken (2014)"],
    ["5", "p = P(χ<super>2</super><sub>k−1</sub> ≥ Q); valor crítico 11,07",
     "Friedman (1937); Siegel e Castellan Jr. (2006)"],
    ["—", "Funções do Excel", "Microsoft (2026)"],
    ["—", "Conferência dos cálculos", "SciPy (VIRTANEN et al., 2020)"],
], [14 * mm, 96 * mm, 64 * mm], primeira_esq=False))

# ---- texto TCC ----
st(PageBreak())
st(P("11. Texto sugerido para o TCC", "h1"))
st(caixa([
    "<b>Metodologia.</b> Para avaliar se as seis estratégias de prompt diferem quanto à qualidade "
    "dos testbenches, aplicou-se o teste de Friedman (FRIEDMAN, 1937; SIEGEL; CASTELLAN JR., "
    "2006), separadamente para cada modelo. A variável analisada foi o número de mutantes mortos "
    "por circuito (0 a 4), atribuindo-se zero aos casos em que o testbench não passou no circuito "
    "original ou excedeu o tempo limite. Cada circuito foi tratado como um bloco, as estratégias "
    "foram ordenadas por postos dentro de cada circuito (empates recebendo o posto médio) e a "
    "estatística foi calculada com correção para empates (HOLLANDER; WOLFE; CHICKEN, 2014), ao "
    "nível de significância de 5%.",
    "",
    f"<b>Resultados.</b> O teste de Friedman não indicou diferença estatisticamente significativa "
    f"entre as seis estratégias (GPT: χ<super>2</super>(5) = {br(gpt['Q'], 2)}, p = {br(gpt['p'], 3)}; "
    f"Gemini: χ<super>2</super>(5) = {br(gem['Q'], 2)}, p = {br(gem['p'], 3)}). Ainda assim, a "
    f"ordenação dos postos médios foi consistente: o Zero-shot obteve o menor posto médio nos "
    f"dois modelos (2,70) e o Especialista Few-shot, o maior (4,00 no GPT e 4,20 no Gemini).",
], fundo=colors.white, estilo="corpo"))

secao_referencias(story, ["DEMSAR", "FRIEDMAN", "HOLLANDER", "MICROSOFT", "SIEGEL", "VIRTANEN"])
st(P("Antes de entregar, confira cada referência pelo DOI ou no Google Acadêmico e ajuste ao "
     "padrão ABNT exigido pela sua instituição.", "nota"))

construir(sys.argv[1], story, TITULO)
for m in RES:
    print(m, "Q=%.4f p=%.4f medias=%s" % (RES[m]["Q"], RES[m]["p"], RES[m]["medias"]))
print("agrupado Q=%.4f p=%.4f | critico=%.4f" % (AGRUPADO["Q"], AGRUPADO["p"], CRITICO))
print("PDF:", sys.argv[1])
