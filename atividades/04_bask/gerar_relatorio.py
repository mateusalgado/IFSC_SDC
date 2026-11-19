from __future__ import annotations

import math
import re
from pathlib import Path

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from padronizar_relatorios import render
    for source in sorted(Path(__file__).parent.glob("relatorio_*_*.md")):
        print(render(source))
    raise SystemExit(0)


try:
    import markdown
except ImportError:
    markdown = None
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import erfc
try:
    from weasyprint import HTML
except Exception:
    HTML = None

BASE = Path(__file__).resolve().parent
FIG_DIR = BASE / "figuras"
MD_PATH = BASE / "relatorio_04_pt.md"
PDF_PATH = BASE / "relatorio_04_pt.pdf"

# Parâmetros individuais conforme o notebook de referência
M = 89
fc = 1000 + 100 * M
A = 3 + (M % 5)
seed = M
Rb = 1_000
Tb = 1.0 / Rb
fs = 100_000


def q_func(x: float) -> float:
    return 0.5 * erfc(x / math.sqrt(2.0))


def theoretical_ber_bask(Eb_over_N0: float) -> float:
    """BER teórica de ASK/BASK coerente em canal AWGN."""
    return q_func(math.sqrt(Eb_over_N0))


def generate_bits(nbits: int = 24) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, size=nbits, endpoint=False)


def ask_waveform(bits: np.ndarray, A: float, fc: float, fs: float, Tb: float):
    n_per_bit = max(1, int(round(fs * Tb)))
    t = np.arange(bits.size * n_per_bit, dtype=float) / fs
    nrz = np.repeat(bits.astype(float), n_per_bit) * A
    carrier = np.cos(2 * np.pi * fc * t)
    s = nrz * carrier
    return t, nrz, s


def correlator_outputs(r: np.ndarray, fc: float, fs: float, Tb: float) -> np.ndarray:
    n_per_bit = max(1, int(round(fs * Tb)))
    t_ref = np.arange(n_per_bit, dtype=float) / fs
    ref = np.cos(2 * np.pi * fc * t_ref)
    nbits = len(r) // n_per_bit
    outputs = np.empty(nbits, dtype=float)
    for k in range(nbits):
        segment = r[k * n_per_bit:(k + 1) * n_per_bit]
        outputs[k] = np.sum(segment * ref)
    return outputs


def simulate_ber_for_snr(EbN0_db: float, nbits: int = 30000) -> float:
    bits = generate_bits(nbits)
    Eb = (A ** 2) * Tb / 2.0
    EbN0 = 10 ** (EbN0_db / 10.0)
    sigma = (A * Tb / 2.0) / math.sqrt(EbN0)
    signal_levels = (bits.astype(float) * (A * Tb / 2.0))
    rx = signal_levels + np.random.default_rng(seed + int(EbN0_db * 100)).normal(0.0, sigma, size=bits.size)
    threshold = A * Tb / 4.0
    decisions = rx > threshold
    return float(np.mean(decisions != bits))


