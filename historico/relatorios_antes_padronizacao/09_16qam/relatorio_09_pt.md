# Atividade 9 - Modulação e demodulação 16-QAM
Mateus Salgado Barboza Costa · Matrícula 202110810789
SCM203405 · Sistemas de Comunicação · IFSC Florianópolis · 11/11/2026

## Resumo executivo
A cadeia 16-QAM transmitiu 64 bits em 16 símbolos, usando a tabela Gray do roteiro. O receptor recuperou todos os bits no canal ideal e no ensaio curto a 12 dB. A análise avaliou o espectro, a energia, os erros em AWGN e a sensibilidade do receptor à fase, à frequência e à duração da integração.

## 1. Parâmetros e mapeamento
A taxa de símbolos é 1 kbaud, com duração de 1 ms. Os quatro bits por símbolo produzem 4 kbit/s e 0,25 ms por bit. A portadora de 5 kHz completa cinco ciclos por símbolo. A amostragem de 200 kHz fornece 200 amostras por símbolo.

| Grupo | Coordenadas I/Q | Energia do símbolo |
|---|---|---|
| Primeiro 0000 | (−3, +3) | 18 J |
| Segundo 0000 | (−3, +3) | 18 J |
| Terceiro 1000 | (−3, −3) | 18 J |
| Quarto 0101 | (−1, +1) | 2 J |

![Figura 1. Constelação 16-QAM e rótulos Gray. Os círculos destacam os pontos presentes nos 16 símbolos transmitidos.](figuras/constelacao_16qam.png)

E₀ = 1 J representa a escala de cada componente PAM. A menor energia QAM é 2E₀, e a média para os 16 pontos equiprováveis é 10E₀. A sequência sorteada teve energia média de 9,50 J, confirmada pela integração da potência do sinal. O canal usa Eb = 10E₀/4 = 2,5 J como referência.

<!-- página -->

## 2. Forma de onda e ocupação espectral
Cada par I/Q escolhe a amplitude e a fase da senoide. No primeiro símbolo, o raio é √18 e o ângulo do vetor é 135°. Com a normalização do roteiro, a amplitude de pico é 189,74. O código soma o ramo seno, de modo que o sinal desse intervalo é 189,74 cos(2π × 5.000t − 135°).

![Figura 2. Ramos I e Q e sinal 16-QAM nos seis primeiros símbolos. A linha tracejada acompanha a envoltória.](figuras/sinal_16qam_tempo.png)

O pulso de cada ramo dura 1 ms. Os primeiros nulos ao redor da portadora aparecem em 4 e 6 kHz, largura de 2 kHz. A sequência polar de bits tem nulos em ±4 kHz, largura de 8 kHz. Agrupar quatro bits por símbolo reduz a largura entre nulos por um fator quatro.

![Figura 3. Espectro do sinal transmitido. As linhas indicam 4, 5 e 6 kHz.](figuras/espectro_16qam.png)

A média unipolar da sequência foi 0,421875 e a polar foi −0,15625. Portanto ambas têm contribuição em DC nesta realização curta. As flutuações unipolares possuem metade da amplitude das polares, correspondendo a cerca de 6 dB a menos em potência. A irregularidade do periodograma diminui ao fazer a média de vários blocos.

<!-- página -->

## 3. Correlação e decisão
A energia numérica de cada base foi 1,000000, e o produto interno foi −9,55 × 10⁻¹⁷. A ortonormalidade permite que cada correlator recupere sua coordenada ao integrar o símbolo inteiro. Para 0000, as saídas são (−3, +3). A mínima distância seleciona esse ponto e a tabela inversa devolve os quatro bits.

![Figura 4. Integrais acumuladas dos dois correlatores no canal ideal. Os pontos marcam as amostras utilizadas pelo decisor.](figuras/correladores_16qam.png)

No canal ideal, os 64 bits foram recuperados sem erro. Ao antecipar a amostragem para T/2, as projeções caíram pela metade. Mantendo os limiares originais, os níveis ±1,5 foram decididos como ±1. O teste produziu 15 bits errados em dez símbolos.

## 4. Canal AWGN
A referência de 12 dB resulta em N₀ = 0,15774 e σ = √(N₀/2) = 0,28084 por eixo. O afastamento até a fronteira mais próxima vale 1, ou 3,56σ. A nuvem de 1.500 símbolos mediu σ de 0,2793 em I e 0,2704 em Q. Foram usados os mesmos bits e sementes nos diferentes níveis de ruído.

