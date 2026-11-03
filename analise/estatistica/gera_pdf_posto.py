# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)
import sys

# Sem argumento, grava em documentacao/ (como os outros scripts de estatistica);
# com um caminho, grava nele. Rodar na raiz do repo.
OUT = sys.argv[1] if len(sys.argv) > 1 else "documentacao/posto_medio_passo_a_passo.pdf"
EST = ["ZS", "FS", "EspZS", "EspFS", "PlnZS", "PlnFS"]
ESTLONG = ["Zero-shot", "Few-shot", "Esp. Zero-shot", "Esp. Few-shot",
           "Plan. Zero-shot", "Plan. Few-shot"]

GPT = {
 "Fsm serialdp":([4,4,0,4,0,4],[0,0,4,0,0,4]),
 "Exams q2fsm":([3,3,3,3,4,3],[3,4,4,0,4,0]),
 "Cout Clock":([4,4,0,4,4,4],[0,4,0,0,4,4]),
 "Cs450/gshare":([0,3,3,0,0,0],[3,3,0,2,3,3]),
 "Lemmings":([4,4,4,4,4,4],[4,4,4,4,4,4]),
 "wbuart32":([0,2,3,3,3,4],[3,0,0,3,4,4]),
 "Cordic":([0,3,3,3,0,3],[2,0,2,3,3,3]),
 "Conwaylife":([0,0,4,0,4,4],[4,4,4,0,4,4]),
 "fancytimer":([0,0,0,3,0,0],[0,0,4,0,3,4]),
 "I2C Slave":([0,3,0,4,0,2],[0,0,3,3,2,3]),
}
GEM = {
 "Fsm serialdp":([0,4,4,4,0,4],[0,4,4,4,0,4]),
 "Exams q2fsm":([3,3,0,4,3,3],[3,3,3,3,3,3]),
 "Cout Clock":([0,3,3,0,3,2],[2,3,0,2,2,2]),
 "Cs450/gshare":([0,0,0,0,1,0],[0,1,0,0,0,0]),
 "Lemmings":([2,4,4,4,4,4],[4,4,4,4,4,4]),
 "wbuart32":([0,0,1,1,3,3],[3,3,3,3,3,3]),
 "Cordic":([1,0,1,1,2,0],[0,1,0,2,0,2]),
 "Conwaylife":([3,3,0,3,0,3],[3,3,3,3,0,4]),
 "fancytimer":([0,4,0,3,1,1],[0,3,3,3,3,3]),
 "I2C Slave":([2,1,1,4,0,0],[1,1,3,2,1,1]),
}

def medias(bloco):
    return {c:[(r1[i]+r2[i])/2 for i in range(6)] for c,(r1,r2) in bloco.items()}

def postos(vals):
    ordem = sorted(range(6), key=lambda i: vals[i])
    p=[0]*6; i=0; pos=1
    while i<6:
        j=i
        while j+1<6 and vals[ordem[j+1]]==vals[ordem[i]]: j+=1
        mp=sum(range(pos,pos+(j-i+1)))/(j-i+1)
        for k in range(i,j+1): p[ordem[k]]=mp
        pos+=(j-i+1); i=j+1
    return p

def posto_medio(bloco):
    med=medias(bloco); soma=[0.0]*6
    for c,v in med.items():
        pp=postos(v)
        for i in range(6): soma[i]+=pp[i]
    N=len(med); return [s/N for s in soma]

def fnum(x):
    return str(int(x)) if x==int(x) else f"{x:.1f}"

