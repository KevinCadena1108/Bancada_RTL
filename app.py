#!/usr/bin/env python3
"""
Backend do avaliador de testbenches.

Recebe um modulo RTL e um testbench (ambos Verilog), roda o Verilator e devolve:
  - se compilou
  - se a simulacao executou / passou
  - cobertura (pontos cobertos / total, %)
  - mutation score (mutantes mortos / total)

Todo o conhecimento acumulado esta aqui:
  * build em /tmp (nunca em caminho com espaco)  -> --Mdir
  * harness C++ proprio para gravar cobertura    -> sim/main.cpp
  * --annotate-min 1 (default 10 daria 0%)
  * modulo do testbench se chama sempre "tb"
"""

import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# Diretorio deste arquivo (para achar sim/main.cpp em qualquer CWD)
BASE = Path(__file__).resolve().parent
HARNESS = BASE / "sim" / "main.cpp"

# Nome que o modulo do testbench DEVE ter. O harness faz #include "Vtb.h".
TB_TOP = "tb"

# Timeout da COMPILACAO (segundos). Alto o bastante para o compile de modulos
# grandes (ex: AES) nao ser morto no meio.
TIMEOUT = 240

# Timeout da EXECUCAO da simulacao (segundos). Curto: um TB correto roda em ms;
# um mutante que trava (ex: clock gerado que nunca alterna, deixando o TB preso
# em @(negedge ...)) deve morrer rapido, sem segurar a requisicao pelo TIMEOUT
# de compilacao. Trava => morto por timeout => conta como mutante detectado.
SIM_TIMEOUT = 30

# Nivel de paralelismo do Verilator (verilacao + build C++). Modulos grandes
# compilam MUITO mais rapido usando varios nucleos; e' o gargalo da bancada.
BUILD_JOBS = "8"

# Quantos mutantes validos (que compilam) avaliar por rodada.
MAX_MUTANTES = 4

# Teto de compilacoes de mutante por rodada (validos ou nao), para limitar
# o tempo total da requisicao.
MAX_TENTATIVAS = 16

# Historico de avaliacoes (uma linha por rodada), para as tabelas
# comparativas do experimento. Exportado em /historico.csv.
HISTORICO = BASE / "historico.csv"

# Copia de cada avaliacao (RTL, testbench e resultado), uma pasta por envio,
# para os testbenches gerados nunca se perderem. Ver salvar_avaliacao().
AVALIACOES = BASE / "avaliacoes"

# Opcional: URL de um webhook (Google Apps Script) para o qual cada avaliacao
# e' enviada, alimentando uma planilha automaticamente. Definido via variavel
# de ambiente GSHEET_WEBHOOK; se vazio, nada e' enviado.
GSHEET_WEBHOOK = os.environ.get("GSHEET_WEBHOOK", "").strip()

# Timeout do envio para a planilha (segundos). O Apps Script pode demorar na
# primeira chamada e espera ate 30s pelo lock; com timeout curto a bancada
# acusava falha mesmo quando a planilha gravava.
SHEETS_TIMEOUT = 30

# Linhas que nao chegaram a planilha (falha de rede/timeout), uma por linha em
# JSON, para reenviar depois. O historico.csv continua tendo tudo.
PENDENTES = BASE / "envios_pendentes.jsonl"


