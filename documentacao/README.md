# Documentação do TCC

Material do TCC "Avaliação de estratégias de engenharia de prompt na geração de testbenches para
verificação de módulos RTL". O texto do TCC fica no Overleaf. Aqui ficam os materiais do
experimento (módulos, prompts e resultados), os apêndices em LaTeX, as figuras, os PDFs que
explicam os resultados, a validação da Bancada RTL e os scripts que geram tudo isso. O código da
bancada está em [`../api/`](../api/).

Os números vêm da planilha do experimento (10 módulos, 6 estratégias, 2 LLMs, 2 rodadas = 240
testbenches), copiada em `analise/estatistica/pdf_comum.py` (mutantes) e
`analise/estatistica/coberturas.json` (coberturas).

## O que tem aqui

| Pasta ou arquivo | O que é | Gerado por |
|---|---|---|
| [`modulos/`](modulos/README.md) | os 10 módulos RTL do experimento, como foram usados | baixados do Drive do autor |
| [`prompts/`](prompts/README.md) | os 6 prompts, um por estratégia | `analise/documentos/gerar_prompts_txt.py` |
| [`resultados/`](resultados/README.md) | `resultados_testbenches.csv` (os 240 testbenches) | `analise/estatistica/gerar_csv_resultados.py` |
| `resultados/resultados_explicados.pdf` | cada resultado da seção Resultados, com o cálculo passo a passo e o que ele representa | `analise/estatistica/gerar_pdf_resultados.py` |
| `resultados/posto_medio_passo_a_passo.pdf` | o posto médio explicado, com a fonte da fórmula e os resultados de cada estratégia | `analise/estatistica/gera_pdf_posto.py` |
| `apendices/apendice_prompts.tex` | Apêndice A do TCC: composição dos 6 prompts e trechos de exemplo | escrito à mão (cópia do Overleaf) |
| `apendices/apendice_resultados.tex` | Apêndice B do TCC: módulos utilizados, cálculo do ICV, uma tabela de resultados por módulo e as posições usadas no posto médio | `analise/estatistica/gerar_apendice_latex.py` |
| `figuras/` | figura das 4 etapas do trabalho (`processo_trabalho`), capturas da tela da bancada (`bancada_rtl_*`) e os gráficos dos Resultados (`grafico_*`) | `analise/figuras/figura_processo.py` (processo) |
| `drive/` | os 8 PDFs explicativos da pasta "Documentação" do Google Drive (ver abaixo) | `analise/documentos/gerar_pdfs_drive.py` |
| [`validacao/`](validacao/README.md) | validação da Bancada RTL, ferramenta × Verilator à mão | `analise/validacao/validar_bancada.py` |
| `analise/` | os scripts acima e os dados da planilha | — |

## Pasta `drive/`

Cópia dos PDFs da pasta "Documentação" do Google Drive (Meu Drive › TCC › Documentação). Foram
refeitos em 18/11/2026 e enviados ao Drive como nova versão de cada arquivo, então os links
continuam os mesmos.

| Arquivo | Conteúdo |
|---|---|
| `Trabalho_visao_geral.pdf` | visão geral: objetivo do TCC, experimento, arquitetura, fluxo e organização do código |
| `analogias_bancada_rtl.pdf` | as métricas explicadas com analogias (a casa e o inspetor), sem código |
| `Metricas_como_funcionam.pdf` | as métricas da bancada (básicas, cobertura, mutação e ICV), no conceito e no código |
| `Mutacao_como_funciona.pdf` | o teste de mutação no conceito e no `app.py`: operadores, escolha dos 4 mutantes, equivalentes |
| `ICV_calculo_atual.pdf` | como o ICV é calculado, com o somador (0,70), a nota máxima (3,00) e os 10 módulos |
| `prova_cobertura.pdf` | detector de "11": comandos manuais, resultados e o `coverage.dat` cru e comentado |
| `prova_fsm_completo.pdf` | detector de "101": resultado da bancada ligado a cada ponto do `coverage.dat` (rastreabilidade) |
| `script_teste_manual_comentado.pdf` | o script de verificação manual explicado parte por parte, com os mesmos números da bancada |

`drive/fontes/` guarda os módulos, testbenches e trechos de `coverage.dat` usados nas provas,
todos de execução real no Verilator 5.032.