| Eb/N₀ | Erros nos 64 bits | BER em 6.000 bits |
|---|---|---|
| 20 dB | 0 | 0 |
| 12 dB | 0 | 0 |
| 10 dB | 0 | 0,001333 |
| 6 dB | 1 | 0,023500 |
| 3 dB | 7 | 0,071000 |
| 0 dB | 12 | 0,136500 |

A 3 dB houve seis erros de símbolo. Cinco trocas atingiram vizinhos horizontais ou verticais e alteraram um bit cada. A troca diagonal 0101 → 0000 alterou dois bits. As SER condicionais foram 0,3436 nos pontos internos, 0,2674 nas bordas e 0,1751 nos cantos. Essas regiões têm, respectivamente, quatro, três e duas fronteiras próximas.

<!-- página -->

## 5. BER e comparação com QPSK
A curva usou 6.000 símbolos por ponto, equivalentes a 24.000 bits. A aproximação Gray é Pb ≈ 0,75 Q(√(0,8 Eb/N₀)). Ela acompanha os resultados e permite comparar o custo energético de aumentar a quantidade de bits por símbolo.

![Figura 5. BER simulada e aproximação teórica da 16-QAM, com a QPSK como referência. Pontos sem erros estão registrados na tabela.](figuras/ber_16qam.png)

| Eb/N₀ | BER simulada | BER teórica aproximada |
|---|---|---|
| 0 dB | 0,141875 | 0,139160 |
| 4 dB | 0,059875 | 0,058618 |
| 6 dB | 0,029333 | 0,027871 |
| 8 dB | 0,009375 | 0,009247 |
| 10 dB | 0,001333 | 0,001754 |
| 12 dB | 0,0000417 | 0,0001387 |
| 14 dB | 0 | 0,00000276 |

A 12 dB foi contado um erro, enquanto a média prevista é de aproximadamente 3,33 erros em 24.000 bits. A 14 dB o número esperado cai para 0,066. A ausência de erros nessa amostra ainda permite um limite superior aproximado de 0,000125 para a BER, com 95% de confiança.

Para BER de 10⁻³, a 16-QAM exige aproximadamente 10,52 dB e a QPSK exige 6,79 dB. A diferença é 3,73 dB. A 16-QAM transmite quatro bits por símbolo, o dobro da QPSK. À mesma taxa de bits, a largura entre nulos cai pela metade.

<!-- página -->

## 6. Sensibilidade e conclusão
A ortogonalidade depende de a janela integrar ciclos completos do produto das bases, que oscila a 2fc. Por isso tanto 5 como 5,5 kHz preservaram a separação dos ramos. Um quarto de ciclo extra gerou projeção cruzada e deslocamento, mesmo sem ruído.

| Portadora | Produto interno inicial | Maior erro de coordenada |
|---|---|---|
| 5,00 e 5,50 kHz | ≈ 0 | ≈ 0 |
| 5,25 kHz | 0,0300 | 0,1051 |
| 40,50 kHz | ≈ 0 | ≈ 0 |
| 40,25 kHz | 0,0016 | 0,0197 |

Uma fase local positiva gira a constelação no sentido anti-horário. A 30 dB, as SER medidas foram zero a 5° e 10°, 0,5260 a 20° e 0,7327 a 30°. Os pontos de canto cruzam a primeira fronteira a cerca de 16,87°. No teste sem ruído dos 16 pontos, houve zero erro a 16° e quatro erros a 17°.

![Figura 6. Constelação recebida com erro de fase de 20° a 30 dB. A rotação atravessa as fronteiras fixas do decisor.](figuras/erro_fase_16qam.png)

Dobrar Rs amplia a largura entre nulos de 2 para 4 kHz. A BER teórica se mantém se Eb/N₀, a sincronização e a normalização forem preservados. Trocar Gray por binário natural aumenta a quantidade de bits errados por troca. A 6 dB, com os mesmos símbolos e ruído, a BER passou de 0,02933 para 0,03867.

Elevar E₀ de 1 para 4 dobra as distâncias físicas e quadruplica a energia. Com N₀ fixo, o ganho efetivo é de 6,02 dB. Os resultados mostram a relação entre eficiência espectral, energia e precisão do receptor.

Material de apoio utilizado nas análises: roteiro Atividade9_Lab_16QAM e Aula 12, Transmissão em banda passante - QAM. As respostas completas, os cálculos de conferência e o log de uso de IA estão no notebook executado.
