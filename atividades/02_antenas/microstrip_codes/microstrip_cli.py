"""
microstrip_cli.py
==================

Modo interativo, linha de comando, que reproduz os mesmos prompts do
MICROSTRIP.m original (SELECT OUTPUT METHOD, PATCH GEOMETRY OPTION,
frequencia, epsr, altura, Yo/Zin, etc.).

Este arquivo NAO contem nenhuma formula de antena: ele so pergunta os
parametros ao usuario (igual ao MATLAB) e repassa para as funcoes de
calculo puras de `microstrip_antenna.py`. Ou seja, a biblioteca continua
100% utilizavel via `import microstrip_antenna`, e quem quiser o
comportamento "pergunta tudo no terminal" do script original roda este
arquivo.

Uso:
    python3 microstrip_cli.py
"""

from __future__ import annotations

import sys
from typing import Optional

import matplotlib.pyplot as plt

import microstrip_antenna as ma


# =====================================================================
#  Helpers de input (equivalentes aos loops "while isempty(x)" do MATLAB)
# =====================================================================


def _ask_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            return float(raw)
        except ValueError:
            print("  -> valor invalido, digite um numero.")


def _ask_float_default(prompt: str, default: float) -> float:
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"  -> valor invalido, usando o padrao ({default}).")
        return default


def _ask_option(prompt: str, valid=(1, 2)) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            val = int(raw)
        except ValueError:
            print("  -> opcao invalida.")
            continue
        if val in valid:
            return val
        print("  -> opcao invalida.")


def _ask_nonempty_str(prompt: str) -> str:
    while True:
        raw = input(prompt).strip()
        if raw:
            return raw


# =====================================================================
#  Fluxo principal (equivalente a MICROSTP no MATLAB)
# =====================================================================


def run_interactive() -> None:
    """Reproduz o fluxo interativo do MICROSTRIP.m original no terminal."""

    print()
    option = _ask_option(
        "SELECT OUTPUT METHOD\n"
        "   OPTION (1): SCREEN\n"
        "   OPTION (2): OUTPUT FILE\n"
        "SELECT OPTION: "
    )

    filename: Optional[str] = None
    if option == 2:
        filename = _ask_nonempty_str("INPUT THE DESIRED OUTPUT FILENAME = ")

    print()
    patchm = _ask_option(
        "PATCH GEOMETRY OPTION\n"
        "   OPTION (1) : RECTANGULAR PATCH\n"
        "   OPTION (2) : CIRCULAR PATCH\n"
        "SELECT OPTION NUMBER: "
    )

    if patchm == 1:
        _run_rectangular(option, filename)
    else:
        _run_circular(option, filename)


# ------------------------- Retangular -------------------------------


