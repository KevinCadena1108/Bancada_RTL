# -*- coding: utf-8 -*-
# Gera a planilha de analise do experimento (6 estrategias x N modulos x repeticoes).
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.utils import get_column_letter

# grava ao lado deste script (sobrescreve a planilha versionada em analise/)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "analise_experimento_prompts.xlsx")

FONT = "Arial"
HEAD_FILL = PatternFill("solid", fgColor="1F4E79")   # azul escuro
HEAD_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=11)
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")   # amarelo -> preencher
CALC_FILL  = PatternFill("solid", fgColor="E2EFDA")    # verde claro -> formula (nao editar)
SUB_FILL   = PatternFill("solid", fgColor="D9E1F2")    # azul claro -> subtitulos
TITLE_FONT = Font(name=FONT, bold=True, size=14, color="1F4E79")
NOTE_FONT  = Font(name=FONT, italic=True, size=9, color="808080")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

R = 500  # ultima linha de dados considerada nas formulas

# ---- estrategias na ordem das colunas do usuario ----
SHOTS = ["Zero-shot", "Few-shot"]
REFS  = ["Sem reforço", "Especialista", "Planning"]
# ordem 1..6 = (shot, ref)
ESTRAT = [
    ("Zero-shot", "Sem reforço"),
    ("Few-shot",  "Sem reforço"),
    ("Zero-shot", "Especialista"),
    ("Few-shot",  "Especialista"),
    ("Zero-shot", "Planning"),
    ("Few-shot",  "Planning"),
]

# ---- dados semente (reais, fornecidos pelo usuario) ----
# cada modulo: (nome, icv, [cobL x6], [cobD x6], [cobA x6], cobFSM_ou_None, [(mortos,total)|None x6])
NP = None
modulos = [
    ("Fsm serialdp", 2.2,
     [100,100,100,100,100,100],
     [100,100,100,100,100,100],
     [100,100,100,100,100,100],
     100,
     [(4,4),(4,4),NP,(4,4),NP,(4,4)]),
    ("Exams/2012 q2fsm", 1.4,
     [100,100,100,100,100,100],
     [100,100,100,100,100,100],
     [100,100,100,100,100,100],
     100,
     [(3,4),(3,4),(3,4),(3,4),(4,4),(3,4)]),
    ("Cout Clock", 1.0,
     [100,75,75,100,100,100],
     [100,65.5,50,100,100,100],
     [67.9,46.4,46.4,82.1,82.1,53.6],
     None,
     [(4,4),(4,4),NP,(4,4),(4,4),(4,4)]),
    ("Cs450/gshare", 1.8,
     [100,100,100,100,33.3,66.7],
     [100,100,100,100,75,87.5],
     [51.5,49.1,52.2,51.9,2.1,7.9],
     None,
     [NP,(3,4),(3,4),NP,NP,NP]),
]

wb = openpyxl.Workbook()
wb.calculation = CalcProperties(fullCalcOnLoad=True)

# ==========================================================================
# ABA 1 - COLETA
# ==========================================================================
ws = wb.active
ws.title = "Coleta"
cols = [
    ("Módulo", 20, "in"), ("ICV", 7, "in"), ("Faixa ICV", 11, "calc"),
    ("Modelo", 14, "in"), ("Shot", 11, "in"), ("Reforço", 13, "in"),
    ("Rep.", 6, "in"), ("Compilou", 9, "in"), ("Executou", 9, "in"),
    ("Passou", 8, "in"), ("Cob Linha (%)", 12, "in"), ("Cob Desvio (%)", 12, "in"),
    ("Cob Altern. (%)", 13, "in"), ("Cob FSM (%)", 11, "in"),
    ("Mut. mortos", 11, "in"), ("Mut. total", 10, "in"),
    ("Mut. score (%)", 13, "calc"), ("Obs.", 40, "in"),
]
for j, (name, w, kind) in enumerate(cols, start=1):
    c = ws.cell(row=1, column=j, value=name)
    c.font = HEAD_FONT; c.fill = HEAD_FILL; c.border = BORDER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.column_dimensions[get_column_letter(j)].width = w
ws.freeze_panes = "A2"

def faixa_formula(r):
    b = f"B{r}"
    return (f'=IF({b}="","",IF({b}<=1.2,"Fácil",IF({b}<=1.9,"Médio",'
            f'IF({b}<=2.3,"Alto","Muito Alta"))))')
def score_formula(r):
    return f'=IF($J{r}=1,IFERROR($O{r}/$P{r}*100,""),"")'

