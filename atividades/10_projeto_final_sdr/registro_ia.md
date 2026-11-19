# Registro de uso de IA

Projeto final de SCM203405, Link de comunicação SDR. Este anexo consolida os registros das etapas feitas até 18/11/2026. Cada item informa a ferramenta, o pedido, o que foi aproveitado e como a resposta foi verificada.

Ferramenta em todas as etapas: Claude Code (Anthropic), com acesso aos arquivos do projeto, ao terminal e ao RTL-SDR ligado ao computador. Os pedidos foram feitos em linguagem natural, em português.

## Etapa 1 - Estudo e auditoria da referência

- Pedido: organizar os arquivos do projeto no padrão das atividades anteriores, ler o enunciado e o código OOK do professor e mapear as funções.
- Aproveitado: a tabela de blocos e funções, a lista de limitações do receptor de referência, o cálculo do goodput máximo do quadro e o roteiro de execução nos rádios.
- Verificação por cálculo: o goodput de 9.438 bit/s para 128 bytes a 10 kbit/s coincide com a observação do enunciado. O CRC-8 da mensagem de exemplo, 0x44, foi calculado antes da recepção e é o mesmo valor recebido pelo rádio.
- Verificação por medição: o receptor de referência foi executado sem alteração do arquivo. Com 34 ppm falhou nos dois dongles disponíveis. Com o ppm calibrado decodificou a mensagem com CRC válido. As saídas estão em resultados/referencia_rx_*.txt.
- Correção de uma hipótese da IA: a primeira captura mostrava rajadas em 915,2 MHz e a IA considerou que poderiam ser o Pluto. A análise no tempo mostrou saltos de frequência e duração de 30 ms, incompatíveis com a transmissão cíclica. O Pluto ainda não estava transmitindo.

## Etapa 2 - Novas modulações

- Pedido: implementar 2-FSK e BPSK em simulação, com um pulso alternativo, e medir a banda de 99%.
- Aproveitado: os moduladores e detectores de sdrlink/modem.py e o script etapa2_modulacoes.py.
- Verificação por teoria: a banda de 99% da BPSK retangular foi comparada ao valor clássico de 20,57 Rb. A simulação deu 19,78 Rb, com variação de 19,43 a 20,26 Rb entre blocos, explicada pela cauda plana do espectro.
- Decisão da equipe a revisar: a IA propôs DBPSK no lugar da BPSK coerente. O enunciado aceita a troca desde que haja comparação em simulação, que está na seção 4 do relatório.

## Etapa 3 - Simulação do canal

- Pedido: curvas de BER em AWGN comparadas à teoria e sensibilidade a fase, offset e temporização.
- Aproveitado: o script etapa3_canal.py e as figuras.
- Verificação por teoria: as quatro curvas simuladas foram comparadas ponto a ponto com as expressões fechadas. Exemplo: BPSK a 10 dB, 0,00000396 simulado contra 0,00000387 teórico, com 16 erros contados. A expressão da OOK não coerente com limiar em metade da amplitude foi deduzida a partir das distribuições de Rayleigh e de Rice e conferida pela simulação.
- Limitação conhecida: os pontos com menos de 20 erros têm incerteza alta.

## Etapa 4 - Integração do protocolo

- Pedido: quadro com número de sequência e CRC-16, receptor de pacotes e medida de PER.
- Aproveitado: sdrlink/quadro.py, sdrlink/receptor.py e etapa4_protocolo.py.
- Verificação por vetor de teste: CRC-16/CCITT de "123456789" igual a 0x29B1 e CRC-8 0x07 igual a 0xF4.
- Verificação por teste exaustivo: nenhum dos 565.516 erros de 2 bits em 1.064 bits passa pelo CRC-16. No CRC-8 passam 3.684 de 531.996.
- Verificação por simulação: a PER do receptor completo foi comparada à previsão pela BER teórica, com diferença menor que 0,1 dB.
- Erro da IA encontrado pela verificação: a curva de PER da DBPSK tinha um ponto fora da tendência em 13 dB. A causa era a escolha do pico de sincronismo, que perdia um quadro em 25.000. O código foi corrigido e a simulação repetida.

## Etapas 5 e 6 - Integração SDR, calibração e caracterização

- Pedido: instalar as bibliotecas, calibrar o RTL-SDR, receber o sinal do Pluto do professor e medir PER, goodput e banda.
- Aproveitado: calibrar_ppm.py, rx_gravar.py, rx_decodificar.py, ensaio_referencia.py e ver_sinal.py.
- Verificação por medição: 56 ppm no dongle A e 86 ppm no dongle B. O valor do dongle B havia sido informado como 84 ppm por outra medida, coerente com o resultado. O offset por quadro estimado pelo receptor foi comparado à posição da portadora na FFT da mesma captura e os dois acompanham a mesma deriva.
- Verificação por repetição: a primeira varredura de ganho saiu irregular. Foi repetida em duas passadas, e a conclusão do relatório usa a repetição e declara a variação do canal.
- Discrepância não resolvida: a banda de 99% medida, 63 kHz, é 24% maior que a simulada, 50,6 kHz.
- Não verificado: tx_pluto.py foi testado apenas a seco, gerando o sinal em arquivo. Ele ainda não transmitiu pelo Pluto.

## Redação

O texto dos relatórios foi redigido pela IA a partir dos resultados acima. A equipe deve revisar o texto, refazer as contas principais e conseguir explicar cada bloco na defesa oral.
