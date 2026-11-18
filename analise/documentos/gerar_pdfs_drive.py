#!/usr/bin/env python3
"""
Gera os PDFs explicativos da pasta "Documentação" do Google Drive.

Uso (no WSL, com reportlab):
    python3 analise/documentos/gerar_pdfs_drive.py [pasta_de_saida]

Saída padrão: documentacao/drive/. Os módulos, testbenches e trechos do
coverage.dat das provas ficam em documentacao/drive/fontes/ e vêm de execução
real (Verilator 5.032), conferida de novo em 18/11/2026.

Código em bloco usa XPreformatted com o texto escapado UMA vez: assim "<=" e
"&&" aparecem certos no PDF (a versão anterior mostrava "&lt;=" e "&amp;&amp;").
"""
import os
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle, XPreformatted)

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FONTES = os.path.join(RAIZ, "documentacao", "drive", "fontes")
SAIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "documentacao", "drive")
REVISAO = "Revisado em 18 nov. 2026."

# --------------------------------------------------------------------------
# Estilo (o mesmo dos outros PDFs do projeto: analise/estatistica/pdf_comum.py)
# --------------------------------------------------------------------------
FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FD + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

AZUL = colors.HexColor("#1F4E79")
AZUL_CLARO = colors.HexColor("#EAF1F8")
ZEBRA = colors.HexColor("#F6F8FA")
BORDA = colors.HexColor("#C9D3DD")
AMARELO = colors.HexColor("#FFF4CC")
OCRE = colors.HexColor("#B7950B")
VERDE = colors.HexColor("#E6F4EA")
VERDE_BORDA = colors.HexColor("#2E7D32")
LARANJA = colors.HexColor("#FDEBD9")
LARANJA_BORDA = colors.HexColor("#C0611B")
ROXO = colors.HexColor("#EFE8F7")
ROXO_BORDA = colors.HexColor("#6A4C93")
CINZA_CLARO = colors.HexColor("#EEF0F2")
CINZA = colors.HexColor("#5A6470")

S = {
    "titulo": ParagraphStyle("titulo", fontName="DVB", fontSize=19, leading=23, textColor=AZUL),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=10.5, leading=14, textColor=CINZA,
                          spaceBefore=3),
    "rev": ParagraphStyle("rev", fontName="DV", fontSize=8, leading=10, textColor=CINZA,
                          spaceBefore=2, spaceAfter=8),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=13.5, leading=17, textColor=AZUL,
                         spaceBefore=13, spaceAfter=6, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=11, leading=14, spaceBefore=9,
                         spaceAfter=4, keepWithNext=1),
    "corpo": ParagraphStyle("corpo", fontName="DV", fontSize=9.8, leading=14.2, spaceAfter=5),
    "item": ParagraphStyle("item", fontName="DV", fontSize=9.8, leading=14.2, leftIndent=12,
                           bulletIndent=2, spaceAfter=2),
    "num": ParagraphStyle("num", fontName="DV", fontSize=9.8, leading=14.2, leftIndent=16,
                          bulletIndent=2, spaceAfter=2),
    "nota": ParagraphStyle("nota", fontName="DV", fontSize=8.3, leading=11, textColor=CINZA,
                           spaceBefore=3, spaceAfter=6),
    "cel": ParagraphStyle("cel", fontName="DV", fontSize=8.5, leading=10.8, alignment=TA_CENTER),
    "celE": ParagraphStyle("celE", fontName="DV", fontSize=8.5, leading=10.8, alignment=TA_LEFT),
    "cab": ParagraphStyle("cab", fontName="DVB", fontSize=8.5, leading=10.8, alignment=TA_CENTER,
                          textColor=colors.white),
    "formula": ParagraphStyle("formula", fontName="DV", fontSize=10, leading=15),
    "caixa": ParagraphStyle("caixa", fontName="DV", fontSize=9.5, leading=13.5),
    "cartao_t": ParagraphStyle("cartao_t", fontName="DVB", fontSize=11, leading=14),
    "cartao": ParagraphStyle("cartao", fontName="DV", fontSize=9, leading=12),
    "seta": ParagraphStyle("seta", fontName="DVB", fontSize=14, leading=16, alignment=TA_CENTER,
                           textColor=CINZA),
}
LARG = A4[0] - 36 * mm


def estilo_codigo(tam):
    return ParagraphStyle(f"cod{tam}", fontName="DVM", fontSize=tam, leading=tam * 1.32,
                          backColor=ZEBRA, borderColor=BORDA, borderWidth=0.5, borderPadding=5,
                          leftIndent=5, rightIndent=5, spaceBefore=6, spaceAfter=9)


def P(txt, st="corpo"):
    return Paragraph(txt, S[st])


def H1(txt):
    return P(txt, "h1")


def H2(txt):
    return P(txt, "h2")


def item(txt):
    return Paragraph(txt, S["item"], bulletText="•")


def num(n, txt):
    return Paragraph(txt, S["num"], bulletText=f"{n}.")


def junto(*flowables):
    """Mantém título, explicação e código na mesma página.
    KeepTogether aninhado força quebra de página no reportlab, então achata."""
    lista = []
    for f in flowables:
        lista.extend(f._content if isinstance(f, KeepTogether) else [f])
    return KeepTogether(lista)


def nota(txt):
    return P(txt, "nota")


def c(txt):
    """Código dentro do texto corrido (escapa uma vez)."""
    return '<font name="DVM" size="8.8">' + escape(txt) + "</font>"


def codigo(texto, numerar=False, tam=8.0):
    """Bloco de código. O texto vai cru: o escape é feito aqui, uma única vez."""
    linhas = texto.rstrip("\n").split("\n")
    n = len(linhas)
    if numerar:
        larg = len(str(n))
        linhas = [f"{i:>{larg}}  {l}" for i, l in enumerate(linhas, 1)]
    bloco = XPreformatted(escape("\n".join(linhas)), estilo_codigo(tam))
    if n > 45:
        return bloco          # código longo (apêndices) pode partir entre páginas
    # código curto vai numa tabela de uma célula, que não se parte. Não usar
    # KeepTogether aqui: aninhado com o keepWithNext do título, força quebra de página.
    t = Table([[bloco]], colWidths=[LARG])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    t.spaceBefore, t.spaceAfter = 6, 9
    return t


def caixa(conteudo, fundo=AZUL_CLARO, borda=AZUL, estilo="caixa"):
    linhas = conteudo if isinstance(conteudo, list) else [conteudo]
    t = Table([[[P(l, estilo) for l in linhas]]], colWidths=[LARG])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fundo),
        ("LINEBEFORE", (0, 0), (0, -1), 3, borda),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    t.spaceBefore, t.spaceAfter = 3, 6
    return t


