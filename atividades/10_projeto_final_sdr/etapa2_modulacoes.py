"""Etapa 2: formas de onda, espectros com banda de 99% e constelação BPSK.

Parâmetros da referência: Rb = 10 kbit/s e fs = 2 MS/s (200 amostras por bit).
Gera figuras em figuras/ e figuras/en/ e os números em resultados/etapa2.json.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from figuras_util import CORES, TINTA, gravar_json, salvar, virgula
from sdrlink import canal, metricas, quadro
from sdrlink.modem import Config, filtro_casado, fluxo, modular

RB, FS = 10e3, 2e6
SPS = int(FS / RB)
SEMENTE = 20261
VARIANTES = [Config("ook"), Config("ook", "rampa"), Config("fsk"), Config("fsk", "gauss"),
             Config("dbpsk"), Config("dbpsk", "rrc")]
# Largura teórica entre os primeiros nulos (ou banda absoluta, no RRC), em múltiplos de Rb.
NULOS = {("ook", "ret"): 2.0, ("ook", "rampa"): None, ("fsk", "ret"): 3.0, ("fsk", "gauss"): None,
         ("dbpsk", "ret"): 2.0, ("dbpsk", "rrc"): 1.35}


def nome(cfg, t):
    pulsos = {"ret": t("retangular", "rectangular"), "rampa": t("rampa de 10%", "10% ramp"),
              "gauss": "gaussiano BT = 0,5" if t("a", "b") == "a" else "Gaussian BT = 0.5",
              "rrc": "RRC α = 0,35" if t("a", "b") == "a" else "RRC α = 0.35"}
    return pulsos[cfg.pulso]


# ---------------------------------------------------------------- formas de onda
def formas_de_onda():
    bits = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0], dtype=np.uint8)
    n_bits, tb = len(bits), 1e3 / RB                       # duração do bit em ms
    t_bit = np.arange(n_bits * SPS) / FS * 1e3
    sinais = {(c.esquema, c.pulso): modular(bits, SPS, c) for c in VARIANTES}

    def desenhar(t):
        fig, eixos = plt.subplots(4, 1, figsize=(9, 8.2), sharex=True, constrained_layout=True)
        ax = eixos[0]
        ax.step(np.arange(n_bits + 1) * tb, np.append(bits, bits[-1]), where="post", color=TINTA)
        for k, b in enumerate(bits):
            ax.text((k + 0.5) * tb, 1.22, str(b), ha="center", va="bottom", color=TINTA, fontsize=9)
        ax.set_ylim(-0.2, 1.75)
        ax.set_yticks([0, 1])
        ax.set_title(t("Bits transmitidos (Rb = 10 kbit/s, 200 amostras por bit)",
                       "Transmitted bits (Rb = 10 kbit/s, 200 samples per bit)"))

        ax = eixos[1]
        ax.plot(t_bit, sinais["ook", "ret"].real, color=CORES["ook"], label=nome(Config("ook"), t))
        ax.plot(t_bit, sinais["ook", "rampa"].real, color=TINTA, ls="--", lw=1.6,
                label=nome(Config("ook", "rampa"), t) + t(" (referência)", " (reference)"))
        ax.set_ylabel(t("envoltória", "envelope"))
        ax.set_title(t("OOK: envoltória", "OOK: envelope"))
        ax.set_ylim(-0.15, 1.3)

        ax = eixos[2]
        for pulso, cor, ls, lw in (("ret", CORES["fsk"], "-", 2.0), ("gauss", TINTA, "--", 1.6)):
            x = sinais["fsk", pulso]
            f_inst = np.diff(np.unwrap(np.angle(x))) * FS / (2 * np.pi) / 1e3
            ax.plot(t_bit[1:], f_inst, color=cor, ls=ls, lw=lw, label=nome(Config("fsk", pulso), t))
        ax.set_ylabel(t("frequência (kHz)", "frequency (kHz)"))
        ax.set_title(t("2-FSK, h = 1: frequência instantânea (desvio de ±Rb/2)",
                       "2-FSK, h = 1: instantaneous frequency (±Rb/2 deviation)"))
        ax.set_ylim(-7.5, 9.5)

        ax = eixos[3]
        ret = sinais["dbpsk", "ret"].real                   # n_bits + 1 símbolos; o primeiro é a referência
        ax.plot((np.arange(len(ret)) / SPS - 1) * tb, ret, color=CORES["dbpsk"], label=nome(Config("dbpsk"), t))
        rrc = sinais["dbpsk", "rrc"].real
        cfg = Config("dbpsk", "rrc")
        t_rrc = ((np.arange(len(rrc)) - cfg.span * SPS) / SPS - 0.5) * tb
        ax.plot(t_rrc, rrc, color=TINTA, ls="--", lw=1.6, label=nome(cfg, t))
        ax.axvspan(-tb, 0, color="#8a9a94", alpha=0.18, lw=0)
        ax.text(-tb / 2, -1.42, t("símbolo de\nreferência", "reference\nsymbol"), ha="center", va="center",
                fontsize=7.5, color=TINTA)
        ax.set_ylabel(t("parte real", "real part"))
        ax.set_title(t("DBPSK: o bit 1 inverte a fase em relação ao símbolo anterior",
                       "DBPSK: a 1 bit flips the phase relative to the previous symbol"))
        ax.set_ylim(-1.75, 1.75)
        ax.set_xlabel(t("tempo (ms)", "time (ms)"))
        ax.set_xlim(-tb, n_bits * tb)
        for ax in eixos[1:]:
            ax.legend(loc="upper right", ncol=2)
        for ax in eixos:
            for k in range(n_bits + 1):
                ax.axvline(k * tb, color="#8a9a94", lw=0.5, alpha=0.5)
        return fig

    salvar(desenhar, "formas_de_onda.png")


# ---------------------------------------------------------------- espectros
def espectros():
    rng = np.random.default_rng(SEMENTE)
    blocos = [rng.integers(0, 2, 20000).astype(np.uint8) for _ in range(3)]
    dados, curvas = [], {}
    for cfg in VARIANTES:
        sinais = [modular(b, SPS, cfg) for b in blocos]
        bandas = [metricas.banda_99(x, FS)[0] / RB for x in sinais]     # um valor por bloco de 20.000 bits
        x = np.concatenate(sinais)
        f, p = metricas.psd(x, FS)
        curvas[cfg.esquema, cfg.pulso] = (f / 1e3, 10 * np.log10(p / p.max() + 1e-16))
        media = float(np.mean(bandas))
        dados.append({
            "esquema": cfg.esquema, "pulso": cfg.pulso, "rotulo": cfg.rotulo,
            "banda99_rb": media, "banda99_rb_min": float(np.min(bandas)), "banda99_rb_max": float(np.max(bandas)),
            "banda99_hz_a_10kbps": media * RB,
            "largura_entre_nulos_teorica_rb": NULOS[cfg.esquema, cfg.pulso],
            "papr_db": float(10 * np.log10(np.max(np.abs(x) ** 2) / np.mean(np.abs(x) ** 2))),
            "rb_max_para_1mhz_bps": 1e6 / media,
        })
    banda = {(d["esquema"], d["pulso"]): d["banda99_rb"] for d in dados}

    def desenhar(t):
        fig, eixos = plt.subplots(1, 3, figsize=(12.5, 4.6), sharey=True, constrained_layout=True)
        paineis = [("ook", "rampa", "OOK", 80), ("fsk", "gauss", "2-FSK (h = 1)", 40), ("dbpsk", "rrc", "DBPSK", 150)]
        for ax, (esq, alt, titulo, lim) in zip(eixos, paineis):
            for pulso, cor, ls, lw in (("ret", CORES[esq], "-", 1.6), (alt, TINTA, "--", 1.3)):
                f, p = curvas[esq, pulso]
                b = banda[esq, pulso]
                rot = f"{nome(Config(esq, pulso), t)}: B99 = " + t(f"{virgula(b)} Rb", f"{b:.2f} Rb")
                ax.plot(f, p, color=cor, ls=ls, lw=lw, label=rot)
                for lado in (-1, 1):
                    ax.axvline(lado * b * RB / 2e3, color=cor, ls=":", lw=1.4)
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-90, 22)
            ax.set_title(titulo)
            ax.set_xlabel(t("frequência em banda base (kHz)", "baseband frequency (kHz)"))
            ax.legend(loc="upper center", fontsize=8)
        eixos[0].set_ylabel(t("PSD relativa ao pico (dB)", "PSD relative to peak (dB)"))
        fig.suptitle(t("Espectros a 10 kbit/s; as linhas pontilhadas delimitam 99% da potência",
                       "Spectra at 10 kbit/s; dotted lines bound 99% of the power"), color="#285b42")
        return fig

    salvar(desenhar, "espectros.png")
    return dados


# ---------------------------------------------------------------- constelação
def constelacao():
    rng = np.random.default_rng(SEMENTE + 1)
    sps, ebn0, n_quadro = 8, 10.0, quadro.bits_do_quadro(128, guarda=False)   # 1093 bits no ar
    df_t = 300.0 / RB                                       # offset de 300 Hz normalizado pela taxa de bits
    cfg = Config("dbpsk")
    bits = rng.integers(0, 2, n_quadro).astype(np.uint8)
    simbolos = 1.0 - 2.0 * bits
    x = np.repeat(simbolos, sps).astype(complex)
    var = canal.variancia_ruido(1.0, sps, ebn0)

    def saida(sinal):
        return filtro_casado(sinal + canal.ruido(len(sinal), var, rng), sps, cfg)[::sps]

    y_awgn = saida(x)
    y_fase = saida(canal.girar(x, fase=np.radians(30)))
    y_off = saida(canal.girar(x, df_t / sps))
    # Produto diferencial com o mesmo offset: os bits viram símbolos pela codificação diferencial.
    xd = canal.girar(modular(bits, sps, cfg), df_t / sps)
    z = fluxo(xd + canal.ruido(len(xd), var, rng), sps, cfg)[::sps]
    passo = 360 * df_t
    erros = {"awgn": int(np.sum((y_awgn.real < 0) != (bits == 1))),
             "fase_30": int(np.sum((y_fase.real < 0) != (bits == 1))),
             "offset_sem_rastreio": int(np.sum((y_off.real < 0) != (bits == 1))),
             "dbpsk_com_offset": int(np.sum((z.real > 0) != (bits == 1)))}

    def desenhar(t):
        fig, eixos = plt.subplots(2, 2, figsize=(9.2, 9.6), constrained_layout=True)
        cor = CORES["bpsk"]
        for ax in eixos.flat:
            ax.set_aspect("equal")
            ax.set_xlim(-1.8, 1.8)
            ax.set_ylim(-1.8, 1.8)
            ax.axhline(0, color="#8a9a94", lw=0.8)
            ax.axvline(0, color="#8a9a94", lw=0.8)
            ax.set_xlabel(t("em fase (I)", "in phase (I)"))
            ax.set_ylabel(t("quadratura (Q)", "quadrature (Q)"))
        ideal = dict(marker="+", color=TINTA, ms=13, mew=2.2, ls="none", label=t("pontos ideais", "ideal points"))

        ax = eixos[0, 0]
        ax.plot(y_awgn.real, y_awgn.imag, ".", color=cor, ms=4, alpha=0.6, label=t("saída do filtro casado", "matched-filter output"))
        ax.plot([-1, 1], [0, 0], **ideal)
        ax.set_title(t("AWGN, Eb/N0 = 10 dB\nfase e frequência ideais", "AWGN, Eb/N0 = 10 dB\nideal phase and frequency"), fontsize=9.5)
        ax.legend(loc="upper right")

        ax = eixos[0, 1]
        ax.plot(y_fase.real, y_fase.imag, ".", color=cor, ms=4, alpha=0.6, label=t("saída do filtro casado", "matched-filter output"))
        ax.plot([-1, 1], [0, 0], **ideal)
        ax.plot([-1.6 * np.cos(np.radians(30)), 1.6 * np.cos(np.radians(30))],
                [-1.6 * np.sin(np.radians(30)), 1.6 * np.sin(np.radians(30))], color=TINTA, ls="--", lw=1.2,
                label=t("eixo girado de 30°", "axis rotated by 30°"))
        ax.set_title(t("Erro de fase estático de 30°\na projeção em I cai para cos 30° = 0,87",
                       "Static 30° phase error\nthe I projection drops to cos 30° = 0.87"), fontsize=9.5)
        ax.legend(loc="upper right")

        ax = eixos[1, 0]
        mapa = LinearSegmentedColormap.from_list("verdes", plt.get_cmap("Greens")(np.linspace(0.25, 1, 64)))
        pontos = ax.scatter(y_off.real, y_off.imag, c=np.arange(n_quadro), cmap=mapa, s=6,
                            label=t("símbolos do quadro (cor = posição)", "frame symbols (colour = position)"))
        k = np.arange(9)
        ax.plot(np.cos(np.radians(passo * k)), np.sin(np.radians(passo * k)), "o-", color=TINTA, ms=5, lw=1.2,
                mfc="white", label=t("fase do símbolo +1, bits 0 a 8", "phase of a +1 symbol, bits 0 to 8"))
        caixa = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9)
        seta = dict(arrowstyle="-", color=TINTA, lw=0.8)
        ax.annotate("k = 0", (1, 0), (1.3, -1.55), fontsize=8.5, color=TINTA, ha="center", bbox=caixa, arrowprops=seta)
        ax.annotate(f"k = 8: {passo * 8:.0f}°", (np.cos(np.radians(passo * 8)), np.sin(np.radians(passo * 8))),
                    (-1.05, 1.6), fontsize=8.5, color=TINTA, ha="center", bbox=caixa, arrowprops=seta)
        barra = fig.colorbar(pontos, ax=ax, fraction=0.046, pad=0.03)
        barra.set_label(t("índice do símbolo no quadro", "symbol index in the frame"))
        ax.set_title(t(f"Offset de 300 Hz a 10 kbit/s sem rastreio\n{virgula(passo, 1)}° por bit, {virgula(df_t * n_quadro, 1)} voltas por quadro",
                       f"300 Hz offset at 10 kbit/s, no tracking\n{passo:.1f}° per bit, {df_t * n_quadro:.1f} turns per frame"), fontsize=9.5)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8)

        ax = eixos[1, 1]
        ax.plot(z.real, z.imag, ".", color=cor, ms=4, alpha=0.6, label=t("produto diferencial z", "differential product z"))
        c, s = np.cos(np.radians(passo)), np.sin(np.radians(passo))
        ax.plot([-1.6 * c, 1.6 * c], [-1.6 * s, 1.6 * s], color=TINTA, ls="--", lw=1.2,
                label=t(f"giro comum de {virgula(passo, 1)}°", f"common rotation of {passo:.1f}°"))
        ax.plot([-c, c], [-s, s], **ideal)
        ax.set_title(t("DBPSK com o mesmo offset\na decisão é preservada",
                       "DBPSK with the same offset\ndecisions are preserved"), fontsize=9.5)
        ax.legend(loc="upper right")
        fig.suptitle(t("Constelação BPSK na saída do filtro casado (pulso retangular)",
                       "BPSK constellation at the matched-filter output (rectangular pulse)"), color="#285b42")
        return fig

    salvar(desenhar, "constelacao_bpsk.png")
    return {"ebn0_db": ebn0, "bits_por_quadro": n_quadro, "offset_hz": 300.0, "rb_bps": RB,
            "giro_por_bit_graus": passo, "bits_ate_90_graus": 90 / passo, "voltas_por_quadro": df_t * n_quadro,
            "projecao_com_30_graus": float(np.cos(np.radians(30))), "erros_em_um_quadro": erros}


if __name__ == "__main__":
    formas_de_onda()
    variantes = espectros()
    const = constelacao()
    gravar_json("etapa2.json", {
        "parametros": {"rb_bps": RB, "fs_hz": FS, "amostras_por_bit": SPS, "semente": SEMENTE,
                       "bits_por_bloco": 20000, "blocos": 3, "definicao_banda": "0,5% da potencia fora de cada lado"},
        "conferencia_bpsk_retangular": {"banda99_teorica_continua_rb": 20.57, "banda99_teorica_200_amostras_rb": 20.39},
        "variantes": variantes,
        "constelacao": const,
    })
    for v in variantes:
        print(f"{v['rotulo']:16s} B99 = {v['banda99_rb']:6.2f} Rb [{v['banda99_rb_min']:.2f}, {v['banda99_rb_max']:.2f}]  "
              f"PAPR = {v['papr_db']:.2f} dB  Rb máx. p/ 1 MHz = {v['rb_max_para_1mhz_bps'] / 1e3:.1f} kbit/s")
