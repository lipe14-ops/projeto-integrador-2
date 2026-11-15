"""Extração reprodutível do banco para a análise espacial e sazonal.

O banco tem ~315 mil anomalias de chuva e 46 milhões de registros de 12 h; as
agregações nacionais levam dezenas de segundos (chuva) a ~20 minutos
(temperatura/umidade). Por isso a análise lê um *snapshot* em Parquet,
gerado por linha de comando e acompanhado de metadados (data, contagens,
SHA-256 de cada arquivo). A API e o relatório leem o mesmo snapshot: os
números do mapa e do relatório são os mesmos.

Arquivos em ``data/analise/`` (fora do Git, como os demais dados):

- ``municipios.parquet``: código IBGE, nome, UF, região, centróide
- ``enso.parquet``: ONI mensal, fase mensal (limiar) e fase por episódio (NOAA)
- ``precipitacao_anomalias.parquet``: anomalias da última detecção concluída
  de cada município + classe operacional (``classification.py``)
- ``precipitacao_exposicao.parquet``: dias válidos por município/ano/mês dentro
  do período pontuado pela detecção
- ``termica_anomalias.parquet``/``termica_exposicao.parquet``/
  ``termica_diagnosticos.parquet``: temperatura e umidade (``thermal.py``)
- ``metadata.json``
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.climate_news.analysis import ANALYSIS_VERSION
from app.climate_news.analysis.classification import classify_precipitation, classify_thermal
from app.climate_news.analysis.seasons import enso_episodes
from app.climate_news.analysis.thermal import VARIABLES, ThermalConfig, detect_thermal_anomalies

log = logging.getLogger("climate_news.analysis")

DEFAULT_DIR = Path(os.getenv("ANALYSIS_SNAPSHOT_DIR", Path(__file__).resolve().parents[3] / "data" / "analise"))

_LATEST_RUNS = """
    SELECT DISTINCT ON (municipality, uf) id, codigo_ibge,
           (summary->'scored_period'->>0)::date AS scored_start,
           (summary->'scored_period'->>1)::date AS scored_end
    FROM pipeline_run
    WHERE run_type = 'detection' AND status = 'completed'
    ORDER BY municipality, uf, finished_at DESC
"""

_PRECIP_ANOMALIES = f"""
    WITH latest AS ({_LATEST_RUNS}),
    news AS (
        SELECT l.anomaly_id, count(*) AS n
        FROM anomaly_news l JOIN news_article n ON n.id = l.news_id
        WHERE l.link_status = 'verified' AND n.verification_status = 'verified'
        GROUP BY l.anomaly_id
    )
    SELECT a.codigo_ibge, a.anomaly_date, a.detector, a.direction, a.status, a.severity,
           a.z_score, a.observed_mm, a.predicted_mm, a.residual, (a.scientific_review->>'residual_mm')::float AS residual_mm,
           (SELECT r->>'verdict' FROM jsonb_array_elements(a.scientific_review->'reviews') r
             WHERE r->>'agent' = 'data_scientist') AS data_verdict,
           (SELECT r->>'verdict' FROM jsonb_array_elements(a.scientific_review->'reviews') r
             WHERE r->>'agent' = 'climatologist') AS climate_verdict,
           (SELECT r->>'verdict' FROM jsonb_array_elements(a.scientific_review->'reviews') r
             WHERE r->>'agent' = 'meteorologist') AS weather_verdict,
           (a.scientific_review->'details'->>'window_days')::int AS window_days,
           coalesce(news.n, 0) AS verified_news,
           EXISTS (SELECT 1 FROM news_investigation ni
                   WHERE ni.anomaly_id = a.id AND ni.status = 'completed') AS news_investigated,
           -- entrada completa? ARIMA: dia anterior válido (senão a previsão é de dois passos);
           -- acumulado: todos os dias da janela válidos (senão a soma é extrapolada por k/(k−1))
           (SELECT count(*) FROM precipitacao_diaria d
             WHERE d.codigo_ibge = a.codigo_ibge AND d.n_metades = 2 AND d.precipitacao IS NOT NULL
               AND d.dia BETWEEN a.anomaly_date - CASE WHEN a.detector = 'arima_zscore' THEN 1
                     ELSE coalesce((a.scientific_review->'details'->>'window_days')::int, 1) - 1 END
                 AND a.anomaly_date)
             = CASE WHEN a.detector = 'arima_zscore' THEN 2
                    ELSE coalesce((a.scientific_review->'details'->>'window_days')::int, 1) END
             AS complete_input
    FROM precipitation_anomaly a
    JOIN latest ON latest.id = a.run_id
    LEFT JOIN news ON news.anomaly_id = a.id
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(frame: pd.DataFrame, directory: Path, name: str) -> dict:
    path = directory / f"{name}.parquet"
    frame.to_parquet(path, index=False)
    return {"rows": int(len(frame)), "sha256": _sha256(path)}


