"""Gera o apêndice do TCC em LaTeX com os dados completos do experimento.

Tabelas: (A.1) cálculo do ICV de cada módulo; (A.2) mutantes mortos por módulo, estratégia,
modelo e rodada; (A.3/A.4) cobertura de linha, desvio, alternância e FSM por modelo.
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

# ICV calculado pela Bancada RTL (resultado.json das avaliações): nome no TCC, linhas, estados,
# portas, flags de lógica (A = aritmética, D = deslocamento, P = estruturas replicadas) e P_LOG.
ICV = {
    "Lemmings1":        ("Lemmings1", 24, 2, 6, "", 0),
    "Conwaylife":       ("Conwaylife", 33, 0, 4, "A", 1),
    "Cout Clock":       ("Count clock", 39, 0, 7, "", 0),
    "Exams/2012 q2fsm": ("Exams/2012 q2fsm", 34, 6, 4, "", 0),
    "Cs450/gshare":     ("Cs450/gshare", 35, 0, 11, "A, D", 3),
    "fancytimer":       ("Fancytimer", 48, 4, 7, "A, D", 3),
    "Cordic":           ("CORDIC", 109, 0, 8, "A, P", 3),
    "Fsm serialdp":     ("Fsm serialdp", 83, 5, 5, "A, D", 3),
    "I2C Slave":        ("SPI Master", 102, 3, 12, "A, D", 3),
    "wbuart32":         ("wbuart32", 84, 10, 5, "A, D", 3),
}
ICV_BANCADA = {"Lemmings1": 1.0, "Conwaylife": 1.0, "Cout Clock": 1.0, "Exams/2012 q2fsm": 1.4,
               "Cs450/gshare": 1.8, "fancytimer": 1.9, "Cordic": 1.9, "Fsm serialdp": 2.2,
               "I2C Slave": 2.4, "wbuart32": 2.5}
ORDEM = list(ICV)  # ordem crescente de ICV, igual à Tabela de módulos do TCC
EST = ["ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"]


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


L = []
w = L.append
w("% Gerado por analise/estatistica/gerar_apendice_latex.py a partir da planilha do experimento.")
w("% Não editar à mão: rode o script de novo se a planilha mudar.")
w("")
w("\\section{Resultados detalhados}")
w("\\label{ap:resultados}")
w("")
w("Este apêndice reúne os dados completos do experimento: o cálculo do ICV de cada módulo "
  "(Tabela~\\ref{tab:ap_icv}), o resultado do teste de mutação de cada \\textit{testbench} "
  "(Tabela~\\ref{tab:ap_mutacao}) e as coberturas medidas pela Bancada RTL "
  "(Tabelas~\\ref{tab:ap_cob_gpt} e~\\ref{tab:ap_cob_gemini}). Nas tabelas de resultados, cada "
  "célula traz os valores das duas rodadas, separados por ponto e vírgula (rodada~1; rodada~2).")
w("")

# ---- A.1 ICV ----
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
    nome, lin, est, por, flags, plog = ICV[c]
    v = round(0.3 * p_loc(lin) + 0.3 * p_fsm(est) + 0.2 * p_io(por) + 0.2 * plog, 2)
    assert abs(v - ICV_BANCADA[c]) < 1e-9, (c, v)
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

# ---- A.2 mutação ----
w("\\begin{table}[htbp]")
w("  \\centering")
w("  \\caption{Mutantes mortos por módulo, estratégia e modelo (rodada 1; rodada 2)}")
w("  \\label{tab:ap_mutacao}")
w("  \\footnotesize")
w("  \\setlength{\\tabcolsep}{4pt}")
w("  \\begin{tabular}{@{}lcccccc@{}}")
w("    \\toprule")
w("    Módulo & " + " & ".join(EST) + " \\\\")
for m in MODELOS:
    w("    \\midrule")
    w(f"    \\multicolumn{{7}}{{@{{}}l}}{{\\textit{{{NOME_MODELO[m]}}}}} \\\\")
    for c in ORDEM:
        d = CIRCUITOS.index(c)
        cel = [f"{mut(RODADAS[1][m][d][e])}; {mut(RODADAS[2][m][d][e])}" for e in range(6)]
        w(f"    {ICV[c][0]} & " + " & ".join(cel) + " \\\\")
w("    \\bottomrule")
w("  \\end{tabular}")
w("")
w("  \\smallskip")
w("  {\\footnotesize $k$/4 = mutantes mortos de 4; NP = não passou no circuito original; "
  "TO = excedeu o tempo limite. ZS = \\textit{Zero-shot}; FS = \\textit{Few-shot}; "
  "Esp = Especialista; Pln = \\textit{Planning}.}")
w("\\end{table}")
w("")

# ---- A.3 / A.4 cobertura ----
METS = [("linha", "Linha"), ("branch", "Desvio"), ("toggle", "Alternância"), ("fsm", "FSM")]
for m, rot in zip(MODELOS, ["tab:ap_cob_gpt", "tab:ap_cob_gemini"]):
    w("\\begin{table}[htbp]")
    w("  \\centering")
    w(f"  \\caption{{Cobertura (\\%) dos \\textit{{testbenches}} do {NOME_MODELO[m]} "
      "(rodada 1; rodada 2)}")
    w(f"  \\label{{{rot}}}")
    w("  \\scriptsize  % 45 linhas: em tamanho menor a tabela cabe numa página do modelo SBC")
    w("  \\setlength{\\tabcolsep}{4pt}")
    # o nome do módulo vira uma linha de título (sem coluna própria), para caber na largura
    w("  \\begin{tabular}{@{}lcccccc@{}}")
    w("    \\toprule")
    w("    Métrica & " + " & ".join(EST) + " \\\\")
    for c in ORDEM:
        d = CIRCUITOS.index(c)
        w("    \\midrule")
        w(f"    \\multicolumn{{7}}{{@{{}}l}}{{\\textit{{{ICV[c][0]}}}}} \\\\")
        for k, nome_k in METS:
            v1, v2 = COB[m]["1"][d][k], COB[m]["2"][d][k]
            vals = [(cobv(v1[e]), cobv(v2[e])) for e in range(6)]
            if all(a is None and b is None for a, b in vals):
                continue  # módulo sem cobertura de FSM
            cel = [f"{a if a is not None else '--'}; {b if b is not None else '--'}" for a, b in vals]
            w(f"    \\quad {nome_k} & " + " & ".join(cel) + " \\\\")
    w("    \\bottomrule")
    w("  \\end{tabular}")
    w("")
    w("  \\smallskip")
    w("  {\\footnotesize TO = excedeu o tempo limite. A linha FSM aparece só nos módulos em que a "
      "métrica se aplica. As coberturas dos \\textit{testbenches} não aprovados estão registradas, "
      "mas não entram nas médias do trabalho, pois a simulação é interrompida no primeiro erro.}")
    w("\\end{table}")
    w("")

open(SAIDA, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("ok", os.path.normpath(SAIDA), len(L), "linhas")