def guardar_pendente(linha, motivo):
    """Anexa a linha que nao chegou a planilha em PENDENTES. Nunca levanta erro."""
    try:
        with open(PENDENTES, "a", encoding="utf-8") as f:
            f.write(json.dumps({**linha, "_motivo": motivo}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def enviar_para_sheets(linha):
    """
    POST da linha (dict) para o webhook da planilha. Nunca levanta erro:
    devolve o que aconteceu, para a tela mostrar. "motivo" e' um de:
    gravou / recusou (o Apps Script respondeu ok:false) / estranha (resposta
    que nao e' o JSON do script) / falhou (rede ou timeout) / sem_webhook.
    """
    if not GSHEET_WEBHOOK:
        return {"ok": False, "motivo": "sem_webhook",
                "msg": "webhook não configurado: suba o servidor com ./start.sh"}
    try:
        req = urllib.request.Request(
            GSHEET_WEBHOOK,
            data=json.dumps(linha).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        corpo = urllib.request.urlopen(req, timeout=SHEETS_TIMEOUT).read()
    except Exception as e:
        # planilha e' um extra: falha nela nunca derruba a avaliacao, mas a
        # linha fica guardada para reenviar
        guardar_pendente(linha, str(e))
        return {"ok": False, "motivo": "falhou",
                "msg": f"envio falhou ({e}). Se foi timeout, a planilha pode ter "
                       f"gravado mesmo assim: confira. A linha ficou em {PENDENTES.name}"}
    try:
        resp = json.loads(corpo.decode("utf-8"))
    except ValueError:
        resp = None
    if not isinstance(resp, dict) or "ok" not in resp:
        trecho = re.sub(r"<[^>]+>", " ", corpo.decode("utf-8", "replace"))
        return {"ok": False, "motivo": "estranha",
                "msg": "a planilha respondeu algo inesperado (erro no Apps Script?): "
                       + " ".join(trecho.split())[:160]}
    # o script antigo repetia nomes em "escreveu"; mostra cada metrica uma vez
    feitas = ", ".join(dict.fromkeys(resp.get("escreveu") or [])) or "nada"
    if resp["ok"]:
        onde = f" na aba {resp['aba']}" if resp.get("aba") else ""
        return {"ok": True, "motivo": "gravou", "msg": f"gravado{onde}: {feitas}",
                "resposta": resp}
    if resp.get("faltou"):
        msg = f"gravou só {feitas}; faltou {', '.join(resp['faltou'])}"
    else:
        msg = resp.get("erro") or "a planilha recusou sem dizer o motivo"
    return {"ok": False, "motivo": "recusou", "msg": msg, "resposta": resp}


def registrar_historico(modulo, estrategia, resultado):
    """
    Anexa a avaliacao ao CSV e envia para a planilha. Nunca derruba a
    requisicao: devolve o status do envio (ver enviar_para_sheets) para a tela.
    """
    try:
        c = resultado.get("cobertura") or {}
        por_tipo = c.get("por_tipo") or {}

        def pct_tipo(t):
            d = por_tipo.get(t)
            if not d or not d["total"]:
                return ""
            return round(100.0 * d["cobertos"] / d["total"], 1)

        fsm = c.get("fsm")
        m = resultado.get("mutacao") or {}
        linha = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modulo": modulo,
            "estrategia": estrategia,
            "compilou": resultado["compilou"],
            "executou": resultado["executou"],
            "passou": resultado["passou"],
            "cobertura_pct": c.get("pct", ""),
            "linha_pct": pct_tipo("line"),
            "alternancia_pct": pct_tipo("toggle"),
            "desvio_pct": pct_tipo("branch"),
            "fsm_pct": fsm["pct"] if fsm else "",
            "mutantes_avaliados": m.get("total", ""),
            "mutantes_mortos": m.get("mortos", ""),
            "mutation_score": "" if m.get("score") is None else m.get("score"),
        }
        novo = not HISTORICO.exists()
        with open(HISTORICO, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(linha))
            if novo:
                w.writeheader()
            w.writerow(linha)
        # Envia para a planilha (com ICV/classe extra). enviar_para_sheets
        # engole seus proprios erros, entao nao derruba a avaliacao.
        icv = resultado.get("icv") or {}
        return enviar_para_sheets({
            **linha,
            "icv": icv.get("icv", ""),
            "classe": icv.get("classificacao", ""),
        })
    except OSError as e:
        return {"ok": False, "motivo": "csv",
                "msg": f"não gravou o historico.csv ({e}); nada foi enviado à planilha"}


def salvar_avaliacao(modulo, estrategia, rtl_txt, tb_txt, resultado):
    """
    Guarda RTL, testbench e resultado (com a lista de mutantes) em
    avaliacoes/<data>_<modulo>_<estrategia>/. Devolve o caminho relativo,
    para a tela, ou None se nao conseguiu gravar. Nunca levanta erro.
    """
    def limpo(s):
        return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_") or "sem_nome"

    base = AVALIACOES / "{}_{}_{}".format(
        datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), limpo(modulo), limpo(estrategia))
    pasta, n = base, 1
    while pasta.exists():           # duas avaliacoes no mesmo segundo
        n += 1
        pasta = base.with_name(f"{base.name}_{n}")
    try:
        pasta.mkdir(parents=True)
        (pasta / "dut.v").write_text(rtl_txt)
        (pasta / "tb.v").write_text(tb_txt)
        (pasta / "resultado.json").write_text(json.dumps(
            {"modulo": modulo, "estrategia": estrategia, **resultado},
            ensure_ascii=False, indent=2))
    except OSError:
        return None
    return str(pasta.relative_to(BASE))


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def run(cmd, cwd, timeout=TIMEOUT):
    """Roda um comando, captura tudo, nunca levanta em erro de processo."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout apos {timeout}s"
    except FileNotFoundError as e:
        return 127, "", str(e)


def build_dir(work):
    """Verilator constroi C++ em disco; precisa ser caminho sem espacos."""
    d = Path(tempfile.gettempdir()) / f"veriweb_{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------
# Etapa 1: compilar + simular + cobertura
# --------------------------------------------------------------------------

def compilar_e_cobrir(rtl_path, tb_path, work):
    """
    Compila o RTL+TB com o harness, roda a simulacao e coleta cobertura.
    Retorna dict com: compilou, executou, passou, log, cobertura.
    """
    mdir = build_dir(work)
    # O make nao compila fontes C++ em caminho com espaco -> copia o harness.
    harness_local = mdir / "main.cpp"
    shutil.copy(HARNESS, harness_local)

    # --- compilar ---
    rc, out, err = run(
        [
            "verilator", "--cc", "--exe", "--build",
            "--timing", "--coverage",
            "-j", BUILD_JOBS,   # verilacao + build C++ em paralelo
            # -Wno-fatal: warnings (LATCH, CASEINCOMPLETE...) nao bloqueiam
            "-Wno-fatal",
            "-Wno-DECLFILENAME", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
            "--Mdir", str(mdir),
            "--top-module", TB_TOP,
            "-o", "sim",
            str(rtl_path), str(tb_path), str(harness_local),
        ],
        cwd=work,
    )
    if rc != 0:
        return {
            "compilou": False, "executou": False, "passou": False,
            "log": (out + err).strip(),
            "cobertura": None,
        }

    # --- simular ---
    covfile = Path(work) / "coverage.dat"
    sim_bin = mdir / "sim"
    rc, out, err = run([str(sim_bin), str(covfile)], cwd=work, timeout=SIM_TIMEOUT)

    executou = rc != 127 and "timeout" not in err
    # exit 0 = testbench passou; != 0 (ex: $fatal) = alguma checagem falhou
    passou = (rc == 0)
    sim_log = (out + err).strip()

    # --- cobertura ---
    cobertura = ler_cobertura(covfile, rtl_path)

    return {
        "compilou": True,
        "executou": executou,
        "passou": passou,
        "log": sim_log,
        "cobertura": cobertura,
    }


def ler_cobertura(covfile, rtl_path):
    """
    Extrai pontos cobertos / total lendo direto o coverage.dat como fonte
    da verdade (o formato e' texto; nao chama verilator_coverage). Coberto =
    contagem >= 1; conta so pontos do dut.v, separando por tipo (v_line /
    v_toggle / v_branch).
    """
    if not covfile.exists():
        return None

    # Conta pontos: cada linha "C '...' N" e' um ponto com contagem N.
    # So pontos do dut.v: cobertura mede o quanto DO MODULO o testbench
    # exercitou — pontos do proprio tb.v nao entram na conta.
    total = 0
    cobertos = 0
    por_tipo = {}  # v_line / v_toggle / v_branch ...
    for linha in covfile.read_text(errors="ignore").splitlines():
        if not linha.startswith("C "):
            continue
        arq = re.search("\x01f\x02([^\x01']*)", linha)
        if not arq or not arq.group(1).endswith("dut.v"):
            continue
        m = re.search(r"'.*'\s+(\d+)\s*$", linha)
        if not m:
            continue
        cnt = int(m.group(1))
        total += 1
        if cnt >= 1:  # --annotate-min 1: coberto = exercitado ao menos 1x
            cobertos += 1
        # ancorado na chave "page": o caminho do arquivo tambem pode conter "v_"
        tm = re.search("\x01page\x02v_(\\w+?)/", linha)
        tipo = tm.group(1) if tm else "outro"
        d = por_tipo.setdefault(tipo, {"total": 0, "cobertos": 0})
        d["total"] += 1
        if cnt >= 1:
            d["cobertos"] += 1

    pct = round(100.0 * cobertos / total, 1) if total else 0.0
    fsm = cobertura_fsm(rtl_path.read_text(errors="ignore"), covfile)
    return {
        "cobertos": cobertos, "total": total, "pct": pct,
        "por_tipo": por_tipo, "fsm": fsm,
    }


def cobertura_fsm(rtl_texto, covfile):
    """
    Cobertura de maquina de estados (o Verilator nao emite esse tipo).
    Aproximacao: acha no RTL um case cujo seletor e' um registrador (sinal
    atualizado com <=, o padrao de FSM) e mede a cobertura dos pontos de
    branch dentro desse case. Sem FSM detectavel -> None ("sem cobertura").
    """
    # 1) intervalos de linha dos case de estado no RTL
    intervalos = []
    for m in re.finditer(r"\bcase[xz]?\s*\(([^)]+)\)", rtl_texto):
        ids = re.findall(r"[A-Za-z_]\w*", m.group(1))
        if not any(re.search(rf"\b{re.escape(s)}\s*<=", rtl_texto) for s in ids):
            continue  # seletor nao e' registrador: nao parece FSM
        fim = re.search(r"\bendcase\b", rtl_texto[m.end():])
        if not fim:
            continue
        ini = rtl_texto.count("\n", 0, m.start()) + 1
        fin = rtl_texto.count("\n", 0, m.end() + fim.end()) + 1
        intervalos.append((ini, fin))
    if not intervalos:
        return None

    # 2) itens do case no coverage.dat: pontos v_line com o=case no dut.v
    #    (um ponto por braco do case = um por estado da FSM)
    total = 0
    cobertos = 0
    for linha in covfile.read_text(errors="ignore").splitlines():
        if not linha.startswith("C ") or "\x01page\x02v_line/" not in linha:
            continue
        if "\x01o\x02case" not in linha:
            continue
        arq = re.search("\x01f\x02([^\x01']*)", linha)
        num = re.search("\x01l\x02(\\d+)", linha)
        cnt = re.search(r"'\s+(\d+)\s*$", linha)
        if not (arq and num and cnt) or not arq.group(1).endswith("dut.v"):
            continue
        n = int(num.group(1))
        if not any(a <= n <= b for a, b in intervalos):
            continue
        total += 1
        if int(cnt.group(1)) >= 1:
            cobertos += 1
    if total == 0:
        return None
    return {
        "cobertos": cobertos, "total": total,
        "pct": round(100.0 * cobertos / total, 1),
    }


# --------------------------------------------------------------------------
# Etapa 2: teste de mutacao
# --------------------------------------------------------------------------

# Operadores de mutacao de primeira ordem, por regex sobre o texto do RTL.
# Um ponto mutavel = uma ocorrencia na logica (always/assign); cada ponto
# gera no maximo UM mutante — sem completar artificialmente ate 4.
MUTACOES = [
    # aritmeticos ("+:"/"-:" de part-select ficam de fora)
    ("+ -> -",   r"\+(?!:)", "-"),
    ("- -> +",   r"(?<![<>=!])-(?![>:-])", "+"),
    # "*" de multiplicacao apenas: exclui "@(*)", atributos "(* *)" e "**"
    ("* -> +",   r"(?<![(*])\*(?![*)])", "+"),
    # bit a bit
    ("& -> |",   r"(?<!&)&(?!&)", "|"),
    ("| -> &",   r"(?<!\|)\|(?!\|)", "&"),
    ("^ -> &",   r"\^(?!~)", "&"),
    # logicos
    ("&& -> ||", r"&&",   "||"),
    ("|| -> &&", r"\|\|", "&&"),
    # igualdade (=== / !== ficam de fora)
    ("== -> !=", r"(?<![=!<>])==(?!=)", "!="),
    ("!= -> ==", r"(?<!=)!=(?!=)", "=="),
    # relacionais; "<=" fica de fora: dentro de always e' quase sempre
    # atribuicao nao-bloqueante, e o mutante nunca compila
    ("< -> >=",  r"(?<![<>=])<(?![<=])", ">="),
    ("> -> <=",  r"(?<![<>=])>(?![>=])", "<="),
    (">= -> <",  r">=",   "<"),
    # deslocamentos
    ("<< -> >>", r"(?<!<)<<(?!<)", ">>"),
    (">> -> <<", r"(?<!>)>>(?!>)", "<<"),
    # constantes com base explicita (ex: 2'd1 -> 2'd0)
    ("constante -> 0", r"'([bdh])\s*[1-9a-fA-F][0-9a-fA-F_]*\b",
     lambda m: "'" + m.group(1) + "0"),
    ("constante 0 -> 1", r"'([bdh])\s*0+\b",
     lambda m: "'" + m.group(1) + "1"),
    # ramos de um ?: simples trocados (cond ? A : B -> cond ? B : A)
    ("?: ramos trocados", r"\?\s*([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)",
     lambda m: "? " + m.group(2) + " : " + m.group(1)),
    # inversao de condicao simples: if (x) -> if (!x) e vice-versa
    ("if(x) -> if(!x)", r"\bif\s*\(\s*([A-Za-z_]\w*)\s*\)",
     lambda m: "if (!" + m.group(1) + ")"),
    ("if(!x) -> if(x)", r"\bif\s*\(\s*!\s*([A-Za-z_]\w*)\s*\)",
     lambda m: "if (" + m.group(1) + ")"),
]


def regioes_de_logica(rtl_texto):
    """
    Spans [ini, fim) onde mutacao e' permitida: corpo de always* e de
    assign. Fora deles (portas, larguras [W-1:0], localparam, typedef)
    um operador trocado gera mutante equivalente ou invalido.

    Heuristica por ancoras, sem parser: um bloco always vai da palavra
    "always" ate a proxima palavra-chave estrutural do modulo (outro
    always, assign, declaracao, endmodule...) — nenhuma delas pode
    aparecer dentro do proprio corpo do always. Um assign vai ate o ";".
    """
    # comentarios viram espacos (posicoes preservadas)
    limpo = re.sub(
        r"//[^\n]*|/\*.*?\*/",
        lambda m: " " * len(m.group(0)),
        rtl_texto, flags=re.S,
    )
    ancoras = list(re.finditer(
        r"\b(always(?:_ff|_comb|_latch)?|assign|initial|function|endfunction|"
        r"task|endtask|generate|endgenerate|module|endmodule|localparam|"
        r"parameter|input|output|inout|wire|reg|logic|integer|genvar|"
        r"typedef)\b",
        limpo,
    ))
    regioes = []
    for k, a in enumerate(ancoras):
        kw = a.group(1)
        if kw == "assign":
            fim = limpo.find(";", a.end())
            if fim >= 0:
                regioes.append((a.end(), fim))
        elif kw.startswith("always"):
            fim = ancoras[k + 1].start() if k + 1 < len(ancoras) else len(limpo)
            regioes.append((a.end(), fim))
    return regioes


def gerar_mutantes(rtl_texto):
    """
    Gera candidatos de primeira ordem: um por ponto mutavel (ocorrencia de
    operador DENTRO de always/assign), cada um com apenas aquela ocorrencia
    trocada. Ordem de varredura do arquivo — deterministica.
    """
    linhas_orig = rtl_texto.splitlines()
    regioes = regioes_de_logica(rtl_texto)
    dentro = lambda i: any(a <= i < b for a, b in regioes)
    # As regioes ja nasceram sem comentarios de fora, mas um comentario no
    # meio de um always ainda esta dentro do span: ignora tambem.
    comentarios = [
        m.span() for m in re.finditer(r"//[^\n]*|/\*.*?\*/", rtl_texto, re.S)
    ]
    em_comentario = lambda i: any(a <= i < b for a, b in comentarios)

    mutantes = []
    for desc, pat, repl in MUTACOES:
        for m in re.finditer(pat, rtl_texto):
            i, j = m.start(), m.end()
            if not dentro(i) or em_comentario(i):
                continue
            novo = repl(m) if callable(repl) else repl
            mut = rtl_texto[:i] + novo + rtl_texto[j:]
            if mut == rtl_texto:
                continue
            num = rtl_texto.count("\n", 0, i) + 1
            mutantes.append({
                "pos": i,
                "desc": desc,
                "texto": mut,
                "linha": num,
                "original": linhas_orig[num - 1].strip(),
                "mutado": mut.splitlines()[num - 1].strip(),
            })
    mutantes.sort(key=lambda mt: mt["pos"])
    return mutantes


def selecionar_espalhados(candidatos, n):
    """
    Reordena os candidatos para amostrar regioes DIFERENTES do modulo, em vez
    de pegar os primeiros n do topo do arquivo (que num modulo grande caem
    todos no mesmo bloco — p.ex. so o reset).

    Divide os pontos mutaveis em n faixas por posicao no arquivo
    (inicio/meio/fim) e intercala (round-robin) uma faixa de cada vez. Assim
    os primeiros da fila cobrem trechos distintos do modulo; se um candidato
    nao compilar, o proximo da fila ja vem de outra regiao, mantendo o
    espalhamento e servindo de reserva. Desempate por operador dentro da
    faixa, para variar tambem o tipo de mutacao. Deterministica.
    """
    if not candidatos:
        return []
    ordenados = sorted(candidatos, key=lambda m: m["pos"])
    lo, hi = ordenados[0]["pos"], ordenados[-1]["pos"]
    span = max(hi - lo, 1)
    faixas = [[] for _ in range(n)]
    for m in ordenados:
        idx = min(n - 1, (m["pos"] - lo) * n // span)
        faixas[idx].append(m)
    # dentro de cada faixa, varia o operador: agrupa por desc e intercala
    for k, f in enumerate(faixas):
        por_op = {}
        for m in f:
            por_op.setdefault(m["desc"], []).append(m)
        filas = list(por_op.values())
        rr = []
        while any(filas):
            for fila in filas:
                if fila:
                    rr.append(fila.pop(0))
        faixas[k] = rr
    # round-robin entre as faixas: 1 do inicio, 1 do meio, 1 do fim, ...
    saida = []
    while any(faixas):
        for f in faixas:
            if f:
                saida.append(f.pop(0))
    return saida


def testar_mutacao(rtl_texto, tb_path, work, max_mutantes=MAX_MUTANTES):
    """
    Avalia max_mutantes mutantes validos (que compilam), amostrando regioes
    distintas do modulo (ver selecionar_espalhados) em vez do topo do arquivo.
    Mutante que nao compila e' descartado sem contar; o proximo da fila
    (ja de outra regiao) entra no lugar. Menos de max_mutantes pontos
    mutaveis na logica => avalia quantos houver.
    exit!=0 => testbench detectou a troca => mutante morto.
    Usa --binary (nao precisa de cobertura aqui) => mais rapido.
    """
    candidatos = selecionar_espalhados(gerar_mutantes(rtl_texto), max_mutantes)
    if not candidatos:
        return {
            "total": 0, "mortos": 0, "sobreviventes": 0, "score": None,
            "detalhe": [],
            "aviso": "nenhum operador mutavel na lógica (always/assign) do RTL",
        }

    mortos = 0
    sobreviventes = 0
    detalhe = []
    tentativas = 0

    for cand in candidatos:
        if mortos + sobreviventes >= max_mutantes:
            break
        # limite de compilacoes para nao estourar o tempo da requisicao
        # num RTL onde muitos candidatos seguidos nao compilam
        if tentativas >= MAX_TENTATIVAS:
            break
        tentativas += 1

        mdir = build_dir(work)
        mut_file = mdir / "mut.v"
        mut_file.write_text(cand["texto"])

        rc, out, err = run(
            [
                "verilator", "--binary", "--timing", "-Wno-fatal",
                "-j", BUILD_JOBS,   # compile de mutante em paralelo
                "-Wno-DECLFILENAME", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
                "--Mdir", str(mdir), "--top-module", TB_TOP, "-o", "mut",
                str(mut_file), str(tb_path),
            ],
            cwd=work,
        )
        if rc != 0:
            # Nao compilou: mutante invalido, tenta o proximo candidato.
            shutil.rmtree(mdir, ignore_errors=True)
            continue

        rc, out, err = run([str(mdir / "mut")], cwd=work, timeout=SIM_TIMEOUT)
        status = "morto" if rc != 0 else "sobreviveu"
        if rc != 0:
            mortos += 1
        else:
            sobreviventes += 1
        detalhe.append({
            "desc": cand["desc"],
            "status": status,
            "linha": cand["linha"],
            "original": cand["original"],
            "mutado": cand["mutado"],
        })
        shutil.rmtree(mdir, ignore_errors=True)

    validos = mortos + sobreviventes
    score = round(100.0 * mortos / validos, 1) if validos else None
    aviso = None
    if validos == 0:
        aviso = "nenhum mutante valido: todos falharam ao compilar"
    elif validos < max_mutantes:
        aviso = f"apenas {validos} mutante(s) valido(s) no RTL"
    return {
        "total": validos, "mortos": mortos, "sobreviventes": sobreviventes,
        "score": score, "detalhe": detalhe, "aviso": aviso,
    }


# --------------------------------------------------------------------------
# Indice de Complexidade Combinada para Verificacao (ICV)
#
# Metrica SO do DUT (texto do modulo RTL). Combina 4 pontuacoes de 0 a 3:
#   ICV = P_LOC*0.30 + P_FSM*0.30 + P_IO*0.20 + P_LOG*0.20   (ICV vai de 0 a 3)
# Cada componente e' extraido por heuristica de texto (sem parser Verilog),
# entao P_FSM e P_LOG sao aproximados — a tela mostra os brutos para auditoria.
# Escala 0-3 (e nao 0-5) porque a classe de modulos do estudo nunca chega perto
# do topo: as faixas altas de cada componente (modulos gigantes) foram fundidas.
# --------------------------------------------------------------------------

def _sem_comentarios(txt):
    """Remove /* */ e // preservando as quebras de linha (para contar LOC)."""
    txt = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), txt, flags=re.S)
    txt = re.sub(r"//[^\n]*", "", txt)
    return txt


