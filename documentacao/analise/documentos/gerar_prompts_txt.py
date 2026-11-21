"""Monta os 6 prompts do experimento em texto puro, a partir de documentacao/apendices/apendice_prompts.tex.

O apêndice traz cada trecho uma única vez (solicitação, papel de especialista, exemplos,
planejamento, módulo e requisitos). Este script junta os trechos na ordem descrita em
"Composição das estratégias" e grava documentacao/prompts/<estrategia>.txt. [MÓDULO] é o lugar onde o código
RTL completo do módulo foi colado em cada geração.

Uso: python3 documentacao/analise/documentos/gerar_prompts_txt.py
"""
import os
import re

DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
tex = open(os.path.join(DOC, "apendices", "apendice_prompts.tex"), encoding="utf-8").read()
blocos = [b.strip("\n") for b in re.findall(r"\\begin\{verbatim\}\n(.*?)\\end\{verbatim\}", tex, re.S)]
assert len(blocos) == 10, len(blocos)
ZS, ESP_ZS, FS_PEDIDO, ESP, INTRO_EX, EX1, EX2, PLAN, MODULO, REQ = blocos
assert ZS.startswith("Crie um testbench") and ESP_ZS.startswith("Aja como")
assert FS_PEDIDO.startswith("Agora crie") and ESP == "Aja como um engenheiro de verificação de hardware."
assert EX1.startswith("module comparador4") and EX2.startswith("module shift_reg4")
assert PLAN.startswith("Antes de gerar") and "[MÓDULO]" in MODULO and REQ.startswith("Requisitos")

EXEMPLOS = "\n\n".join([INTRO_EX, "Exemplo 1", EX1, "Exemplo 2", EX2])
PROMPTS = {
    "1_zero_shot": [ZS, MODULO, REQ],
    "2_few_shot": [EXEMPLOS, FS_PEDIDO, MODULO, REQ],
    "3_especialista_zero_shot": [ESP_ZS, MODULO, REQ],
    "4_especialista_few_shot": [ESP, EXEMPLOS, FS_PEDIDO, MODULO, REQ],
    "5_planning_zero_shot": [PLAN, MODULO, REQ],
    "6_planning_few_shot": [EXEMPLOS, PLAN, MODULO, REQ],
}
saida = os.path.join(DOC, "prompts")
os.makedirs(saida, exist_ok=True)
for nome, partes in PROMPTS.items():
    with open(os.path.join(saida, nome + ".txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n\n".join(partes) + "\n")
    print("ok", nome)
