"""
exemplo_uso.py
==============
Exemplo de uso da biblioteca microstrip_antenna.

Rode com:  python3 exemplo_uso.py
"""

import matplotlib.pyplot as plt
import microstrip_antenna as ma


def exemplo_retangular():
    # 1) Projeto do patch (equivalente aos inputs freq, epsr, height do MATLAB)
    design = ma.design_rectangular_patch(freq_ghz=10, er=2.2, h_cm=0.1588)

    print("Patch retangular projetado:")
    print(f"  W    = {design.W:.4f} cm")
    print(f"  Leff = {design.Leff:.4f} cm")
    print(f"  L    = {design.L:.4f} cm")

    # 2a) Analise informando a posicao do ponto de alimentacao Yo (cm)
    resultado = ma.rectangular_patch_analysis(design, Yo=0.3)
    print(f"\nRin(Yo=0.3cm) = {resultado.RinYo:.2f} ohm")
    print(f"Diretividade  = {resultado.DdB:.2f} dB")
    print(f"HPBW E/H      = {resultado.E_HPBW_deg:.1f} / {resultado.H_HPBW_deg:.1f} graus")

    # 2b) Ou, alternativamente, informando a impedancia desejada
    resultado_zin = ma.rectangular_patch_analysis(design, Zin=50)
    print(f"Yo para casar em 50 ohm = {resultado_zin.Y_for_Zin:.4f} cm")

    # 3) Plots
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    ma.plot_cartesian_patterns(resultado, ax=axes[0])
    ma.plot_semipolar_patterns(resultado, ax=axes[1])
    fig.suptitle("Patch Retangular - 10 GHz, εr=2.2, h=0.1588 cm")
    fig.tight_layout()
    fig.savefig("retangular.png", dpi=120)

    # 4) Exportar padroes em .dat (mesmo formato do MATLAB original)
    ma.save_patterns(resultado, prefix="Epl-Micr_rect")


def exemplo_circular():
    design = ma.design_circular_patch(freq_ghz=10, er=2.2, h_cm=0.1588)

    print("\nPatch circular projetado:")
    print(f"  a  = {design.a:.4f} cm")
    print(f"  ae = {design.ae:.4f} cm")

    resultado = ma.circular_patch_analysis(design, RHOo=0.5, con=1e7, lt=0.0018)
    print(f"Rin(RHOo=0.5cm) = {resultado.Rin:.2f} ohm")
    print(f"Diretividade    = {resultado.DdB:.2f} dB")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    ma.plot_cartesian_patterns(resultado, ax=axes[0])
    ma.plot_semipolar_patterns(resultado, ax=axes[1])
    fig.suptitle("Patch Circular - 10 GHz, εr=2.2, h=0.1588 cm")
    fig.tight_layout()
    fig.savefig("circular.png", dpi=120)


if __name__ == "__main__":
    exemplo_retangular()
    exemplo_circular()
    print("\nProntos: retangular.png, circular.png, Epl-Micr_rect_E.dat, Epl-Micr_rect_H.dat")
