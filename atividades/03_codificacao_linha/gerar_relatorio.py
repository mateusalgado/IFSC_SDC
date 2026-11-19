from pathlib import Path

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from padronizar_relatorios import render
    for source in sorted(Path(__file__).parent.glob("relatorio_*_*.md")):
        print(render(source))
    raise SystemExit(0)


import re
from pathlib import Path

try:
    import markdown
except ImportError:
    markdown = None
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import welch
try:
    from weasyprint import HTML
except Exception:
    HTML = None

from cat5_eth_channel import cat5_channel

BASE = Path(__file__).resolve().parent
FIG_DIR = BASE / "figuras"
MD_PATH = BASE / "relatorio_03_pt.md"
PDF_PATH = BASE / "relatorio_03_pt.pdf"


def unipolar_nrz(bits, Rb, fs):
    bits = np.asarray(bits, dtype=float)
    ns = max(1, int(round(fs / Rb)))
    sinal = np.repeat(bits, ns)
    t = np.arange(len(sinal)) / fs
    return t, sinal


def unipolar_rz(bits, Rb, fs):
    bits = np.asarray(bits, dtype=float)
    ns = max(1, int(round(fs / Rb)))
    half = max(1, ns // 2)
    sinal = np.zeros(bits.size * ns, dtype=float)
    for i, bit in enumerate(bits):
        inicio = i * ns
        sinal[inicio:inicio + half] = bit
    t = np.arange(len(sinal)) / fs
    return t, sinal


def bipolar_nrz(bits, Rb, fs):
    bits = np.asarray(bits, dtype=int)
    ns = max(1, int(round(fs / Rb)))
    sinal = np.zeros(bits.size * ns, dtype=float)
    nivel = 1
    for i, bit in enumerate(bits):
        inicio = i * ns
        if bit == 1:
            sinal[inicio:inicio + ns] = nivel
            nivel *= -1
    t = np.arange(len(sinal)) / fs
    return t, sinal


def bipolar_rz(bits, Rb, fs):
    bits = np.asarray(bits, dtype=int)
    ns = max(1, int(round(fs / Rb)))
    half = max(1, ns // 2)
    sinal = np.zeros(bits.size * ns, dtype=float)
    nivel = 1
    for i, bit in enumerate(bits):
        inicio = i * ns
        if bit == 1:
            sinal[inicio:inicio + half] = nivel
            nivel *= -1
    t = np.arange(len(sinal)) / fs
    return t, sinal


def polar_quaternario_nrz(bits, Rb, fs):
    bits = np.asarray(bits, dtype=int)
    if bits.size % 2 != 0:
        bits = np.concatenate([bits, [0]])
    simbolos = np.empty(bits.size // 2, dtype=int)
    mapeamento = {0: -3, 1: -1, 2: 1, 3: 3}
    for i in range(simbolos.size):
        par = bits[2 * i:2 * i + 2]
        valor = int(par[0]) * 2 + int(par[1])
        simbolos[i] = mapeamento[valor]
    Tsim = 2 / Rb
    ns = max(1, int(round(fs * Tsim)))
    sinal = np.repeat(simbolos, ns).astype(float)
    t = np.arange(len(sinal)) / fs
    return t, sinal


def manchester(bits, Rb, fs):
    bits = np.asarray(bits, dtype=int)
    ns = max(1, int(round(fs / Rb)))
    sinal = np.zeros(bits.size * ns, dtype=float)
    meio = max(1, ns // 2)
    for i, bit in enumerate(bits):
        inicio = i * ns
        polaridade = 1 if bit == 1 else -1
        sinal[inicio:inicio + meio] = polaridade
        sinal[inicio + meio:inicio + ns] = -polaridade
    t = np.arange(len(sinal)) / fs
    return t, sinal


def generate_figures() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    np.random.seed(789)
    bits = np.random.randint(0, 2, size=800)
    Rb = 10e6
    fs = 200 * Rb

    time_data = [
        ("NRZ", unipolar_nrz(bits, Rb, fs)[1]),
        ("RZ", unipolar_rz(bits, Rb, fs)[1]),
        ("AMI NRZ", bipolar_nrz(bits, Rb, fs)[1]),
        ("AMI RZ", bipolar_rz(bits, Rb, fs)[1]),
        ("QPSK/4 níveis", polar_quaternario_nrz(bits, Rb, fs)[1]),
    ]

    fig, ax = plt.subplots(figsize=(12, 7))
    for label, sinal in time_data:
        t = np.arange(len(sinal)) / fs
        amostras = min(len(sinal), int(fs * 4 / Rb))
        ax.plot(t[:amostras], sinal[:amostras], lw=1.2, label=label)
    ax.set_title("Trecho representativo das codificações de linha (Rb = 10 Mbps)")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Amplitude")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "codificacoes_tempo.png", dpi=180)
    plt.close(fig)

    _, ax = plt.subplots(figsize=(10, 5.5))
    for label, func in [
        ("RZ", unipolar_rz),
        ("Manchester", manchester),
    ]:
        _, sinal = func(bits, Rb, fs)
        f, psd = welch(sinal, fs=fs, nperseg=min(4096, len(sinal)))
        ax.plot(f, psd, lw=1.5, label=label)
    ax.set_title("PSD comparando RZ e Manchester")
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("PSD")
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "psd_rz_manchester.png", dpi=180)
    plt.close()

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=False)
    for idx, Rb_plot in enumerate([10e6, 40e6, 100e6]):
        fs_plot = max(200 * Rb_plot, 100e6)
        _, sinal_tx = unipolar_nrz(bits, Rb_plot, fs_plot)
        sinal_rx = cat5_channel(sinal_tx, fs_plot, length_m=49.0)
        tempo = np.arange(len(sinal_rx)) / fs_plot
        amostras = min(len(sinal_rx), int(fs_plot * 2 / Rb_plot))
        axes[idx].plot(tempo[:amostras], sinal_rx[:amostras], lw=1.0)
        axes[idx].set_title(f"Sinal recebido após o cabo CAT5e — {Rb_plot/1e6:.0f} Mbps")
        axes[idx].set_ylabel("Amplitude")
        axes[idx].grid(alpha=0.3)
    axes[-1].set_xlabel("Tempo (s)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "cat5_recebido.png", dpi=180)
    plt.close(fig)


def render_pdf() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    html = markdown.markdown(
        text,
        extensions=["extra", "tables", "sane_lists", "fenced_code"],
    )
    html = re.sub(r'src="([^"]+)"', lambda m: f'src="file://{(BASE / m.group(1)).resolve()}"', html)
    styled = f"""
    <!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8" />
        <style>
          @page {{ size: A4; margin: 2.2cm; }}
          body {{
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.5;
            color: #111827;
            margin: 0;
          }}
          h1, h2, h3 {{
            color: #0f172a;
            page-break-after: avoid;
          }}
          h1 {{ font-size: 24pt; margin-top: 0; }}
          h2 {{ font-size: 18pt; margin-top: 1.2em; }}
          h3 {{ font-size: 14pt; margin-top: 1em; }}
          p, li {{ text-align: justify; }}
          strong {{ color: #0f172a; }}
          img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
            border: 1px solid #cbd5e1;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            font-size: 10.5pt;
          }}
          th, td {{
            border: 1px solid #cbd5e1;
            padding: 0.4em 0.5em;
            vertical-align: top;
            text-align: left;
          }}
          th {{ background: #f1f5f9; }}
          code {{ background: #f8fafc; padding: 0.1em 0.3em; }}
          blockquote {{
            border-left: 4px solid #cbd5e1;
            margin-left: 0;
            padding-left: 1em;
            color: #475569;
          }}
        </style>
      </head>
      <body>
        {html}
      </body>
    </html>
    """
    HTML(string=styled).write_pdf(str(PDF_PATH))
    print(f"PDF gerado em: {PDF_PATH}")


def main() -> None:
    generate_figures()
    render_pdf()
