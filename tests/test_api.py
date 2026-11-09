"""API REST /api/climate/news (banco de teste)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.climate_news.models import AnomalyNews, NewsArticle, PipelineRun, PrecipitationAnomaly
from app.database import get_db
from app.main import app

pytestmark = pytest.mark.db


@pytest.fixture
def client(session_factory):
    def override():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def data(session_factory):
    """3 anomalias em Porto Alegre e 1 em Rio Verde, com notícias:

    - n1: verificada, ligada a 2024-05-01 e 2024-05-02 (mais de uma anomalia)
    - n2: verificada, ligada a 2024-05-01 (várias notícias na mesma anomalia)
    - n3: verificada, ligada a 2023-09-04
    - n4: rejeitada, ligada a 2024-05-01
    - n5: verificada para Rio Verde 2024-01-10
    """
    with session_factory() as db:
        run = PipelineRun(id=uuid.uuid4(), run_type="detection", status="completed", algorithm_version="t",
                          municipality="Porto Alegre", uf="RS", finished_at=datetime.now(timezone.utc))
        db.add(run)

        run_rv = PipelineRun(id=uuid.uuid4(), run_type="detection", status="completed", algorithm_version="t",
                             municipality="Rio Verde", uf="GO", finished_at=datetime.now(timezone.utc))
        db.add(run_rv)

        def anomaly(day, place="Porto Alegre", uf="RS", code=4314902):
            a = PrecipitationAnomaly(id=uuid.uuid4(), run_id=run.id if place == "Porto Alegre" else run_rv.id, codigo_ibge=code, municipality=place, uf=uf,
                                     anomaly_date=day, observed_mm=80.0, predicted_mm=2.0, residual=3.2, z_score=3.5,
                                     direction="positive", classification="statistical_anomaly_above_expected",
                                     status="scientifically_reviewed",
                                     scientific_review={"reviews": [{"agent": "climatologist", "verdict": "x",
                                                                     "metrics": {"enso_phase": "el_nino", "oni": 1.2}}]})
            db.add(a)
            return a

        a1, a2, a3 = anomaly(date(2024, 5, 1)), anomaly(date(2024, 5, 2)), anomaly(date(2023, 9, 4))
        a4 = anomaly(date(2024, 1, 10), "Rio Verde", "GO", 5218805)

        def news(n, status, published, source="G1"):
            item = NewsArticle(
                id=uuid.uuid4(), url=f"https://g1.globo.com/rs/noticia/{n}", original_url=f"https://g1.globo.com/rs/noticia/{n}",
                headline=f"Notícia {n}", source=source, source_domain="g1.globo.com", published_at=published,
                verification_status=status, verification_evidence={"checks": {}},
                verified_by="fact_checker" if status == "verified" else None,
            )
            db.add(item)
            return item

        def ts(*a):
            return datetime(*a, tzinfo=timezone.utc)

        n1 = news("n1", "verified", ts(2024, 5, 3, 12))
        n2 = news("n2", "verified", ts(2024, 5, 1, 18), source="Agência Brasil")
        n3 = news("n3", "verified", ts(2023, 9, 5, 9))
        n4 = news("n4", "rejected", ts(2024, 5, 2, 9))
        n5 = news("n5", "verified", ts(2024, 1, 11, 9))
        db.flush()

        def link(a, n, status="verified", relevance="relevant"):
            db.add(AnomalyNews(anomaly_id=a.id, news_id=n.id, relevance_status=relevance, link_status=status,
                               municipality_match="target", event_date=a.anomaly_date, decision={}))

        link(a1, n1)
        link(a2, n1)
        link(a1, n2)
        link(a3, n3)
        link(a1, n4, "rejected", "not_relevant")
        link(a4, n5)
        db.commit()
    return {"n1": str(n1.id), "n2": str(n2.id), "n3": str(n3.id), "n4": str(n4.id)}


URL = "/api/climate/news"


def test_valid_interval_returns_only_verified(client, data):
    body = client.get(URL, params={"start_date": "2024-01-01", "end_date": "2024-12-31", "municipality": "Porto Alegre"}).json()
    ids = {n["id"] for n in body["news"]}
    assert ids == {data["n1"], data["n2"]}
    assert body["total"] == 2
    assert all(n["verification_status"] == "verified" for n in body["news"])
    assert body["period"] == {"start_date": "2024-01-01", "end_date": "2024-12-31"}


def test_filter_uses_anomaly_date_not_publication_date(client, data):
    # n1 foi publicada em 03/05, mas suas anomalias são 01/05 e 02/05
    body = client.get(URL, params={"start_date": "2024-05-03", "end_date": "2024-05-31"}).json()
    assert body["total"] == 0
    body = client.get(URL, params={"start_date": "2024-05-02", "end_date": "2024-05-02"}).json()
    assert [n["id"] for n in body["news"]] == [data["n1"]]
    assert body["news"][0]["published_at"].startswith("2024-05-03")
    assert body["news"][0]["anomaly_date"] == "2024-05-02"


def test_interval_without_news(client, data):
    body = client.get(URL, params={"start_date": "2020-01-01", "end_date": "2020-12-31"}).json()
    assert body["total"] == 0 and body["news"] == [] and body["pages"] == 0


def test_start_after_end_is_422(client, data):
    response = client.get(URL, params={"start_date": "2024-12-31", "end_date": "2024-01-01"})
    assert response.status_code == 422


def test_invalid_date_is_422(client, data):
    assert client.get(URL, params={"start_date": "2024-13-01", "end_date": "2024-12-31"}).status_code == 422


def test_unknown_municipality_is_404(client, data):
    response = client.get(URL, params={"start_date": "2024-01-01", "end_date": "2024-12-31", "municipality": "Atlântida do Norte"})
    assert response.status_code == 404


def test_pagination(client, data):
    params = {"start_date": "2023-01-01", "end_date": "2024-12-31", "municipality": "porto alegre", "limit": 2}
    first = client.get(URL, params=params).json()
    second = client.get(URL, params={**params, "page": 2}).json()
    assert first["total"] == 3 and first["pages"] == 2
    assert len(first["news"]) == 2 and len(second["news"]) == 1
    assert not {n["id"] for n in first["news"]} & {n["id"] for n in second["news"]}


def test_multiple_news_for_same_anomaly(client, data):
    body = client.get(URL, params={"start_date": "2024-05-01", "end_date": "2024-05-01"}).json()
    assert {n["id"] for n in body["news"]} == {data["n1"], data["n2"]}


def test_news_associated_with_more_than_one_anomaly_appears_once(client, data):
    body = client.get(URL, params={"start_date": "2024-05-01", "end_date": "2024-05-02"}).json()
    n1 = [n for n in body["news"] if n["id"] == data["n1"]]
    assert len(n1) == 1
    assert [a["anomaly_date"] for a in n1[0]["related_anomalies"]] == ["2024-05-01", "2024-05-02"]
    assert n1[0]["anomaly_date"] == "2024-05-01"


def test_rejected_news_never_returned_as_verified(client, data):
    default = client.get(URL, params={"start_date": "2024-05-01", "end_date": "2024-05-02"}).json()
    assert data["n4"] not in {n["id"] for n in default["news"]}
    rejected = client.get(URL, params={"start_date": "2024-05-01", "end_date": "2024-05-02", "verification_status": "rejected"}).json()
    assert [n["id"] for n in rejected["news"]] == [data["n4"]]
    assert rejected["news"][0]["verification_status"] == "rejected"


def test_combined_filters_and_sorting(client, data):
    params = {"start_date": "2023-01-01", "end_date": "2024-12-31", "source": "agência", "municipality": "Porto Alegre"}
    assert [n["id"] for n in client.get(URL, params=params).json()["news"]] == [data["n2"]]
    asc = client.get(URL, params={"start_date": "2023-01-01", "end_date": "2024-12-31", "uf": "RS",
                                   "sort_by": "published_at", "order": "asc"}).json()
    published = [n["published_at"] for n in asc["news"]]
    assert published == sorted(published)


def test_vite_proxy_alias_and_openapi(client, data):
    assert client.get("/climate/news", params={"start_date": "2024-01-01", "end_date": "2024-12-31"}).status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/api/climate/news" in spec["paths"]
    assert "/climate/news" not in spec["paths"]


def test_anomalies_endpoint_counts_verified_news(client, data):
    body = client.get("/api/climate/anomalies", params={"start_date": "2024-05-01", "end_date": "2024-05-02",
                                                       "municipality": "Porto Alegre"}).json()
    counts = {a["anomaly_date"]: a["verified_news"] for a in body["anomalies"]}
    assert counts == {"2024-05-01": 2, "2024-05-02": 1}
    assert {"climate_assessment", "weather_assessment", "accumulation_days", "peak_daily_mm"} <= body["anomalies"][0].keys()
    assert all(a["news_investigated"] is False for a in body["anomalies"])  # nenhuma investigação no cenário


def test_analyzed_municipalities(client, data):
    body = client.get("/api/climate/municipalities").json()
    by_name = {m["municipality"]: m for m in body}
    assert set(by_name) == {"Porto Alegre", "Rio Verde"}
    assert by_name["Porto Alegre"]["anomalies"] == 3
    assert by_name["Porto Alegre"]["verified_news"] == 3  # n1, n2, n3 (n4 rejeitada)
    assert by_name["Rio Verde"]["verified_news"] == 1


def test_related_anomalies_expose_accumulation_days(client, data):
    body = client.get(URL, params={"start_date": "2024-05-01", "end_date": "2024-05-02"}).json()
    assert "accumulation_days" in body["news"][0]["related_anomalies"][0]


def test_analyzed_municipalities_counts_only_latest_detection(client, data, session_factory):
    with session_factory() as db:
        old = PipelineRun(id=uuid.uuid4(), run_type="detection", status="completed", algorithm_version="t",
                          municipality="Porto Alegre", uf="RS", finished_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
        db.add(old)
        db.add(PrecipitationAnomaly(id=uuid.uuid4(), run_id=old.id, codigo_ibge=4314902, municipality="Porto Alegre",
                                    uf="RS", anomaly_date=date(2019, 1, 1), observed_mm=50, direction="positive",
                                    classification="x", status="scientifically_reviewed"))
        db.commit()
    by_name = {m["municipality"]: m for m in client.get("/api/climate/municipalities").json()}
    assert by_name["Porto Alegre"]["anomalies"] == 3  # a detecção antiga não entra


def test_related_anomalies_expose_enso_phase(client, data):
    body = client.get(URL, params={"start_date": "2024-05-01", "end_date": "2024-05-02"}).json()
    related = body["news"][0]["related_anomalies"][0]
    assert related["enso_phase"] == "el_nino" and related["oni"] == 1.2


def test_analyzed_municipalities_follow_period_and_source_filters(client, data):
    by_name = {m["municipality"]: m for m in client.get(
        "/api/climate/municipalities", params={"start_date": "2024-01-01", "end_date": "2024-12-31"}).json()}
    assert by_name["Porto Alegre"]["verified_news"] == 2  # n3 é de 2023
    assert by_name["Porto Alegre"]["anomalies"] == 2
    by_name = {m["municipality"]: m for m in client.get("/api/climate/municipalities", params={"source": "agência"}).json()}
    assert by_name["Porto Alegre"]["verified_news"] == 1
    assert "latitude" in by_name["Porto Alegre"]
