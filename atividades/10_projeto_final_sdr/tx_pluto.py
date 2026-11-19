"""Transmite pacotes pelo ADALM-Pluto em OOK, 2-FSK ou DBPSK (buffer cíclico).

Precisa apenas de numpy e pyadi-iio, como o transmissor de referência.

    python tx_pluto.py --esquema ook                       # OOK 10 kbit/s, quadro do projeto
    python tx_pluto.py --esquema fsk --rb 20e3
    python tx_pluto.py --esquema dbpsk --pulso rrc --rb 50e3
    python tx_pluto.py --esquema fsk --seco teste.cu8      # sem rádio: grava o sinal em arquivo

Cada quadro leva número de sequência de 16 bits, payload de 128 bytes e CRC-16,
seguido de 16 bits de silêncio. Os payloads são pseudoaleatórios e reproduzíveis
(quadro.payload_prbs), para o receptor poder contar erros de bit. O buffer com
os N quadros é repetido pelo Pluto até Ctrl+C. O log fica em resultados/.
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from sdrlink import quadro, radio
from sdrlink.modem import modular


def montar_buffer(cfg, rb: float, fs: float, n_pacotes: int, n_payload: int, semente: int, desloc: float,
                  arquivo: Path = None):
    sps = fs / rb
    if abs(sps - round(sps)) > 1e-9:
        raise SystemExit(f"fs/rb = {sps:g} não é inteiro; escolha uma taxa que divida {fs:g}.")
    sps = int(round(sps))
    dados = arquivo.read_bytes() if arquivo else None
    partes, pacotes = [], []
    for seq in range(n_pacotes):
        payload = (dados[seq * n_payload:(seq + 1) * n_payload] if dados
                   else quadro.payload_prbs(seq, n_payload, semente))
        partes += [modular(quadro.montar(seq, payload), sps, cfg), np.zeros(quadro.BITS_GUARDA * sps, complex)]
        pacotes.append({"seq": seq, "crc16": quadro.crc16(payload)})
    x = np.concatenate(partes)
    x = x * np.exp(2j * np.pi * desloc / fs * np.arange(len(x)))
    return x, sps, pacotes


def abrir_pluto(uri: str):
    radio.preparar_bibliotecas()
    import adi
    tentativas = [uri] if uri else ["ip:192.168.2.1", "ip:pluto.local", "usb:"]
    erro = None
    for u in tentativas:
        try:
            return adi.Pluto(u), u
        except Exception as e:      # tenta o próximo endereço
            erro = e
    raise SystemExit(f"Não foi possível conectar ao Pluto ({tentativas}): {erro}")


def transmitir_roteiro(args):
    """Troca de configuração a cada `passo` segundos, em laço, até Ctrl+C."""
    from sdrlink.modem import Config
    passos = []
    for esquema, pulso, rb in radio.ROTEIROS[args.roteiro]:
        cfg = Config(esquema=esquema, pulso=pulso, h=args.h, bt=args.bt, alfa=args.alfa)
        n = max(2, min(args.pacotes, int(2e6 // (quadro.bits_do_quadro(args.payload) * args.fs / rb))))
        x, _, _ = montar_buffer(cfg, rb, args.fs, n, args.payload, args.semente, args.desloc)
        passos.append((cfg, rb, n, radio.AMPLITUDE * x))
    sdr, uri = abrir_pluto(args.uri)
    sdr.sample_rate = int(args.fs)
    sdr.tx_rf_bandwidth = int(args.fs)
    sdr.tx_lo = int(args.freq)
    sdr.tx_hardwaregain_chan0 = args.ganho
    sdr.tx_cyclic_buffer = True
    eventos = []
    pasta = radio.RAIZ / "resultados"
    pasta.mkdir(exist_ok=True)
    nome = pasta / f"tx_roteiro_{args.roteiro}_{datetime.now():%Y%m%d_%H%M%S}.json"
    print(f"Roteiro '{args.roteiro}': {len(passos)} configurações, {args.passo:g} s cada, em "
          f"{(args.freq + args.desloc) / 1e6:.3f} MHz, ganho {args.ganho} dB, via {uri}. Ctrl+C para parar.")
    try:
        volta = 0
        while True:
            volta += 1
            for cfg, rb, n, x in passos:
                sdr.tx_destroy_buffer()
                sdr.tx(x)
                agora = datetime.now().astimezone().isoformat(timespec="seconds")
                eventos.append({"inicio": agora, "volta": volta, "modulacao": cfg.rotulo, "rb_bps": rb,
                                "quadros_no_buffer": n})
                nome.write_text(json.dumps({"roteiro": args.roteiro, "passo_s": args.passo, "fc_hz": args.freq,
                                            "deslocamento_hz": args.desloc, "ganho_tx_db": args.ganho,
                                            "fs_hz": args.fs, "prbs_semente": args.semente, "uri": uri,
                                            "eventos": eventos}, indent=2, ensure_ascii=False))
                print(f"  [{agora[11:19]}] volta {volta}: {cfg.rotulo} a {rb / 1e3:g} kbit/s ({n} quadros)")
                time.sleep(args.passo)
    except KeyboardInterrupt:
        print("\nEncerrando a transmissão...")
        sdr.tx_destroy_buffer()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    radio.argumentos_modem(ap)
    ap.add_argument("--pacotes", type=int, default=8, help="quadros distintos no buffer cíclico")
    ap.add_argument("--payload", type=int, default=128, help="bytes de payload por quadro")
    ap.add_argument("--arquivo", type=Path, help="arquivo binário de payloads (senão, PRBS)")
    ap.add_argument("--semente", type=int, default=2026)
    ap.add_argument("--freq", type=float, default=radio.FC)
    ap.add_argument("--desloc", type=float, default=radio.DESLOC)
    ap.add_argument("--fs", type=float, default=radio.FS_TX)
    ap.add_argument("--ganho", type=float, default=radio.GANHO_TX, help="ganho de TX em dB (0 = máximo)")
    ap.add_argument("--uri", help="endereço do Pluto, por exemplo ip:192.168.2.1")
    ap.add_argument("--roteiro", choices=sorted(radio.ROTEIROS), help="percorre uma sequência de configurações")
    ap.add_argument("--passo", type=float, default=15.0, help="segundos em cada configuração do roteiro")
    ap.add_argument("--seco", type=Path, help="não transmite: grava o buffer (2 repetições) em formato cu8")
    args = ap.parse_args()
    if args.roteiro:
        return transmitir_roteiro(args)
    cfg = radio.config_de(args)

    x, sps, pacotes = montar_buffer(cfg, args.rb, args.fs, args.pacotes, args.payload, args.semente,
                                    args.desloc, args.arquivo)
    bits = quadro.bits_do_quadro(args.payload)
    potencia = float(np.mean(np.abs(x) ** 2))
    log = {"inicio": datetime.now().astimezone().isoformat(timespec="seconds"), "modulacao": cfg.rotulo,
           "esquema": cfg.esquema, "pulso": cfg.pulso, "h": cfg.h, "bt": cfg.bt, "alfa": cfg.alfa,
           "rb_bps": args.rb, "fs_hz": args.fs, "amostras_por_bit": sps, "fc_hz": args.freq,
           "deslocamento_hz": args.desloc, "ganho_tx_db": args.ganho, "payload_bytes": args.payload,
           "bits_por_quadro": bits, "periodo_quadro_s": len(x) / args.pacotes / args.fs, "quadros_no_buffer": args.pacotes,
           "amostras_no_buffer": len(x), "modo": "ciclico", "prbs_semente": None if args.arquivo else args.semente,
           "potencia_media_rel_pico_db": round(10 * np.log10(potencia), 2),
           "goodput_maximo_bps": round(8 * args.payload * args.rb / bits, 1), "pacotes": pacotes}
    print(f"{cfg.rotulo} a {args.rb / 1e3:g} kbit/s: {args.pacotes} quadros de {bits} bits "
          f"({bits / args.rb * 1e3:.1f} ms cada), {len(x)} amostras, "
          f"potência média {log['potencia_media_rel_pico_db']} dB em relação ao pico")

    if args.seco:
        rng = np.random.default_rng(1)
        y = np.concatenate([np.zeros(5000, complex), x, x]) * 0.5
        y = y + 0.02 * (rng.standard_normal(len(y)) + 1j * rng.standard_normal(len(y)))
        iq = np.empty(2 * len(y), dtype=np.uint8)
        iq[0::2] = np.clip(np.rint(y.real * 127.5 + 127.5), 0, 255)
        iq[1::2] = np.clip(np.rint(y.imag * 127.5 + 127.5), 0, 255)
        iq.tofile(args.seco)
        args.seco.with_suffix(".json").write_text(json.dumps({"fs_hz": args.fs, "sintetico": True}, indent=2))
        print(f"Sinal gravado em {args.seco} (fs = {args.fs:g} Hz). Nada foi transmitido.")
        return

    sdr, uri = abrir_pluto(args.uri)
    sdr.sample_rate = int(args.fs)
    sdr.tx_rf_bandwidth = int(args.fs)
    sdr.tx_lo = int(args.freq)
    sdr.tx_hardwaregain_chan0 = args.ganho
    sdr.tx_cyclic_buffer = True
    log["uri"] = uri
    pasta = radio.RAIZ / "resultados"
    pasta.mkdir(exist_ok=True)
    nome = pasta / f"tx_{cfg.esquema}_{cfg.pulso}_{args.rb / 1e3:g}k_{datetime.now():%Y%m%d_%H%M%S}.json"
    nome.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"Transmitindo em {(args.freq + args.desloc) / 1e6:.3f} MHz, ganho {args.ganho} dB, via {uri}. "
          f"Ctrl+C para parar.\nLog: {nome}")
    sdr.tx(radio.AMPLITUDE * x)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando a transmissão...")
        sdr.tx_destroy_buffer()


if __name__ == "__main__":
    main()
