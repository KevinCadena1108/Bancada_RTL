# Exemplos de pares RTL + testbench

Pares usados para testar a Bancada RTL durante o desenvolvimento. Para avaliar, cole o RTL e um
dos testbenches na página da bancada (o módulo do testbench sempre se chama `tb`).

| Pasta | RTL | Testbenches | Observação |
|---|---|---|---|
| `aes/` | `aes_dut.v` (`aes_core`, AES do OpenCores) | `aes_tb.v`, `aes_tb2.v`, `aes_v1.v`, `aes_v2.v` | módulo grande, bom para medir o tempo de compilação |
| `conwaylife/` | `gol.v` (Conwaylife do HDLBits, ajustado para o Verilator) | `tb_gol.v`, `tb_gol_fix.v` | o `_fix` corrige o valor esperado do *blinker* |
| `fancytimer/` | `fancy.v` (Exams/review2015_fancytimer do HDLBits) | `tb_fancy.v` | FSM escrita com `if` |
| `spi/` | `spi.v` (`spi_master` do OpenCores) | `tb_spi.v` | na planilha do experimento aparece com o nome antigo "I2C Slave" |

Estes testbenches **não** são os do experimento do TCC. Os testbenches gerados pelos LLMs ficam
fora do git, em `~/veriweb/avaliacoes/` no WSL (a partir da 2ª rodada).

Os exemplos colocados nos prompts *Few-shot* também não estão aqui. São um comparador de 4 bits e
um registrador de deslocamento de 4 bits, elaborados para o trabalho, e estão no apêndice dos
prompts (`documentacao/apendice_prompts.tex`).
