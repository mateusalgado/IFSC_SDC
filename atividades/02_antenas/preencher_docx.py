"""Preenche a atividade Word preservando o documento original."""

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK
from docx.text.paragraph import Paragraph
from docx.shared import Inches, Pt


ROOT = Path(__file__).parent
SOURCE = ROOT.parents[1] / "materiais/roteiros/atividade_02_antenas.docx"
TARGET = ROOT / "atividade_02_antenas_preenchida.docx"
RESULTS = ROOT / "figuras"


def paragraph_after(paragraph, text="", style=None):
    new_p = deepcopy(paragraph._p)
    for child in list(new_p):
        new_p.remove(child)
    paragraph._p.addnext(new_p)
    inserted = Paragraph(new_p, paragraph._parent)
    if style:
        inserted.style = style
    if text:
        inserted.add_run(text)
    return inserted


def find_paragraph(document, prefix):
    return next(p for p in document.paragraphs if p.text.strip().startswith(prefix))


def add_answer(document, anchor, text, style="normal"):
    return paragraph_after(find_paragraph(document, anchor), text, style)


def main():
    document = Document(SOURCE)

    # Parametros individualizados, junto da secao correspondente.
    add_answer(document, "Parte 1 (dipolo):", "Para N = 89: f = 2400 + (89 mod 10)*50 = 2850 MHz.")
    add_answer(document, "Parte 2 (microstrip):", "Para N = 89: epsilon_r = 2,2 + (89 mod 5)*0,3 = 3,4.")
    add_answer(document, "Comprimento de onda:", "Assim, lambda = c/f = 0,105263 m = 10,5263 cm.")

    lengths = [
        ("1 lambda", "10,5263 cm"),
        ("0,25 lambda", "2,6316 cm"),
        ("0,125 lambda", "1,3158 cm"),
        ("0,025 lambda", "0,2632 cm"),
        ("0,0125 lambda", "0,1316 cm"),
    ]
    add_answer(document, "0,0125 λ", "Comprimentos físicos: " + "; ".join(f"{name} = {value}" for name, value in lengths) + ".")

    # Insere os cinco graficos no local reservado pelo enunciado.
    anchor = find_paragraph(document, "Copie e cole aqui")
    image_names = ["1_0", "0_25", "0_125", "0_025", "0_0125"]
    for number, image_name in enumerate(image_names, 1):
        image_paragraph = paragraph_after(anchor)
        image_paragraph.alignment = 1
        image_paragraph.add_run().add_picture(str(RESULTS / f"dipolo_{image_name}lambda.png"), width=Inches(3.0))
        caption = paragraph_after(image_paragraph, f"Figura {number} - Diagrama de radiacao para o dipolo da lista.")
        caption.alignment = 1
        caption.paragraph_format.space_after = Pt(2)
        anchor = caption

    add_answer(
        document,
        "Verifique o que acontece",
        "Observando os graficos, para comprimentos muito pequenos o padrao se aproxima do dipolo elementar: um lobo largo, com maxima perpendicular ao fio e nulos na direcao do fio. Quando o comprimento aumenta para 0,25 lambda e 1 lambda, o padrao fica mais variavel, com lobos adicionais e maior diretividade. Portanto, o comprimento eletrico modifica diretamente a forma angular do campo.",
    )
    add_answer(
        document,
        "Verifique o que acontece",
        "Um erro de montagem de 10% afeta proporcionalmente mais o caso de 0,025 lambda. Nesse caso o dipolo ainda esta muito proximo do limite elementar, e a alteracao de comprimento muda mais a aproximacao de campo uniforme. Nos comprimentos maiores, a mesma variacao relativa desloca lobos que ja estao definidos, produzindo uma mudanca proporcional menor na forma normalizada.",
    )

    table = document.tables[0]
    values = [
        ("4,127754", "3,205047", "1,157040", "6,429428"),
        ("4,840221", "3,957824", "1,231993", "7,217926"),
        ("2,371708", "1,825785", "0,630747", "7,279504"),
        ("4,840221", "4,082351", "1,281638", "7,146197"),
    ]
    for row, row_values in zip(table.rows[1:], values):
        for cell, value in zip(row.cells[1:], row_values):
            cell.text = value

    add_answer(
        document,
        "Faça uma comparação das antenas",
        "Antenas 1 e 2: a permissividade muda de 3,4 para 2,2, a impedancia de 50 para 75 ohms, e as demais condicoes permanecem iguais. A permissividade menor aumenta W e L; o novo casamento desloca y0. A Antena 2 teve diretividade maior no modelo.",
    )
    add_answer(
        document,
        "Faça uma comparação das antenas",
        "Antenas 1 e 3: a frequencia sobe de 2,45 para 5 GHz, com er = 2,2, h = 0,3 cm e Zin = 50 ohms na Antena 3. A frequencia maior reduz as dimensoes: W passa de 4,127754 para 2,371708 cm e L de 3,205047 para 1,825785 cm.",
    )
    add_answer(
        document,
        "Faça uma comparação das antenas",
        "Antenas 2 e 4: frequencia, permissividade e impedancia sao iguais; muda apenas h, de 0,3 para 0,1 cm. W permanece igual, mas L passa de 3,957824 para 4,082351 cm, y0 aumenta e a diretividade diminui ligeiramente.",
    )

    add_answer(
        document,
        '"A Antena 4 é menor',
        "Erros: a impedancia de entrada nao reduz a permissividade efetiva; ela determina o ponto de alimentacao depois do dimensionamento. Alem disso, a Antena 4 nao e menor em todas as dimensoes: W4 = W2, mas L4 > L2. A espessura tambem nao afeta apenas o conector: ela entra no calculo de permissividade efetiva e extensao de borda, alterando L e outros resultados. Neste modelo W nao muda diretamente com h, por isso ficou igual. A explicacao correta e que a reducao de h altera esses parametros e produziu L4 maior, y0 maior e diretividade ligeiramente menor.",
    )

    add_answer(
        document,
        "Log de uso de IA:",
        "Prompts usados: interpretar o enunciado da Atividade 2; calcular os resultados para N = 89; executar os scripts Python e gerar os diagramas; inserir os resultados no documento. Validei os numeros executando o modelo Python fornecido e ajustei a discussao aos valores obtidos, especialmente a comparacao entre as Antenas 2 e 4.",
    )

    document.save(TARGET)
    print(TARGET)


if __name__ == "__main__":
    main()