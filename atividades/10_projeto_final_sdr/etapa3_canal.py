"""Etapa 3: BER em AWGN e sensibilidade a fase, offset de frequência e temporização.

Simulação em banda base com 8 amostras por bit (20 no teste de temporização),
usando os mesmos detectores do receptor (sdrlink.modem). O Eb/N0 é sempre a
energia média por bit. Gera figuras e resultados/etapa3.json.
"""
import json
import time

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import brentq

from figuras_util import CORES, RESULTADOS, TINTA, gravar_json, salvar, virgula
from sdrlink import canal, metricas, quadro
from sdrlink.modem import Config, filtro_casado, fluxo, modular

SEMENTE = 20263
N_QUADRO = quadro.bits_do_quadro(128, guarda=False)        # 1093 bits no ar por quadro
N_PROTEGIDOS = N_QUADRO - len(quadro.CABECALHO_SINC)       # 1064 bits cobertos pelo CRC
CAB = quadro.CABECALHO_SINC
T0 = (2.0 * CAB - 1.0) - (2.0 * CAB - 1.0).mean()
CFG = {"ook": Config("ook"), "fsk": Config("fsk"), "bpsk": Config("dbpsk"), "dbpsk": Config("dbpsk")}
TEORIA = {"ook": metricas.ber_ook_nc, "fsk": metricas.ber_fsk_nc, "bpsk": metricas.ber_bpsk, "dbpsk": metricas.ber_dbpsk}
NOME = {"ook": ("OOK não coerente", "Noncoherent OOK"), "fsk": ("2-FSK não coerente", "Noncoherent 2-FSK"),
        "bpsk": ("BPSK coerente", "Coherent BPSK"), "dbpsk": ("DBPSK", "DBPSK")}
COR = {"ook": CORES["ook"], "fsk": CORES["fsk"], "dbpsk": CORES["dbpsk"], "bpsk": CORES["extra"]}
MARCA = {"ook": "o", "fsk": "s", "dbpsk": "^", "bpsk": "D"}
EBN0_FIXO = {"bpsk": 9.0, "dbpsk": 9.0, "ook": 13.0, "fsk": 13.0}


def ber(esq, ebn0_db, rng, sps=8, fase=0.0, df_t=0.0, m=0, corrige=False, quadros=False,
        max_bits=4e6, max_erros=300, n_quadros=100):
    """Conta erros de bit em blocos de n_quadros quadros.

    fase: erro de fase estático (rad). df_t: offset de frequência × duração do bit.
    m: erro de temporização em amostras. quadros=True coloca os 29 bits conhecidos no
    início de cada quadro e conta erros só nos demais; nesse modo a BPSK coerente usa
    a fase do início do quadro sem rastreio e `corrige` estima o giro da DBPSK no cabeçalho.
    """
    cfg, erros, total = CFG[esq], 0, 0
    while total < max_bits and erros < max_erros:
        bits = rng.integers(0, 2, (n_quadros, N_QUADRO)).astype(np.uint8)
        if quadros:
            bits[:, :len(CAB)] = CAB
        plano = bits.ravel()
        x = np.repeat(1.0 - 2.0 * plano, sps).astype(complex) if esq == "bpsk" else modular(plano, sps, cfg)
        potencia = np.mean(np.abs(x) ** 2)
        if esq == "bpsk" and quadros:
            # Fase conhecida no primeiro símbolo de cada quadro e nenhum rastreio depois.
            n = np.arange(len(x)) % (N_QUADRO * sps)
            x = x * np.exp(1j * (2 * np.pi * df_t / sps * n - np.pi * df_t * (sps - 1) / sps + fase))
        else:
            x = canal.girar(x, df_t / sps, fase)
        x = x + canal.ruido(len(x), canal.variancia_ruido(potencia, sps, ebn0_db), rng)
        if esq == "ook":
            dec = fluxo(x, sps, cfg)[m::sps] > 0.5           # limiar em metade da amplitude do bit 1
        elif esq == "fsk":
            dec = fluxo(x, sps, cfg)[m::sps] > 0
        elif esq == "bpsk":
            dec = filtro_casado(x, sps, cfg)[m::sps].real < 0
        else:
            z = fluxo(x, sps, cfg)[m::sps]
            if corrige:
                zq = z[:n_quadros * N_QUADRO].reshape(n_quadros, N_QUADRO)
                giro = np.angle(zq[:, :len(CAB)] @ T0)
                z = (zq * np.exp(-1j * giro)[:, None]).ravel()
            dec = z.real > 0
        n = min(len(dec), len(plano))
        errado = dec[:n] != (plano[:n] == 1)
        if quadros:
            valido = (np.arange(n) % N_QUADRO) >= len(CAB)
            errado, n = errado[valido], int(valido.sum())
        erros += int(errado.sum())
        total += n
    return erros / total, erros, total