def _update_metadata(directory: Path, section: str, content: dict) -> None:
    path = directory / "metadata.json"
    metadata = json.loads(path.read_text()) if path.exists() else {}
    metadata["analysis_version"] = ANALYSIS_VERSION
    metadata[section] = {"generated_at": datetime.now(timezone.utc).isoformat(), **content}
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))


# ---------------------------------------------------------------------------
# Municípios, ENSO e chuva
# ---------------------------------------------------------------------------


def load_municipalities(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        text(
            """
            SELECT m.codigo_ibge, d.municipio AS nome, d.uf, d.regiao, m.latitude, m.longitude
            FROM municipio m LEFT JOIN municipio_details d USING (codigo_ibge)
            ORDER BY m.codigo_ibge
            """
        ),
        engine,
    )


def load_enso_frame(engine: Engine) -> pd.DataFrame:
    frame = pd.read_sql(text("SELECT year, month, enso_index AS oni FROM enso_mensal ORDER BY year, month"), engine)
    oni = {(int(r.year), int(r.month)): r.oni for r in frame.itertuples() if pd.notna(r.oni)}
    episodes = enso_episodes(oni)
    frame["phase_episode"] = [episodes.get((int(y), int(m)), "neutro") for y, m in zip(frame.year, frame.month)]
    frame["phase_monthly"] = np.select(
        [frame.oni >= 0.5, frame.oni <= -0.5], ["el_nino", "la_nina"], default="neutro"
    )
    return frame


def classify_precipitation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    classes = [
        classify_precipitation(r.detector, r.direction, r.data_verdict, r.climate_verdict, r.weather_verdict,
                               int(r.verified_news), bool(getattr(r, "complete_input", True)))
        for r in frame.itertuples()
    ]
    out = frame.copy()
    out["event_class"] = [c.event_class for c in classes]
    out["level"] = [c.level for c in classes]
    out["is_extreme"] = [c.is_extreme for c in classes]
    out["high_intensity"] = [c.high_absolute_intensity for c in classes]
    out["documented_impact"] = [c.documented_impact for c in classes]
    out["counted"] = [c.counted for c in classes]
    return out


def build_precipitation_snapshot(engine: Engine, directory: Path = DEFAULT_DIR) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    municipalities = load_municipalities(engine)
    enso = load_enso_frame(engine)
    runs = pd.read_sql(text(_LATEST_RUNS), engine)
    anomalies = pd.read_sql(text(_PRECIP_ANOMALIES), engine)
    anomalies["anomaly_date"] = pd.to_datetime(anomalies["anomaly_date"])
    anomalies = classify_precipitation_frame(anomalies)

    exposure = pd.read_sql(
        text(
            """
            WITH d AS (
                SELECT codigo_ibge, dia, (n_metades = 2 AND precipitacao IS NOT NULL) AS ok,
                       lag(n_metades = 2 AND precipitacao IS NOT NULL)
                           OVER (PARTITION BY codigo_ibge ORDER BY dia) AS ok_before
                FROM precipitacao_diaria
            )
            -- dia pontuável = válido e com o dia anterior válido (mesma regra de complete_input)
            SELECT codigo_ibge, extract(year FROM dia)::int AS year, extract(month FROM dia)::int AS month,
                   count(*) FILTER (WHERE ok AND coalesce(ok_before, false)) AS valid_days
            FROM d GROUP BY 1, 2, 3
            """
        ),
        engine,
    )
    # mantém só os meses dentro do período pontuado pela detecção de cada município
    exposure = exposure.merge(runs[["codigo_ibge", "scored_start", "scored_end"]], on="codigo_ibge", how="inner")
    month_start = pd.to_datetime(dict(year=exposure.year, month=exposure.month, day=1))
    inside = (month_start >= pd.to_datetime(exposure.scored_start).dt.to_period("M").dt.to_timestamp()) & (
        month_start <= pd.to_datetime(exposure.scored_end)
    )
    exposure = exposure.loc[inside, ["codigo_ibge", "year", "month", "valid_days"]].reset_index(drop=True)

    files = {
        "municipios": _write(municipalities, directory, "municipios"),
        "enso": _write(enso, directory, "enso"),
        "precipitacao_anomalias": _write(anomalies, directory, "precipitacao_anomalias"),
        "precipitacao_exposicao": _write(exposure, directory, "precipitacao_exposicao"),
    }
    with engine.connect() as conn:  # estimativa do PostgreSQL (pg_class), sem varrer a tabela
        records = conn.execute(
            text("SELECT reltuples::bigint FROM pg_class WHERE relname = 'registro_climatico'")
        ).scalar()
    content = {
        "source": "PostgreSQL: precipitation_anomaly (última detecção concluída por município), precipitacao_diaria",
        "climate_records": int(records or 0),
        "municipalities_with_data": int(exposure["codigo_ibge"].nunique()),
        "detection_runs": int(len(runs)),
        "municipalities_with_detection": int(runs.codigo_ibge.nunique()),
        "scored_periods": runs.groupby(["scored_start", "scored_end"]).size().rename("runs").reset_index()
        .astype(str).to_dict("records"),
        "files": files,
    }
    _update_metadata(directory, "precipitation", content)
    return content


