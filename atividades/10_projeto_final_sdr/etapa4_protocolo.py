"""Etapa 4: pacotes com número de sequência e CRC-16 pelo receptor completo.

a) PER x Eb/N0 das três modulações (pulso retangular, Rb = 12 kbit/s, 8 amostras por bit).
b) Goodput e eficiência do quadro.
c) Captura sintética a 2,4 MS/s no formato do RTL-SDR, decodificada pela cadeia real.
d) Comparação numérica entre o CRC-8 da referência e o CRC-16 do projeto.
Gera figuras/per_pacotes.png e resultados/etapa4.json.
"""
import time

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import resample_poly

from figuras_util import CORES, TINTA, gravar_json, salvar
from sdrlink import canal, metricas, quadro
from sdrlink.modem import Config, modular
from sdrlink.receptor import cu8_para_complexo, preparar, receber

SEMENTE = 20264
RB, SPS, SPS_ALTO = 12e3, 8, 32
N_PAYLOAD = 128
N_PROTEGIDOS = quadro.BITS_COMPRIMENTO + quadro.BITS_SEQUENCIA + 8 * N_PAYLOAD + quadro.BITS_CRC   # 1064
OFFSET_HZ = 300.0
CFGS = {"ook": Config("ook"), "fsk": Config("fsk"), "dbpsk": Config("dbpsk")}
TEORIA = {"ook": metricas.ber_ook_nc, "fsk": metricas.ber_fsk_nc, "dbpsk": metricas.ber_dbpsk}
NOME = {"ook": "OOK", "fsk": "2-FSK", "dbpsk": "DBPSK"}
MARCA = {"ook": "o", "fsk": "s", "dbpsk": "^"}
PONTOS = {"ook": range(9, 17), "fsk": range(9, 17), "dbpsk": range(6, 14)}


# ---------------------------------------------------------------- PER
def sinal_de_pacotes(cfg, seqs, sps, rng, extra_max):
    """Quadros separados por 16 bits de silêncio mais um atraso aleatório de até extra_max amostras."""
    partes, energia, ligado, enviados = [np.zeros(20 * sps + int(rng.integers(0, extra_max)), complex)], 0.0, 0, {}
    for seq in seqs:
        enviados[seq] = quadro.payload_prbs(seq, N_PAYLOAD)
        x = modular(quadro.montar(seq, enviados[seq]), sps, cfg)
        energia += float(np.sum(np.abs(x) ** 2))
        ligado += len(x)
        partes += [x, np.zeros(quadro.BITS_GUARDA * sps + int(rng.integers(0, extra_max)), complex)]
    partes.append(np.zeros(20 * sps, complex))
    return np.concatenate(partes), energia / ligado, enviados