def tabela(cab, linhas, larguras, primeira_esq=True, centro=False, destacar_ultima=False):
    dados = [[P(x, "cab") for x in cab]]
    for linha in linhas:
        dados.append([P(str(x), "celE" if (j == 0 and primeira_esq) or (j > 0 and not centro)
                        else "cel") for j, x in enumerate(linha)])
    t = Table(dados, colWidths=larguras, repeatRows=1)
    est = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if destacar_ultima:
        est.append(("BACKGROUND", (0, -1), (-1, -1), AMARELO))
    t.setStyle(TableStyle(est))
    if len(linhas) <= 15:
        # tabela curta dentro de uma célula: assim ela não se parte entre páginas
        t = Table([[t]], colWidths=[sum(larguras)])
        t.setStyle(TableStyle([(k, (0, 0), (-1, -1), 0) for k in
                               ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")]))
    t.spaceBefore, t.spaceAfter = 2, 7
    return t


def ler(nome):
    with open(os.path.join(FONTES, nome), encoding="utf-8") as f:
        return f.read()


def cabecalho(titulo, sub):
    return [P(titulo, "titulo"), P(sub, "sub"), P(REVISAO, "rev")]


def construir(nome, titulo_rodape, story):
    caminho = os.path.join(SAIDA, nome)

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 8)
        canvas.setFillColor(CINZA)
        canvas.drawString(18 * mm, 10 * mm, titulo_rodape)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title=titulo_rodape,
                            author="Bancada RTL (veriweb)")
    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
    print("gerado:", caminho)


FORMULA_ICV = ("ICV = P<sub>LOC</sub> × 0,30 + P<sub>FSM</sub> × 0,30 + "
               "P<sub>IO</sub> × 0,20 + P<sub>LOG</sub> × 0,20")

TABELA_ICV_MODULOS = [
    ["Lemmings1", "24 (1)", "2 (1)", "6 (2)", "— (0)", "1,0", "Fácil"],
    ["Conwaylife", "33 (2)", "— (0)", "4 (1)", "A (1)", "1,0", "Fácil"],
    ["Count clock", "39 (2)", "— (0)", "7 (2)", "— (0)", "1,0", "Fácil"],
    ["Exams/2012 q2fsm", "34 (2)", "6 (2)", "4 (1)", "— (0)", "1,4", "Média"],
    ["Cs450/gshare", "35 (2)", "— (0)", "11 (3)", "A, D (3)", "1,8", "Média"],
    ["Fancytimer", "48 (2)", "4 (1)", "7 (2)", "A, D (3)", "1,9", "Média"],
    ["CORDIC", "109 (3)", "— (0)", "8 (2)", "A, P (3)", "1,9", "Média"],
    ["Fsm serialdp", "83 (2)", "5 (2)", "5 (2)", "A, D (3)", "2,2", "Alta"],
    ["SPI Master", "102 (3)", "3 (1)", "12 (3)", "A, D (3)", "2,4", "Muito Alta"],
    ["wbuart32", "84 (2)", "10 (3)", "5 (2)", "A, D (3)", "2,5", "Muito Alta"],
]

SCORE_EFETIVO = ("score efetivo = mutantes detectados ÷ (4 × testbenches gerados)")


# ==========================================================================
# 1. ICV_calculo_atual.pdf
# ==========================================================================
def doc_icv():
    s = cabecalho("Índice de Complexidade para Verificação (ICV)",
                  "Como a nota é calculada: exemplo do somador (0,70), nota máxima (3,00) e os "
                  "10 módulos do experimento")
    s += [
        H1("O que é o ICV"),
        P("O ICV é uma nota que mede a complexidade de um módulo RTL (o DUT) para fins de "
          "verificação. Ele combina quatro pontuações, cada uma de 0 a 3, com pesos diferentes. "
          "A análise é feita apenas sobre o texto do módulo e não depende do testbench."),
        P("A escala vai de 0 a 3. Os módulos do estudo (problemas didáticos e cores abertos) são "
          "de complexidade baixa a média. Por isso, as faixas mais altas de cada componente, que "
          "só módulos muito grandes atingiriam, foram fundidas no valor 3."),
        caixa([FORMULA_ICV], estilo="formula"),
        nota("P<sub>LOC</sub> = linhas de código (sem comentários e sem linhas em branco) • "
             "P<sub>FSM</sub> = número de estados da máquina de estados • P<sub>IO</sub> = "
             "número de portas de entrada e saída • P<sub>LOG</sub> = natureza da lógica "
             "(aritmética, deslocamento, estruturas replicadas)."),
        H1("Papel do ICV no TCC"),
        P("No TCC, o ICV serve para garantir que os dez módulos tenham complexidades variadas, "
          "de fáceis a muito altas. Os resultados das estratégias não são comparados por classe "
          "de ICV."),
        H1("De onde vêm os pesos (0,30 e 0,20)"),
        P("Os pesos são fixos na fórmula e refletem quanto cada dimensão pesa na dificuldade de "
          "verificar o módulo. P<sub>LOC</sub> e P<sub>FSM</sub> valem 0,30 cada, porque o "
          "tamanho do código e a máquina de estados são o que mais aumenta o esforço de "
          "verificação. P<sub>IO</sub> e P<sub>LOG</sub> valem 0,20 cada. Os quatro pesos somam "
          "exatamente 1,0. Por isso o ICV é uma média ponderada e fica na mesma escala das "
          "pontuações (0 a 3)."),
        H1("Faixas de pontuação (para calcular à mão)"),
        P("Para cada componente, conte a grandeza indicada e leia a pontuação na tabela."),
        H2("P<sub>LOC</sub>: linhas de código"),
        tabela(["Linhas de código", "P<sub>LOC</sub>"],
               [["até 30", "1"], ["31 a 100", "2"], ["mais de 100", "3"]],
               [70 * mm, 30 * mm], centro=True),
        H2("P<sub>FSM</sub>: número de estados da máquina de estados"),
        tabela(["Nº de estados", "P<sub>FSM</sub>"],
               [["0 ou 1 (sem máquina de estados)", "0"], ["2 a 4", "1"], ["5 a 9", "2"],
                ["mais de 9", "3"]],
               [70 * mm, 30 * mm], centro=True),
        nota("Os estados podem ser nomeados (por " + c("parameter") + ", " + c("localparam") +
             " ou " + c("`define") + ") ou numéricos (" + c("state == 2") + ")."),
        H2("P<sub>IO</sub>: número de portas (entradas + saídas, contando portas e não bits)"),
        tabela(["Nº de portas", "P<sub>IO</sub>"],
               [["até 4", "1"], ["5 a 10", "2"], ["mais de 10", "3"]],
               [70 * mm, 30 * mm], centro=True),
        H2("P<sub>LOG</sub>: natureza da lógica (soma das características, com teto 3)"),
        tabela(["Característica presente na lógica", "Pontos"],
               [["combinacional básica (ponto de partida)", "0"],
                ["aritmética (+, -, *)", "+1"],
                ["deslocamento: registrador que recebe uma versão deslocada de si mesmo "
                 "(típico de protocolo serial)", "+2"],
                ["estruturas replicadas: blocos " + c("generate") + " com " + c("for") +
                 " (típico de pipeline)", "+2"]],
               [130 * mm, 30 * mm], centro=True),
        P("Some as características presentes. O total é limitado a 3. Por exemplo, aritmética "
          "mais deslocamento dá 1 + 2 = 3."),
        H1("Passo a passo para calcular à mão"),
        num(1, "Conte as linhas de código, sem comentários e sem linhas em branco, e leia "
               "P<sub>LOC</sub>."),
        num(2, "Conte os estados da máquina de estados e leia P<sub>FSM</sub>."),
        num(3, "Conte as portas de entrada e saída e leia P<sub>IO</sub>."),
        num(4, "Veja a lógica e some as características para obter P<sub>LOG</sub>."),
        num(5, "Multiplique cada pontuação pelo seu peso e some."),
        CondPageBreak(90 * mm),
        H1("Exemplo: somador de 32 bits (ICV = 0,70)"),
        codigo("module adder_32bit (\n    input  [31:0] a,\n    input  [31:0] b,\n"
               "    output [32:0] sum\n);\n    assign sum = a + b;\nendmodule"),
        item("<b>P<sub>LOC</sub> = 1</b>: o módulo tem 7 linhas de código. Faixa até 30, então 1."),
        item("<b>P<sub>FSM</sub> = 0</b>: é puramente combinacional (só " + c("assign") +
             ", sem " + c("<=") + " nem " + c("case") + "). Sem máquina de estados, então 0."),
        item("<b>P<sub>IO</sub> = 1</b>: são 3 portas (a, b e sum). Contam-se portas, não bits. "
             "Faixa até 4, então 1."),
        item("<b>P<sub>LOG</sub> = 1</b>: há aritmética (o + em " + c("a + b") + "), então +1. "
             "Não há deslocamento nem estruturas replicadas."),
        tabela(["Componente", "Pontuação", "Peso", "Contribuição"],
               [["P<sub>LOC</sub>", "1", "0,30", "0,30"], ["P<sub>FSM</sub>", "0", "0,30", "0,00"],
                ["P<sub>IO</sub>", "1", "0,20", "0,20"], ["P<sub>LOG</sub>", "1", "0,20", "0,20"],
                ["<b>ICV (soma)</b>", "", "", "<b>0,70</b>"]],
               [45 * mm, 30 * mm, 30 * mm, 35 * mm], centro=True, destacar_ultima=True),
        P("ICV = (1 × 0,30) + (0 × 0,30) + (1 × 0,20) + (1 × 0,20) = 0,70. Na escala, 0,70 cai "
          "na faixa de 0,0 a 1,2, ou seja, Fácil."),
        H1("Nota máxima possível: 3,00"),
        P("Como os pesos somam exatamente 1,0, o ICV é uma média ponderada das quatro "
          "pontuações. Com todas no máximo (3), ICV = (3 × 0,30) + (3 × 0,30) + (3 × 0,20) + "
          "(3 × 0,20) = 0,9 + 0,9 + 0,6 + 0,6 = 3,00."),
        tabela(["Componente", "Para chegar a 3, o módulo precisa de"],
               [["P<sub>LOC</sub>", "mais de 100 linhas de código"],
                ["P<sub>FSM</sub>", "mais de 9 estados"],
                ["P<sub>IO</sub>", "mais de 10 portas (entradas + saídas)"],
                ["P<sub>LOG</sub>", "lógica rica, por exemplo aritmética + deslocamento (1 + 2) "
                 "ou aritmética + estruturas replicadas"]],
               [40 * mm, 120 * mm]),
        P("A escala foi ajustada de 0 a 5 para 0 a 3 porque os módulos do estudo (problemas "
          "didáticos e cores abertos pequenos) nunca chegam perto do topo. As faixas mais altas "
          "de cada componente foram fundidas no valor 3. Assim os módulos ocupam bem a escala e "
          "a classe Muito Alta fica alcançável. Na prática, o piso de um módulo real fica em "
          "torno de 0,50."),
        H1("Escala de classificação"),
        tabela(["Faixa de ICV", "Classe"],
               [["0,0 a 1,2", "Fácil"], ["1,3 a 1,9", "Média"], ["2,0 a 2,3", "Alta"],
                ["maior que 2,3 (até 3,0)", "Muito Alta"]],
               [70 * mm, 40 * mm], centro=True),
        CondPageBreak(80 * mm),
        H1("ICV dos 10 módulos do experimento"),
        tabela(["Módulo", "Linhas (P<sub>LOC</sub>)", "Estados (P<sub>FSM</sub>)",
                "Portas (P<sub>IO</sub>)", "Lógica (P<sub>LOG</sub>)", "ICV", "Classe"],
               TABELA_ICV_MODULOS,
               [34 * mm, 23 * mm, 23 * mm, 21 * mm, 23 * mm, 13 * mm, 23 * mm], centro=True),
        nota("Entre parênteses, a pontuação de cada componente. Estados: número identificado "
             "pela Bancada RTL; — indica módulo sem máquina de estados. Lógica: A = aritmética, "
             "D = deslocamento, P = estruturas replicadas. Resultado: 3 módulos Fácil, 4 Média, "
             "1 Alta e 2 Muito Alta."),
    ]
    construir("ICV_calculo_atual.pdf", "Índice de Complexidade para Verificação (ICV)", s)


# ==========================================================================
# 2. Metricas_como_funcionam.pdf
# ==========================================================================
def doc_metricas():
    s = cabecalho("As métricas da Bancada: como funcionam",
                  "Básicas, cobertura, teste de mutação e ICV, no conceito e no código")
    s += [
        H1("Visão geral"),
        P("A cada avaliação, a bancada devolve quatro grupos de métricas. Todas são calculadas "
          "em " + c("app.py") + ", a partir da simulação no Verilator ou do texto do módulo."),
        tabela(["Grupo", "O que mede", "De onde vem"],
               [["Básicas", "compilou, executou e passou",
                 "código de saída da compilação e da simulação"],
                ["Cobertura", "quanto do RTL foi exercitado (linha, desvio e alternância)",
                 "arquivo coverage.dat gravado pela simulação"],
                ["Mutação", "quantos defeitos plantados o testbench detecta",
                 "teste de mutação (documento próprio)"],
                ["ICV", "complexidade do módulo (0 a 3)", "análise do texto do RTL"]],
               [28 * mm, 70 * mm, 76 * mm]),
        H1("1. Métricas básicas: compilou, executou e passou"),
        P("A função " + c("compilar_e_cobrir()") + " compila o RTL, o testbench e o harness com o "
          "Verilator e roda a simulação. Os três selos saem assim."),
        tabela(["Selo", "Como é decidido"],
               [["compilou", "o Verilator terminou a compilação sem erro"],
                ["executou", "o programa da simulação rodou: não passou do limite de 30 s e o "
                 "executável existia"],
                ["passou", "a simulação saiu com código 0. Quando uma checagem falha, o "
                 + c("$fatal") + " faz o código ser diferente de 0 e o testbench é reprovado"]],
               [28 * mm, 146 * mm]),
        H1("2. Cobertura de código"),
        P("A cobertura mede quanto do módulo o testbench exercitou. A compilação usa a opção "
          + c("--coverage") + ", que instala um contador em cada ponto do circuito. A simulação "
          "grava esses contadores no arquivo coverage.dat, e a função " + c("ler_cobertura()") +
          " lê esse arquivo."),
        P("<b>Por que existe o harness</b> " + c("sim/main.cpp") + ". Com " + c("--binary") +
          ", o Verilator só grava o coverage.dat quando a simulação termina normalmente. Quando o "
          "testbench encerra com " + c("$fatal") + ", o programa aborta e o arquivo não é "
          "gravado. O harness grava a cobertura também nesse caso, antes de o programa "
          "encerrar."),
        H2("Como o código conta"),
        codigo("para cada linha do coverage.dat que começa com C (um ponto de cobertura):\n"
               "  - só conta pontos do dut.v (ignora o próprio testbench)\n"
               "  - total += 1\n"
               "  - coberto se a contagem N >= 1\n"
               "  - agrupa por tipo: v_line (linha), v_branch (desvio), v_toggle (alternância)\n"
               "pct = 100 * cobertos / total"),
        nota("O critério N ≥ 1 é o mesmo da opção " + c("--annotate-min 1") + " do "
             + c("verilator_coverage") + " (o padrão, 10, daria 0%). A bancada não usa essa "
             "ferramenta: ela conta direto no arquivo."),
        H2("Os tipos de cobertura"),
        tabela(["Tipo", "O que verifica"],
               [["Linha (v_line)", "quais trechos executáveis do RTL foram executados"],
                ["Desvio (v_branch)", "se os dois lados de cada " + c("if") + " foram tomados"],
                ["Alternância (v_toggle)", "se cada bit de sinal mudou de 0 para 1 e de 1 para 0"],
                ["Máquina de estados (aproximada)", "o Verilator não tem essa métrica. A função "
                 + c("cobertura_fsm()") + " relê os braços do " + c("case") + " do registrador de "
                 "estado. A bancada mostra esse valor, mas o TCC não o utiliza"]],
               [45 * mm, 129 * mm]),
        caixa(["<b>Importante.</b> A cobertura conta só os pontos do dut.v. Cobertura alta não "
               "garante circuito correto: ela diz que o trecho foi executado, não que a saída foi "
               "conferida. No TCC, as médias de cobertura usam só os testbenches aprovados."],
              fundo=AMARELO, borda=OCRE),
        H1("3. Teste de mutação"),
        P("Mede a capacidade do testbench de detectar defeitos introduzidos no RTL. É a métrica "
          "mais rigorosa: a cobertura diz que o teste passou por uma linha, a mutação diz se ele "
          "conferiu que a linha está certa. O funcionamento detalhado está no documento próprio. "
          "Em resumo, a bancada sabota o RTL (até 4 mutantes), roda o testbench em cada um e "
          "conta quantos foram detectados (mortos)."),
        P("Por testbench, a bancada mostra mortos ÷ mutantes válidos. No TCC, o resultado "
          "principal é o score efetivo, que considera todos os testbenches gerados."),
        caixa([SCORE_EFETIVO,
               "Um testbench reprovado, ou que passou do tempo limite, conta como 0 detectados."],
              estilo="formula"),
        H1("4. ICV: Índice de Complexidade para Verificação"),
        P("Mede a complexidade do módulo (o DUT) só a partir do texto. Combina quatro pontuações "
          "de 0 a 3, com pesos, e resulta num índice de 0 a 3."),
        caixa([FORMULA_ICV], estilo="formula"),
        tabela(["Componente", "O que conta", "Faixas (0 a 3)"],
               [["P<sub>LOC</sub>", "linhas de código (sem comentários e linhas em branco)",
                 "≤30 → 1 • ≤100 → 2 • >100 → 3"],
                ["P<sub>FSM</sub>", "estados da máquina de estados (nomeados ou numéricos)",
                 "≤1 → 0 • ≤4 → 1 • ≤9 → 2 • >9 → 3"],
                ["P<sub>IO</sub>", "portas de entrada e saída (portas, não bits)",
                 "≤4 → 1 • ≤10 → 2 • >10 → 3"],
                ["P<sub>LOG</sub>", "natureza da lógica (soma, teto 3)",
                 "aritmética +1 • deslocamento +2 • estruturas replicadas +2"]],
               [25 * mm, 74 * mm, 75 * mm]),
        P("Classificação final: 0,0 a 1,2 Fácil • 1,3 a 1,9 Média • 2,0 a 2,3 Alta • acima de "
          "2,3 Muito Alta. A extração é feita por heurística de texto, sem parser. "
          "P<sub>FSM</sub> detecta o registrador de estado e conta as constantes de estado. "
          "P<sub>LOG</sub> procura aritmética, deslocamento (registrador que recebe uma "
          "concatenação de si mesmo) e estruturas replicadas (" + c("generate") + " com "
          + c("for") + "). Detalhes no documento próprio do ICV."),
        P("No TCC, o ICV serve para garantir que os módulos tenham complexidades variadas. Os "
          "resultados não são comparados por classe de ICV."),
    ]
    construir("Metricas_como_funcionam.pdf", "As métricas da Bancada: como funcionam", s)


# ==========================================================================
# 3. Mutacao_como_funciona.pdf
# ==========================================================================
def doc_mutacao():
    s = cabecalho("Teste de mutação: como funciona",
                  "Conceito e implementação no código da bancada (app.py)")
    s += [
        H1("1. A ideia"),
        P("O teste de mutação responde a uma pergunta: o testbench testa mesmo, ou só parece que "
          "testa? A forma de descobrir é sabotar o circuito de propósito e ver se o testbench "
          "percebe. A bancada pega o módulo RTL correto e cria cópias com um pequeno defeito "
          "cada (os mutantes). Depois roda o testbench em cada cópia sabotada."),
        tabela(["Resultado", "O que significa"],
               [["Mutante MORTO", "o testbench acusou erro, ou seja, percebeu o defeito"],
                ["Mutante SOBREVIVEU", "o testbench passou como se nada tivesse mudado, ou seja, "
                 "não percebeu o defeito"]],
               [45 * mm, 129 * mm]),
        P("Por testbench, a nota é o mutation score: dos defeitos plantados, quantos o testbench "
          "pegou."),
        caixa(["MS (%) = mutantes mortos ÷ mutantes válidos × 100"], estilo="formula"),
        P("No TCC, o resultado principal é o score efetivo. Ele soma os mutantes detectados de "
          "todos os testbenches gerados e divide pelo total de falhas possíveis (4 por "
          "testbench). Um testbench reprovado, ou que passou do tempo limite, conta como 0."),
        caixa([SCORE_EFETIVO], estilo="formula"),
        H1("2. Como funciona no código (app.py)"),
        P("Toda a lógica está em " + c("app.py") + ". O fluxo usa quatro funções principais."),
        H2("2.1 Onde pode mutar: regioes_de_logica()"),
        P("Antes de trocar qualquer coisa, a bancada delimita onde a mutação vale: só no corpo "
          "de blocos " + c("always") + " e de " + c("assign") + ". Fora disso (portas, larguras "
          + c("[W-1:0]") + ", " + c("localparam") + "), uma troca de operador geraria um mutante "
          "equivalente ou inválido. A detecção é feita por palavras-chave, sem parser."),
        H2("2.2 O que troca: a tabela MUTACOES"),
        P("Cada operador vira uma regra (descrição, expressão regular e troca). São 20 "
          "operadores de primeira ordem, ou seja, cada mutante tem uma única troca."),
        tabela(["Grupo", "Trocas"],
               [["Aritméticos", c("+ → -") + ",&nbsp;&nbsp; " + c("- → +") + ",&nbsp;&nbsp; " + c("* → +")],
                ["Bit a bit", c("& → |") + ",&nbsp;&nbsp; " + c("| → &") + ",&nbsp;&nbsp; " + c("^ → &")],
                ["Lógicos", c("&& → ||") + ",&nbsp;&nbsp; " + c("|| → &&")],
                ["Igualdade e relacionais", c("== → !=") + ",&nbsp;&nbsp; " + c("!= → ==") + ",&nbsp;&nbsp; "
                 + c("< → >=") + ",&nbsp;&nbsp; " + c("> → <=") + ",&nbsp;&nbsp; " + c(">= → <")],
                ["Deslocamentos", c("<< → >>") + ",&nbsp;&nbsp; " + c(">> → <<")],
                ["Constantes", "constante diferente de zero → 0 (ex.: " + c("2'd1 → 2'd0")
                 + "); zero → 1 (ex.: " + c("'d0 → 'd1") + ")"],
                ["Estruturais", "troca os ramos de " + c("?:") + ";&nbsp;&nbsp; " + c("if (x) → if (!x)")
                 + ";&nbsp;&nbsp; " + c("if (!x) → if (x)")]],
               [40 * mm, 134 * mm]),
        P("As expressões evitam casos que quebram a compilação: " + c("+:") + " e " + c("-:")
          + " de seleção de bits, " + c("@(*)") + ", " + c("===") + " e " + c("!==") + ", e o "
          + c("<=") + " de atribuição dentro de " + c("always") + "."),
        H2("2.3 Geração: gerar_mutantes()"),
        P("Varre o texto e, para cada ocorrência de cada operador que esteja dentro da lógica e "
          "fora de comentário, cria uma cópia do RTL só com aquela troca. Um ponto mutável gera "
          "um mutante. A lista sai ordenada pela posição no arquivo."),
        H2("2.4 Amostragem: selecionar_espalhados()"),
        P("Só 4 mutantes são avaliados (" + c("MAX_MUTANTES = 4") + "). Para não pegar 4 do mesmo "
          "lugar num módulo grande, esta função divide os pontos mutáveis em 4 faixas por posição "
          "no arquivo, uma por mutante, e intercala uma de cada. Dentro de cada faixa, alterna "
          "também o tipo de operador. A ordem é determinística: o mesmo módulo gera sempre os "
          "mesmos mutantes."),
        H2("2.5 Execução: testar_mutacao()"),
        codigo("para cada candidato, na ordem espalhada:\n"
               "  escreve o dut.v sabotado (mut.v)\n"
               "  compila com o tb.v: verilator --binary --timing ... --top-module tb\n"
               "   |- não compilou?                 -> inválido: descarta e tenta o próximo\n"
               "   |- rodou e deu erro (exit != 0)? -> MORTO (o teste pegou)\n"
               "   |- passou de 30 s (travou)?      -> MORTO (o defeito travou o teste)\n"
               "   |- rodou e passou (exit == 0)?   -> SOBREVIVEU\n"
               "  para quando junta 4 mutantes válidos (ou 16 tentativas)"),
        P("O ponto central é que \"deu erro\" significa código de saída diferente de 0. Por isso "
          "o testbench precisa usar " + c("$fatal") + " quando uma checagem falha. É isso que faz "
          "o programa sair com erro, e a bancada interpreta esse erro como \"o teste pegou o "
          "defeito\". Um mutante que trava a simulação também conta como detectado, porque o "
          "defeito teve um efeito visível."),
        P("Dois limites protegem o tempo da avaliação: " + c("MAX_MUTANTES = 4") + " (mutantes "
          "válidos) e " + c("MAX_TENTATIVAS = 16") + " (compilações no total)."),
        H2("2.6 A trava importante (na rota /avaliar)"),
        P("A mutação só roda se o testbench compilou, executou e passou no RTL original. Se o "
          "testbench já falha no circuito correto, ele falharia em todo mutante também, e o score "
          "sairia 100% sem significado. Nesse caso, a bancada não faz a mutação."),
        H1("3. Limitações"),
        item("<b>É expressão regular, não parser.</b> Mutantes inválidos são gerados, mas são "
             "descartados na compilação, sem afetar o score. Eles só gastam tempo, daí o teto de "
             "16 tentativas."),
        item("<b>São só 4 mutantes.</b> O espalhamento torna a amostra justa, mas 4 de, às vezes, "
             "mais de 100 pontos continua sendo uma amostra."),
        item("<b>Mutantes equivalentes.</b> Alguns mutantes têm comportamento idêntico ao "
             "original e sobrevivem sem que nenhum testbench pudesse matá-los. Um exemplo "
             "teórico é um contador módulo 16, onde somar 8 e subtrair 8 dão o mesmo resultado. "
             "No experimento, isso aconteceu no CORDIC: um mutante trocou " + c("if (init)")
             + " por " + c("if (!init)") + " na linha 76, dentro de um bloco " + c("`ifdef ITERATE")
             + " cuja definição está comentada. Esse trecho nem é compilado, então nenhum "
             "testbench consegue detectar a troca. A bancada não detecta mutantes equivalentes "
             "automaticamente."),
    ]
    construir("Mutacao_como_funciona.pdf", "Teste de mutação: como funciona", s)


# ==========================================================================
# 4. Trabalho_visao_geral.pdf
# ==========================================================================
def doc_visao_geral():
    s = cabecalho("A Bancada RTL: visão geral do trabalho",
                  "Objetivo, experimento, arquitetura, fluxo e organização do código")
    s += [
        H1("1. O objetivo (o TCC)"),
        P("O trabalho avalia estratégias de engenharia de prompt na geração de testbenches para a "
          "verificação de módulos RTL. Dois LLMs, o GPT-5.6 Luna e o Gemini 3.5 Flash-Lite, geram "
          "testbenches com seis estratégias, e a bancada mede, de forma objetiva, qual estratégia "
          "gera os testes mais eficazes."),
        tabela(["Grupo", "Estratégias", "Ideia"],
               [["Básicas", "Zero-shot (ZS) e Few-shot (FS)",
                 "só a tarefa, ou a tarefa com dois exemplos de testbench"],
                ["Especialista", "Especialista ZS e Especialista FS",
                 "pede que o LLM aja como engenheiro de verificação de hardware"],
                ["Planning", "Planning ZS e Planning FS",
                 "pede que o LLM analise o módulo antes de gerar o testbench"]],
               [28 * mm, 58 * mm, 88 * mm]),
        P("O experimento usou 10 módulos, 6 estratégias, 2 LLMs e 2 rodadas, o que dá "
          "10 × 6 × 2 × 2 = 240 testbenches."),
        H1("2. O que a bancada faz"),
        P("É uma página web onde se cola um módulo RTL (o circuito, o DUT) e um testbench. Ao "
          "clicar em Avaliar, ela devolve se compilou, se executou, se passou, a cobertura de "
          "código, o teste de mutação e o ICV (complexidade do módulo). Tudo roda sobre o "
          "Verilator, um simulador de Verilog gratuito."),
        H1("3. Arquitetura e fluxo"),
        codigo("navegador (templates/index.html)\n"
               "   |  POST /avaliar { rtl, tb, modulo, estrategia }\n"
               "   v\n"
               "Flask (app.py)\n"
               "   |- escreve dut.v e tb.v numa pasta temporária\n"
               "   |- compila com o harness C++ -> simula -> lê a cobertura\n"
               "   |- calcula o ICV a partir do texto do RTL\n"
               "   |- se o testbench passou: gera mutantes -> roda cada um -> conta os mortos\n"
               "   |- grava no historico.csv, envia para a planilha e salva em avaliacoes/\n"
               "   +- devolve tudo em JSON\n"
               "   v\n"
               "navegador desenha os painéis (estado, cobertura, mutantes, ICV)"),
        P("Cada avaliação roda numa pasta temporária própria, apagada no fim, para que uma "
          "avaliação não interfira na outra. Uma cópia do módulo, do testbench e do resultado "
          "fica em " + c("avaliacoes/<data>_<módulo>_<estratégia>/") + "."),
        H1("4. Como o código está organizado"),
        tabela(["Arquivo", "Papel"],
               [[c("app.py"), "backend Flask: compilar, medir cobertura, mutar, calcular o ICV e "
                 "registrar"],
                [c("templates/index.html"), "a página: campos de RTL e testbench, botão Avaliar e "
                 "os painéis"],
                [c("sim/main.cpp"), "harness C++: laço de tempo da simulação e gravação da "
                 "cobertura, inclusive quando o testbench encerra com $fatal"],
                [c("planilha/doPost.gs"), "script do Google Planilhas que recebe cada avaliação"],
                [c("analise/"), "scripts das tabelas, estatísticas, figuras e PDFs"],
                [c("documentacao/"), "apêndices do TCC, figuras e PDFs explicativos"],
                [c("requirements.txt"), "dependência do Python (Flask)"],
                [c("start.sh"), "sobe o servidor (cria o ambiente, instala e roda o app.py)"]],
               [45 * mm, 129 * mm]),
        H1("5. O caminho de uma avaliação (rota /avaliar)"),
        num(1, "Recebe o JSON com o RTL, o testbench, o nome do módulo e a estratégia. Confere "
               "que o RTL e o testbench não estão vazios e que o módulo do testbench se chama "
               "tb."),
        num(2, "Escreve os dois em arquivos (dut.v e tb.v) numa pasta temporária."),
        num(3, c("compilar_e_cobrir()") + " compila com o Verilator e o harness, roda a "
               "simulação e lê a cobertura."),
        num(4, c("calcular_icv()") + " calcula o ICV a partir do texto do RTL. Isso não "
               "depende de compilar."),
        num(5, "Se compilou, executou e passou, roda a mutação com " + c("testar_mutacao()")
               + ". Se o testbench reprovou no circuito original, a mutação não é feita."),
        num(6, c("registrar_historico()") + " grava a linha no historico.csv e envia para a "
               "planilha. " + c("salvar_avaliacao()") + " guarda os arquivos e o resultado em "
               "avaliacoes/."),
        num(7, "Devolve tudo em JSON e apaga a pasta temporária."),
        H1("6. Conhecimento embutido (os problemas já resolvidos)"),
        tabela(["Detalhe", "Por quê"],
               [["build em /tmp (" + c("--Mdir") + ")", "o make gerado pelo Verilator não aceita "
                 "caminho com espaço"],
                ["harness C++ (" + c("sim/main.cpp") + ")", "com " + c("--binary") + ", a "
                 "cobertura só é gravada no fim normal da simulação; o harness grava também "
                 "quando o testbench encerra com $fatal"],
                ["coberto = contagem ≥ 1", "é o critério do " + c("--annotate-min 1") + "; o "
                 "padrão (10) daria 0% de cobertura"],
                ["módulo do testbench = tb", "o harness inclui " + c("Vtb.h") + ", então o nome "
                 "precisa ser fixo"],
                ["limite de 30 s na simulação", "um mutante que trava não segura a avaliação e "
                 "conta como detectado"],
                ["rodar no WSL", "o projeto e o Verilator ficam no sistema de arquivos do "
                 "Linux"]],
               [55 * mm, 119 * mm]),
        H1("7. Como usar"),
        P("Suba o servidor no WSL (" + c("./start.sh") + ") e abra http://127.0.0.1:5000. Cole o "
          "módulo RTL num campo e o testbench no outro. O módulo do testbench deve se chamar "
          + c("tb") + " e usar " + c("$fatal") + " ao detectar erro. Informe o módulo e a "
          "estratégia e clique em Avaliar. Os painéis mostram o estado, a cobertura por tipo, o "
          "mapa de mutantes e o ICV."),
    ]
    construir("Trabalho_visao_geral.pdf", "A Bancada RTL: visão geral do trabalho", s)


# ==========================================================================
# 5. analogias_bancada_rtl.pdf
# ==========================================================================
def cartao(titulo, pergunta, detalhe, fundo, borda):
    return [P(f'<font color="{borda.hexval().replace("0x", "#")}">{titulo}</font>', "cartao_t"),
            P(pergunta, "cartao"), P(f"<i>{detalhe}</i>", "nota")]


def doc_analogias():
    s = cabecalho("Bancada RTL: as métricas explicadas por analogias",
                  "Como a ferramenta mede compilação, cobertura, mutação e complexidade (ICV), em "
                  "linguagem simples e sem código")
    quadro = Table(
        [[cartao("STATUS", "A casa fica de pé, dá para andar e o inspetor aprova?",
                 "compilou, executou e passou", CINZA_CLARO, CINZA),
          cartao("COBERTURA", "Por quais cômodos o inspetor andou? (sensores)",
                 "quanto do circuito foi exercitado", VERDE, VERDE_BORDA)],
         [cartao("MUTAÇÃO", "Estrago a casa de propósito: o inspetor apita?",
                 "o teste realmente pega erros?", LARANJA, LARANJA_BORDA),
          cartao("ICV", "Nota de dificuldade da casa, só olhando a planta",
                 "quão complexo é o circuito", ROXO, ROXO_BORDA)]],
        colWidths=[LARG / 2 - 2 * mm] * 2)
    quadro.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), CINZA_CLARO), ("BACKGROUND", (1, 0), (1, 0), VERDE),
        ("BACKGROUND", (0, 1), (0, 1), LARANJA), ("BACKGROUND", (1, 1), (1, 1), ROXO),
        ("LINEBEFORE", (0, 0), (0, 0), 3, CINZA), ("LINEBEFORE", (1, 0), (1, 0), 3, VERDE_BORDA),
        ("LINEBEFORE", (0, 1), (0, 1), 3, LARANJA_BORDA),
        ("LINEBEFORE", (1, 1), (1, 1), 3, ROXO_BORDA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), 4, colors.white),
        ("LINEAFTER", (0, 0), (0, -1), 4, colors.white),
    ]))

    def passo(t, d):
        return [P(f"<b>{t}</b>", "cel"), P(d, "nota")]

    cadeia = Table([[passo("RTL + testbench", "a planta da casa e os convidados"), P("→", "seta"),
                     passo("COMPILA com --coverage", "constrói a casa com sensores"),
                     P("→", "seta"),
                     passo("SIMULA", "a festa acontece e os sensores contam"), P("→", "seta"),
                     passo("coverage.dat", "a casa anota os sensores na folha"), P("→", "seta"),
                     passo("a bancada lê e conta", "quantos cômodos foram usados")]],
                   colWidths=[31 * mm, 6 * mm, 31 * mm, 6 * mm, 31 * mm, 6 * mm, 31 * mm, 6 * mm,
                              26 * mm])
    cadeia.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), ZEBRA), ("BACKGROUND", (2, 0), (2, 0), ZEBRA),
        ("BACKGROUND", (4, 0), (4, 0), ZEBRA), ("BACKGROUND", (6, 0), (6, 0), VERDE),
        ("BACKGROUND", (8, 0), (8, 0), ZEBRA),
        ("BOX", (0, 0), (0, 0), 0.5, BORDA), ("BOX", (2, 0), (2, 0), 0.5, BORDA),
        ("BOX", (4, 0), (4, 0), 0.5, BORDA), ("BOX", (6, 0), (6, 0), 0.8, VERDE_BORDA),
        ("BOX", (8, 0), (8, 0), 0.5, BORDA),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    s += [
        H1("A analogia central: a casa e o inspetor"),
        P("Para entender tudo de uma vez, imagine uma casa e um inspetor de qualidade."),
        item("A <b>casa</b> é o circuito (o módulo RTL) que se quer testar."),
        item("O <b>inspetor</b> é o testbench: quem usa o circuito, aplica entradas e confere as "
             "saídas."),
        item("O <b>construtor</b> é o Verilator: pega a planta (o código) e constrói uma casa de "
             "verdade, onde dá para andar (um programa executável)."),
        P("As quatro medidas da ferramenta são quatro perguntas diferentes sobre essa casa e esse "
          "inspetor."),
        Spacer(1, 3), quadro,
        nota("As quatro medidas da Bancada RTL, cada uma respondendo a uma pergunta diferente."),
        H1("1. Cobertura: os sensores nos cômodos"),
        caixa(["<b>Em uma frase:</b> coloco um contador em cada cômodo, deixo a festa acontecer "
               "e, no fim, leio quantos cômodos foram realmente usados."],
              fundo=VERDE, borda=VERDE_BORDA),
        P("Não dá para saber por fora quais partes do circuito o teste exercitou. Então usa-se "
          "um truque: instalar um sensor de passagem em cada ponto do circuito, rodar o teste e, "
          "no fim, ler os sensores. O arquivo coverage.dat é a folha onde esses contadores são "
          "anotados no fim da festa."),
        P("O arquivo nasce em três momentos, e há uma diferença importante entre eles."),
        item("<b>Passo 1: pedir a casa com sensores.</b> Ao mandar construir o circuito, a "
             "ferramenta acrescenta o pedido --coverage: \"instale um sensor em cada cômodo\". "
             "Isso não mede nada e não cria o arquivo. Só deixa a casa pronta, com os sensores "
             "zerados."),
        item("<b>Passo 2: a festa acontece.</b> A simulação roda. O testbench anda pela casa e, "
             "a cada passagem, o contador daquele cômodo sobe. Tudo ainda está na memória."),
        item("<b>Passo 3: a casa anota a folha.</b> Ao terminar, o próprio programa simulado "
             "passa em cada cômodo, lê o sensor e escreve o coverage.dat. Quem grava é a própria "
             "casa, não um comando separado."),
        P("Um detalhe importante: quando o teste acha um erro grave, a festa termina de repente "
          "(o \"parem tudo\" do $fatal). Para não perder os números justo nos casos de erro, a "
          "casa da bancada anota a folha antes de todos saírem correndo. Assim o coverage.dat "
          "sai completo tanto quando o teste passa quanto quando reprova."),
        P("No fim, a ferramenta lê a folha e faz uma conta simples: quantos cômodos existem no "
          "total (só os da casa) e quantos tiveram ao menos uma passagem. Se a casa tem 14 "
          "cômodos e 13 foram usados, a cobertura é 13/14. Nada é inventado: é contagem direta "
          "da folha."),
        Spacer(1, 4), cadeia,
        nota("A cadeia do coverage.dat: a opção --coverage só instala os sensores na construção; "
             "quem grava o arquivo é a simulação rodando; a ferramenta só lê."),
        CondPageBreak(70 * mm),
        H1("2. Mutação: sabotar a casa para testar o inspetor"),
        caixa(["<b>Em uma frase:</b> estrago a casa de propósito e vejo se o inspetor percebe. "
               "Se ele apita em todos os defeitos, é confiável. Se passa direto por alguns, tem "
               "pontos cegos."], fundo=LARANJA, borda=LARANJA_BORDA),
        P("Atenção: a mutação não mede o circuito, ela mede o testbench. A cobertura diz por "
          "quais cômodos o inspetor andou, mas andar não é inspecionar. Um inspetor pode "
          "percorrer a casa inteira e não reparar em nada errado. A mutação prova que o teste "
          "realmente confere as saídas."),
        P("Como funciona, passo a passo:"),
        item("<b>Só faz sentido se o inspetor aprova a casa boa.</b> Se o testbench já reprova o "
             "circuito correto, ele está confuso, e a mutação nem começa."),
        item("<b>Sabotar só onde funciona.</b> O defeito é plantado dentro da lógica de verdade "
             "(blocos always e assign), nunca em declarações ou larguras, que gerariam um "
             "\"defeito falso\"."),
        item("<b>Um defeito por vez.</b> Cada mutante tem um único erro. Assim, se o inspetor "
             "apita, sabe-se exatamente qual defeito ele viu. Por exemplo: trocar um + por -, um "
             "&gt; por &lt;=, um E por OU, zerar uma constante ou inverter um if."),
        item("<b>Espalhar pela casa toda.</b> Em vez de pegar os primeiros defeitos, que num "
             "circuito grande caem todos no mesmo canto, a casa é dividida em 4 partes e "
             "pega-se um defeito de cada, alternando. O teto é de 4 defeitos, para a prova ser "
             "rápida."),
        item("<b>Descartar sabotagem que derruba a casa.</b> Se o circuito com o defeito nem "
             "compila, ele não conta, e o próximo candidato entra no lugar. Só valem casas "
             "defeituosas, porém de pé."),
        item("<b>Soltar o inspetor.</b> Roda-se o mesmo testbench em cada versão defeituosa. Se o "
             "teste falha, o defeito foi detectado (mutante morto, bom sinal). Se a casa trava e "
             "a visita passa do tempo, também conta como detectado. Se o teste passa mesmo com o "
             "defeito, o mutante sobreviveu (ponto cego)."),
        P("Por testbench, a nota é o mutation score: mortos divididos pelo total de defeitos "
          "válidos. Por exemplo, 3 mortos em 4 dá 75%. No TCC, o resultado principal é o score "
          "efetivo: soma os defeitos encontrados por todos os inspetores e divide por 4 vezes o "
          "número de inspetores. Um inspetor que reprova até a casa boa conta como zero "
          "defeitos encontrados."),
        CondPageBreak(60 * mm),
        H1("3. Complexidade (ICV): a nota de dificuldade da casa"),
        caixa(["<b>Em uma frase:</b> antes de contratar o inspetor, quero saber o quão difícil é "
               "aquela casa. Um barraco de um cômodo é fácil. Uma mansão de três andares com "
               "elevador e alarme é difícil."], fundo=ROXO, borda=ROXO_BORDA),
        P("O ICV não roda nada: ele só lê a planta da casa (o texto do RTL) e dá uma nota de "
          "dificuldade. Serve para organizar o experimento, garantindo que os circuitos tenham "
          "dificuldades variadas, do barraco à mansão, e não só casas fáceis. Ele soma quatro "
          "quesitos, cada um com um peso."),
        tabela(["Quesito", "Pergunta", "Peso"],
               [["Tamanho (P<sub>LOC</sub>)", "Quantos cômodos tem? (linhas de código)", "30%"],
                ["Estados (P<sub>FSM</sub>)", "Quantos modos de funcionar? (dia, noite, "
                 "alarme...)", "30%"],
                ["Portas (P<sub>IO</sub>)", "Quantas portas e janelas para o mundo externo?",
                 "20%"],
                ["Tipo de lógica (P<sub>LOG</sub>)", "Que instalação usa? (contas, deslocamento, "
                 "estruturas replicadas)", "20%"]],
               [45 * mm, 109 * mm, 20 * mm]),
        P("Cada quesito vira uma nota de 0 a 3. A soma ponderada dá um número de 0 a 3, que "
          "classifica o circuito em Fácil, Média, Alta ou Muito Alta. Dois cuidados valem ser "
          "citados na banca."),
        item("As faixas foram calibradas para os circuitos do estudo (HDLBits e cores abertos "
             "pequenos, com ICV de cerca de 0,5 a 2,5). Não é uma escala universal: ela foi "
             "ajustada ao conjunto de módulos."),
        item("Antes de contar, a planta é limpa: tira comentários e descarta código desligado "
             "(ifdef inativo), para medir a casa que de fato é construída, e não os rabiscos da "
             "planta."),
        H1("4. Status: a triagem inicial (compilou, executou, passou)"),
        P("Estes três vêm antes de tudo. Eles formam uma corrente: se um falha, os seguintes nem "
          "acontecem."),
        item("<b>Compilou?</b> \"A casa fica de pé?\" O construtor conseguiu montar o circuito a "
             "partir da planta. Se nem constrói (erro de sintaxe), tudo para aqui."),
        item("<b>Executou?</b> \"Dá para abrir a casa e andar dentro?\" A simulação rodou sem "
             "travar nem estourar o tempo. É diferente de \"passou\": a festa aconteceu, seja "
             "qual for o resultado."),
        item("<b>Passou?</b> \"O inspetor aprovou?\" O testbench rodou e não achou nenhuma saída "
             "errada. Se gritou erro ($fatal), reprovou."),
        P("A ordem importa: sem compilar, nada roda; sem passar no circuito original, a mutação "
          "nem começa."),
        H1("O quadro completo"),
        caixa(["O status diz se funciona. A cobertura diz o alcance do teste. A mutação diz a "
               "qualidade do teste. O ICV garante que o desafio seja variado. Juntas, elas "
               "respondem à pergunta central do trabalho: qual estratégia de prompt gera "
               "testbenches que não só passam, mas cobrem mais e pegam mais defeitos."]),
    ]
    construir("analogias_bancada_rtl.pdf", "Bancada RTL: as métricas explicadas por analogias", s)