# ---------------------------------------------------------------------------
# Temperatura e umidade (nacional)
# ---------------------------------------------------------------------------


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def daily_means(frame: pd.DataFrame) -> pd.DataFrame:
    """Média diária (dia UTC) de 00 e 12 UTC; dias com menos de 2 observações ficam NaN."""
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["datetime"], utc=True).dt.tz_localize(None).dt.normalize()
    grouped = frame.groupby(["codigo_ibge", "date"])
    means = grouped[list(VARIABLES)].mean()
    counts = grouped[list(VARIABLES)].count()
    return means.where(counts >= 2).reset_index()


def _thermal_for_range(database_url: str, low: int, high: int, config: ThermalConfig) -> tuple:
    import psycopg

    buffer = io.BytesIO()
    query = (
        "COPY (SELECT codigo_ibge, datetime, temperatura, umidade FROM registro_climatico "
        f"WHERE codigo_ibge BETWEEN {int(low)} AND {int(high)} ORDER BY codigo_ibge, datetime) TO STDOUT WITH CSV"
    )
    with psycopg.connect(_psycopg_url(database_url)) as conn, conn.cursor() as cursor:
        with cursor.copy(query) as copy:
            for chunk in copy:
                buffer.write(chunk)
    buffer.seek(0)
    raw = pd.read_csv(buffer, header=None, names=["codigo_ibge", "datetime", "temperatura", "umidade"])
    daily = daily_means(raw)
    anomalies, exposure, diagnostics, errors = [], [], [], []
    for codigo, group in daily.groupby("codigo_ibge"):
        series_frame = group.set_index("date")
        for variable in VARIABLES:
            series = series_frame[variable]
            if series.notna().sum() < config.min_train_days:
                errors.append({"codigo_ibge": codigo, "variable": variable, "error": "sem dados suficientes"})
                continue
            try:
                result = detect_thermal_anomalies(series, config)
            except Exception as error:  # noqa: BLE001 — registra e segue
                errors.append({"codigo_ibge": codigo, "variable": variable, "error": str(error)})
                continue
            for table, data in ((anomalies, result.anomalies), (exposure, result.exposure)):
                data = data.copy()
                data.insert(0, "variable", variable)
                data.insert(0, "codigo_ibge", codigo)
                table.append(data)
            diagnostics.append({"codigo_ibge": codigo, "variable": variable, **result.diagnostics})
    concat = lambda items: pd.concat(items, ignore_index=True) if items else pd.DataFrame()  # noqa: E731
    return concat(anomalies), concat(exposure), pd.DataFrame(diagnostics), errors