def _run_rectangular(option_a: int, filename: Optional[str]) -> None:
    freq = _ask_float("\nINPUT THE RESONANT FREQUENCY (in GHz) = ")
    er = _ask_float("INPUT THE DIELECTRIC CONSTANT OF THE SUBSTRATE = ")
    h = _ask_float("INPUT THE HEIGHT OF THE SUBSTRATE (in cm) = ")

    option1 = _ask_option(
        "OPTIONS \n"
        "   OPTION (1): FIND INPUT IMPEDANCE Zin AT FEED-POINT Yo \n"
        "   OPTION (2): DETERMINE Yo FOR A GIVEN DESIRED Zin \n"
        "SELECT OPTION NUMBER: "
    )

    Yo = Zin = None
    if option1 == 1:
        Yo = _ask_float(
            "\nINPUT THE POSITION OF THE RECESSED FEED POINT "
            "RELATIVE TO THE LEADING RADIATING EDGE\n"
            "OF THE RECTANGULAR PATCH (in cm) = "
        )
    else:
        Zin = _ask_float("INPUT THE DESIRED INPUT IMPEDANCE Zin (in ohms) = ")

    # --- calculo (biblioteca pura) ---
    design = ma.design_rectangular_patch(freq_ghz=freq, er=er, h_cm=h)
    try:
        result = ma.rectangular_patch_analysis(design, Yo=Yo, Zin=Zin)
    except ValueError as exc:
        print(f"\nERRO: {exc}")
        return

    # --- saida (texto) ---
    lines = []
    lines.append("INPUT PARAMETERS")
    lines.append("================")
    lines.append(f"\nRESONANT FREQUENCY (in GHz) = {freq:.4f}")
    lines.append(f"DIELECTRIC CONSTANT OF THE SUBSTRATE = {er:.4f}")
    lines.append(f"HEIGHT OF THE SUBSTRATE (in cm) = {h:.4f}")
    if option1 == 1:
        lines.append(f"POSITION OF THE RECESSED FEED POINT (in cm) = {Yo:.4f}\n")
    else:
        lines.append(f"DESIRED RESONANT INPUT IMPEDANCE (in ohms) = {Zin:.4f}\n")
    lines.append("OUTPUT PARAMETERS")
    lines.append("=================")
    lines.append(f"\nPHYSICAL WIDTH OF PATCH (in cm) = {design.W:.4f}")
    lines.append(f"EFFECTIVE LENGTH OF PATCH (in cm) = {design.Leff:.4f}")
    lines.append(f"PHYSICAL LENGTH OF PATCH (in cm) = {design.L:.4f}")
    lines.append(f"E-PLANE HPBW (in degrees) = {result.E_HPBW_deg:.4f}")
    lines.append(f"H-PLANE HPBW (in degrees) = {result.H_HPBW_deg:.4f}")
    lines.append(f"DIRECTIVITY OF RECTANGULAR PATCH (dimensionless) = {result.D:.4f}")
    lines.append(f"DIRECTIVITY OF RECTANGULAR PATCH (in dB) = {result.DdB:.4f}\n")
    lines.append(f"RESONANT INPUT RESISTANCE AT LEADING RADIATING EDGE (y=0) Rin0 = {result.Rin0:.4f} ohms\n")
    if option1 == 1:
        lines.append(f"RESONANT INPUT RESISTANCE AT RECESSED FEED POINT (y={Yo:.4f} cm) RINYo = {result.RinYo:.4f} ohms")
    else:
        lines.append(f"FOR DESIRED IMPEDANCE {Zin:.4f} ohms, THE FEED POINT POSITION Yo = {result.Y_for_Zin:.4f} cm\n")
    lines.append("*** NOTE:")
    lines.append("    THE E-PLANE AMPLITUDE PATTERN IS STORED IN Epl-Micr_m.dat")
    lines.append("    THE H-PLANE AMPLITUDE PATTERN IS STORED IN Hpl-Micr_m.dat")
    lines.append("    =========================================================")

    _emit(lines, option_a, filename)

    # --- arquivos .dat (mesmo nome do MATLAB original) ---
    ma.save_patterns(result, prefix="Epl-Micr_m")

    # --- plots (equivalentes as Figures 1 e 2 do MATLAB) ---
    fig1, ax1 = plt.subplots(figsize=(7, 5))
    ma.plot_cartesian_patterns(result, ax=ax1)
    fig2, ax2 = plt.subplots(figsize=(7, 7))
    ma.plot_semipolar_patterns(result, ax=ax2)
    plt.show()


# ------------------------- Circular -----------------------------------