# escreve as linhas semente
r = 2
for (nome, icv, cobL, cobD, cobA, cobFSM, muts) in modulos:
    for k, (shot, ref) in enumerate(ESTRAT):
        mut = muts[k]
        passou = 0 if mut is None else 1
        ws.cell(row=r, column=1, value=nome)
        ws.cell(row=r, column=2, value=icv)
        ws.cell(row=r, column=3, value=faixa_formula(r))
        ws.cell(row=r, column=4, value="(preencher)")
        ws.cell(row=r, column=5, value=shot)
        ws.cell(row=r, column=6, value=ref)
        ws.cell(row=r, column=7, value=1)
        ws.cell(row=r, column=8, value=1)          # compilou (assumido p/ nao-passou)
        ws.cell(row=r, column=9, value=1)          # executou
        ws.cell(row=r, column=10, value=passou)
        ws.cell(row=r, column=11, value=cobL[k])
        ws.cell(row=r, column=12, value=cobD[k])
        ws.cell(row=r, column=13, value=cobA[k])
        ws.cell(row=r, column=14, value=(cobFSM if cobFSM is not None else None))
        if mut is not None:
            ws.cell(row=r, column=15, value=mut[0])
            ws.cell(row=r, column=16, value=mut[1])
        ws.cell(row=r, column=17, value=score_formula(r))
        obs = ""
        if passou == 0:
            obs = "TB não passou; cobertura só até a falha (não comparável); mutação não avaliada"
        ws.cell(row=r, column=18, value=obs)
        r += 1
SEED_LAST = r - 1

# formulas de C e Q para linhas vazias ate R (para novas repeticoes)
for rr in range(r, R + 1):
    ws.cell(row=rr, column=3, value=faixa_formula(rr))
    ws.cell(row=rr, column=17, value=score_formula(rr))

# formatacao de numero + fills por tipo de coluna
calc_cols = {3, 17}
for rr in range(2, R + 1):
    for j in range(1, 19):
        cell = ws.cell(row=rr, column=j)
        cell.font = Font(name=FONT, size=10)
        cell.border = BORDER
        if j in (2, 11, 12, 13, 14, 17):
            cell.number_format = "0.0"
        if j in (7, 8, 9, 10, 15, 16):
            cell.alignment = Alignment(horizontal="center")
        if rr > SEED_LAST:
            cell.fill = CALC_FILL if j in calc_cols else (INPUT_FILL if j not in calc_cols else CALC_FILL)
# marca cabecalho das colunas calculadas
for j in calc_cols:
    ws.cell(row=1, column=j).fill = PatternFill("solid", fgColor="548235")

# ==========================================================================
# ABA 2 - RESUMO POR ESTRATEGIA
# ==========================================================================
ws2 = wb.create_sheet("Resumo Estratégia")
def col_rng(letter):
    return f"Coleta!${letter}$2:${letter}${R}"
E_ = col_rng("E"); F_ = col_rng("F"); J_ = col_rng("J")
K_ = col_rng("K"); L_ = col_rng("L"); M_ = col_rng("M"); N_ = col_rng("N"); Q_ = col_rng("Q")
C_ = col_rng("C")

hdr2 = ["Shot", "Reforço", "N (runs)", "N passou", "Taxa sucesso (%)",
        "Mut. score médio (%)", "Cob Linha méd (%)", "Cob Desvio méd (%)",
        "Cob Altern. méd (%)", "Cob FSM méd (%)"]
ws2.cell(row=1, column=1, value="Resumo por estratégia (qualidade só entre os que passaram)").font = TITLE_FONT
for j, h in enumerate(hdr2, start=1):
    c = ws2.cell(row=2, column=j, value=h)
    c.font = HEAD_FONT; c.fill = HEAD_FILL; c.border = BORDER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws2.column_dimensions[get_column_letter(j)].width = 15