# ---------- estilos ----------
ss=getSampleStyleSheet()
AZUL=colors.HexColor("#123a5e"); VERDE=colors.HexColor("#1a7a4c")
CINZA=colors.HexColor("#eef1f4"); BORD=colors.HexColor("#c9d2da")
H0=ParagraphStyle("H0",parent=ss["Title"],fontName="Helvetica-Bold",fontSize=18,textColor=AZUL,spaceAfter=4,leading=22)
H1=ParagraphStyle("H1",parent=ss["Heading1"],fontName="Helvetica-Bold",fontSize=13,textColor=colors.white,backColor=AZUL,borderPadding=(5,7,5,7),spaceBefore=12,spaceAfter=7,leading=16)
H2=ParagraphStyle("H2",parent=ss["Heading2"],fontName="Helvetica-Bold",fontSize=11,textColor=AZUL,spaceBefore=8,spaceAfter=3)
BODY=ParagraphStyle("BODY",parent=ss["Normal"],fontName="Helvetica",fontSize=10,textColor=colors.HexColor("#1a2430"),alignment=TA_JUSTIFY,leading=14,spaceAfter=6)
BULL=ParagraphStyle("BULL",parent=BODY,leftIndent=14,bulletIndent=2,spaceAfter=2)
CAP=ParagraphStyle("CAP",parent=ss["Normal"],fontName="Helvetica-Oblique",fontSize=8.5,textColor=colors.HexColor("#55636f"),spaceBefore=1,spaceAfter=10)
SMALL=ParagraphStyle("SMALL",parent=BODY,fontSize=9,leading=12)
def esc(s): return s.replace("&","&amp;").replace("<","&lt;")
def P(t,st=BODY): return Paragraph(esc(t),st)
def B(t): return Paragraph(esc(t),BULL,bulletText="•")

story=[]
story.append(Paragraph("Posto medio das estrategias de prompt — metodo, resultados e referencia", H0))
story.append(P("Como a metrica e calculada, os resultados de todas as estrategias e modelos (um por um) "
   "e a fonte da formula. Valor analisado: mutantes mortos por circuito (media das 2 rodadas; "
   "“Nao passou” e “Timeout” = 0).", SMALL))

# 1. o que e / formula
story.append(Paragraph("1. O que e e qual a formula", H1))
story.append(P("O posto medio (average rank) ordena as estrategias para apontar a melhor. Em cada circuito, "
   "as seis estrategias sao ordenadas e recebem um posto de 1 (pior) a 6 (melhor); o posto medio de cada "
   "estrategia e a media de seus postos sobre os N circuitos. Quanto MAIOR o posto medio, melhor a estrategia."))
story.append(P("Posto medio da estrategia j:  R_j = (1/N) &#8721; r_i^j ,  onde r_i^j e o posto da estrategia j "
   "no circuito i, e N e o numero de circuitos.", SMALL))
tb=Table([[P("<b>Fonte da formula:</b> o ranqueamento de metodos por posto medio sobre multiplos conjuntos de "
   "dados e estabelecido por DEM&#352;AR (2006); os postos seguem o teste de FRIEDMAN (1937). A pratica de "
   "repetir as execucoes de algoritmos aleatorios (os LLMs) e analisar a media e recomendada por ARCURI; "
   "BRIAND (2011).", SMALL)]], colWidths=[170*mm])
tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#eaf2fa")),("BOX",(0,0),(-1,-1),0.8,AZUL),
   ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
story.append(tb)

# 2. passo a passo
story.append(Paragraph("2. Passo a passo do calculo", H1))
story.append(B("Passo 1 — Valor de cada estrategia por circuito: mutantes mortos, media das 2 rodadas (NP/Timeout = 0)."))
story.append(B("Passo 2 — Em cada circuito, ordene as 6 estrategias e de postos de 1 (pior) a 6 (melhor)."))
story.append(B("Passo 3 — Empates recebem a media dos postos (ex.: dois empatados nas posicoes 2 e 3 -> 2,5 cada)."))
story.append(B("Passo 4 — Repita para todos os circuitos (10 por modelo; 20 ao juntar os dois modelos)."))
story.append(B("Passo 5 — Posto medio = soma dos postos / N. Maior posto medio = melhor. (Conferencia: a soma dos 6 postos medios e sempre 21.)"))

# exemplo
story.append(Paragraph("Exemplo trabalhado: wbuart32 (GPT)", H2))
story.append(P("Mutantes — rodada 1: NP, 2/4, 3/4, 3/4, 3/4, 4/4;  rodada 2: 3/4, NP, NP, 3/4, 4/4, 4/4.", SMALL))
m=medias(GPT)["wbuart32"]; p=postos(m)
ex=[["", *EST],
    ["media (R1+R2)/2", *[fnum(x) for x in m]],
    ["posto (1 pior..6 melhor)", *[fnum(x) for x in p]]]
