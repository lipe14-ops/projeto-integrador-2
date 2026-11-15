"""Estações do ano (Hemisfério Sul) e fases do ENSO.

Estações meteorológicas (trimestres completos), convenção usada pelo INMET e
pela OMM para o Hemisfério Sul:

- verão: dezembro, janeiro, fevereiro (DJF)
- outono: março, abril, maio (MAM)
- inverno: junho, julho, agosto (JJA)
- primavera: setembro, outubro, novembro (SON)

ENSO: o NOAA/CPC classifica um *episódio* de El Niño (La Niña) quando o ONI
(média móvel trimestral da anomalia de TSM no Niño 3.4) fica ≥ +0,5 °C
(≤ −0,5 °C) por pelo menos 5 trimestres sobrepostos consecutivos. O ONI de um
mês isolado acima do limiar **não** caracteriza episódio. A função
``enso_episodes`` aplica essa regra; ``enso_phase`` do Climatologista usa só o
limiar mensal e continua disponível como contexto de cada anomalia.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

SEASONS: tuple[str, ...] = ("verao", "outono", "inverno", "primavera")
SEASON_LABELS: dict[str, str] = {
    "verao": "Verão (DJF)",
    "outono": "Outono (MAM)",
    "inverno": "Inverno (JJA)",
    "primavera": "Primavera (SON)",
}
_MONTH_TO_SEASON = {
    12: "verao", 1: "verao", 2: "verao",
    3: "outono", 4: "outono", 5: "outono",
    6: "inverno", 7: "inverno", 8: "inverno",
    9: "primavera", 10: "primavera", 11: "primavera",
}

ENSO_PHASES: tuple[str, ...] = ("el_nino", "la_nina", "neutro")
ENSO_LABELS = {"el_nino": "El Niño", "la_nina": "La Niña", "neutro": "Neutro"}
ONI_THRESHOLD = 0.5
MIN_EPISODE_SEASONS = 5


def season_of_month(month: int) -> str:
    """Estação do Hemisfério Sul de um mês (1–12)."""
    try:
        return _MONTH_TO_SEASON[int(month)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"mês inválido: {month!r}") from None


def season_array(months: Iterable[int] | np.ndarray | pd.Series) -> np.ndarray:
    """Versão vetorizada de ``season_of_month``; levanta erro para mês inválido."""
    values = np.asarray(months)
    if values.size and (np.any(values < 1) or np.any(values > 12)):
        raise ValueError("meses devem estar entre 1 e 12")
    lookup = np.array([""] + [_MONTH_TO_SEASON[m] for m in range(1, 13)], dtype=object)
    return lookup[values.astype(int)]


def season_year(year: int, month: int) -> int:
    """Ano da estação: dezembro pertence ao verão do ano seguinte (DJF)."""
    return int(year) + 1 if int(month) == 12 else int(year)


def enso_episodes(oni: Mapping[tuple[int, int], float | None]) -> dict[tuple[int, int], str]:
    """Fase ENSO de cada mês pela regra de episódio do NOAA/CPC.

    ``oni`` mapeia (ano, mês) → ONI do trimestre centrado no mês. Meses sem
    valor quebram a sequência e ficam ``neutro`` (não há como afirmar fase).
    Retorna (ano, mês) → ``el_nino`` | ``la_nina`` | ``neutro``.
    """
    if not oni:
        return {}
    keys = sorted(oni)
    start = pd.Period(year=keys[0][0], month=keys[0][1], freq="M")
    end = pd.Period(year=keys[-1][0], month=keys[-1][1], freq="M")
    months = pd.period_range(start, end, freq="M")
    values = np.array([oni.get((p.year, p.month), np.nan) for p in months], dtype=float)
    values = np.where(pd.isna(values), np.nan, values)
    phases = np.array(["neutro"] * len(months), dtype=object)
    for phase, condition in (
        ("el_nino", values >= ONI_THRESHOLD),
        ("la_nina", values <= -ONI_THRESHOLD),
    ):
        run_start = None
        for i, ok in enumerate(np.append(condition, False)):
            if ok and run_start is None:
                run_start = i
            elif not ok and run_start is not None:
                if i - run_start >= MIN_EPISODE_SEASONS:
                    phases[run_start:i] = phase
                run_start = None
    return {(p.year, p.month): str(ph) for p, ph in zip(months, phases)}
