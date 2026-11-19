"""Gera o PDF a partir do relatório Markdown e recupera as figuras do notebook executado."""
from pathlib import Path

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from padronizar_relatorios import render
    for source in sorted(Path(__file__).parent.glob("relatorio_*_*.md")):
        print(render(source))
    raise SystemExit(0)

import base64
import json
import re
from xml.sax.saxutils import escape

from matplotlib import get_data_path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

BASE = Path(__file__).resolve().parent
NUMERO = 8
FIGURAS = {'constelacao_ideal_8psk.png': ('# ---------------- Look-up table', 0),
 'espectro_8psk.png': ('# Espectro de s(t)', 0),
 'decisao_8psk.png': ('# ---------------- Constelação recebida', 0),
 'constelacoes_awgn_8psk.png': ('LISTA_EbN0_dB', 0),
 'ber_8psk.png': ('def Q(x)', 0),
 'portadora_fracionaria_8psk.png': ('# Mesmos bits', 1)}


def exportar_figuras():
    notebook = next(BASE.glob(f"atividade_{NUMERO:02}_*.ipynb"))
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    pasta = BASE / "figuras"
    pasta.mkdir(exist_ok=True)
    for nome, (inicio, indice) in FIGURAS.items():
        cell = next(c for c in cells if "".join(c["source"]).startswith(inicio))
        imagens = [out["data"]["image/png"] for out in cell["outputs"]
                   if "image/png" in out.get("data", {})]
        (pasta / nome).write_bytes(base64.b64decode(imagens[indice]))


def gerar_pdf():
    fontes = Path(get_data_path()) / "fonts" / "ttf"
    for nome, arquivo in [("Deja", "DejaVuSans.ttf"), ("DejaB", "DejaVuSans-Bold.ttf")]:
        pdfmetrics.registerFont(TTFont(nome, str(fontes / arquivo)))
    verde = colors.HexColor("#285b42")
    cinza = colors.HexColor("#344348")
    corpo = ParagraphStyle("Corpo", fontName="Deja", fontSize=10, leading=15, textColor=cinza,
                           spaceAfter=8)
    titulo = ParagraphStyle("Título", parent=corpo, fontName="DejaB", fontSize=20, leading=26,
                            textColor=verde, spaceAfter=12)
    secao = ParagraphStyle("Seção", parent=titulo, fontSize=15, leading=20, spaceBefore=5, spaceAfter=8)
    legenda = ParagraphStyle("Legenda", parent=corpo, fontSize=8.5, leading=12, textColor=verde)
    tabela = ParagraphStyle("Célula", parent=corpo, fontSize=8.5, leading=12, spaceAfter=0)
    cabecalho = ParagraphStyle("Coluna", parent=tabela, fontName="DejaB", textColor=colors.white)
    largura = A4[0] - 100
    itens = []
    md = (BASE / f"relatorio_{NUMERO:02}_pt.md").read_text(encoding="utf-8")
    for bloco in md.strip().split("\n\n"):
        if bloco.startswith("# "):
            nome, *autoria = bloco.splitlines()
            itens.append(Paragraph(escape(nome[2:]), titulo))
            itens.append(Paragraph("<br/>".join(map(escape, autoria)), corpo))
        elif bloco.startswith("## "):
            cab, *texto = bloco.splitlines()
            itens.append(Paragraph(escape(cab[3:]), secao))
            if texto:
                itens.append(Paragraph(escape(" ".join(texto)), corpo))
        elif bloco.startswith("|"):
            linhas = [[v.strip() for v in linha.strip("|").split("|")]
                      for linha in bloco.splitlines() if not linha.startswith("|---")]
            colunas = len(linhas[0])
            pesos = {3: [0.51, 0.25, 0.24], 4: [0.28, 0.25, 0.21, 0.26],
                     6: [0.22, 0.14, 0.16, 0.18, 0.15, 0.15]}[colunas]
            linhas = [[Paragraph(escape(v), cabecalho if i == 0 else tabela) for v in linha]
                      for i, linha in enumerate(linhas)]
            tab = Table(linhas, colWidths=[largura*p for p in pesos], repeatRows=1)
            tab.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), verde),
                                     ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#eaf1ed"), colors.white]),
                                     ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 4),
                                     ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
            itens.extend([tab, Spacer(1,9)])
        elif bloco.startswith("!["):
            rotulo, caminho = re.fullmatch(r"!\[(.+)\]\((.+)\)", bloco).groups()
            img = Image(str(BASE / caminho))
            escala = min(largura / img.imageWidth, 236 / img.imageHeight)
            img.drawWidth, img.drawHeight = img.imageWidth*escala, img.imageHeight*escala
            itens.append(KeepTogether([img, Spacer(1,4), Paragraph(escape(rotulo), legenda)]))
        elif bloco == "<!-- página -->":
            itens.append(PageBreak())
        else:
            itens.append(Paragraph(escape(bloco), corpo))

    def moldura(canvas, doc):
        canvas.setFillColor(verde)
        canvas.setFont("DejaB", 8)
        canvas.drawString(44, A4[1]-32, f"IFSC  /  SISTEMAS DE COMUNICAÇÃO")
        canvas.setFont("Deja", 8)
        canvas.drawRightString(A4[0]-44, A4[1]-32, f"LABORATÓRIO  {NUMERO:02}")
        canvas.setStrokeColor(colors.HexColor("#b5c8bb"))
        canvas.line(44, A4[1]-41, A4[0]-44, A4[1]-41)
        canvas.drawString(44, 26, "Mateus Salgado Barboza Costa")
        canvas.drawRightString(A4[0]-44, 26, f"{doc.page:02}")

    arquivo = BASE / f"relatorio_{NUMERO:02}_pt.pdf"
    doc = SimpleDocTemplate(str(arquivo), pagesize=A4, leftMargin=44, rightMargin=44,
                            topMargin=54, bottomMargin=40, author="Mateus Salgado Barboza Costa",
                            title=md.splitlines()[0][2:])
    doc.build(itens, onFirstPage=moldura, onLaterPages=moldura)
