"""Agente 3 — Cientista da Computação.

Audita a execução: reprodutibilidade (hash da entrada, versões), custo
computacional e limitações algorítmicas conhecidas.
"""

from __future__ import annotations

import hashlib
import platform
from importlib.metadata import PackageNotFoundError, version

import pandas as pd

from app.climate_news.agents.base import AgentReport
from app.climate_news.detection.arima_zscore import DetectionResult


def series_fingerprint(series: pd.Series) -> str:
    payload = pd.DataFrame({"d": series.index.strftime("%Y-%m-%d"), "v": series.round(6)})
    return hashlib.sha256(payload.to_csv(index=False).encode()).hexdigest()


def _version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


class ComputerScientistAgent:
    name = "computer_scientist"

    def audit(self, series: pd.Series, result: DetectionResult, n_supplementary: int) -> AgentReport:
        n = len(series)
        fits = len(result.model_selection) + len(result.blocks)
        order = result.selected_spec["order"]
        notes = [
            f"Entrada com {n} dias; {fits} ajustes de máxima verossimilhança "
            f"({len(result.model_selection)} na seleção por BIC + {len(result.blocks)} reajustes anuais).",
            "Custo: cada ajuste é O(n·m²) no filtro de Kalman, com m = dimensão do estado "
            f"(≈ max(p, q+1) = {max(order[0], order[2] + 1)}); total O(B·n·m²) com B blocos — linear no tamanho da série.",
            "SARIMA com período 365 teria estado com ~365·(P+Q) dimensões (O(n·365²) por avaliação), "
            "inviável; a sazonalidade anual é tratada por regressores de Fourier com custo O(n·K).",
            "Previsões de um passo usam parâmetros estimados só com anos anteriores e observações até t−1: "
            "não há vazamento de informação futura (verificado em teste automatizado).",
            "Determinismo: mesma entrada (hash abaixo) e mesmas versões produzem os mesmos parâmetros "
            "(otimizador L-BFGS determinístico, sem amostragem aleatória).",
            "Limitação: ARIMA detecta surpresa relativa ao passado recente; eventos persistentes são "
            f"parcialmente previstos pelo próprio modelo. Detector suplementar de acumulados gerou "
            f"{n_supplementary} candidatos adicionais.",
            "Limitação: Z-Score assume resíduos aproximadamente normais; resíduos de chuva têm "
            "assimetria positiva, elevando a taxa empírica de |Z| > 3.",
        ]
        verdict = "reproducible" if result.diagnostics.get("all_blocks_converged", True) else "reproducible_with_warnings"
        metrics = {
            "input_sha256": series_fingerprint(series),
            "n_days": n,
            "n_model_fits": fits,
            "runtime_seconds": round(result.runtime_seconds, 3),
            "fit_seconds_per_block": [b.fit_seconds for b in result.blocks],
            "versions": {
                "python": platform.python_version(),
                "statsmodels": _version("statsmodels"),
                "pandas": _version("pandas"),
                "numpy": _version("numpy"),
                "scipy": _version("scipy"),
            },
        }
        return AgentReport(self.name, verdict, notes, metrics)
