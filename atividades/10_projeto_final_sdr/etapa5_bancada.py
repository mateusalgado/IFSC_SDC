"""Figuras dos ensaios de bancada com a OOK de referência (Pluto -> RTL-SDR).

Lê resultados/bancada_ook_referencia.json e a captura de 60 s, e grava
figuras/bancada_espectro.png e figuras/bancada_sensibilidade.png (PT e EN).
"""
import json

import matplotlib.pyplot as plt
import numpy as np

from figuras_util import CORES, RESULTADOS, TINTA, salvar
from sdrlink import metricas, radio
from sdrlink.receptor import cu8_para_complexo

RB = 10e3
BITS_PROTEGIDOS = 8 + 8 * 21 + 8        # comprimento, payload de 21 bytes e CRC-8


def banda_sem_rajadas(x, fs, desloc, n=1 << 14, janela=120e3):
    """Banda de 99% com e sem os blocos atingidos por rajadas de outros emissores.

    Na faixa de 915 MHz há dispositivos de terceiros que saltam em frequência; uma
    das posições fica 50 kHz acima da portadora. O piso vem do anel de 150 a 190 kHz.
    """
    blocos = np.abs(np.fft.fftshift(np.fft.fft(x[:len(x) // n * n].reshape(-1, n) * np.hanning(n), axis=1),
                                    axes=1)) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n, 1 / fs))
    anel = (np.abs(f - desloc) > 150e3) & (np.abs(f - desloc) < 190e3)
    dentro = np.abs(f - desloc) <= janela

    def b99(psd):
        util = np.maximum(psd[dentro] - psd[anel].mean(), 0)
        acum = np.cumsum(util) / util.sum()
        fd = f[dentro]
        return float(fd[np.searchsorted(acum, 0.005)]), float(fd[min(np.searchsorted(acum, 0.995), len(fd) - 1)])

    lateral = (f - desloc > 40e3) & (f - desloc < 60e3)
    energia = blocos[:, lateral].sum(1)
    tudo = b99(blocos.mean(0))
    limpo = b99(blocos[energia <= np.percentile(energia, 90)].mean(0))
    return {"f_inferior_hz": limpo[0], "f_superior_hz": limpo[1], "banda_99_hz": limpo[1] - limpo[0],
            "todos_os_blocos": {"f_inferior_hz": tudo[0], "f_superior_hz": tudo[1], "banda_99_hz": tudo[1] - tudo[0]},
            "blocos": int(len(blocos)), "fracao_de_blocos_com_rajada": float(np.mean(energia > 3 * np.median(energia))),
            "criterio": "descarta os 10% de blocos com mais energia entre +40 e +60 kHz da portadora"}