ws2.column_dimensions["A"].width = 12
for i, (shot, ref) in enumerate(ESTRAT):
    r = 3 + i
    A = f"$A{r}"; B = f"$B{r}"
    ws2.cell(row=r, column=1, value=shot)
    ws2.cell(row=r, column=2, value=ref)
    ws2.cell(row=r, column=3, value=f"=COUNTIFS({E_},{A},{F_},{B})")
    ws2.cell(row=r, column=4, value=f"=COUNTIFS({E_},{A},{F_},{B},{J_},1)")
    ws2.cell(row=r, column=5, value=f"=IFERROR($D{r}/$C{r}*100,\"\")")
    ws2.cell(row=r, column=6, value=f"=IFERROR(AVERAGEIFS({Q_},{E_},{A},{F_},{B},{J_},1),\"\")")
    ws2.cell(row=r, column=7, value=f"=IFERROR(AVERAGEIFS({K_},{E_},{A},{F_},{B},{J_},1),\"\")")
    ws2.cell(row=r, column=8, value=f"=IFERROR(AVERAGEIFS({L_},{E_},{A},{F_},{B},{J_},1),\"\")")
    ws2.cell(row=r, column=9, value=f"=IFERROR(AVERAGEIFS({M_},{E_},{A},{F_},{B},{J_},1),\"\")")
    ws2.cell(row=r, column=10, value=f"=IFERROR(AVERAGEIFS({N_},{E_},{A},{F_},{B},{J_},1),\"\")")
    for j in range(1, 11):
        cell = ws2.cell(row=r, column=j)
        cell.border = BORDER; cell.font = Font(name=FONT, size=10)
        if j >= 5: cell.number_format = "0.0"
        if j in (3, 4): cell.alignment = Alignment(horizontal="center")

