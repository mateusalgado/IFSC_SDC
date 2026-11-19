"""Métricas do enunciado: banda a 99%, BER teórica, PER e goodput."""
import numpy as np
from scipy.signal import welch
from scipy.special import erfc
from scipy.stats import ncx2


def q(x):
    return 0.5 * erfc(np.asarray(x) / np.sqrt(2))


def ber_bpsk(g):
    """BPSK coerente. g = Eb/N0 linear."""
    return q(np.sqrt(2 * g))


def ber_dbpsk(g):
    return 0.5 * np.exp(-g)


def ber_fsk_nc(g):
    """2-FSK ortogonal com detecção não coerente."""
    return 0.5 * np.exp(-g / 2)


def ber_ook_nc(g):
    """OOK com detecção de envoltória e limiar em metade da amplitude.

    g é o Eb/N0 médio; o bit 1 carrega 2Eb. P(e|0) segue Rayleigh e P(e|1), Rice.
    """
    g = np.asarray(g, dtype=float)
    return 0.5 * (np.exp(-g / 2) + ncx2.cdf(g, 2, 4 * g))


def psd(x: np.ndarray, fs: float, nfft: int = 8192):
    """Densidade espectral bilateral (Welch), com a frequência em ordem crescente."""
    f, p = welch(x, fs=fs, nperseg=nfft, return_onesided=False, detrend=False)
    ordem = np.argsort(f)
    return f[ordem], p[ordem]


def banda_99(x: np.ndarray, fs: float, fracao: float = 0.99, nfft: int = 8192, faixa=None):
    """Banda ocupada: faixa que deixa (1-fracao)/2 da potência de cada lado.

    `faixa` = (fmin, fmax) restringe a análise, por exemplo à janela do sinal em
    uma captura real. Devolve (largura, f_inferior, f_superior).
    """
    f, p = psd(x, fs, nfft)
    if faixa is not None:
        dentro = (f >= faixa[0]) & (f <= faixa[1])
        f, p = f[dentro], p[dentro]
    acumulado = np.cumsum(p) / np.sum(p)
    cauda = (1 - fracao) / 2
    f_inf = f[np.searchsorted(acumulado, cauda)]
    f_sup = f[min(np.searchsorted(acumulado, 1 - cauda), len(f) - 1)]
    return float(f_sup - f_inf), float(f_inf), float(f_sup)


def resumo_ensaio(enviados: dict, recebidos: list, duracao_s: float) -> dict:
    """PER, goodput e BER de um ensaio.

    enviados: {seq: payload} do log do transmissor. recebidos: lista de Pacote.
    Um pacote só conta como correto quando o payload é idêntico ao transmitido.
    A BER considera apenas os quadros aceitos pelo CRC; os perdidos entram na PER.
    """
    corretos, bits_ok, bits_err, bits_comp, errados = set(), 0, 0, 0, 0
    for p in recebidos:
        if p.seq not in enviados or p.seq in corretos:
            continue
        ref = enviados[p.seq]
        if p.payload == ref:
            corretos.add(p.seq)
            bits_ok += 8 * len(ref)
            bits_comp += 8 * len(ref)
        elif len(p.payload) == len(ref):
            errados += 1
            a = np.unpackbits(np.frombuffer(p.payload, np.uint8))
            b = np.unpackbits(np.frombuffer(ref, np.uint8))
            bits_err += int(np.sum(a != b))
            bits_comp += len(a)
    n = len(enviados)
    return {
        "transmitidos": n,
        "corretos": len(corretos),
        "aceitos_com_conteudo_errado": errados,
        "perdidos": n - len(corretos),
        "per": (n - len(corretos)) / n if n else float("nan"),
        "goodput_bps": bits_ok / duracao_s if duracao_s > 0 else float("nan"),
        "ber_quadros_aceitos": bits_err / bits_comp if bits_comp else float("nan"),
        "duracao_s": duracao_s,
    }
