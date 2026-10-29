"""Partes comuns dos PDFs de estatistica: dados da planilha, calculos basicos, estilos e referencias."""
import math
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from scipy.stats import PermutationMethod, wilcoxon

# --------------------------------------------------------------------------
# Dados: linha "Mutantes" da planilha, na ordem ZS, FS, EspZS, EspFS, PlnZS, PlnFS.
# Duas rodadas com os mesmos 10 circuitos (mesmo RTL, logo os mesmos 4 mutantes); na 2a os
# testbenches foram gerados de novo (blocos com o nome terminado em "2" na planilha).
# --------------------------------------------------------------------------
ESTR = ["ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"]
NOME_ESTR = {
    "ZS": "Zero-shot", "FS": "Few-shot",
    "EspZS": "Especialista Zero-shot", "EspFS": "Especialista Few-shot",
    "PlnZS": "Planning Zero-shot", "PlnFS": "Planning Few-shot",
}
CIRCUITOS = ["Fsm serialdp", "Exams/2012 q2fsm", "Cout Clock", "Cs450/gshare", "Lemmings1",
             "wbuart32", "Cordic", "Conwaylife", "fancytimer", "I2C Slave"]
NP = "Não passou"
PLANILHA_R1 = {
    "GPT-5.6 Luna": [
        ["4/4", "4/4", NP, "4/4", NP, "4/4"],
        ["3/4", "3/4", "3/4", "3/4", "4/4", "3/4"],
        ["4/4", "4/4", NP, "4/4", "4/4", "4/4"],
        [NP, "3/4", "3/4", NP, NP, NP],
        ["4/4", "4/4", "4/4", "4/4", "4/4", "4/4"],
        [NP, "2/4", "3/4", "3/4", "3/4", "4/4"],
        [NP, "3/4", "3/4", "3/4", NP, "3/4"],
        [NP, NP, "4/4", NP, "4/4", "4/4"],
        [NP, NP, NP, "3/4", NP, NP],
        ["Timeout", "3/4", NP, "4/4", NP, "2/4"],
    ],
    "Gemini 3.5 Flash-Lite": [
        [NP, "4/4", "4/4", "4/4", NP, "4/4"],
        ["3/4", "3/4", NP, "4/4", "3/4", "3/4"],
        [NP, "3/4", "3/4", NP, "3/4", "2/4"],
        [NP, NP, "0/4", "0/4", "1/4", NP],
        ["2/4", "4/4", "4/4", "4/4", "4/4", "4/4"],
        [NP, NP, "1/4", "1/4", "3/4", "3/4"],
        ["1/4", NP, "1/4", "1/4", "2/4", "0/4"],
        ["3/4", "3/4", "0/4", "3/4", "0/4", "3/4"],
        [NP, "4/4", "0/4", "3/4", "1/4", "1/4"],
        ["2/4", "1/4", "1/4", "4/4", NP, NP],
    ],
}
PLANILHA_R2 = {
    "GPT-5.6 Luna": [
        [NP, NP, "4/4", NP, NP, "4/4"],
        ["3/4", "4/4", "4/4", NP, "4/4", NP],
        [NP, "4/4", NP, NP, "4/4", "4/4"],
        ["3/4", "3/4", NP, "2/4", "3/4", "3/4"],
        ["4/4", "4/4", "4/4", "4/4", "4/4", "4/4"],
        ["3/4", NP, NP, "3/4", "4/4", "4/4"],
        ["2/4", NP, "2/4", "3/4", "3/4", "3/4"],
        ["4/4", "4/4", "4/4", NP, "4/4", "4/4"],
        [NP, NP, "4/4", NP, "3/4", "4/4"],
        [NP, NP, "3/4", "3/4", "2/4", "3/4"],
    ],
    "Gemini 3.5 Flash-Lite": [
        [NP, "4/4", "4/4", "4/4", NP, "4/4"],
        ["3/4", "3/4", "3/4", "3/4", "3/4", "3/4"],
        ["2/4", "3/4", NP, "2/4", "2/4", "2/4"],
        ["0/4", "1/4", NP, NP, NP, NP],
        ["4/4", "4/4", "4/4", "4/4", "4/4", "4/4"],
        ["3/4", "3/4", "3/4", "3/4", "3/4", "3/4"],
        [NP, "1/4", NP, "2/4", NP, "2/4"],
        ["3/4", "3/4", "3/4", "3/4", "0/4", "4/4"],
        [NP, "3/4", "3/4", "3/4", "3/4", "3/4"],
        ["1/4", "1/4", "3/4", "2/4", "1/4", "1/4"],
    ],
}
RODADAS = {1: PLANILHA_R1, 2: PLANILHA_R2}
MODELOS = list(PLANILHA_R1)
CURTO = {"GPT-5.6 Luna": "GPT", "Gemini 3.5 Flash-Lite": "Gemini"}
# Na 2a rodada, 2 celulas foram reavaliadas com um testbench NOVO (os outros reenvios corrigiam um
# TB colado na estrategia errada) e a planilha ficou com o 2o resultado. Aqui fica o 1o, para a
# verificacao de robustez: (modelo, circuito, estrategia) -> celula do 1o envio.
PRIMEIRO_ENVIO_R2 = {
    ("GPT-5.6 Luna", 1, 4): NP,                 # Exams/2012 q2fsm2, Planning Zero-shot (depois 4/4)
    ("Gemini 3.5 Flash-Lite", 7, 5): "0/4",     # Conwaylife2_gemini, Planning Few-shot (depois 4/4)
}


