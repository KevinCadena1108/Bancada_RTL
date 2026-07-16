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

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from flask import Flask, render_template, request, jsonify

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
    cobertura = ler_cobertura(covfile, work)

    return {
        "compilou": True,
        "executou": executou,
        "passou": passou,
        "log": sim_log,
        "cobertura": cobertura,
    }


def ler_cobertura(covfile, work):
    """
    Roda verilator_coverage e extrai pontos cobertos / total.
    Le direto o coverage.dat como fonte da verdade (o binario e' texto).
    """
    if not covfile.exists():
        return None

    # Conta pontos: cada linha "C '...' N" e' um ponto com contagem N.
    total = 0
    cobertos = 0
    por_tipo = {}  # v_line / v_toggle / v_branch ...
    for linha in covfile.read_text(errors="ignore").splitlines():
        if not linha.startswith("C "):
            continue
        m = re.search(r"'.*'\s+(\d+)\s*$", linha)
        if not m:
            continue
        cnt = int(m.group(1))
        total += 1
        if cnt >= 1:  # --annotate-min 1: coberto = exercitado ao menos 1x
            cobertos += 1
        tm = re.search(r"v_(\w+?)/", linha)
        tipo = tm.group(1) if tm else "outro"
        d = por_tipo.setdefault(tipo, {"total": 0, "cobertos": 0})
        d["total"] += 1
        if cnt >= 1:
            d["cobertos"] += 1

    pct = round(100.0 * cobertos / total, 1) if total else 0.0
    return {"cobertos": cobertos, "total": total, "pct": pct, "por_tipo": por_tipo}


# --------------------------------------------------------------------------
# Etapa 2: teste de mutacao
# --------------------------------------------------------------------------

# Operadores de mutacao de primeira ordem, por regex sobre o texto do RTL.
# Cada tupla: (descricao, regex, substituicao).
# So se aplica quando o padrao existe no modulo -> mutantes gerados variam.
MUTACOES = [
    ("+ -> -",   r"\+",   "-"),
    ("- -> +",   r"(?<![<>=!])-(?![>-])", "+"),
    ("* -> +",   r"\*",   "+"),
    ("& -> |",   r"&(?!&)", "|"),
    ("| -> &",   r"\|(?!\|)", "&"),
    ("&& -> ||", r"&&",   "||"),
    ("|| -> &&", r"\|\|", "&&"),
    ("== -> !=", r"==",   "!="),
    ("!= -> ==", r"!=",   "=="),
    ("< -> >=",  r"(?<![<>=])<(?![<=])", ">="),
    ("> -> <=",  r"(?<![<>=])>(?![>=])", "<="),
    (">= -> <",  r">=",   "<"),
    ("<= -> >",  r"<=",   ">"),
]


def gerar_mutantes(rtl_texto):
    """
    Gera mutantes de primeira ordem: para cada ocorrencia de cada operador,
    uma copia do RTL com apenas aquela ocorrencia trocada.
    Retorna lista de dicts com o texto mutado e a linha antes/depois da troca.
    """
    linhas_orig = rtl_texto.splitlines()
    mutantes = []
    for desc, pat, repl in MUTACOES:
        for m in re.finditer(pat, rtl_texto):
            i, j = m.start(), m.end()
            mut = rtl_texto[:i] + repl + rtl_texto[j:]
            if mut == rtl_texto:
                continue
            num = rtl_texto.count("\n", 0, i) + 1
            mutantes.append({
                "desc": desc,
                "texto": mut,
                "linha": num,
                "original": linhas_orig[num - 1].strip(),
                "mutado": mut.splitlines()[num - 1].strip(),
            })
    return mutantes


def ordenar_diverso(mutantes):
    """
    Intercala os mutantes por operador (round-robin) para que os primeiros
    avaliados cubram operadores diferentes, e nao 4 variantes do mesmo "+".
    """
    por_op = {}
    for mt in mutantes:
        por_op.setdefault(mt["desc"], []).append(mt)
    filas = list(por_op.values())
    ordenado = []
    while filas:
        filas = [f for f in filas if f]
        for f in filas:
            if f:
                ordenado.append(f.pop(0))
    return ordenado


def testar_mutacao(rtl_texto, tb_path, work, max_mutantes=MAX_MUTANTES):
    """
    Avalia ate max_mutantes mutantes validos (que compilam), em ordem
    diversificada por operador. Para cada um: compila com o TB e roda.
    exit!=0 => testbench detectou a troca => mutante morto.
    Usa --binary (nao precisa de cobertura aqui) => mais rapido.
    """
    candidatos = ordenar_diverso(gerar_mutantes(rtl_texto))
    if not candidatos:
        return {
            "total": 0, "mortos": 0, "sobreviventes": 0, "score": None,
            "detalhe": [], "aviso": "nenhum operador mutavel encontrado no RTL",
        }

    mortos = 0
    sobreviventes = 0
    detalhe = []

    for cand in candidatos:
        if mortos + sobreviventes >= max_mutantes:
            break

        mdir = build_dir(work)
        mut_file = mdir / "mut.v"
        mut_file.write_text(cand["texto"])

        rc, out, err = run(
            [
                "verilator", "--binary", "--timing",
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

        # So roda mutacao se compilou e executou (senao nao faz sentido)
        if resultado["compilou"] and resultado["executou"]:
            resultado["mutacao"] = testar_mutacao(rtl_txt, tb_path, work)
        else:
            resultado["mutacao"] = None

        return jsonify(resultado)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    # host 0.0.0.0 para funcionar tambem via WSL
    app.run(host="127.0.0.1", port=5000, debug=True)
