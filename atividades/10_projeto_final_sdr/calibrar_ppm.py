"""Calibra a correção de frequência (ppm) do RTL-SDR usando a portadora do Pluto.

O Pluto deve estar transmitindo em FC + DESLOC (tom de tx_test.py ou a OOK de
referência, cuja portadora é uma linha espectral). O script mede a posição da
linha, converte o erro em ppm, aplica a correção e mede o offset residual.

    .venv/bin/python calibrar_ppm.py            # parte de 0 ppm
    .venv/bin/python calibrar_ppm.py --ppm 56 --medidas 10   # só mede o residual

O resultado é acrescentado a resultados/calibracao.json.
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np

from sdrlink import radio

radio.preparar_bibliotecas()
from rtlsdr import RtlSdr  # noqa: E402

NFFT = 1 << 20


def medir_linha(sdr: RtlSdr, esperado_hz: float, busca_hz: float):
    """Frequência (em relação ao centro) e nível da maior linha perto de `esperado_hz`."""
    sdr.read_bytes(2 * 262144)
    x = np.asarray(sdr.read_samples(NFFT))
    x = (x - x.mean()) * np.hanning(NFFT)
    espectro = np.abs(np.fft.fft(x)) ** 2
    f = np.fft.fftfreq(NFFT, 1 / sdr.sample_rate)
    janela = np.abs(f - esperado_hz) <= busca_hz
    i = np.flatnonzero(janela)[np.argmax(espectro[janela])]
    a, b, c = np.log(espectro[i - 1]), np.log(espectro[i]), np.log(espectro[(i + 1) % NFFT])
    delta = 0.5 * (a - c) / (a - 2 * b + c)            # interpolação parabólica do pico
    piso = np.median(espectro[janela])
    return f[i] + delta * sdr.sample_rate / NFFT, 10 * np.log10(espectro[i] / piso)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freq", type=float, default=radio.FC)
    ap.add_argument("--desloc", type=float, default=radio.DESLOC, help="posição esperada da portadora, Hz")
    ap.add_argument("--fs", type=float, default=radio.FS_RX)
    ap.add_argument("--ganho", type=float, default=radio.GANHO_RX)
    ap.add_argument("--ppm", type=int, default=0, help="correção inicial")
    ap.add_argument("--busca", type=float, help="meia largura da primeira busca, Hz "
                    "(padrão: 120 kHz partindo de 0 ppm; 15 kHz quando --ppm é informado)")
    ap.add_argument("--medidas", type=int, default=5, help="medidas do residual após a correção")
    ap.add_argument("--fixo", action="store_true", help="não altera o ppm; só mede o residual")
    args = ap.parse_args()

    sdr = RtlSdr()
    sdr.sample_rate = args.fs
    sdr.gain = args.ganho
    ppm = args.ppm
    registro = {"horario": datetime.now().astimezone().isoformat(timespec="seconds"),
                "fc_hz": args.freq, "portadora_esperada_hz": args.freq + args.desloc,
                "fs_hz": args.fs, "ganho_db": sdr.gain, "ppm_inicial": ppm, "iteracoes": []}
    busca = args.busca or (120e3 if ppm == 0 else 15e3)
    for _ in range(4):
        if ppm != sdr.freq_correction:
            sdr.freq_correction = ppm
        sdr.center_freq = args.freq
        medido, nivel = medir_linha(sdr, args.desloc, busca)
        erro_hz = args.desloc - medido
        erro_ppm = erro_hz / (args.freq + args.desloc) * 1e6
        registro["iteracoes"].append({"ppm": ppm, "linha_hz": round(medido, 1), "erro_hz": round(erro_hz, 1),
                                      "erro_ppm": round(erro_ppm, 2), "nivel_db": round(nivel, 1)})
        print(f"ppm={ppm:3d}: linha em {medido / 1e3:+9.3f} kHz ({nivel:.0f} dB sobre o piso), "
              f"erro {erro_hz:+8.1f} Hz = {erro_ppm:+.2f} ppm")
        if args.fixo or round(erro_ppm) == 0:
            break
        ppm += int(round(erro_ppm))
        busca = 15e3                # depois do primeiro ajuste, só a vizinhança da portadora
    residuos = []
    for _ in range(args.medidas):
        medido, _ = medir_linha(sdr, args.desloc, 20e3)
        residuos.append(medido - args.desloc)
        time.sleep(0.5)
    sdr.close()
    registro.update({"ppm_final": ppm, "residuo_hz": [round(r, 1) for r in residuos],
                     "residuo_medio_hz": round(float(np.mean(residuos)), 1),
                     "residuo_desvio_hz": round(float(np.std(residuos)), 1)})
    print(f"Correção final: {ppm} ppm | offset residual {np.mean(residuos):+.1f} Hz "
          f"(desvio {np.std(residuos):.1f} Hz em {len(residuos)} medidas; 1 ppm = "
          f"{(args.freq + args.desloc) / 1e6:.0f} Hz)")
    arquivo = radio.RAIZ / "resultados" / "calibracao.json"
    historico = json.loads(arquivo.read_text()) if arquivo.exists() else []
    historico.append(registro)
    arquivo.write_text(json.dumps(historico, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
