"""Serviço da análise espacial/sazonal: snapshot → eventos → métricas por município.

Une chuva (anomalias do ARIMA + acumulados) e temperatura/umidade (detector
térmico) em um formato só:

    eventos:   codigo_ibge, date, variable, event_class, is_extreme,
               documented_impact, abs_z, value, enso_phase, season, year
    exposição: codigo_ibge, variable_family, year, month, days, enso_phase

e calcula as métricas do mapa coroplético com a mesma função usada pelo
relatório (``seasonal.py``). Resultados nacionais ficam em cache por filtro.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.climate_news.analysis import ANALYSIS_VERSION
from app.climate_news.analysis.classification import CLASS_DEFINITIONS, THERMAL_CLASS_DEFINITIONS
from app.climate_news.analysis.seasonal import (
    MIN_EVENTS,
    add_calendar,
    concentration,
    decluster,
    dominant_distribution,
    enso_seasonal_rates,
    knn_weights,
    morans_i,
    pooled_shares,
    seasonal_exposure,
    seasonal_table,
)
from app.climate_news.analysis.seasons import ENSO_LABELS, SEASON_LABELS, SEASONS
from app.climate_news.analysis.snapshot import DEFAULT_DIR

VARIABLES: dict[str, dict] = {
    "precipitacao": {"family": "precipitacao", "direction": "positive", "label": "Chuva acima do esperado", "unit": "mm"},
    "temperatura_alta": {"family": "temperatura", "direction": "positive", "label": "Temperatura acima do esperado", "unit": "°C"},
    "temperatura_baixa": {"family": "temperatura", "direction": "negative", "label": "Temperatura abaixo do esperado", "unit": "°C"},
    "umidade_alta": {"family": "umidade", "direction": "positive", "label": "Umidade acima do esperado", "unit": "%"},
    "umidade_baixa": {"family": "umidade", "direction": "negative", "label": "Umidade abaixo do esperado", "unit": "%"},
}
CLASS_FILTERS: dict[str, str] = {
    "todas": "Todas as anomalias válidas (exclui artefatos e chuva abaixo do previsto)",
    "estatisticas": "Somente anomalias estatísticas (não extremas para o local)",
    "extremos": "Somente extremos para o local/época (percentis da climatologia local)",
    "impacto": "Somente eventos com notícia verificada (apenas chuva)",
}
METRICS: dict[str, dict] = {
    "taxa": {"label": "Frequência de eventos", "unit": "eventos por 1.000 dias válidos", "scale": "sequential",
             "definition": "Eventos (dias anômalos consecutivos contam como um) divididos pelos dias com dado válido "
             "no período, estação e fase ENSO filtrados, × 1.000. Comparável entre municípios."},
    "contagem": {"label": "Número de eventos", "unit": "eventos", "scale": "sequential",
                 "definition": "Contagem absoluta de eventos. Não considera diferenças de cobertura: use a frequência "
                 "para comparar municípios."},
    "intensidade": {"label": "Intensidade mediana", "unit": "|Z| (desvios-padrão do resíduo)", "scale": "sequential",
                    "definition": "Mediana de |Z| do dia mais intenso de cada evento: quanto o valor observado se "
                    "afastou da previsão, em desvios-padrão dos resíduos de treino."},
    "participacao": {"label": "Participação da estação", "unit": "% da frequência anual", "scale": "diverging",
                     "definition": "Taxa da estação escolhida dividida pela soma das taxas das 4 estações. 25% = sem "
                     "preferência sazonal. Só com pelo menos 20 eventos."},
    "outono_inverno": {"label": "Participação de outono + inverno", "unit": "% da frequência anual", "scale": "diverging",
                       "definition": "Soma das participações normalizadas de outono (MAM) e inverno (JJA). 50% = sem "
                       "preferência. Só com pelo menos 20 eventos."},
    "concentracao": {"label": "Concentração sazonal", "unit": "índice 0–1", "scale": "sequential",
                     "definition": "1 − H/ln 4, H = entropia das participações normalizadas. 0: eventos igualmente "
                     "distribuídos; 1: todos em uma estação. Só com pelo menos 20 eventos."},
    "estacao_dominante": {"label": "Estação predominante", "unit": "categoria", "scale": "categorical",
                          "definition": "Estação de maior taxa, quando o teste qui-quadrado contra a distribuição "
                          "uniforme (corrigido por FDR de Benjamini–Hochberg, q < 0,05) é significativo."},
    "razao_enso": {"label": "Razão de frequência ENSO/neutro", "unit": "razão de taxas", "scale": "diverging",
                   "definition": "Taxa de eventos nos meses de episódio da fase escolhida (regra do NOAA: ONI ≥ +0,5 "
                   "ou ≤ −0,5 por 5 trimestres) dividida pela taxa nos meses neutros. 1 = sem diferença. Só com "
                   "pelo menos 10 eventos nas duas fases."},
}


class SnapshotMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class Filters:
    variable: str = "precipitacao"
    event_class: str = "todas"
    start_year: int = 2017
    end_year: int = 2025
    season: str | None = None
    enso_phase: str | None = None

    def validate(self) -> None:
        if self.variable not in VARIABLES:
            raise ValueError(f"variável inválida: {self.variable}")
        if self.event_class not in CLASS_FILTERS:
            raise ValueError(f"classe inválida: {self.event_class}")
        if self.event_class == "impacto" and VARIABLES[self.variable]["family"] != "precipitacao":
            raise ValueError("o filtro de impacto (notícias) existe só para chuva")
        if self.start_year > self.end_year:
            raise ValueError("ano inicial maior que o final")
        if self.season is not None and self.season not in SEASONS:
            raise ValueError(f"estação inválida: {self.season}")
        if self.enso_phase is not None and self.enso_phase not in ENSO_LABELS:
            raise ValueError(f"fase ENSO inválida: {self.enso_phase}")


class AnalysisService:
    def __init__(self, directory: Path = DEFAULT_DIR):
        self.directory = Path(directory)
        self._lock = threading.Lock()
        self._loaded = False

    # ---- carga ---------------------------------------------------------
    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            required = ["municipios", "enso", "precipitacao_anomalias", "precipitacao_exposicao"]
            missing = [n for n in required if not (self.directory / f"{n}.parquet").exists()]
            if missing:
                raise SnapshotMissing(
                    f"Snapshot da análise ausente em {self.directory} ({', '.join(missing)}). Rode "
                    "`uv run python -m app.climate_news.analysis.cli snapshot-chuva` (e `snapshot-termica`)."
                )
            read = lambda name: pd.read_parquet(self.directory / f"{name}.parquet")  # noqa: E731
            self.municipalities = read("municipios")
            enso = read("enso")
            phase = {(int(y), int(m)): p for y, m, p in zip(enso.year, enso.month, enso.phase_episode)}
            self.enso = enso

            precip = read("precipitacao_anomalias")
            precip = precip[precip["counted"]].copy()
            self.precip = precip  # anomalias de chuva contadas (para a análise das notícias)
            events = [
                pd.DataFrame(
                    {
                        "codigo_ibge": precip["codigo_ibge"].astype(int),
                        "date": pd.to_datetime(precip["anomaly_date"]),
                        "variable": "precipitacao",
                        "detector": precip["detector"],
                        "event_class": precip["event_class"],
                        "is_extreme": precip["is_extreme"].astype(bool),
                        "documented_impact": precip["documented_impact"].astype(bool),
                        "abs_z": precip["z_score"].abs(),
                        "value": precip["observed_mm"],
                        # início da janela do acumulado (ARIMA: o próprio dia)
                        "start": pd.to_datetime(precip["anomaly_date"])
                        - pd.to_timedelta(precip.get("window_days", pd.Series(1, index=precip.index)).fillna(1).astype(int) - 1,
                                         unit="D"),
                    }
                )
            ]
            exp = read("precipitacao_exposicao").rename(columns={"valid_days": "days"})
            exposures = [exp.assign(variable_family="precipitacao")]
            self.has_thermal = (self.directory / "termica_anomalias.parquet").exists()
            if self.has_thermal:
                thermal = read("termica_anomalias")
                variable = thermal["variable"] + np.where(thermal["direction"] == "positive", "_alta", "_baixa")
                events.append(
                    pd.DataFrame(
                        {
                            "codigo_ibge": thermal["codigo_ibge"].astype(int),
                            "date": pd.to_datetime(thermal["date"]),
                            "variable": variable,
                            "detector": "fourier_ar_zscore",
                            "event_class": thermal["event_class"],
                            "is_extreme": thermal["is_extreme"].astype(bool),
                            "documented_impact": False,
                            "abs_z": thermal["z"].abs(),
                            "value": thermal["value"],
                        }
                    )
                )
                texp = read("termica_exposicao").rename(columns={"scored_days": "days", "variable": "variable_family"})
                exposures.append(texp)
            events = add_calendar(pd.concat(events, ignore_index=True))
            events["enso_phase"] = [phase.get((y, m), "neutro") for y, m in zip(events.year, events.month)]
            exposure = pd.concat(exposures, ignore_index=True)
            exposure["enso_phase"] = [phase.get((int(y), int(m)), "neutro") for y, m in zip(exposure.year, exposure.month)]
            self.events = events
            self.exposure = exposure
            meta_path = self.directory / "metadata.json"
            self.metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            self._loaded = True

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    def available_variables(self) -> list[str]:
        self.ensure_loaded()
        return [v for v, d in VARIABLES.items() if d["family"] == "precipitacao" or self.has_thermal]

    # ---- filtros -------------------------------------------------------
    def _check(self, f: Filters) -> None:
        f.validate()
        if f.variable not in self.available_variables():
            raise SnapshotMissing("Anomalias de temperatura/umidade ainda não foram geradas (snapshot-termica).")

    @lru_cache(maxsize=64)  # noqa: B019 — o serviço é um singleton por processo
    def filtered_events(self, f: Filters) -> pd.DataFrame:
        self.ensure_loaded()
        self._check(f)
        e = self.events
        e = e[(e["variable"] == f.variable) & e["year"].between(f.start_year, f.end_year)]
        if f.event_class == "estatisticas":
            e = e[e["event_class"] == "anomalia_estatistica"]
        elif f.event_class == "extremos":
            e = e[e["is_extreme"]]
        elif f.event_class == "impacto":
            e = e[e["documented_impact"]]
        events = decluster(e, ["codigo_ibge"], gap_days=1, start_col="start")
        if f.season:
            events = events[events["season"] == f.season]
        if f.enso_phase:
            events = events[events["enso_phase"] == f.enso_phase]
        return events

    @lru_cache(maxsize=32)  # noqa: B019
    def filtered_exposure(self, f: Filters) -> pd.DataFrame:
        self.ensure_loaded()
        family = VARIABLES[f.variable]["family"]
        x = self.exposure
        x = x[(x["variable_family"] == family) & x["year"].between(f.start_year, f.end_year)]
        if f.enso_phase:
            x = x[x["enso_phase"] == f.enso_phase]
        return x

    @lru_cache(maxsize=32)  # noqa: B019
    def national(self, f: Filters) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Tabela sazonal e concentração de todos os municípios (sem filtro de estação)."""
        base = Filters(f.variable, f.event_class, f.start_year, f.end_year, None, f.enso_phase)
        events = self.filtered_events(base)
        exp = seasonal_exposure(self.filtered_exposure(base), ["codigo_ibge"])
        table = seasonal_table(events, exp, ["codigo_ibge"])
        conc = concentration(table, ["codigo_ibge"])
        conc = conc.merge(self.municipalities, on="codigo_ibge", how="left")
        return table, conc

    # ---- métricas por município (mapa) --------------------------------
    def choropleth(self, metric: str, f: Filters, compare_phase: str = "el_nino") -> dict:
        if metric not in METRICS:
            raise ValueError(f"métrica inválida: {metric}")
        if metric == "participacao" and not f.season:
            raise ValueError("a métrica 'participacao' exige uma estação")
        self.ensure_loaded()
        self._check(f)
        requested = f
        if metric == "razao_enso" and f.enso_phase:  # a razão já compara as fases
            f = Filters(f.variable, f.event_class, f.start_year, f.end_year, f.season, None)
        if self.filtered_exposure(f).empty:
            raise ValueError("nenhum dia válido para os filtros escolhidos (período ou fase ENSO sem meses)")
        table, conc = self.national(f)
        exposure = self.filtered_exposure(f)
        if f.season:
            exposure = exposure[exposure["month"].isin([m for m, s in SEASON_OF.items() if s == f.season])]
        days = exposure.groupby("codigo_ibge")["days"].sum()
        events = self.filtered_events(f)
        counts = events.groupby("codigo_ibge").size()
        frame = pd.DataFrame({"days": days}).join(counts.rename("n")).fillna({"n": 0})
        frame["n"] = frame["n"].astype(int)
        enough = conc.set_index("codigo_ibge")["n_events"].reindex(frame.index).fillna(0) >= MIN_EVENTS
        status = pd.Series("ok", index=frame.index)
        category = None
        if metric == "taxa":
            value = 1000 * frame["n"] / frame["days"].where(frame["days"] > 0)
        elif metric == "contagem":
            value = frame["n"].astype(float)
        elif metric == "intensidade":
            value = events.groupby("codigo_ibge")["abs_z"].median().reindex(frame.index)
            status[frame["n"] == 0] = "sem_eventos"
        elif metric in {"participacao", "outono_inverno", "concentracao", "estacao_dominante"}:
            c = conc.set_index("codigo_ibge").reindex(frame.index)
            column = {"participacao": f"share_norm_{f.season}", "outono_inverno": "autumn_winter_share",
                      "concentracao": "concentration", "estacao_dominante": "pattern"}[metric]
            value = c[column]
            if metric in {"participacao", "outono_inverno"}:
                value = 100 * value
            status[~enough] = "insuficiente"
            if metric == "estacao_dominante":
                category = value.where(enough)
                value = pd.Series(np.nan, index=frame.index)
        else:  # razao_enso
            rates = self._enso_municipal(f, compare_phase)
            value = rates["ratio"].reindex(frame.index)
            low = rates["n_total"].reindex(frame.index).fillna(0) < 10
            status[low] = "insuficiente"
        if metric not in {"estacao_dominante"}:
            value = value.where(status == "ok")
            # ok sem valor: sem dias válidos (taxa) ou taxa neutra nula (razão ENSO)
            status[(status == "ok") & value.isna()] = "sem_dados"
        frame["value"] = value
        frame["category"] = category if category is not None else None
        frame["status"] = status
        valid = frame["value"].dropna()
        meta = METRICS[metric]
        breaks = self._breaks(metric, valid)
        return {
            "metric": metric,
            **meta,
            "filters": requested.__dict__ | ({"compare_phase": compare_phase} if metric == "razao_enso" else {}),
            # filtros aceitos mas sem efeito nesta métrica (ela compara as estações ou as fases)
            "ignored_filters": [name for name, applies in (
                ("season", requested.season and metric in {"outono_inverno", "concentracao", "estacao_dominante"}),
                ("enso_phase", requested.enso_phase and metric == "razao_enso"),
            ) if applies],
            "variable_label": VARIABLES[f.variable]["label"],
            "period": {"start_year": f.start_year, "end_year": f.end_year},
            "breaks": breaks,
            "summary": {
                "municipalities_with_data": int((frame["status"] == "ok").sum()),
                "insufficient": int((frame["status"] == "insuficiente").sum()),
                # cadastrados sem nenhum dia válido no período (nome mantido por compatibilidade)
                "without_detection": int(len(self.municipalities) - len(frame)),
                "without_valid_data": int(len(self.municipalities) - len(frame)),
                "no_data": int((frame["status"] == "sem_dados").sum()),
                "total_events": int(frame["n"].sum()),
                "median": None if valid.empty else round(float(valid.median()), 3),
            },
            "values": [
                {
                    "codigo_ibge": int(code),
                    "value": None if pd.isna(row.value) else round(float(row.value), 4),
                    "category": None if (row.category is None or pd.isna(row.category)) else str(row.category),
                    "n": int(row.n),
                    "days": int(row.days),
                    "status": row.status,
                }
                for code, row in frame.iterrows()
            ],
        }

    @staticmethod
    def _breaks(metric: str, valid: pd.Series) -> list[float]:
        if metric == "participacao":
            return [10, 15, 20, 25, 30, 35, 40]
        if metric == "outono_inverno":
            return [30, 40, 45, 50, 55, 60, 70]
        if metric == "razao_enso":
            return [0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0]
        if metric == "estacao_dominante" or valid.empty:
            return []
        qs = valid.quantile([0.2, 0.4, 0.6, 0.8]).to_numpy()
        return sorted({round(float(q), 3) for q in qs})

    @lru_cache(maxsize=16)  # noqa: B019
    def _enso_municipal(self, f: Filters, phase: str) -> pd.DataFrame:
        base = Filters(f.variable, f.event_class, f.start_year, f.end_year, f.season, None)
        events = self.filtered_events(base)
        exposure = self.filtered_exposure(base)
        if f.season:
            exposure = exposure[exposure["month"].isin([m for m, s in SEASON_OF.items() if s == f.season])]
        days = exposure.groupby(["codigo_ibge", "enso_phase"])["days"].sum().unstack(fill_value=0)
        n = events.groupby(["codigo_ibge", "enso_phase"]).size().unstack(fill_value=0)
        n = n.reindex(index=days.index, columns=days.columns, fill_value=0)
        rate = n / days.where(days > 0)
        out = pd.DataFrame(index=days.index)
        out["ratio"] = (rate.get(phase) / rate.get("neutro")).replace([np.inf], np.nan)
        out["n_total"] = n.get(phase, 0) + n.get("neutro", 0)
        return out

    # ---- município, regiões, ranking, ENSO ----------------------------
    def municipality(self, codigo_ibge: int, f: Filters) -> dict:
        self.ensure_loaded()
        self._check(f)
        info = self.municipalities[self.municipalities["codigo_ibge"] == codigo_ibge]
        if info.empty:
            raise KeyError(codigo_ibge)
        info = info.iloc[0]
        table, conc = self.national(f)
        own = table[table["codigo_ibge"] == codigo_ibge]
        summary = conc[conc["codigo_ibge"] == codigo_ibge]
        region_codes = self.municipalities.loc[self.municipalities["regiao"] == info["regiao"], "codigo_ibge"]
        region = pooled_shares(table[table["codigo_ibge"].isin(region_codes)], [])
        uf_codes = self.municipalities.loc[self.municipalities["uf"] == info["uf"], "codigo_ibge"]
        state = pooled_shares(table[table["codigo_ibge"].isin(uf_codes)], [])
        brazil = pooled_shares(table, [])
        events = self.filtered_events(f)
        events = events[events["codigo_ibge"] == codigo_ibge]
        own_exposure = self.filtered_exposure(f)
        own_exposure = own_exposure[own_exposure["codigo_ibge"] == codigo_ibge]
        if f.season:  # mesma restrição dos eventos: sem linhas de outras estações com 0 eventos
            own_exposure = own_exposure[own_exposure["month"].map(SEASON_OF) == f.season]
        enso = enso_seasonal_rates(events, own_exposure, ["codigo_ibge"]) if not events.empty else pd.DataFrame()
        records = lambda frame, cols: [  # noqa: E731
            {k: _clean(v) for k, v in row.items()} for row in frame[cols].to_dict("records")
        ]
        return {
            "codigo_ibge": int(codigo_ibge),
            "nome": info["nome"],
            "uf": info["uf"],
            "regiao": info["regiao"],
            "filters": f.__dict__,
            "has_detection": not own.empty,
            "seasons": records(own, ["season", "n", "days", "rate_per_1000", "share_abs", "share_norm"]) if not own.empty else [],
            "summary": {k: _clean(v) for k, v in summary.iloc[0].to_dict().items()} if not summary.empty else None,
            "comparison": {
                "estado": records(state, ["season", "n", "days", "rate_per_1000", "share_norm"]),
                "regiao": records(region, ["season", "n", "days", "rate_per_1000", "share_norm"]),
                "brasil": records(brazil, ["season", "n", "days", "rate_per_1000", "share_norm"]),
            },
            "enso": records(enso, ["season", "enso_phase", "n", "days", "rate_per_1000", "ratio_vs_neutral",
                                   "ratio_ci_low", "ratio_ci_high"]) if not enso.empty else [],
            "events_by_year": events.groupby("year").size().astype(int).to_dict(),
        }

    def regions(self, f: Filters) -> dict:
        self.ensure_loaded()
        self._check(f)
        table, conc = self.national(f)
        table = table.merge(self.municipalities[["codigo_ibge", "regiao", "uf"]], on="codigo_ibge", how="left")
        pooled_region = pooled_shares(table, ["regiao"])
        pooled_brazil = pooled_shares(table, []).assign(regiao="Brasil")
        dist = dominant_distribution(conc, ["regiao"])
        dist_brazil = dominant_distribution(conc.assign(regiao="Brasil"), ["regiao"])
        median_conc = conc.groupby("regiao")["concentration"].median()
        valid = conc.dropna(subset=["autumn_winter_share", "latitude", "longitude"])
        valid = valid[valid["n_events"] >= MIN_EVENTS]
        moran = (
            morans_i(valid["autumn_winter_share"].to_numpy(), knn_weights(valid.latitude, valid.longitude), 199)
            if len(valid) >= 30 else None
        )
        return {
            "filters": f.__dict__,
            "pooled": [{k: _clean(v) for k, v in r.items()} for r in pd.concat([pooled_region, pooled_brazil])
                       [["regiao", "season", "n", "days", "rate_per_1000", "share_norm"]].to_dict("records")],
            "patterns": [{k: _clean(v) for k, v in r.items()} for r in pd.concat([dist, dist_brazil]).to_dict("records")],
            "median_concentration": {str(k): _clean(v) for k, v in median_conc.items()},
            "moran_autumn_winter": moran,
        }

    def ranking(self, f: Filters, season: str, limit: int = 20, ascending: bool = False) -> list[dict]:
        from app.climate_news.analysis.seasonal import ranking as rank

        self.ensure_loaded()
        self._check(f)
        _, conc = self.national(f)
        top = rank(conc, season, limit, ascending)
        cols = ["codigo_ibge", "nome", "uf", "regiao", "n_events", f"share_norm_{season}", "concentration",
                "dominant_season", "pattern", "chi2_qvalue"]
        return [{k: _clean(v) for k, v in r.items()} for r in top[cols].rename(
            columns={f"share_norm_{season}": "share_norm"}).to_dict("records")]

    # ---- notícias × intensidade e visão geral -------------------------
    INTENSITY_BINS = (0, 20, 40, 60, 100, float("inf"))
    INTENSITY_LABELS = ("< 20 mm", "20–40 mm", "40–60 mm", "60–100 mm", "≥ 100 mm")

    @staticmethod
    def _rate(n: int, k: int) -> dict:
        """Proporção k/n com intervalo de Wilson de 95%."""
        if n == 0:
            return {"n": 0, "with_news": 0, "pct": None, "ci_low": None, "ci_high": None}
        z = 1.959964
        p = k / n
        center = (p + z * z / (2 * n)) / (1 + z * z / n)
        half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        return {"n": int(n), "with_news": int(k), "pct": round(100 * p, 1),
                "ci_low": round(float(100 * max(center - half, 0)), 1),
                "ci_high": round(float(100 * min(center + half, 1)), 1)}

    def news_by_intensity(self) -> dict:
        """Proporção de eventos de chuva com notícia verificada, por intensidade e por classe.

        Usa só as anomalias cujas notícias já foram investigadas. Não há grupo de
        controle (dias sem anomalia), então a proporção mede a confirmação dos
        eventos detectados, não o acerto da detecção.
        """
        self.ensure_loaded()
        d = self.precip
        if "news_investigated" not in d:
            raise SnapshotMissing("O snapshot não informa quais anomalias tiveram notícias investigadas; "
                                  "rode `snapshot-chuva` novamente.")
        d = d[d["news_investigated"].astype(bool)].copy()
        d["has_news"] = d["verified_news"] > 0
        daily = d[d["detector"] == "arima_zscore"]
        bins = pd.cut(daily["observed_mm"], self.INTENSITY_BINS, right=False, labels=self.INTENSITY_LABELS)
        by_intensity = [
            {"label": str(label), **self._rate(int((bins == label).sum()), int(daily.loc[bins == label, "has_news"].sum()))}
            for label in self.INTENSITY_LABELS
        ]
        class_order = ["anomalia_estatistica", "extremo_sazonal", "extremo_local", "extremo_acumulado"]
        by_class = [
            {"event_class": c, "label": CLASS_DEFINITIONS[c]["label"],
             **self._rate(int((d["event_class"] == c).sum()), int(d.loc[d["event_class"] == c, "has_news"].sum()))}
            for c in class_order
        ]
        high = d["high_intensity"].astype(bool)
        return {
            "investigated_events": int(len(d)),
            "investigated_municipalities": int(d["codigo_ibge"].nunique()),
            "overall": self._rate(int(len(d)), int(d["has_news"].sum())),
            "by_intensity_daily": by_intensity,
            "by_class": by_class,
            "by_high_intensity": {
                "alta": self._rate(int(high.sum()), int(d.loc[high, "has_news"].sum())),
                "demais": self._rate(int((~high).sum()), int(d.loc[~high, "has_news"].sum())),
            },
            "definitions": {
                "high_intensity": "≥ 50 mm em um dia ou ≥ 100 mm em 5 dias",
                "intensity_bins": "chuva do dia nas anomalias diárias (ARIMA + Z)",
                "with_news": "pelo menos uma notícia verificada na página original",
            },
            "caveats": [
                "Só eventos com notícias investigadas (municípios selecionados), não todo o país.",
                "Sem grupo de controle: não se sabe quantas notícias seriam achadas em dias comuns.",
                "Notícia indica cobertura de uma ocorrência, não confirma o fenômeno meteorológico.",
            ],
        }

    def overview(self) -> dict:
        """Volume de dados reunido pela plataforma (lido do snapshot)."""
        self.ensure_loaded()
        precipitation = self.metadata.get("precipitation", {})
        return {
            "climate_records": precipitation.get("climate_records"),
            "municipalities": int(len(self.municipalities)),
            "municipalities_with_data": precipitation.get("municipalities_with_data"),
            "period": {"start": 2015, "end": 2025, "scored_start": 2017},
            "rain_events": int(len(self.precip)),
            "thermal_anomalies": int((self.events["variable"] != "precipitacao").sum()),
            "variables": ["temperatura", "umidade relativa", "precipitação"],
        }

    def definitions(self) -> dict:
        self.ensure_loaded()
        return {
            "analysis_version": ANALYSIS_VERSION,
            "seasons": SEASON_LABELS,
            "enso_phases": ENSO_LABELS,
            "enso_rule": "Episódio: ONI ≥ +0,5 °C (El Niño) ou ≤ −0,5 °C (La Niña) por 5 trimestres sobrepostos "
            "consecutivos (NOAA/CPC). Demais meses: neutro.",
            "variables": {k: {"label": v["label"], "unit": v["unit"], "available": k in self.available_variables()}
                          for k, v in VARIABLES.items()},
            "class_filters": CLASS_FILTERS,
            "precipitation_classes": CLASS_DEFINITIONS,
            "thermal_classes": THERMAL_CLASS_DEFINITIONS,
            "metrics": METRICS,
            "min_events": MIN_EVENTS,
            "snapshot": {k: v.get("generated_at") for k, v in self.metadata.items() if isinstance(v, dict)},
        }


SEASON_OF = {m: SEASONS[[0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 0][m - 1]] for m in range(1, 13)}


def _clean(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else round(float(value), 5)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA or (isinstance(value, float) and np.isnan(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


_service: AnalysisService | None = None


def get_service() -> AnalysisService:
    global _service
    if _service is None:
        _service = AnalysisService()
    return _service
