# Documentação do TCC

Material de apoio do TCC "Avaliação de estratégias de engenharia de prompt na geração de
testbenches para verificação de módulos RTL". O texto do TCC fica no Overleaf. Aqui ficam os
apêndices em LaTeX, a figura, os PDFs que explicam os resultados e a validação da Bancada RTL.

Todos os PDFs são gerados por scripts em `analise/`. Os números vêm da planilha do experimento
(10 módulos, 6 estratégias, 2 LLMs, 2 rodadas = 240 testbenches), copiada em
`analise/estatistica/pdf_comum.py` (mutantes) e `analise/estatistica/coberturas.json` (coberturas).

## O que tem aqui

| Arquivo | O que é | Gerado por |
|---|---|---|
| `apendice_prompts.tex` | Apêndice A do TCC: composição dos 6 prompts e trechos de exemplo | escrito à mão (cópia do Overleaf) |
| `apendice_resultados.tex` | Apêndice B do TCC: ICV de cada módulo e uma tabela de resultados por módulo | `analise/estatistica/gerar_apendice_latex.py` |
| `figuras/processo_trabalho.pdf` e `.png` | figura das 4 etapas do trabalho (preparação, geração, avaliação, análise) | `analise/figuras/figura_processo.py` |
| `resultados_explicados.pdf` | cada resultado da seção Resultados, com o cálculo passo a passo e o que ele representa | `analise/estatistica/gerar_pdf_resultados.py` |
| `posto_medio_passo_a_passo.pdf` | o posto médio explicado, com a fonte da fórmula e os resultados de cada estratégia | `analise/estatistica/gera_pdf_posto.py` |
| `drive/` | os 8 PDFs explicativos da pasta "Documentação" do Google Drive (ver abaixo) | `analise/documentos/gerar_pdfs_drive.py` |
| `validacao/` | validação da Bancada RTL, ferramenta × Verilator à mão ([README](validacao/README.md)) | `analise/validacao/validar_bancada.py` |

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

Os arquivos do Drive "Comparação API/mão" e "prompting" são documentos do Google e não têm cópia
aqui. A versão em Word da comparação está em `validacao/comparacao_api_manual.docx`.

## Como gerar de novo

No WSL (as fontes DejaVu vêm do Ubuntu), na raiz do repositório:

```bash
python3 -m venv /tmp/docs && /tmp/docs/bin/pip install reportlab pypdfium2
/tmp/docs/bin/python analise/estatistica/gerar_pdf_resultados.py
/tmp/docs/bin/python analise/estatistica/gera_pdf_posto.py
/tmp/docs/bin/python analise/estatistica/gerar_apendice_latex.py
/tmp/docs/bin/python analise/documentos/gerar_pdfs_drive.py
/tmp/docs/bin/python analise/figuras/figura_processo.py
```

Sem argumento, cada script grava no lugar indicado na tabela. O PNG da figura é feito a partir do
PDF com o `pypdfium2` (escala 300/72, ou seja, 300 dpi). Os scripts conferem os números do TCC com
`assert` e param se a planilha mudar.

## O que saiu (18/11/2026)

O TCC passou a usar só análise descritiva (taxa de aprovação, score efetivo, posto médio e
cobertura dos aprovados), e a cobertura de FSM e a análise por classe de ICV saíram do texto. Por
isso foram removidos do repositório os PDFs de Friedman, Wilcoxon e conclusão estatística, o PDF
de ICV e cobertura, a correlação de Spearman e a planilha `.xlsx` antiga de 4 módulos. Eles
continuam no histórico do git. Para recuperar um arquivo:

```bash
git show e89bd43:documentacao/friedman_passo_a_passo.pdf > friedman_passo_a_passo.pdf
```
