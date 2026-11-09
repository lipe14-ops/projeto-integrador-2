"""Fixtures compartilhadas: séries sintéticas, HTTP falso e banco de teste.

Os testes de banco usam um banco separado (``<banco>_test``) no mesmo
servidor PostgreSQL/PostGIS; ele é recriado a cada sessão de testes. Se o
servidor não estiver acessível, esses testes são pulados.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.climate_news.news.http import FetchResult

# ---------------------------------------------------------------------------
# Séries sintéticas
# ---------------------------------------------------------------------------


def synthetic_rain(
    start: str = "2015-01-01",
    years: int = 5,
    seed: int = 7,
    wet_base: float = 0.35,
    wet_amp: float = 0.25,
    mean_amp: float = 0.6,
    mean_mm: float = 8.0,
) -> pd.Series:
    """Chuva diária com sazonalidade anual em frequência e intensidade."""
    rng = np.random.default_rng(seed)
    index = pd.date_range(start, periods=int(365.25 * years), freq="D")
    phase = 2 * np.pi * (index.dayofyear.to_numpy() - 15) / 365.25
    p_wet = np.clip(wet_base + wet_amp * np.cos(phase), 0.02, 0.95)
    scale = mean_mm * (1 + mean_amp * np.cos(phase))
    wet = rng.random(len(index)) < p_wet
    amount = rng.gamma(0.8, np.maximum(scale, 0.5) / 0.8)
    return pd.Series(np.where(wet, amount, 0.0).round(2), index=index, name="precipitation_mm")


def as_frame(series: pd.Series) -> pd.DataFrame:
    return series.rename("precipitation_mm").rename_axis("date").reset_index()


# ---------------------------------------------------------------------------
# HTTP falso
# ---------------------------------------------------------------------------


def article_html(
    title: str,
    body: str,
    published: str | None = "2024-05-02T10:00:00-03:00",
    site: str = "G1",
    canonical: str | None = None,
) -> str:
    date_meta = f'<meta property="article:published_time" content="{published}">' if published else ""
    canonical_tag = f'<link rel="canonical" href="{canonical}">' if canonical else ""
    paragraphs = "".join(f"<p>{p}</p>" for p in body.split("\n"))
    return f"""<html><head><title>{title} | {site}</title>
    <meta property="og:title" content="{title}"><meta property="og:site_name" content="{site}">
    {date_meta}{canonical_tag}</head><body><article><h1>{title}</h1>{paragraphs}</article></body></html>"""


class FakeHttpClient:
    """Responde a partir de um dicionário url -> (status, html) e registra chamadas."""

    def __init__(self, pages: dict[str, tuple[int | None, str | None]]):
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str, **_) -> FetchResult:
        self.calls.append(url)
        status, content = self.pages.get(url, (404, "not found"))
        error = None if status else "ConnectError: falha de rede"
        return FetchResult(url, url if status else None, status, content if status else None, error, 0.01, 1)


@pytest.fixture
def utc():
    return lambda *a: datetime(*a, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Banco de teste
# ---------------------------------------------------------------------------


def _test_database_url() -> str:
    from app.database import DATABASE_URL

    url = make_url(os.getenv("TEST_DATABASE_URL", DATABASE_URL))
    if not url.database.endswith("_test"):
        url = url.set(database=f"{url.database}_test")
    return url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def db_engine():
    url = make_url(_test_database_url())
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponível para testes: {error}")
    finally:
        admin.dispose()

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    import app.climate_news.models  # noqa: F401
    import app.models.enso_mensal  # noqa: F401
    import app.models.municipio  # noqa: F401
    import app.models.municipio_details  # noqa: F401
    import app.models.registro_climatico  # noqa: F401
    from app.database import Base

    Base.metadata.create_all(engine)
    square = "ST_GeomFromText('MULTIPOLYGON(((0 0,1 0,1 1,0 1,0 0)))', 4326)"
    neighbor = "ST_GeomFromText('MULTIPOLYGON(((1 0,2 0,2 1,1 1,1 0)))', 4326)"
    far = "ST_GeomFromText('MULTIPOLYGON(((10 10,11 10,11 11,10 11,10 10)))', 4326)"
    with engine.begin() as conn:
        for code, geom, name, uf, state, region in (
            (4314902, square, "Porto Alegre", "RS", "Rio Grande do Sul", "Sul"),
            (4304606, neighbor, "Canoas", "RS", "Rio Grande do Sul", "Sul"),
            (5218805, far, "Rio Verde", "GO", "Goiás", "Centro-Oeste"),
        ):
            conn.execute(text(f"INSERT INTO municipio (codigo_ibge, geometry) VALUES ({code}, {geom})"))
            conn.execute(
                text(
                    "INSERT INTO municipio_details (codigo_ibge, municipio, uf, estado, regiao, populacao) "
                    "VALUES (:c, :n, :u, :s, :r, 1000)"
                ),
                {"c": code, "n": name, "u": uf, "s": state, "r": region},
            )
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    yield factory
    with db_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE news_verification_attempt, anomaly_news, news_investigation, "
                "news_article, precipitation_anomaly, pipeline_run CASCADE"
            )
        )
