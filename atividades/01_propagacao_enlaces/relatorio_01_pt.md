# Atividade 1: Alcance e Perda de Percurso em Enlaces Sem Fio

**Transceptor escolhido:** Wi-Fi ESP32 (módulo **ESP32-WROOM-32**)

Este relatório estima até onde um enlace Wi-Fi baseado no ESP32-WROOM-32 consegue alcançar em
condição ideal — espaço livre, sem nenhum obstáculo — e mostra, na prática, o quanto esse alcance
encolhe quando o mesmo módulo é usado dentro de diferentes tipos de prédio. Para isso, usamos os
parâmetros reais do datasheet do fabricante e dois modelos de propagação: a equação de Friis
(espaço livre) e o modelo log-distância (ambientes indoor).

## 1. Datasheet e parâmetros

Para saber até onde um sinal de rádio chega, basta comparar duas coisas: o quanto o transmissor
consegue "falar alto" (potência de transmissão) e o quanto o receptor ainda consegue "ouvir baixo"
(sensibilidade). A diferença entre essas duas grandezas — descontados os ganhos de antena — é a
perda de percurso máxima que o enlace tolera antes do sinal ficar fraco demais para ser
decodificado.

**Fonte:** Espressif Systems, *ESP32-WROOM-32 Datasheet*, Tabela 17 "TX Power" e Tabela 19 "RX
Sensitivity". Link: [https://documentation.espressif.com/esp32-wroom-32_datasheet_en.pdf](https://documentation.espressif.com/esp32-wroom-32_datasheet_en.pdf) — cópia
local em `referencias/esp32-wroom-32_datasheet_en.pdf`.

| Símbolo            | Significado                                                                        | 802.11b, 1 Mbps                       | 802.11g, 54 Mbps |
| ------------------ | ---------------------------------------------------------------------------------- | ------------------------------------- | ---------------- |
| $P_{Tx}$ [dBm]     | Potência de transmissão                                                            | 19,5                                  | 14,0             |
| $S$ [dBm]          | Sensibilidade do receptor (menor sinal ainda decodificável)                        | −97,0                                 | −75,0            |
| $G_t$, $G_r$ [dBi] | Ganho das antenas Tx/Rx (PCB integrada, não especificado no datasheet → assumido¹) | 2                                     | 2                |
| $f$ [MHz]          | Frequência de operação                                                             | 2437 (canal 6, meio de 2412–2484 MHz) | idem             |

¹ Conforme permitido pelo enunciado (antena integrada, datasheet omisso): $G_t = G_r = 2\ \text{dBi}$, dentro da faixa 0–3 dBi sugerida.

Além desses parâmetros, as seguintes variáveis aparecem nos cálculos das próximas seções:

- $PL_{max}$ [dB] — perda de percurso máxima que o enlace tolera sem que o sinal caia abaixo de $S$;
- $d$ — alcance do enlace (em km no espaço livre, em m nos cenários indoor);
- $d_0 = 1\ \text{m}$ — distância de referência do modelo log-distância;
- $PL(d_0)$ [dB] — perda de referência em $d_0$, aqui igual à $FSPL$ em 1 m na frequência do módulo;
- $n$ — expoente de perda de percurso: descreve o quão rápido o sinal enfraquece com a distância em cada tipo de ambiente (quanto maior, mais rápido a perda cresce);
- $\sigma$ [dB] — desvio-padrão do *shadowing*, a variação aleatória do sinal em torno do valor médio previsto pelo modelo.

O ESP32-WROOM-32 reduz $P_{Tx}$ e piora $S$ à medida que a taxa de transmissão aumenta: em
1 Mbps ele usa uma modulação simples e robusta (DSSS), enquanto em 54 Mbps usa OFDM com 64-QAM nas subportadoras, que carrega mais bits por símbolo mas exige um sinal bem mais forte para ser
decodificada corretamente. É a troca clássica entre velocidade e alcance no Wi-Fi — por isso essas
duas taxas foram escolhidas para representar, respectivamente, o melhor e o pior caso de alcance
do módulo.

## 2. Alcance em espaço livre (LOS)

O primeiro passo é descobrir o orçamento de perdas ($PL_{max}$) disponível em cada taxa — ou seja,
quanto o sinal pode se atenuar no caminho antes de ficar abaixo da sensibilidade do receptor:

$$
PL_{max}[\text{dB}] = P_{Tx} + G_t + G_r - S
\qquad\Rightarrow\qquad
\begin{aligned}
PL_{max}^{1\text{Mbps}} &= 19{,}5+2+2-(-97{,}0) = 120{,}50\ \text{dB}
PL_{max}^{54\text{Mbps}} &= 14{,}0+2+2-(-75{,}0) = 93{,}00\ \text{dB}
\end{aligned}
$$

Com esse valor em mãos, usamos a equação de Friis / FSPL para descobrir a que distância essa perda
é atingida — isolando $d$, encontramos o alcance máximo em visada direta, sem obstáculos:

$$
FSPL(d)[\text{dB}] = 32{,}44 + 20\log_{10}(f_{\text{MHz}}) + 20\log_{10}(d_{\text{km}})
\Rightarrow
d_{\text{km}} = 10^{\frac{PL_{max} - 32{,}44 - 20\log_{10}(f_{\text{MHz}})}{20}}
$$

$$
\begin{aligned}
d^{1\text{Mbps}}*{\text{km}} &= 10^{\frac{120{,}50 - 32{,}44 - 20\log*{10}(2437)}{20}} = 10{,}38\ \text{km} \approx 10379\ \text{m}
d^{54\text{Mbps}}*{\text{km}} &= 10^{\frac{93{,}00 - 32{,}44 - 20\log*{10}(2437)}{20}} = 0{,}438\ \text{km} \approx 438\ \text{m}
\end{aligned}
$$

**Em outras palavras:** os $27{,}5\ \text{dB}$ de diferença de $PL_{max}$ entre as duas taxas
($5{,}5\ \text{dB}$ vindos de $P_{Tx}$ e $22\ \text{dB}$ vindos de $S$) parecem pouco, mas cortam o
alcance em quase 24 vezes (de 10,38 km para 0,44 km). Isso acontece porque $d \propto 10^{PL_{max}/20}$: a distância cresce **exponencialmente** com o orçamento de perdas, já que a
$FSPL$ só cresce 20 dB a cada vez que a distância multiplica por 10. Ou seja: pequenas variações na
sensibilidade do receptor têm um efeito desproporcional no alcance final.

## 3. Perda de percurso indoor

Dentro de um prédio, o sinal não se propaga mais como no espaço livre: paredes, móveis, estruturas
metálicas e pessoas fazem a potência cair mais rápido com a distância. O modelo log-distância
descreve esse efeito através do expoente $n$ — quanto maior o $n$ de um ambiente, mais rápido o
sinal perde força a cada metro percorrido:

$$
PL(d)[\text{dB}] = PL(d_0) + 10n\log_{10}\left(\frac{d}{d_0}\right) + X_\sigma,
\qquad
PL(d_0) = 32{,}44 + 20\log_{10}(2437) + 20\log_{10}(0{,}001) = 40{,}18\ \text{dB}
$$

Usando o mesmo $PL_{max}$ calculado para a condição de potência máxima (802.11b, 1 Mbps,
$120{,}50$ dB) e isolando $d$ (com $\sigma$ desprezado, conforme permitido pelo enunciado),
calculamos o alcance nominal em 4 cenários da tabela do enunciado — dois escritórios e duas
fábricas, incluindo um caso com visada direta (LOS) e outro obstruído (OBS):

$$
d = d_0\cdot 10^{\frac{PL_{max}-PL(d_0)}{10n}}
\Rightarrow
\begin{aligned}
d_{\text{escrit. suave}} &= 10^{\frac{120{,}50-40{,}18}{10\cdot 2{,}4}} = 2222\ \text{m} & (n=2{,}4,\ \sigma=9{,}6\text{ dB})
d_{\text{escrit. severo}} &= 10^{\frac{120{,}50-40{,}18}{10\cdot 3{,}0}} = 476\ \text{m} & (n=3{,}0,\ \sigma=7{,}0\text{ dB})
d_{\text{fábrica LOS}} &= 10^{\frac{120{,}50-40{,}18}{10\cdot 2{,}0}} = 10379\ \text{m} & (n=2{,}0,\ \sigma=3{,}0\text{ dB})
d_{\text{fábrica OBS}} &= 10^{\frac{120{,}50-40{,}18}{10\cdot 3{,}3}} = 272\ \text{m} & (n=3{,}3,\ \sigma=6{,}8\text{ dB})
\end{aligned}
$$