def _resolver_ifdef(txt):
    """
    Mini-preprocessador: resolve `define/`undef/`ifdef/`ifndef/`elsif/`else/
    `endif e DESCARTA os ramos inativos. Assim a analise nao conta codigo morto
    (ex: no CORDIC, portas em `ifdef ITERATE/VALID_FLAG e a tabela DEGREE_8_8).
    Nao expande macros — so decide quais linhas ficam.
    """
    defs = set()
    stack = []   # cada frame: {"active", "parent", "taken"}
    ativo = lambda: stack[-1]["active"] if stack else True
    out = []
    for linha in txt.splitlines():
        s = linha.strip()
        m = re.match(r"`(ifdef|ifndef)\s+(\w+)", s)
        if m:
            parent = ativo()
            cond = (m.group(2) in defs) if m.group(1) == "ifdef" else (m.group(2) not in defs)
            stack.append({"active": parent and cond, "parent": parent, "taken": parent and cond})
            continue
        m = re.match(r"`elsif\s+(\w+)", s)
        if m and stack:
            fr = stack[-1]
            act = fr["parent"] and (not fr["taken"]) and (m.group(1) in defs)
            fr["active"] = act
            fr["taken"] = fr["taken"] or act
            continue
        if s.startswith("`else") and stack:
            fr = stack[-1]
            fr["active"] = fr["parent"] and (not fr["taken"])
            fr["taken"] = True
            continue
        if s.startswith("`endif"):
            if stack:
                stack.pop()
            continue
        if ativo():
            md = re.match(r"`define\s+(\w+)", s)
            if md:
                defs.add(md.group(1))
            mu = re.match(r"`undef\s+(\w+)", s)
            if mu:
                defs.discard(mu.group(1))
            out.append(linha)
    return "\n".join(out)


