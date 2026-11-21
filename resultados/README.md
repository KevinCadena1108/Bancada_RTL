# Resultados do experimento

`resultados_testbenches.csv` tem uma linha para cada um dos 240 *testbenches* avaliados
(10 módulos × 6 estratégias × 2 LLMs × 2 rodadas). Separador ponto e vírgula e vírgula decimal,
para abrir direto no Excel em português.

| Coluna | Conteúdo |
|---|---|
| `llm` | GPT-5.6 Luna ou Gemini 3.5 Flash-Lite |
| `rodada` | 1 ou 2 |
| `modulo` | nome do módulo no TCC (arquivos em `modulos/`) |
| `estrategia` | uma das 6 estratégias (prompts em `prompts/`) |
| `resultado` | `aprovado` no circuito original, `reprovado` (não compilou ou falhou) ou `tempo esgotado` |
| `mutantes_detectados` | de 0 a 4; reprovados e tempo esgotado contam 0 (a mutação só roda para os aprovados) |
| `cobertura_linha`, `cobertura_desvio`, `cobertura_alternancia` | cobertura em % registrada pela Bancada RTL |

A cobertura dos reprovados também está registrada, mas não entra nas médias do TCC: a simulação
para no primeiro erro, então ela não mostra quanto o *testbench* exercitaria o circuito.

Com esse arquivo se refazem os números do TCC, por exemplo 175 aprovados de 240 (72,9%) e 519
mutantes detectados de 960 possíveis (*score* efetivo de 54,1%).

Os dados vêm da planilha do experimento (Google Sheets), copiada em
`analise/estatistica/pdf_comum.py` e `analise/estatistica/coberturas.json` e conferida célula a
célula. O CSV é gerado por `analise/estatistica/gerar_csv_resultados.py`. Os *testbenches* em si
não estão no repositório: os da 1ª rodada não foram guardados.
