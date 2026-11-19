"""
microstrip_antenna.py
======================

Biblioteca Python para projeto e analise de radiacao de antenas microstrip
(patch) retangulares e circulares, baseada no modelo da cavidade e operando
no modo dominante:

    - Patch retangular : modo TM(010)
    - Patch circular    : modo TM(110)

Esta biblioteca e uma conversao direta dos scripts MATLAB originais
(MICROSTRIP.m, semipolar_micror.m, semipolar_microc.m), escritos por
Sung-Woo Lee e modificados por Zhiyong Huang (Arizona State University,
2004), publicados como material de apoio do livro:

    C. A. Balanis, "Antenna Theory: Analysis and Design".

Diferencas em relacao ao script MATLAB original
-------------------------------------------------
1. Nao ha mais `input()` interativo: todos os parametros sao passados como
   argumentos de funcao.
2. Calculo e plotagem foram separados: as funcoes de calculo retornam
   sempre arrays/numeros (nunca plotam nem escrevem arquivos), e as
   funcoes de plotagem/gravacao sao chamadas explicitamente por quem usa
   a biblioteca.
3. `semipolar_micror.m` e `semipolar_microc.m` foram unificadas em uma
   unica funcao `_semipolar_plot`, parametrizada pelo tipo de patch.
4. O metodo de busca de Yo/RHOo dado um Zin desejado foi mantido FIEL ao
   MATLAB original (varredura numerica com tolerancia heuristica), a
   pedido do usuario, em vez de usar um solver como scipy.optimize.

Uso basico
----------
    import microstrip_antenna as ma

    design = ma.design_rectangular_patch(freq_ghz=10, er=2.2, h_cm=0.1588)
    result = ma.rectangular_patch_analysis(design, Yo=0.3)

    ma.plot_cartesian_patterns(result)
    ma.plot_semipolar_patterns(result)
    ma.save_patterns(result, prefix="Epl-Micr")

Todas as funcoes tem docstrings com as unidades de entrada/saida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
from scipy.special import jv as besselj

__all__ = [
    # rectangular
    "RectangularPatchDesign",
    "RectangularPatchResult",
    "design_rectangular_patch",
    "rectangular_patch_analysis",
    # circular
    "CircularPatchDesign",
    "CircularPatchResult",
    "design_circular_patch",
    "circular_patch_analysis",
    # plotting / IO
    "plot_cartesian_patterns",
    "plot_semipolar_patterns",
    "save_patterns",
]


# =====================================================================
#  RETANGULAR
# =====================================================================


@dataclass
class RectangularPatchDesign:
    """Parametros fisicos do patch retangular (saida do modelo da cavidade)."""

    freq_ghz: float
    er: float
    h_cm: float
    W: float          # largura fisica do patch (cm)
    ereff: float       # constante dieletrica efetiva
    dl: float          # extensao de borda dL (cm)
    L: float           # comprimento fisico do patch (cm)
    Leff: float        # comprimento efetivo (cm)
    lambda_o: float    # comprimento de onda no espaco livre (cm)
    lambda_g: float    # comprimento de onda guiado (cm)
    ko: float          # numero de onda no espaco livre (rad/cm)
    Emax: float        # fator de normalizacao do campo


def design_rectangular_patch(freq_ghz: float, er: float, h_cm: float) -> RectangularPatchDesign:
    """
    Projeta um patch retangular no modo TM(010) a partir da frequencia de
    ressonancia, constante dieletrica do substrato e altura do substrato.

    Parameters
    ----------
    freq_ghz : frequencia de ressonancia (GHz)
    er       : constante dieletrica do substrato
    h_cm     : altura do substrato (cm)

    Returns
    -------
    RectangularPatchDesign
    """
    freq = float(freq_ghz)
    h = float(h_cm)

    W = 30.0 / (2.0 * freq) * np.sqrt(2.0 / (er + 1.0))
    ereff = (er + 1.0) / 2.0 + (er - 1.0) / (2.0 * np.sqrt(1.0 + 12.0 * h / W))
    dl = 0.412 * h * ((ereff + 0.3) * (W / h + 0.264)) / ((ereff - 0.258) * (W / h + 0.8))
    lambda_o = 30.0 / freq
    lambda_g = 30.0 / (freq * np.sqrt(ereff))
    Leff = 30.0 / (2.0 * freq * np.sqrt(ereff))
    L = Leff - 2.0 * dl
    ko = 2.0 * np.pi / lambda_o
    Emax = np.sinc(h * ko / 2.0 / np.pi)  # np.sinc(x) = sin(pi x)/(pi x), igual ao MATLAB sinc(x)

    return RectangularPatchDesign(
        freq_ghz=freq, er=er, h_cm=h, W=W, ereff=ereff, dl=dl, L=L, Leff=Leff,
        lambda_o=lambda_o, lambda_g=lambda_g, ko=ko, Emax=Emax,
    )


def _e_plane_rect(phir: np.ndarray, h: float, ko: float, Leff: float, Emax: float) -> np.ndarray:
    """Porta de E_th(phir,h,ko,Leff,Emax). phir em radianos. Retorna dB."""
    ARG = np.cos(phir) * h * ko / 2.0
    Ethval = (np.sinc(ARG / np.pi) * np.cos(np.sin(phir) * ko * Leff / 2.0)) / Emax
    with np.errstate(divide="ignore"):
        Eth = 20.0 * np.log10(np.abs(Ethval))
    Eth = np.where((phir > np.pi / 2) & (phir < 3 * np.pi / 2), -60.0, Eth)
    Eth = np.where(Eth <= -60.0, -60.0, Eth)
    return Eth


def _h_plane_rect(thr: np.ndarray, h: float, ko: float, W: float, Emax: float) -> np.ndarray:
    """Porta de E_ph(thr,h,ko,W,Emax). thr em radianos. Retorna dB."""
    ARG1 = np.sin(thr) * h * ko / 2.0
    ARG2 = np.cos(thr) * W * ko / 2.0
    Ephval = np.sin(thr) * np.sinc(ARG1 / np.pi) * np.sinc(ARG2 / np.pi) / Emax
    with np.errstate(divide="ignore"):
        Eph1 = 20.0 * np.log10(np.abs(Ephval))
    Eph1 = np.where(Eph1 <= -60.0, -60.0, Eph1)
    return Eph1


def _directivity_rect(W: float, h: float, Leff: float, L: float, ko: float) -> tuple[float, float]:
    """Porta de dir_rect. Retorna (D linear, D em dB)."""
    th = np.arange(0, 181)          # graus, 0..180
    phi = np.concatenate([np.arange(0, 91), np.arange(270, 361)])  # graus
    t, p = np.meshgrid(th * np.pi / 180.0, phi * np.pi / 180.0)    # igual ao MATLAB meshgrid(th,phi)

    X = ko * h / 2.0 * np.sin(t) * np.cos(p)
    Z = ko * W / 2.0 * np.cos(t)
    Et = np.sin(t) * np.sinc(X / np.pi) * np.sinc(Z / np.pi) * np.cos(ko * Leff / 2.0 * np.sin(t) * np.sin(p))
    U = Et ** 2

    dt = (th[1] - th[0]) * np.pi / 180.0
    dp = (phi[1] - phi[0]) * np.pi / 180.0
    Prad = np.sum(U * np.sin(t)) * dt * dp
    D = 4.0 * np.pi * np.max(U) / Prad
    DdB = 10.0 * np.log10(D)
    return float(D), float(DdB)


def _sintegr(W: float, L: float, ko: float) -> tuple[float, float]:
    """Porta de sintegr: condutancias de radiacao G1 (auto) e G12 (mutua)."""
    th = np.arange(0, 181)  # graus, passo 1
    t = th * np.pi / 180.0
    ARG = np.cos(t) * (ko * W / 2.0)
    common = np.sinc(ARG / np.pi) ** 2 * np.sin(t) ** 2 * np.sin(t) * ((np.pi / 180.0) * (ko * W / 2.0) ** 2)
    res1 = np.sum(common)
    res12 = np.sum(common * besselj(0, np.sin(t) * (ko * L)))
    G1 = res1 / (120.0 * np.pi ** 2)
    G12 = res12 / (120.0 * np.pi ** 2)
    return float(G1), float(G12)


@dataclass
class RectangularPatchResult:
    """Resultado completo da analise de um patch retangular."""

    design: RectangularPatchDesign

    # padroes de radiacao (graus, dB), 0..360
    phi_deg: np.ndarray          # eixo phi (plano E), 0..360
    Eth_dB: np.ndarray           # padrao plano E normalizado (dB)
    phi_H_deg: np.ndarray        # eixo phi (plano H, remontado a partir de theta), 0..360
    Eph_dB: np.ndarray           # padrao plano H normalizado (dB), remontado como no MATLAB

    # curvas cruas de theta 0..180 (usadas no HPBW do plano H)
    theta_deg: np.ndarray
    Eph1_dB: np.ndarray

    E_HPBW_deg: float
    H_HPBW_deg: float

    D: float
    DdB: float

    G1: float
    G12: float
    Rin0: float                   # resistencia de entrada na borda irradiante (y=0), ohms
    Yo: Optional[float] = None    # posicao do ponto de alimentacao (cm), se fornecida
    RinYo: Optional[float] = None  # resistencia de entrada em Yo, ohms
    Zin: Optional[float] = None   # impedancia desejada (ohms), se fornecida
    Y_for_Zin: Optional[float] = None  # posicao Yo calculada para o Zin desejado (cm)


def rectangular_patch_analysis(
    design: RectangularPatchDesign,
    Yo: Optional[float] = None,
    Zin: Optional[float] = None,
) -> RectangularPatchResult:
    """
    Calcula os padroes de radiacao, HPBW, diretividade e resistencia de
    entrada de um patch retangular ja projetado.

    Informe exatamente um dos dois:
      - Yo  : posicao do ponto de alimentacao (cm), para obter RinYo
      - Zin : impedancia de entrada desejada (ohms), para obter a posicao Yo

    Se nenhum dos dois for informado, apenas os padroes de radiacao,
    diretividade e Rin0 (borda irradiante, y=0) sao calculados.
    """
    if Yo is not None and Zin is not None:
        raise ValueError("Informe apenas um de Yo ou Zin, nao os dois.")

    h, ko, Leff, W, L, Emax = design.h_cm, design.ko, design.Leff, design.W, design.L, design.Emax

    # --- Plano E: phi de 0 a 360 graus ---
    phi = np.arange(0, 361)
    phir = phi * np.pi / 180.0
    Eth = _e_plane_rect(phir, h, ko, Leff, Emax)

    # --- Plano H: theta de 0 a 180 graus, depois remontado para 0..360 (como no MATLAB) ---
    theta = np.arange(0, 181)
    thr = theta * np.pi / 180.0
    Eph1 = _h_plane_rect(thr, h, ko, W, Emax)

    Eph = np.empty(361)
    Eph[0:91] = Eph1[90:181]
    Eph[90:270] = Eph1[180]
    Eph[270:361] = Eph1[0:91]
    phi_H = np.arange(0, 361)

    # --- HPBW ---
    an = phi[Eth > -3]
    an = an[an <= 90]
    E_HPBW = 2.0 * np.abs(np.max(an)) if an.size else float("nan")

    idx = np.where(Eph1 > -3)[0]
    H_HPBW = 2.0 * np.abs(90 - theta[idx].min()) if idx.size else float("nan")

    # --- Diretividade ---
    D, DdB = _directivity_rect(W, h, Leff, L, ko)

    # --- Resistencia de entrada ---
    G1, G12 = _sintegr(W, L, ko)
    Rin0 = (2.0 * (G1 + G12)) ** -1

    RinYo = None
    Y_for_Zin = None
    if Yo is not None:
        RinYo = Rin0 * np.cos(np.pi * Yo / L) ** 2
    elif Zin is not None:
        ratio = Zin / Rin0
        if ratio > 1.0:
            raise ValueError(
                f"Zin={Zin} ohms nao e atingivel: excede Rin0={Rin0:.4f} ohms "
                "na borda irradiante (nenhuma posicao Yo fisica satisfaz isso)."
            )
        Y_for_Zin = np.arccos(np.sqrt(ratio)) * L / np.pi

    return RectangularPatchResult(
        design=design,
        phi_deg=phi, Eth_dB=Eth,
        phi_H_deg=phi_H, Eph_dB=Eph,
        theta_deg=theta, Eph1_dB=Eph1,
        E_HPBW_deg=E_HPBW, H_HPBW_deg=H_HPBW,
        D=D, DdB=DdB,
        G1=G1, G12=G12, Rin0=Rin0,
        Yo=Yo, RinYo=RinYo, Zin=Zin, Y_for_Zin=Y_for_Zin,
    )


# =====================================================================
#  CIRCULAR
# =====================================================================


@dataclass
class CircularPatchDesign:
    """Parametros fisicos do patch circular (saida do modelo da cavidade)."""

    freq_ghz: float
    er: float
    h_cm: float
    a: float           # raio fisico (cm)
    ae: float          # raio efetivo (cm)
    ko: float          # numero de onda no espaco livre (rad/cm)
    lambda_o: float    # comprimento de onda no espaco livre (cm)


def design_circular_patch(freq_ghz: float, er: float, h_cm: float) -> CircularPatchDesign:
    """
    Projeta um patch circular no modo TM(110) a partir da frequencia de
    ressonancia, constante dieletrica e altura do substrato.
    """
    freq = float(freq_ghz)
    h = float(h_cm)

    lambda_o = 30.0 / freq
    ko = 2.0 * np.pi / lambda_o
    F = 8.791 / (freq * np.sqrt(er))
    a = F / np.sqrt(1 + 2 * h / (np.pi * er * F) * (np.log(np.pi * F / (2 * h)) + 1.7726))
    ae = a * np.sqrt(1 + 2 * h / (np.pi * er * a) * (np.log(np.pi * a / (2 * h)) + 1.7726))

    return CircularPatchDesign(freq_ghz=freq, er=er, h_cm=h, a=a, ae=ae, ko=ko, lambda_o=lambda_o)


def _directivity_circ(a: float, ae: float, ko: float) -> tuple[float, float]:
    """Porta de dir_cir. Retorna (D linear, D em dB)."""
    th = np.arange(0, 91)
    phi = np.arange(0, 361)
    t, p = np.meshgrid(th * np.pi / 180.0, phi * np.pi / 180.0)

    x = np.sin(t) * ko * ae
    J0 = besselj(0, x)
    J2 = besselj(2, x)
    J02P = J0 - J2
    J02 = J0 + J2
    Ucirc = (J02P * np.cos(p)) ** 2 + (J02 * np.cos(t) * np.sin(p)) ** 2
    Umax = np.max(Ucirc)
    Ua = Ucirc * np.sin(t) * (np.pi / 180.0) ** 2
    Prad = np.sum(Ua)

    D = 4.0 * np.pi * Umax / Prad
    DdB = 10.0 * np.log10(D)
    return float(D), float(DdB)


@dataclass
class CircularPatchResult:
    """Resultado completo da analise de um patch circular."""

    design: CircularPatchDesign

    theta_deg: np.ndarray     # 0..90, curvas cruas usadas para HPBW
    Eth2_dB: np.ndarray
    Eph2_dB: np.ndarray

    phi_deg: np.ndarray       # 0..360, padroes remontados (mesma convencao do MATLAB)
    Eth_dB: np.ndarray
    Eph_dB: np.ndarray

    E_HPBW_deg: float
    H_HPBW_deg: float

    D: float
    DdB: float

    con: float
    lt: float
    Rin0: float                          # resistencia de entrada em rho=ae, ohms
    RHOo: Optional[float] = None          # posicao do ponto de alimentacao (cm), se fornecida
    Rin: Optional[float] = None           # resistencia de entrada em RHOo, ohms
    Zin: Optional[float] = None           # impedancia desejada (ohms), se fornecida
    RHOo_solutions: Optional[np.ndarray] = None  # possiveis posicoes RHOo para o Zin desejado (cm)


def circular_patch_analysis(
    design: CircularPatchDesign,
    RHOo: Optional[float] = None,
    Zin: Optional[float] = None,
    con: float = 1e7,
    lt: float = 0.0018,
) -> CircularPatchResult:
    """
    Calcula os padroes de radiacao, HPBW, diretividade e resistencia de
    entrada de um patch circular ja projetado (modo TM(110)).

    Informe no maximo um de:
      - RHOo : posicao do ponto de alimentacao relativa ao centro (cm), para obter Rin
      - Zin  : impedancia de entrada desejada (ohms), para obter a(s) posicao(oes) RHOo

    Parameters
    ----------
    con : condutividade do condutor (S/m). Default 1e7 (igual ao MATLAB).
    lt  : tangente de perdas do dieletrico. Default 0.0018 (igual ao MATLAB, TM110).
    """
    if RHOo is not None and Zin is not None:
        raise ValueError("Informe apenas um de RHOo ou Zin, nao os dois.")

    freq, er, h, a, ae, ko = design.freq_ghz, design.er, design.h_cm, design.a, design.ae, design.ko

    # --- Padroes 0..90 graus ---
    th = np.arange(0, 91)
    thr = th * np.pi / 180.0
    x = np.sin(thr) * ko * ae
    J0 = besselj(0, x)
    J2 = besselj(2, x)
    Eth1 = J0 - J2
    Eph1 = (J0 + J2) * np.cos(thr)

    Eth2 = 20.0 * np.log10(np.abs(Eth1) / np.max(np.abs(Eth1)))
    Eph2 = 20.0 * np.log10(np.abs(Eph1) / np.max(np.abs(Eph1)))
    Eth2 = np.where(Eth2 <= -60.0, -60.0, Eth2)
    Eph2 = np.where(Eph2 <= -60.0, -60.0, Eph2)

    # --- Remontagem para 0..360 (mesma logica do MATLAB) ---
    Eth = np.empty(361)
    Eth[0:91] = Eth2[0:91]
    Eth[90:270] = Eth2[90]
    Eth[270:361] = Eth2[90::-1]

    Eph = np.empty(361)
    Eph[0:91] = Eph2[0:91]
    Eph[90:270] = Eph2[90]
    Eph[270:361] = Eph2[90::-1]

    phi = np.arange(0, 361)

    # --- HPBW ---
    an = th[Eth2 > -3]
    bn = th[Eph2 > -3]
    E_HPBW = 2.0 * np.abs(np.max(an)) if an.size else float("nan")
    H_HPBW = 2.0 * np.abs(np.max(bn)) if bn.size else float("nan")

    # --- Diretividade ---
    D, DdB = _directivity_circ(a, ae, ko)

    # --- Resistencia de entrada (radiacao + condutor + dieletrico) ---
    t = np.arange(0, np.pi / 2 + 1e-12, 0.001)
    xr = ko * ae * np.sin(t)
    j0 = besselj(0, xr)
    j2 = besselj(2, xr)
    j02p = j0 - j2
    j02 = j0 + j2
    grad = (ko * ae) ** 2 / 480.0 * np.sum((j02p ** 2 + (np.cos(t)) ** 2 * j02 ** 2) * np.sin(t) * 0.001)

    emo = 1.0
    m = 1.0
    mu0 = 4 * np.pi * 1e-7
    k = ko * np.sqrt(er)

    gc = emo * np.pi * (np.pi * mu0 * freq * 1e9) ** (-1.5) * ((k * ae) ** 2 - m ** 2) / (4 * (h / 100) ** 2 * np.sqrt(con))
    gd = emo * lt * ((k * ae) ** 2 - m ** 2) / (4 * mu0 * (h / 100) * freq * 1e9)
    gt = grad + gc + gd
    Rin0 = 1.0 / gt

    Rin = None
    RHOo_solutions = None
    if RHOo is not None:
        Rin = Rin0 * besselj(1, k * RHOo) ** 2 / besselj(1, k * ae) ** 2
    elif Zin is not None:
        krhov = np.arange(0, k * a, 0.0001)
        temp = besselj(1, krhov) ** 2
        rho_thresh = np.max(np.abs(np.diff(temp))) / 2.0
        temp1 = Zin / Rin0 * besselj(1, k * ae) ** 2
        rhoi = np.where(np.abs(temp - temp1) < rho_thresh)[0]

        if rhoi.size == 0:
            RHOo_solutions = np.array([])
        else:
            rho_candidates = krhov[rhoi] / k
            if rhoi.size > 1:
                grouped = []
                rho_sum = 0.0
                num = 0
                for kk in range(len(rhoi)):
                    rho_sum += rho_candidates[kk]
                    num += 1
                    is_last = kk == len(rhoi) - 1
                    gap_ends_cluster = (not is_last) and (rhoi[kk + 1] - rhoi[kk] > 1)
                    if gap_ends_cluster or is_last:
                        grouped.append(rho_sum / num)
                        rho_sum, num = 0.0, 0
                RHOo_solutions = np.array(grouped)
            else:
                RHOo_solutions = rho_candidates

    return CircularPatchResult(
        design=design,
        theta_deg=th, Eth2_dB=Eth2, Eph2_dB=Eph2,
        phi_deg=phi, Eth_dB=Eth, Eph_dB=Eph,
        E_HPBW_deg=E_HPBW, H_HPBW_deg=H_HPBW,
        D=D, DdB=DdB,
        con=con, lt=lt, Rin0=Rin0,
        RHOo=RHOo, Rin=Rin, Zin=Zin, RHOo_solutions=RHOo_solutions,
    )


# =====================================================================
#  PLOTAGEM
# =====================================================================


def plot_cartesian_patterns(result, title: Optional[str] = None, ax=None):
    """
    Plota os padroes de radiacao dos planos E e H em coordenadas
    cartesianas (equivalente a "Figure 1" do MICROSTRIP.m), theta de
    -90 a 90 graus no eixo x, amplitude em dB no eixo y.

    Funciona tanto para RectangularPatchResult quanto CircularPatchResult.
    """
    import matplotlib.pyplot as plt

    is_rect = isinstance(result, RectangularPatchResult)

    if is_rect:
        # remonta -90..90 a partir do array de 0..360 (mesma logica do MATLAB)
        Eth_full = result.Eth_dB
        e_curve = np.concatenate([Eth_full[270:361], Eth_full[1:91]])
        h_curve = np.concatenate([result.Eph1_dB[90::-1], result.Eph1_dB[1:91]])
        x_axis = np.arange(-90, 91)
        e_label, h_label = r"$E_\phi$ (plano E)", r"$E_\phi$ (plano H)"
        xlabel = r"$\theta$ / $\phi$ (graus)"
        default_title = "Padroes de radiacao - Patch Retangular"
    else:
        e_curve = np.concatenate([result.Eth2_dB[::-1], result.Eth2_dB[1:]])
        h_curve = np.concatenate([result.Eph2_dB[::-1], result.Eph2_dB[1:]])
        x_axis = np.arange(-90, 91)
        e_label, h_label = r"$E_\theta$ (plano E)", r"$E_\phi$ (plano H)"
        xlabel = r"$\theta$ (graus)"
        default_title = "Padroes de radiacao - Patch Circular"

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x_axis, e_curve, "b-", linewidth=2, label=e_label)
    ax.plot(x_axis, h_curve, "r:", linewidth=2, label=h_label)
    ax.set_xlim(-90, 90)
    ax.set_ylim(-60, 0)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel("Padrao de radiacao (dB)", fontsize=12)
    ax.set_title(title or default_title, fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower center")
    return ax


def _semipolar_plot(ax, theta_deg: np.ndarray, rho_db: np.ndarray, rmin: float, rmax: float,
                     rticks: int, line_style: str, color: str, angle_mode: str, label: str = None):
    """
    Porta funcional de semipolar_micror.m / semipolar_microc.m: plota um
    padrao de radiacao (rho em dB, possivelmente negativo) em um grafico
    semi-polar (theta de 0 a 180 graus na tela, mapeando o intervalo
    angular fisico do padrao).

    angle_mode: 'phi' (para o plano/rotulo do patch retangular) ou
                'theta' (para o patch circular), apenas para os rotulos.
    """
    theta_rad = np.asarray(theta_deg) * np.pi / 180.0
    rho = np.asarray(rho_db, dtype=float)

    # grade radial (circulos + raios)
    if not getattr(ax, "_semipolar_grid_drawn", False):
        rinc = (rmax - rmin) / rticks
        circle_t = np.linspace(0, np.pi, 200)
        for level in np.arange(rmin + rinc, rmax + 1e-9, rinc):
            radius = level - rmin
            ax.plot(radius * np.cos(circle_t), radius * np.sin(circle_t), "-", color="0.6", linewidth=0.5)
            ax.text(radius, -0.06 * (rmax - rmin), f"{level:.0f}", ha="center", fontsize=8)
            ax.text(-radius, -0.06 * (rmax - rmin), f"{level:.0f}", ha="center", fontsize=8)

        for spoke_deg in range(0, 181, 30):
            sr = spoke_deg * np.pi / 180.0
            ax.plot([0, (rmax - rmin) * np.cos(sr)], [0, (rmax - rmin) * np.sin(sr)], "-", color="0.6", linewidth=0.5)
            rt = 1.15 * (rmax - rmin)
            outer_label = f"{spoke_deg}" if angle_mode == "theta" else f"{spoke_deg}"
            inner_label = f"{abs(90 - (spoke_deg - 90))}" if spoke_deg <= 90 else f"{abs(spoke_deg - 90)}"
            ax.text(rt * np.cos(sr), rt * np.sin(sr), outer_label, ha="center", color="red", fontsize=8)

        ax.text(0, -0.06 * (rmax - rmin), "dB", ha="center", fontsize=9)
        ax.set_aspect("equal")
        ax.axis("off")
        ax._semipolar_grid_drawn = True

    rho_clipped = np.clip(rho, rmin, None)
    radius = np.where(rho > rmin, rho - rmin, 0.0)
    xx = radius * np.cos(theta_rad + np.pi / 2)
    yy = radius * np.sin(theta_rad + np.pi / 2)
    (line,) = ax.plot(xx, yy, line_style, color=color, linewidth=2, label=label)
    return line


def plot_semipolar_patterns(result, title: Optional[str] = None, ax=None):
    """
    Plota os padroes de radiacao dos planos E e H em grafico semi-polar
    (equivalente a "Figure 2" do MICROSTRIP.m: 0 a 180 graus na tela).

    Funciona tanto para RectangularPatchResult quanto CircularPatchResult.
    """
    import matplotlib.pyplot as plt

    is_rect = isinstance(result, RectangularPatchResult)

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 7))

    if is_rect:
        theta_screen = np.arange(0, 361)
        line_e = _semipolar_plot(ax, theta_screen, result.Eth_dB, -60, 0, 4, "-", "b",
                                  angle_mode="phi", label=r"$E_\phi$ (plano E)")
        line_h = _semipolar_plot(ax, theta_screen, result.Eph_dB, -60, 0, 4, ":", "r",
                                  angle_mode="phi", label=r"$E_\phi$ (plano H)")
        default_title = "Padroes de radiacao (semi-polar) - Patch Retangular"
    else:
        theta_screen = (np.arange(-90, 91)) % 360
        e_curve = np.concatenate([result.Eth2_dB[::-1], result.Eth2_dB[1:]])
        h_curve = np.concatenate([result.Eph2_dB[::-1], result.Eph2_dB[1:]])
        line_e = _semipolar_plot(ax, np.arange(0, 181), e_curve, -60, 0, 4, "-", "b",
                                  angle_mode="theta", label=r"$E_\theta$ (plano E)")
        line_h = _semipolar_plot(ax, np.arange(0, 181), h_curve, -60, 0, 4, ":", "r",
                                  angle_mode="theta", label=r"$E_\phi$ (plano H)")
        default_title = "Padroes de radiacao (semi-polar) - Patch Circular"

    ax.set_title(title or default_title, fontsize=12)
    ax.legend(loc="upper right", fontsize=9)
    return ax


def save_patterns(result, prefix: str = "Epl-Micr", out_dir: str = ".") -> tuple[str, str]:
    """
    Salva os padroes de plano E e plano H em arquivos .dat de texto,
    no mesmo formato dos arquivos gerados pelo MICROSTRIP.m original
    (Epl-Micr_m.dat / Hpl-Micr_m.dat).

    Returns
    -------
    (caminho_arquivo_E, caminho_arquivo_H)
    """
    import os

    is_rect = isinstance(result, RectangularPatchResult)

    e_path = os.path.join(out_dir, f"{prefix}_E.dat")
    h_path = os.path.join(out_dir, f"{prefix}_H.dat")

    with open(e_path, "wt") as f:
        f.write("# E-PLANE RADIATION PATTERN\n# -------------------------\n#\n")
        angles = result.phi_deg
        values = result.Eth_dB
        for a, v in zip(angles, values):
            f.write(f"  {a:7.4f}\t{v:7.4f}\n")

    with open(h_path, "wt") as f:
        f.write("# H-PLANE RADIATION PATTERN\n")
        if is_rect:
            f.write("# NOTE: THIS PATTERN IS ROTATED CCW BY 90 DEGREES\n")
        f.write("# -------------------------\n#\n")
        angles = result.phi_deg if not is_rect else result.phi_H_deg
        values = result.Eph_dB
        mask = (angles <= 90) | (angles >= 270)
        for a, v in zip(angles[mask], values[mask]):
            f.write(f"  {a:7.4f}\t{v:7.4f}\n")

    return e_path, h_path