def _texto_ativo(rtl_texto):
    """Texto pronto para analise: sem comentarios e com ifdefs resolvidos."""
    return _resolver_ifdef(_sem_comentarios(rtl_texto))


def _modulo_topo(t):
    """
    Corpo do modulo de topo (o DUT): o modulo que NENHUM outro instancia.
    Para arquivos com submodulos (ex: CORDIC), evita contar portas dos helpers.
    """
    mods = re.findall(r"\bmodule\s+(\w+)", t)
    if not mods:
        return t
    instanciados = {nome for nome in mods
                    if re.search(rf"\b{re.escape(nome)}\s+\w+\s*\(", t)}
    candidatos = [m for m in mods if m not in instanciados] or mods
    nome_topo = candidatos[-1]
    mm = re.search(rf"\bmodule\s+{re.escape(nome_topo)}\b.*?\bendmodule\b", t, re.S)
    return mm.group(0) if mm else t


def _faixa(valor, faixas):
    """faixas = lista de (limite_superior, pontuacao); ultima com limite None."""
    for lim, pts in faixas:
        if lim is None or valor <= lim:
            return pts
    return faixas[-1][1]


def p_loc(t):
    """Linhas de codigo: sem comentarios/ifdef mortos e sem linhas em branco."""
    n = sum(1 for l in t.splitlines() if l.strip())
    pts = _faixa(n, [(30, 1), (100, 2), (None, 3)])
    return pts, n


