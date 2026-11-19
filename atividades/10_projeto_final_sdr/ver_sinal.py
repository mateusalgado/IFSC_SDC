"""Mostra ao vivo o que o RTL-SDR recebe: espectro, portadora e envoltória.

    .venv/bin/python ver_sinal.py --ppm 86            # janela ao vivo; feche para sair
    .venv/bin/python ver_sinal.py --ppm 86 --salvar resultados/ver_sinal.png

Painéis: espectro da captura inteira (2,4 MHz), zoom de ±60 kHz em torno da
portadora esperada (915,2 MHz) e envoltória de 30 ms depois de um filtro de
±20 kHz, onde aparecem os bits da OOK e o intervalo de guarda entre quadros.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
import numpy as np
from scipy.signal import resample_poly

from sdrlink import radio

N = 1 << 19      # amostras por atualização (~0,22 s)
NFFT = 1 << 14


def analisar(x, fs, desloc):
    x = x - x.mean()
    blocos = x[:len(x) // NFFT * NFFT].reshape(-1, NFFT) * np.hanning(NFFT)
    p = np.mean(np.abs(np.fft.fftshift(np.fft.fft(blocos, axis=1), axes=1)) ** 2, axis=0)
    f = np.fft.fftshift(np.fft.fftfreq(NFFT, 1 / fs))
    db = 10 * np.log10(p / np.median(p))
    perto = np.abs(f - desloc) <= 60e3
    pico = f[perto][np.argmax(db[perto])]
    y = resample_poly(x * np.exp(-2j * np.pi * desloc / fs * np.arange(len(x))), 1, 60)   # 40 kHz
    return f, db, pico, np.abs(y)[40:1240]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ppm", type=int, default=0)
    ap.add_argument("--freq", type=float, default=radio.FC)
    ap.add_argument("--desloc", type=float, default=radio.DESLOC)
    ap.add_argument("--ganho", type=float, default=radio.GANHO_RX)
    ap.add_argument("--salvar", type=Path, help="grava um PNG e sai, sem abrir janela")
    args = ap.parse_args()
    fs = radio.FS_RX
    matplotlib.use("Agg" if args.salvar else ("MacOSX" if sys.platform == "darwin" else "TkAgg"))
    import matplotlib.pyplot as plt

    radio.preparar_bibliotecas()
    from rtlsdr import RtlSdr
    sdr = RtlSdr()
    sdr.sample_rate = fs
    if args.ppm != sdr.freq_correction:
        sdr.freq_correction = args.ppm
    sdr.center_freq = args.freq
    sdr.gain = args.ganho
    sdr.read_samples(1 << 16)

    fig, ax = plt.subplots(3, 1, figsize=(11, 8.5))
    f, db, pico, env = analisar(np.asarray(sdr.read_samples(N)), fs, args.desloc)
    mhz = (args.freq + f) / 1e6
    l0, = ax[0].plot(mhz, db, lw=0.8, color="#2a78d6")
    ax[0].axvline((args.freq + args.desloc) / 1e6, color="#eb6834", ls="--", lw=1, label="portadora esperada")
    ax[0].set(ylim=(-5, 60), xlabel="Frequência (MHz)", ylabel="dB acima do piso", title="Espectro da captura")
    ax[0].legend(loc="upper left")
    perto = np.abs(f - args.desloc) <= 60e3
    l1, = ax[1].plot((f[perto] - args.desloc) / 1e3, db[perto], lw=1.2, color="#2a78d6")
    marca = ax[1].axvline((pico - args.desloc) / 1e3, color="#eb6834", ls="--", lw=1)
    ax[1].set(ylim=(-5, 60), xlabel="Frequência em relação a 915,2 MHz (kHz)", ylabel="dB acima do piso")
    l2, = ax[2].plot(np.arange(len(env)) / 40, env, lw=0.9, color="#2a78d6")
    ax[2].set(xlabel="Tempo (ms)", ylabel="Envoltória", title="Envoltória em ±20 kHz (bits da OOK)")
    fig.tight_layout()

    def atualizar():
        f, db, pico, env = analisar(np.asarray(sdr.read_samples(N)), fs, args.desloc)
        l0.set_ydata(db)
        l1.set_ydata(db[perto])
        marca.set_xdata([(pico - args.desloc) / 1e3] * 2)
        l2.set_ydata(env)
        ax[2].set_ylim(0, max(1.15 * env.max(), 0.02))
        ax[1].set_title(f"Portadora: {(args.freq + pico) / 1e6:.4f} MHz, {pico - args.desloc:+.0f} Hz do esperado, "
                        f"{db[perto].max():.0f} dB acima do piso (resolução {fs / NFFT:.0f} Hz)")

    atualizar()
    if args.salvar:
        fig.savefig(args.salvar, dpi=110)
        print(args.salvar)
    else:
        plt.show(block=False)
        try:
            while plt.fignum_exists(fig.number):
                atualizar()
                fig.canvas.draw_idle()
                plt.pause(0.05)
        except KeyboardInterrupt:
            pass
    sdr.close()


if __name__ == "__main__":
    main()
