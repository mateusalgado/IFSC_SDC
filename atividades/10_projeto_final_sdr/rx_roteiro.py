"""Caracteriza o enlace enquanto o Pluto percorre um roteiro (tx_pluto.py --roteiro).

O receptor grava janelas curtas em sequência e tenta decodificar cada janela com
todas as configurações do roteiro; a que produz quadros válidos identifica o que
estava no ar. Os resultados são acumulados por configuração.

    .venv/bin/python rx_roteiro.py --roteiro basico --ppm 56 --minutos 3

Saída: resultados/bancada_<roteiro>_<horário>.json e uma captura de exemplo por
configuração em capturas/roteiro_<...>.cu8.
"""
import argparse
import json
import shutil
import time
from datetime import datetime

import numpy as np

from rx_decodificar import banda_medida, carregar, perdas_por_intervalo
from rx_gravar import abrir, gravar
from sdrlink import quadro, radio
from sdrlink.modem import Config
from sdrlink.receptor import receber


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roteiro", choices=sorted(radio.ROTEIROS), default="basico")
    ap.add_argument("--ppm", type=int, default=0)
    ap.add_argument("--ganho", type=float, default=radio.GANHO_RX)
    ap.add_argument("--freq", type=float, default=radio.FC)
    ap.add_argument("--fs", type=float, default=radio.FS_RX)
    ap.add_argument("--desloc", type=float, default=radio.DESLOC)
    ap.add_argument("--janela", type=float, default=5.0, help="segundos por captura")
    ap.add_argument("--minutos", type=float, default=3.0, help="duração total do ensaio")
    ap.add_argument("--semente", type=int, default=2026)
    ap.add_argument("--nota", default="", help="descrição da montagem (distância, antenas)")
    args = ap.parse_args()

    configs = radio.ROTEIROS[args.roteiro]
    pasta = radio.RAIZ / "capturas"
    pasta.mkdir(exist_ok=True)
    tmp = pasta / "_roteiro_tmp.cu8"
    horario = datetime.now()
    acum = {c: {"capturas": 0, "validos": 0, "perdidos": 0, "crc_invalido": 0, "candidatos": 0,
                "conteudo_errado": 0, "bits_errados": 0, "bits_comparados": 0, "tempo_util_s": 0.0,
                "offsets": [], "rho": [], "banda": [], "exemplo": None} for c in configs}
    sdr = abrir(args.freq, args.fs, args.ganho, args.ppm)
    ganho_real = sdr.gain
    n = int(args.janela * args.fs)
    fim = time.time() + 60 * args.minutos
    print(f"Roteiro '{args.roteiro}' ({len(configs)} configurações), {args.minutos:g} min, ppm {args.ppm}, "
          f"ganho {ganho_real:.1f} dB. Ctrl+C encerra e salva.")
    try:
        while time.time() < fim:
            gravar(sdr, tmp, n)
            bases, achados = {}, []
            for c in configs:
                esquema, pulso, rb = c
                if rb not in bases:
                    bases[rb] = carregar(tmp, args.fs, rb, 8, args.desloc)[0]
                cfg = Config(esquema=esquema, pulso=pulso)
                pacotes, cont = receber(bases[rb], 8, cfg, rb)
                if len(pacotes) < 3:
                    continue
                a = acum[c]
                tempos = np.array([p.tempo_s for p in pacotes])
                tam = len(pacotes[0].payload)
                perdidos, _ = perdas_por_intervalo(tempos, quadro.bits_do_quadro(tam) / rb)
                a["capturas"] += 1
                a["validos"] += len(pacotes)
                a["perdidos"] += perdidos
                a["crc_invalido"] += cont["crc_invalido"]
                a["candidatos"] += cont["candidatos"]
                a["tempo_util_s"] += float(tempos[-1] - tempos[0])
                a["offsets"] += [p.offset_hz for p in pacotes]
                a["rho"] += [p.rho for p in pacotes]
                for p in pacotes:
                    ref = quadro.payload_prbs(p.seq, len(p.payload), args.semente)
                    a["bits_comparados"] += 8 * len(ref)
                    if p.payload != ref:
                        a["conteudo_errado"] += 1
                        a["bits_errados"] += int(np.sum(np.unpackbits(np.frombuffer(p.payload, np.uint8))
                                                        != np.unpackbits(np.frombuffer(ref, np.uint8))))
                cobre = (tempos[-1] - tempos[0]) > 0.85 * args.janela
                achados.append((c, len(pacotes), perdidos, cobre))
            # banda e captura de exemplo só quando uma única configuração ocupa a janela inteira
            if len(achados) == 1 and achados[0][3]:
                c = achados[0][0]
                acum[c]["banda"].append(banda_medida(tmp, args.fs, args.desloc, min(12 * c[2], 0.55e6)))
                if acum[c]["exemplo"] is None:
                    destino = pasta / f"roteiro_{c[0]}_{c[1]}_{c[2] / 1e3:g}k.cu8"
                    shutil.copyfile(tmp, destino)
                    destino.with_suffix(".json").write_text(json.dumps(
                        {"fc_hz": args.freq, "fs_hz": args.fs, "ganho_db": ganho_real, "ppm": args.ppm,
                         "inicio": datetime.now().astimezone().isoformat(timespec="seconds"),
                         "amostras": n}, indent=2))
                    acum[c]["exemplo"] = destino.name
            texto = "; ".join(f"{c[0]}/{c[1]}/{c[2] / 1e3:g}k: {v} válidos, {p} perdidos" for c, v, p, _ in achados)
            if not achados:
                # Nada do roteiro: confere se o que está no ar é a OOK de referência do professor.
                base = bases.get(10e3)
                if base is None:
                    base = carregar(tmp, args.fs, 10e3, 8, args.desloc)[0]
                ref, _ = receber(base, 8, Config("ook", "rampa"), 10e3, formato="referencia")
                texto = (f"nenhuma configuração do roteiro; o Pluto está enviando a OOK de REFERÊNCIA "
                         f"({len(ref)} quadros, mensagem {ref[0].payload.decode('ascii', 'replace')!r}). "
                         f"Rode tx_pluto.py --roteiro {args.roteiro} no computador do Pluto."
                         if len(ref) >= 3 else
                         "nenhum quadro reconhecido (nem do roteiro, nem da referência): confira ppm, ganho e se o Pluto transmite")
            print(f"  [{datetime.now():%H:%M:%S}] {texto}")
    except KeyboardInterrupt:
        print("\nInterrompido; salvando.")
    sdr.close()
    tmp.unlink(missing_ok=True)

    linhas = []
    for (esquema, pulso, rb), a in acum.items():
        total = a["validos"] + a["perdidos"]
        tam = 128
        linha = {"modulacao": Config(esquema=esquema, pulso=pulso).rotulo, "esquema": esquema, "pulso": pulso,
                 "rb_bps": rb, "capturas_reconhecidas": a["capturas"], "quadros_validos": a["validos"],
                 "quadros_perdidos": a["perdidos"], "per": a["perdidos"] / total if total else None,
                 "crc_invalido": a["crc_invalido"], "candidatos": a["candidatos"],
                 "aceitos_com_conteudo_errado": a["conteudo_errado"], "bits_comparados": a["bits_comparados"],
                 "bits_errados": a["bits_errados"],
                 "goodput_bps": round(8 * tam * (a["validos"] - a["conteudo_errado"]) / a["tempo_util_s"], 1)
                 if a["tempo_util_s"] > 0 else None,
                 "goodput_maximo_bps": round(8 * tam * rb / quadro.bits_do_quadro(tam), 1),
                 "captura_exemplo": a["exemplo"]}
        if a["offsets"]:
            linha["offset_residual_hz"] = {"media": round(float(np.mean(a["offsets"])), 1),
                                           "desvio": round(float(np.std(a["offsets"])), 1)}
            linha["rho_medio"] = round(float(np.mean(a["rho"])), 3)
        if a["banda"]:
            linha["banda_99_hz"] = round(float(np.median([b["banda_99_hz"] for b in a["banda"]])), 0)
            linha["sinal_sobre_ruido_na_janela_db"] = round(float(np.median(
                [b["sinal_sobre_ruido_na_janela_db"] for b in a["banda"]])), 1)
            linha["medidas_de_banda"] = len(a["banda"])
        linhas.append(linha)
    saida = radio.RAIZ / "resultados" / f"bancada_{args.roteiro}_{horario:%Y%m%d_%H%M%S}.json"
    saida.write_text(json.dumps({"inicio": horario.astimezone().isoformat(timespec="seconds"),
                                 "roteiro": args.roteiro, "fc_hz": args.freq, "fs_hz": args.fs,
                                 "deslocamento_hz": args.desloc, "ganho_rx_db": ganho_real, "ppm": args.ppm,
                                 "janela_s": args.janela, "nota": args.nota, "resultados": linhas},
                                indent=2, ensure_ascii=False))
    print(f"\n{'modulação':16s} {'Rb':>7s} {'válidos':>8s} {'perd.':>6s} {'PER':>8s} {'goodput':>9s} "
          f"{'offset':>12s} {'banda 99%':>10s}")
    for r in linhas:
        if not r["quadros_validos"]:
            print(f"{r['modulacao']:16s} {r['rb_bps'] / 1e3:6g}k  não recebida")
            continue
        o = r["offset_residual_hz"]
        banda = f"{r['banda_99_hz'] / 1e3:.0f} kHz" if "banda_99_hz" in r else "-"
        print(f"{r['modulacao']:16s} {r['rb_bps'] / 1e3:6g}k {r['quadros_validos']:8d} {r['quadros_perdidos']:6d} "
              f"{r['per']:8.4f} {r['goodput_bps']:9.0f} {o['media']:+6.0f}±{o['desvio']:<4.0f} {banda:>10s}")
    print(f"\n{saida}")


if __name__ == "__main__":
    main()