def p_io(t):
    """Conta PORTAS input/output/inout do modulo de topo (nao bits)."""
    corpo = _modulo_topo(t)
    # remove corpos de function/task (tem 'input' de argumento, nao e' porta)
    corpo = re.sub(r"\bfunction\b.*?\bendfunction\b", " ", corpo, flags=re.S)
    corpo = re.sub(r"\btask\b.*?\bendtask\b", " ", corpo, flags=re.S)
    corpo = re.sub(r"\[[^\]]*\]", " ", corpo)               # tira larguras [x:y]
    corpo = re.sub(r"\b(wire|reg|logic|signed|unsigned)\b", " ", corpo)
    total = 0
    for m in re.finditer(
        r"\b(?:input|output|inout)\b"
        r"((?:(?!\b(?:input|output|inout)\b)[^;()])*)", corpo):
        total += len(re.findall(r"[A-Za-z_]\w*", m.group(1)))
    pts = _faixa(total, [(4, 1), (10, 2), (None, 3)])
    return pts, total


def _nomes_parametros(t):
    """Todos os nomes declarados em parameter/localparam (varios por linha)."""
    nomes = set()
    for stmt in re.finditer(r"\b(?:parameter|localparam)\b([^;]*)", t):
        for nm in re.finditer(r"\b([A-Za-z_]\w*)\s*=", stmt.group(1)):
            nomes.add(nm.group(1))
    return nomes


