"""Executa o receptor OOK de referência sem alterar o arquivo original.

O código do professor é carregado como texto; apenas a constante de ppm pode
ser substituída em memória (--ppm), porque ela depende de cada RTL-SDR. A
janela gráfica é trocada por um arquivo PNG e a saída do terminal é registrada.

    .venv/bin/python etapa1_executar_referencia.py            # como entregue (34 ppm)
    .venv/bin/python etapa1_executar_referencia.py --ppm 56   # ppm calibrado deste dongle
"""
import argparse
import contextlib
import io
import re
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent
FONTE = RAIZ / "referencia_ook" / "rtl_rx_ook_v2.py"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ppm", type=int, help="substitui FREQ_CORRECTION_PPM em memória")
    ap.add_argument("--nome", help="sufixo dos arquivos de saída")
    args = ap.parse_args()
    codigo = FONTE.read_text()
    if args.ppm is not None:
        codigo, n = re.subn(r"^FREQ_CORRECTION_PPM = .*$", f"FREQ_CORRECTION_PPM = {args.ppm}", codigo, flags=re.M)
        assert n == 1
    nome = args.nome or ("original" if args.ppm is None else f"ppm{args.ppm}")
    figura = RAIZ / "resultados" / f"referencia_rx_{nome}.png"
    plt.show = lambda *a, **k: plt.gcf().savefig(figura, dpi=110)
    saida = io.StringIO()

    class Duplo(io.TextIOBase):
        def write(self, s):
            sys.__stdout__.write(s)
            return saida.write(s)

    erro = None
    with contextlib.redirect_stdout(Duplo()):
        try:
            exec(compile(codigo, str(FONTE), "exec"), {"__name__": "__main__"})
        except Exception as e:      # o original interrompe com exceção quando a captura não serve
            erro = f"{type(e).__name__}: {e}"
            print("ERRO:", erro)
    log = RAIZ / "resultados" / f"referencia_rx_{nome}.txt"
    cabecalho = (f"# rtl_rx_ook_v2.py, {datetime.now().astimezone().isoformat(timespec='seconds')}, "
                 f"ppm={'34 (original)' if args.ppm is None else args.ppm}\n")
    log.write_text(cabecalho + saida.getvalue().replace("\r", "\n"))
    print(f"\nLog: {log}" + ("" if erro else f"\nFigura: {figura}"))


if __name__ == "__main__":
    main()
