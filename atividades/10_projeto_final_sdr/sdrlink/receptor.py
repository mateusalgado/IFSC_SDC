"""Receptor de pacotes: conversão para banda base, sincronismo, decisão e CRC.

O processamento é o mesmo para as três modulações depois do detector:
correlação com os 29 bits conhecidos (preâmbulo + Barker-13), leitura dos bits
a cada `sps` amostras, verificação do CRC-16 e registro das métricas.
"""
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from scipy.signal import resample_poly

from . import quadro
from .modem import Config, filtro_casado, tons_fsk

_T = 2.0 * quadro.CABECALHO_SINC - 1.0
_T0 = _T - _T.mean()
_L = len(_T)


@dataclass
class Pacote:
    seq: int
    payload: bytes
    tempo_s: float       # início do quadro, em relação ao início da captura
    rho: float           # correlação normalizada do sincronismo (0 a 1)
    offset_hz: float     # offset de frequência estimado no cabeçalho
    duplicado: bool = False


def cu8_para_complexo(bruto: np.ndarray) -> np.ndarray:
    """Amostras I/Q intercaladas de 8 bits (formato do RTL-SDR) -> complex64."""
    v = bruto.astype(np.float32)
    v -= 127.5
    v /= 127.5
    return v[0::2] + 1j * v[1::2]


def preparar(x: np.ndarray, fs: float, rb: float, sps: int, f_desloc: float = 0.0,
             n0: int = 0) -> np.ndarray:
    """Desloca o sinal de f_desloc para 0 Hz e reamostra para rb*sps (sps inteiro)."""
    n = np.arange(n0, n0 + len(x), dtype=np.float64)
    x = (x * np.exp(-2j * np.pi * (f_desloc / fs) * n)).astype(np.complex64)
    razao = Fraction(int(round(rb * sps)), int(round(fs)))
    if razao == 1:
        return x
    return resample_poly(x, razao.numerator, razao.denominator).astype(np.complex64)


def detector(x: np.ndarray, sps: int, cfg: Config):
    """Fluxo de decisão e saídas complexas auxiliares (para estimar o offset)."""
    if cfg.esquema == "ook":
        y = filtro_casado(x, sps, cfg)
        return np.abs(y), (y,)
    if cfg.esquema == "fsk":
        y1, y0 = tons_fsk(x, sps, cfg)
        return np.abs(y1) - np.abs(y0), (y1, y0)
    y = filtro_casado(x, sps, cfg)
    return -y[sps:] * np.conj(y[:-sps]), ()


def _metrica(s: np.ndarray, sps: int):
    """Correlação de Pearson entre o fluxo e os 29 bits conhecidos, por amostra."""
    m = len(s) - (_L - 1) * sps
    num = np.zeros(m, dtype=s.dtype)
    soma = np.zeros(m, dtype=s.dtype)
    energia = np.zeros(m, dtype=np.float64)
    for k in range(_L):
        trecho = s[k * sps:k * sps + m]
        num += _T0[k] * trecho
        soma += trecho
        energia += np.abs(trecho) ** 2
    var = np.maximum(energia - np.abs(soma) ** 2 / _L, 1e-30)
    rho = num / np.sqrt(var * np.sum(_T0 ** 2))
    return (np.abs(rho) if np.iscomplexobj(rho) else rho), rho


def _ler(v: np.ndarray, pos: float, k0: int, n: int, sps: int):
    """Lê n valores espaçados de sps a partir do bit k0, com interpolação linear."""
    p = pos + (k0 + np.arange(n)) * sps
    i = np.floor(p).astype(np.int64)
    if i[0] < 0 or i[-1] + 1 >= len(v):
        return None
    f = p - i
    return v[i] * (1 - f) + v[i + 1] * f


def _offset(aux, pos: float, sps: int, cfg: Config, rb: float) -> float:
    """Offset de frequência pelos bits 1 (e 0, no FSK) do preâmbulo alternado."""
    if cfg.esquema == "ook":
        v = _ler(aux[0], pos, 0, 16, sps)[0::2]
        acum = np.sum(v[1:] * np.conj(v[:-1]))
    else:
        v1 = _ler(aux[0], pos, 0, 16, sps)[0::2]
        v0 = _ler(aux[1], pos, 0, 16, sps)[1::2]
        giro = np.exp(2j * np.pi * cfg.h)
        acum = np.sum(v1[1:] * np.conj(v1[:-1])) * giro + np.sum(v0[1:] * np.conj(v0[:-1])) * np.conj(giro)
    return float(np.angle(acum) * rb / (4 * np.pi))