def main():
    dados = json.loads((RESULTADOS / "bancada_ook_referencia.json").read_text())
    fs, desloc = dados["fs_hz"], radio.DESLOC
    x = cu8_para_complexo(np.fromfile(radio.RAIZ / "capturas" / "ook_ref_ensaio_60s.cu8", dtype=np.uint8,
                                      count=2 * (1 << 24)))
    x -= x.mean()
    f, p = metricas.psd(x, fs, 1 << 14)
    piso = np.median(p)
    banda = banda_sem_rajadas(x, fs, desloc)
    dados["ensaio_longo"]["banda_analise"] = banda
    (RESULTADOS / "bancada_ook_referencia.json").write_text(json.dumps(dados, indent=2, ensure_ascii=False))

    def espectro(t):
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.25, 1]})
        ax[0].plot(f / 1e3, 10 * np.log10(p / piso), color=CORES["ook"], lw=1.2)
        ax[0].axvline(desloc / 1e3, color=TINTA, ls=":", lw=1)
        ax[0].annotate(t("portadora\n915,2 MHz", "carrier\n915.2 MHz"), (desloc / 1e3, 46), xytext=(330, 40),
                       fontsize=8.5, color=TINTA, arrowprops={"arrowstyle": "-", "color": TINTA, "lw": 0.8})
        ax[0].annotate(t("DC do receptor\ne OL do Pluto", "receiver DC and\nPluto LO leakage"), (0, 14),
                       xytext=(-620, 34), fontsize=8.5, color=TINTA,
                       arrowprops={"arrowstyle": "-", "color": TINTA, "lw": 0.8})
        ax[0].set(xlim=(-1200, 1200), ylim=(-6, 55), xlabel=t("Frequência em relação a 915 MHz (kHz)",
                                                               "Frequency relative to 915 MHz (kHz)"),
                  ylabel=t("PSD acima do piso de ruído (dB)", "PSD above the noise floor (dB)"),
                  title=t("Captura de 2,4 MHz", "2.4 MHz capture"))
        perto = np.abs(f - desloc) <= 130e3
        ax[1].plot((f[perto] - desloc) / 1e3, 10 * np.log10(p[perto] / piso), color=CORES["ook"], lw=1.4,
                   label=t("OOK de referência, 10 kbit/s", "Reference OOK, 10 kbit/s"))
        lim = [(banda["f_inferior_hz"] - desloc) / 1e3, (banda["f_superior_hz"] - desloc) / 1e3]
        ax[1].axvspan(*lim, color=CORES["ook"], alpha=0.10,
                      label=t(f"banda de 99%: {banda['banda_99_hz'] / 1e3:.0f} kHz (sem rajadas de terceiros)",
                              f"99% bandwidth: {banda['banda_99_hz'] / 1e3:.0f} kHz (third-party bursts removed)"))
        ax[1].set(xlim=(-130, 130), ylim=(-6, 55), xlabel=t("Frequência em relação à portadora (kHz)",
                                                             "Frequency relative to the carrier (kHz)"),
                  title=t("Sinal recebido e banda ocupada", "Received signal and occupied bandwidth"))
        ax[1].legend(loc="upper right")
        fig.suptitle(t("OOK de referência recebida pelo RTL-SDR (60 s, ganho 29,7 dB, 86 ppm)",
                       "Reference OOK received by the RTL-SDR (60 s, 29.7 dB gain, 86 ppm)"))
        fig.tight_layout()
        return fig

    medidas = dados["varredura_de_ganho_repeticao"]["medidas"]
    ebn0 = np.array([m["snr_20khz_db"] for m in medidas]) + 10 * np.log10(20e3 / RB)
    per = np.array([m["per"] for m in medidas])
    ganho = np.array([m["ganho_db"] for m in medidas])
    snr = np.array([m["snr_20khz_db"] for m in medidas])
    passada = np.array([m["passada"] for m in medidas])
    eixo = np.linspace(6, 20, 200)
    previsto = 1 - (1 - metricas.ber_ook_nc(10 ** (eixo / 10))) ** BITS_PROTEGIDOS
    tol = dados["tolerancia_a_offset"]
    deriva = dados["ensaio_longo"]["offset_ao_longo_do_tempo"]

    def sensibilidade(t):
        fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
        for k, marc in ((1, "o"), (2, "s")):
            sel = passada == k
            ordem = np.argsort(ganho[sel])
            ax[0].plot(ganho[sel][ordem], snr[sel][ordem], marker=marc, color=CORES["ook"],
                       ls="-" if k == 1 else "--", label=t(f"passada {k}", f"pass {k}"))
        ax[0].set(xlabel=t("Ganho do RTL-SDR (dB)", "RTL-SDR gain (dB)"),
                  ylabel=t("S/N em 20 kHz (dB)", "S/N in 20 kHz (dB)"),
                  title=t("Relação sinal-ruído e ganho", "Signal-to-noise ratio and gain"))
        ax[0].legend(loc="lower right")
        ax[1].semilogy(eixo, previsto, color=TINTA, lw=1.6,
                       label=t("previsão (BER teórica, 184 bits)", "prediction (theoretical BER, 184 bits)"))
        ax[1].semilogy(ebn0, np.maximum(per, 2e-3), "o", color=CORES["ook"],
                       label=t("medido (5 s por ponto)", "measured (5 s per point)"))
        ax[1].axhline(0.01, color=TINTA, ls=":", lw=1)
        ax[1].text(19.8, 0.012, "PER 1%", ha="right", fontsize=8.5, color=TINTA)
        ax[1].set(xlim=(-8, 30), ylim=(1.5e-3, 1.5), xlabel=t("Eb/N0 estimado (dB)", "Estimated Eb/N0 (dB)"),
                  ylabel="PER", title=t("PER e relação sinal-ruído", "PER and signal-to-noise ratio"))
        ax[1].legend(loc="lower left")
        ax[2].plot([d["erro_hz"] / 1e3 for d in tol], [d["per"] for d in tol], "o-", color=CORES["ook"],
                   label=t("PER com erro de sintonia", "PER with tuning error"))
        ax[2].set(xlabel=t("Erro de sintonia aplicado (kHz)", "Applied tuning error (kHz)"), ylabel="PER",
                  ylim=(-0.05, 1.05), title=t("Tolerância a offset (2619 quadros)", "Offset tolerance (2619 frames)"))
        ax[2].axvline(0.9152, color=TINTA, ls=":", lw=1)
        ax[2].text(1.1, 0.5, "1 ppm", fontsize=8.5, color=TINTA)
        ax[2].legend(loc="upper left")
        fig.suptitle(t("Sensibilidade medida da OOK de referência", "Measured sensitivity of the reference OOK"))
        fig.tight_layout()
        return fig

    salvar(espectro, "bancada_espectro.png")
    salvar(sensibilidade, "bancada_sensibilidade.png")
    print("deriva do offset em 60 s:", deriva[0]["offset_hz"], "->", deriva[-1]["offset_hz"], "Hz")


if __name__ == "__main__":
    main()
