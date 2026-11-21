"""Validação da Bancada RTL: compara a ferramenta com a execução manual no Verilator.

Para cada par em documentacao/validacao/pares/<caso>/ (dut.v + tb.v):
  1) BANCADA: chama as funções do app.py (compilar_e_cobrir e testar_mutacao), sem a rota
     /avaliar — nada vai para a planilha nem para avaliacoes/;
  2) MANUAL: compila direto com `verilator --binary --coverage` (sem o harness da bancada),
     conta a cobertura no coverage.dat com awk (coberto = contagem >= 1, só pontos do dut.v),
     e aplica à mão cada mutante que a bancada avaliou, simulando com o mesmo testbench
     (código de saída != 0 = morto).
Compara aprovação, cobertura por tipo e o destino de cada mutante, e grava a tabela em
documentacao/validacao/resultado.md. Termina com erro se alguma coisa não bater.

Uso (WSL, com o venv da bancada, que tem o flask):
  ~/veriweb/venv/bin/python documentacao/analise/validacao/validar_bancada.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

DOC = Path(__file__).resolve().parents[2]          # documentacao/
PARES = DOC / "validacao" / "pares"
SAIDA = DOC / "validacao" / "resultado.md"
sys.path.insert(0, str(DOC.parent / "api"))        # app.py da bancada
os.environ["GSHEET_WEBHOOK"] = ""
import app  # noqa: E402

CASOS = [
    ("somador32", "Somador de 32 bits (combinacional)"),
    ("detector11", "Detector da sequência 11 (FSM com case)"),
    ("detector101", "Detector da sequência 101 (FSM com case)"),
    ("temporizador_case", "Temporizador (FSM com case, 7 estados)"),
    ("fancytimer_if", "Fancytimer do HDLBits (FSM com if)"),
]
TIPOS = [("line", "v_line"), ("branch", "v_branch"), ("toggle", "v_toggle")]
FLAGS = ["-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-WIDTH", "-Wno-UNOPTFLAT", "--top-module", "tb"]


def sh(cmd, cwd, timeout=240):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode
    except subprocess.TimeoutExpired:
        return 124


def awk_conta(cov, filtro):
    """Mesma contagem dos documentos: pontos 'C ...' do dut.v com contagem >= 1."""
    prog = "/^C/ && /dut\\.v/ " + filtro + " {n++; if ($NF+0>=1) c++} END{printf \"%d %d\", c, n}"
    out = subprocess.run(["awk", prog, str(cov)], capture_output=True, text=True).stdout.split()
    return int(out[0]), int(out[1])


def manual(dut, tb, mutantes):
    d = Path(tempfile.mkdtemp(prefix="valid_manual_"))
    try:
        shutil.copy(dut, d / "dut.v")
        shutil.copy(tb, d / "tb.v")
        if sh(["verilator", "--binary", "--timing", "--coverage", *FLAGS, "-o", "sim",
               "dut.v", "tb.v"], d) != 0:
            return {"compilou": False}
        rc = sh(["./obj_dir/sim"], d, timeout=app.SIM_TIMEOUT)
        cov = d / "coverage.dat"
        r = {"compilou": True, "passou": rc == 0}
        for nome, tag in TIPOS:
            r[nome] = awk_conta(cov, f"&& /{tag}/")
        # FSM: pontos de linha do dut.v que são braço de case (o=case), como no grep dos
        # documentos (o separador do campo é o byte \x02 e o fim do valor é \x01)
        fsm = [l for l in cov.read_bytes().split(b"\n") if l.startswith(b"C ")
               and b"dut.v" in l and b"v_line" in l and b"\x02case\x01" in l]
        r["fsm"] = (sum(int(l.split()[-1]) >= 1 for l in fsm), len(fsm))
        # mutantes: a mesma troca que a bancada fez, aplicada na linha indicada
        linhas = (d / "dut.v").read_text().split("\n")
        r["mutantes"] = []
        for m in mutantes:
            i = m["linha"] - 1
            assert linhas[i].strip() == m["original"].strip(), (m, linhas[i])
            ind = linhas[i][:len(linhas[i]) - len(linhas[i].lstrip())]
            mut = linhas[:i] + [ind + m["mutado"].strip()] + linhas[i + 1:]
            (d / "mut.v").write_text("\n".join(mut))
            shutil.rmtree(d / "obj_dir", ignore_errors=True)
            if sh(["verilator", "--binary", "--timing", *FLAGS, "-o", "mut", "mut.v", "tb.v"], d) != 0:
                r["mutantes"].append("não compilou")
                continue
            rc = sh(["./obj_dir/mut"], d, timeout=app.SIM_TIMEOUT)
            r["mutantes"].append("morto" if rc != 0 else "sobreviveu")
        return r
    finally:
        shutil.rmtree(d, ignore_errors=True)


def bancada(dut, tb):
    work = Path(tempfile.mkdtemp(prefix="valid_bancada_"))
    try:
        shutil.copy(dut, work / "dut.v")
        shutil.copy(tb, work / "tb.v")
        res = app.compilar_e_cobrir(work / "dut.v", work / "tb.v", work)
        r = {"compilou": res["compilou"], "passou": res["passou"]}
        c = res["cobertura"] or {}
        pt = c.get("por_tipo", {})
        for nome, _ in TIPOS:
            t = pt.get(nome)
            r[nome] = (t["cobertos"], t["total"]) if t else (0, 0)
        f = c.get("fsm")
        r["fsm"] = (f["cobertos"], f["total"]) if f else (0, 0)
        m = app.testar_mutacao((work / "dut.v").read_text(), work / "tb.v", work) if res["passou"] else None
        r["detalhe"] = m["detalhe"] if m else []
        r["mutantes"] = [x["status"] for x in r["detalhe"]]
        return r
    finally:
        shutil.rmtree(work, ignore_errors=True)


def fmt(par):
    return "—" if par[1] == 0 else f"{par[0]}/{par[1]}"


def mortos(lst):
    return f"{sum(s == 'morto' for s in lst)}/{len(lst)}"


linhas_md, tudo_ok = [], True
for caso, titulo in CASOS:
    dut, tb = PARES / caso / "dut.v", PARES / caso / "tb.v"
    b = bancada(dut, tb)
    m = manual(dut, tb, b["detalhe"])
    campos = ["compilou", "passou", "line", "branch", "toggle", "fsm", "mutantes"]
    dif = [k for k in campos if b.get(k) != m.get(k)]
    ok = not dif
    tudo_ok &= ok
    print(f"{caso:18s} {'IGUAL' if ok else 'DIFERENTE ' + str(dif)}")
    for k in campos:
        print(f"   {k:9s} bancada={b.get(k)}  manual={m.get(k)}")
    linhas_md.append(f"| {titulo} | {'sim' if b['passou'] else 'não'} | {fmt(b['line'])} | "
                     f"{fmt(b['branch'])} | {fmt(b['toggle'])} | {fmt(b['fsm'])} | "
                     f"{mortos(b['mutantes'])} | {'✅ iguais' if ok else '❌ ' + ', '.join(dif)} |")

SAIDA.write_text(
    "# Validação da Bancada RTL: ferramenta × execução manual\n\n"
    f"Gerado por `documentacao/analise/validacao/validar_bancada.py` em {date.today():%d/%m/%Y}. "
    "Valores da bancada; a última coluna diz se a execução manual deu o mesmo resultado "
    "(aprovação, cada tipo de cobertura e o destino de cada mutante). "
    "— = métrica sem pontos no circuito.\n\n"
    "| Circuito | Passou | Linha | Desvio | Alternância | FSM | Mutantes mortos | Manual |\n"
    "|---|---|---|---|---|---|---|---|\n" + "\n".join(linhas_md) + "\n", encoding="utf-8")
print("gravado", SAIDA)
sys.exit(0 if tudo_ok else 1)
