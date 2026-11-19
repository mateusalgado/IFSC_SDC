"""Grava amostras IQ do RTL-SDR em arquivo (formato cu8) com os parâmetros do ensaio.

Exemplo:
    .venv/bin/python rx_gravar.py --segundos 10 --ppm 34 --nome ook_10k

Gera capturas/<nome>.cu8 (I e Q intercalados, 8 bits sem sinal) e
capturas/<nome>.json com frequência, taxa, ganho, ppm e horário. O AGC fica
desligado: o ganho é manual e registrado.
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from sdrlink import radio

radio.preparar_bibliotecas()
from rtlsdr import RtlSdr  # noqa: E402


def abrir(fc: float, fs: float, ganho: float, ppm: int) -> RtlSdr:
    sdr = RtlSdr()
    sdr.sample_rate = fs
    if ppm != sdr.freq_correction:      # a biblioteca rejeita regravar o mesmo valor
        sdr.freq_correction = ppm
    sdr.center_freq = fc
    sdr.gain = ganho
    sdr.read_bytes(2 * 256 * 1024)       # descarta o transitório de sintonia
    return sdr


def gravar(sdr: RtlSdr, arquivo: Path, n_amostras: int) -> int:
    """Leitura assíncrona direto para o arquivo. Devolve o número de amostras gravadas."""
    falta = 2 * n_amostras
    with open(arquivo, "wb") as saida:
        def recebe(dados, _):
            nonlocal falta
            bloco = bytes(dados)[:falta]
            saida.write(bloco)
            falta -= len(bloco)
            if falta <= 0:
                sdr.cancel_read_async()
        sdr.read_bytes_async(recebe, 2 * 262144)
    return n_amostras - falta // 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freq", type=float, default=radio.FC, help="frequência central, Hz")
    ap.add_argument("--fs", type=float, default=radio.FS_RX, help="taxa de amostragem, Hz")
    ap.add_argument("--ganho", type=float, default=radio.GANHO_RX, help="ganho manual, dB")
    ap.add_argument("--ppm", type=int, default=0, help="correção de frequência calibrada")
    ap.add_argument("--segundos", type=float, default=5.0)
    ap.add_argument("--nome", default=datetime.now().strftime("captura_%Y%m%d_%H%M%S"))
    ap.add_argument("--pasta", type=Path, default=radio.RAIZ / "capturas")
    args = ap.parse_args()

    args.pasta.mkdir(parents=True, exist_ok=True)
    arquivo = args.pasta / f"{args.nome}.cu8"
    sdr = abrir(args.freq, args.fs, args.ganho, args.ppm)
    meta = {"arquivo": arquivo.name, "fc_hz": args.freq, "fs_hz": sdr.sample_rate,
            "ganho_pedido_db": args.ganho, "ganho_db": sdr.gain, "ppm": args.ppm,
            "inicio": datetime.now().astimezone().isoformat(timespec="milliseconds")}
    n = int(round(args.segundos * args.fs))
    print(f"Gravando {args.segundos:.1f} s em {args.freq / 1e6:.3f} MHz, {args.fs / 1e6:.3f} MS/s, "
          f"ganho {sdr.gain:.1f} dB, ppm {args.ppm}...")
    t0 = time.time()
    meta["amostras"] = gravar(sdr, arquivo, n)
    meta["duracao_real_s"] = round(time.time() - t0, 3)
    sdr.close()
    arquivo.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"{meta['amostras']} amostras em {arquivo} ({arquivo.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