def ebn0_necessario(esq, alvo):
    """Eb/N0 (dB) em que a BER teórica atinge o alvo."""
    return brentq(lambda d: np.log10(TEORIA[esq](10 ** (d / 10))) - np.log10(alvo), 0, 25)


# ---------------------------------------------------------------- AWGN
def curvas_awgn(rng):
    faixas = {"bpsk": range(0, 11), "dbpsk": range(0, 11), "fsk": range(0, 14), "ook": range(0, 14)}
    tabela = {}
    for esq, pontos in faixas.items():
        linhas = []
        for d in pontos:
            sim, erros, total = ber(esq, d, rng)
            linhas.append({"ebn0_db": d, "ber_simulada": sim, "ber_teorica": float(TEORIA[esq](10 ** (d / 10))),
                           "erros": erros, "bits": total})
        tabela[esq] = linhas
        print(f"AWGN {esq}: último ponto {linhas[-1]}")

    def desenhar(t):
        fig, ax = plt.subplots(figsize=(9, 5.4), constrained_layout=True)
        d = np.linspace(0, 14, 200)
        for esq in ("bpsk", "dbpsk", "fsk", "ook"):
            pt, en = NOME[esq]
            ax.semilogy(d, TEORIA[esq](10 ** (d / 10)), color=COR[esq], label=t(pt, en) + t(": teoria", ": theory"))
            ax.semilogy([p["ebn0_db"] for p in tabela[esq]], [p["ber_simulada"] for p in tabela[esq]], MARCA[esq],
                        color=COR[esq], mec="white", mew=0.8, ms=7.5, label=t(pt, en) + t(": simulação", ": simulation"))
        ax.set_ylim(5e-6, 1)
        ax.set_xlim(-0.3, 14.3)
        ax.set_xlabel(t("Eb/N0 médio (dB)", "Average Eb/N0 (dB)"))
        ax.set_ylabel(t("taxa de erro de bit", "bit error rate"))
        ax.set_title(t("BER em canal AWGN: simulação e teoria", "BER over the AWGN channel: simulation and theory"))
        ax.grid(True, which="both", alpha=0.2)
        ax.legend(ncol=2, loc="lower left")
        return fig

    salvar(desenhar, "ber_awgn.png")
    return tabela