# ==========================================================================
# 6. prova_cobertura.pdf (detector de "11")
# ==========================================================================
COMANDOS_D11 = r"""# 1) criar a pasta e salvar dut.v e tb.v (o código das páginas anteriores)
cd ~ && mkdir -p prova_data && cd prova_data

# 2) compilar COM --coverage e rodar a simulação (gera coverage.dat)
verilator --binary --timing --coverage -Wno-fatal -Wno-DECLFILENAME \
  -Wno-WIDTH -Wno-UNOPTFLAT --top-module tb -o sim dut.v tb.v
./obj_dir/sim ; echo "codigo de saida (0 = passou): $?"

# 3) contar a cobertura direto no coverage.dat (coberto = contagem >= 1)
awk '/^C/ && /dut\.v/ {n++; if ($NF+0>=1) c++} \
  END{printf "geral : %d/%d = %.1f%%\n", c,n,100*c/n}' coverage.dat
awk '/^C/ && /dut\.v/ && /v_line/ {n++; if ($NF+0>=1) c++} \
  END{printf "linha : %d/%d\n", c,n}' coverage.dat
awk '/^C/ && /dut\.v/ && /v_branch/ {n++; if ($NF+0>=1) c++} \
  END{printf "desvio: %d/%d\n", c,n}' coverage.dat
awk '/^C/ && /dut\.v/ && /v_toggle/ {n++; if ($NF+0>=1) c++} \
  END{printf "toggle: %d/%d\n", c,n}' coverage.dat"""

