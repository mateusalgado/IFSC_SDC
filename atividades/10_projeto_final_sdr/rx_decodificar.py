"""Decodifica uma captura IQ do RTL-SDR e calcula as métricas do ensaio.

    .venv/bin/python rx_decodificar.py capturas/ook_ref.cu8 --formato referencia
    .venv/bin/python rx_decodificar.py capturas/fsk_20k.cu8 --esquema fsk --rb 20e3 --prbs

Saídas, ao lado da captura:
    <nome>_pacotes.csv     sequência, instante, offset estimado, correlação e payload (hex)
    <nome>_resultado.json  contadores, PER, goodput, BER, offset residual e banda de 99%

PER em transmissão cíclica: o transmissor repete o buffer sem parar, então os
quadros perdidos são contados pelos intervalos entre quadros válidos
consecutivos (um intervalo de k períodos indica k-1 quadros perdidos).
"""
import argparse
import csv
import json
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

from sdrlink import metricas, quadro, radio
from sdrlink.receptor import cu8_para_complexo, preparar, receber


def carregar(arquivo: Path, fs: float, rb: float, sps: int, f_desloc: float, bloco: int = 1 << 22):
    """Lê a captura em blocos, leva o sinal a 0 Hz e reamostra para rb*sps."""
    bruto = np.memmap(arquivo, dtype=np.uint8, mode="r")
    n = len(bruto) // 2
    razao = Fraction(int(round(rb * sps)), int(round(fs)))
    cima, baixo = razao.numerator, razao.denominator
    bloco -= bloco % baixo
    margem = 64 * baixo
    partes, saturadas = [], 0
    for c0 in range(0, n, bloco):
        a, b = max(0, c0 - margem), min(n, c0 + bloco + margem)
        trecho = np.asarray(bruto[2 * a:2 * b])
        if c0 == 0 or True:
            centro = trecho[2 * (c0 - a):2 * (min(c0 + bloco, n) - a)]
            saturadas += int(np.count_nonzero((centro == 0) | (centro == 255)))
        x = cu8_para_complexo(trecho)
        x -= x.mean()                                   # remove o DC do RTL-SDR
        y = preparar(x, fs, rb, sps, f_desloc, n0=a)
        ini = (c0 - a) * cima // baixo
        partes.append(y[ini:ini + (min(c0 + bloco, n) - c0) * cima // baixo])
    return np.concatenate(partes), n, saturadas / (2 * n)


def banda_medida(arquivo: Path, fs: float, f_centro: float, meia_janela: float, amostras: int = 1 << 24):
    """Banda de 99% pela PSD da captura, descontado o piso de ruído (mediana da PSD)."""
    bruto = np.fromfile(arquivo, dtype=np.uint8, count=2 * amostras)
    x = cu8_para_complexo(bruto)
    x -= x.mean()
    f, p = metricas.psd(x, fs, 1 << 14)
    piso = np.median(p)
    dentro = np.abs(f - f_centro) <= meia_janela
    f, p = f[dentro], np.maximum(p[dentro] - piso, 0)
    acum = np.cumsum(p) / np.sum(p)
    f_inf, f_sup = f[np.searchsorted(acum, 0.005)], f[min(np.searchsorted(acum, 0.995), len(f) - 1)]
    snr = 10 * np.log10(np.sum(p) / (piso * np.count_nonzero(dentro)))
    return {"banda_99_hz": float(f_sup - f_inf), "f_inferior_hz": float(f_inf), "f_superior_hz": float(f_sup),
            "janela_hz": 2 * meia_janela, "sinal_sobre_ruido_na_janela_db": round(float(snr), 1)}


def perdas_por_intervalo(tempos: np.ndarray, periodo: float):
    """Quadros perdidos entre o primeiro e o último quadro válido de uma transmissão cíclica."""
    if len(tempos) < 2:
        return 0, len(tempos)
    passos = np.rint(np.diff(tempos) / periodo).astype(int)
    perdidos = int(np.sum(np.maximum(passos - 1, 0)))
    return perdidos, perdidos + len(tempos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captura", type=Path)
    radio.argumentos_modem(ap)
    ap.add_argument("--formato", choices=("projeto", "referencia"), default="projeto")
    ap.add_argument("--fs", type=float, help="taxa da captura (padrão: a do .json da captura)")
    ap.add_argument("--desloc", type=float, default=radio.DESLOC)
    ap.add_argument("--sps", type=int, default=8, help="amostras por bit no processamento")
    ap.add_argument("--limiar", type=float, default=0.6, help="correlação mínima do sincronismo")
    ap.add_argument("--prbs", action="store_true", help="compara com quadro.payload_prbs(seq)")
    ap.add_argument("--semente", type=int, default=2026)
    ap.add_argument("--janela-banda", type=float, help="meia janela da banda de 99%%, Hz (padrão 12·Rb)")
    args = ap.parse_args()
    cfg = radio.config_de(args)

    meta_arq = args.captura.with_suffix(".json")
    meta = json.loads(meta_arq.read_text()) if meta_arq.exists() else {}
    fs = args.fs or meta.get("fs_hz", radio.FS_RX)

    t0 = time.time()
    x, n, saturadas = carregar(args.captura, fs, args.rb, args.sps, args.desloc)
    t1 = time.time()
    pacotes, cont = receber(x, args.sps, cfg, args.rb, limiar=args.limiar, formato=args.formato)
    t2 = time.time()
    duracao = n / fs

    with open(args.captura.with_name(args.captura.stem + "_pacotes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "tempo_s", "offset_hz", "rho", "duplicado", "payload_hex"])
        for p in pacotes:
            w.writerow([p.seq, f"{p.tempo_s:.6f}", f"{p.offset_hz:.1f}", f"{p.rho:.3f}", int(p.duplicado), p.payload.hex()])

    res = {"captura": args.captura.name, "captura_meta": meta, "modulacao": cfg.rotulo, "rb_bps": args.rb,
           "formato_quadro": args.formato, "duracao_s": round(duracao, 3), "fracao_saturada": saturadas,
           "sps_processamento": args.sps, "limiar_sincronismo": args.limiar, "receptor": cont,
           "quadros_validos": len(pacotes),
           "tempo_processamento_s": {"conversao": round(t1 - t0, 2), "deteccao": round(t2 - t1, 2)}}
    if pacotes:
        off = np.array([p.offset_hz for p in pacotes])
        tam = max(set(len(p.payload) for p in pacotes), key=[len(p.payload) for p in pacotes].count)
        bits_quadro = (quadro.bits_do_quadro_referencia(tam) if args.formato == "referencia"
                       else quadro.bits_do_quadro(tam))
        periodo = bits_quadro / args.rb
        tempos = np.array([p.tempo_s for p in pacotes])
        perdidos, total = perdas_por_intervalo(tempos, periodo)
        res.update({
            "offset_residual_hz": {"media": round(float(off.mean()), 1), "desvio": round(float(off.std()), 1),
                                   "min": round(float(off.min()), 1), "max": round(float(off.max()), 1)},
            "rho_medio": round(float(np.mean([p.rho for p in pacotes])), 3),
            "payload_bytes": tam, "bits_por_quadro": bits_quadro, "periodo_quadro_s": periodo,
            "ciclico": {"quadros_no_intervalo": total, "perdidos": perdidos,
                        "per": perdidos / total if total else None,
                        "goodput_bancada_bps": round(8 * tam * len(pacotes) / duracao, 1),
                        "goodput_maximo_bps": round(8 * tam / periodo, 1)}})
        conteudos = {}
        for p in pacotes:
            conteudos[p.payload] = conteudos.get(p.payload, 0) + 1
        res["payloads_distintos"] = len(conteudos)
        if args.formato == "referencia":
            comum = max(conteudos, key=conteudos.get)
            res["mensagem_mais_frequente"] = comum.decode("ascii", errors="replace")
            res["quadros_com_outro_conteudo"] = len(pacotes) - conteudos[comum]
        if args.prbs and args.formato == "projeto":
            errados = erros = comparados = 0
            for p in pacotes:
                ref = quadro.payload_prbs(p.seq, len(p.payload), args.semente)
                comparados += 8 * len(ref)
                if p.payload != ref:
                    errados += 1
                    erros += int(np.sum(np.unpackbits(np.frombuffer(p.payload, np.uint8))
                                        != np.unpackbits(np.frombuffer(ref, np.uint8))))
            res["prbs"] = {"quadros_comparados": len(pacotes), "aceitos_com_conteudo_errado": errados,
                           "bits_comparados": comparados, "bits_errados": erros,
                           "ber_quadros_aceitos": erros / comparados if comparados else None}
    res["banda"] = banda_medida(args.captura, fs, args.desloc, args.janela_banda or 12 * args.rb)
    saida = args.captura.with_name(args.captura.stem + "_resultado.json")
    saida.write_text(json.dumps(res, indent=2, ensure_ascii=False))

    print(f"{cfg.rotulo}, {args.rb / 1e3:g} kbit/s, quadro {args.formato}: {duracao:.1f} s de captura, "
          f"{100 * saturadas:.3f}% saturado")
    print(f"  candidatos {cont['candidatos']} | CRC inválido {cont['crc_invalido']} | válidos {len(pacotes)}")
    if pacotes:
        c = res["ciclico"]
        o = res["offset_residual_hz"]
        print(f"  PER (por intervalos) {c['per']:.4f} ({c['perdidos']} perdidos em {c['quadros_no_intervalo']}) | "
              f"goodput {c['goodput_bancada_bps']:.0f} bit/s (máx. {c['goodput_maximo_bps']:.0f})")
        print(f"  offset residual {o['media']:+.0f} ± {o['desvio']:.0f} Hz | rho médio {res['rho_medio']:.3f}")
        if "prbs" in res:
            print(f"  BER nos quadros aceitos: {res['prbs']['bits_errados']} erros em {res['prbs']['bits_comparados']} bits")
        if "mensagem_mais_frequente" in res:
            print(f"  mensagem: {res['mensagem_mais_frequente']!r} (outros conteúdos: {res['quadros_com_outro_conteudo']})")
    b = res["banda"]
    print(f"  banda de 99%: {b['banda_99_hz'] / 1e3:.1f} kHz (janela de {b['janela_hz'] / 1e3:.0f} kHz, "
          f"S/N {b['sinal_sobre_ruido_na_janela_db']} dB)")
    print(f"  processamento: {t2 - t0:.1f} s  ->  {saida.name}")


if __name__ == "__main__":
    main()
