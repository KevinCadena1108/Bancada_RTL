"""Partes comuns dos PDFs da análise: dados da planilha, cálculos básicos e estilos.

Os testes estatísticos (Friedman, Wilcoxon, Holm, Nemenyi) saíram em 2026-11-18, junto com os PDFs
que os usavam: o TCC usa só análise descritiva. Estão no histórico do git (commit e89bd43).
"""
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


def converter(celula):
    """'3/4' -> 3 (mutantes mortos); 'Não passou' / 'Timeout' -> 0."""
    m = re.fullmatch(r"(\d)/4", celula.strip())
    return int(m.group(1)) if m else 0


def abrev(celula):
    """Celula da planilha em forma curta para as tabelas: NP = Não passou, TO = Timeout."""
    return {NP: "NP", "Timeout": "TO"}.get(celula, celula)


def celulas(modelo, rodada):
    return [list(linha) for linha in RODADAS[rodada][modelo]]


def valores(modelo, rodada=None):
    """Mutantes mortos por circuito × estratégia. Com rodada = 1 ou 2, os inteiros daquela rodada;
    sem rodada, a média das duas (0; 0,5; ...; 4), que é o valor analisado."""
    if rodada is not None:
        return [[converter(c) for c in linha] for linha in celulas(modelo, rodada)]
    r1, r2 = valores(modelo, 1), valores(modelo, 2)
    return [[(a + b) / 2 for a, b in zip(l1, l2)] for l1, l2 in zip(r1, r2)]


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
