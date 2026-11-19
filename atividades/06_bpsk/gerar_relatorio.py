from __future__ import annotations

import hashlib
import math
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

try:
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None

try:
    from reportlab.lib import colors
except Exception:
    colors = None

BASE = Path(__file__).resolve().parent
FIG_DIR = BASE / "figuras"
MD_PATH = BASE / "relatorio_06_pt.md"
PDF_PATH = BASE / "relatorio_06_pt.pdf"

MATRICULA = "89"


def parametros_individualizados(matricula: str):
    h = hashlib.sha256(matricula.encode()).hexdigest()
    seed = int(h[:8], 16)
    rng = np.random.default_rng(seed)

    Tb = 1e-3
    k = 2 + seed % 5
    fracao = [0.0, 0.25, 0.5][(seed // 5) % 3]
    fc = (k + fracao) / Tb
    bits = rng.integers(0, 2, size=10)

    return {
        "matricula": matricula,
        "seed": seed,
        "Tb": Tb,
        "fc": fc,
        "ciclos_por_bit": fc * Tb,
        "bits": bits,
    }


PARAMS = parametros_individualizados(MATRICULA)
Eb = 1.0
fs = 200_000


def modula_bpsk(bits, fc, Tb, Eb, fs):
    """Retorna (t, nrz, s) para sinal BPSK coerente."""
    nppb = int(round(Tb * fs))
    t = np.arange(len(bits) * nppb, dtype=float) / fs
    nrz = np.empty_like(t)
    s = np.empty_like(t)
    phi1 = np.sqrt(2.0 / Tb) * np.cos(2.0 * np.pi * fc * t)

    for i, bit in enumerate(bits):
        inicio = i * nppb
        fim = (i + 1) * nppb
        nivel = np.sqrt(Eb) if bit == 1 else -np.sqrt(Eb)
        nrz[inicio:fim] = nivel
        s[inicio:fim] = nivel * phi1[inicio:fim]

    return t, nrz, s


def demodula_bpsk(t, s, fc, Tb, fs):
    nppb = int(round(Tb * fs))
    n_bits = len(s) // nppb
    phi1 = np.sqrt(2.0 / Tb) * np.cos(2.0 * np.pi * fc * t)

    x1 = np.zeros(n_bits)
    bits_rx = np.zeros(n_bits, dtype=int)
    for i in range(n_bits):
        inicio = i * nppb
        fim = (i + 1) * nppb
        segmento = s[inicio:fim]
        referencia = phi1[inicio:fim]
        x1[i] = np.sum(segmento * referencia) / fs
        bits_rx[i] = 1 if x1[i] > 0 else 0

    return bits_rx, x1


def canal_awgn(s, EbN0_dB, Eb, Tb, fs):
    EbN0 = 10 ** (EbN0_dB / 10.0)
    N0 = Eb / EbN0
    var_ruido = N0 * fs / 2.0
    ruido = np.random.normal(0.0, np.sqrt(var_ruido), size=s.shape)
    return s + ruido


def calcula_ber(n_bits, EbN0_dB, fc, Tb, Eb, fs, rng):
    bits = rng.integers(0, 2, size=n_bits)
    t, nrz, s = modula_bpsk(bits, fc, Tb, Eb, fs)
    s_ruidoso = canal_awgn(s, EbN0_dB, Eb, Tb, fs)
    bits_rx, x1 = demodula_bpsk(t, s_ruidoso, fc, Tb, fs)
    return np.mean(bits != bits_rx)


def largura_banda_99(s, fs, fc):
    spec = np.abs(np.fft.rfft(s)) ** 2
    freq = np.fft.rfftfreq(len(s), d=1.0 / fs)
    energia_total = spec.sum()
    energia_acumulada = np.cumsum(spec)
    indice_99 = np.where(energia_acumulada >= 0.99 * energia_total)[0]
    if len(indice_99) == 0:
        return float(freq[-1] - freq[0])

    idx = indice_99[0]
    posicoes = np.abs(freq - fc) <= (freq[idx] - freq[0])
    if np.any(posicoes):
        banda = 2.0 * np.max(freq[posicoes])
        return float(banda)

    return float(2 * freq[idx])


def gerar_figuras() -> dict:
    FIG_DIR.mkdir(exist_ok=True)

    bits = PARAMS["bits"]
    t, nrz, s = modula_bpsk(bits, PARAMS["fc"], PARAMS["Tb"], Eb, fs)

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    amostras = min(len(nrz), 1000)
    axes[0].plot(t[:amostras], nrz[:amostras], color="tab:blue", lw=1.5)
    axes[0].set_title("NRZ polar (saída do conversor)")
    axes[0].set_ylabel("Amplitude")
    axes[0].grid(alpha=0.3)

    axes[1].plot(t[:amostras], s[:amostras], color="tab:orange", lw=1.5)
    axes[1].set_title("Sinal BPSK no domínio do tempo")
    axes[1].set_xlabel("Tempo (s)")
    axes[1].set_ylabel("Amplitude")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "sinal_bpsk_tempo.png", dpi=180)
    plt.close(fig)

    fft_freq = np.fft.rfftfreq(len(s), d=1.0 / fs)
    fft_mag = np.abs(np.fft.rfft(s))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(fft_freq, fft_mag, color="tab:green", lw=1.5)
    ax.axvline(PARAMS["fc"], color="tab:red", ls="--", lw=1.5, label=f"f_c = {PARAMS['fc']:.3f} Hz")
    ax.set_xlim(0, max(PARAMS["fc"], 1000) * 2)
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("Espectro de amplitude do sinal BPSK")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "espectro_bpsk.png", dpi=180)
    plt.close(fig)

    EbN0_db_range = np.arange(0, 11, 1)
    rng = np.random.default_rng(PARAMS["seed"])
    ber_simulada = [calcula_ber(10_000, eb_db, PARAMS["fc"], PARAMS["Tb"], Eb, fs, rng) for eb_db in EbN0_db_range]
    ber_teorica = 0.5 * erfc(np.sqrt(10 ** (np.array(EbN0_db_range) / 10.0)))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.semilogy(EbN0_db_range, ber_simulada, "o-", color="tab:blue", label="Simulada")
    ax.semilogy(EbN0_db_range, ber_teorica, "s--", color="tab:red", label="Teórica")
    ax.set_xlabel("Eb/N0 (dB)")
    ax.set_ylabel("BER")
    ax.set_title("BER simulada e teórica para BPSK coerente")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ber_bpsk.png", dpi=180)
    plt.close(fig)

    bits_rx, x1 = demodula_bpsk(t, s, PARAMS["fc"], PARAMS["Tb"], fs)
    return {
        "bits": bits,
        "bits_rx": bits_rx,
        "x1": x1,
        "fc": PARAMS["fc"],
        "Tb": PARAMS["Tb"],
        "ciclos_por_bit": PARAMS["ciclos_por_bit"],
        "EbN0_db_range": EbN0_db_range,
        "ber_simulada": ber_simulada,
        "ber_teorica": ber_teorica,
        "largura_banda_99": largura_banda_99(s, fs, PARAMS["fc"]),
        "largura_teorica": 2.0 / PARAMS["Tb"],
    }