def converter(celula):
    """'3/4' -> 3 (mutantes mortos); 'Não passou' / 'Timeout' -> 0."""
    m = re.fullmatch(r"(\d)/4", celula.strip())
    return int(m.group(1)) if m else 0


def abrev(celula):
    """Celula da planilha em forma curta para as tabelas: NP = Não passou, TO = Timeout."""
    return {NP: "NP", "Timeout": "TO"}.get(celula, celula)


def celulas(modelo, rodada, primeiro_envio=False):
    tab = [list(linha) for linha in RODADAS[rodada][modelo]]
    if rodada == 2 and primeiro_envio:
        for (m, i, j), cel in PRIMEIRO_ENVIO_R2.items():
            if m == modelo:
                tab[i][j] = cel
    return tab


def valores(modelo, rodada=None, primeiro_envio=False):
    """Mutantes mortos por circuito × estratégia. Com rodada = 1 ou 2, os inteiros daquela rodada;
    sem rodada, a média das duas (0; 0,5; ...; 4), que é o valor analisado."""
    if rodada is not None:
        return [[converter(c) for c in linha] for linha in celulas(modelo, rodada, primeiro_envio)]
    r1, r2 = valores(modelo, 1), valores(modelo, 2, primeiro_envio)
    return [[(a + b) / 2 for a, b in zip(l1, l2)] for l1, l2 in zip(r1, r2)]


def wilc(x, y):
    """Wilcoxon pareado bicaudal exato de y − x (zeros descartados, postos médios).
    Retorna (ganha, perde, empata, T, p)."""
    d = [b - a for a, b in zip(x, y)]
    nz = [i for i, v in enumerate(d) if v != 0]
    ganha, perde = sum(v > 0 for v in d), sum(v < 0 for v in d)
    if not nz:
        return ganha, perde, len(d), 0.0, 1.0
    r = wilcoxon([y[i] for i in nz], [x[i] for i in nz], zero_method="wilcox",
                 method=PermutationMethod(n_resamples=max(10 ** 6, 2 ** len(nz))))
    return ganha, perde, len(d) - len(nz), float(r.statistic), float(r.pvalue)


def holm(ps):
    """p-valores ajustados por Holm (1979): o i-ésimo menor × (m − i + 1), sem deixar cair, até 1."""
    ordem = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, acc = [0.0] * len(ps), 0.0
    for pos, i in enumerate(ordem):
        acc = max(acc, min(1.0, (len(ps) - pos) * ps[i]))
        adj[i] = acc
    return adj


Q_NEMENYI_6 = 2.850     # q de Nemenyi para k = 6 e alfa = 0,05 (Demšar 2006, tabela 5a)