def _run_circular(option_a: int, filename: Optional[str]) -> None:
    freq = _ask_float("\nINPUT THE RESONANT FREQUENCY (in GHz) = ")
    er = _ask_float("INPUT THE DIELECTRIC CONSTANT OF THE SUBSTRATE = ")
    h = _ask_float("INPUT THE HEIGHT OF THE SUBSTRATE (in cm) = ")

    con = _ask_float_default(
        "PLEASE INPUT THE CONDUCTIVITY (DEFAULT VALUE IS 10^7): ", default=1e7
    )
    lt = _ask_float_default(
        "PLEASE INPUT THE LOSS TANGENT (DEFAULT VALUE OF DOMINANT MODE TM110 IS 0.0018): ",
        default=0.0018,
    )

    option1 = _ask_option(
        "OPTIONS \n"
        "   OPTION (1): FIND INPUT IMPEDANCE Zin AT FEED-POINT RHOo \n"
        "   OPTION (2): DETERMINE RHOo FOR A GIVEN DESIRED Zin \n"
        "SELECT OPTION NUMBER: "
    )

    RHOo = Zin = None
    if option1 == 1:
        RHOo = _ask_float(
            "\nINPUT THE POSITION OF THE RECESSED FEED POINT "
            "RELATIVE TO THE CENTER OF THE CIRCULAR PATCH (in cm) = "
        )
    else:
        Zin = _ask_float("INPUT THE DESIRED INPUT IMPEDANCE Zin (in ohms) = ")

    # --- calculo (biblioteca pura) ---
    design = ma.design_circular_patch(freq_ghz=freq, er=er, h_cm=h)
    result = ma.circular_patch_analysis(design, RHOo=RHOo, Zin=Zin, con=con, lt=lt)

    # --- saida (texto) ---
    lines = []
    lines.append("INPUT PARAMETERS")
    lines.append("================")
    lines.append(f"\nRESONANT FREQUENCY (in GHz) = {freq:.4f}")
    lines.append(f"DIELECTRIC CONSTANT OF THE SUBSTRATE = {er:.4f}")
    lines.append(f"HEIGHT OF THE SUBSTRATE (in cm) = {h:.4f}\n")
    lines.append("OUTPUT PARAMETERS")
    lines.append("=================")
    lines.append(f"\nPHYSICAL RADIUS OF THE PATCH (in cm) = {design.a:.4f}")
    lines.append(f"EFFECTIVE RADIUS OF THE PATCH (in cm) = {design.ae:.4f}")
    lines.append(f"E-PLANE HPBW (in degrees) = {result.E_HPBW_deg:.4f}")
    lines.append(f"H-PLANE HPBW (in degrees) = {result.H_HPBW_deg:.4f}")
    lines.append(f"DIRECTIVITY OF CIRCULAR PATCH (dimensionless) = {result.D:.4f}")
    lines.append(f"DIRECTIVITY OF CIRCULAR PATCH (in dB) = {result.DdB:.4f}\n")
    lines.append("*** TM110 MODE ***")
    lines.append(f"RESONANT INPUT RESISTANCE AT RHO=ae : Rin0 = {result.Rin0:.4f} ohms")
    if option1 == 1:
        lines.append(f"RESONANT INPUT RESISTANCE AT RECESSED FEED POINT (RHO={RHOo:.4f} cm) RIN = {result.Rin:.4f} ohms")
    else:
        sols = result.RHOo_solutions
        if sols is None or len(sols) == 0:
            lines.append(f"\nSORRY. NO PHYSICAL SOLUTION OF RHOo FOR THE GIVEN DESIRED IMPEDANCE: {Zin:.4f} ohms!\n")
        else:
            lines.append(f"THERE ARE {len(sols)} POSSIBLE VALUE(S) OF RHOo FOR THE DESIRED IMPEDANCE {Zin:.4f} ohms")
            for i, rho in enumerate(sols, start=1):
                lines.append(f"THE FEED POINT POSITION RHOo{i} = {rho:.5f} cm")
    lines.append("*** NOTE:")
    lines.append("    THE E-PLANE AMPLITUDE PATTERN IS STORED IN Epl-Micr_m.dat")
    lines.append("    THE H-PLANE AMPLITUDE PATTERN IS STORED IN Hpl-Micr_m.dat")
    lines.append("    =========================================================")

    _emit(lines, option_a, filename)

    # --- arquivos .dat (mesmo nome do MATLAB original) ---
    ma.save_patterns(result, prefix="Epl-Micr_m")

    # --- plots (equivalentes as Figures 1 e 2 do MATLAB) ---
    fig1, ax1 = plt.subplots(figsize=(7, 5))
    ma.plot_cartesian_patterns(result, ax=ax1)
    fig2, ax2 = plt.subplots(figsize=(7, 7))
    ma.plot_semipolar_patterns(result, ax=ax2)
    plt.show()


# ------------------------- saida: tela ou arquivo (equivalente a diary) --


def _emit(lines: list[str], option_a: int, filename: Optional[str]) -> None:
    text = "\n".join(lines)
    print("\n" + text + "\n")
    if option_a == 2 and filename:
        with open(filename, "wt") as f:
            f.write(text + "\n")
        print(f"(resultado tambem salvo em: {filename})")


if __name__ == "__main__":
    try:
        run_interactive()
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")
        sys.exit(1)