def build_thermal_snapshot(
    engine: Engine,
    directory: Path = DEFAULT_DIR,
    workers: int = 4,
    config: ThermalConfig | None = None,
    codes: list[int] | None = None,
) -> dict:
    """Roda o detector térmico em todos os municípios, por faixas de código IBGE (UF)."""
    config = config or ThermalConfig()
    directory.mkdir(parents=True, exist_ok=True)
    if codes:
        ranges = [(c, c) for c in sorted(set(codes))]
    else:
        prefixes = pd.read_sql(text("SELECT DISTINCT codigo_ibge / 100000 AS uf FROM municipio ORDER BY 1"), engine)
        ranges = [(int(p) * 100000, int(p) * 100000 + 99999) for p in prefixes.uf]
    url = engine.url.render_as_string(hide_password=False)
    parts_a, parts_e, parts_d, errors = [], [], [], []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_thermal_for_range, url, low, high, config): (low, high) for low, high in ranges}
        for done, future in enumerate(as_completed(futures), 1):
            low, high = futures[future]
            a, e, d, err = future.result()
            parts_a.append(a)
            parts_e.append(e)
            parts_d.append(d)
            errors += err
            log.info("térmica %d/%d: códigos %d–%d, %d anomalias", done, len(ranges), low, high, len(a))
    anomalies = pd.concat(parts_a, ignore_index=True)
    anomalies["date"] = pd.to_datetime(anomalies["date"])
    classes = [classify_thermal(p, d) for p, d in zip(anomalies["climate_percentile"], anomalies["direction"])]
    anomalies["event_class"] = [c.event_class for c in classes]
    anomalies["level"] = [c.level for c in classes]
    anomalies["is_extreme"] = [c.is_extreme for c in classes]
    exposure = pd.concat(parts_e, ignore_index=True)
    diagnostics = pd.concat(parts_d, ignore_index=True)
    files = {
        "termica_anomalias": _write(anomalies, directory, "termica_anomalias"),
        "termica_exposicao": _write(exposure, directory, "termica_exposicao"),
        "termica_diagnosticos": _write(diagnostics, directory, "termica_diagnosticos"),
    }
    content = {
        "source": "PostgreSQL: registro_climatico (ERA5-Land 00 e 12 UTC → média diária)",
        "config": config.__dict__,
        "municipalities": int(diagnostics.codigo_ibge.nunique()) if len(diagnostics) else 0,
        "errors": errors[:200],
        "n_errors": len(errors),
        "files": files,
    }
    _update_metadata(directory, "thermal", content)
    return content


# ---------------------------------------------------------------------------
# Malha municipal simplificada (mapas do relatório)
# ---------------------------------------------------------------------------

GEOMETRY_TOLERANCE = 0.01


def build_geometry_snapshot(engine: Engine, directory: Path = DEFAULT_DIR, tolerance: float = GEOMETRY_TOLERANCE) -> dict:
    """Malha IBGE simplificada (mesma tolerância da API ``/api/analysis/geometrias``)."""
    import geopandas as gpd

    directory.mkdir(parents=True, exist_ok=True)
    frame = gpd.read_postgis(
        text(
            "SELECT codigo_ibge, ST_SimplifyPreserveTopology(geometry, :tol) AS geometry "
            "FROM municipio WHERE geometry IS NOT NULL ORDER BY codigo_ibge"
        ),
        engine,
        geom_col="geometry",
        params={"tol": tolerance},
    )
    path = directory / "malha_simplificada.parquet"
    frame.to_parquet(path, index=False)
    content = {"rows": int(len(frame)), "tolerance_degrees": tolerance, "sha256": _sha256(path)}
    _update_metadata(directory, "geometry", content)
    return content


def reclassify_thermal(directory: Path = DEFAULT_DIR) -> dict:
    """Recalcula as classes térmicas do snapshot (sem refazer a detecção)."""
    path = directory / "termica_anomalias.parquet"
    anomalies = pd.read_parquet(path)
    before = anomalies["event_class"].value_counts().to_dict()
    classes = [classify_thermal(p, d) for p, d in zip(anomalies["climate_percentile"], anomalies["direction"])]
    anomalies["event_class"] = [c.event_class for c in classes]
    anomalies["level"] = [c.level for c in classes]
    anomalies["is_extreme"] = [c.is_extreme for c in classes]
    info = _write(anomalies, directory, "termica_anomalias")
    after = anomalies["event_class"].value_counts().to_dict()
    _update_metadata(directory, "thermal_reclassification", {"before": before, "after": after, "file": info})
    return {"before": before, "after": after}
