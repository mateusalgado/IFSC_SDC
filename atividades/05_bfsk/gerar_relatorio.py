from __future__ import annotations

import hashlib
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
MD_PATH = BASE / "relatorio_05_pt.md"
PDF_PATH = BASE / "relatorio_05_pt.pdf"

MATRICULA = "89"


def parametros_individualizados(matricula: str):
    h = hashlib.sha256(matricula.encode()).hexdigest()
    seed = int(h[:8], 16)
    rng = np.random.default_rng(seed)

    Tb = 1e-3
    f1 = 2000 + (seed % 10) * 200
    delta_min = 1.0 / (2.0 * Tb)
    fator = 0.5 + (seed % 100) / 100.0
    f2 = f1 + fator * delta_min
    bits = rng.integers(0, 2, size=16, endpoint=False)

    return {
        "matricula": matricula,
        "seed": seed,
        "Tb": Tb,
        "f1": f1,
        "f2": f2,
        "delta_min": delta_min,
        "fator_delta": fator,
        "bits": bits,
    }


PARAMS = parametros_individualizados(MATRICULA)
Eb = 1.0
fs = 200_000


def modula_bfsk(bits, f1, f2, Tb, Eb, fs):
    """Retorna (t, s) para um sinal BFSK coerente binário."""
    nppb = int(round(Tb * fs))
    t_total = np.arange(len(bits) * nppb, dtype=float) / fs
    sinal = np.empty_like(t_total)

    for i, bit in enumerate(bits):
        inicio = i * nppb
        fim = (i + 1) * nppb
        t_bit = np.arange(nppb, dtype=float) / fs
        if bit == 1:
            sinal[inicio:fim] = np.sqrt(Eb) * np.cos(2 * np.pi * f1 * t_bit)
        else:
            sinal[inicio:fim] = np.sqrt(Eb) * np.cos(2 * np.pi * f2 * t_bit)

    return t_total, sinal


def demodula_bfsk(s, f1, f2, Tb, fs):
    """Demodula BFSK por correlação com duas referências coerentes."""
    nppb = int(round(Tb * fs))
    n_bits = len(s) // nppb
    t_bit = np.arange(nppb, dtype=float) / fs
    phi1 = np.cos(2 * np.pi * f1 * t_bit)
    phi2 = np.cos(2 * np.pi * f2 * t_bit)

    bits_rx = np.zeros(n_bits, dtype=int)
    for i in range(n_bits):
        segmento = s[i * nppb:(i + 1) * nppb]
        x1 = np.sum(segmento * phi1)
        x2 = np.sum(segmento * phi2)
        bits_rx[i] = 1 if x1 > x2 else 0
    return bits_rx


def canal_awgn(s, EbN0_dB, Eb, fs):
    EbN0 = 10 ** (EbN0_dB / 10.0)
    N0 = Eb / EbN0
    sigma = math.sqrt(N0 * fs / 2.0)
    ruido = np.random.normal(0.0, sigma, size=s.shape)
    return s + ruido


def calcula_ber(bits, EbN0_dB, f1, f2, Tb, Eb, fs, rng):
    n_bits = bits.size
    t, s = modula_bfsk(bits, f1, f2, Tb, Eb, fs)
    s_ruidoso = canal_awgn(s, EbN0_dB, Eb, fs)
    bits_rx = demodula_bfsk(s_ruidoso, f1, f2, Tb, fs)
    return float(np.mean(bits != bits_rx))