# Literal Verilog inteiro: 3, 2'd3, 4'h8, 3'b010, 8'hFF...
_LIT = r"(?:\d+)?'[sS]?[bodhBODH][0-9a-fA-F_]+|\d+"


def _valor_literal(s):
    """Valor inteiro de um literal Verilog; None se nao der para converter."""
    s = s.strip().replace("_", "")
    m = re.fullmatch(r"(?:\d+)?'[sS]?([bodhBODH])([0-9a-fA-F]+)", s)
    if m:
        base = {"b": 2, "o": 8, "d": 10, "h": 16}[m.group(1).lower()]
        try:
            return int(m.group(2), base)
        except ValueError:
            return None
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None


def _e_estado_numerico(v, t):
    """
    Heuristica anti-contador: o sinal e' DECODIFICADO em assigns
    (assign saida = v == NUM) com >=2 valores distintos. Isso caracteriza
    uma FSM de estados numericos e nao um simples contador.
    """
    dec = set()
    for m in re.finditer(rf"\bassign\b[^;]*?\b{re.escape(v)}\s*==\s*({_LIT})", t):
        val = _valor_literal(m.group(1))
        if val is not None:
            dec.add(val)
    return len(dec) >= 2


def _estados_numericos(estado, t):
    """Valores numericos distintos atribuidos/comparados ao estado."""
    vals = set()
    for m in re.finditer(rf"\b{re.escape(estado)}\s*(?:<=|==|!=|<|>|>=)\s*({_LIT})", t):
        val = _valor_literal(m.group(1))
        if val is not None:
            vals.add(val)
    # rotulos numericos de um case(estado)
    mc = re.search(rf"\bcase[xz]?\s*\(\s*{re.escape(estado)}\s*\)(.*?)\bendcase\b",
                   t, re.S)
    if mc:
        for lab in re.finditer(rf"(?:^|\n)\s*({_LIT})\s*:", mc.group(1)):
            val = _valor_literal(lab.group(1))
            if val is not None:
                vals.add(val)
    return vals


