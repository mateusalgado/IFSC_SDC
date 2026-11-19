# Atividade 7 — Modulação e demodulação QPSK
Mateus Salgado Barboza Costa · Matrícula 202110810789
SCM203405 · Sistemas de Comunicação · IFSC Florianópolis

## Resumo executivo
O transmissor agrupou dez bits em cinco dibits. No canal ideal, os correlatores recuperaram as cinco coordenadas I/Q e reproduziram os dez bits. Sob ruído a 6 dB, integrar durante o símbolo inteiro reduziu a contagem de erros de 45 para 7 nos mesmos 2.000 bits.

## 1. Modulação no tempo
A taxa de 1.000 bit/s dá 1 ms por bit e 2 ms por símbolo. A portadora de 2,5 kHz completa cinco ciclos por símbolo. Com energia de 1 J por bit, cada coordenada vale +1 ou −1. A envoltória tem amplitude √(4Eb/T) = 44,72, igual ao pico amostrado.

![Figura 1. Bits, ramos I/Q e sinal QPSK. As linhas verticais marcam os limites dos cinco símbolos.](figuras/sinal_qpsk_tempo.png)

Os dibits 00 | 00 | 00 | 11 | 01 explicam os dois saltos. Em 6 ms, a passagem de (−1, −1) para (+1, +1) inverte a portadora. Em 8 ms, apenas I muda de sinal e o vetor gira mais 90°.

<!-- página -->

## 2. Espectro e recepção coerente
Cada ramo mantém o mesmo nível durante 2 ms. Assim, os primeiros nulos se encontram a 1/T = 500 Hz da portadora, em 2 e 3 kHz. A largura do lóbulo principal é 1 kHz. A sequência curta introduz oscilações no espectro de amplitude.

![Figura 2. FFT da sequência de cinco símbolos em escala linear e em decibéis.](figuras/espectro_qpsk.png)

O receptor multiplica o sinal por cada base e soma as 200 amostras do símbolo com peso de 10 µs. A ortogonalidade cancela a contribuição do outro ramo. A componente em fase resulta em −1, −1, −1, +1, −1. Em quadratura, resulta em −1, −1, −1, +1, +1.

![Figura 3. Acumulação nos dois correlatores. Os pontos indicam a última amostra de cada janela.](figuras/correladores_qpsk.png)

Aplicar o limiar zero e intercalar os ramos fornece 0000001101, a sequência transmitida. Os três primeiros símbolos repetem a fase, por isso há somente três posições ocupadas na constelação desta sequência.

<!-- página -->

## 3. Sensibilidade à fase, ao ruído e à janela
Cada ensaio usou 2.000 bits. Nas comparações de janela, foram mantidos os bits e as amostras de ruído. A BER é a razão entre bits errados e bits transmitidos.

| Ensaio | Erros / 2.000 bits | BER |
|---|---|---|
| Portadora com 1,3 ou 5,3 ciclos por símbolo, sem ruído | 0 em cada teste | 0 |
| Erro de fase de 30° ou 44,9°, sem ruído | 0 em cada teste | 0 |
| Erro de fase de 45,1° ou 60°, sem ruído | 1.000 em cada teste | 0,5000 |
| AWGN a 12 dB, janela de 2 ms | 0 | 0 |
| AWGN a 6 dB, janela de 2 ms | 7 | 0,0035 |
| AWGN a 0 dB, janela de 2 ms | 164 | 0,0820 |
| AWGN a 6 dB, janela de 1 ms | 45 | 0,0225 |

Com ciclos fracionários, a projeção de um ramo pode aparecer na saída do outro. A 1,3 ciclo, os deslocamentos são maiores que a 5,3 ciclos. Nos dois testes ainda se preserva a polaridade. O erro de fase tem outro efeito. Ele gira toda a constelação e, ao ultrapassar 45°, leva cada ponto ao quadrante vizinho.

![Figura 4. Dispersão das saídas I/Q a 6 dB com integração durante o símbolo inteiro.](figuras/constelacao_qpsk_6db.png)

## 4. Conclusão
A 6 dB, a BER teórica vale aproximadamente 0,00239, compatível com os sete erros observados. Usar só a primeira metade do símbolo preserva o sinal das projeções no canal ideal, mas descarta metade da energia. A perda de aproximadamente 3 dB explica por que a janela curta erra com mais frequência.
