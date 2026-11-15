"""Validação da verificação automática de notícias com DADOS REAIS do banco.

Subcomandos (rodar a partir da raiz do projeto):

    uv run python -m scripts.amostra_validacao_noticias amostra [--n-por-estrato 10] [--semente 20261114]
    uv run python -m scripts.amostra_validacao_noticias estatisticas [--log ARQ]
    uv run python -m scripts.amostra_validacao_noticias metricas ARQUIVO_ANOTADO.csv [--amostra AMOSTRA.csv]
    uv run python -m scripts.amostra_validacao_noticias acessibilidade [--n 50] [--log ARQ]
    uv run python -m scripts.amostra_validacao_noticias impacto-jsonld [--n 40] [--log ARQ]

- ``amostra``: sorteio estratificado e reprodutível (semente fixa) dos vínculos
  anomalia × notícia por decisão do sistema (verified/rejected/pending) e por
  região; exporta o modelo de anotação (CSV completo) e uma versão cega, sem a
  decisão do sistema, para os anotadores.
- ``estatisticas``: estatísticas descritivas do pipeline real.
- ``metricas``: precisão, revocação, F1, taxas de erro e kappa de Cohen a
  partir do CSV anotado (ver ``app/climate_news/validation.py``).
- ``impacto-jsonld``: reacessa páginas que ficaram pendentes por "data não
  encontrada" e compara o extrator corrigido com o anterior (que descartava o
  JSON-LD); mesma política de acesso do ``acessibilidade``.
- ``acessibilidade``: reacessa uma amostra de URLs verificadas (1 req/s,
  timeout 10 s, User-Agent genérico) e informa quantas ainda respondem.

Nenhum rótulo humano é preenchido por este script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.climate_news.news.text import normalize_text
from app.climate_news.validation import ANNOTATION_LABELS, evaluate_annotations, load_annotation_csv
from app.database import engine

OUT_DIR = Path("docs/avaliacao_professor/validacao_noticias")
LOG_DIR = Path("docs/avaliacao_professor/execucoes")
STATUSES = ("verified", "rejected", "pending_verification")
REGIONS = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")

LINKS_SQL = """
SELECT an.anomaly_id::text AS anomaly_id, an.news_id::text AS news_id,
       an.link_status, an.relevance_status, an.municipality_match, an.event_date,
       an.decision,
       pa.anomaly_date, pa.municipality, pa.uf, pa.codigo_ibge, pa.observed_mm, pa.detector,
       pa.z_score, pa.scientific_review->'details' AS details,
       md.regiao,
       na.original_url, na.headline, na.source, na.source_domain, na.published_at,
       na.discovered_by->>'claimed_headline' AS claimed_headline
