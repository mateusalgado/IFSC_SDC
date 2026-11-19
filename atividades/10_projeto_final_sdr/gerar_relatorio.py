"""Gera os PDFs do relatório do projeto final com a renderização comum do repositório."""
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from padronizar_relatorios import render
    for fonte in sorted(Path(__file__).parent.glob("relatorio_*_*.md")):
        print(render(fonte))
