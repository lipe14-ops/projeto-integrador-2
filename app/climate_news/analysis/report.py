"""Relatório reprodutível da análise espacial e sazonal.

Lê o snapshot (``data/analise``) com as mesmas funções da API e grava em
``docs/avaliacao_professor/resultados/``:

- ``tabelas/*.csv``: tabela municipal (participações, padrão, teste), regiões,
  ENSO por região × estação, classes de evento, avaliação do método;
- ``figuras/*.png``: mapas coropléticos e gráficos;
- ``resumo.json``: todos os números citados no relatório final.

Nenhum número do relatório final é digitado à mão: todos saem daqui.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from app.climate_news.analysis import ANALYSIS_VERSION
from app.climate_news.analysis.method_eval import GAUSSIAN_TAIL, THRESHOLDS
from app.climate_news.analysis.seasonal import MIN_EVENTS, enso_seasonal_rates, pooled_shares
from app.climate_news.analysis.seasons import ENSO_LABELS, SEASON_LABELS, SEASONS
from app.climate_news.analysis.service import VARIABLES, AnalysisService, Filters

log = logging.getLogger("climate_news.analysis")

POA = 4314902
REGIONS = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

# Paleta validada (CVD e visão normal, todos os pares) — ver relatório final.
SEASON_COLORS = {"verao": "#e34948", "outono": "#eda100", "inverno": "#2a78d6", "primavera": "#1baf7a"}
NEUTRAL = "#b9b8b2"
MISSING = "#ffffff"
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#a3302f", "#e34948", "#f0a3a2", "#f0efec", "#9ec5f4", "#2a78d6", "#184f95"]
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _r(value, digits: int = 4):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else round(float(value), digits)
    return value


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2,
        "ytick.color": INK_2, "axes.titlecolor": INK, "axes.titlesize": 10, "axes.spines.top": False,
        "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight",
    })
    return plt


def _map_axes(plt, ax, gdf, column, colors, breaks=None, categories=None, title="", legend_title=""):
    """Coroplético: classes por quebras (``breaks``) ou categorias. NaN = sem dados (hachurado)."""
    from matplotlib.patches import Patch

    missing = gdf[column].isna() if categories is None else ~gdf[column].isin(list(categories))
    no_data = missing & gdf["n_events"].isna() if "n_events" in gdf else missing & False
    insufficient = missing & ~no_data
    if insufficient.any():  # geopandas falha ao desenhar camada vazia
        gdf[insufficient].plot(ax=ax, color=MISSING, edgecolor="#c9c8c2", linewidth=0.05, hatch="////")
    if no_data.any():
        gdf[no_data].plot(ax=ax, color="#8e8d88", linewidth=0)
    handles = []
    if categories is not None:
        for key, (label, color) in categories.items():
            part = gdf[gdf[column] == key]
            if not part.empty:
                part.plot(ax=ax, color=color, linewidth=0)
            handles.append(Patch(facecolor=color, label=f"{label} ({len(part)})"))
    else:
        edges = [-np.inf, *breaks, np.inf]
        values = gdf[column]
        for i, color in enumerate(colors[: len(edges) - 1]):
            part = gdf[(values >= edges[i]) & (values < edges[i + 1])]
            if not part.empty:
                part.plot(ax=ax, color=color, linewidth=0)
            low = "" if i == 0 else f"{edges[i]:g}"
            high = "" if i == len(edges) - 2 else f"{edges[i + 1]:g}"
            label = f"< {high}" if not low else (f"≥ {low}" if not high else f"{low} – {high}")
            handles.append(Patch(facecolor=color, label=f"{label} ({len(part)})"))
    handles.append(Patch(facecolor=MISSING, edgecolor="#c9c8c2", hatch="////",
                         label=f"< {MIN_EVENTS} eventos: insuficiente ({int(insufficient.sum())})"))
    if "n_events" in gdf:
        handles.append(Patch(facecolor="#8e8d88", label=f"sem dados válidos ({int(no_data.sum())})"))
    # legenda fora do mapa (dentro, cobria o Sul do país)
    ax.legend(handles=handles, title=legend_title, loc="upper left", bbox_to_anchor=(0.0, -0.01), ncol=2,
              fontsize=7, title_fontsize=7, frameon=False, alignment="left")
    ax.set_title(title, loc="left")
    ax.set_axis_off()


def _season_bars(plt, ax, pooled: pd.DataFrame, groups: list[str], title: str):
    width = 0.2
    x = np.arange(len(groups))
    for i, season in enumerate(SEASONS):
        values = [
            100 * pooled[(pooled["grupo"] == g) & (pooled["season"] == season)]["share_norm"].sum() for g in groups
        ]
        ax.bar(x + (i - 1.5) * width, values, width * 0.9, color=SEASON_COLORS[season], label=SEASON_LABELS[season])
    ax.axhline(25, color=INK_2, linewidth=0.8, linestyle="--", label="25% = sem preferência")
    ax.set_xticks(x, groups)
    ax.set_ylabel("participação normalizada (%)")
    ax.set_title(title, loc="left")
    ax.grid(axis="y", color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Blocos de análise
# ---------------------------------------------------------------------------


def seasonal_block(svc: AnalysisService, f: Filters) -> dict:
    table, conc = svc.national(f)
    regioes = svc.regions(f)
    conc = conc.copy()
    eligible = conc[conc["n_events"] >= MIN_EVENTS]
    by_region = {}
    for region in REGIONS + ["Brasil"]:
        part = eligible if region == "Brasil" else eligible[eligible["regiao"] == region]
        all_part = conc if region == "Brasil" else conc[conc["regiao"] == region]
        patterns = part["pattern"].value_counts()
        by_region[region] = {
            "municipios": int(len(all_part)),
            "elegiveis": int(len(part)),
            "mediana_eventos": _r(all_part["n_events"].median(), 1),
            "mediana_outono_inverno_pct": _r(100 * part["autumn_winter_share"].median(), 1),
            "pct_outono_inverno_acima_50": _r(100 * (part["autumn_winter_share"] > 0.5).mean(), 1),
            "padroes_pct": {k: _r(100 * v / max(len(part), 1), 1) for k, v in patterns.items()},
            "predominio_outono_ou_inverno_pct": _r(
                100 * part["pattern"].isin(["predominio_outono", "predominio_inverno"]).mean(), 1
            ),
        }
    poa = conc[conc["codigo_ibge"] == POA]
    poa_info = None
    if not poa.empty:
        row = poa.iloc[0]
        share = row["autumn_winter_share"]
        south = eligible[eligible["regiao"] == "Sul"]["autumn_winter_share"]
        rs = eligible[eligible["uf"] == "RS"]["autumn_winter_share"]
        poa_info = {
            "n_eventos": int(row["n_events"]),
            "participacao_norm_pct": {s: _r(100 * row[f"share_norm_{s}"], 1) for s in SEASONS},
            "outono_inverno_pct": _r(100 * share, 1),
            "padrao": row["pattern"],
            "qvalor": _r(row["chi2_qvalue"]),
            "pvalor": _r(row["chi2_pvalue"]),
            "percentil_brasil": _r(100 * (eligible["autumn_winter_share"] <= share).mean(), 1),
            "percentil_sul": _r(100 * (south <= share).mean(), 1) if len(south) else None,
            "mediana_rs_pct": _r(100 * rs.median(), 1) if len(rs) else None,
        }
    pooled = pd.DataFrame(regioes["pooled"])
    return {
        "table": table, "conc": conc, "pooled": pooled, "moran": regioes["moran_autumn_winter"],
        "summary": {"por_regiao": by_region, "porto_alegre": poa_info, "moran_outono_inverno": regioes["moran_autumn_winter"],
                    "pooled_regioes": {
                        f"{r['regiao']}|{r['season']}": _r(100 * r["share_norm"], 1) for r in regioes["pooled"]
                    }},
    }


def enso_block(svc: AnalysisService, f: Filters) -> pd.DataFrame:
    events = svc.filtered_events(f).merge(svc.municipalities[["codigo_ibge", "regiao"]], on="codigo_ibge")
    exposure = svc.filtered_exposure(f).merge(svc.municipalities[["codigo_ibge", "regiao"]], on="codigo_ibge")
    regional = enso_seasonal_rates(events, exposure, ["regiao"])
    national = enso_seasonal_rates(events.assign(regiao="Brasil"), exposure.assign(regiao="Brasil"), ["regiao"])
    return pd.concat([regional, national], ignore_index=True)


def classes_block(directory: Path) -> dict:
    precip = pd.read_parquet(directory / "precipitacao_anomalias.parquet")
    out = {
        "chuva_por_classe": precip["event_class"].value_counts().to_dict(),
        "chuva_por_detector_e_classe": {
            f"{d}|{c}": int(n) for (d, c), n in precip.groupby(["detector", "event_class"]).size().items()
        },
    }
    arima = precip[(precip["detector"] == "arima_zscore") & precip["counted"]]
    out["arima_contadas"] = int(len(arima))
    out["arima_pct_apenas_estatistica"] = _r(100 * (arima["event_class"] == "anomalia_estatistica").mean(), 1)
    out["arima_pct_extremo"] = _r(100 * arima["is_extreme"].mean(), 1)
    out["arima_pct_intensidade_alta"] = _r(100 * arima["high_intensity"].mean(), 1)
    out["arima_pct_com_noticia"] = _r(100 * arima["documented_impact"].mean(), 2)
    extremes = precip[precip["is_extreme"] & precip["counted"]]
    out["extremos_pct_com_noticia"] = _r(100 * extremes["documented_impact"].mean(), 2)
    thermal_path = directory / "termica_anomalias.parquet"
    if thermal_path.exists():
        thermal = pd.read_parquet(thermal_path)
        out["termica_por_variavel_direcao_classe"] = {
            f"{v}|{d}|{c}": int(n) for (v, d, c), n in thermal.groupby(["variable", "direction", "event_class"]).size().items()
        }
        diag = pd.read_parquet(directory / "termica_diagnosticos.parquet")
        out["termica_diagnosticos"] = {
            var: {
                "z_std_mediana": _r(g["z_std"].median()),
                "taxa_pos_mediana_pct": _r(100 * g["rate_positive"].median(), 3),
                "taxa_neg_mediana_pct": _r(100 * g["rate_negative"].median(), 3),
                "ordem_ar_moda": int(g["ar_order"].mode().iloc[0]),
            }
            for var, g in diag.groupby("variable")
        }
    # exemplo real de resíduo (Porto Alegre, ARIMA): usado na explicação do "resíduo de chuva"
    poa = precip[(precip["codigo_ibge"] == POA) & (precip["detector"] == "arima_zscore")].sort_values("anomaly_date")
    out["exemplos_residuo_poa"] = [
        {"data": str(r.anomaly_date.date()), "observado_mm": _r(r.observed_mm, 2), "previsto_mm": _r(r.predicted_mm, 2),
         "residuo_log": _r(r.residual), "residuo_mm": _r(r.residual_mm, 2), "z": _r(r.z_score, 3)}
        for r in poa.itertuples()
    ]
    return out


def method_block(directory: Path) -> dict | None:
    path = directory / "metodo_avaliacao.parquet"
    if not path.exists():
        return None
    m = pd.read_parquet(path)
    errors = m[m["error"].notna()] if "error" in m else m.iloc[0:0]
    m = m[m["error"].isna()] if "error" in m else m
    out: dict = {"municipios": int(len(m)), "erros": int(len(errors))}
    out["taxa_alerta_pct"] = {
        str(k): {"mediana": _r(100 * m[f"rate_pos_{k}"].median(), 3), "p10": _r(100 * m[f"rate_pos_{k}"].quantile(0.1), 3),
                 "p90": _r(100 * m[f"rate_pos_{k}"].quantile(0.9), 3), "gaussiana": _r(100 * GAUSSIAN_TAIL[k], 3)}
        for k in THRESHOLDS
    }
    out["z_std_mediana"] = _r(m["z_std"].median())
    out["z_assimetria_mediana"] = _r(m["z_skew"].median())
    out["pct_modelos_com_fourier"] = _r(100 * (m["seasonal_terms"] == "fourier").mean(), 1)
    out["pct_brown_forsythe_p_menor_005"] = _r(100 * (m["brown_forsythe_p"] < 0.05).mean(), 1)
    ratio = m[[f"z_std_{s}" for s in SEASONS]].max(axis=1) / m[[f"z_std_{s}" for s in SEASONS]].min(axis=1)
    out["razao_dp_max_min_estacoes_mediana"] = _r(ratio.median(), 3)
    for kind in ("global", "seasonal"):
        totals = {s: int(m[f"alerts_{kind}_{s}"].sum()) for s in SEASONS}
        days = {s: int(m[f"days_cmp_{s}"].sum()) for s in SEASONS}
        rates = {s: totals[s] / days[s] for s in SEASONS}
        out[f"alertas_sigma_{kind}"] = {
            "contagem": totals, "participacao_norm_pct": {s: _r(100 * rates[s] / sum(rates.values()), 1) for s in SEASONS}
        }
    # mesmo município: mudança da estação dominante ao trocar σ único por σ sazonal
    dom = lambda kind: m[[f"alerts_{kind}_{s}" for s in SEASONS]].div(  # noqa: E731
        m[[f"days_cmp_{s}" for s in SEASONS]].to_numpy()).idxmax(axis=1).str.split("_").str[-1]
    enough = m[[f"alerts_global_{s}" for s in SEASONS]].sum(axis=1) >= 8
    out["pct_muda_estacao_dominante"] = _r(100 * (dom("global") != dom("seasonal"))[enough].mean(), 1)
    out["municipios_com_8_alertas"] = int(enough.sum())
    for pct in (95, 99):
        if f"p{pct}_verao" in m:
            rates = {s: m[f"p{pct}_{s}"].sum() / m[f"days_{s}"].sum() for s in SEASONS}
            out[f"extremos_p{pct}_participacao_norm_pct"] = {
                s: _r(100 * rates[s] / sum(rates.values()), 1) for s in SEASONS
            }
        out[f"jaccard_p{pct}_mediana"] = _r(m[f"jaccard_p{pct}"].median(), 3)
        out[f"pct_alertas_que_sao_p{pct}"] = _r(100 * m[f"p{pct}_and_arima"].sum() / max(m["arima_alerts"].sum(), 1), 1)
        out[f"pct_p{pct}_detectados_pelo_arima"] = _r(100 * m[f"p{pct}_and_arima"].sum() / max(m[f"p{pct}_days"].sum(), 1), 1)
    null_path = directory / "metodo_simulacao_nula.parquet"
    if null_path.exists():
        null = pd.read_parquet(null_path)
        out["simulacao_nula"] = {
            "series": int(len(null)),
            "taxa_alerta_pct": {str(k): {"mediana": _r(100 * null[f"rate_pos_{k}"].median(), 3),
                                         "min": _r(100 * null[f"rate_pos_{k}"].min(), 3),
                                         "max": _r(100 * null[f"rate_pos_{k}"].max(), 3)} for k in THRESHOLDS},
            "por_forma_gama": {str(s): _r(100 * g["rate_pos_3.0"].median(), 3) for s, g in null.groupby("shape")},
        }
    return out


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def build_report(directory: Path, out: Path) -> dict:
    out = Path(out)
    (out / "tabelas").mkdir(parents=True, exist_ok=True)
    (out / "figuras").mkdir(parents=True, exist_ok=True)
    svc = AnalysisService(directory)
    svc.ensure_loaded()
    plt = _plt()
    import geopandas as gpd

    mesh_path = Path(directory) / "malha_simplificada.parquet"
    mesh = gpd.read_parquet(mesh_path) if mesh_path.exists() else None
    names = svc.municipalities[["codigo_ibge", "nome", "uf", "regiao"]]

    summary: dict = {"analysis_version": ANALYSIS_VERSION, "snapshot": svc.metadata, "min_eventos": MIN_EVENTS}
    exposure = svc.exposure.groupby(["variable_family", "codigo_ibge"])["days"].sum()
    summary["cobertura"] = {
        fam: {"municipios": int(len(g)), "dias_validos_min": int(g.min()), "dias_validos_mediana": _r(g.median(), 0),
              "dias_validos_max": int(g.max())}
        for fam, g in exposure.groupby(level=0)
    }
    summary["municipios_cadastrados"] = int(len(svc.municipalities))

    seasonal: dict = {}
    pooled_all, patterns_all = [], []
    dominant_maps = {}
    for variable in svc.available_variables():
        for event_class in ("todas", "extremos") + (("impacto",) if variable == "precipitacao" else ()):
            f = Filters(variable=variable, event_class=event_class)
            log.info("relatório: %s / %s", variable, event_class)
            block = seasonal_block(svc, f)
            key = f"{variable}|{event_class}"
            seasonal[key] = block["summary"]
            conc = block["conc"]
            cols = ["codigo_ibge", "nome", "uf", "regiao", "n_events", "days"] + [f"share_norm_{s}" for s in SEASONS] + [
                f"rate_{s}" for s in SEASONS] + ["autumn_winter_share", "concentration", "dominant_season", "chi2_pvalue",
                                                 "chi2_qvalue", "pattern"]
            conc[cols].to_csv(out / "tabelas" / f"municipios_{variable}_{event_class}.csv", index=False)
            pooled_all.append(block["pooled"].assign(variable=variable, event_class=event_class))
            dist = pd.DataFrame([{"regiao": r, **v["padroes_pct"]} for r, v in block["summary"]["por_regiao"].items()])
            patterns_all.append(dist.assign(variable=variable, event_class=event_class))
            if event_class == "todas":
                dominant_maps[variable] = conc
    summary["sazonal"] = seasonal
    pooled_all = pd.concat(pooled_all, ignore_index=True)
    pooled_all.to_csv(out / "tabelas" / "participacao_sazonal_regioes.csv", index=False)
    pd.concat(patterns_all, ignore_index=True).to_csv(out / "tabelas" / "padroes_por_regiao.csv", index=False)

    # ---- ENSO ------------------------------------------------------------
    enso_frames = []
    summary["enso"] = {}
    for variable in svc.available_variables():
        f = Filters(variable=variable, event_class="todas")
        frame = enso_block(svc, f).assign(variable=variable)
        enso_frames.append(frame)
        nat = frame[(frame["regiao"] == "Brasil") & (frame["enso_phase"] != "neutro")]
        summary["enso"][variable] = {
            f"{r.enso_phase}|{r.season}": {"razao": _r(r.ratio_vs_neutral, 3), "ic95": [_r(r.ratio_ci_low, 3), _r(r.ratio_ci_high, 3)],
                                           "n": int(r.n), "dias": int(r.days)}
            for r in nat.itertuples()
        }
    enso = pd.concat(enso_frames, ignore_index=True)
    enso.to_csv(out / "tabelas" / "enso_regiao_estacao.csv", index=False)
    phase_months = svc.enso.groupby("phase_episode").size().to_dict()
    summary["enso_meses_por_fase_2015_2025"] = {k: int(v) for k, v in phase_months.items()}
    scored = svc.enso[svc.enso["year"] >= 2017].groupby("phase_episode").size().to_dict()
    summary["enso_meses_por_fase_2017_2025"] = {k: int(v) for k, v in scored.items()}

    summary["classes"] = classes_block(Path(directory))
    summary["metodo"] = method_block(Path(directory))

    # ---- Figuras ---------------------------------------------------------
    figures = []
    pattern_categories = {
        "predominio_verao": ("Verão", SEASON_COLORS["verao"]),
        "predominio_outono": ("Outono", SEASON_COLORS["outono"]),
        "predominio_inverno": ("Inverno", SEASON_COLORS["inverno"]),
        "predominio_primavera": ("Primavera", SEASON_COLORS["primavera"]),
        "sem_predominio": ("Sem predomínio (q ≥ 0,05)", NEUTRAL),
    }
    if mesh is not None:
        # 1. estação predominante, uma por variável (pequenos múltiplos)
        variables = list(dominant_maps)
        ncols = 3 if len(variables) > 2 else len(variables)
        nrows = int(np.ceil(len(variables) / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 5.4 * nrows))
        axes = np.atleast_1d(axes).ravel()
        for ax, variable in zip(axes, variables):
            gdf = mesh.merge(dominant_maps[variable][["codigo_ibge", "pattern", "n_events"]], on="codigo_ibge",
                             how="left")
            _map_axes(plt, ax, gdf, "pattern", None, categories=pattern_categories,
                      title=VARIABLES[variable]["label"], legend_title="Estação predominante")
        for ax in axes[len(variables):]:
            ax.set_axis_off()
        fig.suptitle("Estação com maior frequência de eventos (qui-quadrado, FDR q < 0,05) — 2017–2025",
                     x=0.01, ha="left", fontsize=11)
        path = out / "figuras" / "mapa_estacao_predominante.png"
        fig.savefig(path)
        plt.close(fig)
        figures.append(path.name)

        # 2. participação outono+inverno (chuva), divergente em 50%
        for variable in variables:
            gdf = mesh.merge(dominant_maps[variable][["codigo_ibge", "autumn_winter_share", "n_events"]],
                             on="codigo_ibge", how="left")
            gdf["valor"] = np.where(gdf["n_events"] >= MIN_EVENTS, 100 * gdf["autumn_winter_share"], np.nan)
            fig, ax = plt.subplots(figsize=(6.5, 7.5))
            _map_axes(plt, ax, gdf, "valor", DIVERGING, breaks=[30, 40, 45, 55, 60, 70],
                      title=f"Participação de outono + inverno — {VARIABLES[variable]['label']}",
                      legend_title="% da frequência anual\n(50% = sem preferência)")
            poa = gdf[gdf["codigo_ibge"] == POA]
            if not poa.empty:
                point = poa.geometry.iloc[0].representative_point()
                ax.annotate("Porto Alegre", (point.x, point.y), xytext=(point.x + 4, point.y - 3), fontsize=7,
                            color=INK, arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.6})
            path = out / "figuras" / f"mapa_outono_inverno_{variable}.png"
            fig.savefig(path)
            plt.close(fig)
            figures.append(path.name)

        # 3. frequência de eventos de chuva (taxa)
        f = Filters("precipitacao", "todas")
        choro = pd.DataFrame(svc.choropleth("taxa", f)["values"])
        gdf = mesh.merge(choro[["codigo_ibge", "value", "n"]].rename(columns={"n": "n_events"}), on="codigo_ibge",
                         how="left")
        breaks = [round(float(q), 1) for q in gdf["value"].quantile([1 / 7 * i for i in range(1, 7)])]
        fig, ax = plt.subplots(figsize=(6.5, 6.5))
        _map_axes(plt, ax, gdf, "value", SEQUENTIAL, breaks=breaks,
                  title="Frequência de anomalias de chuva (Z > 3 ou acumulado ≥ P99)",
                  legend_title="eventos por 1.000 dias válidos")
        path = out / "figuras" / "mapa_taxa_chuva.png"
        fig.savefig(path)
        plt.close(fig)
        figures.append(path.name)

    # 4. barras por região (chuva e demais variáveis)
    for variable in svc.available_variables():
        pooled = pooled_all[(pooled_all["variable"] == variable) & (pooled_all["event_class"] == "todas")]
        pooled = pooled.rename(columns={"regiao": "grupo"})
        fig, ax = plt.subplots(figsize=(7.5, 3.4))
        _season_bars(plt, ax, pooled, REGIONS + ["Brasil"], f"{VARIABLES[variable]['label']}: participação por estação")
        ax.legend(ncol=5, fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12))
        path = out / "figuras" / f"barras_regioes_{variable}.png"
        fig.savefig(path)
        plt.close(fig)
        figures.append(path.name)

    # 5. ENSO: razão de taxas por região × estação (chuva), com IC 95%
    for variable in ("precipitacao",):
        frame = enso[(enso["variable"] == variable) & (enso["enso_phase"] != "neutro")]
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
        for ax, phase in zip(axes, ("el_nino", "la_nina")):
            part = frame[frame["enso_phase"] == phase]
            groups = REGIONS + ["Brasil"]
            for i, season in enumerate(SEASONS):
                rows = part[part["season"] == season].set_index("regiao").reindex(groups)
                x = np.arange(len(groups)) + (i - 1.5) * 0.18
                y = rows["ratio_vs_neutral"].to_numpy(dtype=float)
                low = rows["ratio_ci_low"].to_numpy(dtype=float)
                high = rows["ratio_ci_high"].to_numpy(dtype=float)
                ax.errorbar(x, y, yerr=[y - low, high - y], fmt="o", ms=4, color=SEASON_COLORS[season],
                            elinewidth=1, label=SEASON_LABELS[season])
            ax.axhline(1, color=INK_2, linewidth=0.8, linestyle="--")
            ax.set_yscale("log")
            from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter

            ax.yaxis.set_major_locator(FixedLocator([0.5, 0.67, 1, 1.5, 2, 3]))
            ax.yaxis.set_major_formatter(ScalarFormatter())
            ax.yaxis.set_minor_formatter(NullFormatter())
            ax.set_xticks(np.arange(len(groups)), groups, fontsize=7)
            ax.set_title(f"{ENSO_LABELS[phase]} / neutro", loc="left")
            ax.grid(axis="y", color=GRID, linewidth=0.5)
        axes[0].set_ylabel("razão de frequência (escala log)")
        fig.suptitle("EXPLORATÓRIO — 2 a 3 episódios por fase; IC 95% supõem eventos independentes entre municípios "
                     "(estreitos demais)", x=0.01, ha="left", fontsize=8, color=INK_2)
        axes[0].legend(ncol=4, fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12))
        path = out / "figuras" / f"enso_razao_{variable}.png"
        fig.savefig(path)
        plt.close(fig)
        figures.append(path.name)

    # 6. avaliação do método: participação sazonal dos alertas com σ único × σ sazonal
    if summary["metodo"]:
        m = summary["metodo"]
        fig, ax = plt.subplots(figsize=(6, 3))
        x = np.arange(len(SEASONS))
        for i, (kind, label, color) in enumerate(
            (("global", "σ único (detector atual)", "#256abf"), ("seasonal", "σ por estação (anos anteriores)", "#eb6834"))
        ):
            values = [m[f"alertas_sigma_{kind}"]["participacao_norm_pct"][s] for s in SEASONS]
            ax.bar(x + (i - 0.5) * 0.36, values, 0.33, color=color, label=label)
        ax.axhline(25, color=INK_2, linewidth=0.8, linestyle="--")
        ax.set_xticks(x, [SEASON_LABELS[s] for s in SEASONS])
        ax.set_ylabel("participação dos alertas Z > 3 (%)")
        ax.set_title(f"Alertas de chuva por estação, amostra de {m['municipios']} municípios", loc="left")
        ax.legend(fontsize=7, frameon=False)
        ax.grid(axis="y", color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)
        path = out / "figuras" / "metodo_sigma_sazonal.png"
        fig.savefig(path)
        plt.close(fig)
        figures.append(path.name)

    summary["figuras"] = figures
    (out / "resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return {k: summary[k] for k in ("cobertura", "classes") if k in summary} | {
        "porto_alegre": {k: v["porto_alegre"] for k, v in seasonal.items()},
        "brasil": {k: v["por_regiao"]["Brasil"] for k, v in seasonal.items()},
        "figuras": figures,
    }
