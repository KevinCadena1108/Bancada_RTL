# Bancada RTL — avaliador web de testbenches

A Bancada RTL é uma página web que avalia testbenches em Verilog. Você cola um módulo RTL e um
testbench e clica em **Avaliar**. A bancada compila e simula os dois no Verilator e mostra se o
testbench passou, a cobertura de código, o teste de mutação e o **ICV**, um índice de complexidade
do módulo. Funciona com qualquer módulo e qualquer testbench, desde que o módulo do testbench se
chame `tb`.

A bancada foi feita para o TCC "Avaliação de estratégias de engenharia de prompt na geração de
testbenches para verificação de módulos RTL". O material do TCC está em
[`documentacao/`](documentacao/README.md).

## O experimento do TCC

Dois LLMs geraram testbenches para 10 módulos com 6 estratégias de prompt, em 2 rodadas. São 240
testbenches, e todos foram avaliados nesta bancada.

| | |
|---|---|
| **Módulos** | Lemmings1, Conwaylife, Count clock, Exams/2012 q2fsm, Cs450/gshare, Fancytimer e Fsm serialdp, do HDLBits, e CORDIC, SPI Master e wbuart32, do OpenCores. São 10 módulos sequenciais em Verilog, 6 deles com máquina de estados. |
| **Estratégias** | Zero-shot, Few-shot, Especialista Zero-shot, Especialista Few-shot, Planning Zero-shot e Planning Few-shot |
| **LLMs** | GPT-5.6 Luna e Gemini 3.5 Flash-Lite |
| **Total** | 10 módulos × 6 estratégias × 2 LLMs × 2 rodadas = 240 testbenches |