def _decodificar(s, aux, pos: float, sps: int, cfg: Config, rb: float, formato: str = "projeto"):
    cab = _ler(s, pos, 0, _L, sps)
    if cab is None:
        return None
    limiar, giro, offset = 0.0, 1.0, 0.0
    if cfg.esquema == "dbpsk":
        angulo = np.angle(np.sum(cab * _T0))
        giro = np.exp(-1j * angulo)
        offset = float(angulo * rb / (2 * np.pi))
    elif cfg.esquema == "ook":
        limiar = 0.5 * (cab[_T > 0].mean() + cab[_T < 0].mean())

    def bits(k0, n):
        v = _ler(s, pos, k0, n, sps)
        return None if v is None else (np.real(v * giro) > limiar).astype(np.uint8)

    if formato == "referencia":     # [comprimento 8][payload][CRC-8 só do payload], sem sequência
        tamanho = bits(_L, 8)
        if tamanho is None:
            return None
        n_payload = quadro.bits_para_bytes(tamanho)[0]
        resto = bits(_L + 8, 8 * n_payload + 8)
        if resto is None:
            return None
        dados = quadro.bits_para_bytes(resto)
        if quadro.crc8(dados[:-1]) != dados[-1]:
            return False
        return -1, dados[:-1], (_offset(aux, pos, sps, cfg, rb) if cfg.esquema != "dbpsk" else offset)
    cabecalho = bits(_L, 24)
    if cabecalho is None:
        return None
    campos = quadro.bits_para_bytes(cabecalho)
    n_payload = campos[0]
    resto = bits(_L + 24, 8 * n_payload + 16)
    if resto is None:
        return None
    dados = campos + quadro.bits_para_bytes(resto)
    if quadro.crc16(dados[:-2]) != int.from_bytes(dados[-2:], "big"):
        return False
    if cfg.esquema != "dbpsk":
        offset = _offset(aux, pos, sps, cfg, rb)
    return int.from_bytes(dados[1:3], "big"), dados[3:-2], offset


def receber(x: np.ndarray, sps: int, cfg: Config, rb: float, limiar: float = 0.6,
            bloco: int = 1 << 21, formato: str = "projeto"):
    """Procura e decodifica todos os quadros de um sinal já em banda base a rb*sps.

    Devolve a lista de pacotes com CRC válido e um dicionário de contadores.
    formato="referencia" lê o quadro original do professor (CRC-8, sem sequência);
    nesse caso os pacotes recebem seq = -1 e nenhum é marcado como duplicado.
    """
    s, aux = detector(x, sps, cfg)
    alcance = (_L - 1) * sps
    total = len(s) - alcance
    pacotes, vistos = [], set()
    cont = {"candidatos": 0, "crc_invalido": 0, "validos": 0, "duplicados": 0}
    pos = 0
    while pos < total:
        fim = min(pos + bloco, total)
        m, rho = _metrica(s[pos:fim + alcance], sps)
        acima = np.flatnonzero(m > limiar)
        prox = 0
        while True:
            j = np.searchsorted(acima, prox)
            if j >= len(acima):
                prox = max(prox, len(m))
                break
            i = int(acima[j])
            if i + 4 * sps + 1 > len(m) and fim < total and i > 0:
                prox = i          # a janela do pico cruza o bloco: recomeça nele
                break
            pico = i + int(np.argmax(m[i:i + 4 * sps + 1]))
            while True:     # sobe até o máximo local: o cruzamento pode ser um lóbulo do preâmbulo
                novo = pico + int(np.argmax(m[pico:pico + sps + 1]))
                if novo == pico:
                    break
                pico = novo
            delta = 0.0
            if 0 < pico < len(m) - 1:
                a, b, c = m[pico - 1], m[pico], m[pico + 1]
                if b > min(a, c):
                    delta = float(np.clip((c - a) / (2 * (b - min(a, c))), -0.5, 0.5))
            cont["candidatos"] += 1
            inicio = pos + pico + delta
            res = _decodificar(s, aux, inicio, sps, cfg, rb, formato)
            if res:
                seq, payload, offset = res
                dup = seq >= 0 and seq in vistos
                vistos.add(seq)
                cont["duplicados" if dup else "validos"] += 1
                pacotes.append(Pacote(seq, payload, inicio / (rb * sps), float(m[pico]), offset, dup))
                tamanho = (quadro.bits_do_quadro_referencia(len(payload)) - quadro.BITS_GUARDA
                           if formato == "referencia" else quadro.bits_do_quadro(len(payload), guarda=False))
                prox = pico + (tamanho - 1) * sps
            else:
                if res is False:
                    cont["crc_invalido"] += 1
                prox = pico + sps
        pos += max(prox, 1)
    return pacotes, cont
