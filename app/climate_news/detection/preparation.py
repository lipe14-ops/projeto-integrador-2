"""Etapa 1 — preparação e validação da série diária de precipitação.

Estratégias de tratamento (documentadas também no relatório de qualidade):

- Datas são convertidas para ``datetime`` e normalizadas para o dia (UTC).
- A série é ordenada e reindexada em frequência diária; dias inexistentes
  na entrada viram ``NaN`` (dado ausente), nunca zero.
- Duplicatas com o mesmo valor são consolidadas; duplicatas com valores
  diferentes são consideradas inconsistentes e o dia vira ``NaN``.
- Valores negativos ou acima de ``max_valid_mm`` são fisicamente inválidos e
  viram ``NaN``. Valores acima de ``suspect_mm`` são mantidos, mas sinalizados.
- Precipitação zero é um valor válido e é preservada.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np
import pandas as pd

# Recorde diário brasileiro conhecido fica abaixo de 700 mm (litoral norte de
# SP, fev/2023). Acima de 1000 mm/dia o valor é tratado como erro físico.
MAX_VALID_MM = 1000.0
SUSPECT_MM = 400.0


@dataclass
class DataQualityReport:
    start: date | None = None
    end: date | None = None
    n_input_rows: int = 0
    n_days: int = 0
    n_valid: int = 0
    n_missing: int = 0
    n_missing_dates_inserted: int = 0
    n_zero: int = 0
    n_wet_days: int = 0  # >= 1 mm (convenção ETCCDI)
    n_duplicates_consolidated: int = 0
    n_duplicates_conflicting: int = 0
    n_negative: int = 0
    n_implausible: int = 0
    n_suspect: int = 0
    n_incomplete_aggregation: int = 0
    missing_fraction: float = 0.0
    zero_fraction: float = 0.0
    suspect_dates: list[str] = field(default_factory=list)
    invalid_dates: list[str] = field(default_factory=list)
    strategies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["start"] = self.start.isoformat() if self.start else None
        data["end"] = self.end.isoformat() if self.end else None
        return data


def _to_day_index(values: pd.Series) -> pd.DatetimeIndex:
    parsed = pd.to_datetime(values, utc=True, errors="coerce")
    return pd.DatetimeIndex(parsed).tz_convert("UTC").tz_localize(None).normalize()


def aggregate_era5_12h_to_daily(
    frame: pd.DataFrame,
    datetime_col: str = "datetime",
    value_col: str = "precipitacao",
) -> tuple[pd.DataFrame, int]:
    """Converte acumulados ERA5-Land de 12 h em totais diários (dia UTC).

    No banco, o valor às 12:00 UTC do dia D é a chuva entre 00–12 UTC de D, e
    o valor às 00:00 UTC de D+1 é a chuva entre 12–24 UTC de D. O total do
    dia D só é calculado quando as duas metades existem; caso contrário o dia
    fica ausente (não zero). Retorna o DataFrame diário e o número de dias
    com agregação incompleta.
    """
    timestamps = pd.to_datetime(frame[datetime_col], utc=True)
    values = pd.to_numeric(frame[value_col], errors="coerce")
    # o acumulado que termina às 00 UTC pertence ao dia anterior
    day = (timestamps - pd.Timedelta(hours=1)).dt.tz_localize(None).dt.normalize()
    grouped = pd.DataFrame({"date": day, "value": values}).groupby("date")["value"]
    daily = grouped.sum(min_count=2)
    halves = grouped.count()
    daily[halves < 2] = np.nan
    incomplete = int((halves < 2).sum())
    out = daily.rename("precipitation_mm").rename_axis("date").reset_index()
    return out, incomplete


def prepare_daily_series(
    frame: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "precipitation_mm",
    max_valid_mm: float = MAX_VALID_MM,
    suspect_mm: float = SUSPECT_MM,
    incomplete_aggregation: int = 0,
) -> tuple[pd.Series, DataQualityReport]:
    """Valida e regulariza uma série diária. Retorna (série, relatório)."""
    report = DataQualityReport(n_input_rows=len(frame))
    report.n_incomplete_aggregation = incomplete_aggregation
    if frame.empty:
        raise ValueError("A série de precipitação está vazia.")
    if date_col not in frame or value_col not in frame:
        raise ValueError(f"Colunas obrigatórias ausentes: {date_col!r}, {value_col!r}")

    days = _to_day_index(frame[date_col])
    if days.isna().any():
        raise ValueError(f"{int(days.isna().sum())} datas não puderam ser interpretadas.")
    values = pd.to_numeric(frame[value_col], errors="coerce").astype(float)
    raw = pd.Series(values.to_numpy(), index=days).sort_index()

    # duplicatas: mesmo valor -> consolida; valores distintos -> inconsistente
    duplicated_days = raw.index[raw.index.duplicated(keep=False)].unique()
    conflicting: list[pd.Timestamp] = []
    for day in duplicated_days:
        group = raw.loc[[day]].dropna().round(6).unique()
        if len(group) > 1:
            conflicting.append(day)
    report.n_duplicates_consolidated = int(raw.index.duplicated().sum()) - len(conflicting)
    report.n_duplicates_conflicting = len(conflicting)
    series = raw.groupby(level=0).first()
    if conflicting:
        series.loc[conflicting] = np.nan
        report.invalid_dates += [d.date().isoformat() for d in conflicting]

    negative = series < 0
    implausible = series > max_valid_mm
    report.n_negative = int(negative.sum())
    report.n_implausible = int(implausible.sum())
    report.invalid_dates += [d.date().isoformat() for d in series.index[negative | implausible]]
    series[negative | implausible] = np.nan
    suspect = series > suspect_mm
    report.n_suspect = int(suspect.sum())
    report.suspect_dates = [d.date().isoformat() for d in series.index[suspect]]

    # dias ausentes nas pontas não carregam informação: a série começa e
    # termina no primeiro/último dia válido
    valid_days = series.dropna().index
    if valid_days.empty:
        raise ValueError("A série não possui nenhum valor válido.")
    series = series.loc[valid_days.min() : valid_days.max()]
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="D")
    report.n_missing_dates_inserted = len(full_index) - len(series)
    series = series.reindex(full_index).rename("precipitation_mm")
    series.index.name = "date"

    report.start = full_index[0].date()
    report.end = full_index[-1].date()
    report.n_days = len(series)
    report.n_missing = int(series.isna().sum())
    report.n_valid = report.n_days - report.n_missing
    report.n_zero = int((series == 0).sum())
    report.n_wet_days = int((series >= 1.0).sum())
    report.missing_fraction = round(report.n_missing / report.n_days, 6)
    report.zero_fraction = round(report.n_zero / max(report.n_valid, 1), 6)
    report.invalid_dates = sorted(set(report.invalid_dates))
    report.strategies = [
        "datas normalizadas para o dia UTC e ordenadas cronologicamente",
        "frequência diária garantida por reindexação; dias ausentes ficam NaN",
        "duplicatas idênticas consolidadas; duplicatas conflitantes viram NaN",
        f"valores negativos ou > {max_valid_mm:g} mm/dia viram NaN (fisicamente inválidos)",
        f"valores > {suspect_mm:g} mm/dia mantidos e sinalizados como suspeitos",
        "precipitação zero preservada; ausência nunca é imputada como zero",
        "o modelo ARIMA trata NaN pelo filtro de Kalman, sem imputação",
    ]
    if incomplete_aggregation:
        report.strategies.append(
            "dias com acumulado ERA5 de 12 h incompleto ficam ausentes"
        )
    return series, report
