"""Figura do processo do trabalho (fluxograma vetorial em PDF, largura 16 cm = largura do texto).

Uso (no WSL, precisa de reportlab e das fontes DejaVu do Ubuntu): python figura_processo.py [saida.pdf]
Sem argumento grava em documentacao/figuras/processo_trabalho.pdf.
"""
import os, sys
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

DV = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", DV + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", DV + "DejaVuSans-Bold.ttf"))

W, H = 160, 169  # mm
TINTA = HexColor("#1F2A36")
FAIXA = HexColor("#F3F5F8")
FAIXA_BORDA = HexColor("#9AA6B2")
ROTULO = HexColor("#DDE3EA")
PROC = HexColor("#E3EEF9")
PROC_BORDA = HexColor("#3B6EA5")
DECISAO = HexColor("#FFF3D6")
DECISAO_BORDA = HexColor("#B8860B")
FIM = HexColor("#E4F3E6")
FIM_BORDA = HexColor("#3C8D4A")
NEG = HexColor("#F8E4E2")
NEG_BORDA = HexColor("#B04A3F")

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "documentacao", "figuras", "processo_trabalho.pdf")
c = canvas.Canvas(SAIDA, pagesize=(W * mm, H * mm))
c.setTitle("Processo do trabalho")


def Y(topo):
    """Converte coordenada medida do topo (mm) para a do reportlab."""
    return (H - topo) * mm


def texto(cx, cy, linhas, tam=7.6):
    """Linhas centradas em (cx, cy); a primeira em negrito."""
    passo = tam * 1.3 * 0.3528  # entrelinha em mm
    topo = cy - len(linhas) * passo / 2
    c.setFillColor(TINTA)
    for i, l in enumerate(linhas):
        fonte = "DVB" if i == 0 else "DV"
        t = tam if i == 0 else tam - 0.6
        c.setFont(fonte, t)
        c.drawCentredString(cx * mm, Y(topo + i * passo + passo * 0.72), l)


def caixa(x, topo, w, h, linhas, fundo=PROC, borda=PROC_BORDA):
    c.setFillColor(fundo); c.setStrokeColor(borda); c.setLineWidth(0.9)
    c.roundRect(x * mm, Y(topo + h), w * mm, h * mm, 1.8 * mm, fill=1, stroke=1)
    texto(x + w / 2, topo + h / 2, linhas)


def losango(cx, cy, w, h, linhas):
    c.setFillColor(DECISAO); c.setStrokeColor(DECISAO_BORDA); c.setLineWidth(0.9)
    p = c.beginPath()
    p.moveTo(cx * mm, Y(cy - h / 2)); p.lineTo((cx + w / 2) * mm, Y(cy))
    p.lineTo(cx * mm, Y(cy + h / 2)); p.lineTo((cx - w / 2) * mm, Y(cy)); p.close()
    c.drawPath(p, fill=1, stroke=1)
    texto(cx, cy, linhas)


def seta(*pts, rotulo=None, pos_rotulo=None):
    """Polilinha (x, topo) em mm com ponta de seta no ultimo ponto."""
    c.setStrokeColor(TINTA); c.setFillColor(TINTA); c.setLineWidth(0.8)
    p = c.beginPath(); p.moveTo(pts[0][0] * mm, Y(pts[0][1]))
    for x, t in pts[1:]:
        p.lineTo(x * mm, Y(t))
    c.drawPath(p, stroke=1, fill=0)
    (x0, t0), (x1, t1) = pts[-2], pts[-1]
    dx, dy = x1 - x0, t1 - t0
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    a, b = 2.2, 1.1  # comprimento e meia largura da ponta (mm)
    q = c.beginPath()
    q.moveTo(x1 * mm, Y(t1))
    q.lineTo((x1 - a * ux - b * uy) * mm, Y(t1 - a * uy + b * ux))
    q.lineTo((x1 - a * ux + b * uy) * mm, Y(t1 - a * uy - b * ux))
    q.close(); c.drawPath(q, fill=1, stroke=0)
    if rotulo:
        c.setFont("DVB", 7); c.drawCentredString(pos_rotulo[0] * mm, Y(pos_rotulo[1]), rotulo)


def faixa(topo, h, nome):
    c.setFillColor(FAIXA); c.setStrokeColor(FAIXA_BORDA); c.setLineWidth(0.6); c.setDash(2, 1.5)
    c.roundRect(2 * mm, Y(topo + h), 156 * mm, h * mm, 2.5 * mm, fill=1, stroke=1)
    c.setDash()
    c.setFillColor(ROTULO)
    c.roundRect(2 * mm, Y(topo + h), 13 * mm, h * mm, 2.5 * mm, fill=1, stroke=0)
    c.saveState()
    c.translate(9.3 * mm, Y(topo + h / 2)); c.rotate(90)
    c.setFillColor(TINTA); c.setFont("DVB", 7.6); c.drawCentredString(0, 0, nome)
    c.restoreState()


# faixas (etapas)
faixa(2, 26, "1. Preparação")
faixa(36, 24, "2. Geração")
faixa(68, 67, "3. Avaliação")
faixa(143, 24, "4. Análise")

# 1. preparação
caixa(22, 7, 62, 16, ["Seleção dos circuitos", "10 circuitos RTL em Verilog", "(HDLBits e OpenCores)"])
caixa(92, 7, 62, 16, ["Definição das estratégias de prompt", "Zero-shot, Few-shot,", "Especialista e Planejamento (ZS e FS)"])

# 2. geração
caixa(38, 40.5, 100, 15, ["Geração dos testbenches pelos LLMs",
                          "GPT-5.6 Luna e Gemini 3.5 Flash-Lite, em 2 rodadas",
                          "10 circuitos × 6 estratégias × 2 modelos × 2 rodadas = 240"])
seta((53, 23), (53, 40.5))
seta((123, 23), (123, 40.5))

# 3. avaliação na bancada
caixa(22, 73, 40, 16, ["Compilação e simulação", "Verilator, com o", "circuito como DUT"])
caixa(70, 73, 42, 16, ["Medição da cobertura", "linha, desvio,", "alternância e FSM"])
seta((42, 55.5), (42, 73))
seta((62, 81), (70, 81))
losango(91, 104, 40, 18, ["Testbench passou?"])
seta((91, 89), (91, 95))
caixa(118, 96.5, 37, 15, ["Teste de mutação", "até 4 mutantes do RTL;", "score = mortos / total"])
caixa(22, 96.5, 40, 15, ["Score de mutação = 0", "não passou ou", "estourou o tempo"], fundo=NEG, borda=NEG_BORDA)
seta((111, 104), (118, 104), rotulo="Sim", pos_rotulo=(114.5, 102))
seta((71, 104), (62, 104), rotulo="Não", pos_rotulo=(66.5, 102))
caixa(53, 119, 70, 11, ["Registro dos resultados na planilha", "por circuito, estratégia, modelo e rodada"])
seta((136.5, 111.5), (136.5, 124.5), (123, 124.5))
seta((42, 111.5), (42, 124.5), (53, 124.5))

# 4. análise
caixa(30, 148, 62, 15, ["Análise estatística", "Friedman, Wilcoxon, Holm", "e posto médio"])
caixa(102, 148, 52, 15, ["Comparação e conclusões", "estratégias de prompt", "e modelos"], fundo=FIM, borda=FIM_BORDA)
seta((61, 130), (61, 148))
seta((92, 155.5), (102, 155.5))

c.showPage(); c.save()
print("ok", SAIDA)
