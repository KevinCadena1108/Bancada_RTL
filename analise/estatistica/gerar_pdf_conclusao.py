"""Gera o PDF "Conclusão da análise estatística" (Friedman + Wilcoxon juntos).

Os numeros sao recalculados com o SciPy a partir da linha "Mutantes" da planilha (os mesmos
valores dos PDFs de Friedman e Wilcoxon, que conferem seus calculos contra o SciPy).
Uso: python gerar_pdf_conclusao.py <saida.pdf>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer, TableStyle
from scipy.stats import PermutationMethod, combine_pvalues, friedmanchisquare, rankdata, wilcoxon

from pdf_comum import (AMARELO, CIRCUITOS, CURTO, ESTR, NOME_ESTR, OCRE, PLANILHA, VERDE,
                       VERDE_BORDA, br, caixa, construir, fonte, item, P, secao_referencias,
                       tabela, valores)

TITULO = "Conclusão da análise estatística"
MODELOS = list(PLANILHA)
ZS_FAM, FS_FAM = [0, 2, 4], [1, 3, 5]
VERMELHO = colors.HexColor("#FDECEA")
VERMELHO_BORDA = colors.HexColor("#C62828")


def wilc(x, y):
    """Wilcoxon bicaudal exato (zeros descartados); retorna (ganha, perde, empata, T, p)."""
    d = [b - a for a, b in zip(x, y)]
    nz = [i for i, v in enumerate(d) if v != 0]
    ganha, perde = sum(v > 0 for v in d), sum(v < 0 for v in d)
    if not nz:
        return ganha, perde, len(d), 0.0, 1.0
    r = wilcoxon([y[i] for i in nz], [x[i] for i in nz], zero_method="wilcox",
                 method=PermutationMethod(n_resamples=max(10 ** 6, 2 ** len(nz))))
    return ganha, perde, len(d) - len(nz), float(r.statistic), float(r.pvalue)


def coluna(vals, j):
    return [linha[j] for linha in vals]


VAL = {m: valores(m) for m in MODELOS}
JUNTOS = VAL[MODELOS[0]] + VAL[MODELOS[1]]

# Friedman: estatistica, p e postos medios
FRI = {}
for nome, vals in list(VAL.items()) + [("juntos", JUNTOS)]:
    sp = friedmanchisquare(*[coluna(vals, j) for j in range(6)])
    rk = [rankdata(linha) for linha in vals]
    medios = [sum(r[j] for r in rk) / len(rk) for j in range(6)]
    FRI[nome] = dict(Q=float(sp.statistic), p=float(sp.pvalue), medios=medios)

# Wilcoxon das familias
def familias(vals):
    return ([sum(l[j] for j in ZS_FAM) for l in vals], [sum(l[j] for j in FS_FAM) for l in vals])


WIL = {m: wilc(*familias(VAL[m])) for m in MODELOS}
WIL["juntos"] = wilc(*familias(JUNTOS))
FISHER = combine_pvalues([WIL[m][4] for m in MODELOS], method="fisher")

# pares de um fator
PARES_SHOT = [("ZS", "FS"), ("EspZS", "EspFS"), ("PlnZS", "PlnFS")]
PARES_REF = [("ZS", "EspZS"), ("ZS", "PlnZS"), ("FS", "EspFS"), ("FS", "PlnFS")]
PAR = {m: {(a, b): wilc(coluna(VAL[m], ESTR.index(a)), coluna(VAL[m], ESTR.index(b)))
           for a, b in PARES_SHOT + PARES_REF} for m in MODELOS}
MIN_PAR = min(v[4] for m in MODELOS for v in PAR[m].values())
MIN_REF = min(PAR[m][par][4] for m in MODELOS for par in PARES_REF)
MIN_ESPFS = min(PAR[m][("FS", "EspFS")][4] for m in MODELOS)

# descritivo: aprovados e score efetivo (mortos / 40)
DESC = {}
for m in MODELOS:
    DESC[m] = {e: (sum(1 for l in PLANILHA[m] if l[j].endswith("/4")),
                   100 * sum(coluna(VAL[m], j)) / 40) for j, e in enumerate(ESTR)}

# conferencias contra os valores dos PDFs anteriores
assert round(FRI[MODELOS[0]]["Q"], 2) == 6.12 and round(FRI[MODELOS[1]]["Q"], 2) == 5.31
assert round(WIL["juntos"][4], 3) == 0.009 and round(FISHER.pvalue, 3) == 0.044

g, m2 = MODELOS
fg, fm, fj = FRI[g], FRI[m2], FRI["juntos"]
wg, wm, wj = WIL[g], WIL[m2], WIL["juntos"]


def media_fam(medios, fam):
    return sum(medios[j] for j in fam) / 3


story = []
st = story.append
st(P(TITULO, "titulo"))
st(P("O que os testes de Friedman e Wilcoxon dizem, juntos, sobre as estratégias de prompt na "
     "geração de testbenches por LLM", "sub"))
st(Spacer(1, 10))
st(caixa([
    "<b>Conclusão em uma frase:</b> usar exemplos no prompt (few-shot) faz os LLMs gerarem "
    "testbenches que detectam significativamente mais defeitos (com os dois modelos analisados "
    "juntos, e com a mesma tendência em cada um); já a persona de especialista e o planejamento "
    "não mostraram efeito comprovado, e nenhuma das seis estratégias se destaca sozinha das demais.",
], fundo=VERDE, borda=VERDE_BORDA))

# ---- 1 ----
st(P("1. As perguntas e as respostas", "h1"))
st(tabela(["Teste", "Pergunta", "Resultado", "Resposta"], [
    ["Friedman (6 estratégias)", "Alguma das seis estratégias é diferente das outras?",
     f"GPT p = {br(fg['p'], 3)}<br/>Gemini p = {br(fm['p'], 3)}<br/>Juntos p = {br(fj['p'], 3)}",
     "<b>Não</b> dá para afirmar"],
    ["Wilcoxon (família FS × ZS)", "Ter exemplos no prompt melhora o testbench?",
     f"GPT p = {br(wg[4], 3)}<br/>Gemini p = {br(wm[4], 3)}<br/>Juntos p = {br(wj[4], 3)}<br/>"
     f"Fisher p = {br(FISHER.pvalue, 3)}",
     "<b>Sim</b> (significativo com os dois modelos juntos)"],
    ["Wilcoxon (pares de 1 fator)", "Algum par específico de estratégias difere?",
     f"Todos p ≥ {br(MIN_PAR, 3)}", "<b>Não</b> dá para afirmar"],
], [36 * mm, 50 * mm, 46 * mm, 42 * mm]))
st(P("Valor analisado nos três casos: mutantes mortos por circuito (0 a 4), com “Não passou” e "
     "“Timeout” valendo 0. Nível de significância: 5%. Detalhes de cada cálculo nos PDFs "
     "“Teste de Friedman — passo a passo” e “Teste de Wilcoxon pareado — passo a passo”.", "nota"))

# ---- 2 ----
st(P("2. Como os dois resultados se encaixam", "h1"))
st(P("Os resultados <b>não se contradizem</b>. Eles respondem a perguntas diferentes:"))
st(item("O <b>Friedman</b> olha as seis estratégias ao mesmo tempo e pergunta se alguma se destaca. "
        "Ele não encontrou uma vencedora clara."))
st(item("O <b>Wilcoxon</b> faz um único confronto direto, planejado antes: com exemplos × sem "
        "exemplos. Nesse confronto a diferença aparece."))
st(P("A explicação é que as seis estratégias formam <b>dois grupos</b>: as três com exemplos e as "
     "três sem. Dentro de cada grupo elas são parecidas entre si. Quando o Friedman mistura as "
     "seis, a diferença entre os grupos se dilui nas comparações sem importância. Quando o "
     "Wilcoxon compara os dois grupos diretamente, ela fica visível."))
st(P("Os postos médios do Friedman mostram esses dois grupos:"))
linhas = []
for zs, fs in PARES_SHOT:
    jz, jf = ESTR.index(zs), ESTR.index(fs)
    lin = [f"{NOME_ESTR[zs]} → {NOME_ESTR[fs]}"]
    for m in MODELOS:
        a, b = FRI[m]["medios"][jz], FRI[m]["medios"][jf]
        lin.append(f"{br(a, 2)} → {br(b, 2)}  {'✓' if b > a else '✗'}")
    linhas.append(lin)
linhas.append(["<b>Média da família: zero-shot → few-shot</b>"] + [
    f"<b>{br(media_fam(FRI[m]['medios'], ZS_FAM), 2)} → {br(media_fam(FRI[m]['medios'], FS_FAM), 2)}</b>"
    for m in MODELOS])
st(tabela(["Sem exemplo → com exemplo (posto médio)", "GPT-5.6 Luna", "Gemini 3.5 Flash-Lite"],
          linhas, [74 * mm, 50 * mm, 50 * mm], destacar_ultima=True))
nao = [(m, zs, fs) for m in MODELOS for zs, fs in PARES_SHOT
       if FRI[m]["medios"][ESTR.index(fs)] <= FRI[m]["medios"][ESTR.index(zs)]]
excecao = "; ".join(f"{CURTO[m]}: {NOME_ESTR[zs]} → {NOME_ESTR[fs]}" for m, zs, fs in nao)
st(P(f"Em {6 - len(nao)} das 6 comparações, a versão com exemplo ficou à frente da versão sem "
     f"exemplo. A exceção ({excecao}) é a única em que adicionar exemplos não melhorou o posto "
     f"médio."))
st(fonte("postos médios do teste de Friedman (FRIEDMAN, 1937; SIEGEL; CASTELLAN JR., 2006); "
         "contraste de famílias pelo teste de Wilcoxon (WILCOXON, 1945)."))

# ---- 3 ----
st(PageBreak())
st(P("3. O que se pode concluir", "h1"))
st(P("Pode afirmar (comprovado estatisticamente)", "h2"))
st(caixa([
    f"• <b>O few-shot melhora a qualidade dos testbenches.</b> Os testbenches gerados com exemplos "
    f"mataram mais mutantes que os gerados sem exemplos (Wilcoxon com os dois modelos: few-shot "
    f"ganhou em {wj[0]} e perdeu em {wj[1]} dos 20 pares, T = {br(wj[3])}, p = {br(wj[4], 3)}; "
    f"combinação de Fisher: p = {br(FISHER.pvalue, 3)}).",
    f"• <b>O efeito tem a mesma direção nos dois modelos.</b> O few-shot ganhou em {wg[0]} circuitos "
    f"no GPT e em {wm[0]} no Gemini, com p = {br(wg[4], 3)} em cada um.",
], fundo=VERDE, borda=VERDE_BORDA, estilo="corpo"))
st(P("Pode sugerir (tendência consistente, sem significância)", "h2"))
dg, dm = DESC[g], DESC[m2]
st(caixa([
    f"• <b>Zero-shot puro é a pior estratégia:</b> último posto médio nos dois modelos "
    f"({br(fg['medios'][0], 2)}) e menor score efetivo ({br(dg['ZS'][1], 1)}% no GPT, "
    f"{br(dm['ZS'][1], 1)}% no Gemini).",
    f"• <b>As variantes few-shot ficam no topo:</b> o Especialista Few-shot tem o maior posto médio "
    f"nos dois modelos ({br(fg['medios'][3], 2)} no GPT, empatado com o Planning Few-shot, e "
    f"{br(fm['medios'][3], 2)} no Gemini).",
    f"• <b>Persona e planejamento parecem ajudar mais quando não há exemplos:</b> no GPT, o score "
    f"efetivo sobe de {br(dg['ZS'][1], 1)}% (Zero-shot) para {br(dg['EspZS'][1], 1)}% (Especialista) "
    f"e {br(dg['PlnZS'][1], 1)}% (Planning); com exemplos, sobe só de {br(dg['FS'][1], 1)}% para "
    f"{br(dg['EspFS'][1], 1)}% e {br(dg['PlnFS'][1], 1)}%. É uma observação descritiva.",
], fundo=AMARELO, borda=OCRE, estilo="corpo"))
st(P("Não pode afirmar", "h2"))
st(caixa([
    f"• <b>Que o Especialista Few-shot é a melhor estratégia.</b> Ele matou só 2 mutantes a mais "
    f"(em 40) que o Few-shot simples nos dois modelos, e a comparação entre os dois não é "
    f"significativa (p ≥ {br(MIN_ESPFS, 2)}).",
    f"• <b>Que a persona de especialista ou o planejamento melhoram o testbench.</b> Nenhuma "
    f"comparação com a versão base foi significativa (p ≥ {br(MIN_REF, 2)}).",
    "• <b>Que um modelo é melhor que o outro.</b> Os testes comparam estratégias dentro de cada "
    "modelo, não os modelos entre si. As diferenças entre GPT e Gemini (seção 5) são descritivas.",
], fundo=VERMELHO, borda=VERMELHO_BORDA, estilo="corpo"))
st(fonte("“não significativo” indica evidência insuficiente, não ausência de efeito "
         "(WASSERSTEIN; LAZAR, 2016)."))

# ---- 4 ----
st(P("4. Respostas diretas para o TCC", "h1"))
st(tabela(["Pergunta", "Resposta"], [
    ["A estratégia de prompt influencia a qualidade dos testbenches gerados por LLM?",
     "<b>Sim.</b> O componente com efeito comprovado é o uso de exemplos (few-shot)."],
    ["Qual estratégia usar?",
     "<b>Qualquer variante few-shot.</b> Entre elas não há diferença detectável com estes dados."],
    ["Persona de especialista e planejamento valem a pena?",
     "<b>Não há evidência estatística.</b> Se existe ganho, ele é secundário e aparece mais quando "
     "o prompt não tem exemplos."],
    ["Basta o testbench “passar” para ser bom?",
     "<b>Não.</b> A análise usa mutantes mortos: um testbench pode passar e verificar pouco "
     "(ver seção 5)."],
], [78 * mm, 96 * mm]))

# ---- 5 ----
st(PageBreak())
st(P("5. Números de apoio (descritivos)", "h1"))
st(P("Para a discussão. Score efetivo = mutantes mortos ÷ 40 possíveis (10 circuitos × 4), com "
     "“Não passou” valendo 0. Aprovados = testbenches que passaram no circuito original."))
linhas = []
for e in ESTR:
    linhas.append([NOME_ESTR[e], f"{dg[e][0]}/10", f"{br(dg[e][1], 1)}%", f"{dm[e][0]}/10",
                   f"{br(dm[e][1], 1)}%"])
fam = {}
for m in MODELOS:
    d = DESC[m]
    fam[m] = [(sum(d[ESTR[j]][0] for j in f), sum(d[ESTR[j]][1] for j in f) / 3) for f in (ZS_FAM, FS_FAM)]
linhas.append(["<b>Família zero-shot</b>", f"<b>{fam[g][0][0]}/30</b>", f"<b>{br(fam[g][0][1], 1)}%</b>",
               f"<b>{fam[m2][0][0]}/30</b>", f"<b>{br(fam[m2][0][1], 1)}%</b>"])
linhas.append(["<b>Família few-shot</b>", f"<b>{fam[g][1][0]}/30</b>", f"<b>{br(fam[g][1][1], 1)}%</b>",
               f"<b>{fam[m2][1][0]}/30</b>", f"<b>{br(fam[m2][1][1], 1)}%</b>"])
t = tabela(["Estratégia", "GPT: aprovados", "GPT: score efetivo", "Gemini: aprovados",
            "Gemini: score efetivo"], linhas, [54 * mm, 28 * mm, 32 * mm, 28 * mm, 32 * mm])
t.setStyle(TableStyle([("BACKGROUND", (0, -2), (-1, -1), AMARELO)]))
st(t)
aprov = {m: sum(DESC[m][e][0] for e in ESTR) for m in MODELOS}
mortos = {m: sum(sum(coluna(VAL[m], j)) for j in range(6)) for m in MODELOS}
qual = {m: 100 * mortos[m] / (4 * aprov[m]) for m in MODELOS}
st(Spacer(1, 6))
st(P("Passar não é o mesmo que verificar bem", "h2"))
st(P(f"O GPT teve {aprov[g]}/60 testbenches aprovados e o Gemini, {aprov[m2]}/60. Mas, entre os "
     f"aprovados, os do GPT mataram {br(qual[g], 0)}% dos mutantes e os do Gemini, apenas "
     f"{br(qual[m2], 0)}%. O caso mais claro é o Especialista Zero-shot do Gemini: "
     f"{dm['EspZS'][0]} de 10 aprovados, mas score efetivo de {br(dm['EspZS'][1], 1)}%. Ou seja, "
     f"“passou” sozinho premiaria o testbench mais fraco; por isso a conclusão se apoia nos "
     f"mutantes mortos."))
st(P("Esta comparação entre modelos é <b>descritiva</b>: não foi feito teste estatístico entre GPT e "
     "Gemini, e eles são de categorias diferentes (o Flash-Lite é a versão leve do Gemini).", "nota"))

# ---- 6 ----
st(P("6. Limitações que acompanham a conclusão", "h1"))
for txt in [
    "<b>Uma execução por estratégia e circuito.</b> LLMs são estocásticos; outra execução poderia "
    "mudar resultados individuais (ARCURI; BRIAND, 2011).",
    "<b>Quatro mutantes por circuito.</b> A nota só varia de 25 em 25%, com muitos empates. Isso "
    f"reduz a resolução dos testes: com poucas diferenças, o menor p possível já é alto (ex.: "
    f"{br(MIN_PAR, 3)} nos pares).",
    "<b>Dez circuitos por modelo.</b> Amostra pequena: diferenças finas entre estratégias não são "
    "detectáveis.",
    "<b>Agrupamento dos modelos.</b> Os mesmos circuitos aparecem nos dois modelos; os 20 pares não "
    "são totalmente independentes. A combinação de Fisher, que não depende disso, chega à mesma "
    "conclusão.",
    "<b>EAS-28 fora da comparação</b> (sem dados no Gemini; no GPT, todas as estratégias empataram "
    "com 4/4).",
    "<b>Mutantes gerados por regex</b>, sem parser de Verilog, e cobertura com tetos estruturais em "
    "alguns circuitos (ex.: Cordic em 50% de linha).",
]:
    st(item(txt))

st(P("7. Trabalhos futuros", "h1"))
for txt in [
    "Repetir cada célula 3 a 5 vezes e reportar média e desvio, ou pass@k.",
    "Usar 8 a 10 mutantes por circuito, para dar mais resolução aos testes.",
    "Comparar os modelos com um teste próprio, em modelos da mesma categoria.",
    "Incluir no ICV um componente de complexidade temporal (contadores longos, protocolos).",
]:
    st(item(txt))

# ---- 8 ----
st(PageBreak())
st(P("8. Texto sugerido para o TCC", "h1"))
st(P("Discussão dos resultados", "h2"))
st(caixa([
    f"Os dois testes estatísticos, considerados em conjunto, indicam que o fator decisivo para a "
    f"qualidade dos testbenches gerados é o uso de exemplos no prompt. O teste de Friedman não "
    f"apontou diferença significativa entre as seis estratégias (GPT: χ<super>2</super>(5) = "
    f"{br(fg['Q'], 2)}, p = {br(fg['p'], 3)}; Gemini: χ<super>2</super>(5) = {br(fm['Q'], 2)}, "
    f"p = {br(fm['p'], 3)}), o que mostra que nenhuma estratégia, isoladamente, domina as demais. "
    f"Entretanto, o contraste planejado entre as famílias few-shot e zero-shot, avaliado pelo teste "
    f"de Wilcoxon pareado, foi significativo com os dois modelos agrupados (T = {br(wj[3])}, "
    f"p = {br(wj[4], 3)}), resultado confirmado pela combinação dos p-valores de cada modelo pelo "
    f"método de Fisher (p = {br(FISHER.pvalue, 3)}). Os resultados são coerentes: as seis "
    f"estratégias se organizam em dois grupos, com e sem exemplos, e a diferença entre eles se "
    f"dilui quando todas são comparadas ao mesmo tempo. A persona de especialista e o planejamento "
    f"não apresentaram efeito estatisticamente comprovado (p ≥ {br(MIN_REF, 2)}), embora os dados "
    f"descritivos sugiram ganho maior quando o prompt não contém exemplos.",
], fundo=colors.white, estilo="corpo"))
st(P("Conclusão", "h2"))
st(caixa([
    "Este trabalho avaliou seis estratégias de prompt na geração de testbenches por LLM, medindo a "
    "qualidade da verificação por meio de teste de mutação. Conclui-se que a estratégia de prompt "
    "influencia a qualidade dos testbenches e que o componente com efeito comprovado é o uso de "
    "exemplos (few-shot): testbenches gerados com exemplos detectaram significativamente mais "
    "defeitos quando os dois modelos avaliados foram analisados em conjunto, com a mesma tendência "
    "em cada modelo isoladamente. Persona de especialista e "
    "planejamento não mostraram ganho comprovado, e as variantes few-shot ficaram praticamente "
    "empatadas entre si. Os resultados também reforçam que avaliar um testbench apenas por sua "
    "aprovação é insuficiente: testbenches aprovados podem verificar pouco, o que só o teste de "
    "mutação revela. Como limitações, destacam-se a execução única por estratégia, o número reduzido "
    "de mutantes e de circuitos; trabalhos futuros devem repetir as execuções e ampliar o conjunto "
    "de mutantes para detectar diferenças mais finas entre as estratégias.",
], fundo=colors.white, estilo="corpo"))

secao_referencias(story, ["ARCURI", "FISHER", "FRIEDMAN", "SIEGEL", "WASSERSTEIN", "WILCOXON"])

construir(sys.argv[1], story, TITULO)
print("Friedman", {k: (round(v["Q"], 4), round(v["p"], 4)) for k, v in FRI.items()})
print("Wilcoxon", WIL, "Fisher", round(FISHER.pvalue, 4))
print("min par", MIN_PAR, "min ref", MIN_REF, "min FSxEspFS", MIN_ESPFS)
print("aprovados", aprov, "qualidade", {k: round(v, 1) for k, v in qual.items()})
print("excecao", nao)
print("PDF:", sys.argv[1])
