"""Renderiza os relatórios existentes em português e inglês no padrão único."""
from pathlib import Path
import re
import html
from xml.sax.saxutils import escape

from matplotlib import get_data_path
from pylatexenc.latex2text import LatexNodes2Text
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ROOT=Path(__file__).resolve().parents[1]
GREEN=colors.HexColor('#285b42')
INK=colors.HexColor('#293b42')
LIGHT=colors.HexColor('#edf3ef')
FONTS=Path(get_data_path())/'fonts/ttf'
for name,file in [('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),
                  ('Italic','DejaVuSans-Oblique.ttf'),('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONTS/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')
STYLES={
 'body':ParagraphStyle('Body',fontName='Body',fontSize=10,leading=15.2,textColor=INK,spaceAfter=8),
 'title':ParagraphStyle('Title',fontName='Bold',fontSize=23,leading=29,textColor=GREEN,spaceAfter=14),
 'h2':ParagraphStyle('H2',fontName='Bold',fontSize=14,leading=19,textColor=GREEN,spaceBefore=14,spaceAfter=7,keepWithNext=True),
 'h3':ParagraphStyle('H3',fontName='Bold',fontSize=11,leading=16,textColor=GREEN,spaceBefore=8,spaceAfter=5,keepWithNext=True),
 'caption':ParagraphStyle('Caption',fontName='Body',fontSize=8.2,leading=11.5,textColor=GREEN,spaceAfter=12),
 'formula':ParagraphStyle('Formula',fontName='Body',fontSize=10,leading=16,backColor=LIGHT,borderPadding=8,spaceBefore=5,spaceAfter=12),
 'cell':ParagraphStyle('Cell',fontName='Body',fontSize=8.2,leading=11.5,textColor=INK),
 'headcell':ParagraphStyle('HeaderCell',fontName='Bold',fontSize=8.2,leading=11.5,textColor=colors.white)
}

def inline(s):
    s=html.unescape(s)
    s=re.sub(r'\$(.*?)\$',lambda m:LatexNodes2Text().latex_to_text(m[1]),s)
    s=re.sub(r'</?(?:div|sub|sup)[^>]*>','',s)
    s=escape(s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1',s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'\x60([^\x60]+)\x60',r'<font name="Mono">\1</font>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<i>\1</i>',s)
    return s.replace('\n',' ')

def normalized_source(s,number,lang):
    if number==1 and lang=='pt':
        equations=[
          'PLmax = Ptx + Gt + Gr − S\n1 Mbit/s → 120,50 dB\n54 Mbit/s → 93,00 dB',
          'FSPL = 32,44 + 20 log₁₀(fMHz) + 20 log₁₀(dkm)\ndkm = 10^[(PLmax − 32,44 − 20 log₁₀(fMHz))/20]',
          '1 Mbit/s → d ≈ 10,38 km\n54 Mbit/s → d ≈ 0,438 km',
          'PL(d) = PL(d₀) + 10n log₁₀(d/d₀) + Xσ\nPL(d₀) ≈ 40,18 dB em d₀ = 1 m',
          'd = d₀ × 10^[(PLmax − PL(d₀))/(10n)]\nEscritório suave → 2.222 m\nEscritório severo → 476 m\nFábrica LOS → 10.379 m\nFábrica obstruída → 272 m',
          'PLprojeto = PLmax − M\nMargem ilustrativa M ≈ 1 a 2σ']
        values=iter(equations)
        s=re.sub(r'\$\$.*?\$\$',lambda m:'\n'+''.join('> '+line+'\n' for line in next(values).splitlines())+'\n',s,flags=re.S)
    return s

def render(md):
    match=re.search(r'relatorio_(\d+)_(pt|en)',md.name)
    number,lang=int(match[1]),match[2]
    text=normalized_source(md.read_text(),number,lang)
    lines=text.splitlines()
    title=next(line[2:] for line in lines if line.startswith('# '))
    items=[Paragraph(inline(title),STYLES['title']),
           Paragraph('Mateus Salgado Barboza Costa',STYLES['body']),
           Paragraph('SCM203405 · '+('Sistemas de Comunicação' if lang=='pt' else 'Communication Systems')+
                     ' · IFSC Florianópolis',STYLES['caption'])]
    width=A4[0]-96
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line or line.startswith('# '):i+=1;continue
        if line.startswith('## '):
            items.append(Paragraph(inline(line[3:]),STYLES['h2']));i+=1;continue
        if line.startswith('### '):
            items.append(Paragraph(inline(line[4:]),STYLES['h3']));i+=1;continue
        if line.startswith('!['):
            label,path=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line).groups()
            file=md.parent/path
            if lang=='en' and (file.parent/'en'/file.name).exists():
                file=file.parent/'en'/file.name
            if not file.exists():raise FileNotFoundError(file)
            im=Image(str(file))
            max_height = 210 if number == 9 and lang == "en" else 240
            scale=min(width/im.imageWidth,max_height/im.imageHeight)
            im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale
            items.append(KeepTogether([Spacer(1,6),im,Spacer(1,5),Paragraph(inline(label),STYLES['caption'])]))
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',v.replace(' ','')) for v in row):rows.append(row)
                i+=1
            count=len(rows[0])
            if not all(len(row)==count for row in rows):raise ValueError(f'Tabela irregular em {md}')
            weights=[max(8,min(40,max(len(re.sub(r'[*$]','',row[j])) for row in rows))) for j in range(count)]
            widths=[width*v/sum(weights) for v in weights]
            formatted=[[Paragraph(inline(v),STYLES['headcell' if j==0 else 'cell']) for v in row] for j,row in enumerate(rows)]
            tab=Table(formatted,colWidths=widths,repeatRows=1,hAlign='LEFT')
            tab.setStyle(TableStyle([
               ('BACKGROUND',(0,0),(-1,0),GREEN),
               ('ROWBACKGROUNDS',(0,1),(-1,-1),[LIGHT,colors.white]),
               ('VALIGN',(0,0),(-1,-1),'TOP'),
               ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
               ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]))
            items.append(KeepTogether([Spacer(1,4),tab,Spacer(1,10)]))
            continue
        if line.startswith('>'):
            chunk=[]
            while i<len(lines) and lines[i].strip().startswith('>'):
                chunk.append(inline(lines[i].strip()[1:].strip()));i+=1
            items.append(Paragraph('<br/>'.join(chunk),STYLES['formula']));continue
        if line.startswith('- ') or re.match(r'^\d+\. ',line):
            items.append(Paragraph('• '+inline(line[2:] if line.startswith('- ') else line),STYLES['body']))
            i+=1;continue
        para=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|!\[|\||>|- |\d+\. )',lines[i].strip()):
            para.append(lines[i].strip());i+=1
        items.append(Paragraph(inline(' '.join(para)),STYLES['body']))
    def frame(canvas,doc):
        canvas.setFont('Bold',8);canvas.setFillColor(GREEN)
        canvas.drawString(48,A4[1]-29,'SCM203405  /  '+('SISTEMAS DE COMUNICAÇÃO' if lang=='pt' else 'COMMUNICATION SYSTEMS'))
        rotulo=(('PROJETO FINAL' if lang=='pt' else 'FINAL PROJECT') if number==10 else
                ('ATIVIDADE' if lang=='pt' else 'ACTIVITY')+f'  {number:02} / 09')
        canvas.drawRightString(A4[0]-48,A4[1]-29,rotulo)
        canvas.setStrokeColor(colors.HexColor('#bbcfc3'))
        canvas.line(48,A4[1]-38,A4[0]-48,A4[1]-38)
        canvas.setFont('Body',8);canvas.drawString(48,27,'Mateus Salgado Barboza Costa')
        canvas.drawRightString(A4[0]-48,27,f'{lang.upper()}  ·  {doc.page:02}')
    pdf=md.with_suffix('.pdf')
    SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=58,bottomMargin=46,
                      title=title,author='Mateus Salgado Barboza Costa').build(items,onFirstPage=frame,onLaterPages=frame)
    return pdf

if __name__=='__main__':
    for file in sorted(ROOT.glob('atividades/*/relatorio_*_*.md')):
        print(render(file))
