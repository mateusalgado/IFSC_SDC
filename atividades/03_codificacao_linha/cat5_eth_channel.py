

"""
cat5_eth_channel.py
----------------
Modelo de canal (cabo CAT5/CAT5e) baseado na curva real de Insertion Loss (IL)
do datasheet, em dB por 100 m.

Fonte dos dados: MPTcable, "Cabo LAN CAT 5e U/UTP 4p x 24AWG - LSZH-3",
DTM 0027/19, Revisão 10, 01/09/2024 (tabela "Características Elétricas e de
Transmissão", coluna Insertion Loss [dB/100m]).

Observação importante sobre extrapolação: o datasheet declara transmissão
"verificada até 100 MHz" (é um cabo CAT5e, não CAT6/CAT6a) — acima de 100 MHz
não há garantia do fabricante, e a extrapolação analítica abaixo é uma
estimativa, não um dado de catálogo. Se o sinal do aluno não tiver energia
relevante acima de 100 MHz, essa extrapolação nem chega a ser usada.

Como usar
---------
1) Substitua os vetores `freq_MHz` e `IL_dB_100m` abaixo pelos valores EXATOS
   da tabela do seu datasheet (frequência em MHz vs. IL em dB/100 m).
2) Chame `cat5_channel(sinal, fs, length_m)` passando o seu sinal já
   codificado em linha (NRZ, Manchester, etc.), a taxa de amostragem usada
   para gerar esse sinal, e o comprimento do cabo que quer emular.

Observação sobre extrapolação
------------------------------
Datasheets normalmente tabelam IL só até uma frequência máxima (ex.: 100 MHz
para CAT5e). Se fs/2 do seu sinal for maior que isso, o módulo extrapola
usando o modelo analítico padrão (TIA/EIA):

    IL(f) = a*sqrt(f) + b*f + c/sqrt(f)      [dB/100 m, f em MHz]

ajustado por mínimos quadrados aos próprios pontos do datasheet — em vez de
simplesmente repetir o último valor tabelado (o que subestimaria a perda em
frequências mais altas).
"""

import numpy as np
from scipy.signal import firwin2, lfilter, freqz


# ---------------------------------------------------------------------
# 1) Tabela de Insertion Loss extraída do datasheet
# ---------------------------------------------------------------------
# Fonte: MPTcable DTM 0027/19 (CAT5e U/UTP 4p x 24AWG - LSZH-3), rev. 10,
# 01/09/2024 — coluna "Insertion Loss [dB/100m]". Se for usar outro cabo,
# troque os dois vetores abaixo pelos valores do datasheet correspondente.
freq_MHz    = np.array([1.0, 4.0, 8.0, 10.0, 16.0, 20.0, 25.0, 31.25, 62.5, 100.0])
IL_dB_100m  = np.array([2.0, 4.1, 5.8,  6.5,  8.2,  9.3, 10.4,  11.7, 17.0,  22.0])

# Atraso de propagação (também do datasheet) — não usado no filtro de
# magnitude abaixo, mas fica disponível caso queira estender o modelo com
# dispersão (atraso de grupo variável com a frequência), em vez do FIR de
# fase linear (atraso constante) usado atualmente.
propag_delay_freq_MHz = np.array([1.0, 10.0, 100.0])
propag_delay_ns_100m  = np.array([570.0, 545.0, 538.0])


# ---------------------------------------------------------------------
# 2) Ajuste do modelo analítico (para extrapolar além da tabela)
# ---------------------------------------------------------------------
def _fit_il_formula(freq_MHz, IL_dB_100m):
    """Ajusta a*sqrt(f) + b*f + c/sqrt(f) aos pontos do datasheet
    por mínimos quadrados. Retorna (a, b, c)."""
    f = freq_MHz
    A = np.column_stack([np.sqrt(f), f, 1.0 / np.sqrt(f)])
    coef, *_ = np.linalg.lstsq(A, IL_dB_100m, rcond=None)
    return coef  # a, b, c


_a, _b, _c = _fit_il_formula(freq_MHz, IL_dB_100m)


def il_formula_dB_100m(f_MHz):
    """Modelo analítico contínuo de IL (dB/100 m), ajustado aos pontos
    do datasheet. Usado sobretudo para extrapolar acima da última
    frequência tabelada."""
    f_MHz = np.maximum(f_MHz, 1e-6)  # evita divisão por zero em f=0
    return _a * np.sqrt(f_MHz) + _b * f_MHz + _c / np.sqrt(f_MHz)


# ---------------------------------------------------------------------
# 3) Curva de IL efetiva (dados tabelados + extrapolação) e escala por comprimento
# ---------------------------------------------------------------------
def cat5_insertion_loss_dB(f_Hz, length_m=100.0):
    """
    Retorna a atenuação (IL) em dB, positiva, para cada frequência em f_Hz,
    já escalada para o comprimento 'length_m' do cabo.

    - Dentro da faixa tabelada: interpolação linear entre os pontos do datasheet.
    - Acima da última frequência tabelada: modelo analítico ajustado.
    - Em f = 0 (DC): atenuação = 0 dB (o cabo não atenua nível DC).
    """
    f_MHz = np.abs(np.asarray(f_Hz, dtype=float)) / 1e6

    IL_100 = np.interp(f_MHz, freq_MHz, IL_dB_100m)

    acima = f_MHz > freq_MHz[-1]
    if np.any(acima):
        IL_100[acima] = il_formula_dB_100m(f_MHz[acima])

    IL_100[f_MHz < 1e-9] = 0.0  # DC sem perda

    return IL_100 * (length_m / 100.0)