def p_fsm(t):
    """
    Numero de estados da FSM. Detecta um registrador de estado (var com <= em
    bloco de clock, usada em case(var) ou comparada com constantes) e conta as
    constantes de estado (parameter/localparam ou macros `define).
    Para estados em `define percorridos por aritmetica (ex: state<=state+1),
    conta TODOS os `define que compartilham o prefixo comum dos referenciados.
    Tambem reconhece FSMs com estados NUMERICOS (state==2, state<=3), contando
    os literais distintos. Sem FSM detectavel -> 0.
    """
    regs = set(re.findall(r"(\w+)\s*<=", t))
    estado = None
    for m in re.finditer(r"\bcase[xz]?\s*\(\s*(\w+)\s*\)", t):
        if m.group(1) in regs:
            estado = m.group(1)
            break
    if not estado:                       # FSM por if com estados nomeados
        for v in regs:
            if re.search(rf"\b{re.escape(v)}\s*(==|>|<|>=)\s*`?[A-Za-z_]", t):
                estado = v
                break
    if not estado:                       # FSM com estados numericos (state==2..)
        for v in regs:
            if _e_estado_numerico(v, t):
                estado = v
                break
    if not estado:
        return 0, 0

    params = _nomes_parametros(t)
    defines = set(re.findall(r"`define\s+([A-Za-z_]\w*)", t))
    simbolos = params | defines

    # rotulos de case (inicio de linha "NOME:") que sao estados declarados
    labels = set()
    for lab in re.finditer(r"(?:^|\n)\s*`?([A-Za-z_]\w*)\s*:", t):
        nome = lab.group(1)
        if nome != "default" and nome in simbolos:
            labels.add(nome)

    if labels:
        n = len(labels)
    else:
        # FSM por if (sem case): constantes comparadas/atribuidas ao estado
        refs = set()
        for m in re.finditer(
                rf"{re.escape(estado)}\s*(?:<=|==|>|<|>=)\s*(`?[A-Za-z_]\w*)", t):
            refs.add(m.group(1).lstrip("`"))
        ref_defs = {r for r in refs if r in defines}
        ref_params = {r for r in refs if r in params}
        estados = set(ref_params)
        if ref_defs:
            pref = os.path.commonprefix(list(ref_defs))
            if len(pref) >= 2 and "_" in pref:
                estados |= {d for d in defines if d.startswith(pref)}
            else:
                estados |= ref_defs
        n = len(estados)
        if n == 0:                       # sem estados nomeados -> tenta numericos
            n = len(_estados_numericos(estado, t))

    pts = _faixa(n, [(1, 0), (4, 1), (9, 2), (None, 3)])
    return pts, n


