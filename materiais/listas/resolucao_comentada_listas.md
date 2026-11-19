# Resolucao comentada das listas: banda base e banda passante

Este guia resolve as questoes das duas listas da disciplina e explica os conceitos usados em cada etapa. Os enunciados sao das listas de [Banda Base](Lista_Banda_Base.pdf) e [Banda Passante](Lista_Banda_Passante.pdf).

## Convencoes e formulas de referencia

### Parametros digitais

- $R_b$: taxa de bits, em bit/s.
- $R_s$: taxa de simbolos, em simbolos/s ou baud.
- $M$: numero de simbolos da constelacao.
- $k=\log_2(M)$: bits transportados por simbolo.
- $R_s=R_b/k$ e $T_s=1/R_s$.
- Para amostragem de voz, a taxa binaria e a taxa de amostragem multiplicada pelo numero de bits por amostra.

Para pulsos cosseno levantado, usando largura unilateral em banda base e largura total em banda passante:

$$
B_{BB}=\frac{(1+\alpha)R_s}{2},
\qquad
B_{BP}=(1+\alpha)R_s.
$$

Em banda passante, o espectro centrado em $f_c$ vai de $f_c-B_{BP}/2$ ate $f_c+B_{BP}/2$. Quando se pede a menor largura de banda possivel, usa-se $\alpha=0$, salvo indicacao diferente.

### Ruido e probabilidade de erro

Converta dB para escala linear antes de aplicar uma formula:

$$
\gamma_{dB}=10\log_{10}(\gamma),
\qquad
\gamma=10^{\gamma_{dB}/10}.
$$

A funcao $Q$ e a cauda da distribuicao normal padrao:

$$
Q(x)=\frac{1}{\sqrt{2\pi}}\int_x^{\infty}e^{-u^2/2}\,du
=\frac{1}{2}\operatorname{erfc}\!\left(\frac{x}{\sqrt{2}}\right).
$$

Formulas coerentes em AWGN:

- OOK/BASK unipolar: $P_b=Q\!\left(\sqrt{E_b/N_0}\right)$.
- BPSK e QPSK: $P_b=Q\!\left(\sqrt{2E_b/N_0}\right)$.
- BFSK ortogonal: $P_b=Q\!\left(\sqrt{E_b/N_0}\right)$.

Para M-PAM, a aproximacao para erro de simbolo e:

$$
P_s\approx\frac{2(M-1)}{M}
Q\!\left(\sqrt{\frac{6}{M^2-1}\frac{E_s}{N_0}}\right).
$$

Para M-PSK e M-QAM quadrada com mapeamento Gray, usaremos aproximacoes usuais em BER baixa:

$$
P_b^{M\text{-PSK}}\approx\frac{2}{\log_2 M}
Q\!\left(\sqrt{2\log_2(M)\frac{E_b}{N_0}}\sin\frac{\pi}{M}\right),
$$

$$
P_b^{M\text{-QAM}}\approx\frac{4}{\log_2 M}\left(1-\frac{1}{\sqrt M}\right)
Q\!\left(\sqrt{\frac{3\log_2 M}{M-1}\frac{E_b}{N_0}}\right).
$$

Essas expressoes sao aproximadas. Em respostas de prova, indique a hipotese de AWGN, deteccao coerente e, quando aplicavel, codificacao Gray.

## Lista de Banda Base

### Questao 1: comparar BER de NRZ unipolar e RZ bipolar

**Conceito.** A energia media por bit nao e a mesma coisa que a amplitude. Para a mesma razao $E_b/N_0$, sinais antipodais (polar/bipolar) tem maior distancia entre as hipoteses do que OOK unipolar e, portanto, menor BER.

Converta a razao recebida:

$$
\frac{E_b}{N_0}=10^{15/10}=31.62.
$$

Para NRZ unipolar/OOK:

$$
P_b=Q(\sqrt{31.62})\approx9.36\times10^{-9}.
$$

Para RZ bipolar antipodal:

$$
P_b=Q(\sqrt{2\cdot31.62})\approx9.12\times10^{-16}.
$$

**Resposta:** a codificacao bipolar tem BER menor para o mesmo $E_b/N_0$.

### Questao 2: energia, amplitude e limiar para OOK

Dados: BER maxima $10^{-5}$, NRZ unipolar, $N_0=-60$ dBW/Hz e $R_b=1$ Mbps.

**Conceito.** O sinal OOK representa 1 por um pulso de amplitude $A$ e 0 por ausencia de pulso. Para bits equiprovaveis, a energia media por bit e $E_b=A^2T_b/2$. O receptor otimo compara a amostra com o ponto medio entre as duas hipoteses.

Primeiro, converta a densidade de ruido:

$$
N_0=10^{-60/10}=10^{-6}\text{ W/Hz}.
$$

Para OOK, $P_b=Q(\sqrt{E_b/N_0})$. Como $Q^{-1}(10^{-5})\approx4.2649$:

$$
\frac{E_b}{N_0}=4.2649^2\approx18.189,
\qquad
E_{b,\min}=18.189\cdot10^{-6}=1.819\times10^{-5}\text{ J}.
$$

A potencia media e $P=E_bR_b$:

$$
P_{\min}=1.819\times10^{-5}\cdot10^6\approx18.19\text{ W}.
$$

Como $T_b=1/R_b=1\,\mu$s e $E_b=A^2T_b/2$:

$$
A_{\min}=\sqrt{\frac{2E_b}{T_b}}\approx6.03\text{ V}.
$$

O limiar na amostra direta e $A/2\approx3.02$ V. Se o receptor for descrito pela saida do correlator casado, o limiar equivalente e $A^2T_b/2$.

### Questoes 3 e 4: banda e erro de simbolo para M-PAM

Dados: voz amostrada a 8 kHz, 8 bits por amostra.

**Conceito.** M-PAM agrupa $k=\log_2M$ bits em cada amplitude. Mais niveis reduzem a taxa de simbolos necessaria e a banda, mas aproximam os niveis e elevam a probabilidade de erro.

A taxa binaria da fonte e:

$$
R_b=8\,000\cdot8=64\text{ kbps}.
$$

Com rolloff minimo, $\alpha=0$, temos $R_s=R_b/\log_2M$ e $B=R_s/2$:

- 4-PAM: $R_s=32$ kbaud, $B_{\min}=16$ kHz.
- 8-PAM: $R_s=21.33$ kbaud, $B_{\min}=10.67$ kHz.
- 16-PAM: $R_s=16$ kbaud, $B_{\min}=8$ kHz.

Para a questao 4, $E_s/N_0=30$ dB $=1000$. Aplicando a formula de M-PAM:

- 4-PAM: $P_s\approx1.5Q(20)\approx4.13\times10^{-89}$.
- 8-PAM: $P_s\approx1.75Q(9.759)\approx1.48\times10^{-22}$.
- 16-PAM: $P_s\approx1.875Q(4.851)\approx1.15\times10^{-6}$.

**Conclusao:** 16-PAM usa menos banda, mas tem a maior probabilidade de erro entre as tres para o mesmo $E_s/N_0$.

### Questao 5: rolloff maximo para 4-PAM

Dados: $R_b=1$ Mbps e canal com $B=200$ kHz.

4-PAM leva $\log_2 4=2$ bits por simbolo:

$$
R_s=\frac{1\text{ Mbps}}{2}=500\text{ kbaud}.
$$

Pela relacao de banda base $B=(1+\alpha)R_s/2$:

$$
\alpha=\frac{2B}{R_s}-1
=\frac{2\cdot200}{500}-1=-0.2.
$$

Um rolloff negativo nao e realizavel. Mesmo com $\alpha=0$, a banda minima e $250$ kHz.

**Resposta:** nao existe rolloff que permita transmitir a taxa solicitada nesse canal com 4-PAM.

### Questao 6: comparar dois transmissores PAM

**Conceito.** A taxa de bits e o produto da taxa de simbolos pelo numero de bits por simbolo. Para cosseno levantado em banda base, $B=(1+\alpha)R_s/2$.

Transmissor A: 16 niveis, $T_s=1.5\,\mu$s.

$$
R_{s,A}=\frac{1}{1.5\,\mu s}=666.7\text{ kbaud},
\qquad
R_{b,A}=4R_{s,A}=2.667\text{ Mbps}.
$$

Transmissor B: 4 niveis, $T_s=1\,\mu$s.

$$
R_{s,B}=1\text{ Mbaud},
\qquad
R_{b,B}=2R_{s,B}=2\text{ Mbps}.
$$

**(a)** O transmissor A tem maior taxa de bits.

**(b)** Para $B=600$ kHz:

$$
\alpha_A=\frac{2B}{R_{s,A}}-1=0.8,
\qquad
\alpha_B=\frac{2B}{R_{s,B}}-1=0.2.
$$

**(c)** Com $\alpha=1$, $B=R_s$. Assim, $\eta_A=R_{b,A}/R_{s,A}=4$ bit/s/Hz e $\eta_B=R_{b,B}/R_{s,B}=2$ bit/s/Hz.

## Lista de Banda Passante

### Questao 1: potencia de transmissao para BPSK

Dados: $N_0=10^{-10}$ W/Hz, $R_b=1$ kbps e $P_b=10^{-5}$.