def build_markdown(results: dict) -> str:
    bits = results["bits"]
    bit_sequence = "".join(str(int(bit)) for bit in bits)
    x1_text = ", ".join(f"{valor:.4f}" for valor in results["x1"])
    ber_text = "\n".join(
        [
            f"- Eb/N0 = {db} dB: BER simulada ≈ {results['ber_simulada'][i]:.4f}; BER teórica ≈ {results['ber_teorica'][i]:.4f}"
            for i, db in enumerate(results["EbN0_db_range"])
        ]
    )

    return f'''<style>
.formula {{
  display: block;
  margin: 14px 0;
  padding: 10px 14px;
  background: #f6f8fa;
  border-left: 4px solid #2f6fbd;
  border-radius: 6px;
  color: #1f2937;
  font-family: "Georgia", "Times New Roman", serif;
  font-size: 1.02em;
  line-height: 1.5;
  font-style: italic;
}}
</style>

# Atividade 6: Simulação BPSK

**Disciplina:** SCM203405 — Sistemas de Comunicação — IFSC Florianópolis  
**Tema:** modulação e demodulação BPSK coerente, correlação e BER em canal AWGN

## Resumo executivo

A atividade foi desenvolvida para simular a modulação binária por fase (BPSK), com transmissão de símbolos na forma de fase invertida em relação à portadora. O processo consistiu em gerar uma sequência binária pseudoaleatória, mapear cada bit para um símbolo com amplitude ±√E_b, multiplicar pela portadora cossenoidal e, em seguida, adicionar ruído gaussiano branco em um canal AWGN. O receptor implementou a demodulação por correlação com a mesma referência de fase da portadora, permitindo a recuperação dos bits com base na polaridade da saída do correlator. A análise comparou a BER simulada com a curva teórica da BPSK coerente e confirmou o comportamento esperado do sistema em diferentes níveis de Eb/N0.

## 1. Parâmetros individualizados

Os parâmetros foram definidos de forma determinística a partir da matrícula escolhida para a atividade, seguindo o mesmo padrão dos laboratórios anteriores:

- Matrícula utilizada: {MATRICULA}
- f_c = {results['fc']:.3f} Hz
- T_b = {results['Tb']:.3e} s
- ciclos por bit = f_c T_b = {results['ciclos_por_bit']:.4f}
- sequência de bits: {bit_sequence}

A portadora foi escolhida com um número de ciclos por bit que pode ou não ser inteiro, e esse ponto é importante para a análise de sincronismo e de fase da referência. Em um sistema BPSK coerente ideal, a referência do receptor usa a mesma frequência e fase da portadora do transmissor, e a decisão final é baseada na polaridade de x1.

## 2. Modelo teórico da BPSK coerente

Na modulação BPSK, os dois símbolos são representados por fases opostas da portadora:

<div class="formula">s_1(t) = +√E_b φ_1(t),  0 ≤ t < T_b</div>
<div class="formula">s_0(t) = -√E_b φ_1(t),  0 ≤ t < T_b</div>

com

<div class="formula">φ_1(t) = √(2/T_b) cos(2πf_c t)</div>

A detecção coerente é realizada por correlação com a mesma função-base. Em cada intervalo de bit, a saída do correlator é:

<div class="formula">x_1 = ∫_0^{{T_b}} r(t) φ_1(t) dt</div>

Se x_1 > 0, decide-se bit 1; se x_1 < 0, decide-se bit 0. No caso ideal, os valores esperados de x_1 são ±√E_b, pois a energia da referência em um intervalo de bit é unitária.

## 3. Implementação do modulador BPSK

A sequência de bits gerada foi:

{bit_sequence}

A modulação BPSK foi realizada em duas etapas:

1. Conversão do bit para nível NRZ polar: bit 1 → +√E_b, bit 0 → -√E_b.
2. Multiplicação do nível NRZ pela portadora cossenoidal φ_1(t).

Assim, cada símbolo corresponde a uma fase de 0° ou 180° em relação à portadora, o que produz a inversão de fase característica da BPSK.

## 4. Demodulação por correlação

O receptor foi implementado com a mesma função-base φ_1(t), em fase com a portadora do transmissor. Para cada bit, a saída do correlator foi calculada como soma amostral sobre T_b:

<div class="formula">x_1 = (1/f_s) Σ s[n] φ_1[n]</div>

Os valores observados foram:

{x1_text}

A sequência demodulada coincidiu com a sequência original em canal ideal, o que confirma que a estrutura do receptor está correta e que a sincronização em fase foi preservada.

## 5. Resultados no domínio do tempo e da frequência

![Sinal BPSK no domínio do tempo.](figuras/sinal_bpsk_tempo.png)

A figura acima mostra a comparação entre o sinal NRZ polar e a versão BPSK modulada no tempo. As inversões de fase são visíveis nas transições entre bits, como esperado em uma modulação por mudança de fase.

![Espectro de amplitude do sinal BPSK.](figuras/espectro_bpsk.png)

No espectro, a energia do sinal é concentrada em torno de f_c e a ocupação espectral é compatível com o modelo teórico de BPSK. A largura de banda principal está centrada em f_c e tem largura aproximada 2/T_b para os lóbulos principais.

## 6. Canal AWGN e BER

Para avaliar o desempenho em presença de ruído, o sinal foi submetido a diferentes níveis de Eb/N0. A BER simulada foi comparada com a curva teórica da BPSK coerente, dada por:

<div class="formula">P_b = Q(√(2E_b/N_0)) = 1/2 erfc(√(E_b/N_0))</div>

![Comparação entre BER simulada e BER teórica.](figuras/ber_bpsk.png)

Os valores principais observados foram:

{ber_text}

A curva simulada acompanha a tendência teórica, com pequenas diferenças estatísticas esperadas em função do número finito de bits usados na simulação.

## 7. Ocupação espectral e análise do caso prático

A estimativa da largura de banda ocupada pelo sinal, em uma aproximação baseada na energia espectral, foi de aproximadamente {results['largura_banda_99']:.2f} Hz. O valor teórico de referência para a largura entre nulos do lóbulo principal é:

<div class="formula">B = 2/T_b</div>

Como T_b = {results['Tb']:.3e} s, então:

<div class="formula">B = 2 / {results['Tb']:.3e} = {results['largura_teorica']:.0f} Hz</div>

Esse comportamento é consistente com a teoria da BPSK: o sinal é efetivamente limitado a uma faixa em torno da portadora, com largura proporcional ao inverso da duração de símbolo.

## 8. Discussão

O comportamento observado confirma a teoria da BPSK coerente: a decisão por correlação responde corretamente à fase da portadora, e a BER cresce quando o ruído aumenta. O caso em que o número de ciclos por bit não é inteiro não prejudica a demodulação por correlação em canal ideal, porque o correlator usa a mesma função-base do transmissor e a energia da referência continua sendo a mesma em cada intervalo T_b. A principal limitação prática fica mais ligada à sincronização de fase, ao erro de frequência e aos efeitos não ideais do canal do que à ausência de integridade exata do número de ciclos por bit.

A montagem também mostra que, em um sistema real, o principal desafio está na manutenção da fase e da sincronização entre transmissor e receptor. Qualquer desvio de fase constante ou de frequência tende a reduzir a projeção do sinal recebido sobre a referência e, portanto, aumenta a BER.

## 9. Conclusão

A atividade confirmou os principios da modulação BPSK coerente: a sequência de bits foi mapeada em símbolos de fase oposta, a demodulação por correlação recuperou corretamente a informação em canal ideal e a comparação com a BER teórica validou a análise em AWGN. O experimento reforça a importância da sincronização em fase e da escolha da duração de bit na definição da ocupação espectral do sistema.
'''