def ensaio(esq, ebn0_db, n_pacotes, rng, lote=100):
    """PER, BER e goodput de n_pacotes pelo canal (atraso fracionário, fase, offset e AWGN)."""
    cfg, enviados, recebidos, duracao = CFGS[esq], {}, [], 0.0
    cont = {"candidatos": 0, "crc_invalido": 0}
    for inicio in range(0, n_pacotes, lote):
        x, potencia, env = sinal_de_pacotes(cfg, range(inicio, min(inicio + lote, n_pacotes)), SPS_ALTO, rng, SPS_ALTO)
        # A subamostragem com fase aleatória deixa as bordas dos bits fora da grade de 1/8 de bit.
        x = x[int(rng.integers(0, SPS_ALTO // SPS))::SPS_ALTO // SPS]
        x = canal.girar(x, OFFSET_HZ / (RB * SPS), rng.uniform(0, 2 * np.pi))
        x = x + canal.ruido(len(x), canal.variancia_ruido(potencia, SPS, ebn0_db), rng)
        pacotes, c = receber(x, SPS, cfg, RB)
        enviados.update(env)
        recebidos += pacotes
        duracao += len(x) / (RB * SPS)
        for k in cont:
            cont[k] += c[k]
    r = metricas.resumo_ensaio(enviados, recebidos, duracao)
    offsets = np.array([p.offset_hz for p in recebidos]) if recebidos else np.array([np.nan])
    r.update({"ebn0_db": ebn0_db, "candidatos": cont["candidatos"], "crc_invalido": cont["crc_invalido"],
              "offset_estimado_media_hz": float(np.mean(offsets)), "offset_estimado_desvio_hz": float(np.std(offsets)),
              "per_prevista_teoria": float(1 - (1 - TEORIA[esq](10 ** (ebn0_db / 10))) ** N_PROTEGIDOS)})
    return r


def ebn0_para_per(pontos, alvo=0.01):
    """Interpola log10(PER) entre os dois pontos que cercam o alvo."""
    n = pontos[0]["transmitidos"]
    for a, b in zip(pontos, pontos[1:]):
        if a["per"] > alvo >= b["per"]:
            la, lb = np.log10(a["per"]), np.log10(max(b["per"], 0.5 / n))
            return float(a["ebn0_db"] + (np.log10(alvo) - la) / (lb - la) * (b["ebn0_db"] - a["ebn0_db"]))
    return None


def curvas_per(rng, n_pacotes=1000):
    tabela = {}
    for esq in CFGS:
        tabela[esq] = [ensaio(esq, d, n_pacotes, rng) for d in PONTOS[esq]]
        print("PER", esq, [(p["ebn0_db"], round(p["per"], 4)) for p in tabela[esq]])

    def desenhar(t):
        fig, ax = plt.subplots(figsize=(9, 5.4), constrained_layout=True)
        d = np.linspace(5, 17, 300)
        piso = 0.5 / n_pacotes
        for esq in ("dbpsk", "fsk", "ook"):                  # FSK maior e por baixo: OOK e FSK quase coincidem
            ax.semilogy(d, 1 - (1 - TEORIA[esq](10 ** (d / 10))) ** N_PROTEGIDOS, color=CORES[esq],
                        label=NOME[esq] + t(": previsão pela BER teórica", ": prediction from theoretical BER"))
            ax.semilogy([p["ebn0_db"] for p in tabela[esq]], [max(p["per"], piso) for p in tabela[esq]], MARCA[esq],
                        color=CORES[esq], mec="white", mew=0.8, ms=11 if esq == "fsk" else 7.5,
                        label=NOME[esq] + t(": receptor completo", ": full receiver"))
        ax.axhline(0.01, color=TINTA, ls="--", lw=1.2)
        ax.text(5.15, 0.0115, t("limite das provas: PER = 1%", "competition limit: PER = 1%"), fontsize=8.5, color=TINTA, va="bottom")
        ax.text(5.15, piso * 1.12, t(f"nenhum pacote perdido em {n_pacotes}", f"no packet lost out of {n_pacotes}"),
                fontsize=8, color=TINTA, va="bottom")
        ax.axhline(piso, color="#8a9a94", ls=":", lw=1)
        ax.set_ylim(piso * 0.6, 1.5)
        ax.set_xlim(5, 17)
        ax.set_xlabel(t("Eb/N0 médio (dB)", "Average Eb/N0 (dB)"))
        ax.set_ylabel(t("taxa de erro de pacote (PER)", "packet error rate (PER)"))
        ax.set_title(t(f"PER com payload de 128 bytes, offset de 300 Hz e {n_pacotes} pacotes por ponto",
                       f"PER with 128-byte payload, 300 Hz offset and {n_pacotes} packets per point"))
        ax.grid(True, which="both", alpha=0.2)
        ax.legend(loc="lower left", ncol=1, bbox_to_anchor=(0.0, 0.12))
        return fig

    salvar(desenhar, "per_pacotes.png")
    return tabela


# ---------------------------------------------------------------- goodput
def goodput():
    nq, nref = quadro.bits_do_quadro(N_PAYLOAD), quadro.bits_do_quadro_referencia(N_PAYLOAD)
    util = 8 * N_PAYLOAD
    return {
        "bits_uteis": util, "bits_protegidos_pelo_crc": N_PROTEGIDOS,
        "quadro_do_projeto": {"bits_com_guarda": nq, "bits_dbpsk_com_simbolo_de_referencia": nq + 1,
                              "eficiencia": util / nq, "rb_minima_para_10kbps_per_0": 10e3 * nq / util,
                              "rb_minima_para_10kbps_per_1pct": 10e3 * nq / util / 0.99},
        "quadro_de_referencia": {"bits_com_guarda": nref, "eficiencia": util / nref,
                                 "goodput_maximo_a_10kbps": 10e3 * util / nref,
                                 "rb_minima_para_10kbps_per_0": 10e3 * nref / util},
        "goodput_maximo_por_taxa_bps": {str(int(rb)): rb * util / nq for rb in (10e3, 12e3, 20e3, 50e3, 100e3, 200e3)},
    }


# ---------------------------------------------------------------- captura sintética
def captura_sintetica(rng, n_pacotes=60):
    """TX a 2 MS/s em +200 kHz, RX a 2,4 MS/s em 8 bits, erro de portadora de +1,5 kHz."""
    fs_tx, fs_rx, rb, f_desloc, erro_hz, ebn0 = 2e6, 2.4e6, 20e3, 200e3, 1500.0, 15.0
    sps_tx, sps_rx = int(fs_tx / rb), fs_rx / rb
    saida = {"parametros": {"fs_tx_hz": fs_tx, "fs_rx_hz": fs_rx, "rb_bps": rb, "deslocamento_hz": f_desloc,
                            "erro_de_portadora_hz": erro_hz, "ebn0_db": ebn0, "pacotes": n_pacotes,
                            "quantizacao": "8 bits, I/Q intercalados"}}
    for esq, cfg in CFGS.items():
        x, potencia, enviados = sinal_de_pacotes(cfg, range(n_pacotes), sps_tx, rng, sps_tx)
        x = x * np.exp(2j * np.pi * f_desloc / fs_tx * np.arange(len(x)))
        x = resample_poly(x, 6, 5)
        x = canal.girar(x, erro_hz / fs_rx, rng.uniform(0, 2 * np.pi))
        x = 0.15 * (x + canal.ruido(len(x), canal.variancia_ruido(potencia, sps_rx, ebn0), rng))
        bruto = np.empty(2 * len(x), dtype=np.uint8)
        bruto[0::2] = np.clip(np.round(x.real * 127.5 + 127.5), 0, 255)
        bruto[1::2] = np.clip(np.round(x.imag * 127.5 + 127.5), 0, 255)
        saturadas = float(np.mean((bruto == 0) | (bruto == 255)))
        inicio = time.time()
        y = preparar(cu8_para_complexo(bruto), fs_rx, rb, SPS, f_desloc=f_desloc)
        pacotes, cont = receber(y, SPS, cfg, rb)
        tempo = time.time() - inicio
        duracao = len(x) / fs_rx
        r = metricas.resumo_ensaio(enviados, pacotes, duracao)
        offsets = np.array([p.offset_hz for p in pacotes])
        r.update({"candidatos": cont["candidatos"], "crc_invalido": cont["crc_invalido"],
                  "offset_estimado_media_hz": float(offsets.mean()), "offset_estimado_desvio_hz": float(offsets.std()),
                  "amostras_saturadas": saturadas, "tempo_de_processamento_s": tempo,
                  "tempo_estimado_para_60s_de_captura_s": tempo * 60 / duracao})
        saida[esq] = r
        print(f"captura sintética {esq}: PER={r['per']:.3f} offset={r['offset_estimado_media_hz']:.0f}±"
              f"{r['offset_estimado_desvio_hz']:.0f} Hz, {tempo:.2f} s para {duracao:.2f} s de sinal")
    return saida


# ---------------------------------------------------------------- CRC
def _crc_vetorizado(dados, bits):
    """CRC-8 (0x07, inicial 0) ou CRC-16/CCITT-FALSE de cada linha de `dados` (uint8)."""
    if bits == 8:
        tabela = np.array([quadro.crc8(bytes([i])) for i in range(256)], dtype=np.uint16)
        crc = np.zeros(len(dados), dtype=np.uint16)
        for j in range(dados.shape[1]):
            crc = tabela[crc ^ dados[:, j]]
        return crc
    tabela = np.array(quadro._CRC16, dtype=np.uint16)
    crc = np.full(len(dados), 0xFFFF, dtype=np.uint16)
    for j in range(dados.shape[1]):
        crc = ((crc << 8) & 0xFFFF) ^ tabela[(crc >> 8) ^ dados[:, j]]
    return crc


def _sindromes(n_bytes, bits, calcula):
    """Síndrome de cada erro de um bit na palavra-código (dados + CRC). O código é linear."""
    s = []
    for p in range(8 * n_bytes):
        e = bytearray(n_bytes)
        e[p // 8] = 0x80 >> (p % 8)
        s.append(calcula(bytes(e)))
    return np.array(s + [1 << (bits - 1 - k) for k in range(bits)])


def comparar_crc(rng):
    # Erros de dois bits passam quando as duas síndromes de um bit são iguais.
    s8 = _sindromes(N_PAYLOAD, 8, lambda e: quadro.crc8(e))
    s16 = _sindromes(3 + N_PAYLOAD, 16, lambda e: quadro.crc16(e, inicial=0))
    res = {}
    for nome, s in (("crc8_referencia", s8), ("crc16_projeto", s16)):
        n = len(s)
        _, contagem = np.unique(s, return_counts=True)
        iguais = np.flatnonzero(s[:, None] == s[None, :])
        i, j = np.unravel_index(iguais, (n, n))
        dist = (j - i)[j > i]
        res[nome] = {"bits_da_palavra_codigo": n, "pares_de_bits": n * (n - 1) // 2,
                     "erros_de_1_bit_nao_detectados": int(np.sum(s == 0)),
                     "erros_de_2_bits_nao_detectados": int(np.sum(contagem * (contagem - 1) // 2)),
                     "menor_separacao_nao_detectada_bits": int(dist.min()) if len(dist) else None}
    # Demonstração direta: dois bits do payload separados por 127 posições.
    payload = bytearray(quadro.payload_prbs(0, N_PAYLOAD))
    original = quadro.crc8(bytes(payload))
    for p in (100, 227):
        payload[p // 8] ^= 0x80 >> (p % 8)
    res["demonstracao"] = {"bits_invertidos": [100, 227], "crc8_original": original, "crc8_alterado": quadro.crc8(bytes(payload)),
                           "crc8_detectou": original != quadro.crc8(bytes(payload)),
                           "crc16_detectou": quadro.crc16(bytes(payload)) != quadro.crc16(quadro.payload_prbs(0, N_PAYLOAD))}
    # Aceitação falsa de quadros aleatórios (ruído decodificado como quadro).
    assert int(_crc_vetorizado(np.frombuffer(b"123456789", np.uint8)[None, :], 8)[0]) == quadro.crc8(b"123456789")
    assert int(_crc_vetorizado(np.frombuffer(b"123456789", np.uint8)[None, :], 16)[0]) == quadro.crc16(b"123456789")
    n_total, aceitos8, aceitos16 = 4_000_000, 0, 0
    for _ in range(n_total // 250_000):
        d = rng.integers(0, 256, (250_000, 3 + N_PAYLOAD + 2), dtype=np.uint8)
        aceitos8 += int(np.sum(_crc_vetorizado(d[:, :N_PAYLOAD], 8) == d[:, N_PAYLOAD]))
        recebido = d[:, -2].astype(np.uint16) << 8 | d[:, -1]
        aceitos16 += int(np.sum(_crc_vetorizado(d[:, :-2], 16) == recebido))
    res["aceitacao_falsa_de_quadros_aleatorios"] = {
        "quadros_testados": n_total,
        "crc8": {"aceitos": aceitos8, "taxa": aceitos8 / n_total, "esperado": 2.0 ** -8},
        "crc16": {"aceitos": aceitos16, "taxa": aceitos16 / n_total, "esperado": 2.0 ** -16}}
    return res


if __name__ == "__main__":
    inicio = time.time()
    rng = np.random.default_rng(SEMENTE)
    crc = comparar_crc(rng)
    print("CRC:", {k: v for k, v in crc.items() if k != "demonstracao"})
    sintetica = captura_sintetica(rng)
    per = curvas_per(rng)
    minimo = {esq: ebn0_para_per(per[esq]) for esq in per}
    gravar_json("etapa4.json", {
        "parametros": {"semente": SEMENTE, "rb_bps": RB, "amostras_por_bit": SPS, "payload_bytes": N_PAYLOAD,
                       "offset_hz": OFFSET_HZ, "bits_protegidos_pelo_crc": N_PROTEGIDOS,
                       "canal": "atraso fracionario aleatorio por quadro, fase aleatoria, offset fixo e AWGN",
                       "guarda": "16 bits de silencio mais ate 1 bit de atraso aleatorio"},
        "goodput": goodput(),
        "per": per,
        "ebn0_minimo_para_per_1pct_db": minimo,
        "ebn0_teorico_para_per_1pct_db": {esq: float(np.interp(
            0.01, *(lambda d: ((1 - (1 - TEORIA[esq](10 ** (d / 10))) ** N_PROTEGIDOS)[::-1], d[::-1]))(np.linspace(5, 18, 2601))))
            for esq in TEORIA},
        "captura_sintetica": sintetica,
        "crc": crc,
        "tempo_de_execucao_s": time.time() - inicio,
    })
    print("Eb/N0 mínimo para PER 1%:", minimo, f"({time.time() - inicio:.0f} s)")