COMENTARIO_D11 = """# --- PONTOS DO dut.v (os únicos que contam) ---
l=12 v_line   block  6 -> bloco always @(posedge clk): rodou 6x (uma por borda do clock). COBERTO
l=13 v_branch if     1 -> rst=1 (reset inicial): tomado 1x. COBERTO
l=13 v_branch else   5 -> rst=0 (operação normal): tomado 5x. COBERTO
l=17 v_line   case   2 -> braço do estado S0 executado 2x. COBERTO
l=17 v_branch if     2 -> in=1 em S0: tomado 2x. COBERTO
l=17 v_branch else   0 -> in=0 em S0: NUNCA tomado. NÃO COBERTO
l=18 v_line   case   2 -> braço do estado S1 executado 2x. COBERTO
l=18 v_branch if     1 -> in=1 em S1 (vai para S2): 1x. COBERTO
l=18 v_branch else   1 -> in=0 em S1 (volta para S0): 1x. COBERTO
l=19 v_line   case   1 -> braço do estado S2 executado 1x. COBERTO
l=19 v_branch if     0 -> in=1 em S2: NUNCA tomado. NÃO COBERTO
l=19 v_branch else   1 -> in=0 em S2 (volta para S0): 1x. COBERTO
l=20 v_line   case   0 -> braço default: NUNCA executado. NÃO COBERTO
l=2  v_toggle clk   11 -> o clock alternou. COBERTO
l=3  v_toggle rst    2 -> rst subiu e desceu. COBERTO
l=4  v_toggle in     4 -> in teve 4 transições. COBERTO
l=5  v_toggle out    2 -> out subiu (viu "11") e desceu. COBERTO
l=8  v_toggle state[0] 4 -> bit 0 do estado: 4 transições. COBERTO
l=8  v_toggle state[1] 2 -> bit 1 do estado: 2 transições. COBERTO

# --- RESULTADO (coberto = contagem >= 1) ---
# LINHA   (v_line)   : 4/5  (faltou l=20, o default do case)
# DESVIO  (v_branch) : 6/8  (faltou o else da l=17 e o if da l=19)
# TOGGLE  (v_toggle) : 6/6  (todos os sinais alternaram)
# GERAL              : 16/19 = 84,2%"""