FROM anomaly_news an
JOIN precipitation_anomaly pa ON pa.id = an.anomaly_id
JOIN news_article na ON na.id = an.news_id
LEFT JOIN municipio_details md ON md.codigo_ibge = pa.codigo_ibge
"""


def load_links() -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(text(LINKS_SQL), conn)
    # ordem determinística, independente da ordem física do banco
    return df.sort_values(["anomaly_id", "news_id"]).reset_index(drop=True)


def failing_check(decision: dict) -> str | None:
    for name, check in (decision.get("checks") or {}).items():
        if not check.get("passed", True):
            return name
    return None


def failure_category(decision: dict) -> str | None:
    """Motivo da rejeição/pendência, com subtipo para os critérios mais comuns."""
    name = failing_check(decision)
    if name is None:
        return None
    detail = str(decision["checks"][name].get("detail", ""))
    if name == "temporal_relation":
        if "fora da janela" in detail:
            return "temporal_relation: publicação fora da janela"
        if "outro período" in detail:
            return "temporal_relation: manchete cita outro ano"
        if "retrospectiva" in detail:
            return "temporal_relation: pista de retrospectiva"
        if "outro evento" in detail:
            return "temporal_relation: evento datado fora da faixa"
    if name == "page_exists":
        if "HTTP 404" in detail or "HTTP 410" in detail:
            return "page_exists: 404/410"
        if "redireciona" in detail:
            return "page_exists: redireciona para não-matéria"
        if "sem título" in detail:
            return "page_exists: sem título"
        if "falha ao interpretar HTML" in detail:
            return "page_exists: HTML não interpretável (" + ("vazio" if "empty" in detail else "outro erro") + ")"
        match = re.search(r"não acessível \(([^)]*)\)", detail)
        if match:
            code = match.group(1)
            return f"page_exists: inacessível ({code if code.isdigit() else 'erro de rede/timeout'})"
    if name == "url_is_article":
        return f"url_is_article: {detail}"
    return name


def _s(value) -> str:
    """Valor para o CSV: vazio para None/NaN/NaT."""
    if value is None or (not isinstance(value, (str, dict, list)) and pd.isna(value)):
        return ""
    return str(value)


def _reasons(decision: dict) -> str:
    return " | ".join(decision.get("reasons") or [])


# ---------------------------------------------------------------------------
# Amostra estratificada
# ---------------------------------------------------------------------------

TEMPLATE_COLUMNS = [
    "id_amostra", "estrato_decisao", "estrato_regiao", "peso_amostral",
    "data_anomalia", "municipio", "uf", "regiao", "detector", "observado_mm", "z_score",
    "acumulado_inicio", "acumulado_fim", "acumulado_mm",
    "url_noticia", "titulo", "manchete_buscador", "fonte", "dominio", "data_publicacao",
    "status_sistema", "relevancia_sistema", "municipio_match_sistema", "data_evento_estimada_sistema",
    "nivel_fonte_sistema", "duplicata_sistema", "motivos_sistema",
    "rotulo_anotador_1", "rotulo_anotador_2", "rotulo_adjudicado", "observacao",
]
BLIND_COLUMNS = [
    "id_amostra", "data_anomalia", "municipio", "uf", "detector", "observado_mm",
    "acumulado_inicio", "acumulado_fim", "acumulado_mm",
    "url_noticia", "titulo", "fonte", "data_publicacao",
    "rotulo_anotador_1", "rotulo_anotador_2", "rotulo_adjudicado", "observacao",
]


def stratified_sample(df: pd.DataFrame, per_stratum: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    df = df.assign(regiao=df["regiao"].fillna("sem_regiao"))
    parts, sizes = [], []
    for status in STATUSES:
        for region in REGIONS:
            stratum = df[(df["link_status"] == status) & (df["regiao"] == region)]
            n = min(per_stratum, len(stratum))
            sizes.append({"decisao": status, "regiao": region, "populacao": len(stratum), "amostra": n})
            if n == 0:
                continue
            chosen = stratum.iloc[np.sort(rng.choice(len(stratum), size=n, replace=False))]
            parts.append(chosen.assign(peso_amostral=len(stratum) / n))
    sample = pd.concat(parts)
    # ordem embaralhada: os anotadores não veem os estratos agrupados
    sample = sample.iloc[rng.permutation(len(sample))].reset_index(drop=True)
    return sample, pd.DataFrame(sizes)


def to_template(sample: pd.DataFrame) -> list[dict]:
    rows = []
    for i, r in enumerate(sample.itertuples(index=False), start=1):
        decision = r.decision or {}
        details = r.details or {}
        start = end = acc = ""
        if r.detector == "accumulation_percentile" and details.get("event_start"):
            # mesmo período usado pelo Fact-Checker (orchestrator.verification_context)
            days = int(details.get("window_days", 1))
            start = (pd.Timestamp(details["event_start"]) - pd.Timedelta(days=days - 1)).date().isoformat()
            end, acc = details.get("event_end", ""), details.get("accumulated_mm", "")
        rows.append({
            "id_amostra": f"A{i:03d}",
            "estrato_decisao": r.link_status,
            "estrato_regiao": r.regiao,
            "peso_amostral": round(r.peso_amostral, 4),
            "data_anomalia": r.anomaly_date.isoformat(),
            "municipio": r.municipality,
            "uf": r.uf,
            "regiao": r.regiao,
            "detector": r.detector,
            "observado_mm": round(r.observed_mm, 2),
            "z_score": "" if _s(r.z_score) == "" else round(r.z_score, 2),
            "acumulado_inicio": start, "acumulado_fim": end, "acumulado_mm": acc,
            "url_noticia": r.original_url,
            "titulo": r.headline,
            "manchete_buscador": _s(r.claimed_headline),
            "fonte": _s(r.source),
            "dominio": r.source_domain,
            "data_publicacao": "" if pd.isna(r.published_at) else pd.Timestamp(r.published_at).isoformat(),
            "status_sistema": r.link_status,
            "relevancia_sistema": r.relevance_status,
            "municipio_match_sistema": _s(r.municipality_match),
            "data_evento_estimada_sistema": _s(r.event_date),
            "nivel_fonte_sistema": decision.get("source_tier") or "",
            "duplicata_sistema": decision.get("duplicate_kind") or "",
            "motivos_sistema": _reasons(decision),
            "rotulo_anotador_1": "", "rotulo_anotador_2": "", "rotulo_adjudicado": "", "observacao": "",
        })
    return rows


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def cmd_amostra(args) -> None:
    df = load_links()
    key = hashlib.sha256("\n".join(df["anomaly_id"] + "|" + df["news_id"]).encode()).hexdigest()
    sample, sizes = stratified_sample(df, args.n_por_estrato, args.semente)
    rows = to_template(sample)
    out = Path(args.saida)
    write_csv(out, rows, TEMPLATE_COLUMNS)
    blind = out.with_name(out.stem + "_cega.csv")
    write_csv(blind, rows, BLIND_COLUMNS)
    lines = [
        f"gerado em {datetime.now(timezone.utc).isoformat()}",
        f"populacao de vinculos anomalia x noticia: {len(df)} (sha256 das chaves: {key})",
        f"semente: {args.semente}; alvo por estrato (decisao x regiao): {args.n_por_estrato}",
        f"linhas exportadas: {len(rows)} -> {out} e {blind}",
        f"rotulos permitidos: {', '.join(ANNOTATION_LABELS)}",
        "",
        sizes.to_string(index=False),
    ]
    text_out = "\n".join(lines)
    print(text_out)
    (out.parent / "amostra_estratos.txt").write_text(text_out + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Estatísticas descritivas
# ---------------------------------------------------------------------------

# Padrões de manchete associados a falsos positivos conhecidos do benchmark.
# Contagem de EXPOSIÇÃO ao risco, não de erros confirmados.
RISK_PATTERNS = {
    "estiagem/seca/falta de chuva": r"\b(?:estiagem|seca|falta de chuva|sem chuva)\b",
    "calor/temperatura": r"\b(?:onda de calor|calor|temperatura)\b",
    "previsao/alerta": r"\b(?:previsao|preve|alerta|aviso)\b",
    "frio/geada": r"\b(?:frio|geada|frente fria)\b",
    "uso figurado de 'cheia'": r"\b(?:casa|lua|agenda) cheia\b",
    "vento sem chuva na manchete": r"\b(?:vendaval|ventania|rajada)",
    "politica/projeto/obra": r"\b(?:projeto|obra|obras|licitacao|camara|vereador)",
}


def _episodes(dates: list) -> int:
    """Agrupa datas a até 1 dia uma da outra (mesma regra de episódio da detecção)."""
    count, last = 0, None
    for d in sorted(set(dates)):
        if last is None or (d - last).days > 1:
            count += 1
        last = d
    return count


def cmd_estatisticas(args) -> None:
    out: list[str] = [f"gerado em {datetime.now(timezone.utc).isoformat()}", ""]

    def section(title: str) -> None:
        out.extend(["", f"== {title}"])

    with engine.connect() as conn:
        q = lambda sql: conn.execute(text(sql)).all()  # noqa: E731
        section("execucoes de investigacao (pipeline_run)")
        for status, n in q("SELECT status, count(*) FROM pipeline_run WHERE run_type='investigation' GROUP BY 1 ORDER BY 1"):
            out.append(f"{status}: {n}")
        section("investigacoes (news_investigation)")
        (total, distinct, found, zero, ver, rej, pend), = q(
            "SELECT count(*), count(DISTINCT anomaly_id), sum(n_found), count(*) FILTER (WHERE n_found=0), "
            "sum(n_verified), sum(n_rejected), sum(n_pending) FROM news_investigation"
        )
        out += [
            f"tarefas: {total}; anomalias distintas investigadas: {distinct}",
            "municipios investigados: " + str(q(
                "SELECT count(DISTINCT pa.codigo_ibge) FROM news_investigation ni "
                "JOIN precipitation_anomaly pa ON pa.id = ni.anomaly_id")[0][0]),
            f"candidatas encontradas (soma n_found): {found}",
            f"tarefas sem nenhuma candidata: {zero} ({zero / total:.1%})",
            f"contadores das tarefas: verified={ver} rejected={rej} pending={pend}",
        ]
        for status, n in q("SELECT status, count(*) FROM news_investigation GROUP BY 1 ORDER BY 1"):
            out.append(f"status {status}: {n}")
        for det, n, with_verified in q(
            "SELECT pa.detector, count(DISTINCT ni.anomaly_id), "
            "count(DISTINCT ni.anomaly_id) FILTER (WHERE ni.n_verified > 0) "
            "FROM news_investigation ni JOIN precipitation_anomaly pa ON pa.id = ni.anomaly_id GROUP BY 1"
        ):
            out.append(f"detector {det}: {n} anomalias investigadas, {with_verified} com >=1 noticia verificada ({with_verified / n:.1%})")
        section("noticias (news_article, status global por URL)")
        for status, n in q("SELECT verification_status, count(*) FROM news_article GROUP BY 1 ORDER BY 1"):
            out.append(f"{status}: {n}")
        for rel, n in q("SELECT reliability, count(*) FROM news_article WHERE verification_status='verified' GROUP BY 1 ORDER BY 1"):
            out.append(f"verificadas com confiabilidade {rel}: {n}")
        (multi,), = q("SELECT count(*) FROM (SELECT news_id FROM anomaly_news GROUP BY 1 HAVING count(*) > 1) s")
        out.append(f"noticias ligadas a mais de uma anomalia: {multi}")
        (attempts,), = q("SELECT count(*) FROM news_verification_attempt")
        out.append(f"tentativas de verificacao registradas: {attempts}")

    df = load_links()
    df["regiao"] = df["regiao"].fillna("sem_regiao")
    decisions = df["decision"].apply(lambda d: d or {})
    section("vinculos anomalia x noticia (anomaly_news)")
    out.append(f"total: {len(df)}")
    out.append(df.groupby(["link_status", "relevance_status"]).size().to_string())
    section("vinculos por regiao e decisao")
    out.append(pd.crosstab(df["regiao"], df["link_status"], margins=True).to_string())

    section("motivo da rejeicao (primeiro criterio que falhou)")
    for status in ("rejected", "pending_verification"):
        subset = decisions[df["link_status"] == status]
        counts = Counter(failure_category(d) or "sem criterio falho registrado" for d in subset)
        out.append(f"-- {status} (n={len(subset)})")
        for reason, n in counts.most_common():
            out.append(f"  {reason}: {n} ({n / len(subset):.1%})")

    section("nivel da fonte (source_tier)")
    tiers = decisions.apply(lambda d: d.get("source_tier") or "nao_avaliado")
    out.append(pd.crosstab(tiers, df["link_status"], margins=True).to_string())
    verified = df["link_status"] == "verified"
    out.append("confiabilidade nos vinculos verificados: " + json.dumps(
        Counter(decisions[verified].apply(lambda d: d.get("reliability"))).most_common()))
    methods = decisions.apply(
        lambda d: ((d.get("checks") or {}).get("publication_date_confirmed") or {}).get("detail") or {}
    ).apply(lambda x: x.get("method") if isinstance(x, dict) else None)
    out.append("metodo da data de publicacao (vinculos com data lida): " + json.dumps(
        Counter(m for m in methods if isinstance(m, str)).most_common(), ensure_ascii=False))
    claimed_diff = decisions.apply(lambda d: any(str(r).startswith("claimed_date_differs") for r in d.get("reasons") or []))
    out.append(f"vinculos em que a data do buscador diverge da pagina (> 2 dias): {int(claimed_diff.sum())}")

    section("duplicatas detectadas (vinculos verificados)")
    kinds = decisions[verified].apply(lambda d: d.get("duplicate_kind") or "nenhuma")
    for kind, n in kinds.value_counts().items():
        out.append(f"{kind}: {n}")

    section("eventos distintos com >=1 noticia verificada")
    ver = df[verified]
    pairs = ver.drop_duplicates(["codigo_ibge", "anomaly_date"])
    out.append(f"pares (municipio, data da anomalia) distintos: {len(pairs)}")
    out.append(f"municipios distintos: {ver['codigo_ibge'].nunique()}")
    episodes = sum(_episodes(list(g["anomaly_date"])) for _, g in pairs.groupby("codigo_ibge"))
    out.append(f"episodios (datas a <=1 dia agrupadas, por municipio): {episodes}")
    out.append(f"noticias distintas verificadas em algum vinculo: {ver['news_id'].nunique()}")
    per_news = ver.groupby("news_id").size()
    out.append(f"noticias verificadas para mais de uma anomalia: {int((per_news > 1).sum())} "
               "(mesma materia sustentando anomalias de detectores/datas proximas)")
    out.append("episodios com noticia verificada por regiao: " + json.dumps({
        region: int(sum(_episodes(list(g["anomaly_date"])) for _, g in grp.drop_duplicates(["codigo_ibge", "anomaly_date"]).groupby("codigo_ibge")))
        for region, grp in ver.groupby("regiao")
    }, ensure_ascii=False))

    section("exposicao a padroes de falso positivo do benchmark (manchetes de vinculos VERIFICADOS)")
    out.append("(contagem de manchetes que contem o padrao; NAO e contagem de erros: exige revisao humana)")
    titles = ver.drop_duplicates("news_id")["headline"].map(normalize_text)
    for label, pattern in RISK_PATTERNS.items():
        n = int(titles.str.contains(pattern, regex=True).sum())
        out.append(f"{label}: {n} de {len(titles)} ({n / len(titles):.1%})")

    text_out = "\n".join(out)
    print(text_out)
    if args.log:
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        Path(args.log).write_text(text_out + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Métricas a partir do CSV anotado
# ---------------------------------------------------------------------------


def cmd_metricas(args) -> None:
    rows = load_annotation_csv(args.anotado)
    if rows and "status_sistema" not in rows[0]:
        if not args.amostra:
            sys.exit("o arquivo anotado não tem status_sistema: informe --amostra com o CSV completo")
        full = {r["id_amostra"]: r for r in load_annotation_csv(args.amostra)}
        rows = [{**full[r["id_amostra"]], **{k: v for k, v in r.items() if k.startswith("rotulo") or k == "observacao"}}
                for r in rows]
    print(json.dumps(evaluate_annotations(rows), indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Reacesso das URLs verificadas
# ---------------------------------------------------------------------------


def cmd_acessibilidade(args) -> None:
    import httpx

    with engine.connect() as conn:
        urls = sorted(u for (u,) in conn.execute(text(
            "SELECT original_url FROM news_article WHERE verification_status = 'verified'")))
    rng = np.random.default_rng(args.semente)
    chosen = [urls[i] for i in sorted(rng.choice(len(urls), size=min(args.n, len(urls)), replace=False))]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; verificacao-academica/1.0)"}
    results = []
    with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
        for url in chosen:
            try:
                response = client.get(url)
                results.append((url, response.status_code, str(response.url) != url, None))
            except httpx.HTTPError as error:
                results.append((url, None, False, type(error).__name__))
            time.sleep(1.0)
    ok = sum(1 for _, s, _, _ in results if s is not None and 200 <= s < 300)
    by_status = Counter(str(s) if s is not None else f"erro:{e}" for _, s, _, e in results)
    lines = [
        f"gerado em {datetime.now(timezone.utc).isoformat()}",
        f"URLs verificadas no banco: {len(urls)}; amostra (semente {args.semente}): {len(results)}",
        f"respondem com 2xx: {ok} ({ok / len(results):.1%})",
        f"distribuicao: {dict(by_status)}",
        f"redirecionadas (URL final diferente): {sum(1 for _, _, r, _ in results if r)}",
        "(2xx indica que a URL responde; nao reconfirma o conteudo da materia)",
        "",
    ] + [f"{s if s is not None else e} | {'redir' if r else '-'} | {u}" for u, s, r, e in results]
    text_out = "\n".join(lines)
    print(text_out)
    if args.log:
        Path(args.log).write_text(text_out + "\n", encoding="utf-8")


def cmd_impacto_jsonld(args) -> None:
    import httpx

    from app.climate_news.news.extract import extract_metadata

    def old_extract(content: str, url: str):
        # comportamento anterior à correção: <script> removido antes de ler o JSON-LD
        return extract_metadata(re.sub(r"(?is)<script[^>]*>.*?</script>", "", content), url)

    with engine.connect() as conn:
        urls = sorted(u for (u,) in conn.execute(text(
            "SELECT DISTINCT na.original_url FROM anomaly_news an JOIN news_article na ON na.id = an.news_id "
            "WHERE an.link_status = 'pending_verification' "
            "AND an.decision->'checks'->'publication_date_confirmed'->>'passed' = 'false'")))
    rng = np.random.default_rng(args.semente)
    chosen = [urls[i] for i in sorted(rng.choice(len(urls), size=min(args.n, len(urls)), replace=False))]
    counts, lines = Counter(), []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; verificacao-academica/1.0)"}
    with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
        for url in chosen:
            try:
                response = client.get(url)
                if response.status_code != 200:
                    kind, source = f"http_{response.status_code}", None
                else:
                    new, old = extract_metadata(response.text, url), old_extract(response.text, url)
                    kind = ("data_so_com_correcao" if new.published_at and not old.published_at
                            else "data_por_outro_metodo" if old.published_at else "sem_data_nas_duas")
                    source = new.published_source
            except Exception as error:  # noqa: BLE001
                kind, source = f"erro_{type(error).__name__}", None
            counts[kind] += 1
            lines.append(f"{kind} | {source} | {url}")
            time.sleep(1.0)
    text_out = "\n".join([
        f"gerado em {datetime.now(timezone.utc).isoformat()}",
        f"URLs distintas pendentes por data ausente: {len(urls)}; amostra (semente {args.semente}): {len(chosen)}",
        f"resultado: {dict(counts)}",
        "data_so_com_correcao = data encontrada apenas com a correcao do JSON-LD (extract.py)",
        "data_por_outro_metodo = a pagina hoje traz data em meta/time (mudou desde a coleta ou outro User-Agent)",
        "",
    ] + lines)
    print(text_out)
    if args.log:
        Path(args.log).write_text(text_out + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("amostra")
    p.add_argument("--n-por-estrato", type=int, default=10)
    p.add_argument("--semente", type=int, default=20261114)
    p.add_argument("--saida", default=str(OUT_DIR / "amostra_para_anotacao.csv"))
    p.set_defaults(func=cmd_amostra)
    p = sub.add_parser("estatisticas")
    p.add_argument("--log", default=str(LOG_DIR / "estatisticas_noticias.log"))
    p.set_defaults(func=cmd_estatisticas)
    p = sub.add_parser("metricas")
    p.add_argument("anotado")
    p.add_argument("--amostra", default=None)
    p.set_defaults(func=cmd_metricas)
    p = sub.add_parser("acessibilidade")
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--semente", type=int, default=20261114)
    p.add_argument("--log", default=str(LOG_DIR / "acessibilidade_urls_verificadas.log"))
    p.set_defaults(func=cmd_acessibilidade)
    p = sub.add_parser("impacto-jsonld")
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--semente", type=int, default=20261114)
    p.add_argument("--log", default=str(LOG_DIR / "impacto_correcao_jsonld.log"))
    p.set_defaults(func=cmd_impacto_jsonld)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