t=Table(ex, colWidths=[44*mm]+[21*mm]*6)
t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),AZUL),("TEXTCOLOR",(0,0),(-1,0),colors.white),
   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),
   ("GRID",(0,0),(-1,-1),0.4,BORD),("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
   ("BACKGROUND",(0,1),(0,-1),CINZA),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
story.append(t)
story.append(Paragraph("FS (1,0) e o menor -> posto 1; ZS e EspZS empatam em 1,5 (posicoes 2 e 3) -> 2,5 cada; "
   "EspFS 3,0 -> 4; PlnZS 3,5 -> 5; PlnFS 4,0 -> 6.", CAP))

# ---------- tabela detalhada por modelo ----------
def tabela_modelo(titulo, bloco, cor):
    story.append(Paragraph(titulo, H1))
    story.append(P("Cada celula mostra a media das 2 rodadas e, entre parenteses, o posto naquele circuito. "
        "A ultima linha e o posto medio (soma dos postos / 10).", SMALL))
    med=medias(bloco)
    head=["Circuito", *EST]
    rows=[head]
    somas=[0.0]*6
    for c,v in med.items():
        pp=postos(v)
        for i in range(6): somas[i]+=pp[i]
        rows.append([c, *[f"{fnum(v[i])} ({fnum(pp[i])})" for i in range(6)]])
    pm=[s/10 for s in somas]
    rows.append(["POSTO MEDIO", *[f"{x:.2f}" for x in pm]])
    t=Table(rows, colWidths=[30*mm]+[23.3*mm]*6, repeatRows=1)
    sty=[("BACKGROUND",(0,0),(-1,0),cor),("TEXTCOLOR",(0,0),(-1,0),colors.white),
         ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
         ("GRID",(0,0),(-1,-1),0.4,BORD),("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
         ("ROWBACKGROUNDS",(0,1),(-1,-2),[colors.white,CINZA]),
         ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#dff0e6")),("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
         ("TOPPADDING",(0,0),(-1,-1),2.5),("BOTTOMPADDING",(0,0),(-1,-1),2.5)]
    # destaca o melhor posto medio (maior)
    mx=max(pm); ib=pm.index(mx)
    sty.append(("TEXTCOLOR",(ib+1,-1),(ib+1,-1),VERDE))
    t.setStyle(TableStyle(sty))
    story.append(t)
    ordem=sorted(range(6),key=lambda i:-pm[i])
    rank=" > ".join(f"{EST[i]} ({pm[i]:.2f})" for i in ordem)
    story.append(Paragraph("Ranking: "+rank, CAP))
    return pm

story.append(PageBreak())
story.append(Paragraph("3. Resultados por modelo (um por um)", H1))
story.append(P("As tabelas a seguir trazem os 10 circuitos de cada modelo, com a media e o posto de cada "
   "estrategia, e o posto medio final. O verde marca o maior posto medio."))
pm_gpt=tabela_modelo("3.1 GPT-5.6 Luna", GPT, AZUL)
pm_gem=tabela_modelo("3.2 Gemini 3.5 Flash-Lite", GEM, colors.HexColor("#5b3a8e"))

# ---------- juntos ----------
story.append(PageBreak())
story.append(Paragraph("4. Resultado com os dois modelos juntos (20 circuitos)", H1))
story.append(P("Ao juntar os modelos, cada combinacao circuito x modelo vira um bloco (20 no total). As "
   "estrategias sao ranqueadas DENTRO de cada bloco, do mesmo modo; o posto medio e a media sobre os 20. "
   "O modelo nunca e ranqueado — ele apenas dobra o numero de blocos."))
JUNTOS={**{f"GPT {k}":v for k,v in GPT.items()}, **{f"Gem {k}":v for k,v in GEM.items()}}
medJ=medias(JUNTOS)
rows=[["Circuito (modelo)", *EST]]
somas=[0.0]*6
for c,v in medJ.items():
    pp=postos(v)
    for i in range(6): somas[i]+=pp[i]
    rows.append([c, *[fnum(pp[i]) for i in range(6)]])
pm_jun=[s/20 for s in somas]
rows.append(["POSTO MEDIO", *[f"{x:.2f}" for x in pm_jun]])
t=Table(rows, colWidths=[36*mm]+[22.3*mm]*6, repeatRows=1)
sty=[("BACKGROUND",(0,0),(-1,0),VERDE),("TEXTCOLOR",(0,0),(-1,0),colors.white),
     ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7.5),
     ("GRID",(0,0),(-1,-1),0.4,BORD),("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
     ("ROWBACKGROUNDS",(0,1),(-1,-2),[colors.white,CINZA]),
     ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#dff0e6")),("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
     ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]
mx=max(pm_jun); ib=pm_jun.index(mx); sty.append(("TEXTCOLOR",(ib+1,-1),(ib+1,-1),colors.HexColor("#0a5")));
t.setStyle(TableStyle(sty))
story.append(Paragraph("Nesta tabela as celulas mostram so o posto (as medias estao nas tabelas por modelo).", CAP))
story.append(t)
ordem=sorted(range(6),key=lambda i:-pm_jun[i])
story.append(Spacer(1,3*mm))
# ranking final destacado
rk=[["Pos.","Estrategia","Posto medio"]]
for pos,i in enumerate(ordem,1):
    rk.append([str(pos), ESTLONG[i], f"{pm_jun[i]:.2f}"])
t=Table(rk,colWidths=[16*mm,70*mm,30*mm])
t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),AZUL),("TEXTCOLOR",(0,0),(-1,0),colors.white),
   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.4,BORD),("FONTSIZE",(0,0),(-1,-1),9.5),
   ("ALIGN",(0,0),(0,-1),"CENTER"),("ALIGN",(2,0),(2,-1),"CENTER"),
   ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,CINZA]),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