def nemenyi_cd(k, n):
    """Diferença crítica de postos médios do pós-teste de Nemenyi (Demšar 2006)."""
    assert k == 6
    return Q_NEMENYI_6 * math.sqrt(k * (k + 1) / (6 * n))


def postos(vals):
    """Postos 1..n em ordem crescente; empate recebe a media das posicoes ocupadas."""
    ordem = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and vals[ordem[j + 1]] == vals[ordem[i]]:
            j += 1
        for q in range(i, j + 1):
            r[ordem[q]] = (i + j) / 2 + 1
        i = j + 1
    return r


def br(x, nd=None):
    """Numero no formato brasileiro (virgula decimal, ponto de milhar)."""
    if nd is None:
        s = f"{x:.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# --------------------------------------------------------------------------
# Estilos
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
VERDE = colors.HexColor("#E6F4EA")
VERDE_BORDA = colors.HexColor("#2E7D32")
OCRE = colors.HexColor("#B7950B")
CINZA = colors.HexColor("#5A6470")

S = {
    "titulo": ParagraphStyle("titulo", fontName="DVB", fontSize=19, leading=23, textColor=AZUL),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=10.5, leading=14, textColor=CINZA),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=13.5, leading=17, textColor=AZUL,
                         spaceBefore=14, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=11, leading=14, spaceBefore=9, spaceAfter=4),
    "corpo": ParagraphStyle("corpo", fontName="DV", fontSize=9.8, leading=14.2, spaceAfter=5),
    "item": ParagraphStyle("item", fontName="DV", fontSize=9.8, leading=14.2, leftIndent=12,
                           bulletIndent=2, spaceAfter=2),
    "nota": ParagraphStyle("nota", fontName="DV", fontSize=8.3, leading=11, textColor=CINZA,
                           spaceBefore=3, spaceAfter=6),
    "fonte": ParagraphStyle("fonte", fontName="DV", fontSize=8.3, leading=11,
                            textColor=colors.HexColor("#3D5A80"), spaceBefore=3, spaceAfter=7),
    "cel": ParagraphStyle("cel", fontName="DV", fontSize=8.3, leading=10.4, alignment=TA_CENTER),
    "celE": ParagraphStyle("celE", fontName="DV", fontSize=8.3, leading=10.4, alignment=TA_LEFT),
    "cab": ParagraphStyle("cab", fontName="DVB", fontSize=8.3, leading=10.4, alignment=TA_CENTER,
                          textColor=colors.white),
    "formula": ParagraphStyle("formula", fontName="DV", fontSize=10, leading=15),
    "codigo": ParagraphStyle("codigo", fontName="DVM", fontSize=8.6, leading=11.5),
    "legenda": ParagraphStyle("legenda", fontName="DVB", fontSize=9, leading=12, spaceBefore=6,
                              spaceAfter=3, textColor=AZUL),
    "ref": ParagraphStyle("ref", fontName="DV", fontSize=9.3, leading=13, spaceAfter=7),
}
LARG = A4[0] - 36 * mm
W8 = [33 * mm] + [20 * mm] * 6 + [21 * mm]      # circuito + 6 estrategias + coluna extra
W7 = [34 * mm] + [23.3 * mm] * 6


def P(txt, st="corpo"):
    return Paragraph(txt, S[st])


def item(txt):
    return Paragraph(txt, S["item"], bulletText="•")


def fonte(txt):
    return Paragraph("<b>Fonte:</b> " + txt, S["fonte"])


def caixa(conteudo, fundo=AZUL_CLARO, borda=AZUL, estilo="formula"):
    linhas = conteudo if isinstance(conteudo, list) else [conteudo]
    t = Table([[[P(l, estilo) for l in linhas]]], colWidths=[LARG])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fundo),
        ("LINEBEFORE", (0, 0), (0, -1), 3, borda),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def tabela(cab, linhas, larguras, destacar_ultima=False, primeira_esq=True, cor_ultima=AMARELO):
    dados = [[P(c, "cab") for c in cab]]
    for linha in linhas:
        dados.append([P(str(c), "celE" if (j == 0 and primeira_esq) else "cel")
                      for j, c in enumerate(linha)])
    t = Table(dados, colWidths=larguras, repeatRows=1)
    est = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if destacar_ultima:
        est.append(("BACKGROUND", (0, -1), (-1, -1), cor_ultima))
    t.setStyle(TableStyle(est))
    return t


