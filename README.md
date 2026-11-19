# Bancada RTL — avaliador web de testbenches

Página web onde você cola um módulo RTL e um testbench, clica em **Avaliar**, e
recebe: se compilou, se executou, se passou, cobertura de código, mutation score
e o **ICV** (índice de complexidade do módulo). Funciona para qualquer módulo e
qualquer testbench, desde que o módulo do testbench se chame `tb`.

Foi feita para o TCC "Avaliação de estratégias de engenharia de prompt na geração de
testbenches para verificação de módulos RTL", que compara 6 estratégias de prompt em
10 módulos com 2 LLMs (240 testbenches). O material do TCC está em
[`documentacao/`](documentacao/README.md).

## Rodar

No **WSL/Linux**, nunca em `/mnt/c` (o Verilator não compila lá):

```bash
cd ~/veriweb        # ou onde você extraiu
chmod +x start.sh
./start.sh
```

Abra `http://127.0.0.1:5000` no navegador.

Primeira execução cria um venv e instala o Flask. Depois é só `./start.sh`.

## Pré-requisitos

```bash
sudo apt install verilator build-essential python3-venv
verilator --version    # precisa ser 5.x
```

## Como funciona por dentro

```
navegador (templates/index.html)
    │  POST /avaliar  { rtl, tb, modulo, estrategia }
    ▼
Flask (app.py)
    ├─ escreve rtl e tb em /tmp (dut.v, tb.v)
    ├─ compila com harness → simula → lê cobertura
    ├─ calcula o ICV a partir do texto do RTL
    ├─ gera mutantes do RTL → roda cada um → conta mortos
    ├─ registra a avaliação no histórico (CSV)
    └─ devolve JSON
```

O núcleo carrega as correções descobertas na prática:

- **build em `/tmp`** via `--Mdir` (o make do Verilator não aceita caminho com
  espaço)
- **harness C++** (`sim/main.cpp`) grava a cobertura via *flush callback* — assim o
  que foi exercitado é salvo **mesmo quando o testbench aborta com `$fatal`**
- **cobertura lida direto do `coverage.dat`** (formato texto): a bancada **não**
  chama `verilator_coverage`; conta os pontos do `dut.v` por tipo (coberto = contador ≥ 1)
- **compilação em paralelo** (`-j`) e **timeouts separados** — `TIMEOUT` alto para
  compilar módulos grandes sem ser morto, e `SIM_TIMEOUT` curto para a execução
  (um mutante que trava a simulação morre rápido)
- **módulo do testbench = `tb`** para o harness ser genérico

## O que sai

- **Estado**: compilou / executou / passou (três indicadores). `passou` reflete o
  código de saída da simulação (exit 0 = passou).
- **Cobertura**: % e pontos cobertos/total, quebrado por tipo — **linha**,
  **desvio (branch)** e **alternância (toggle)**. Só conta pontos do `dut.v`
  (ignora o testbench). A API também calcula uma cobertura de **máquina de estados
  (FSM)** aproximada (campo `fsm` do JSON e coluna no histórico), mas ela saiu do
  TCC e não aparece na tela (ver Limitações).
- **Mutation score**: % de mutantes mortos (defeitos detectados pelo testbench).
- **Mutantes avaliados**: um cartão por mutante mostrando o operador trocado, a
  linha, o **diff** (antes/depois) e o veredito — **detectado** (verde, o
  testbench falhou na versão trocada) ou **sobreviveu** (vermelho, passou batido).
- **ICV**: índice de complexidade do módulo (0 a 3) com a classificação
  (Fácil / Média / Alta / Muito Alta) e os 4 componentes discriminados.

## ICV — Índice de Complexidade para Verificação

Métrica calculada **só do texto do DUT** (não depende do testbench). Combina
quatro pontuações de 0 a 3, com pesos:

```
ICV = P_LOC·0,30 + P_FSM·0,30 + P_IO·0,20 + P_LOG·0,20      (0 a 3)
```

- **P_LOC** — linhas de código (sem comentários/brancos): `≤30→1 · ≤100→2 · >100→3`
- **P_FSM** — nº de estados da FSM, nomeados ou numéricos: `≤1→0 · ≤4→1 · ≤9→2 · >9→3`
- **P_IO** — portas input+output (portas, não bits): `≤4→1 · ≤10→2 · >10→3`
- **P_LOG** — natureza da lógica (soma, teto 3): aritmética `+1`, shift register/serial
  `+2`, pipeline `+2`

Classificação: `0,0–1,2 Fácil · 1,3–1,9 Média · 2,0–2,3 Alta · >2,3 Muito Alta`.
As faixas foram calibradas para a classe de módulos do estudo (HDLBits / cores
abertos pequenos); a extração é por heurística de texto, sem parser.

## Detalhes da mutação

- **Mutação de primeira ordem por regex.** 20 operadores (`+`↔`-`, `==`↔`!=`,
  `&`↔`|`, `<<`↔`>>`, troca de constantes, ramos de `?:`, `if(x)`↔`if(!x)`…), só
  aplicados **dentro da lógica** (corpo de `always`/`assign`).
- **Até 4 mutantes válidos por rodada** (`MAX_MUTANTES = 4`), com teto de 16
  compilações (`MAX_TENTATIVAS = 16`). Mutante que não compila é descartado sem
  contar.
- **Espalhamento**: os 4 mutantes são amostrados de **regiões diferentes** do
  arquivo (início/meio/fim), para não caírem todos no mesmo bloco.
- **Trava**: a mutação só roda se o testbench **compilou, executou e passou** no
  RTL original. Senão, todo mutante "morreria" de graça e o score seria falso.

## Histórico

