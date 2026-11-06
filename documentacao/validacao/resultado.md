# Validação da Bancada RTL: ferramenta × execução manual

Gerado por `analise/validacao/validar_bancada.py` em 06/11/2026. Valores da bancada; a última coluna diz se a execução manual deu o mesmo resultado (aprovação, cada tipo de cobertura e o destino de cada mutante). — = métrica sem pontos no circuito.

| Circuito | Passou | Linha | Desvio | Alternância | FSM | Mutantes mortos | Manual |
|---|---|---|---|---|---|---|---|
| Somador de 32 bits (combinacional) | sim | — | — | 13/97 | — | 1/1 | ✅ iguais |
| Detector da sequência 11 (FSM com case) | sim | 4/5 | 6/8 | 6/6 | 3/4 | 4/4 | ✅ iguais |
| Detector da sequência 101 (FSM com case) | sim | 5/6 | 2/2 | 6/6 | 4/5 | 4/4 | ✅ iguais |
| Temporizador (FSM com case, 7 estados) | sim | 8/9 | 17/18 | 24/34 | 7/8 | 4/4 | ✅ iguais |
| Fancytimer do HDLBits (FSM com if) | sim | 4/4 | 9/10 | 28/35 | — | 3/4 | ✅ iguais |