# ---------------------------------------------------------------- sensibilidade
def sensibilidade(rng):
    fases = [0, 10, 20, 30, 40, 50, 60]
    offsets = [0, 0.003, 0.006, 0.01, 0.03, 0.05, 0.1, 0.15, 0.2, 0.25]
    atrasos = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
    res = {"fase": {}, "offset": {}, "temporizacao": {}}

    for esq in ("bpsk", "dbpsk", "fsk", "ook"):
        res["fase"][esq] = [{"fase_graus": f, **dict(zip(("ber", "erros", "bits"),
                             ber(esq, EBN0_FIXO[esq], rng, fase=np.radians(f), max_bits=4e6 if esq == "bpsk" else 2e6)))}
                            for f in fases]
        print("fase", esq, [f"{p['ber']:.2e}" for p in res["fase"][esq]])

    series = [("bpsk", "bpsk", False), ("dbpsk_sem_correcao", "dbpsk", False), ("dbpsk_com_correcao", "dbpsk", True),
              ("fsk", "fsk", False), ("ook", "ook", False)]
    for chave, esq, corrige in series:
        res["offset"][chave] = [{"df_t": o, **dict(zip(("ber", "erros", "bits"),
                                 ber(esq, EBN0_FIXO[esq], rng, df_t=o, corrige=corrige, quadros=True)))}
                                for o in offsets]
        print("offset", chave, [f"{p['ber']:.2e}" for p in res["offset"][chave]])

    for esq in ("bpsk", "dbpsk", "fsk", "ook"):
        res["temporizacao"][esq] = [{"tau": a, **dict(zip(("ber", "erros", "bits"),
                                     ber(esq, EBN0_FIXO[esq], rng, sps=20, m=int(round(a * 20)), max_bits=2e6, n_quadros=50)))}
                                    for a in atrasos]
        print("temporização", esq, [f"{p['ber']:.2e}" for p in res["temporizacao"][esq]])

    g_bpsk = 10 ** (EBN0_FIXO["bpsk"] / 10)
    piso = 3e-6                                             # pontos sem erro aparecem neste piso do gráfico

    def desenhar(t):
        fig, eixos = plt.subplots(1, 3, figsize=(13.5, 6.3), sharey=True, constrained_layout=True)
        dec = (lambda v: virgula(v, 3).rstrip("0").rstrip(",")) if t("a", "b") == "a" else (lambda v: f"{v:g}")
        sufixo = {e: f" ({EBN0_FIXO[e]:.0f} dB)" for e in EBN0_FIXO}

        ax = eixos[0]
        f = np.linspace(0, 60, 100)
        ax.semilogy(f, metricas.q(np.sqrt(2 * g_bpsk) * np.cos(np.radians(f))), color=COR["bpsk"],
                    label=t("BPSK coerente: teoria", "Coherent BPSK: theory"))
        for esq in ("bpsk", "dbpsk", "fsk", "ook"):
            pt, en = NOME[esq]
            ax.semilogy(fases, [max(p["ber"], piso) for p in res["fase"][esq]], MARCA[esq], color=COR[esq],
                        ls="none" if esq == "bpsk" else ":", lw=1.3, mec="white", mew=0.8, ms=7.5, label=t(pt, en) + sufixo[esq])
        ax.set_xlabel(t("erro de fase estático (graus)", "static phase error (degrees)"))
        ax.set_ylabel(t("taxa de erro de bit", "bit error rate"))
        ax.set_title(t("Erro de fase", "Phase error"))

        ax = eixos[1]
        zero = 0.001                                         # posição do ponto de offset nulo no eixo logarítmico
        estilos = {"bpsk": ("bpsk", "-", t("BPSK coerente, sem rastreio", "Coherent BPSK, no tracking")),
                   "dbpsk_sem_correcao": ("dbpsk", "--", t("DBPSK sem correção", "DBPSK, uncorrected")),
                   "dbpsk_com_correcao": ("dbpsk", "-", t("DBPSK com correção no cabeçalho", "DBPSK, header-corrected")),
                   "fsk": ("fsk", "-", t("2-FSK não coerente", "Noncoherent 2-FSK")),
                   "ook": ("ook", "-", t("OOK não coerente", "Noncoherent OOK"))}
        for chave, (esq, ls, rot) in estilos.items():
            xs = [max(p["df_t"], zero) for p in res["offset"][chave]]
            ax.loglog(xs, [max(p["ber"], piso) for p in res["offset"][chave]], marker=MARCA[esq], ls=ls, lw=1.6,
                      color=COR[esq], mec=COR[esq] if ls == "--" else "white", mew=1.4 if ls == "--" else 0.8, ms=7.5,
                      mfc="white" if ls == "--" else COR[esq], label=rot + sufixo[esq])
        for x0, rot in ((0.003, "300 Hz\n100 kbit/s"), (0.03, "300 Hz\n10 kbit/s")):
            ax.axvline(x0, color=TINTA, ls=":", lw=1.1)
            ax.text(x0 * 1.08, 0.42, rot, fontsize=7.5, color=TINTA, va="top")
        marcas = [zero, 0.003, 0.01, 0.03, 0.1, 0.25]
        ax.set_xticks(marcas)
        ax.set_xticklabels(["0"] + [dec(v) for v in marcas[1:]])
        ax.minorticks_off()
        ax.set_xlabel(t("offset de frequência × duração do bit (Δf·T)", "frequency offset × bit duration (Δf·T)"))
        ax.set_title(t("Offset de frequência (quadro de 1093 bits)", "Frequency offset (1093-bit frame)"))

        ax = eixos[2]
        a = np.linspace(0, 0.4, 100)
        ax.semilogy(a, 0.5 * metricas.q(np.sqrt(2 * g_bpsk)) + 0.5 * metricas.q(np.sqrt(2 * g_bpsk) * (1 - 2 * a)),
                    color=COR["bpsk"], label=t("BPSK coerente: teoria", "Coherent BPSK: theory"))
        for esq in ("bpsk", "dbpsk", "fsk", "ook"):
            pt, en = NOME[esq]
            ax.semilogy(atrasos, [max(p["ber"], piso) for p in res["temporizacao"][esq]], MARCA[esq], color=COR[esq],
                        ls="none" if esq == "bpsk" else ":", lw=1.3, mec="white", mew=0.8, ms=7.5, label=t(pt, en) + sufixo[esq])
        ax.set_xlabel(t("erro de temporização (fração do bit, τ/T)", "timing error (fraction of a bit, τ/T)"))
        ax.set_title(t("Erro de temporização", "Timing error"))
        for ax in eixos:
            ax.set_ylim(piso * 0.7, 1)
            ax.grid(True, which="both", alpha=0.2)
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8, ncol=1)
        fig.suptitle(t("Sensibilidade da BER em Eb/N0 fixo (entre parênteses)",
                       "BER sensitivity at fixed Eb/N0 (in parentheses)"), color="#285b42")
        return fig

    salvar(desenhar, "sensibilidade.png")
    return res, offsets


