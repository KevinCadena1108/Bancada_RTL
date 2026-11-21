# Prompts do experimento

Os 6 prompts usados para gerar os *testbenches*, um arquivo por estratégia. Em cada geração,
`[MÓDULO]` foi substituído pelo código completo do módulo avaliado (pasta `documentacao/modulos/`), e cada
prompt foi enviado em uma sessão nova do LLM. Foi considerado o primeiro *testbench* gerado, sem
correções manuais.

| Arquivo | Estratégia | Composição |
|---|---|---|
| `1_zero_shot.txt` | Zero-shot | solicitação + módulo + requisitos |
| `2_few_shot.txt` | Few-shot | exemplos + solicitação + módulo + requisitos |
| `3_especialista_zero_shot.txt` | Especialista Zero-shot | papel de especialista + solicitação + módulo + requisitos |
| `4_especialista_few_shot.txt` | Especialista Few-shot | papel de especialista + exemplos + solicitação + módulo + requisitos |
| `5_planning_zero_shot.txt` | Planning Zero-shot | planejamento + módulo + requisitos |
| `6_planning_few_shot.txt` | Planning Few-shot | exemplos + planejamento + módulo + requisitos |

Os exemplos das estratégias *Few-shot* são um comparador de 4 bits (circuito combinacional) e um
registrador de deslocamento de 4 bits (sequencial), elaborados para o trabalho. Os requisitos são
os mesmos nos 6 prompts.

Os arquivos são gerados a partir do Apêndice A do TCC (`documentacao/apendices/apendice_prompts.tex`) por
`documentacao/analise/documentos/gerar_prompts_txt.py`. O texto é o mesmo enviado aos LLMs; só as quebras de
linha podem diferir do original.