def doc_prova_cobertura():
    s = cabecalho("Prova de cobertura na mão: detector de sequência \"11\"",
                  "Módulo, testbench, comandos, resultados e o coverage.dat cru e comentado. "
                  "Reproduza no Verilator e confira que os números batem.")
    s += [
        P("Este documento permite que qualquer pessoa comprove, manualmente, que a medição de "
          "cobertura funciona. Basta ter o Verilator 5.x, salvar os dois arquivos abaixo, rodar os "
          "comandos e comparar com os resultados registrados aqui. Tudo foi gerado por execução "
          "real no Verilator 5.032 e conferido de novo em 18/11/2026."),
        H1("A analogia (para entender o que está sendo medido)"),
        caixa(["Coloco um contador em cada cômodo de uma casa, deixo a festa acontecer e, no fim, "
               "leio quantos cômodos foram realmente usados. Essa folha de contagens é o "
               "coverage.dat."], fundo=VERDE, borda=VERDE_BORDA),
        P("A casa é o módulo (o circuito). Os convidados são o testbench, que anda pela casa "
          "aplicando entradas e conferindo saídas. Ao compilar com " + c("--coverage") + ", o "
          "Verilator instala um sensor em cada ponto do circuito (trechos de código, cada lado de "
          "um if, cada bit de sinal). Quando a simulação roda, cada passagem faz o contador "
          "daquele ponto subir. No fim, o próprio programa simulado grava o coverage.dat com "
          "esses números. Contar a cobertura é só ler essa folha: ponto com contagem maior ou "
          "igual a 1 foi visitado (coberto); contagem 0 não foi. Neste exemplo, a casa tem 19 "
          "cômodos e 16 foram usados (84,2%)."),
        H1("1. Módulo sob teste (dut.v)"),
        P("Uma máquina de estados que liga a saída " + c("out") + " quando vê dois 1 seguidos na "
          "entrada " + c("in") + ". Os números à esquerda são as linhas do arquivo, as mesmas que "
          "aparecem no coverage.dat (campo " + c("l=") + ")."),
        codigo(ler("detector11_dut.v"), numerar=True),
        junto(H1("2. Testbench (tb.v)"),
              P("Aplica uma sequência de bits, confere " + c("out") + " a cada passo e encerra "
                "com " + c("$fatal") + " se houver erro."),
              codigo(ler("detector11_tb.v"), numerar=True)),
        CondPageBreak(95 * mm),
        H1("3. Comandos para rodar na mão"),
        P("No terminal Linux (WSL/Ubuntu), dentro da pasta com dut.v e tb.v:"),
        codigo(COMANDOS_D11, tam=7.8),
        caixa(["<b>Atenção.</b> Com " + c("--binary") + ", o coverage.dat só é gravado quando a "
               "simulação termina normalmente (no " + c("$finish") + "). Se o testbench encerrar "
               "com " + c("$fatal") + ", o programa aborta e o arquivo não é gravado (conferido "
               "com uma checagem errada de propósito: código de saída 134 e nenhum coverage.dat). "
               "A bancada não tem essa limitação, porque compila com o harness "
               + c("sim/main.cpp") + "."], fundo=AMARELO, borda=OCRE),
        H1("4. Resultados obtidos (execução real)"),
        codigo("codigo de saida (0 = passou): 0\ngeral : 16/19 = 84.2%\nlinha : 4/5\n"
               "desvio: 6/8\ntoggle: 6/6"),
        tabela(["Métrica", "Resultado", "Observação"],
               [["Compilou", "sim", "o Verilator retornou 0"],
                ["Passou", "sim", "código de saída 0 (sem $fatal)"],
                ["Cobertura de linha", "4/5", "faltou o default do case"],
                ["Cobertura de desvio", "6/8", "faltou in=0 em S0 e in=1 em S2"],
                ["Cobertura de alternância", "6/6", "todos os sinais alternaram"],
                ["Cobertura geral", "16/19 = 84,2%", "soma dos pontos do dut.v"]],
               [50 * mm, 32 * mm, 92 * mm]),
        nota("O TCC usa as três coberturas separadas (linha, desvio e alternância). A cobertura "
             "geral aparece aqui só para fechar a conta."),
        H1("5. O arquivo coverage.dat (cru)"),
        P("Cada linha " + c("C '...' N") + " é um ponto de cobertura. O número final N é quantas "
          "vezes o ponto foi exercitado. Só os pontos com " + c("f=dut.v") + " entram na conta."),
        codigo("# SystemC::Coverage-3\n" + ler("detector11_coverage.txt").rstrip("\n") +
               "\n( ... depois vêm os pontos do tb.v, que NÃO contam para a cobertura )", tam=7.2),
        nota("No arquivo real, os separadores são caracteres de controle invisíveis (^A e ^B). "
             "Aqui foram trocados por | e = para ficar legível."),
        CondPageBreak(110 * mm),
        H1("6. O mesmo coverage.dat, comentado"),
        P("Cada ponto do dut.v traduzido para linguagem comum, com o resultado explicado."),
        codigo(COMENTARIO_D11, tam=7.0),
        nota("O assign da linha 10 não aparece como ponto de linha. A saída " + c("out") + " é "
             "medida pela alternância (l=5)."),
        H1("7. Por que 84,2% (e não 100%)"),
        P("Os três pontos não cobertos contam uma história real do teste. Não são defeito da "
          "medição."),
        item("<b>in=0 estando em S0:</b> o testbench só ficou em S0 com in=1, então o else da "
             "linha 17 nunca disparou."),
        item("<b>in=1 estando em S2:</b> chegou-se a S2, mas logo veio in=0, então o if da linha "
             "19 nunca disparou."),
        item("<b>default do case (linha 20):</b> o estado só assumiu S0, S1 e S2. O valor 3 é "
             "inalcançável em operação normal."),
        P("Ou seja, dá para dizer exatamente o que faltou exercitar. A métrica é real, rastreável "
          "até o bit e interpretável. Rodando na mão, os mesmos números aparecem."),
        H1("8. Comprovação de que a bancada mede certo"),
        P("A bancada não reimplementa a medição de cobertura. Ela usa a mesma instrumentação do "
          "Verilator (" + c("--coverage") + "), lê o mesmo arquivo (coverage.dat) e aplica o mesmo "
          "critério da rota manual: conta só os pontos do dut.v e considera coberto o ponto com "
          "contagem maior ou igual a 1. A única diferença é que a bancada compila com o harness "
          + c("sim/main.cpp") + " em vez de " + c("--binary") + ", para gravar a cobertura também "
          "quando o testbench falha."),
        P("A comprovação é empírica. Submetendo este mesmo par à bancada, ela reporta os mesmos "
          "valores obtidos na mão: compilou e passou, linha 4/5, desvio 6/8, alternância 6/6 e "
          "geral 16/19 (84,2%). O mesmo foi conferido com o detector de 101 e com o exemplo do "
          "script de verificação manual. A execução manual funciona, portanto, como uma "
          "verificação independente: confirma, ponto a ponto, que os números da ferramenta "
          "correspondem à simulação, e não a um cálculo próprio ou a valores fixos."),
        caixa(["<b>Em resumo:</b> a bancada só orquestra o Verilator e a leitura do coverage.dat. "
               "Rodar os mesmos passos na mão e obter os mesmos números mostra que a medição da "
               "ferramenta é real e correta."]),
    ]
    construir("prova_cobertura.pdf", "Prova de cobertura na mão: detector de \"11\"", s)