**Conceito.** BPSK e uma sinalizacao antipodal. A sua BER coerente e $P_b=Q(\sqrt{2E_b/N_0})$.

Como $Q^{-1}(10^{-5})\approx4.2649$:

$$
\frac{E_b}{N_0}=\frac{4.2649^2}{2}\approx9.095,
\qquad
E_b=9.095\cdot10^{-10}\text{ J}.
$$

A potencia media e $P=E_bR_b$:

$$
P\approx9.095\times10^{-10}\cdot10^3
=9.095\times10^{-7}\text{ W}.
$$

### Questao 2: banda e requisito de BER para BPSK

Dados: $R_b=1$ Mbps, $\alpha=0.25$, $f_c=2$ MHz e BER maxima $10^{-6}$.

**(a)** BPSK transmite um bit por simbolo, entao $R_s=R_b$. A banda total e:

$$
B=(1+\alpha)R_s=1.25\text{ MHz}.
$$

**(b)** A banda e centrada em $f_c$, logo:

$$
f_{\min}=2-\frac{1.25}{2}=1.375\text{ MHz},
\qquad
f_{\max}=2+\frac{1.25}{2}=2.625\text{ MHz}.
$$

**(c)** Para BPSK, $E_b/N_0=[Q^{-1}(10^{-6})]^2/2$:

$$
\frac{E_b}{N_0}\approx11.30=10.53\text{ dB}.
$$

### Questao 3: distancia maxima de um enlace QPSK

Dados: potencia $P=10$ W, duracao de simbolo $T_s=1$ ms, $N_0=10^{-6}$ W/Hz e perda de 10 dB/km.

**Conceito.** QPSK leva dois bits por simbolo, portanto $E_b=E_s/2$. A atenuacao reduz a energia recebida e, com ela, $E_b/N_0$.

Energia por simbolo e por bit antes da perda:

$$
E_s=PT_s=10\cdot10^{-3}=0.01\text{ J},
\qquad
E_b=\frac{E_s}{2}=0.005\text{ J}.
$$

A relacao inicial e $E_b/N_0=0.005/10^{-6}=5000$. Para BER $10^{-6}$, QPSK exige aproximadamente $E_b/N_0=11.30$. A margem de perda permitida e:

$$
L_{\max}=10\log_{10}\left(\frac{5000}{11.30}\right)
\approx26.46\text{ dB}.
$$

Com 10 dB/km, a distancia maxima e:

$$
d_{\max}=\frac{26.46}{10}\approx2.65\text{ km}.
$$

### Questao 4: escolher QPSK ou 8-PSK

Dados: $R_b=130$ kbps e canal de 80 kHz.

**Conceito.** A modulacao de ordem maior carrega mais bits por simbolo e reduz a taxa de simbolos, mas diminui a distancia entre simbolos e piora a BER para a mesma qualidade de canal.

Para QPSK, $k=2$:

$$
R_s=65\text{ kbaud},
\qquad
\alpha=\frac{80}{65}-1\approx0.231.
$$

Para 8-PSK, $k=3$:

$$
R_s=43.33\text{ kbaud},
\qquad
\alpha=\frac{80}{43.33}-1\approx0.846.
$$

Ambas cabem no canal com os rolloffs calculados. Para uma mesma $E_b/N_0$, QPSK tem maior distancia angular entre simbolos e menor BER.

**Resposta:** escolha QPSK se a prioridade for menor probabilidade de erro.

### Questao 5: estimar a BER e $E_b/N_0$ de 8-PSK

Dados: $R_b=300$ kbps; em 10 minutos, 10 simbolos foram detectados incorretamente.

**(a)** 8-PSK leva 3 bits por simbolo:

$$
R_s=\frac{300\text{ kbps}}{3}=100\text{ kbaud},
\qquad
T_s=\frac{1}{R_s}=10\,\mu s.
$$

**(b)** Em 600 segundos, o total transmitido e $100\,000\cdot600=60\,000\,000$ simbolos:

$$
P_s\approx\frac{10}{60\,000\,000}=1.667\times10^{-7}.
$$

**(c)** Com Gray, uma aproximacao e $P_b\approx P_s/\log_2 8$:

$$
P_b\approx5.556\times10^{-8}.
$$

**(d)** Usando a aproximacao M-PSK, $Q(x)=P_b\log_2(M)/2=P_s/2$. Assim, $x=Q^{-1}(8.333\times10^{-8})\approx5.233$ e:

$$
\frac{E_b}{N_0}
=\frac{x^2}{2\log_2(8)\sin^2(\pi/8)}
\approx31.17
\approx14.94\text{ dB}.
$$

E uma estimativa: a contagem de simbolos errados nao revela quantos bits erraram em cada simbolo.

