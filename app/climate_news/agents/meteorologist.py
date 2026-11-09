"""Agente 6 — Meteorologista.

Avalia magnitude, persistência e distribuição temporal da chuva em torno de
cada anomalia. Os mecanismos sinóticos citados são sempre *hipóteses* a serem
confirmadas por análise sinótica — nunca afirmações.

Faixas de referência diária inspiradas nos avisos de acumulado do INMET
(perigo potencial até 50 mm/dia, perigo 50–100 mm/dia, grande perigo acima de
100 mm/dia). Aqui são aplicadas a dados de reanálise na escala diária, o que é
uma aproximação.
"""

from __future__ import annotations

import pandas as pd

from app.climate_news.agents.base import AgentReport, MunicipalityContext
from app.climate_news.detection.arima_zscore import Anomaly


def intensity_band(daily_mm: float) -> str:
    if daily_mm >= 100:
        return "grande_perigo_ref_inmet"
    if daily_mm >= 50:
        return "perigo_ref_inmet"
    if daily_mm >= 20:
        return "perigo_potencial_ref_inmet"
    return "abaixo_dos_limiares_de_aviso"


def mechanism_hypotheses(region: str | None, month: int, prolonged: bool) -> list[str]:
    warm = month in (10, 11, 12, 1, 2, 3)
    hypotheses: list[str] = []
    if region == "Sul":
        hypotheses.append("passagem de sistema frontal")
        if month in (4, 5, 6, 7, 8, 9, 10):
            hypotheses.append("ciclone extratropical")
        if warm:
            hypotheses.append("complexo convectivo de mesoescala")
        if prolonged:
            hypotheses.append("bloqueio atmosférico mantendo frente estacionária")
    elif region in ("Sudeste", "Centro-Oeste"):
        if warm and prolonged:
            hypotheses.append("Zona de Convergência do Atlântico Sul (ZCAS)")
        if warm:
            hypotheses.append("convecção de verão")
        hypotheses.append("passagem de sistema frontal")
    elif region == "Norte":
        if month in (12, 1, 2, 3, 4, 5):
            hypotheses.append("Zona de Convergência Intertropical (ZCIT) / convecção tropical")
        hypotheses.append("convecção local")
    elif region == "Nordeste":
        if month in (2, 3, 4, 5):
            hypotheses.append("Zona de Convergência Intertropical (ZCIT), no norte do Nordeste")
        if month in (4, 5, 6, 7):
            hypotheses.append("distúrbios ondulatórios de leste, no litoral leste")
        if warm:
            hypotheses.append("vórtice ciclônico de altos níveis (VCAN) ou ZCAS")
    return hypotheses


class MeteorologistAgent:
    name = "meteorologist"

    def review(self, anomaly: Anomaly, series: pd.Series, context: MunicipalityContext) -> AgentReport:
        day = pd.Timestamp(anomaly.date)
        around = series.loc[day - pd.Timedelta(days=7) : day + pd.Timedelta(days=7)]
        if anomaly.detector == "accumulation_percentile":
            window = series.loc[day - pd.Timedelta(days=anomaly.accumulation_days - 1) : day]
            peak_day = window.idxmax() if window.notna().any() else day
            daily = float(window.max()) if window.notna().any() else float("nan")
        else:
            peak_day, daily = day, float(anomaly.observed_mm)

        acc3 = float(series.loc[day - pd.Timedelta(days=1) : day + pd.Timedelta(days=1)].sum())
        acc5 = float(series.loc[day - pd.Timedelta(days=2) : day + pd.Timedelta(days=2)].sum())
        wet = (around >= 1.0).astype(int)
        run = 0
        if peak_day in wet.index and wet.loc[peak_day]:
            position = wet.index.get_loc(peak_day)
            left = position
            while left - 1 >= 0 and wet.iloc[left - 1]:
                left -= 1
            right = position
            while right + 1 < len(wet) and wet.iloc[right + 1]:
                right += 1
            run = right - left + 1

        prolonged = anomaly.detector == "accumulation_percentile" or (run >= 3 and acc5 >= 50)
        band = intensity_band(daily)
        notes = [
            f"Máximo diário {daily:.1f} mm ({band.replace('_', ' ')}); acumulado 3 dias centrado {acc3:.1f} mm; "
            f"5 dias centrado {acc5:.1f} mm.",
            (
                f"Episódio prolongado: {run} dias chuvosos consecutivos (≥ 1 mm) em torno do pico."
                if prolonged
                else f"Evento isolado/curto: sequência de {run} dia(s) chuvoso(s) em torno do pico."
            ),
        ]
        if daily >= 50 or acc5 >= 100:
            verdict = "plausible_extreme_event"
        elif daily >= 20 or acc5 >= 50:
            verdict = "plausible_significant_event"
        else:
            verdict = "low_meteorological_significance"
            notes.append("Magnitude baixa para impactos típicos (alagamentos, deslizamentos).")

        hypotheses = mechanism_hypotheses(context.region, day.month, prolonged)
        if hypotheses:
            notes.append(
                "Hipóteses de mecanismo (NÃO confirmadas; exigem análise sinótica): " + "; ".join(hypotheses) + "."
            )
        notes.append("Dados de reanálise (~9 km) suavizam extremos convectivos locais; totais pontuais podem ser maiores.")
        metrics = {
            "peak_daily_mm": round(daily, 2),
            "peak_day": str(pd.Timestamp(peak_day).date()),
            "accumulated_3d_centered_mm": round(acc3, 2),
            "accumulated_5d_centered_mm": round(acc5, 2),
            "consecutive_wet_days": run,
            "persistence": "prolonged" if prolonged else "isolated",
            "intensity_band": band,
            "mechanism_hypotheses": hypotheses,
        }
        return AgentReport(self.name, verdict, notes, metrics)
