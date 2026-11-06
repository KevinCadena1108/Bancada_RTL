"""Gera o apêndice do TCC em LaTeX com os dados completos do experimento.

Organizado como a planilha: (1) uma tabela com o cálculo do ICV de cada módulo; (2) uma tabela por
módulo, com um bloco por IA (GPT e Gemini) e, em cada bloco, as linhas Linha, Desvio, Alternância,
FSM e Mutantes, com a rodada 1 ao lado da rodada 2 (6 estratégias em cada).
Os dados vêm de PLANILHA_R1/R2 (pdf_comum.py) e de coberturas.json — os mesmos da planilha do
experimento. Usa booktabs (já carregado no preâmbulo do TCC).
Uso (WSL): python gerar_apendice_latex.py [saida.tex]   (padrão: documentacao/apendice_resultados.tex)
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from pdf_comum import CIRCUITOS, MODELOS, RODADAS  # noqa: E402

SAIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "..", "..", "documentacao",
                                                           "apendice_resultados.tex")
COB = json.load(open(os.path.join(AQUI, "coberturas.json"), encoding="utf-8"))
NOME_MODELO = {MODELOS[0]: "GPT-5.6 Luna", MODELOS[1]: "Gemini 3.5 Flash-Lite"}

# ICV calculado pela Bancada RTL (resultado.json das avaliações): nome no TCC, origem, linhas,
# estados, portas, flags de lógica (A = aritmética, D = deslocamento, P = estruturas
# replicadas) e P_LOG. Ordem crescente de ICV, igual à Tabela de módulos do TCC.
ICV = {
    "Lemmings1":        ("Lemmings1", "HDLBits", 24, 2, 6, "", 0),
    "Conwaylife":       ("Conwaylife", "HDLBits", 33, 0, 4, "A", 1),
    "Cout Clock":       ("Count clock", "HDLBits", 39, 0, 7, "", 0),
    "Exams/2012 q2fsm": ("Exams/2012 q2fsm", "HDLBits", 34, 6, 4, "", 0),
    "Cs450/gshare":     ("Cs450/gshare", "HDLBits", 35, 0, 11, "A, D", 3),
    "fancytimer":       ("Fancytimer", "HDLBits", 48, 4, 7, "A, D", 3),
    "Cordic":           ("CORDIC", "OpenCores", 109, 0, 8, "A, P", 3),
    "Fsm serialdp":     ("Fsm serialdp", "HDLBits", 83, 5, 5, "A, D", 3),
    "I2C Slave":        ("SPI Master", "OpenCores", 102, 3, 12, "A, D", 3),
    "wbuart32":         ("wbuart32", "OpenCores", 84, 10, 5, "A, D", 3),
}
ICV_BANCADA = {"Lemmings1": 1.0, "Conwaylife": 1.0, "Cout Clock": 1.0, "Exams/2012 q2fsm": 1.4,
               "Cs450/gshare": 1.8, "fancytimer": 1.9, "Cordic": 1.9, "Fsm serialdp": 2.2,
               "I2C Slave": 2.4, "wbuart32": 2.5}
ORDEM = list(ICV)
EST = ["ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"]
METS = [("linha", "Linha"), ("branch", "Desvio"), ("toggle", "Alternância"), ("fsm", "FSM")]


def faixa(v, faixas):
    for lim, p in faixas:
        if lim is None or v <= lim:
            return p


def p_loc(n): return faixa(n, [(30, 1), (100, 2), (None, 3)])
def p_fsm(n): return faixa(n, [(1, 0), (4, 1), (9, 2), (None, 3)])
def p_io(n): return faixa(n, [(4, 1), (10, 2), (None, 3)])


def classe(v):
    return "Fácil" if v <= 1.2 else "Média" if v <= 1.9 else "Alta" if v <= 2.3 else "Muito Alta"


def br(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def icv(c):
    _, _, lin, est, por, _, plog = ICV[c]
    v = round(0.3 * p_loc(lin) + 0.3 * p_fsm(est) + 0.2 * p_io(por) + 0.2 * plog, 2)
    assert abs(v - ICV_BANCADA[c]) < 1e-9, (c, v)
    return v


def mut(cel):
    if "/" in cel:
        return cel
    return {"Não passou": "NP", "Timeout": "TO", "Não compilou": "NC"}[cel]


def cobv(v):
    if v is None:
        return None
    if isinstance(v, str):
        return {"Timeout": "TO"}[v]
    return str(int(v)) if float(v).is_integer() else br(v)


def rotulo(c):
    return "tab:ap_" + "".join(ch for ch in ICV[c][0].lower() if ch.isalnum())


L = []
w = L.append
w("% Gerado por analise/estatistica/gerar_apendice_latex.py a partir da planilha do experimento.")
w("% Não editar à mão: rode o script de novo se a planilha mudar.")
w("")
w("\\section{Resultados detalhados}")
w("\\label{ap:resultados}")
w("")
w("Este apêndice reúne os dados completos do experimento. A Tabela~\\ref{tab:ap_icv} mostra o "
  "cálculo do ICV de cada módulo, e as Tabelas~\\ref{" + rotulo(ORDEM[0]) + "} a~\\ref{"
  + rotulo(ORDEM[-1]) + "} trazem, para cada módulo e cada LLM, as coberturas (\\%) e os "
  "mutantes mortos de cada estratégia nas duas rodadas. Abreviações: ZS = \\textit{Zero-shot}; "
  "FS = \\textit{Few-shot}; Esp = Especialista; Pln = \\textit{Planning}; $k$/4 = mutantes "
  "mortos de 4; NP = não passou no circuito original; TO = excedeu o tempo limite. A linha FSM "
  "aparece só nos módulos em que a métrica se aplica. As coberturas dos \\textit{testbenches} "
  "não aprovados estão registradas, mas não entram nas médias do trabalho, pois a simulação é "
  "interrompida no primeiro erro.")
w("")

# ---- cálculo do ICV ----
w("\\begin{table}[htbp]")
w("  \\centering")
w("  \\caption{Cálculo do ICV de cada módulo}")
w("  \\label{tab:ap_icv}")
w("  \\footnotesize")
w("  \\setlength{\\tabcolsep}{4pt}")
w("  \\begin{tabular}{@{}lccccll@{}}")
w("    \\toprule")
w("    Módulo & Linhas & Estados & Portas & Lógica & ICV & Classe \\\\")
w("     & ($P_{\\mathrm{LOC}}$) & ($P_{\\mathrm{FSM}}$) & ($P_{\\mathrm{IO}}$) & "
  "($P_{\\mathrm{LOG}}$) & & \\\\")
w("    \\midrule")
for c in ORDEM:
    nome, _, lin, est, por, flags, plog = ICV[c]
    v = icv(c)
    w(f"    {nome} & {lin} ({p_loc(lin)}) & {est if est else '--'} ({p_fsm(est)}) & "
      f"{por} ({p_io(por)}) & {flags if flags else '--'} ({plog}) & {br(v)} & {classe(v)} \\\\")
w("    \\bottomrule")
w("  \\end{tabular}")
w("")
w("  \\smallskip")
w("  {\\footnotesize Entre parênteses, a pontuação de cada componente. Lógica: A = aritmética, "
  "D = deslocamento, P = estruturas replicadas. "
  "$\\mathrm{ICV} = 0{,}30P_{\\mathrm{LOC}} + 0{,}30P_{\\mathrm{FSM}} + 0{,}20P_{\\mathrm{IO}} + "
  "0{,}20P_{\\mathrm{LOG}}$.}")
w("\\end{table}")
w("")

# ---- uma tabela por módulo: bloco por IA, rodada 1 ao lado da rodada 2 ----
for c in ORDEM:
    d = CIRCUITOS.index(c)
    nome, origem = ICV[c][0], ICV[c][1]
    v = icv(c)
    w("\\begin{table}[htbp]")
    w("  \\centering")
    w(f"  \\caption{{Resultados do módulo {nome} ({origem}; ICV {br(v)}, {classe(v)})}}")
    w(f"  \\label{{{rotulo(c)}}}")
    w("  \\scriptsize")
    w("  \\setlength{\\tabcolsep}{3pt}")
    w("  \\begin{tabular}{@{}l*{6}{c}@{\\hspace{8pt}}*{6}{c}@{}}")
    w("    \\toprule")
    w("     & \\multicolumn{6}{c}{Rodada 1} & \\multicolumn{6}{c}{Rodada 2} \\\\")
    w("    \\cmidrule(r){2-7} \\cmidrule(l){8-13}")
    w("     & " + " & ".join(EST + EST) + " \\\\")
    for m in MODELOS:
        w("    \\midrule")
        w(f"    \\multicolumn{{13}}{{@{{}}l}}{{\\textit{{{NOME_MODELO[m]}}}}} \\\\")
        for k, nome_k in METS:
            v1, v2 = COB[m]["1"][d][k], COB[m]["2"][d][k]
            vals = [cobv(x) for x in v1] + [cobv(x) for x in v2]
            if all(x is None for x in vals):
                continue  # módulo sem cobertura de FSM
            w(f"    \\quad {nome_k} & " + " & ".join(x if x is not None else "--" for x in vals)
              + " \\\\")
        muts = [mut(RODADAS[1][m][d][e]) for e in range(6)] + \
               [mut(RODADAS[2][m][d][e]) for e in range(6)]
        w("    \\quad Mutantes & " + " & ".join(muts) + " \\\\")
    w("    \\bottomrule")
    w("  \\end{tabular}")
    w("\\end{table}")
    w("")

open(SAIDA, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("ok", os.path.normpath(SAIDA), len(L), "linhas")
