"""Parâmetros comuns dos scripts de bancada e carga das bibliotecas nativas."""
import argparse
import os
import sys
from pathlib import Path

from .modem import ESQUEMAS, Config

# Valores do código de referência do professor (frequência e ganho autorizados).
FC = 915e6          # frequência central, Hz
DESLOC = 200e3      # deslocamento do sinal em relação a FC, Hz (longe do DC do RTL-SDR)
FS_TX = 2e6         # taxa de amostragem do Pluto, Hz
FS_RX = 2.4e6       # taxa de amostragem do RTL-SDR, Hz
GANHO_TX = -20.0    # dB (0 é a potência máxima do Pluto)
GANHO_RX = 30.0     # dB, ganho manual do RTL-SDR (AGC desligado)
AMPLITUDE = 2 ** 14
RAIZ = Path(__file__).resolve().parents[1]

# Roteiros de bancada: sequências (esquema, pulso, taxa de bits) que o transmissor
# percorre sozinho e o receptor reconhece testando cada configuração.
_BASICO = [("ook", "ret", 10e3), ("fsk", "ret", 10e3), ("dbpsk", "ret", 10e3)]
_PULSOS = [("ook", "rampa", 10e3), ("fsk", "gauss", 10e3), ("dbpsk", "rrc", 10e3)]
_TAXAS = [("ook", "ret", 20e3), ("fsk", "ret", 20e3), ("dbpsk", "ret", 20e3), ("dbpsk", "rrc", 20e3),
          ("ook", "ret", 50e3), ("fsk", "ret", 50e3), ("dbpsk", "ret", 50e3), ("dbpsk", "rrc", 50e3),
          ("fsk", "gauss", 100e3), ("dbpsk", "rrc", 100e3), ("dbpsk", "rrc", 200e3)]
ROTEIROS = {"basico": _BASICO, "pulsos": _PULSOS, "taxas": _TAXAS, "completo": _BASICO + _PULSOS + _TAXAS}


def preparar_bibliotecas():
    """No macOS, deixa o ctypes encontrar libiio e librtlsdr instaladas fora de /usr/lib."""
    if sys.platform == "darwin":
        pastas = [str(Path(sys.prefix) / "lib"), "/usr/local/lib", "/usr/lib"]
        atual = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH")
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(([atual] if atual else []) + pastas)


def argumentos_modem(ap: argparse.ArgumentParser):
    ap.add_argument("--esquema", choices=ESQUEMAS, default="ook")
    ap.add_argument("--pulso", default="ret", help="ook: ret|rampa; fsk: ret|gauss; dbpsk: ret|rrc")
    ap.add_argument("--rb", type=float, default=10e3, help="taxa de bits, bit/s")
    ap.add_argument("--h", type=float, default=1.0, help="índice de modulação FSK")
    ap.add_argument("--bt", type=float, default=0.5, help="BT do filtro gaussiano")
    ap.add_argument("--alfa", type=float, default=0.35, help="roll-off do RRC")


def config_de(args) -> Config:
    return Config(esquema=args.esquema, pulso=args.pulso, h=args.h, bt=args.bt, alfa=args.alfa)