# ==========================================================================
# 7. prova_fsm_completo.pdf (detector de "101")
# ==========================================================================
MUTANTES_D101 = """#1 l11  if (rst)                   -> if (!rst)                    [MORTO]
#2 l15  A: state <= x ? B : A;     -> A: state <= x ? A : B;       [MORTO]
#3 l17  C: state <= x ? D : A;     -> C: state <= x ? A : D;       [MORTO]
#4 l24  assign y = (state == D);   -> assign y = (state != D);     [MORTO]"""

COMENTARIO_D101 = """# cabeçalho: ignorado (não começa com 'C ')
# SystemC::Coverage-3

# ===== PONTOS DO dut.v (14 pontos, ENTRAM na conta) =====
# --- LINHA (v_line): trechos executáveis. Cobertos = 5 de 6 ---
l10 v_line   block    = 7   # bloco always executou 7x            -> coberto
l15 v_line   case A   = 1   # braço A do case                     -> coberto
l16 v_line   case B   = 2   # braço B                             -> coberto
l17 v_line   case C   = 2   # braço C                             -> coberto
l18 v_line   case D   = 1   # braço D                             -> coberto
l19 v_line   default  = 0   # braço default NUNCA executado       -> falta
# --- DESVIO (v_branch): os dois lados do if. Cobertos = 2 de 2 ---
l11 v_branch if       = 1   # if (rst) verdadeiro 1x              -> coberto
l11 v_branch else     = 6   # if (rst) falso 6x                   -> coberto
# --- ALTERNÂNCIA (v_toggle): um ponto por bit. Cobertos = 6 de 6 ---
l2  v_toggle clk      = 13  # clk mudou                           -> coberto
l3  v_toggle rst      = 2   # rst mudou                           -> coberto
l4  v_toggle x        = 5   # x mudou                             -> coberto
l5  v_toggle y        = 3   # y mudou                             -> coberto
l8  v_toggle state[0] = 5   # bit 0 de state mudou                -> coberto
l8  v_toggle state[1] = 3   # bit 1 de state mudou                -> coberto

# ===== PONTOS DO tb.v (IGNORADOS: a bancada filtra só o dut.v) =====
# -> não entram em nenhum número (a cobertura é do MÓDULO, não do testbench)"""


