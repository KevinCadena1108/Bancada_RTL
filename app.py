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
import os
import re
import shutil
import subprocess
import tempfile
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

# Timeout por invocacao do Verilator/simulacao (segundos).
TIMEOUT = 60

# Quantos mutantes validos (que compilam) avaliar por rodada.
MAX_MUTANTES = 4

# Teto de compilacoes de mutante por rodada (validos ou nao), para limitar
# o tempo total da requisicao.
MAX_TENTATIVAS = 16

# Historico de avaliacoes (uma linha por rodada), para as tabelas
# comparativas do experimento. Exportado em /historico.csv.
HISTORICO = BASE / "historico.csv"


def registrar_historico(modulo, estrategia, resultado):
    """Anexa a avaliacao ao CSV. Nunca derruba a requisicao se falhar."""
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
    except OSError:
        pass


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
    rc, out, err = run([str(sim_bin), str(covfile)], cwd=work)

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
    Roda verilator_coverage e extrai pontos cobertos / total.
    Le direto o coverage.dat como fonte da verdade (o binario e' texto).
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

        rc, out, err = run([str(mdir / "mut")], cwd=work)
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

        registrar_historico(
            data.get("modulo", "").strip(),
            data.get("estrategia", "").strip(),
            resultado,
        )
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
    app.run(host="127.0.0.1", port=5000, debug=True)