A pasta do Drive também tem `resultados_explicados.pdf` e `posto_medio_passo_a_passo.pdf`, enviados
em 19/11/2026. No repositório, eles ficam em `resultados/`.

Os arquivos do Drive "Comparação API/mão" e "prompting" são documentos do Google e não têm cópia
aqui. A versão em Word da comparação está em `validacao/comparacao_api_manual.docx`.

## Conferência com o TCC

Em 21/11/2026 a documentação foi comparada de novo com o PDF do TCC II (24 páginas).

- Os dois apêndices em LaTeX estão iguais aos do TCC. As 10 tabelas de resultados do Apêndice B
  (960 valores) foram conferidas por script contra `analise/estatistica/pdf_comum.py` e
  `coberturas.json`, sem nenhuma diferença. A Tabela 6 (ICV) também confere com os arquivos de
  `modulos/`.
- `resultados/resultados_explicados.pdf` usa os mesmos números das Tabelas 3 e 4 e da Figura 4 do
  TCC, com uma casa decimal. O gerador confere esses números com `assert`.
- A Tabela 2 do TCC (validação) é a soma dos pontos de linha, desvio e alternância de
  `validacao/resultado.md`.
- Figuras do TCC: a Figura 1 é `figuras/processo_trabalho.png`; a Figura 2 é
  `figuras/bancada_rtl_completa.png`; as Figuras 3 e 4 são `figuras/grafico_exemplos.png` e
  `figuras/grafico_cobertura100.png` (feitas fora do repositório, sem script gerador).
- **Count clock, GPT, rodada 1, *Few-shot*.** O desvio desse testbench aparece como 65,5% na
  planilha, no Apêndice B e no TCC, e esse é o valor usado em todos os resultados. No
  `historico.csv` da bancada, a mesma avaliação aparece com 62,5% (18/09/2026, 15h14). Com 62,5%,
  só a média de desvio do *Few-shot* na Tabela 4 mudaria, de 91,7% para 91,6%. Nenhuma conclusão
  do trabalho muda.

## Como gerar de novo

Rode no WSL, na raiz do repositório. As fontes DejaVu vêm do Ubuntu. O venv fica na pasta pessoal,
e não no `/tmp`, porque o WSL apaga o `/tmp` quando desliga.

```bash
python3 -m venv ~/venv-docs && ~/venv-docs/bin/pip install reportlab pypdfium2
~/venv-docs/bin/python documentacao/analise/estatistica/gerar_pdf_resultados.py
~/venv-docs/bin/python documentacao/analise/estatistica/gera_pdf_posto.py
~/venv-docs/bin/python documentacao/analise/estatistica/gerar_apendice_latex.py
~/venv-docs/bin/python documentacao/analise/estatistica/gerar_csv_resultados.py
~/venv-docs/bin/python documentacao/analise/documentos/gerar_prompts_txt.py
~/venv-docs/bin/python documentacao/analise/documentos/gerar_pdfs_drive.py
~/venv-docs/bin/python documentacao/analise/figuras/figura_processo.py
```

O PNG da figura é feito a partir do PDF, a 300 dpi:

```bash
~/venv-docs/bin/python -c "import pypdfium2 as p; p.PdfDocument('documentacao/figuras/processo_trabalho.pdf')[0].render(scale=300/72).to_pil().save('documentacao/figuras/processo_trabalho.png')"
```

Sem argumento, cada script grava no lugar indicado na tabela. Os geradores dos resultados, do CSV
e do apêndice conferem os números do TCC com `assert` e param se a planilha mudar. O do posto
médio imprime os postos no terminal para conferir.

Em 21/11/2026, depois da reorganização das pastas, todos os geradores e o `validar_bancada.py`
foram rodados de novo a partir dos lugares novos e funcionaram.

## O que saiu (18/11/2026)

O TCC passou a usar só análise descritiva (taxa de aprovação, score efetivo, posto médio e
cobertura dos aprovados), e a cobertura de FSM e a análise por classe de ICV saíram do texto. Por
isso foram removidos do repositório os PDFs de Friedman, Wilcoxon e conclusão estatística, o PDF
de ICV e cobertura, a correlação de Spearman e a planilha `.xlsx` antiga de 4 módulos. Eles
continuam no histórico do git. Para recuperar um arquivo:

```bash
git show e89bd43:documentacao/friedman_passo_a_passo.pdf > friedman_passo_a_passo.pdf
```