def p_log(t):
    """
    Natureza da logica (acumulativo, teto 3):
      +1 aritmetica (+,-,* na logica)
      +2 serial/shift register (registrador que recebe versao concatenada de si)
      +2 pipeline (generate-for: replicacao estrutural de estagios)
    Retorna (pontuacao, lista_de_flags).
    """
    flags = []
    pts = 0

    # aritmetica: so dentro da logica (always/assign)
    regioes = regioes_de_logica(t)
    dentro = lambda i: any(a <= i < b for a, b in regioes)
    arit = False
    for pat in [r"(?<![<>=!+])\+(?![+:])", r"(?<![<>=!-])-(?![>:-])",
                r"(?<![(*])\*(?![*)])"]:
        for m in re.finditer(pat, t):
            if dentro(m.start()):
                arit = True
                break
        if arit:
            break
    if arit:
        pts += 1
        flags.append("aritmética")

    # serial: LHS recebe concatenacao que contem o proprio LHS -> shift register
    if re.search(r"(\w+)\s*(?:<=|=)\s*\{[^;{}]*\b\1\s*\[", t):
        pts += 2
        flags.append("serial/shift")

    # pipeline: generate ... for (replicacao estrutural de estagios)
    if re.search(r"\bgenerate\b", t) and re.search(r"\bfor\b", t):
        pts += 2
        flags.append("pipeline")

    return min(pts, 3), flags


def calcular_icv(rtl_texto):
    """Monta o ICV do DUT e a classificacao final."""
    t = _texto_ativo(rtl_texto)
    ploc, loc_n = p_loc(t)
    pfsm, fsm_n = p_fsm(t)
    pio, io_n = p_io(t)
    plog, log_flags = p_log(t)

    icv = ploc * 0.30 + pfsm * 0.30 + pio * 0.20 + plog * 0.20
    icv = round(icv, 2)
    # Faixas calibradas para a classe de modulos do estudo (HDLBits / cores
    # abertos pequenos), cujo ICV vai na pratica de ~0,5 a ~2,5. A escala
    # absoluta original (ate 5) deixava Alta/Muito Alta vazias.
    if icv <= 1.2:
        classe = "Fácil"
    elif icv <= 1.9:
        classe = "Média"
    elif icv <= 2.3:
        classe = "Alta"
    else:
        classe = "Muito Alta"

    return {
        "icv": icv,
        "classificacao": classe,
        "componentes": {
            "P_LOC": {"pts": ploc, "peso": 0.30, "detalhe": f"{loc_n} linhas de código"},
            "P_FSM": {"pts": pfsm, "peso": 0.30, "detalhe": f"{fsm_n} estado(s)"},
            "P_IO":  {"pts": pio,  "peso": 0.20, "detalhe": f"{io_n} portas"},
            "P_LOG": {"pts": plog, "peso": 0.20,
                      "detalhe": ", ".join(log_flags) if log_flags else "combinacional básica"},
        },
    }


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/avaliar", methods=["POST"])
def avaliar():
    data = request.get_json(force=True)
    rtl_txt = data.get("rtl", "")
    tb_txt = data.get("tb", "")

    if not rtl_txt.strip() or not tb_txt.strip():
        return jsonify({"erro": "RTL e testbench nao podem estar vazios"}), 400

    # Aviso util: o testbench precisa ter "module tb"
    if not re.search(r"\bmodule\s+tb\b", tb_txt):
        return jsonify({
            "erro": "O modulo do testbench deve se chamar 'tb' "
                    "(ex: module tb; ... endmodule)"
        }), 400

    work = Path(tempfile.mkdtemp(prefix="veriweb_work_"))
    try:
        rtl_path = work / "dut.v"
        tb_path = work / "tb.v"
        rtl_path.write_text(rtl_txt)
        tb_path.write_text(tb_txt)

        resultado = compilar_e_cobrir(rtl_path, tb_path, work)

        # ICV: analise SO do texto do DUT — independe de compilar/executar.
        resultado["icv"] = calcular_icv(rtl_txt)

        # Mutacao exige testbench passando no RTL original: se ja falha nele,
        # todo mutante "morre" de graca e o score vira 100% enganoso.
        if not (resultado["compilou"] and resultado["executou"]):
            resultado["mutacao"] = None
        elif not resultado["passou"]:
            resultado["mutacao"] = {
                "total": 0, "mortos": 0, "sobreviventes": 0, "score": None,
                "detalhe": [],
                "aviso": "testbench reprovou no RTL original: "
                         "mutação não avaliada",
            }
        else:
            resultado["mutacao"] = testar_mutacao(rtl_txt, tb_path, work)

        modulo = data.get("modulo", "").strip()
        estrategia = data.get("estrategia", "").strip()
        resultado["planilha"] = registrar_historico(modulo, estrategia, resultado)
        resultado["salvo_em"] = salvar_avaliacao(modulo, estrategia, rtl_txt, tb_txt,
                                                 resultado)
        return jsonify(resultado)
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.route("/historico.csv")
def historico():
    if not HISTORICO.exists():
        return "nenhuma avaliação registrada ainda", 404
    return send_file(HISTORICO, as_attachment=True,
                     download_name="historico.csv")


if __name__ == "__main__":
    # host 0.0.0.0 para funcionar tambem via WSL
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
