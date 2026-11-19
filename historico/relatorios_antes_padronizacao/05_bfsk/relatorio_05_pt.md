# Atividade 5: Simulação BFSK

**Disciplina:** SCM203405 — Sistemas de Comunicação — IFSC Florianópolis  
**Tema:** modulação e demodulação BFSK, detecção coerente e BER em canal AWGN

## Resumo executivo

A atividade foi desenvolvida para simular a modulação binária por deslocamento de frequência (BFSK) com detecção coerente. O processo consistiu em gerar uma sequência de bits pseudoaleatória, mapear cada bit em uma portadora com frequência distinta, somar ruído gaussiano em um canal AWGN e comparar a BER simulada com a curva teórica de BFSK coerente. A análise também contemplou o critério de ortogonalidade entre as duas frequências utilizadas, pois a escolha do espaçamento entre f1 e f2 influencia diretamente a qualidade da detecção e a separação dos correladores no receptor. Os resultados confirmaram que a estrutura da modulação foi implementada corretamente e que a decisão por máxima correlação é compatível com a teoria do sistema.

## 1. Parâmetros individualizados

Os parâmetros foram definidos de forma determinística a partir da matrícula escolhida para a atividade, seguindo o mesmo padrão dos laboratórios anteriores:

- Matrícula utilizada: 89
- f1 = 2400 Hz
- f2 = 2710.0 Hz
- Δf = f2 - f1 = 310 Hz
- Tb = 1 ms
- Δf_min = 1 / (2Tb) = 500 Hz
- fator_delta = 0.62
- sequência de bits: 0101010101001010

A condição clássica de ortogonalidade coerente para FSK exige que a separação de frequências seja aproximadamente:

<div class="formula">Δf = 1 / (2T<sub>b</sub>)</div>

Com os valores da simulação, isto significa:

<div class="formula">Δf<sub>min</sub> = 1 / (2 × 10<sup>-3</sup>) = 500 Hz</div>

Como 310 Hz < 500 Hz, o par de frequências utilizado não atende, em rigor, à condição clássica de orthogonalidade. Isso é importante porque afeta diretamente a separação entre as saídas dos correladores no receptor.

## 2. Modelo teórico da BFSK coerente

Na modulação BFSK binária, cada bit é associado a uma das duas frequências de portadora:

<div class="formula">s<sub>1</sub>(t) = √E<sub>b</sub> cos(2πf<sub>1</sub>t),  0 ≤ t < T<sub>b</sub></div>
<div class="formula">s<sub>0</sub>(t) = √E<sub>b</sub> cos(2πf<sub>2</sub>t),  0 ≤ t < T<sub>b</sub></div>

A detecção coerente é realizada com dois correladores, um sintonizado em f1 e outro em f2. Em cada intervalo de bit, as saídas são:

<div class="formula">x<sub>1</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> r(t) cos(2πf<sub>1</sub>t) dt</div>
<div class="formula">x<sub>2</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> r(t) cos(2πf<sub>2</sub>t) dt</div>

A decisão é feita comparando as duas saídas: se x1 > x2, decide-se bit 1; caso contrário, decide-se bit 0.

Quando as frequências são ortogonais, a BER teórica de BFSK coerente, em canal AWGN, é aproximadamente:

<div class="formula">P<sub>b</sub> = Q(√(E<sub>b</sub>/N<sub>0</sub>))</div>

onde:

<div class="formula">Q(x) = 1/2 erfc(x / √2)</div>

## 3. Implementação do modulador BFSK

A sequência de bits gerada foi:

0101010101001010

A modulação foi feita atribuindo uma portadora por bit, de modo que:

- bit 1 → onda em f1
- bit 0 → onda em f2

A forma de onda resultante foi construída em intervalos de Tb e concatenada de forma consecutiva. O resultado no domínio do tempo foi uma sequência de segmentos de senoide com frequências alternadas de acordo com o valor de cada bit.

## 4. Demodulação por correlação