def doc_prova_fsm():
    s = cabecalho("Prova de rastreabilidade: detector de sequência 101",
                  "Módulo, testbench, resultado da bancada e o coverage.dat comentado (de onde sai "
                  "cada número)")
    s += [
        P("Este documento mostra, de ponta a ponta, de onde vêm os resultados da bancada. Ele "
          "traz (1) o resultado que a bancada devolve, (2) o módulo dut.v, (3) o testbench tb.v e "
          "(4) o arquivo oficial de cobertura do Verilator, o coverage.dat, comentado linha a "
          "linha e ligado ao número final. Os valores foram conferidos de novo em 18/11/2026, no "
          "Verilator 5.032."),
        H1("1. Resultado que a bancada devolve"),
        tabela(["Métrica", "Valor", "Vem de"],
               [["Compilou / Executou / Passou", "sim / sim / sim",
                 "código de retorno do Verilator e do programa simulado"],
                ["Cobertura de linha (v_line)", "5/6 = 83,3%", "trechos executáveis"],
                ["Cobertura de desvio (v_branch)", "2/2 = 100%", "os dois lados do if (rst)"],
                ["Cobertura de alternância (v_toggle)", "6/6 = 100%",
                 "bits de sinal que mudaram de valor"],
                ["Teste de mutação", "4/4 detectados", "mutantes que o testbench pegou"],
                ["ICV", "0,8 (Fácil)", "23 linhas (1), 4 estados (1), 4 portas (1), lógica "
                 "básica (0)"]],
               [55 * mm, 33 * mm, 86 * mm]),
        nota("A bancada também mostra a cobertura geral (13/14 = 92,9%) e uma cobertura de "
             "máquina de estados aproximada (4/5). O TCC não usa essas duas."),
        H2("Mutantes avaliados (todos detectados)"),
        codigo(MUTANTES_D101, tam=7.8),
        H2("Saída da simulação"),
        codigo("[PASSOU] seq_detector 101 ok\n- .../tb.v:28: Verilog $finish"),
        junto(H1("2. Módulo (dut.v)"), codigo(ler("detector101_dut.v"), numerar=True, tam=7.5)),
        junto(H1("3. Testbench (tb.v)"), codigo(ler("detector101_tb.v"), numerar=True, tam=7.5)),
        CondPageBreak(120 * mm),
        H1("4. O coverage.dat comentado (de onde vem cada número)"),
        P("O Verilator gera este arquivo ao rodar a simulação compilada com " + c("--coverage")
          + ". Cada linha iniciada por C é um ponto de cobertura. O número no fim é quantas vezes "
          "ele foi exercitado (0 = não coberto). Abaixo, a versão legível, com um comentário em "
          "cada linha explicando o que ela vira no resultado."),
        codigo(COMENTARIO_D101, tam=7.4),
        H1("5. Como a bancada transforma isso nos números"),
        P("A função " + c("ler_cobertura") + " do " + c("app.py") + " percorre o arquivo, descarta "
          "o cabeçalho e todos os pontos do tb.v e, sobre os 14 pontos do dut.v, conta quantos "
          "têm contagem maior ou igual a 1."),
        codigo("LINHA   = 5/6   (só o default, l19, ficou em 0)\n"
               "DESVIO  = 2/2   (if e else, os dois exercitados)\n"
               "TOGGLE  = 6/6   (todos os sinais mudaram de valor)\n"
               "----------------------------------------------------\n"
               "GERAL   = (5+2+6) / (6+2+6) = 13/14 = 92,9%  (mostrada, mas não usada no TCC)"),
        P("<b>Regra única:</b> um ponto é coberto se foi exercitado ao menos uma vez. A bancada "
          "aplica essa regra sobre o coverage.dat, o dado oficial do Verilator, contando só os "
          "pontos do dut.v. É exatamente o que este documento mostra, ponto a ponto."),
        CondPageBreak(90 * mm),
        H1("6. Como visualizar o coverage.dat no VS Code"),
        P("O coverage.dat tem bytes de controle, que aparecem como blocos vermelhos no editor. "
          "Nenhuma extensão decodifica esse formato do Verilator diretamente. Há dois caminhos "
          "práticos."),
        H2("Opção A: ler o texto do arquivo"),
        P("Gera uma cópia legível, com os separadores trocados, e abre no editor:"),
        codigo("cd ~/prova_fsm\nsed 's/\\x01/ | /g; s/\\x02/=/g' coverage.dat > coverage_legivel.txt"),
        P("Abra o coverage_legivel.txt: ele fica limpo, com | e = no lugar dos blocos vermelhos. "
          "Não precisa de extensão."),
        H2("Opção B: ver a cobertura colorida no próprio código"),
        P("Pinta as linhas cobertas de verde e as não cobertas de vermelho, na margem do editor, "
          "usando a extensão Coverage Gutters (ryanluker.vscode-coverage-gutters)."),
        codigo("# 1) instale a extensão 'Coverage Gutters' no VS Code\n"
               "# 2) gere o arquivo LCOV com o nome que a extensão procura:\n"
               "cd ~/prova_fsm\n"
               "verilator_coverage --write-info lcov.info coverage.dat\n"
               "# 3) abra a pasta ~/prova_fsm, abra o dut.v, aperte Ctrl+Shift+P e rode\n"
               "#    'Coverage Gutters: Display Coverage' (ou clique em Watch na barra de status)"),
        nota("Ressalva: o Coverage Gutters lê o formato LCOV, que só representa linhas. A "
             "alternância não aparece. Os números por tipo continuam vindo do "
             "verilator_coverage --annotate ou da contagem direta (bancada)."),
        tabela(["Quero...", "Como"],
               [["Ler o texto do .dat sem os blocos vermelhos",
                 c("sed ... > coverage_legivel.txt") + " (opção A)"],
                ["Ver verde e vermelho no meu código", "extensão Coverage Gutters + lcov.info "
                 "(opção B)"],
                ["Ver todos os tipos (linha, desvio, alternância)",
                 c("verilator_coverage --annotate") + " ou a bancada"]],
               [75 * mm, 99 * mm]),
    ]
    construir("prova_fsm_completo.pdf", "Prova de rastreabilidade: detector de 101", s)


