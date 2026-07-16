# Bancada RTL — avaliador web de testbenches

Página web onde você cola um módulo RTL e um testbench, clica em **Avaliar**, e
recebe: se compilou, se executou, cobertura e mutation score. Funciona para
qualquer módulo e qualquer testbench, desde que o módulo do testbench se chame
`tb`.

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
    │  POST /avaliar  { rtl, tb }
    ▼
Flask (app.py)
    ├─ escreve rtl e tb em /tmp
    ├─ compila com harness → simula → lê cobertura
    ├─ gera mutantes do RTL → roda cada um → conta mortos
    └─ devolve JSON
```

O núcleo é o mesmo fluxo de linha de comando que você já validou, com as mesmas
correções embutidas:

- **build em `/tmp`** via `--Mdir` (o make do Verilator não aceita caminho com
  espaço)
- **harness C++** (`sim/main.cpp`) para gravar a cobertura — o `--binary` sozinho
  não grava
- **`--annotate-min 1`** na leitura de cobertura (o default 10 daria 0%)
- **módulo do testbench = `tb`** para o harness ser genérico

## O que sai

- **Estado**: compilou / executou / passou (três indicadores)
- **Cobertura**: % e pontos cobertos/total, quebrado por tipo (line, toggle, …)
- **Mutation score**: % de mutantes mortos
- **Mapa de mutantes**: cada célula é um mutante — acesa (verde) = morto,
  apagada (vermelho) = sobreviveu. Passe o mouse para ver qual operador.

## Limitações honestas

**Mutação por regex, não por parser.** Os mutantes são gerados trocando
operadores no texto (`+`→`-`, `==`→`!=`, etc.). Dois efeitos:

1. Um módulo sem operadores mutáveis gera zero mutantes (a página avisa).
2. O regex não distingue `<=` de comparação de `<=` de atribuição
   não-bloqueante. Mutantes inválidos são gerados, mas **não compilam e são
   descartados** — não afetam o score, só gastam tempo.

Para o TCC, isso é suficiente para comparar estratégias de prompt entre si (todas
enfrentam o mesmo gerador). Se precisar de mutação rigorosa e reproduzível,
ferramentas dedicadas (ex.: baseadas em Yosys/AST) seriam o próximo passo — mas
aí é outro escopo.

**Um módulo por vez.** A página avalia um par RTL+TB. Para rodar os 6–10 módulos
× 4 estratégias em lote, o mesmo `app.py` pode virar um script de linha de comando
— as funções `compilar_e_cobrir` e `testar_mutacao` já são independentes do Flask.

## Estrutura

```
veriweb/
├── app.py                backend Flask (toda a lógica)
├── sim/main.cpp          harness C++ (loop de tempo + grava cobertura)
├── templates/index.html  a página
├── requirements.txt
└── start.sh              sobe o servidor
```

## Testbench: formato esperado

O módulo do testbench precisa se chamar `tb` e encerrar com `$finish`. Para o
resultado "passou" refletir corretude, use `$fatal(1, ...)` quando uma checagem
falhar — é isso que faz o exit code virar ≠ 0:

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
