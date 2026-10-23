"""Partes comuns dos PDFs de estatistica: dados da planilha, calculos basicos, estilos e referencias."""
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

# --------------------------------------------------------------------------
# Dados: linha "Mutantes" da planilha, na ordem ZS, FS, EspZS, EspFS, PlnZS, PlnFS
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
PLANILHA = {
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
CURTO = {"GPT-5.6 Luna": "GPT", "Gemini 3.5 Flash-Lite": "Gemini"}


def converter(celula):
    """'3/4' -> 3 (mutantes mortos); 'Não passou' / 'Timeout' -> 0."""
    m = re.fullmatch(r"(\d)/4", celula.strip())
    return int(m.group(1)) if m else 0


def valores(modelo):
    return [[converter(c) for c in linha] for linha in PLANILHA[modelo]]


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
