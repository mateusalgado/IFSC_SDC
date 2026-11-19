"""Caracteriza a OOK de referência enquanto o Pluto transmite pluto_tx_ook_v2.py.

    .venv/bin/python ensaio_referencia.py --ppm 86

1. Ensaio de 60 s no ganho nominal: PER, goodput, offset residual e banda de 99%.
2. Varredura do ganho do RTL-SDR: relação sinal-ruído medida e PER em cada ganho.
3. Tolerância a offset de frequência: a captura de 60 s é decodificada com erros
   de sintonia aplicados digitalmente, o que equivale a um ppm mal calibrado.
4. Sensibilidade ao número de amostras por bit do processamento.

Grava resultados/bancada_ook_referencia.json. As capturas da varredura de ganho
são apagadas depois de decodificadas; a de 60 s fica em capturas/.
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np

from rx_decodificar import banda_medida, carregar, perdas_por_intervalo
from rx_gravar import abrir, gravar
from sdrlink import metricas, quadro, radio
from sdrlink.modem import Config
from sdrlink.receptor import cu8_para_complexo, receber

RB = 10e3
CFG = Config("ook", "rampa")


def decodificar(arquivo, fs, desloc, sps=8):
    t0 = time.time()
    x, n, saturado = carregar(arquivo, fs, RB, sps, desloc)
    pacotes, cont = receber(x, sps, CFG, RB, formato="referencia")
    r = {"quadros_validos": len(pacotes), "crc_invalido": cont["crc_invalido"], "candidatos": cont["candidatos"],
         "fracao_saturada": saturado, "duracao_s": n / fs, "tempo_processamento_s": round(time.time() - t0, 2)}
    if len(pacotes) >= 2:
        tam = len(pacotes[0].payload)
        periodo = quadro.bits_do_quadro_referencia(tam) / RB
        tempos = np.array([p.tempo_s for p in pacotes])
        perdidos, total = perdas_por_intervalo(tempos, periodo)
        off = np.array([p.offset_hz for p in pacotes])
        r.update({"payload_bytes": tam, "quadros_no_intervalo": total, "quadros_perdidos": perdidos,
                  "per": perdidos / total, "esperados_na_captura": int(n / fs / periodo),
                  "goodput_bps": round(8 * tam * len(pacotes) / (n / fs), 1),
                  "goodput_maximo_bps": round(8 * tam / periodo, 1),
                  "offset_hz_media": round(float(off.mean()), 1), "offset_hz_desvio": round(float(off.std()), 1),
                  "rho_medio": round(float(np.mean([p.rho for p in pacotes])), 3),
                  "conteudos_distintos": len({p.payload for p in pacotes})})
        r["_tempos"], r["_offsets"] = tempos, off
    else:
        r["esperados_na_captura"] = int(n / fs / (229 / RB))
        r["per"] = 1.0
    return r


def snr_da_portadora(arquivo, fs, desloc):
    """Sinal na faixa de ±10 kHz em torno da portadora sobre o ruído da mesma largura, em dB."""
    x = cu8_para_complexo(np.fromfile(arquivo, dtype=np.uint8, count=2 * (1 << 23)))
    x -= x.mean()
    f, p = metricas.psd(x, fs, 1 << 14)
    piso = np.median(p)
    faixa = np.abs(f - desloc) <= 10e3
    sinal = np.sum(np.maximum(p[faixa] - piso, 0))
    return float(10 * np.log10(max(sinal, 1e-30) / (piso * np.count_nonzero(faixa)))), float(np.sqrt(np.mean(np.abs(x) ** 2)))


def limpo(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ppm", type=int, required=True)
    ap.add_argument("--ganho", type=float, default=radio.GANHO_RX)
    ap.add_argument("--segundos", type=float, default=60.0)
    ap.add_argument("--nota", default="")
    args = ap.parse_args()
    fs, fc, desloc = radio.FS_RX, radio.FC, radio.DESLOC
    pasta = radio.RAIZ / "capturas"
    saida = {"inicio": datetime.now().astimezone().isoformat(timespec="seconds"), "nota": args.nota,
             "transmissor": "pluto_tx_ook_v2.py (referência), 915 MHz + 200 kHz, 10 kbit/s",
             "fc_hz": fc, "fs_hz": fs, "ppm": args.ppm}

    # 1. ensaio longo
    sdr = abrir(fc, fs, args.ganho, args.ppm)
    longa = pasta / "ook_ref_ensaio_60s.cu8"
    print(f"Ensaio de {args.segundos:g} s, ganho {sdr.gain:.1f} dB...")
    inicio = datetime.now().astimezone().isoformat(timespec="seconds")
    n = gravar(sdr, longa, int(args.segundos * fs))
    longa.with_suffix(".json").write_text(json.dumps({"fc_hz": fc, "fs_hz": fs, "ganho_db": sdr.gain,
                                                      "ppm": args.ppm, "inicio": inicio, "amostras": n}, indent=2))
    r = decodificar(longa, fs, desloc)
    snr, rms = snr_da_portadora(longa, fs, desloc)
    passo = max(1, len(r["_tempos"]) // 60)
    saida["ensaio_longo"] = {**limpo(r), "ganho_db": sdr.gain, "snr_20khz_db": round(snr, 1), "rms": round(rms, 4),
                             "banda": banda_medida(longa, fs, desloc, 120e3),
                             "offset_ao_longo_do_tempo": [
                                 {"t_s": round(float(np.mean(r["_tempos"][i:i + passo])), 1),
                                  "offset_hz": round(float(np.mean(r["_offsets"][i:i + passo])), 1)}
                                 for i in range(0, len(r["_tempos"]), passo)]}
    print(f"  {r['quadros_validos']} válidos, {r['quadros_perdidos']} perdidos, PER {r['per']:.4f}, "
          f"goodput {r['goodput_bps']:.0f} bit/s, offset {r['offset_hz_media']:+.0f} ± {r['offset_hz_desvio']:.0f} Hz, "
          f"S/N {snr:.1f} dB")

    # 2. varredura de ganho
    ganhos = [g for g in sdr.valid_gains_db if g in (0.0, 3.7, 7.7, 12.5, 15.7, 19.7, 22.9, 29.7, 36.4, 42.1, 49.6)]
    tmp = pasta / "_ganho_tmp.cu8"
    saida["varredura_de_ganho"] = []
    print("Varredura de ganho (8 s cada):")
    for g in ganhos:
        sdr.gain = g
        sdr.read_bytes(2 * 262144)
        gravar(sdr, tmp, int(8 * fs))
        r = decodificar(tmp, fs, desloc)
        snr, rms = snr_da_portadora(tmp, fs, desloc)
        saida["varredura_de_ganho"].append({"ganho_db": g, "snr_20khz_db": round(snr, 1), "rms": round(rms, 4),
                                            **limpo(r)})
        print(f"  {g:5.1f} dB: S/N {snr:5.1f} dB, rms {rms:.4f}, saturação {100 * r['fracao_saturada']:.2f}%, "
              f"{r['quadros_validos']}/{r['esperados_na_captura']} quadros, PER {r['per']:.4f}")
    sdr.close()
    tmp.unlink(missing_ok=True)

    # 3. tolerância a offset (erro de sintonia aplicado na captura longa)
    saida["tolerancia_a_offset"] = []
    print("Erro de sintonia aplicado digitalmente à captura longa:")
    for erro in (0, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7000, 10000):
        r = decodificar(longa, fs, desloc + erro)
        saida["tolerancia_a_offset"].append({"erro_hz": erro, "erro_ppm": round(erro / 915.2, 2), **limpo(r)})
        print(f"  {erro:+6d} Hz ({erro / 915.2:4.1f} ppm): {r['quadros_validos']} válidos, PER {r['per']:.4f}")

    # 4. amostras por bit do processamento
    saida["amostras_por_bit"] = []
    for sps in (4, 8, 16):
        r = decodificar(longa, fs, desloc, sps)
        saida["amostras_por_bit"].append({"sps": sps, **limpo(r)})
        print(f"  sps = {sps:2d}: {r['quadros_validos']} válidos, PER {r['per']:.4f}, {r['tempo_processamento_s']} s")

    arquivo = radio.RAIZ / "resultados" / "bancada_ook_referencia.json"
    arquivo.write_text(json.dumps(saida, indent=2, ensure_ascii=False))
    print(arquivo)


if __name__ == "__main__":
    main()
