"""Gera os resultados da Atividade 2 para uma matricula individual."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "microstrip_codes"))
import microstrip_antenna as ma


N = 89
OUTPUT = Path(__file__).parent / "figuras"


def dipole_pattern(theta: np.ndarray, ratio: float) -> np.ndarray:
    """Retorna o campo normalizado do dipolo, usando l/lambda = ratio."""
    numerator = np.cos(np.pi * ratio * np.cos(theta)) - np.cos(np.pi * ratio)
    with np.errstate(divide="ignore", invalid="ignore"):
        field = np.abs(numerator / np.sin(theta))
    field = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0)
    maximum = np.max(field)
    return field / maximum if maximum else field


def generate_dipole_figures() -> None:
    frequency_hz = 2.4e9 + (N % 10) * 50e6
    wavelength_m = 3e8 / frequency_hz
    theta = np.linspace(0.0, 2.0 * np.pi, 2001)
    ratios = (1.0, 0.25, 0.125, 0.025, 0.0125)

    fig, axes = plt.subplots(2, 3, subplot_kw={"projection": "polar"}, figsize=(12, 8))
    axes = axes.ravel()
    for index, ratio in enumerate(ratios):
        pattern = dipole_pattern(theta, ratio)
        axis = axes[index]
        axis.plot(theta, pattern, color="#c2410c", linewidth=1.5)
        axis.set_title(f"l = {ratio:g} lambda\n({ratio * wavelength_m * 100:.4f} cm)")
        axis.set_rticks([0.25, 0.5, 0.75, 1.0])
        axis.set_rmax(1.0)

        individual = plt.figure(figsize=(6, 6))
        individual_axis = individual.add_subplot(111, projection="polar")
        individual_axis.plot(theta, pattern, color="#c2410c", linewidth=1.8)
        individual_axis.set_title(
            f"Dipolo - f = {frequency_hz / 1e9:.3f} GHz, l = {ratio:g} lambda"
        )
        individual_axis.set_rticks([0.25, 0.5, 0.75, 1.0])
        individual_axis.set_rmax(1.0)
        individual.tight_layout()
        individual.savefig(OUTPUT / f"dipolo_{str(ratio).replace('.', '_')}lambda.png", dpi=160)
        plt.close(individual)

    axes[-1].axis("off")
    fig.suptitle(f"Diagramas de radiacao do dipolo - f = {frequency_hz / 1e9:.3f} GHz")
    fig.tight_layout()
    fig.savefig(OUTPUT / "dipolos_comparacao.png", dpi=180)
    plt.close(fig)


def generate_microstrip_table() -> list[dict[str, float]]:
    epsilon_antenna_1 = 2.2 + (N % 5) * 0.3
    specifications = (
        (1, 2.45, epsilon_antenna_1, 50.0, 0.3),
        (2, 2.45, 2.2, 75.0, 0.3),
        (3, 5.0, 2.2, 50.0, 0.3),
        (4, 2.45, 2.2, 75.0, 0.1),
    )
    rows = []
    for antenna, frequency, er, impedance, height in specifications:
        design = ma.design_rectangular_patch(frequency, er, height)
        result = ma.rectangular_patch_analysis(design, Zin=impedance)
        rows.append({"antenna": antenna, "W": design.W, "L": design.L,
                     "y0": result.Y_for_Zin, "DdB": result.DdB})
    return rows


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    generate_dipole_figures()
    rows = generate_microstrip_table()
    print("antena,W_cm,L_cm,y0_cm,diretividade_dB")
    for row in rows:
        print(f"{row['antenna']},{row['W']:.6f},{row['L']:.6f},{row['y0']:.6f},{row['DdB']:.6f}")


if __name__ == "__main__":
    main()