### Questao 6: maximizar a taxa usando M-PSK ou M-QAM

Dados: $E_b/N_0=20$ dB $=100$, banda 500 kHz e $\alpha=0$.

**Conceito.** Com rolloff zero, $R_s=B$ na convencao passante usada nesta lista. Logo $R_b=B\log_2M$. Procura-se o maior $M$ cuja BER calculada nao ultrapasse $10^{-5}$.

Para M-PSK, a aproximacao Gray indica que 16-PSK atende ($P_b\approx8.57\times10^{-9}$), mas 32-PSK nao atende ($P_b\approx3.88\times10^{-4}$). Portanto:

$$
R_{b,\max}^{M\text{-PSK}}=500\text{ kHz}\cdot4=2\text{ Mbps}.
$$

Para M-QAM quadrada, 64-QAM atende ($P_b\approx2.63\times10^{-8}$), mas 256-QAM nao atende ($P_b\approx5.05\times10^{-4}$). Portanto:

$$
R_{b,\max}^{M\text{-QAM}}=500\text{ kHz}\cdot6=3\text{ Mbps}.
$$

**Resposta:** escolha 64-QAM, com taxa maxima aproximada de 3 Mbps.

### Questao 7: maximizar taxa no canal de 915 a 925 MHz

Dados: BER maxima $10^{-6}$, rolloff unitario e $E_s/N_0=20$ dB $=100$.

**Conceito.** A portadora fica no centro da faixa. O rolloff determina a taxa de simbolos possivel; a BER determina a maior constelacao aceitavel.

$$
f_c=\frac{915+925}{2}=920\text{ MHz},
\qquad
B=10\text{ MHz},
\qquad
R_s=\frac{B}{1+\alpha}=5\text{ Mbaud}.
$$

8-PSK tem $E_b/N_0=E_s/(3N_0)=100/3$. Sua BER aproximada e:

$$
P_b\approx\frac{2}{3}Q\!\left(\sqrt{200}\sin\frac{\pi}{8}\right)
\approx2.08\times10^{-8}.
$$

Ela atende ao limite e fornece $R_b=3R_s=15$ Mbps. 16-PSK ultrapassa o limite de BER. 16-QAM tambem nao atende: sua BER aproximada e $2.90\times10^{-6}$.

**Resposta:** use 8-PSK, portadora em 920 MHz, taxa de 15 Mbps e BER aproximada de $2.08\times10^{-8}$.

### Questao 8: avaliar a afirmacao sobre FSK

A afirmacao de que FSK deve ser escolhida para obter simultaneamente alta robustez ao ruido e alta eficiencia espectral e **falsa**.

FSK pode ser robusta, especialmente quando se usa deteccao nao coerente ou quando a amplitude do sinal varia. Porem, os tons precisam ser separados e a largura de banda cresce com o numero de frequencias. Por isso, M-FSK costuma ter baixa eficiencia espectral. PSK e QAM aproveitam melhor a banda, mas constelacoes de ordem alta ficam mais sensiveis ao ruido.

## Resumo dos conceitos por modulacao

- **ASK:** carrega informacao na amplitude da portadora. OOK e um caso especial; e simples, mas sensivel a variacoes de amplitude e ruido.
- **FSK:** carrega informacao na frequencia. A ortogonalidade dos tons facilita a deteccao, mas normalmente custa mais banda.
- **M-PSK:** carrega varios bits por simbolo mudando a fase. Boa eficiencia espectral; aumentar $M$ reduz a distancia angular e piora a robustez.
- **M-QAM:** muda amplitude e fase, representadas como pontos no plano I-Q. Constelacoes quadradas de ordem alta oferecem alta eficiencia espectral, mas precisam de maior SNR.
- **BPSK/QPSK:** sao particularmente eficientes em energia; QPSK transporta dois bits por simbolo sem perder a BER ideal de BPSK para a mesma energia por bit.

## Observacoes sobre os materiais das atividades

- O relatorio da [Atividade 3](../Atividade3/relatorio_atividade3.md) associa os nulos do Manchester a multiplos de $R_b$. O slide da Aula 4 indica primeiro nulo em $2R_b$.
- No relatorio da [Atividade 4](../Atividade4/relatorio_atividade4.md), para $M=89$, as formulas do roteiro fornecem $f_c=9900$ Hz e $A=7$ V. Algumas contas do relatorio usam $A=5$ V, portanto aqueles resultados numericos nao devem ser memorizados sem conferir os parametros.
- A BFSK deve ser ortogonal para que a formula teorica usual $P_b=Q(\sqrt{E_b/N_0})$ se aplique diretamente. O espacamento inadequado entre tons pode degradar o desempenho.