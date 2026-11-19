"""Estilo comum das figuras e gravação em português e inglês."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parent
FIGURAS = BASE / "figuras"
RESULTADOS = BASE / "resultados"
VERDE = "#285b42"
TINTA = "#293b42"
# Cor por entidade, em ordem fixa: a mesma modulação tem sempre a mesma cor.
CORES = {"ook": "#2a78d6", "fsk": "#eb6834", "bpsk": "#1baf7a", "dbpsk": "#1baf7a", "extra": "#eda100"}


def estilo():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.titleweight": "bold", "axes.titlecolor": VERDE, "axes.titlesize": 11,
        "axes.labelcolor": TINTA, "axes.edgecolor": "#8a9a94", "xtick.color": TINTA, "ytick.color": TINTA,
        "axes.grid": True, "grid.alpha": 0.3, "grid.color": "#8a9a94",
        "lines.linewidth": 2.0, "lines.markersize": 6.5, "legend.fontsize": 8.5, "legend.framealpha": 0.92,
        "font.size": 9.5, "figure.titleweight": "bold", "figure.titlesize": 12.5,
    })


def salvar(desenhar, nome: str):
    """Chama desenhar(t) duas vezes; t(pt, en) escolhe o rótulo do idioma."""
    estilo()
    for idioma, pasta in (("pt", FIGURAS), ("en", FIGURAS / "en")):
        pasta.mkdir(parents=True, exist_ok=True)
        fig = desenhar(lambda pt, en, _i=idioma: pt if _i == "pt" else en)
        fig.savefig(pasta / nome, dpi=150)
        plt.close(fig)
    print("figura:", nome)


def _nativo(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def _sem_nan(o):
    """Troca NaN por null para o arquivo ser JSON válido (pontos sem pacotes recebidos)."""
    if isinstance(o, dict):
        return {k: _sem_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sem_nan(v) for v in o]
    if isinstance(o, (float, np.floating)) and np.isnan(o):
        return None
    return o


def gravar_json(nome: str, dados: dict):
    RESULTADOS.mkdir(exist_ok=True)
    texto = json.dumps(_sem_nan(dados), indent=2, ensure_ascii=False, default=_nativo, allow_nan=False)
    (RESULTADOS / nome).write_text(texto + "\n", encoding="utf-8")
    print("resultados:", nome)


def virgula(v, casas=2):
    """Número com vírgula decimal, para rótulos em português."""
    return f"{v:.{casas}f}".replace(".", ",")