# ---------------------------------------------------------------------
# 4) Projeto do filtro FIR por amostragem em frequência (firwin2)
# ---------------------------------------------------------------------
def design_cat5_filter(fs, length_m=100.0, numtaps=513):
    """
    Projeta um FIR (fase linear, causal) cuja resposta em magnitude
    reproduz a curva de Insertion Loss do datasheet, escalada para
    'length_m' metros de cabo.

    Parameters
    ----------
    fs        : taxa de amostragem do sinal (Hz)
    length_m  : comprimento do cabo a emular (m)
    numtaps   : ordem do FIR (ímpar recomendado; mais taps = melhor
                aderência à curva do datasheet, à custa de mais atraso
                de grupo, ~ (numtaps-1)/2 amostras)

    Returns
    -------
    b : coeficientes do FIR (use com scipy.signal.lfilter ou np.convolve)
    """
    freqs_norm = np.linspace(0, 1, numtaps)  # 0 .. Nyquist normalizado (1 = fs/2)
    f_Hz = freqs_norm * (fs / 2.0)

    IL_dB = cat5_insertion_loss_dB(f_Hz, length_m)
    gain = 10 ** (-IL_dB / 20.0)
    gain[0] = 1.0  # garante ganho unitário em DC

    b = firwin2(numtaps, freqs_norm, gain)
    return b


# ---------------------------------------------------------------------
# 5) Função principal: aplica o "cabo" ao sinal do aluno
# ---------------------------------------------------------------------
def cat5_channel(signal, fs, length_m=100.0, numtaps=513):
    """
    Emula a passagem do sinal (já codificado em linha) por 'length_m'
    metros de cabo CAT5, usando a curva de IL do datasheet.

    Parameters
    ----------
    signal    : array 1D com o sinal codificado em linha (ex.: NRZ, Manchester)
    fs        : taxa de amostragem usada para gerar 'signal' (Hz)
    length_m  : comprimento do cabo a emular (m)
    numtaps   : ordem do FIR interno (ver design_cat5_filter)

    Returns
    -------
    y : sinal filtrado (mesmo comprimento de 'signal', devido ao lfilter;
        note que há um atraso de grupo de ~(numtaps-1)/2 amostras a
        compensar se for comparar y com o sinal original amostra a amostra)
    """
    b = design_cat5_filter(fs, length_m, numtaps)
    y = lfilter(b, [1.0], signal)
    return y

# ---------------------------------------------------------------------
# 6) Verificação: compara a resposta do filtro projetado com os pontos do datasheet
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    fs = 500e6
    length_m = 100.0
    numtaps = 513

    b = design_cat5_filter(fs, length_m, numtaps)

    # Resposta em frequência
    w, h = freqz(b, [1.0], worN=8192, fs=fs)

    # Magnitude do canal em dB
    ganho_dB = 20 * np.log10(np.abs(h) + 1e-12)

    # -----------------------------------------------------------------
    # Curva contínua baseada diretamente no modelo do cabo
    # -----------------------------------------------------------------
    f_plot_MHz = np.logspace(
        np.log10(1.0),
        np.log10(fs / 2 / 1e6),
        1000
    )

    IL_plot = cat5_insertion_loss_dB(
        f_plot_MHz * 1e6,
        length_m
    )

    ganho_cabo_dB = -IL_plot

    # -----------------------------------------------------------------
    # Gráfico
    # -----------------------------------------------------------------
    plt.figure(figsize=(9, 5.5))

    # Resposta do FIR
    plt.plot(
        w / 1e6,
        ganho_dB,
        label="Filtro FIR"
    )

    # Curva ideal desejada do canal
    plt.plot(
        f_plot_MHz,
        ganho_cabo_dB,
        "--",
        linewidth=2,
        label="Modelo do cabo"
    )

    # Pontos do datasheet
    plt.plot(
        freq_MHz,
        -IL_dB_100m * (length_m / 100.0),
        "o",
        markersize=6,
        label="Datasheet"
    )

    # Linha de referência de -3 dB
    plt.axhline(
        -3,
        linestyle=":",
        linewidth=1,
        label="-3 dB"
    )

    plt.xscale("log")
    plt.xlim(1, fs / 2 / 1e6)

    plt.xlabel("Frequência (MHz)")
    plt.ylabel("Ganho do canal (dB)")
    plt.title(f"Resposta em frequência do cabo CAT5e — {length_m:.0f} m")

    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        "resposta_filtro_cat5.png",
        dpi=150
    )

    plt.show()

    print(
        "Filtro projetado com",
        numtaps,
        "taps."
    )



