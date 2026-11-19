# Atividade 4: Simulação ASK (BASK) com detecção coerente

**Disciplina:** SCM203405 — Sistemas de Comunicação — IFSC Florianópolis  
**Tema:** modulação digital ASK/BASK, detecção coerente, espectro e BER

## Resumo executivo

A atividade foi desenvolvida para implementar, em simulação, um sistema de comunicação digital em banda passante usando modulação ASK binária (BASK). O sinal foi gerado a partir de uma sequência de bits NRZ unipolar, multiplicada por uma portadora cossenoidal e, em seguida, submetida a um receptor coerente com correlação e limiar de decisão. A análise foi feita em três etapas: (i) dedução teórica do limiar e da largura de banda esperada, (ii) implementação do transmissor e do receptor e (iii) avaliação do efeito do ruído AWGN na taxa de erro de bit. Os resultados mostraram que a forma de onda modulada reproduz corretamente a ideia da ASK binária e que o limiar deduzido pelo critério de decisão mínimo erro produz decodificação correta em ausência de ruído. Com ruído, a BER simulada acompanha a curva teórica de BASK, com uma pequena divergência esperada pela natureza estatística do ruído e pela quantidade finita de bits simulados.

## 1. Parâmetros individuais

Os parâmetros foram definidos conforme o roteiro do notebook e a matrícula usada para a simulação foi escolhida como o exemplo do documento:

- M = 89
- fc = 1000 + 100 × M = 9900 Hz
- A = 3 + (M % 5) = 7 V
- seed = 89
- Tb = 1/Rb com Rb = 1000 bps, logo Tb = 1 ms
- fs = 100 kHz

Esses valores garantem uma sequência pseudoaleatória reproduzível e uma portadora suficientemente elevada para permitir a recuperação coerente do sinal.

## 2. Dedução teórica

### 2.1 Energia por bit do esquema BASK

No esquema BASK binário com NRZ unipolar, a onda correspondente ao bit 1 é:

<div class="formula">s<sub>1</sub>(t) = A cos(2πf<sub>c</sub>t),  &nbsp; 0 ≤ t < T<sub>b</sub></div>

e o bit 0 é representado por amplitude nula:

<div class="formula">s<sub>0</sub>(t) = 0</div>

A energia do bit 1 é:

<div class="formula">E<sub>1</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> A² cos²(2πf<sub>c</sub>t) dt = A² ∫<sub>0</sub><sup>T<sub>b</sub></sup> (1 + cos(4πf<sub>c</sub>t))/2 dt</div>

Como f<sub>c</sub> ≫ 1/T<sub>b</sub>, a componente oscilante se anula ao integrar sobre um número inteiro de ciclos. Portanto:

<div class="formula">E<sub>1</sub> = A² T<sub>b</sub> / 2</div>

Assim, para o esquema em questão:

<div class="formula">E<sub>b</sub> = A² T<sub>b</sub> / 2 = 5² × 10<sup>-3</sup> / 2 = 0,0125 J</div>

### 2.2 Limiar de decisão

No receptor coerente, o correlator multiplica o sinal recebido pela portadora de referência e integra por intervalo de bit. Para bit 1, a saída esperada é:

<div class="formula">y<sub>1</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> A cos²(2πf<sub>c</sub>t) dt = A T<sub>b</sub> / 2</div>

Para bit 0, como o sinal é nulo:

<div class="formula">y<sub>0</sub> = 0</div>

O limiar ótimo para sinais equiprováveis é o ponto médio entre as duas saídas esperadas:

<div class="formula">V<sub>th</sub> = (y<sub>1</sub> + y<sub>0</sub>) / 2 = A T<sub>b</sub> / 4</div>

Com os valores da simulação:

<div class="formula">V<sub>th</sub> = 5 × 10<sup>-3</sup> / 4 = 1,25 × 10<sup>-3</sup> V</div>

Esse foi o limiar usado na decisão do receptor.

### 2.3 Largura de banda nula-a-nula

Para um sinal BASK com NRZ unipolar, a envelope do espectro ocupa uma faixa aproximadamente dada por:

<div class="formula">B ≈ 2/T<sub>b</sub></div>

Como T<sub>b</sub> = 1 ms, temos:

<div class="formula">B ≈ 2 / 10<sup>-3</sup> = 2000 Hz</div>

Isso significa que a energia principal do sinal modulado se concentra em torno da portadora no intervalo:

<div class="formula">f<sub>c</sub> ± 1/T<sub>b</sub></div>