story.append(t)
story.append(Paragraph("As variantes few-shot ocupam o topo e o zero-shot e o ultimo. Por modelo, o 1o e PlnFS "
   "no GPT (4,65) e EspFS no Gemini (4,30); o ZS e o ultimo nos dois.", CAP))

# 5. como obter / reprodutibilidade
story.append(Paragraph("5. Como os resultados foram obtidos", H1))
story.append(B("Os valores vem da planilha do experimento (linha “Mutantes” de cada circuito), nas 2 rodadas."))
story.append(B("Para cada circuito calcula-se a media das 2 rodadas, os postos (passos 2-3) e, ao final, o posto medio."))
story.append(B("O calculo e reproduzivel por script (Python) e os postos medios conferem com os do teste de Friedman."))

# 6. interpretacao / ressalvas
story.append(Paragraph("6. Interpretacao e ressalvas", H1))
story.append(P("O posto medio ORDENA as estrategias (aponta Planning Few-shot em 1o e Zero-shot em ultimo), mas, "
   "sozinho, nao prova que o 1o e significativamente melhor que o 2o. Para isso usa-se a diferenca critica de "
   "Nemenyi, que neste caso mostra que as estrategias do topo estao empatadas. Assim, a leitura correta e "
   "“as variantes few-shot lideram e o zero-shot e o pior”, sem eleger uma unica melhor."))
story.append(P("O posto medio e uma comparacao ENTRE ESTRATEGIAS, interna a cada modelo (a soma dos postos medios "
   "e sempre 21, no GPT e no Gemini). Por isso ele NAO compara GPT x Gemini: para comparar os modelos usam-se "
   "metricas absolutas (score efetivo, taxa de aprovacao), e essa comparacao e apenas descritiva. Ao juntar os "
   "modelos, declara-se que os mesmos circuitos aparecem nos dois (os 20 blocos nao sao totalmente "
   "independentes)."))

# referencias
story.append(Paragraph("Referencias", H1))
for r in [
 "ARCURI, Andrea; BRIAND, Lionel. A practical guide for using statistical tests to assess randomized "
 "algorithms in software engineering. In: INTERNATIONAL CONFERENCE ON SOFTWARE ENGINEERING (ICSE), 33., "
 "2011, Honolulu. Proceedings... New York: ACM, 2011. p. 1-10. DOI: 10.1145/1985793.1985795.",
 "DEMŠAR, Janez. Statistical comparisons of classifiers over multiple data sets. Journal of Machine "
 "Learning Research, v. 7, p. 1-30, 2006.",
 "FRIEDMAN, Milton. The use of ranks to avoid the assumption of normality implicit in the analysis of "
 "variance. Journal of the American Statistical Association, v. 32, n. 200, p. 675-701, 1937. "
 "DOI: 10.1080/01621459.1937.10503522.",
]:
    story.append(Paragraph(esc(r), SMALL))

doc=SimpleDocTemplate(OUT,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=15*mm,bottomMargin=15*mm,
                      title="Posto medio - passo a passo")
doc.build(story)
print("PDF salvo em", OUT)
print("Conferencia postos medios juntos:", {EST[i]:round(pm_jun[i],2) for i in ordem})
