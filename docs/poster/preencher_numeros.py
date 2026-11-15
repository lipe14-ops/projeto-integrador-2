"""Gera poster.tex a partir de poster.tex.in com os números de resumo.json.

    uv run python docs/poster/preencher_numeros.py

Também copia as figuras de docs/avaliacao_professor/resultados/figuras/.
Falha se algum marcador @@...@@ ficar sem valor.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "avaliacao_professor" / "resultados"
FIGURES = ["barras_regioes_precipitacao.png", "metodo_sigma_sazonal.png", "mapa_estacao_predominante.png"]


def br(value: float, digits: int = 1) -> str:
    """Número no formato brasileiro (vírgula decimal)."""
    return f"{value:.{digits}f}".replace(".", ",")


def main() -> None:
    s = json.loads((RESULTS / "resumo.json").read_text())
    rain = s["sazonal"]["precipitacao|todas"]
    poa = rain["porto_alegre"]
    brazil = rain["por_regiao"]["Brasil"]["padroes_pct"]
    m = s["metodo"]
    values = {
        "DIAS": f"{s['cobertura']['precipitacao']['dias_validos_mediana']:,.0f}".replace(",", "."),
        "ARIMA_EST": br(s["classes"]["arima_pct_apenas_estatistica"]),
        "M_N": str(m["municipios"]),
        "M_RATE": br(m["taxa_alerta_pct"]["3.0"]["mediana"], 2),
        "M_NULL": br(m["simulacao_nula"]["taxa_alerta_pct"]["3.0"]["mediana"], 2),
        "M_BF": br(m["pct_brown_forsythe_p_menor_005"], 0),
        "M_P99A": br(m["pct_alertas_que_sao_p99"], 0),
        "M_P99D": br(m["pct_p99_detectados_pelo_arima"], 0),
        "POA_OI": br(poa["outono_inverno_pct"]),
        "POA_N": str(poa["n_eventos"]),
        "POA_Q": br(poa["qvalor"], 2),
        "POA_VER": br(poa["participacao_norm_pct"]["verao"]),
        "RS_OI": br(poa["mediana_rs_pct"]),
        "BR_VER": br(brazil.get("predominio_verao", 0)),
        "BR_OUT": br(brazil.get("predominio_outono", 0)),
        "BR_INV": br(brazil.get("predominio_inverno", 0)),
    }
    text = (HERE / "poster.tex.in").read_text()
    for key, value in values.items():
        text = text.replace(f"@@{key}@@", value)
    left = re.findall(r"@@\w+@@", text)
    if left:
        raise SystemExit(f"marcadores sem valor: {left}")
    (HERE / "poster.tex").write_text(text)
    (HERE / "figures").mkdir(exist_ok=True)
    for name in FIGURES:
        shutil.copy(RESULTS / "figuras" / name, HERE / "figures" / name)
    print(json.dumps(values, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
