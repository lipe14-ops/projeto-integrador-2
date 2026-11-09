"""Monta o notebook Colab a partir dos módulos de work/.

O código dos métodos é lido dos arquivos .py (sem o bloco __main__ e sem
`from common import *`) para que notebook e scripts testados sejam o mesmo
código.
"""
from pathlib import Path
import re
import sys

import nbformat as nbf

WORK = Path(__file__).parent
SAIDA = WORK.parent / "outliers_climaticos.ipynb"
sys.path.insert(0, str(WORK))
from secoes import SECOES  # noqa: E402


def codigo_modulo(nome):
    texto = (WORK / nome).read_text()
    texto = re.split(r'\nif __name__ == "__main__":', texto)[0]
    texto = re.sub(r"^from common import \*.*\n", "", texto, flags=re.M)

    return texto.strip() + "\n"


def docstring_modulo(nome):
    """Docstring do módulo, usada como célula markdown de decisões."""
    m = re.match(r'^"""([\s\S]*?)"""', (WORK / nome).read_text())
    return m.group(1).strip() if m else ""


def montar():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.metadata["colab"] = {"provenance": [], "toc_visible": True}
    for tipo, conteudo in SECOES(codigo_modulo):
        if tipo == "md":
            nb.cells.append(nbf.v4.new_markdown_cell(conteudo.strip()))
        else:
            nb.cells.append(nbf.v4.new_code_cell(conteudo.strip()))
    nbf.write(nb, SAIDA)
    print(f"{SAIDA} com {len(nb.cells)} células")


if __name__ == "__main__":
    montar()
