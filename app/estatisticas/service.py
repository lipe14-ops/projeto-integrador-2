"""Carga única de ``clima_mensal`` (≈735 mil linhas) e cache dos resultados por recorte."""

from __future__ import annotations

import threading
from functools import lru_cache

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.climate_news.analysis.seasons import enso_episodes
from app.estatisticas import calculos as c

SQL_MENSAL = """
SELECT cm.codigo_ibge,
       extract(year FROM cm.mes)::int AS year,
       extract(month FROM cm.mes)::int AS month,
       cm.temperatura, cm.umidade, cm.precipitacao,
       d.regiao, d.uf, d.area_km2
FROM clima_mensal cm
JOIN municipio_details d ON d.codigo_ibge = cm.codigo_ibge
"""
SQL_NOMES = "SELECT codigo_ibge, municipio, uf FROM municipio_details"
SQL_ENSO = "SELECT year, month, enso_index FROM enso_mensal ORDER BY year, month"


class EstatisticasService:
    def __init__(self, engine: Engine | None = None, mensal: pd.DataFrame | None = None,
                 enso: pd.DataFrame | None = None, nomes: dict[int, tuple[str, str]] | None = None):
        self._engine = engine
        self._lock = threading.Lock()
        self._df: pd.DataFrame | None = None
        if mensal is not None:
            self._montar(mensal, enso if enso is not None else pd.DataFrame(columns=["year", "month", "oni"]),
                         nomes or {})

    def _montar(self, mensal: pd.DataFrame, enso: pd.DataFrame, nomes: dict[int, tuple[str, str]]) -> None:
        oni = {(int(y), int(m)): (None if pd.isna(v) else float(v)) for y, m, v in zip(enso.year, enso.month, enso.oni)}
        fases = enso_episodes(oni)
        self.enso_mensal = pd.DataFrame(
            [{"year": y, "month": m, "oni": oni.get((y, m)), "enso_phase": fases.get((y, m), "neutro")}
             for (y, m) in sorted(oni)],
            columns=["year", "month", "oni", "enso_phase"],
        )
        fase = {(y, m): p for (y, m), p in fases.items()}
        df = c.preparar(mensal)
        df["enso_phase"] = [fase.get((int(y), int(m)), "neutro") for y, m in zip(df.year, df.month)]
        self.nomes = nomes
        self.total_cadastrados = len(nomes) or int(mensal["codigo_ibge"].nunique())
        self._anom = c.anomalias_climatologicas(df)
        self._df = df

    def _carregar(self) -> None:
        with self._lock:
            if self._df is not None:
                return
            if self._engine is None:
                from app.database import engine
                self._engine = engine
            with self._engine.connect() as con:
                mensal = pd.read_sql(text(SQL_MENSAL), con)
                nomes_df = pd.read_sql(text(SQL_NOMES), con)
                enso = pd.read_sql(text(SQL_ENSO), con).rename(columns={"enso_index": "oni"})
            for col in ("temperatura", "umidade", "precipitacao", "area_km2"):
                mensal[col] = pd.to_numeric(mensal[col], errors="coerce").astype(float)
            nomes = {int(k): (n, u) for k, n, u in zip(nomes_df.codigo_ibge, nomes_df.municipio, nomes_df.uf)}
            self._montar(mensal, enso, nomes)

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self._carregar()
        return self._df  # type: ignore[return-value]

    @lru_cache(maxsize=128)  # noqa: B019 — singleton por processo
    def resumo(self, r: c.Recorte) -> dict:
        return c.resumo(self.df, r, self.nomes, self.total_cadastrados)

    @lru_cache(maxsize=128)  # noqa: B019
    def serie(self, r: c.Recorte) -> dict:
        return c.serie(self.df, r, self.enso_mensal)

    @lru_cache(maxsize=64)  # noqa: B019
    def sazonal(self, r: c.Recorte) -> dict:
        return c.sazonal(self.df, r)

    @lru_cache(maxsize=64)  # noqa: B019
    def regioes(self, r: c.Recorte) -> dict:
        return c.regioes(self.df, r)

    @lru_cache(maxsize=64)  # noqa: B019
    def enso(self, r: c.Recorte) -> dict:
        self.df  # garante a carga
        return c.enso(self._anom, r)

    @lru_cache(maxsize=64)  # noqa: B019
    def mapa(self, r: c.Recorte, variavel: str) -> dict:
        return c.mapa(self.df, r, variavel)

    @lru_cache(maxsize=1)  # noqa: B019
    def ufs(self) -> list[dict]:
        return c.por_uf(self.df)

    @lru_cache(maxsize=1)  # noqa: B019
    def abrangencia(self) -> dict:
        df = self.df
        return {
            "municipios_com_dados": int(df.dropna(subset=["temperatura"])["codigo_ibge"].nunique()),
            "municipios_cadastrados": self.total_cadastrados,
            "periodo": {"inicio": int(df["year"].min()), "fim": int(df["year"].max())},
            "meses": int(df[["year", "month"]].drop_duplicates().shape[0]),
            "regioes": len(c.REGIOES),
            "ufs": int(df["uf"].nunique()),
            "variaveis": ["temperatura do ar a 2 m", "umidade relativa", "precipitação"],
            "resolucao_temporal": "Leituras às 00 e 12 UTC, agregadas por dia e por mês",
            "resolucao_espacial": "ERA5-Land, grade de 0,1° (≈ 9 km), amostrada em cada município",
            "fonte": "ERA5-Land (ECMWF/Copernicus); malha e atributos municipais do IBGE; ONI do NOAA/CPC",
        }


_service: EstatisticasService | None = None


def get_service() -> EstatisticasService:
    global _service
    if _service is None:
        _service = EstatisticasService()
    return _service