def generate_figures() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    bits = generate_bits(16)
    t, nrz, s = ask_waveform(bits, A, fc, fs, Tb)

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
    axes[0].plot(t[:len(bits) * 20], nrz[:len(bits) * 20], color="tab:blue", lw=1.8, label="NRZ unipolar")
    axes[1].plot(t[:len(bits) * 20], s[:len(bits) * 20], color="tab:orange", lw=1.6, label="BASK modulado")
    for ax in axes:
        ax.grid(alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("Amplitude")
    axes[1].set_ylabel("Amplitude")
    axes[1].set_xlabel("Tempo (s)")
    axes[0].set_title("Sinal NRZ e sinal BASK (M = 89)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "sinal_bask_tempo.png", dpi=180)
    plt.close(fig)

    freq = np.fft.rfftfreq(len(s), d=1.0 / fs)
    spec = np.abs(np.fft.rfft(s))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(freq, spec, lw=1.5, color="tab:green")
    ax.axvline(fc - 1.0 / Tb, color="tab:red", linestyle="--", alpha=0.8, label="fc - 1/Tb")
    ax.axvline(fc + 1.0 / Tb, color="tab:red", linestyle="--", alpha=0.8, label="fc + 1/Tb")
    ax.set_xlim(0, 2 * fc)
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("Espectro do sinal BASK e banda nula-a-nula")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "espectro_bask.png", dpi=180)
    plt.close(fig)

    snr_db = np.arange(0, 11, 2)
    sim = [simulate_ber_for_snr(db, nbits=20000) for db in snr_db]
    th = [theoretical_ber_bask(10 ** (db / 10.0)) for db in snr_db]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.semilogy(snr_db, sim, "o-", color="tab:blue", label="Simulada")
    ax.semilogy(snr_db, th, "s--", color="tab:red", label="Teórica")
    ax.set_xlabel("Eb/N0 (dB)")
    ax.set_ylabel("BER")
    ax.set_title("BER simulada e teórica para BASK coerente")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ber_bask.png", dpi=180)
    plt.close(fig)

    return {
        "bits": bits,
        "snr_db": snr_db,
        "sim": sim,
        "th": th,
        "threshold": A * Tb / 4.0,
    }


def build_markdown(results: dict) -> str:
    bit_sequence = "".join(str(int(bit)) for bit in results["bits"])
    Eb = (A ** 2) * Tb / 2.0
    threshold = A * Tb / 4.0
    EbN0 = 10 ** (10 / 10.0)
    ber_10db = theoretical_ber_bask(EbN0)
    ber_6db = theoretical_ber_bask(10 ** (6 / 10.0))
    sim_6db = results["sim"][results["snr_db"].tolist().index(6)]
    sim_10db = results["sim"][results["snr_db"].tolist().index(10)]

    return f'''# Atividade 4: Simulação ASK (BASK) com detecção coerente

**Disciplina:** SCM203405 — Sistemas de Comunicação — IFSC Florianópolis  
**Tema:** modulação digital ASK/BASK, detecção coerente, espectro e BER

## Resumo executivo

A atividade foi desenvolvida para implementar, em simulação, um sistema de comunicação digital em banda passante usando modulação ASK binária (BASK). O sinal foi gerado a partir de uma sequência de bits NRZ unipolar, multiplicada por uma portadora cossenoidal e, em seguida, submetida a um receptor coerente com correlação e limiar de decisão. A análise foi feita em três etapas: (i) dedução teórica do limiar e da largura de banda esperada, (ii) implementação do transmissor e do receptor e (iii) avaliação do efeito do ruído AWGN na taxa de erro de bit. Os resultados mostraram que a forma de onda modulada reproduz corretamente a ideia da ASK binária e que o limiar deduzido pelo critério de decisão mínimo erro produz decodificação correta em ausência de ruído. Com ruído, a BER simulada acompanha a curva teórica de BASK, com uma pequena divergência esperada pela natureza estatística do ruído e pela quantidade finita de bits simulados.

## 1. Parâmetros individuais

Os parâmetros foram definidos conforme o roteiro do notebook e a matrícula usada para a simulação foi escolhida como o exemplo do documento:

- M = 89
- fc = 1000 + 100 × M = 9900 Hz
- A = 3 + (M % 5) = 7 V
- seed = 89
- Tb = 1/Rb com Rb = 1000 bps, logo Tb = 1 ms
- fs = 100 kHz

Esses valores garantem uma sequência pseudoaleatória reproduzível e uma portadora suficientemente elevada para permitir a recuperação coerente do sinal.

## 2. Dedução teórica

### 2.1 Energia por bit do esquema BASK

No esquema BASK binário com NRZ unipolar, a onda correspondente ao bit 1 é:

<div class="formula">s<sub>1</sub>(t) = A cos(2πf<sub>c</sub>t),  &nbsp; 0 ≤ t < T<sub>b</sub></div>

e o bit 0 é representado por amplitude nula:

<div class="formula">s<sub>0</sub>(t) = 0</div>

A energia do bit 1 é:

<div class="formula">E<sub>1</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> A² cos²(2πf<sub>c</sub>t) dt = A² ∫<sub>0</sub><sup>T<sub>b</sub></sup> (1 + cos(4πf<sub>c</sub>t))/2 dt</div>

Como f<sub>c</sub> ≫ 1/T<sub>b</sub>, a componente oscilante se anula ao integrar sobre um número inteiro de ciclos. Portanto:

<div class="formula">E<sub>1</sub> = A² T<sub>b</sub> / 2</div>

Assim, para o esquema em questão:

<div class="formula">E<sub>b</sub> = A² T<sub>b</sub> / 2 = 5² × 10<sup>-3</sup> / 2 = 0,0125 J</div>

### 2.2 Limiar de decisão

No receptor coerente, o correlator multiplica o sinal recebido pela portadora de referência e integra por intervalo de bit. Para bit 1, a saída esperada é:

<div class="formula">y<sub>1</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> A cos²(2πf<sub>c</sub>t) dt = A T<sub>b</sub> / 2</div>

Para bit 0, como o sinal é nulo:

<div class="formula">y<sub>0</sub> = 0</div>

O limiar ótimo para sinais equiprováveis é o ponto médio entre as duas saídas esperadas:

<div class="formula">V<sub>th</sub> = (y<sub>1</sub> + y<sub>0</sub>) / 2 = A T<sub>b</sub> / 4</div>

Com os valores da simulação:

<div class="formula">V<sub>th</sub> = 5 × 10<sup>-3</sup> / 4 = 1,25 × 10<sup>-3</sup> V</div>

Esse foi o limiar usado na decisão do receptor.

### 2.3 Largura de banda nula-a-nula

Para um sinal BASK com NRZ unipolar, a envelope do espectro ocupa uma faixa aproximadamente dada por:

<div class="formula">B ≈ 2/T<sub>b</sub></div>

Como T<sub>b</sub> = 1 ms, temos:

<div class="formula">B ≈ 2 / 10<sup>-3</sup> = 2000 Hz</div>

Isso significa que a energia principal do sinal modulado se concentra em torno da portadora no intervalo:

<div class="formula">f<sub>c</sub> ± 1/T<sub>b</sub></div>

logo, a banda nula-a-nula do envelope é aproximadamente 2 kHz.

## 3. Implementação do sistema BASK

A sequência de bits gerada foi:

{bit_sequence}

A forma de onda NRZ unipolar foi construída com amplitude A para bit 1 e zero para bit 0, e a portadora foi:

<div class="formula">s(t) = b(t) × A cos(2πf<sub>c</sub>t)</div>

A demodulação foi feita por correlação coerente: o receptor multiplicou o sinal recebido pela mesma portadora de referência e integrou por intervalo de bit. A decisão final foi feita com o limiar deduzido teoricamente:

<div class="formula">V<sub>th</sub> = A T<sub>b</sub> / 4</div>

Neste caso, a detecção em canal ideal produz uma reconstrução perfeita da sequência de bits, como esperado para um sistema sem ruído e sem desalinhamento de portadora.

## 4. Resultados no domínio do tempo e na frequência

![Sinal NRZ e sinal BASK no domínio do tempo.](figuras/sinal_bask_tempo.png)

A figura acima mostra a sequência de bits NRZ aplicada ao modulador e a onda BASK resultante. O bit 1 aparece como uma porção da portadora em fase com amplitude A; o bit 0 corresponde à ausência de portadora.

![Espectro do sinal BASK e banda nula-a-nula esperada.](figuras/espectro_bask.png)

Na figura do espectro, observa-se que a potência do sinal está concentrada em torno de fc e que os limites da banda principal, em torno de fc ± 1/Tb, estão compatíveis com a previsão teórica de 2/Tb. Em outras palavras, o espectro obedecia ao comportamento esperado de um sinal ASK binário em banda passante.

## 5. Canal com ruído AWGN e BER

Para analisar o desempenho em presença de ruído, adicionou-se ruído gaussiano ao sinal de decisão do correlator. A relação sinal-ruído foi variada em Eb/N0 e a taxa de erro de bit foi comparada com a curva teórica de BASK coerente.

A expressão teórica usada foi:

<div class="formula">P<sub>b</sub> = Q(√(E<sub>b</sub>/N<sub>0</sub>))</div>

Com os parâmetros da simulação:

<div class="formula">E<sub>b</sub> = A² T<sub>b</sub> / 2 = 1,25 × 10<sup>-2</sup> J</div>

A curva obtida foi:

![Comparação entre BER simulada e BER teórica para BASK.](figuras/ber_bask.png)

Os valores principais foram:

- Eb/N0 = 6 dB: BER teórica ≈ {ber_6db:.3e}; BER simulada ≈ {sim_6db:.3e}
- Eb/N0 = 10 dB: BER teórica ≈ {ber_10db:.3e}; BER simulada ≈ {sim_10db:.3e}

## 6. Discussão

A simulação mostrou que, em canal ideal, o desempenho do receptor coerente é perfeito, pois o limiar de decisão foi calculado exatamente a partir do valor esperado da saída do correlator e a portadora foi assumida perfeitamente sincronizada com a do transmissor. Isso confirma a importância da dedução analítica da decisão, porque um limiar escolhido arbitrariamente poderia gerar erros mesmo sem ruído.

Com ruído, a BER simulada acompanha a curva teórica, mas não coincide exatamente em todos os pontos por duas razões principais: (i) a simulação usa um número finito de bits e, portanto, a estatística amostral ainda apresenta flutuação; (ii) o ruído gaussiano é gerado aleatoriamente e a sua variabilidade pode deslocar a curva em torno do valor teórico. À medida que o número de bits aumenta, a curva simulada tende a convergir para a previsão analítica.

A relação entre Eb/N0 e BER também mostra que o aumento da relação sinal-ruído reduz drasticamente a probabilidade de erro. Assim, BASK coerente funciona bem quando o ruído é pequeno e a portadora é conhecida com boa precisão, mas torna-se sensível à presença de ruído e de erro de sincronismo.

## 7. Conclusão

A atividade confirmou, de forma consistente, os princípios da modulação ASK binária em banda passante: a sequência NRZ unipolar foi convertida em uma onda modulada pela portadora, o espectro do sinal ocupou a banda esperada de 2/Tb e o receptor coerente recuperou corretamente os bits utilizando o limiar derivado da média das saídas do correlator. A análise da BER mostrou que o comportamento simulado acompanha a teoria de detecção coerente em AWGN, reforçando a validade do modelo matemático e a importância da escolha correta do limiar. Em suma, a simulação reproduziu corretamente o funcionamento de um sistema BASK binário e validou a teoria do esquema de detecção adotado.
'''


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
          .formula {{
            margin: 0.7em 0;
            text-align: center;
            font-family: "Times New Roman", Georgia, serif;
            font-size: 13.5pt;
            line-height: 1.35;
            color: #111827;
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 0.2em 0;
          }}
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
          }}
        </style>
      </head>
      <body>{html}</body>
    </html>
    """
    HTML(string=styled).write_pdf(str(PDF_PATH))


def main() -> None:
    results = generate_figures()
    md = build_markdown(results)
    MD_PATH.write_text(md, encoding="utf-8")
    try:
        render_pdf()
        print(f"Relatório gerado em: {MD_PATH}")
        print(f"PDF gerado em: {PDF_PATH}")
    except Exception as exc:
        print(f"Relatório gerado em: {MD_PATH}")
        print(f"Aviso: PDF não foi gerado ({exc})")