# --------------------------------------------------------------------------
# Referencias (ABNT)
# --------------------------------------------------------------------------
REFS = {
    "ARCURI": "ARCURI, Andrea; BRIAND, Lionel. A practical guide for using statistical tests to "
              "assess randomized algorithms in software engineering. In: INTERNATIONAL CONFERENCE "
              "ON SOFTWARE ENGINEERING, 33., 2011, Honolulu. <b>Proceedings</b> [...]. New York: "
              "ACM, 2011. p. 1-10. DOI: 10.1145/1985793.1985795.",
    "WASSERSTEIN": "WASSERSTEIN, Ronald L.; LAZAR, Nicole A. The ASA's statement on p-values: "
                   "context, process, and purpose. <b>The American Statistician</b>, v. 70, n. 2, "
                   "p. 129-133, 2016. DOI: 10.1080/00031305.2016.1154108.",
    "DEMSAR": "DEMŠAR, Janez. Statistical comparisons of classifiers over multiple data sets. "
              "<b>Journal of Machine Learning Research</b>, v. 7, p. 1-30, 2006.",
    "FISHER": "FISHER, Ronald A. <b>Statistical methods for research workers</b>. 4. ed. "
              "Edinburgh: Oliver and Boyd, 1932.",
    "FRIEDMAN": "FRIEDMAN, Milton. The use of ranks to avoid the assumption of normality implicit "
                "in the analysis of variance. <b>Journal of the American Statistical "
                "Association</b>, v. 32, n. 200, p. 675-701, 1937. "
                "DOI: 10.1080/01621459.1937.10503522.",
    "HOLLANDER": "HOLLANDER, Myles; WOLFE, Douglas A.; CHICKEN, Eric. <b>Nonparametric "
                 "statistical methods</b>. 3. ed. Hoboken: Wiley, 2014.",
    "HOLM": "HOLM, Sture. A simple sequentially rejective multiple test procedure. "
            "<b>Scandinavian Journal of Statistics</b>, v. 6, n. 2, p. 65-70, 1979.",
    "MICROSOFT": "MICROSOFT. <b>Funções estatísticas (referência)</b>. Microsoft Suporte, 2026. "
                 "Disponível em: https://support.microsoft.com/pt-br/Excel/"
                 "statistical-functions-reference. Acesso em: 23 out. 2026.",
    "PRATT": "PRATT, John W. Remarks on zeros and ties in the Wilcoxon signed rank procedures. "
             "<b>Journal of the American Statistical Association</b>, v. 54, n. 287, "
             "p. 655-667, 1959. DOI: 10.1080/01621459.1959.10501526.",
    "SIEGEL": "SIEGEL, Sidney; CASTELLAN JR., N. John. <b>Estatística não-paramétrica para "
              "ciências do comportamento</b>. 2. ed. Porto Alegre: Artmed, 2006.",
    "VIRTANEN": "VIRTANEN, Pauli et al. SciPy 1.0: fundamental algorithms for scientific "
                "computing in Python. <b>Nature Methods</b>, v. 17, p. 261-272, 2020. "
                "DOI: 10.1038/s41592-019-0686-2.",
    "WILCOXON": "WILCOXON, Frank. Individual comparisons by ranking methods. <b>Biometrics "
                "Bulletin</b>, v. 1, n. 6, p. 80-83, 1945. DOI: 10.2307/3001968.",
}


def secao_referencias(story, chaves):
    story.append(P("Referências", "h1"))
    for k in sorted(chaves):
        story.append(P(REFS[k], "ref"))


DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                    "documentacao"))


def saida(nome):
    """Caminho do PDF: o argumento da linha de comando, ou documentacao/<nome> na raiz do repo."""
    return sys.argv[1] if len(sys.argv) > 1 else os.path.join(DOC, nome)


def construir(caminho, story, titulo):
    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 8)
        canvas.setFillColor(CINZA)
        canvas.drawString(18 * mm, 10 * mm, titulo)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title=titulo, author="veriweb")
    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