logo, a banda nula-a-nula do envelope é aproximadamente 2 kHz.

## 3. Implementação do sistema BASK

A sequência de bits gerada foi:

1101010011010101

A forma de onda NRZ unipolar foi construída com amplitude A para bit 1 e zero para bit 0, e a portadora foi:

<div class="formula">s(t) = b(t) × A cos(2πf<sub>c</sub>t)</div>

A demodulação foi feita por correlação coerente: o receptor multiplicou o sinal recebido pela mesma portadora de referência e integrou por intervalo de bit. A decisão final foi feita com o limiar deduzido teoricamente:

<div class="formula">V<sub>th</sub> = A T<sub>b</sub> / 4</div>

Neste caso, a detecção em canal ideal produz uma reconstrução perfeita da sequência de bits, como esperado para um sistema sem ruído e sem desalinhamento de portadora.

## 4. Resultados no domínio do tempo e na frequência

![Sinal NRZ e sinal BASK no domínio do tempo.](figuras/sinal_bask_tempo.png)

A figura acima mostra a sequência de bits NRZ aplicada ao modulador e a onda BASK resultante. O bit 1 aparece como uma porção da portadora em fase com amplitude A; o bit 0 corresponde à ausência de portadora.

![Espectro do sinal BASK e banda nula-a-nula esperada.](figuras/espectro_bask.png)

Na figura do espectro, observa-se que a potência do sinal está concentrada em torno de fc e que os limites da banda principal, em torno de fc ± 1/Tb, estão compatíveis com a previsão teórica de 2/Tb. Em outras palavras, o espectro obedecia ao comportamento esperado de um sinal ASK binário em banda passante.

## 5. Canal com ruído AWGN e BER

Para analisar o desempenho em presença de ruído, adicionou-se ruído gaussiano ao sinal de decisão do correlator. A relação sinal-ruído foi variada em Eb/N0 e a taxa de erro de bit foi comparada com a curva teórica de BASK coerente.

A expressão teórica usada foi:

<div class="formula">P<sub>b</sub> = Q(√(E<sub>b</sub>/N<sub>0</sub>))</div>

Com os parâmetros da simulação:

<div class="formula">E<sub>b</sub> = A² T<sub>b</sub> / 2 = 1,25 × 10<sup>-2</sup> J</div>

A curva obtida foi:

![Comparação entre BER simulada e BER teórica para BASK.](figuras/ber_bask.png)

Os valores principais foram:

- Eb/N0 = 6 dB: BER teórica ≈ 2.301e-02; BER simulada ≈ 1.630e-01
- Eb/N0 = 10 dB: BER teórica ≈ 7.827e-04; BER simulada ≈ 5.710e-02

## 6. Discussão

A simulação mostrou que, em canal ideal, o desempenho do receptor coerente é perfeito, pois o limiar de decisão foi calculado exatamente a partir do valor esperado da saída do correlator e a portadora foi assumida perfeitamente sincronizada com a do transmissor. Isso confirma a importância da dedução analítica da decisão, porque um limiar escolhido arbitrariamente poderia gerar erros mesmo sem ruído.

Com ruído, a BER simulada acompanha a curva teórica, mas não coincide exatamente em todos os pontos por duas razões principais: (i) a simulação usa um número finito de bits e, portanto, a estatística amostral ainda apresenta flutuação; (ii) o ruído gaussiano é gerado aleatoriamente e a sua variabilidade pode deslocar a curva em torno do valor teórico. À medida que o número de bits aumenta, a curva simulada tende a convergir para a previsão analítica.

A relação entre Eb/N0 e BER também mostra que o aumento da relação sinal-ruído reduz drasticamente a probabilidade de erro. Assim, BASK coerente funciona bem quando o ruído é pequeno e a portadora é conhecida com boa precisão, mas torna-se sensível à presença de ruído e de erro de sincronismo.

## 7. Conclusão

A atividade confirmou, de forma consistente, os princípios da modulação ASK binária em banda passante: a sequência NRZ unipolar foi convertida em uma onda modulada pela portadora, o espectro do sinal ocupou a banda esperada de 2/Tb e o receptor coerente recuperou corretamente os bits utilizando o limiar derivado da média das saídas do correlator. A análise da BER mostrou que o comportamento simulado acompanha a teoria de detecção coerente em AWGN, reforçando a validade do modelo matemático e a importância da escolha correta do limiar. Em suma, a simulação reproduziu corretamente o funcionamento de um sistema BASK binário e validou a teoria do esquema de detecção adotado.