def export_pdf_fallback(md: str):
    if canvas is None:
        return False

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image, PageBreak
    import re

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyled",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "H2Styled",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyStyled",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    list_style = ParagraphStyle(
        "ListStyled",
        parent=body_style,
        leftIndent=18,
        bulletIndent=0,
        spaceAfter=4,
    )
    formula_style = ParagraphStyle(
        "FormulaStyled",
        parent=body_style,
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        leftIndent=18,
        rightIndent=18,
        borderWidth=1,
        borderColor=colors.HexColor("#d8dee9") if colors is not None else None,
        backColor=colors.HexColor("#f6f8fa") if colors is not None else None,
        borderPadding=8,
        spaceBefore=8,
        spaceAfter=8,
    )

    story = []
    lines = md.splitlines()
    image_refs = []
    in_style_block = False

    for raw in lines:
        line = raw.strip()

        if line.startswith("<style>"):
            in_style_block = True
            continue
        if in_style_block:
            if line.startswith("</style>"):
                in_style_block = False
            continue

        if not line:
            story.append(Spacer(1, 6))
            continue

        if line.startswith("# "):
            story.append(Paragraph(line[2:], title_style))
            continue

        if line.startswith("## "):
            story.append(Paragraph(line[3:], h2_style))
            continue

        if line.startswith("**Disciplina:**") or line.startswith("**Tema:**"):
            story.append(Paragraph(line.replace("**", ""), body_style))
            continue

        if line.startswith("<div class=\"formula\">"):
            formula = line.replace('<div class="formula">', "").replace("</div>", "")
            story.append(Paragraph(formula, formula_style))
            continue

        if line.startswith("!["):
            match = re.search(r"!\[(.*?)\]\((.*?)\)", line)
            if match:
                caption = match.group(1)
                image_path = match.group(2)
                image_refs.append((caption, image_path))
                story.append(Paragraph(caption, body_style))
                img_file = BASE / image_path
                if img_file.exists():
                    story.append(Image(str(img_file), width=5.2 * inch, height=2.6 * inch))
                else:
                    story.append(Paragraph(f"Imagem ausente: {image_path}", body_style))
            continue

        if line.startswith("- "):
            story.append(Paragraph(line[2:], list_style))
            continue

        if line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. "):
            story.append(Paragraph(line, list_style))
            continue

        if line.startswith("|"):
            continue

        story.append(Paragraph(line.replace("**", ""), body_style))

    if image_refs:
        story.append(PageBreak())
        story.append(Paragraph("Figuras do relatório", h2_style))
        for caption, image_path in image_refs:
            img_file = BASE / image_path
            if img_file.exists():
                story.append(Paragraph(caption, body_style))
                story.append(Image(str(img_file), width=5.3 * inch, height=2.7 * inch))
                story.append(Spacer(1, 8))

    doc.build(story)
    return True


def main():
    results = gerar_figuras()
    md = build_markdown(results)
    MD_PATH.write_text(md, encoding="utf-8")

    pdf_ok = False
    if HTML is not None:
        html = markdown.markdown(md, extensions=["extra", "sane_lists", "tables"])
        HTML(string=f"<html><body>{html}</body></html>").write_pdf(str(PDF_PATH))
        pdf_ok = True
        print(f"PDF salvo em: {PDF_PATH}")
    else:
        pdf_ok = export_pdf_fallback(md)
        if pdf_ok:
            print(f"PDF salvo em: {PDF_PATH}")
        else:
            print("WeasyPrint não está disponível e não foi possível gerar PDF no ambiente atual.")

    print(f"Relatório salvo em: {MD_PATH}")
    print(f"Matrícula: {MATRICULA}")
    print(f"fc: {PARAMS['fc']:.6f} Hz")
    print(f"Tb: {PARAMS['Tb']:.6e} s")
    print(f"ciclos_por_bit: {PARAMS['ciclos_por_bit']:.6f}")
    print(f"bits: {PARAMS['bits']}")