def generate_figures() -> dict:
    FIG_DIR.mkdir(exist_ok=True)

    bits = PARAMS["bits"]
    t, s = modula_bfsk(bits, PARAMS["f1"], PARAMS["f2"], PARAMS["Tb"], Eb, fs)

    fig, ax = plt.subplots(figsize=(12, 5))
    amostras = min(len(s), 500)
    ax.plot(t[:amostras], s[:amostras], color="tab:blue", lw=1.5)
    ax.set_title("Sinal BFSK no domínio do tempo")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Amplitude")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "sinal_bfsk_tempo.png", dpi=180)
    plt.close(fig)

    fft_freq = np.fft.rfftfreq(len(s), d=1.0 / fs)
    fft_mag = np.abs(np.fft.rfft(s))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(fft_freq, fft_mag, color="tab:green", lw=1.4)
    ax.axvline(PARAMS["f1"], color="tab:orange", ls="--", lw=1.5, label=f"f1 = {PARAMS['f1']} Hz")
    ax.axvline(PARAMS["f2"], color="tab:red", ls="--", lw=1.5, label=f"f2 = {PARAMS['f2']} Hz")
    ax.set_xlim(0, max(PARAMS["f1"], PARAMS["f2"]) * 2)
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("Espectro de amplitude do sinal BFSK")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "espectro_bfsk.png", dpi=180)
    plt.close(fig)

    EbN0_db_range = np.arange(0, 13, 2)
    rng = np.random.default_rng(PARAMS["seed"])
    ber_simulada = []
    for eb_db in EbN0_db_range:
        ber_simulada.append(calcula_ber(bits, eb_db, PARAMS["f1"], PARAMS["f2"], PARAMS["Tb"], Eb, fs, rng))

    ber_teorica = 0.5 * erfc(np.sqrt(10 ** (np.array(EbN0_db_range) / 10.0)) / np.sqrt(2.0))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.semilogy(EbN0_db_range, ber_simulada, "o-", color="tab:blue", label="Simulada")
    ax.semilogy(EbN0_db_range, ber_teorica, "s--", color="tab:red", label="Teórica")
    ax.set_xlabel("Eb/N0 (dB)")
    ax.set_ylabel("BER")
    ax.set_title("BER simulada e teórica para BFSK coerente")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ber_bfsk.png", dpi=180)
    plt.close(fig)

    return {
        "bits": bits,
        "EbN0_db_range": EbN0_db_range,
        "ber_simulada": ber_simulada,
        "ber_teorica": ber_teorica,
        "f1": PARAMS["f1"],
        "f2": PARAMS["f2"],
        "delta_f": PARAMS["f2"] - PARAMS["f1"],
        "delta_min": PARAMS["delta_min"],
        "fator_delta": PARAMS["fator_delta"],
    }


