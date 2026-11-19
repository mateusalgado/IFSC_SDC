"""Moduladores e detectores em banda base complexa.

Convenção: `sps` é o número inteiro de amostras por bit. Todo modulador devolve
um sinal com amplitude de pico unitária (o DAC do Pluto é limitado em pico).
Todo detector devolve um fluxo `s` alinhado de modo que o bit k de um quadro que
começa na amostra n0 seja lido em s[n0 + k*sps]. O bit vale 1 quando a parte
real do fluxo (depois da correção do sincronismo) está acima do limiar.
"""
from dataclasses import dataclass

import numpy as np

ESQUEMAS = ("ook", "fsk", "dbpsk")


@dataclass(frozen=True)
class Config:
    """Parâmetros da camada física."""
    esquema: str = "ook"
    pulso: str = "ret"      # ook: ret | rampa;  fsk: ret | gauss;  dbpsk: ret | rrc
    h: float = 1.0          # índice de modulação FSK (desvio de ±h·Rb/2)
    bt: float = 0.5         # produto BT do filtro gaussiano (FSK)
    alfa: float = 0.35      # roll-off do cosseno levantado (DBPSK)
    rampa: float = 0.1      # fração do bit usada na rampa OOK da referência
    span: int = 8           # meia duração do filtro RRC, em símbolos

    def __post_init__(self):
        if self.esquema not in ESQUEMAS:
            raise ValueError(f"esquema deve ser um de {ESQUEMAS}")

    @property
    def rotulo(self) -> str:
        nomes = {"ook": "OOK", "fsk": "2-FSK", "dbpsk": "DBPSK"}
        return f"{nomes[self.esquema]} ({self.pulso})"


# ---------------------------------------------------------------- pulsos
def rrc(alfa: float, sps: int, span: int = 8) -> np.ndarray:
    """Raiz de cosseno levantado com energia unitária."""
    t = np.arange(-span * sps, span * sps + 1) / sps
    h = np.empty_like(t)
    zero = np.isclose(t, 0.0)
    sing = np.isclose(np.abs(t), 1 / (4 * alfa)) if alfa > 0 else np.zeros_like(zero)
    reg = ~(zero | sing)
    tr = t[reg]
    h[reg] = (np.sin(np.pi * tr * (1 - alfa)) + 4 * alfa * tr * np.cos(np.pi * tr * (1 + alfa))) / (
        np.pi * tr * (1 - (4 * alfa * tr) ** 2))
    h[zero] = 1 - alfa + 4 * alfa / np.pi
    if alfa > 0:
        h[sing] = alfa / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * alfa))
                                      + (1 - 2 / np.pi) * np.cos(np.pi / (4 * alfa)))
    return h / np.sqrt(np.sum(h ** 2))


def gaussiano(bt: float, sps: int, span: int = 3) -> np.ndarray:
    """Filtro gaussiano de soma unitária, usado antes do integrador de fase FSK."""
    t = np.arange(-span * sps, span * sps + 1) / sps
    sigma = np.sqrt(np.log(2)) / (2 * np.pi * bt)
    g = np.exp(-t ** 2 / (2 * sigma ** 2))
    return g / g.sum()


def soma_movel(x: np.ndarray, n: int) -> np.ndarray:
    """saida[i] = soma de x[i:i+n]; comprimento len(x) - n + 1."""
    c = np.cumsum(np.concatenate(([0], x)))
    return c[n:] - c[:-n]


# ---------------------------------------------------------------- moduladores
def dif_codificar(bits: np.ndarray) -> np.ndarray:
    """Bits -> L+1 símbolos ±1. O bit 1 inverte a fase em relação ao símbolo anterior."""
    d = np.concatenate(([0], np.cumsum(bits) % 2))
    return 1.0 - 2.0 * d


def modular(bits: np.ndarray, sps: int, cfg: Config) -> np.ndarray:
    """Banda base complexa de um quadro (sem guarda), com pico unitário."""
    bits = np.asarray(bits, dtype=np.uint8)
    if cfg.esquema == "ook":
        env = np.repeat(bits.astype(float), sps)
        if cfg.pulso == "rampa":
            comprimento = max(1, int(sps * cfg.rampa))
            sobe = 0.5 * (1 - np.cos(np.pi * np.arange(comprimento) / comprimento))
            g = np.diff(np.concatenate(([0.0], sobe, [1.0])))
            env = np.convolve(env, g)[:len(env)]
        return env.astype(complex)
    if cfg.esquema == "fsk":
        nrz = np.repeat(2.0 * bits - 1.0, sps)
        if cfg.pulso == "gauss":
            g = gaussiano(cfg.bt, sps)
            borda = len(g) // 2
            nrz = np.convolve(np.pad(nrz, borda, mode="edge"), g, mode="valid")
        fase = np.pi * cfg.h / sps * (np.cumsum(nrz) - nrz / 2)
        return np.exp(1j * fase)
    simbolos = dif_codificar(bits)
    if cfg.pulso == "rrc":
        impulsos = np.zeros(len(simbolos) * sps)
        impulsos[::sps] = simbolos
        x = np.convolve(impulsos, rrc(cfg.alfa, sps, cfg.span))
        return (x / np.max(np.abs(x))).astype(complex)
    return np.repeat(simbolos, sps).astype(complex)


def amostras_do_quadro(n_bits: int, sps: int, cfg: Config) -> int:
    """Comprimento do sinal devolvido por `modular` para um quadro de n_bits."""
    if cfg.esquema != "dbpsk":
        return n_bits * sps
    return (n_bits + 1) * sps + (2 * cfg.span * sps if cfg.pulso == "rrc" else 0)


# ---------------------------------------------------------------- detectores
def filtro_casado(x: np.ndarray, sps: int, cfg: Config) -> np.ndarray:
    """Integra um bit (pulso retangular) ou aplica o RRC casado."""
    if cfg.esquema == "dbpsk" and cfg.pulso == "rrc":
        return np.convolve(x, rrc(cfg.alfa, sps, cfg.span)[::-1], mode="valid")
    return soma_movel(x, sps) / sps


def tons_fsk(x: np.ndarray, sps: int, cfg: Config):
    """Saídas dos correlatores não coerentes nos tons do bit 1 e do bit 0."""
    w = np.pi * cfg.h / sps
    n = np.arange(len(x))
    giro = np.exp(-1j * w * n)
    return soma_movel(x * giro, sps) / sps, soma_movel(x * np.conj(giro), sps) / sps


def fluxo(x: np.ndarray, sps: int, cfg: Config) -> np.ndarray:
    """Fluxo de decisão por amostra (real para OOK e FSK, complexo para DBPSK)."""
    if cfg.esquema == "ook":
        return np.abs(filtro_casado(x, sps, cfg))
    if cfg.esquema == "fsk":
        y1, y0 = tons_fsk(x, sps, cfg)
        return np.abs(y1) - np.abs(y0)
    y = filtro_casado(x, sps, cfg)
    return -y[sps:] * np.conj(y[:-sps])