# ==========================================================================
# ABA 3 - FATORIAL (efeitos principais + interacao)
# ==========================================================================
ws3 = wb.create_sheet("Fatorial")
ws3.cell(row=1, column=1, value="Análise fatorial 2×3 (shot × reforço)").font = TITLE_FONT
def head_row(ws, r, labels, widths=None):
    for j, h in enumerate(labels, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font = HEAD_FONT; c.fill = HEAD_FILL; c.border = BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if widths:
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w

# Efeito do shot
ws3.cell(row=3, column=1, value="Efeito principal — Shot").font = Font(name=FONT, bold=True, size=12)
head_row(ws3, 4, ["Shot", "N", "N passou", "Taxa sucesso (%)", "Mut. score médio (%)"],
         [16, 8, 9, 16, 18])
for i, shot in enumerate(SHOTS):
    r = 5 + i
    A = f"$A{r}"
    ws3.cell(row=r, column=1, value=shot)
    ws3.cell(row=r, column=2, value=f"=COUNTIFS({E_},{A})")
    ws3.cell(row=r, column=3, value=f"=COUNTIFS({E_},{A},{J_},1)")
    ws3.cell(row=r, column=4, value=f"=IFERROR($C{r}/$B{r}*100,\"\")")
    ws3.cell(row=r, column=5, value=f"=IFERROR(AVERAGEIFS({Q_},{E_},{A},{J_},1),\"\")")
    for j in range(1, 6):
        cc = ws3.cell(row=r, column=j); cc.border = BORDER; cc.font = Font(name=FONT, size=10)
        if j >= 4: cc.number_format = "0.0"
        if j in (2, 3): cc.alignment = Alignment(horizontal="center")

# Efeito do reforco
base = 8
ws3.cell(row=base, column=1, value="Efeito principal — Reforço").font = Font(name=FONT, bold=True, size=12)
head_row(ws3, base+1, ["Reforço", "N", "N passou", "Taxa sucesso (%)", "Mut. score médio (%)"])
for i, ref in enumerate(REFS):
    r = base + 2 + i
    A = f"$A{r}"
    ws3.cell(row=r, column=1, value=ref)
    ws3.cell(row=r, column=2, value=f"=COUNTIFS({F_},{A})")
    ws3.cell(row=r, column=3, value=f"=COUNTIFS({F_},{A},{J_},1)")
    ws3.cell(row=r, column=4, value=f"=IFERROR($C{r}/$B{r}*100,\"\")")
    ws3.cell(row=r, column=5, value=f"=IFERROR(AVERAGEIFS({Q_},{F_},{A},{J_},1),\"\")")
    for j in range(1, 6):
        cc = ws3.cell(row=r, column=j); cc.border = BORDER; cc.font = Font(name=FONT, size=10)
        if j >= 4: cc.number_format = "0.0"
        if j in (2, 3): cc.alignment = Alignment(horizontal="center")

# Interacao: matriz mut score medio (shot x reforco)
base2 = base + 6
ws3.cell(row=base2, column=1, value="Interação — Mut. score médio (%)  [linhas=shot, colunas=reforço]").font = Font(name=FONT, bold=True, size=12)
# cabecalho de colunas = reforcos
ws3.cell(row=base2+1, column=1, value="Shot \\ Reforço").font = HEAD_FONT
ws3.cell(row=base2+1, column=1).fill = HEAD_FILL; ws3.cell(row=base2+1, column=1).border = BORDER
for jj, ref in enumerate(REFS):
    c = ws3.cell(row=base2+1, column=2+jj, value=ref)
    c.font = HEAD_FONT; c.fill = HEAD_FILL; c.border = BORDER
    c.alignment = Alignment(horizontal="center")
for ii, shot in enumerate(SHOTS):
    r = base2 + 2 + ii
    c0 = ws3.cell(row=r, column=1, value=shot); c0.font = HEAD_FONT; c0.fill = SUB_FILL; c0.border = BORDER
    for jj, ref in enumerate(REFS):
        colcell = ws3.cell(row=base2+1, column=2+jj).coordinate  # ref header
        rowcell = f"$A{r}"
        # referencia absoluta ao cabecalho da coluna
        col_letter = get_column_letter(2+jj)
        ref_abs = f"{col_letter}${base2+1}"
        cc = ws3.cell(row=r, column=2+jj,
                      value=f"=IFERROR(AVERAGEIFS({Q_},{E_},{rowcell},{F_},{ref_abs},{J_},1),\"\")")
        cc.border = BORDER; cc.number_format = "0.0"; cc.font = Font(name=FONT, size=10)
        cc.alignment = Alignment(horizontal="center")

# ==========================================================================
# ABA 4 - POR FAIXA ICV
# ==========================================================================
ws4 = wb.create_sheet("Por Faixa ICV")
ws4.cell(row=1, column=1, value="Desempenho por faixa de ICV × estratégia").font = TITLE_FONT
hdr4 = ["Faixa ICV", "Shot", "Reforço", "N", "N passou", "Taxa sucesso (%)", "Mut. score médio (%)"]
for j, h in enumerate(hdr4, start=1):
    c = ws4.cell(row=2, column=j, value=h)
    c.font = HEAD_FONT; c.fill = HEAD_FILL; c.border = BORDER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws4.column_dimensions[get_column_letter(j)].width = [12,11,13,7,9,16,18][j-1]
FAIXAS = ["Fácil", "Médio", "Alto", "Muito Alta"]
r = 3
for faixa in FAIXAS:
    for (shot, ref) in ESTRAT:
        FA = f"$A{r}"; SH = f"$B{r}"; RE = f"$C{r}"
        ws4.cell(row=r, column=1, value=faixa)
        ws4.cell(row=r, column=2, value=shot)
        ws4.cell(row=r, column=3, value=ref)
        ws4.cell(row=r, column=4, value=f"=COUNTIFS({C_},{FA},{E_},{SH},{F_},{RE})")
        ws4.cell(row=r, column=5, value=f"=COUNTIFS({C_},{FA},{E_},{SH},{F_},{RE},{J_},1)")
        ws4.cell(row=r, column=6, value=f"=IFERROR($E{r}/$D{r}*100,\"\")")
        ws4.cell(row=r, column=7, value=f"=IFERROR(AVERAGEIFS({Q_},{C_},{FA},{E_},{SH},{F_},{RE},{J_},1),\"\")")
        for j in range(1, 8):
            cc = ws4.cell(row=r, column=j); cc.border = BORDER; cc.font = Font(name=FONT, size=10)
            if j >= 6: cc.number_format = "0.0"
            if j in (4, 5): cc.alignment = Alignment(horizontal="center")
        r += 1
    r += 0

# ==========================================================================
# ABA 5 - INSTRUCOES
# ==========================================================================
ws5 = wb.create_sheet("Instruções", 0)  # primeira aba
ws5.column_dimensions["A"].width = 110
linhas = [
    ("Análise de estratégias de prompt na geração de testbenches — planilha de coleta e análise", "title"),
    ("", "n"),
    ("COMO USAR", "h"),
    ("1. Preencha UMA linha por (módulo × estratégia × repetição) na aba 'Coleta'.", "n"),
    ("2. Rode cada célula (módulo × estratégia) 3–5 vezes — a variação do LLM exige repetições; as abas de resumo tiram a média sozinhas.", "n"),
    ("3. As abas 'Resumo Estratégia', 'Fatorial' e 'Por Faixa ICV' se calculam automaticamente ao abrir no Excel.", "n"),
    ("", "n"),
    ("COLUNAS DA ABA 'Coleta'", "h"),
    ("• Amarelo = você preenche.  Verde = fórmula (não edite): 'Faixa ICV' e 'Mut. score (%)'.", "n"),
    ("• Passou: 1 = compilou+executou+passou;  0 = 'Não passou' (falhou/checagem ou não compilou).", "n"),
    ("• Cobertura (Linha/Desvio/Altern./FSM) e mutação em % (0–100). Cob FSM em branco para módulos sem FSM.", "n"),
    ("• Mut. mortos / Mut. total: normalmente x/4. Deixe em branco quando 'Não passou' (mutação não é avaliada).", "n"),
    ("• Modelo: FIXE um modelo por experimento (ou trate 'modelo' como fator). NÃO misture modelos na mesma comparação.", "n"),
    ("", "n"),
    ("COMO COMPARAR (ordem de prioridade das métricas)", "h"),
    ("1º TAXA DE SUCESSO — % de módulos em que a estratégia gerou um TB que passou. 'Não passou' conta como falha.", "n"),
    ("2º MUTATION SCORE — só entre os que passaram. É a qualidade real (o TB pega bugs?).", "n"),
    ("3º COBERTURA — métrica secundária, só entre os que passaram. Alta cobertura + baixa mutação = TB que exercita mas não verifica.", "n"),
    ("Regra: taxa de sucesso → mutação → cobertura. Nunca comece pela cobertura.", "n"),
    ("", "n"),
    ("DESENHO FATORIAL 2×3", "h"),
    ("A aba 'Fatorial' separa os efeitos: Shot (zero vs few), Reforço (nenhum/especialista/planning) e a interação.", "n"),
    ("Isso responde 'qual estratégia é melhor' de forma defensável, em vez de comparar 6 colunas isoladas.", "n"),
    ("", "n"),
    ("CUIDADOS (para a banca)", "h"),
    ("• Efeito-teto: módulos onde toda estratégia dá 100% de cobertura não discriminam — só a mutação separa.", "n"),
    ("• Cobertura de um TB que 'Não passou' NÃO é comparável (mede só até a falha); por isso as médias usam só Passou=1.", "n"),
    ("• N pequeno: reporte média ± desvio. Teste sugerido: Friedman (bloqueado por módulo) sobre o mutation score.", "n"),
    ("", "n"),
    ("Os dados já preenchidos (24 linhas) são os 4 módulos que você enviou, em rodada única — servem de exemplo e ponto de partida.", "note"),
    ("Modelo indicado como '(preencher)': o cabeçalho de 'Fsm serialdp' mencionava GPT-5.6 Luna; confirme o modelo de cada rodada.", "note"),
]
rr = 1
for txt, kind in linhas:
    c = ws5.cell(row=rr, column=1, value=txt)
    if kind == "title": c.font = TITLE_FONT
    elif kind == "h": c.font = Font(name=FONT, bold=True, size=12, color="1F4E79")
    elif kind == "note": c.font = NOTE_FONT
    else: c.font = Font(name=FONT, size=10)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    rr += 1

wb.save(OUT)
print("SALVO:", OUT)
print("Linhas semente:", SEED_LAST - 1)

# ==========================================================================
# VERIFICACAO INDEPENDENTE (replica a logica das formulas em Python)
# ==========================================================================
print("\n=== CONFERENCIA (o que as formulas devem dar) ===")
rows = []
for (nome, icv, cobL, cobD, cobA, cobFSM, muts) in modulos:
    for k, (shot, ref) in enumerate(ESTRAT):
        mut = muts[k]
        passou = 0 if mut is None else 1
        score = (mut[0]/mut[1]*100) if mut else None
        rows.append(dict(mod=nome, shot=shot, ref=ref, passou=passou, score=score,
                         cobL=cobL[k], cobD=cobD[k], cobA=cobA[k]))
def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals)/len(vals), 1) if vals else ""
print("\n[Resumo por estrategia]")
for shot, ref in ESTRAT:
    sub = [r for r in rows if r["shot"]==shot and r["ref"]==ref]
    npass = [r for r in sub if r["passou"]==1]
    taxa = round(len(npass)/len(sub)*100,1) if sub else ""
    ms = avg([r["score"] for r in npass])
    cl = avg([r["cobL"] for r in npass]); cd = avg([r["cobD"] for r in npass]); ca = avg([r["cobA"] for r in npass])
    print(f"  {shot:9} / {ref:12} N={len(sub)} passou={len(npass)} taxa={taxa} mut={ms} cobL={cl} cobD={cd} cobA={ca}")
print("\n[Efeito Shot]")
for shot in SHOTS:
    sub=[r for r in rows if r["shot"]==shot]; npass=[r for r in sub if r["passou"]==1]
    print(f"  {shot:9} taxa={round(len(npass)/len(sub)*100,1)} mut={avg([r['score'] for r in npass])}")
print("\n[Efeito Reforco]")
for ref in REFS:
    sub=[r for r in rows if r["ref"]==ref]; npass=[r for r in sub if r["passou"]==1]
    print(f"  {ref:12} taxa={round(len(npass)/len(sub)*100,1)} mut={avg([r['score'] for r in npass])}")