Cada avaliação é registrada em `historico.csv` (data, módulo, estratégia,
compilou/executou/passou, cobertura por tipo, FSM, mutantes e mutation score).
Baixe em `GET /historico.csv`. Os campos `modulo` e `estrategia` vêm dos inputs
da tela (enviados no JSON do POST) — úteis para comparar estratégias de prompt em lote.

Além disso, cada avaliação é **salva inteira** em
`avaliacoes/<data>_<módulo>_<estratégia>/`: o RTL (`dut.v`), o testbench (`tb.v`) e
o resultado completo (`resultado.json`, com a lista dos mutantes e o retorno da
planilha). A tela mostra a pasta. Assim os testbenches gerados não se perdem.

## Envio automático para o Google Sheets (opcional)

Se a variável de ambiente **`GSHEET_WEBHOOK`** estiver definida, cada avaliação
também é enviada (POST JSON) para esse webhook — um *Google Apps Script* (`doPost`)
preso à planilha do experimento, que preenche a matriz (bloco por módulo, métricas
nas linhas, estratégias nas colunas).

- A URL fica em **`webhook.env`** (ao lado do `start.sh`), que **não vai para o git**.
  Crie com: `export GSHEET_WEBHOOK="https://script.google.com/macros/s/SEU_ID/exec"`.
  O `start.sh` faz `source webhook.env` se o arquivo existir.
- **Falha no envio nunca derruba a avaliação, mas aparece na tela.** Abaixo do botão
  Avaliar, uma caixa mostra o que a planilha respondeu: gravou (verde), recusou com o
  motivo (vermelho: módulo não encontrado, bloco travado, gravou só parte...), falha de
  rede/timeout (vermelho) ou servidor sem webhook (amarelo). O timeout é de 30 s.
- Linhas que não chegaram (falha de rede/timeout) ficam em **`envios_pendentes.jsonl`**,
  para reenviar. O `historico.csv` sempre grava tudo.
- O Apps Script roda **no Google**; a versão em uso está copiada em
  [`planilha/doPost.gs`](planilha/doPost.gs). Ele acha o bloco pelo nome em qualquer
  coluna (a 2ª rodada fica ao lado da 1ª, com nomes terminados em "2"), trava os blocos
  da coluna A (1ª rodada) e separa "Não compilou", "Timeout" e "Não passou". Depois de
  colar uma versão nova no editor do Apps Script, atualize a implantação existente
  (**Implantar → Gerenciar implantações → editar → Nova versão**), não crie outra: uma
  implantação nova muda a URL do `webhook.env`.

## Limitações honestas

**Mutação por regex, não por parser.** Dois efeitos:

1. Um módulo sem operadores mutáveis gera zero mutantes (a página avisa).
2. Mutantes inválidos são gerados, mas **não compilam e são descartados** — não
   afetam o score, só gastam tempo (daí o teto de tentativas).

Além disso, são só **4 mutantes** (uma amostra, mesmo espalhada) e existem
**mutantes equivalentes** — comportamento idêntico ao original (ex.: contador
módulo-16 onde `−8 ≡ +8`) que sobrevivem sem que nenhum testbench pudesse
matá-los. Para o TCC isso é suficiente para comparar estratégias de prompt entre
si (todas enfrentam o mesmo gerador). Mutação rigorosa e reproduzível (ex.:
baseada em Yosys/AST) seria o próximo passo — outro escopo.

**Cobertura de FSM aproximada (fora do TCC).** O Verilator não emite cobertura de
FSM; a bancada aproxima procurando um `case` cujo seletor é um registrador (padrão
de FSM) e medindo a cobertura dos braços desse case. A heurística confunde `case`
que não é FSM (Conwaylife) e não vê FSMs escritas com `if` (Fancytimer, wbuart32),
por isso a métrica saiu do TCC e da tela. O `P_FSM` do ICV usa outra detecção e
continua valendo.

**ICV é heurístico.** Sem parser, P_FSM e P_LOG são estimativas de texto — por
isso a tela mostra os 4 componentes brutos, para auditoria.

**Um módulo por vez.** A página avalia um par RTL+TB. Para rodar os 10 módulos
× 6 estratégias em lote, o mesmo `app.py` pode virar um script de linha de comando
— as funções `compilar_e_cobrir`, `testar_mutacao` e `calcular_icv` já são
independentes do Flask (é o que `analise/validacao/validar_bancada.py` faz).

## Estrutura

```
veriweb/
├── app.py                backend Flask (toda a lógica)
├── sim/main.cpp          harness C++ (loop de tempo + grava cobertura)
├── templates/index.html  a página
├── requirements.txt
├── start.sh              sobe o servidor
├── planilha/doPost.gs    cópia do Apps Script que grava na planilha do experimento
├── exemplos/             pares RTL + testbench para testar a bancada (ver o README da pasta)
├── analise/              scripts que geram os PDFs, a figura e o apêndice do TCC
│   ├── estatistica/      dados da planilha (pdf_comum.py, coberturas.json) e geradores
│   ├── documentos/       gerador dos PDFs da pasta "Documentação" do Google Drive
│   ├── figuras/          gerador da figura do processo do trabalho
│   └── validacao/        validar_bancada.py: bancada × Verilator à mão
└── documentacao/         apêndices LaTeX, figura, PDFs e validação (ver o README da pasta)
```

Ficam fora do git (só no WSL): `webhook.env`, `historico.csv`, `avaliacoes/` e
`envios_pendentes.jsonl`.

## Testbench: formato esperado

O módulo do testbench precisa se chamar `tb` e encerrar com `$finish`. Para o
resultado "passou" refletir corretude, use `$fatal(1, ...)` quando uma checagem
falhar — é isso que faz o exit code virar ≠ 0 (e é o que a mutação usa para saber
se o testbench detectou o defeito):

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