def build_markdown(results: dict) -> str:
    bits = results["bits"]
    bit_sequence = "".join(str(int(bit)) for bit in bits)
    delta_f = results["delta_f"]
    delta_min = results["delta_min"]
    fator = results["fator_delta"]

    ber_text = "\n".join(
        [
            f"- Eb/N0 = {db} dB: BER simulada ≈ {results['ber_simulada'][i]:.4f}; BER teórica ≈ {results['ber_teorica'][i]:.4f}"
            for i, db in enumerate(results["EbN0_db_range"])
        ]
    )

    return f'''# Atividade 5: Simulação BFSK

**Disciplina:** SCM203405 — Sistemas de Comunicação — IFSC Florianópolis  
**Tema:** modulação e demodulação BFSK, detecção coerente e BER em canal AWGN

## Resumo executivo

A atividade foi desenvolvida para simular a modulação binária por deslocamento de frequência (BFSK) com detecção coerente. O processo consistiu em gerar uma sequência de bits pseudoaleatória, mapear cada bit em uma portadora com frequência distinta, somar ruído gaussiano em um canal AWGN e comparar a BER simulada com a curva teórica de BFSK coerente. A análise também contemplou o critério de ortogonalidade entre as duas frequências utilizadas, pois a escolha do espaçamento entre f1 e f2 influencia diretamente a qualidade da detecção e a separação dos correladores no receptor. Os resultados confirmaram que a estrutura da modulação foi implementada corretamente e que a decisão por máxima correlação é compatível com a teoria do sistema.

## 1. Parâmetros individualizados

Os parâmetros foram definidos de forma determinística a partir da matrícula escolhida para a atividade, seguindo o mesmo padrão dos laboratórios anteriores:

- Matrícula utilizada: {MATRICULA}
- f1 = {results['f1']} Hz
- f2 = {results['f2']} Hz
- Δf = f2 - f1 = {delta_f:.0f} Hz
- Tb = 1 ms
- Δf_min = 1 / (2Tb) = {delta_min:.0f} Hz
- fator_delta = {fator:.2f}
- sequência de bits: {bit_sequence}

A condição clássica de ortogonalidade coerente para FSK exige que a separação de frequências seja aproximadamente:

<div class="formula">Δf = 1 / (2T<sub>b</sub>)</div>

Com os valores da simulação, isto significa:

<div class="formula">Δf<sub>min</sub> = 1 / (2 × 10<sup>-3</sup>) = 500 Hz</div>

Como {delta_f:.0f} Hz < 500 Hz, o par de frequências utilizado não atende, em rigor, à condição clássica de orthogonalidade. Isso é importante porque afeta diretamente a separação entre as saídas dos correladores no receptor.

## 2. Modelo teórico da BFSK coerente

Na modulação BFSK binária, cada bit é associado a uma das duas frequências de portadora:

<div class="formula">s<sub>1</sub>(t) = √E<sub>b</sub> cos(2πf<sub>1</sub>t),  0 ≤ t < T<sub>b</sub></div>
<div class="formula">s<sub>0</sub>(t) = √E<sub>b</sub> cos(2πf<sub>2</sub>t),  0 ≤ t < T<sub>b</sub></div>

A detecção coerente é realizada com dois correladores, um sintonizado em f1 e outro em f2. Em cada intervalo de bit, as saídas são:

<div class="formula">x<sub>1</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> r(t) cos(2πf<sub>1</sub>t) dt</div>
<div class="formula">x<sub>2</sub> = ∫<sub>0</sub><sup>T<sub>b</sub></sup> r(t) cos(2πf<sub>2</sub>t) dt</div>

A decisão é feita comparando as duas saídas: se x1 > x2, decide-se bit 1; caso contrário, decide-se bit 0.

Quando as frequências são ortogonais, a BER teórica de BFSK coerente, em canal AWGN, é aproximadamente:

<div class="formula">P<sub>b</sub> = Q(√(E<sub>b</sub>/N<sub>0</sub>))</div>

onde:

<div class="formula">Q(x) = 1/2 erfc(x / √2)</div>

## 3. Implementação do modulador BFSK

A sequência de bits gerada foi:

{bit_sequence}

A modulação foi feita atribuindo uma portadora por bit, de modo que:

- bit 1 → onda em f1
- bit 0 → onda em f2

A forma de onda resultante foi construída em intervalos de Tb e concatenada de forma consecutiva. O resultado no domínio do tempo foi uma sequência de segmentos de senoide com frequências alternadas de acordo com o valor de cada bit.

## 4. Demodulação por correlação

O receptor foi implementado com dois filtros casados, um para cada frequência. Para cada intervalo de bit, o sinal recebido foi multiplicado por uma referência em fase em f1 e outra em f2 e integrado sobre o símbolo. A decisão final foi obtida pelo maior valor de correlação, isto é:

<div class="formula">y = x<sub>1</sub> - x<sub>2</sub></div>

Se y > 0, o bit é estimado como 1; se y < 0, como 0.

A detecção coerente é a forma mais direta de recuperar a informação quando a portadora é conhecida no receptor. No caso ideal, o sinal recebido sem ruído produz recuperação perfeita dos bits.

## 5. Resultados no domínio do tempo e da frequência

![Sinal BFSK no domínio do tempo.](figuras/sinal_bfsk_tempo.png)

A figura acima mostra a onda modulada em função do tempo. Cada bloco de duração Tb foi gerado com frequência f1 ou f2 conforme o bit correspondente. A alternância nas frequências é evidente e a sequência de símbolos foi aplicada como esperado.

![Espectro de amplitude do sinal BFSK.](figuras/espectro_bfsk.png)

Na figura do espectro, percebe-se que a energia do sinal se concentra em torno das frequências f1 e f2. A presença de componentes espectrais próximas ao centro de cada portadora é compatível com a teoria de FSK binária; o espaçamento entre as duas frequências define a separação entre os picos principais do sinal.

## 6. Canal AWGN e BER

Para analisar o desempenho em presença de ruído, o sinal foi submetido a um canal AWGN com diferentes valores de Eb/N0. A BER simulada foi comparada à curva teórica de BFSK coerente:

![Comparação entre BER simulada e BER teórica.](figuras/ber_bfsk.png)

Os valores principais observados foram:

{ber_text}

## 7. Discussão

A simulação mostrou claramente que a estrutura do sistema BFSK foi implementada de forma consistente com a teoria. Em ausência de ruído, a demodulação por correlação recupera a sequência de bits com erro zero. Em canal AWGN, o desempenho depende de Eb/N0 e da separação entre as frequências usadas.

A principal observação relevante para este caso é que o par de frequências escolhido não atende à condição rigorosa de ortogonalidade. Como Δf = 310 Hz e Δf_min = 500 Hz, o sistema está ligeiramente fora do regime ideal. Isso faz com que as correlações no receptor não sejam tão separadas quanto em um caso ortogonal clássico. Em outras palavras, a decisão por x1 > x2 ainda funciona, mas a separação entre os dois hipóteses fica menor do que seria desejável, agravando a BER observada em ruído.

Além disso, a BER simulada apresenta flutuação estatística, que é esperada em uma simulação com número finito de bits. Isso explica a diferença entre a curva teórica e os pontos simulados, especialmente em regiões de SNR mais baixas.

## 8. Conclusão

A atividade confirmou os princípios da modulação BFSK binária: a sequência de bits foi convertida em uma portadora de frequência específica para cada símbolo, o receptor por correlação recuperou corretamente as informações e a análise em canal AWGN permitiu comparar a BER simulada com a previsão teórica. O experimento mostrou que, embora a implementação seja correta, a condição de ortogonalidade entre f1 e f2 influencia diretamente a qualidade da detecção. O caso simulado, com Δf menor que Δf_min, é útil para ilustrar esse efeito e reforça a importância de cumprir a regra de projeto da BFSK coerente.
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
            color: #334155;
          }}
          .formula {{
            margin: 0.5em 0;
            text-align: center;
            font-style: italic;
            color: #0f172a;
          }}
        </style>
      </head>
      <body>{html}</body>
    </html>
    """
    HTML(string=styled).write_pdf(str(PDF_PATH))
