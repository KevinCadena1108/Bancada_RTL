# Módulos RTL do experimento

Os 10 módulos avaliados no TCC, exatamente como foram colados nos prompts e na Bancada RTL. Todos
são sequenciais. Alguns foram ajustados para compilar no Verilator (o ajuste está comentado no
início do arquivo).

| Arquivo | Módulo no TCC | Origem | Função | ICV | Classe |
|---|---|---|---|---|---|
| `lemmings1.v` | Lemmings1 | HDLBits | controle de direção de personagem | 1,0 | Fácil |
| `conwaylife.v` | Conwaylife | HDLBits | Jogo da Vida em grade 16×16 | 1,0 | Fácil |
| `count_clock.v` | Count clock | HDLBits | relógio de 12 horas | 1,0 | Fácil |
| `exams_2012_q2fsm.v` | Exams/2012 q2fsm | HDLBits | máquina de estados | 1,4 | Média |
| `cs450_gshare.v` | Cs450/gshare | HDLBits | preditor de desvios | 1,8 | Média |
| `fancytimer.v` | Fancytimer | HDLBits | temporizador acionado por sequência | 1,9 | Média |
| `cordic.v` | CORDIC | OpenCores | cálculo trigonométrico em *pipeline* | 1,9 | Média |
| `fsm_serialdp.v` | Fsm serialdp | HDLBits | receptor serial com paridade | 2,2 | Alta |
| `spi_master.v` | SPI Master | OpenCores | mestre de comunicação SPI | 2,4 | Muito Alta |
| `wbuart32_txuartlite.v` | wbuart32 | OpenCores | transmissor UART (`txuartlite`) | 2,5 | Muito Alta |

Na planilha do experimento, o SPI Master aparece com o nome antigo "I2C Slave" e o Count clock
como "Cout Clock".

**Conferência (21/11/2026):** os arquivos vieram da pasta "Modulos" do Google Drive do autor. O ICV
que a Bancada RTL calcula para cada um (linhas, estados, portas e ICV) é igual ao da Tabela do
ICV no Apêndice B do TCC (`documentacao/apendice_resultados.tex`), e todos passam no
`verilator --lint-only`. O CORDIC tem um mutante equivalente (dentro de um `` `ifdef ``
desligado), que nenhum *testbench* consegue detectar.