def sintese_offset(res):
    """Efeito de 300 Hz de offset residual em três taxas de bits."""
    saida = []
    for rb in (10e3, 50e3, 100e3):
        d = 300.0 / rb
        sinc_db = float(20 * np.log10(np.sinc(d)))
        linha = {"rb_bps": rb, "df_t": d, "giro_por_bit_graus": 360 * d, "bits_ate_90_graus_sem_rastreio": 0.25 / d,
                 "perda_analitica_db": {
                     "ook_e_dbpsk_corrigida_filtro_casado": sinc_db,
                     "fsk_tom_desejado": sinc_db,
                     "dbpsk_sem_correcao_aprox": float(sinc_db + 20 * np.log10(np.cos(2 * np.pi * d)))},
                 "razao_ber_simulada_em_relacao_a_offset_zero": {}}
        for chave, pontos in res["offset"].items():
            base = pontos[0]["ber"]
            alvo = next(p for p in pontos if abs(p["df_t"] - d) < 1e-9)
            linha["razao_ber_simulada_em_relacao_a_offset_zero"][chave] = {
                "ber": alvo["ber"], "erros": alvo["erros"], "razao": alvo["ber"] / base if base > 0 else None}
        saida.append(linha)
    return saida


if __name__ == "__main__":
    inicio = time.time()
    rng = np.random.default_rng(SEMENTE)
    awgn = curvas_awgn(rng)
    sens, offsets = sensibilidade(rng)

    per_alvo = 0.01
    ber_per1 = 1 - (1 - per_alvo) ** (1 / N_PROTEGIDOS)
    alvos = {"ber_1e-3": 1e-3, "ber_para_per_1pct": ber_per1}
    necessario = {esq: {k: ebn0_necessario(esq, v) for k, v in alvos.items()} for esq in TEORIA}
    papr_rrc = None
    arq = RESULTADOS / "etapa2.json"
    if arq.exists():
        papr_rrc = next(v["papr_db"] for v in json.loads(arq.read_text())["variantes"] if v["pulso"] == "rrc")
    gravar_json("etapa3.json", {
        "parametros": {"semente": SEMENTE, "amostras_por_bit": 8, "amostras_por_bit_temporizacao": 20,
                       "bits_no_ar_por_quadro": N_QUADRO, "bits_protegidos_pelo_crc": N_PROTEGIDOS,
                       "max_bits_por_ponto": 4e6, "max_erros_por_ponto": 300, "ebn0_fixo_db": EBN0_FIXO,
                       "limiar_ook": "metade da amplitude do bit 1", "ebn0": "energia media por bit"},
        "awgn": awgn,
        "alvos_de_ber": alvos,
        "ebn0_necessario_teoria_db": necessario,
        "dbpsk_menos_bpsk_coerente_db": {k: necessario["dbpsk"][k] - necessario["bpsk"][k] for k in alvos},
        "mesma_potencia_de_pico": {
            "observacao": "o DAC limita o pico; a perda abaixo e a reducao de Eb medio para o mesmo pico",
            "perda_db": {"ook": 10 * np.log10(2), "fsk": 0.0, "dbpsk_retangular": 0.0, "dbpsk_rrc": papr_rrc},
            "ebn0_de_pico_para_per_1pct_db": {
                "ook": necessario["ook"]["ber_para_per_1pct"] + 10 * np.log10(2),
                "fsk": necessario["fsk"]["ber_para_per_1pct"],
                "dbpsk_retangular": necessario["dbpsk"]["ber_para_per_1pct"],
                "dbpsk_rrc": None if papr_rrc is None else necessario["dbpsk"]["ber_para_per_1pct"] + papr_rrc,
                "bpsk_coerente_retangular": necessario["bpsk"]["ber_para_per_1pct"]}},
        "sensibilidade": sens,
        "offset_300hz": sintese_offset(sens),
        "tempo_de_execucao_s": time.time() - inicio,
    })
    for esq in TEORIA:
        print(esq, {k: round(v, 2) for k, v in necessario[esq].items()})
    print(f"tempo: {time.time() - inicio:.0f} s")
