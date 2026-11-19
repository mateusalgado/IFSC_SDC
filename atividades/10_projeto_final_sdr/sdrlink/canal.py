"""Modelos de canal para a simulação: AWGN, fase, offset de frequência e atraso."""
import numpy as np


def ruido(n: int, variancia: float, rng) -> np.ndarray:
    """Ruído gaussiano complexo com variância total `variancia` por amostra."""
    return np.sqrt(variancia / 2) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))


def variancia_ruido(potencia_media: float, sps: float, ebn0_db: float) -> float:
    """Variância por amostra para o Eb/N0 pedido (Eb = potência média × duração do bit)."""
    return potencia_media * sps / 10 ** (ebn0_db / 10)


def girar(x: np.ndarray, df_ciclos_por_amostra: float = 0.0, fase: float = 0.0, n0: int = 0) -> np.ndarray:
    """Aplica fase inicial e offset de frequência (em ciclos por amostra)."""
    n = np.arange(n0, n0 + len(x))
    return x * np.exp(1j * (2 * np.pi * df_ciclos_por_amostra * n + fase))
