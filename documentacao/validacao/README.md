# Validação da Bancada RTL

Prova de que a bancada (API) dá o resultado certo: os mesmos pares de módulo + testbench foram
avaliados **pela ferramenta** e **à mão no Verilator 5.032**, por uma rota independente, e os
resultados foram idênticos em todos os casos. É a base da subseção "Validação da Bancada RTL" da
Metodologia do TCC.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `pares/<caso>/dut.v` e `tb.v` | os 5 pares usados (módulo e testbench) |
| `resultado.md` | tabela gerada pelo script de comparação (bancada × manual) |
| `comparacao_api_manual.docx` | somador de 32 bits, temporizador (FSM com `case`) e Fancytimer (FSM com `if`): comandos manuais, saída do terminal e capturas de tela da API |
| [`../drive/prova_cobertura.pdf`](../drive/prova_cobertura.pdf) | detector de "11": rota manual passo a passo (comandos, `coverage.dat` cru e comentado) |
| [`../drive/prova_fsm_completo.pdf`](../drive/prova_fsm_completo.pdf) | detector de "101": resultado da API ligado ponto a ponto ao `coverage.dat` |

Os documentos foram feitos pelo autor em 2026-11-06. Os dois PDFs foram refeitos em 2026-11-18 por
`documentacao/analise/documentos/gerar_pdfs_drive.py` e ficam só em `documentacao/drive/` (antes havia uma cópia
idêntica aqui): o código agora mostra `<=` e `&&` (antes saía `&lt;=` e `&amp;&amp;`), a linha 12
do detector de "11" é o bloco `always` (não o `assign`) e a cobertura de FSM saiu. Os números
foram conferidos de novo no Verilator 5.032.

**Cobertura de FSM:** saiu do TCC em 2026-11-13 (a aproximação da bancada confunde o `case` do
Conwaylife com uma FSM e não vê FSMs escritas com `if`). A validação foi feita antes disso, por
isso o `resultado.md` ainda tem a coluna FSM. No TCC, a comparação vale para aprovação, linha,
desvio, alternância e mutantes.

**No TCC (Tabela 2):** a coluna de cobertura é a soma dos pontos de linha, desvio e alternância de
cada caso. Por exemplo, 16/19 no detector de "11" é 4/5 + 6/8 + 6/6. Os mutantes são os mesmos
de `resultado.md`, e a coluna FSM não aparece.

## Os 5 casos

| Caso (`pares/`) | Circuito | Por que está aqui |
|---|---|---|
| `somador32` | somador combinacional de 32 bits | só tem pontos de alternância; 1 mutante válido |
| `detector11` | FSM com `case`, 3 estados + `default` | cobertura parcial explicável (faltam 2 desvios e o `default`) |
| `detector101` | FSM com `case`, 4 estados + `default` | resultado da API rastreado até cada ponto do `coverage.dat` |
| `temporizador_case` | FSM com `case`, 7 estados | circuito maior, 4 mutantes mortos |
| `fancytimer_if` | Fancytimer do HDLBits, FSM com `if` | **um mutante sobrevive** e a FSM **não é reconhecida** (sem `case`) |

## Como a comparação é feita

- **Bancada:** as funções do `api/app.py` (`compilar_e_cobrir` e `testar_mutacao`), as mesmas da rota
  `/avaliar`, mas sem ela — nada vai para a planilha nem para `avaliacoes/`.
- **Manual (independente da ferramenta):** `verilator --binary --timing --coverage` (sem o harness
  `api/sim/main.cpp` da bancada), simulação, e contagem no `coverage.dat` com `awk`: ponto do `dut.v`
  com contagem ≥ 1 = coberto. FSM = pontos `v_line` com `o=case` (braços do `case`, inclusive o
  `default`). Cada mutante que a bancada avaliou é aplicado à mão na mesma linha, compilado com
  `--binary` e simulado com o mesmo testbench: código de saída ≠ 0 = morto.
- Compara: aprovação, linha, desvio, alternância, FSM e o destino de cada mutante.

## Resultado

Os 5 casos deram **iguais** em tudo (ver `resultado.md`). Destaques:
- o mutante #1 do Fancytimer (`|` → `&`, linha 20) **sobreviveu** nas duas rotas (código de saída
  0): a bancada marca sobrevivente corretamente;
- a cobertura de FSM conta também o braço `default` (por isso 3/4 no detector de "11", que visita
  os 3 estados);
- FSM escrita com `if` não recebe cobertura de FSM (Fancytimer), um dos motivos para essa métrica
  ter saído do TCC.

## Como reproduzir

No Linux ou no WSL, na raiz do repositório, com o venv que o `api/start.sh` cria (tem o `flask`):

```
api/venv/bin/python documentacao/analise/validacao/validar_bancada.py
```

Imprime bancada × manual de cada caso, regrava `resultado.md` e sai com erro se algo não bater.
Para refazer um caso à mão, siga os comandos dos documentos acima.

Em 19/11/2026 o script foi rodado de novo numa cópia limpa do repositório. Os 5 casos deram iguais,
e o `resultado.md` só mudou na data.