## Tabela-resumo final

| Cenário                                 | Distância / Perda calculada                 | Observações                               |
| --------------------------------------- | ------------------------------------------- | ----------------------------------------- |
| Espaço livre (FSPL) — potência máxima   | **10,38 km** ($PL_{max}=120{,}50$ dB)       | 802.11b, 1 Mbps; melhor caso $P_{Tx}$/$S$ |
| Indoor — Escritório (obstrução suave)   | **2222 m** ($n=2{,}4$, $\sigma=9{,}6$ dB)   | ≈ 4,7× menor que o espaço livre           |
| Indoor — Escritório (obstrução severa)  | **476 m** ($n=3{,}0$, $\sigma=7{,}0$ dB)    | ≈ 22× menor que o espaço livre            |
| Indoor — Fábrica (LOS — Têxtil/Química) | **10 379 m** ($n=2{,}0$, $\sigma=3{,}0$ dB) | $n\approx 2$ ⇒ ≈ igual ao espaço livre    |
| Indoor — Fábrica (OBS — Metalurgia)     | **272 m** ($n=3{,}3$, $\sigma=6{,}8$ dB)    | menor alcance; maior $n$ do conjunto      |

## 4. Discussão

**Espaço livre × indoor.** O alcance em espaço livre (10,38 km) supera os cenários indoor
obstruídos (272–476 m) em até ~38 vezes. A explicação está no expoente $n$: em ambientes com
paredes, divisórias e estruturas metálicas, $n$ é sempre maior que 2 (o valor de referência do
espaço livre), e como $d\propto 10^{PL_{max}/(10n)}$, mesmo um pequeno aumento de $n$ já corta o
alcance de forma exponencial. Já a fábrica LOS ($n=2{,}0$) resultou num alcance praticamente igual
ao do espaço livre — o que faz sentido, já que seu expoente de perda coincide com o da propagação
sem obstáculos. Isso mostra que, em ambientes bem "abertos" (como um galpão grande, com pouca
obstrução entre transmissor e receptor), o modelo log-distância converge para o próprio $FSPL$.

**Cenário de menor alcance.** A **Fábrica OBS — Metalurgia** ($n=3{,}3$) apresentou o menor alcance
do conjunto (272 m), seguida de perto pelo Escritório com obstrução severa ($n=3{,}0$, 476 m). Faz
sentido fisicamente: metalurgia com obstrução (OBS) é o ambiente com maior densidade de estruturas
metálicas do conjunto, o que causa mais reflexão, absorção e difração do sinal do que um cenário
LOS ou um escritório mais leve — exatamente o comportamento esperado de um $n$ que cresce junto com
a "severidade" do ambiente.

**O papel de $\sigma$ e a margem de desvanecimento.** $\sigma$ é o desvio-padrão, em dB, de uma
variável aleatória gaussiana somada ao modelo log-distância — representa o *shadowing*, as
variações que o modelo determinístico não prevê sozinho, causadas por fatores como móveis, pessoas
circulando ou portas abertas/fechadas. Um $\sigma$ pequeno indica um modelo previsível; um $\sigma$
grande (ex.: 14,1 dB em escritórios a 1900 MHz) indica bastante variabilidade ponto a ponto. Ou
seja, o alcance calculado corresponde ao modelo mediano em dB — em um "dia ruim" (mais pessoas, causando desvanecimento
adicional tipo Rayleigh/Rician), o sinal pode estar mais fraco que o previsto. Por isso, para
projetar com mais segurança, reserva-se uma **margem de desvanecimento** ($M$) proporcional a
$\sigma$ antes de calcular o alcance:

$$
PL_{max}^{\text{projeto}} = PL_{max} - M, \qquad M \approx 1\ \text{a}\ 2\sigma
$$

Isso reduz um pouco o alcance de projeto, e aumenta a probabilidade de atendimento ao limiar. Uma margem finita corresponde a uma probabilidade de indisponibilidade, e não a uma garantia absoluta. *(Cálculos gerados e conferidos
com o script* `[calculo_link_budget.py](calculo_link_budget.py)`*.)*

Os alcances são limites dos modelos com margem zero e ganhos de antena assumidos. Os valores indoor extrapolam o ambiente de aplicação e não representam cobertura medida.