As gerações foram feitas na interface web de cada LLM, que não deixa ajustar a temperatura. Por
isso cada combinação foi gerada duas vezes. Cada geração foi feita num chat novo, em guia anônima,
e valeu o primeiro testbench gerado. Todos os prompts pediram os mesmos requisitos mínimos (ver
[Formato do testbench](#formato-do-testbench)). Os prompts completos estão em
[`documentacao/apendice_prompts.tex`](documentacao/apendice_prompts.tex).

A análise é descritiva. Ela usa quatro medidas.

- **Taxa de aprovação.** Quantos testbenches passaram no módulo correto.
- **Score efetivo.** Quantas falhas foram detectadas, de todas as possíveis. Cada testbench enfrenta
  4 mutantes, então são 960 falhas. Um testbench que não compilou, não passou ou travou detecta 0.
- **Posto médio.** Em cada módulo e em cada LLM, as 6 estratégias são ordenadas pelas falhas
  detectadas, com a média das duas rodadas. A melhor recebe posto 6 e a pior, posto 1. Estratégias
  empatadas dividem o posto. O posto médio é a média desses postos. Quanto maior, melhor.
- **Cobertura dos aprovados.** Linha, desvio e alternância, só dos testbenches que passaram.

Principais resultados:

- 175 dos 240 testbenches passaram (72,9%). O Gemini teve mais aprovados (95 contra 80), mas o GPT
  teve score efetivo maior (57,9% contra 50,2%).
- O score efetivo geral foi 54,1% (519 de 960 falhas). O maior foi o da Planning Few-shot (66,9%) e
  o menor, o da Zero-shot (38,1%).
- As estratégias com exemplos (Few-shot) detectaram 61,0% das falhas. As sem exemplos detectaram
  47,1%.
- No posto médio com os dois LLMs juntos, a ordem foi Planning Few-shot (4,30), Especialista
  Few-shot (3,75), Few-shot (3,675), Planning Zero-shot (3,625), Especialista Zero-shot (3,30) e
  Zero-shot (2,35).
- Entre os aprovados, a cobertura média variou menos de 5 pontos entre as estratégias, e o score
  dos aprovados variou de 69,3% a 78,7%. A detecção de falhas variou mais que a cobertura.
- Dos 122 testbenches com 100% de cobertura de linha, 63 deixaram alguma falha sem detectar
  (51,6%). A cobertura sozinha não basta para avaliar um testbench.

O cálculo de cada número está em
[`documentacao/resultados_explicados.pdf`](documentacao/resultados_explicados.pdf).

## Rodar

Use o **WSL/Linux**, numa pasta do Linux (por exemplo, `~/veriweb`). Nunca rode em `/mnt/c`, porque
o Verilator não compila lá.

Pré-requisitos:

```bash
sudo apt install verilator build-essential python3-venv
verilator --version    # precisa ser 5.x
```

Para subir a bancada:

```bash
cd ~/veriweb
chmod +x start.sh
./start.sh
```

Depois abra `http://127.0.0.1:5000` no navegador. A primeira execução cria um venv e instala o
Flask. Nas próximas, basta rodar `./start.sh`.

## Formato do testbench

O módulo do testbench precisa se chamar `tb` e terminar com `$finish`. Quando uma checagem falhar,
use `$fatal(1, ...)`. Isso faz o código de saída ficar diferente de 0. É assim que a bancada sabe
que o testbench reprovou, e é assim que o teste de mutação sabe que um mutante foi detectado.

No TCC, todos os prompts pediram os mesmos requisitos, sem dizer como testar o módulo.

- O módulo do testbench deve se chamar `tb`.
- Ele instancia o módulo sob teste e compara as saídas com os valores esperados usando `!==`.
- Em caso de erro, usa `$fatal(1, ...)`.
- Cada `$display` tem a string numa linha só, porque o Verilog não junta strings quebradas.
- Termina com `$finish`.
- Compila no Verilator, sem arquivos externos.

```verilog
module tb;
    // ... sinais e DUT ...
    initial begin
        // estimulos e checagens
        if (erro) $fatal(1, "falhou");
        $finish;
    end
endmodule
```

## Como funciona por dentro

```
navegador (templates/index.html)
    │  POST /avaliar  { rtl, tb, modulo, estrategia }
    ▼
Flask (app.py)
    ├─ grava dut.v e tb.v numa pasta temporária em /tmp
    ├─ compila com o harness → simula → lê a cobertura
    ├─ calcula o ICV a partir do texto do RTL
    ├─ gera mutantes do RTL → roda cada um → conta os detectados
    ├─ registra no historico.csv e envia para a planilha (opcional)
    ├─ salva RTL, testbench e resultado em avaliacoes/
    └─ devolve o JSON para a tela
```

O núcleo guarda as correções descobertas na prática.

- **Build em `/tmp`** com `--Mdir`. O make gerado pelo Verilator não aceita caminho com espaço.
- **Harness C++** (`sim/main.cpp`). Ele grava a cobertura com um *flush callback*. Assim o que foi
  exercitado é salvo **mesmo quando o testbench para no `$fatal`**. Com `--binary` sozinho, o
  Verilator 5.032 não grava o `coverage.dat` nesse caso.
- **Cobertura lida direto do `coverage.dat`**, que é texto. A bancada não chama o
  `verilator_coverage`. Ela conta os pontos do `dut.v` por tipo, e um ponto está coberto quando o
  contador é pelo menos 1. Isso equivale ao `--annotate-min 1` (o padrão 10 daria 0%).
- **Compilação em paralelo** (`-j 8`) e **dois timeouts**. O `TIMEOUT` (240 s) é alto, para módulos
  grandes compilarem sem ser interrompidos. O `SIM_TIMEOUT` (30 s) é curto, para um mutante que
  trava a simulação parar logo.
- **Módulo do testbench = `tb`**, para o harness servir para qualquer par.

## O que a tela mostra

- **Estado.** Compilou, executou e passou. O "passou" vem do código de saída da simulação (0 =
  passou).
- **Cobertura.** Percentual e pontos cobertos/total, por tipo: **linha**, **desvio (branch)** e
  **alternância (toggle)**. Só conta pontos do `dut.v`, não do testbench.
- **Mutation score.** Percentual de mutantes detectados.
- **Mutantes avaliados.** Um cartão por mutante, com o operador trocado, a linha, o **diff** (antes
  e depois) e o veredito. **Detectado** (verde) quer dizer que o testbench falhou na versão trocada.
  **Sobreviveu** (vermelho) quer dizer que o defeito passou batido.
- **ICV.** O índice (0 a 3), a classe (Fácil, Média, Alta ou Muito Alta) e os 4 componentes.
- **Planilha e pasta.** O que a planilha respondeu e a pasta onde a avaliação foi salva.

A API também calcula uma cobertura de **máquina de estados (FSM)** aproximada. Ela vai no campo
`fsm` do JSON e numa coluna do histórico. Essa métrica saiu do TCC e não aparece na tela (ver
Limitações).

## ICV — Índice de Complexidade para Verificação

O ICV é calculado **só do texto do módulo**. Ele não depende do testbench. Junta quatro notas de 0
a 3, com pesos.

```
ICV = P_LOC·0,30 + P_FSM·0,30 + P_IO·0,20 + P_LOG·0,20      (0 a 3)
```

| Nota | O que mede | Faixas |
|---|---|---|
| **P_LOC** | linhas de código, sem comentários e linhas em branco | ≤30 → 1 · ≤100 → 2 · >100 → 3 |
| **P_FSM** | número de estados da FSM, nomeados ou numéricos | ≤1 → 0 · ≤4 → 1 · ≤9 → 2 · >9 → 3 |
| **P_IO** | portas de entrada e saída (portas, não bits) | ≤4 → 1 · ≤10 → 2 · >10 → 3 |
| **P_LOG** | tipo de lógica, somando até no máximo 3 | aritmética +1 · registrador de deslocamento +2 · `generate` com `for` (estruturas replicadas) +2 |

Classes: Fácil até 1,2 · Média até 1,9 · Alta até 2,3 · Muito Alta acima de 2,3. As faixas foram
calibradas para os módulos do estudo (HDLBits e cores abertos pequenos). A extração é feita por
heurística de texto, sem parser. Os pesos e os limites foram definidos pelo autor, sem um estudo de
validação. Por isso, no TCC, o ICV serve só para mostrar que os 10 módulos são variados. Eles
ficaram com ICV entre 1,0 e 2,5, sendo 3 fáceis, 4 médios, 1 alto e 2 muito altos.

## Teste de mutação

- **Mutação de primeira ordem por regex.** São 20 operadores, como `+`↔`-`, `==`↔`!=`, `&`↔`|`,
  `<<`↔`>>`, troca de constantes, troca dos ramos de `?:` e `if(x)`↔`if(!x)`. Eles só são aplicados
  **dentro da lógica**, no corpo de `always` e `assign`.
- **Até 4 mutantes válidos por avaliação** (`MAX_MUTANTES = 4`), com teto de 16 compilações
  (`MAX_TENTATIVAS = 16`). Um mutante que não compila é descartado e não conta.
- **Espalhamento.** Os pontos mutáveis são divididos em 4 faixas do arquivo. A bancada pega um de
  cada faixa por vez e varia o operador dentro da faixa. Assim os 4 mutantes não caem no mesmo
  bloco.
- **Escolha determinística.** Os mutantes dependem só do módulo. Então todos os testbenches de um
  mesmo módulo enfrentam os mesmos 4 mutantes, em qualquer estratégia, LLM ou rodada.
- **Mutante que trava** a simulação estoura o `SIM_TIMEOUT` e conta como detectado.
- **Trava de segurança.** A mutação só roda se o testbench **compilou, executou e passou** no RTL
  original. Senão, todo mutante seria "detectado" de graça e o score seria falso.

## Validação

A bancada foi conferida contra o Verilator usado à mão, por uma rota independente, em 5 casos. A
aprovação, a cobertura de cada tipo e o destino de cada mutante deram iguais nos 5. Os pares e a
tabela de resultado estão em [`documentacao/validacao/`](documentacao/validacao/README.md), com os
links para as provas em PDF. Para refazer, rode no WSL, na raiz do repositório:

```bash
~/veriweb/venv/bin/python analise/validacao/validar_bancada.py
```

## Histórico e avaliações salvas

Cada avaliação vira uma linha em `historico.csv`. A linha tem data, módulo, estratégia,
compilou/executou/passou, cobertura por tipo, FSM, mutantes e mutation score. Para baixar, use
`GET /historico.csv`. O módulo e a estratégia vêm dos campos da tela, o que ajuda a comparar
estratégias em lote.

Cada avaliação também é **salva inteira** em `avaliacoes/<data>_<módulo>_<estratégia>/`. A pasta
tem o RTL (`dut.v`), o testbench (`tb.v`) e o resultado completo (`resultado.json`, com os mutantes
e a resposta da planilha). Assim nenhum testbench gerado se perde.

## Envio automático para o Google Sheets (opcional)

Se a variável **`GSHEET_WEBHOOK`** estiver definida, cada avaliação também é enviada (POST JSON)
para esse endereço. Ele é um *Google Apps Script* (`doPost`) ligado à planilha do experimento, que
preenche a matriz com um bloco por módulo, as métricas nas linhas e as estratégias nas colunas.

- A URL fica em **`webhook.env`**, ao lado do `start.sh`. Esse arquivo **não vai para o git**. Ele
  tem uma linha só, `export GSHEET_WEBHOOK="https://script.google.com/macros/s/SEU_ID/exec"`. O
  `start.sh` carrega o arquivo se ele existir.
- **Uma falha no envio nunca derruba a avaliação, mas aparece na tela.** Abaixo do botão Avaliar,
  uma caixa mostra a resposta da planilha. Verde quer dizer que gravou. Vermelho quer dizer que
  recusou (com o motivo) ou que houve falha de rede ou timeout. Amarelo quer dizer que o servidor
  está sem webhook. O timeout do envio é de 30 s.
- As linhas que não chegaram por falha de rede ou timeout ficam em **`envios_pendentes.jsonl`**,
  para reenviar. O `historico.csv` sempre grava tudo.
- O Apps Script roda **no Google**. A versão em uso está copiada em
  [`planilha/doPost.gs`](planilha/doPost.gs). Ele acha o bloco pelo nome em qualquer coluna. A 2ª
  rodada fica ao lado da 1ª, com nomes terminados em "2". Os blocos da coluna A (1ª rodada) ficam
  travados. Ele separa "Não compilou", "Timeout" e "Não passou".
- Depois de colar uma versão nova no editor do Apps Script, atualize a implantação existente
  (**Implantar → Gerenciar implantações → editar → Nova versão**). Não crie outra implantação,
  porque isso muda a URL do `webhook.env`.

## Limitações

**Mutação por regex, não por parser.** Um módulo sem operadores mutáveis gera zero mutantes, e a
página avisa. Mutantes inválidos são gerados, mas não compilam e são descartados. Eles não afetam o
score, só gastam tempo (por isso existe o teto de tentativas).

**Amostra pequena e mutantes equivalentes.** São só 4 mutantes por avaliação. Alguns mutantes são
**equivalentes**, ou seja, se comportam igual ao original e nenhum testbench consegue detectá-los
(por exemplo, um contador módulo 16 em que −8 e +8 dão o mesmo resultado). Para o TCC isso basta,
porque todas as estratégias enfrentam o mesmo gerador. Uma mutação mais rigorosa, baseada em
Yosys ou numa árvore sintática, seria o próximo passo.

**Cobertura de FSM aproximada (fora do TCC).** O Verilator não tem cobertura de FSM. A bancada
procura um `case` cujo seletor é um registrador, que é o padrão de uma FSM, e mede quantos braços
desse `case` foram executados. A heurística confunde `case` que não é FSM (Conwaylife) e não vê
FSMs escritas com `if` (Fancytimer, wbuart32). Por isso a métrica saiu do TCC e da tela. O `P_FSM`
do ICV usa outra detecção e continua valendo.

**ICV heurístico.** Sem parser, o P_FSM e o P_LOG são estimativas feitas a partir do texto. Por
isso a tela mostra os 4 componentes, para conferência.

**Um par por vez.** A página avalia um par RTL + testbench por vez. As funções
`compilar_e_cobrir`, `testar_mutacao` e `calcular_icv` não dependem do Flask e podem ser usadas num
script de linha de comando, como faz o `analise/validacao/validar_bancada.py`.

## Estrutura

```
veriweb/
├── app.py                backend Flask (toda a lógica)
├── sim/main.cpp          harness C++ (loop de tempo e gravação da cobertura)
├── templates/index.html  a página
├── requirements.txt
├── start.sh              sobe o servidor
├── planilha/doPost.gs    cópia do Apps Script que grava na planilha do experimento
├── analise/              scripts que geram os PDFs, a figura e o apêndice do TCC
│   ├── estatistica/      dados da planilha (pdf_comum.py, coberturas.json) e geradores
│   ├── documentos/       gerador dos PDFs da pasta "Documentação" do Google Drive
│   ├── figuras/          gerador da figura do processo do trabalho
│   └── validacao/        validar_bancada.py, bancada × Verilator à mão
└── documentacao/         apêndices LaTeX, figura, PDFs e validação (ver o README da pasta)
```

Ficam fora do git, só no WSL, os arquivos `webhook.env`, `historico.csv` e
`envios_pendentes.jsonl` e a pasta `avaliacoes/`.