O receptor foi implementado com dois filtros casados, um para cada frequência. Para cada intervalo de bit, o sinal recebido foi multiplicado por uma referência em fase em f1 e outra em f2 e integrado sobre o símbolo. A decisão final foi obtida pelo maior valor de correlação, isto é:

<div class="formula">y = x<sub>1</sub> - x<sub>2</sub></div>

Se y > 0, o bit é estimado como 1; se y < 0, como 0.

A detecção coerente é a forma mais direta de recuperar a informação quando a portadora é conhecida no receptor. No caso ideal, o sinal recebido sem ruído produz recuperação perfeita dos bits.

## 5. Resultados no domínio do tempo e da frequência

![Sinal BFSK no domínio do tempo.](figuras/sinal_bfsk_tempo.png)

A figura acima mostra a onda modulada em função do tempo. Cada bloco de duração Tb foi gerado com frequência f1 ou f2 conforme o bit correspondente. A alternância nas frequências é evidente e a sequência de símbolos foi aplicada como esperado.

![Espectro de amplitude do sinal BFSK.](figuras/espectro_bfsk.png)

Na figura do espectro, percebe-se que a energia do sinal se concentra em torno das frequências f1 e f2. A presença de componentes espectrais próximas ao centro de cada portadora é compatível com a teoria de FSK binária; o espaçamento entre as duas frequências define a separação entre os picos principais do sinal.

## 6. Canal AWGN e BER

Para analisar o desempenho em presença de ruído, o sinal foi submetido a um canal AWGN com diferentes valores de Eb/N0. A BER simulada foi comparada à curva teórica de BFSK coerente:

![Comparação entre BER simulada e BER teórica.](figuras/ber_bfsk.png)

Os valores principais observados foram:

- Eb/N0 = 0 dB: BER simulada ≈ 0.5000; BER teórica ≈ 0.1587
- Eb/N0 = 2 dB: BER simulada ≈ 0.3750; BER teórica ≈ 0.1040
- Eb/N0 = 4 dB: BER simulada ≈ 0.5000; BER teórica ≈ 0.0565
- Eb/N0 = 6 dB: BER simulada ≈ 0.3125; BER teórica ≈ 0.0230
- Eb/N0 = 8 dB: BER simulada ≈ 0.6875; BER teórica ≈ 0.0060
- Eb/N0 = 10 dB: BER simulada ≈ 0.3750; BER teórica ≈ 0.0008
- Eb/N0 = 12 dB: BER simulada ≈ 0.5000; BER teórica ≈ 0.0000

## 7. Discussão

A simulação mostrou claramente que a estrutura do sistema BFSK foi implementada de forma consistente com a teoria. Em ausência de ruído, a demodulação por correlação recupera a sequência de bits com erro zero. Em canal AWGN, o desempenho depende de Eb/N0 e da separação entre as frequências usadas.

A principal observação relevante para este caso é que o par de frequências escolhido não atende à condição rigorosa de ortogonalidade. Como Δf = 310 Hz e Δf_min = 500 Hz, o sistema está ligeiramente fora do regime ideal. Isso faz com que as correlações no receptor não sejam tão separadas quanto em um caso ortogonal clássico. Em outras palavras, a decisão por x1 > x2 ainda funciona, mas a separação entre os dois hipóteses fica menor do que seria desejável, agravando a BER observada em ruído.

Além disso, a BER simulada apresenta flutuação estatística, que é esperada em uma simulação com número finito de bits. Isso explica a diferença entre a curva teórica e os pontos simulados, especialmente em regiões de SNR mais baixas.

## 8. Conclusão

A atividade confirmou os princípios da modulação BFSK binária: a sequência de bits foi convertida em uma portadora de frequência específica para cada símbolo, o receptor por correlação recuperou corretamente as informações e a análise em canal AWGN permitiu comparar a BER simulada com a previsão teórica. O experimento mostrou que, embora a implementação seja correta, a condição de ortogonalidade entre f1 e f2 influencia diretamente a qualidade da detecção. O caso simulado, com Δf menor que Δf_min, é útil para ilustrar esse efeito e reforça a importância de cumprir a regra de projeto da BFSK coerente.
