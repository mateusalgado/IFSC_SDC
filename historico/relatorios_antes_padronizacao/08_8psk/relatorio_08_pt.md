# Atividade 8 — Modulação e demodulação 8-PSK
Mateus Salgado Barboza Costa · Matrícula 202110810789
SCM203405 · Sistemas de Comunicação · IFSC Florianópolis

## Resumo executivo
O transmissor enviou quatro símbolos Gray na sequência S6, S5, S8 e S8. A 9 dB, o receptor recuperou os 12 bits. O segundo símbolo apresentou a menor margem angular. Ao reduzir a relação Eb/N0 para 8 dB, mantendo a realização do ruído, somente esse símbolo passou a ser decidido como o vizinho.

## 1. Parâmetros e mapeamento
A taxa de 3.000 bit/s e os três bits por símbolo produzem 1.000 símbolos/s. Cada símbolo dura 1 ms e contém três ciclos da portadora de 3 kHz. A envoltória é de 1 V e a energia por símbolo vale 0,0005 J para a carga de 1 Ω.

| Intervalo | Bits | Símbolo | Fase I/Q | I/√E | Q/√E |
|---|---|---|---|---|---|
| 0 a 1 ms | 000 | S6 | 225° | −0,7071 | −0,7071 |
| 1 a 2 ms | 001 | S5 | 180° | −1,0000 | 0 |
| 2 a 3 ms | 101 | S8 | 315° | +0,7071 | −0,7071 |
| 3 a 4 ms | 101 | S8 | 315° | +0,7071 | −0,7071 |

![Figura 1. A tabela Gray posiciona os oito símbolos a cada 45°. Os círculos destacam os três usados na sequência.](figuras/constelacao_ideal_8psk.png)

A distância entre vizinhos é 2√E sen(22,5°) = 0,7654√E. As três fronteiras temporais têm variações de −45°, +135° e 0° no plano I/Q. Como a forma de onda usa cos(2πfct − φ), o sinal do deslocamento da senoide é oposto.

<!-- página -->

## 2. Largura de banda e decisão por fase
Em banda base, o pulso NRZ de 0,333 ms dá nulos a cada 3 kHz. Sua média positiva produz a componente contínua. Após o agrupamento, os coeficientes I/Q duram 1 ms. O lóbulo principal modulado fica entre 2 e 4 kHz, centrado na portadora de 3 kHz.

![Figura 2. Espectro dos quatro símbolos e estimativa da densidade de potência de uma sequência longa.](figuras/espectro_8psk.png)

As duas bases têm energia unitária e produto interno de 1,10 × 10⁻¹⁶ no primeiro símbolo. Os correlatores acumulam as projeções durante 1 ms. O receptor calcula a fase por atan2(Y, X) e escolhe o centro de menor distância angular, considerando a volta de 360°.

| Símbolo enviado | Fase estimada | Decisão | Margem angular |
|---|---|---|---|
| S6 | 220,26° | S6 | 35,51° |
| S5 | 201,79° | S5 | 1,42° |
| S8 | 320,30° | S8 | 34,41° |
| S8 | 327,88° | S8 | 19,24° |

A margem é a diferença entre as distâncias às duas fases candidatas mais próximas. Para S5, a fronteira com S6 está em 202,5°. A estimativa ficou a apenas 0,71° dessa fronteira. A 8 dB ela a ultrapassou, trocando 001 por 000. O código Gray limitou essa troca a um bit errado.

![Figura 3. Deslocamento dos quatro símbolos e comparação dos bits no ponto de referência de 9 dB.](figuras/decisao_8psk.png)

<!-- página -->

## 3. Ruído e desempenho estatístico
O ruído branco gera um patamar aproximadamente plano no espectro. A 0 dB a oscilação recebida fica difícil de reconhecer a olho. O receptor se beneficia da integração durante todo o símbolo. A 9 dB, em 2.000 símbolos, o desvio-padrão normalizado medido nos ramos foi 0,1475, próximo dos 0,1449 previstos.

![Figura 4. Constelações com 2.000 símbolos por nível de Eb/N0. Os pontos vermelhos correspondem a decisões erradas.](figuras/constelacoes_awgn_8psk.png)

Para estimar a BER, cada ponto da curva usou 30.000 símbolos, ou 90.000 bits. A aproximação teórica considera trocas entre vizinhos. A 0 dB, houve BER de 0,1230, frente a 0,1162 previstos. A 14 dB houve zero erro na amostra, com previsão de 8,76 × 10⁻⁷ por bit.

![Figura 5. BER simulada e aproximação teórica para 8-PSK Gray, com BPSK/QPSK como referência.](figuras/ber_8psk.png)

Para BER de 10⁻⁴, as curvas indicam 11,72 dB para 8-PSK e 8,40 dB para BPSK/QPSK. O custo de cerca de 3,33 dB acompanha a maior eficiência espectral. À mesma taxa de bits, 8-PSK exige dois terços da taxa de símbolos da QPSK.

<!-- página -->

## 4. Sincronismo e análise de sensibilidade
Uma defasagem local de +20° gira os pontos e reduz a margem até a fronteira mais próxima de 22,5° para apenas 2,5°. A 30 dB, houve zero erro em 2.000 símbolos com e sem o desvio. A 9 dB, a taxa de erro de símbolo passou de 0,0075 para 0,3865. No canal ideal, a SER medida foi zero a 22,4° e um a 22,6°.

| Alteração | Medida de referência | Medida após a alteração |
|---|---|---|
| Eb/N0 de 9 para 12 dB | σ = 0,14541 | σ = 0,10294 |
| Mesma comparação, 90.000 bits | BER = 0,002989 | BER = 0,0000222 |
| Portadora de 3 para 3,3 kHz a 30 dB | Desvio RMS = 0,0183 | Desvio RMS = 0,0508 |

![Figura 6. Detalhe da vizinhança de S1 a 30 dB, com 3 e 3,3 ciclos por símbolo. Escalas normalizadas por √E.](figuras/portadora_fracionaria_8psk.png)

Com 3,3 ciclos, a projeção cruzada e a energia das bases variam conforme a fase inicial da janela. Surgem vários centros, mesmo com pouco ruído. Já o aumento de 3 dB em Eb/N0 reduz o espalhamento aleatório por um fator de 0,708, em acordo com a previsão de 10^(−3/20).

## 5. Conclusão
O 8-PSK transmite três bits por símbolo, mas exige maior precisão de fase que a QPSK. Mantendo Eb, passar para 16-PSK reduz a distância entre vizinhos de 1,3257√Eb para 0,7804√Eb. Para a mesma taxa de bits, o lóbulo principal fica 25% mais estreito. A menor distância aumenta a suscetibilidade a erros.