# ==========================================================================
# 8. script_teste_manual_comentado.pdf
# ==========================================================================
SAIDA_SCRIPT = """==== 1) COMPILAR ====
compilou: OK
==== 2) EXECUTAR (0 = passou) ====
passou (codigo de saida): 0
==== 3) COBERTURA ====
geral : 49/61 = 80.3%
linha : 8/9
desvio: 17/18
toggle: 24/34
==== 4) MUTACAO (4 mutantes da bancada) ====
  #1 == -> !=       (linha 25) -> codigo 134 = MORTO (detectado)
  #2 if(data)->if(!data) (l54) -> codigo 134 = MORTO (detectado)
  #3 10'd0 -> 10'd1  (linha 76) -> codigo 134 = MORTO (detectado)
  #4 + -> -          (linha 92) -> codigo 134 = MORTO (detectado)"""

RUN_MUT = """run_mut() {
  cp dut.v mut.v; sed -i "$2" mut.v; rm -f obj_dir/mut
  if verilator --binary --timing -Wno-fatal -Wno-DECLFILENAME -Wno-WIDTH \\
       -Wno-UNOPTFLAT --top-module tb -o mut mut.v tb.v > /dev/null 2>&1; then
    ./obj_dir/mut > /dev/null 2>&1; code=$?
    [ $code -ne 0 ] && echo "  $1 -> codigo $code = MORTO (detectado)" \\
                    || echo "  $1 -> codigo $code = SOBREVIVEU"
  else
    echo "  $1 -> nao compilou"
  fi
}"""

CHAMADAS_MUT = """run_mut "#1 == -> !=       (linha 25)" '25s/==/!=/'
run_mut "#2 if(data)->if(!data) (l54)" '54s/if (data)/if (!data)/'
run_mut "#3 10'd0 -> 10'd1  (linha 76)" "76s/10'd0/10'd1/"
run_mut "#4 + -> -          (linha 92)" "92s/+ 1'b1/- 1'b1/\""""


def doc_script_manual():
    s = cabecalho("Script de verificação manual, comentado",
                  "Como o script testa um módulo RTL no Verilator e reproduz os resultados da "
                  "bancada")
    s += [
        P("Este documento explica, parte por parte, o script que cria os arquivos, compila, "
          "simula, mede a cobertura (linha, desvio e alternância) e roda o teste de mutação, "
          "obtendo os mesmos números da aplicação web. O código completo do módulo e do "
          "testbench está no apêndice, com as linhas numeradas."),
        caixa(["<b>Sobre o módulo usado.</b> É um exemplo: um detector da sequência 1101 seguido "
               "de um temporizador, com 7 estados nomeados (S_SEARCH0 a S_DONE). Ele não é o "
               "Fancytimer do experimento do TCC, que tem outra implementação, com 4 estados "
               "numéricos."], fundo=AMARELO, borda=OCRE),
        H1("1. Preparar a pasta"),
        codigo("cd ~/teste_manual && rm -rf obj_dir anotado coverage.dat mut.v"),
        item(c("cd ~/teste_manual") + ": entra na pasta de trabalho."),
        item(c("rm -rf ...") + ": apaga o que sobrou da rodada anterior (o build em obj_dir, o "
             "relatório anotado, o coverage.dat e o mutante mut.v), garantindo um resultado "
             "limpo."),
        H1("2. Criar os arquivos de entrada"),
        codigo("cat > dut.v <<'EOF'\n...conteúdo do módulo...\nEOF"),
        P("Isso é um here-document: " + c("cat > dut.v") + " grava no arquivo dut.v tudo o que "
          "vier até a marca EOF, sem abrir editor. O " + c("'EOF'") + " entre aspas impede o bash "
          "de interpretar símbolos como " + c("$finish") + " ou " + c("!") + ", e tudo é gravado "
          "literalmente. O mesmo vale para o " + c("cat > tb.v <<'EOF' ... EOF") + ", que cria o "
          "testbench (código completo no apêndice)."),
        H1("3. Compilar (o módulo compilou?)"),
        codigo("verilator --binary --timing --coverage \\\n"
               "  -Wno-fatal -Wno-DECLFILENAME -Wno-WIDTH -Wno-UNOPTFLAT \\\n"
               "  --top-module tb -o sim dut.v tb.v > /dev/null 2>&1 \\\n"
               "  && echo \"compilou: OK\" || echo \"compilou: ERRO\""),
        item(c("--binary") + ": gera um executável pronto para rodar."),
        item(c("--timing") + ": aceita os atrasos (" + c("#5") + ", " + c("#1") + ") do "
             "testbench."),
        item(c("--coverage") + ": instrumenta o código para coletar cobertura."),
        item(c("-Wno-fatal") + " e os outros " + c("-Wno-*") + ": avisos (latch, largura...) não "
             "travam a compilação. São os mesmos da bancada."),
        item(c("--top-module tb") + ": o topo da simulação é o módulo tb."),
        item(c("-o sim") + ": nome do executável de saída."),
        item(c("> /dev/null 2>&1") + ": descarta a saída do compilador (esconde as linhas do "
             "g++)."),
        item(c("&& echo OK || echo ERRO") + ": imprime se compilou."),
        H1("4. Executar (executou? passou?)"),
        codigo("./obj_dir/sim > /dev/null 2>&1; echo \"passou (codigo de saida): $?\""),
        item(c("./obj_dir/sim") + ": roda a simulação, que grava o coverage.dat."),
        item(c("$?") + ": guarda o código de saída do programa anterior. 0 = passou (chegou ao "
             + c("$finish") + "); diferente de 0 = falhou (algum " + c("$fatal") + ")."),
        nota("Com " + c("--binary") + ", o coverage.dat só é gravado quando a simulação termina "
             "normalmente. Se o testbench falhar com " + c("$fatal") + ", não haverá cobertura "
             "para contar. A bancada grava nos dois casos, porque usa o harness "
             + c("sim/main.cpp") + "."),
        H1("5. Cobertura (os comandos awk)"),
        P("No coverage.dat, cada ponto de cobertura é uma linha que começa com C e termina com um "
          "número (quantas vezes foi exercitado). Cada awk conta esses pontos:"),
        codigo("awk '/^C/ && /dut\\.v/ {n++; if ($NF+0>=1) c++} \\\n"
               "  END{printf \"geral : %d/%d = %.1f%%\\n\", c, n, 100*c/n}' coverage.dat"),
        item(c("/^C/") + ": só linhas que começam com C (os pontos)."),
        item(c("&& /dut\\.v/") + ": e que sejam do arquivo dut.v (só o módulo, não o "
             "testbench)."),
        item(c("n++") + ": soma 1 no total de pontos."),
        item(c("if ($NF+0>=1) c++") + ": se a contagem (o último campo, " + c("$NF") + ") for "
             "maior ou igual a 1, soma 1 nos cobertos."),
        item(c("END{printf ...}") + ": imprime cobertos/total e a porcentagem."),
        P("As três linhas seguintes são iguais, só filtrando o tipo do ponto:"),
        codigo("awk '... && /v_line/   ...'  -> cobertura de LINHA\n"
               "awk '... && /v_branch/ ...'  -> cobertura de DESVIO\n"
               "awk '... && /v_toggle/ ...'  -> cobertura de ALTERNÂNCIA"),
        P("Esse é exatamente o critério da bancada: coberto é o ponto exercitado ao menos uma "
          "vez, contando só os pontos do dut.v. A cobertura geral aparece na bancada, mas o TCC "
          "usa só as três coberturas separadas."),
        H1("6. Teste de mutação"),
        P("Primeiro, o script define uma função que avalia um mutante:"),
        codigo(RUN_MUT, tam=7.8),
        item(c("cp dut.v mut.v") + ": copia o módulo original."),
        item(c("sed -i \"$2\" mut.v") + ": aplica uma alteração na cópia. O " + c("$2") + " é a "
             "expressão do sed. Por exemplo, " + c("25s/==/!=/") + " troca == por != na linha "
             "25."),
        item(c("rm -f obj_dir/mut") + ": apaga o executável anterior, para não rodar o mutante "
             "errado."),
        item(c("if verilator ... then") + ": compila o mutante. Se compilar, roda e lê o "
             + c("$?") + ": diferente de 0 = MORTO (o testbench pegou); igual a 0 = SOBREVIVEU."),
        item("Se não compilar, marca \"nao compilou\"."),
        P("Depois, chama a função uma vez para cada um dos 4 mutantes que a bancada listou, pelo "
          "número da linha, para bater exatamente:"),
        codigo(CHAMADAS_MUT, tam=7.8),
        caixa(["<b>Erro comum.</b> O " + c("!") + " de " + c("if (!data)") + " dentro de aspas "
               "duplas faz o bash tentar expandir o histórico (" + c("!data: event not found")
               + ") e o mutante não roda. Por isso a expressão do sed do #2 usa aspas simples, que "
               "preservam o " + c("!") + "."], fundo=AMARELO, borda=OCRE),
        CondPageBreak(80 * mm),
        H1("7. Saída esperada"),
        codigo(SAIDA_SCRIPT, tam=7.8),
        P("Cada valor corresponde a um cartão da bancada: linha 8/9 (88,9%), desvio 17/18 "
          "(94,4%), alternância 24/34 (70,6%) e 4/4 mutantes mortos (score 100%). No mesmo par, a "
          "bancada lista os mesmos 4 mutantes, nas linhas 25, 54, 76 e 92. Tudo foi conferido de "
          "novo em 18/11/2026, no Verilator 5.032."),
        CondPageBreak(60 * mm),
        H1("Apêndice A: dut.v (módulo RTL)"),
        nota("As linhas 25, 54, 76 e 92 são as dos 4 mutantes."),
        codigo(ler("exemplo1101_dut.v"), numerar=True, tam=7.6),
        H1("Apêndice B: tb.v (testbench)"),
        codigo(ler("exemplo1101_tb.v"), numerar=True, tam=7.2),
    ]
    construir("script_teste_manual_comentado.pdf", "Script de verificação manual, comentado", s)


DOCS = {
    "icv": doc_icv,
    "metricas": doc_metricas,
    "mutacao": doc_mutacao,
    "visao": doc_visao_geral,
    "analogias": doc_analogias,
    "prova_cobertura": doc_prova_cobertura,
    "prova_fsm": doc_prova_fsm,
    "script": doc_script_manual,
}

if __name__ == "__main__":
    os.makedirs(SAIDA, exist_ok=True)
    for f in DOCS.values():
        f()
