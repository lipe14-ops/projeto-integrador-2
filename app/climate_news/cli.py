"""CLI do sistema de anomalias e notícias.

Exemplos::

    uv run python -m app.climate_news.cli run --municipio "Porto Alegre" --uf RS
    uv run python -m app.climate_news.cli detect --municipio "Rio Verde" --uf GO
    uv run python -m app.climate_news.cli investigate --detection-run <uuid>
    uv run python -m app.climate_news.cli resume --investigation-run <uuid>
    uv run python -m app.climate_news.cli revalidate --investigation-run <uuid>
    uv run python -m app.climate_news.cli show --run <uuid>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import date

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.agents.fact_checker import FactCheckerAgent
from app.climate_news.agents.news_researcher import NewsResearcherAgent
from app.climate_news.agents.orchestrator import InvestigationConfig, Orchestrator
from app.climate_news.data_source import load_daily_series, load_enso, resolve_municipality
from app.climate_news.detection.accumulation import AccumulationConfig
from app.climate_news.detection.arima_zscore import DetectionConfig, load_series_from_csv
from app.climate_news.models import PipelineRun
from app.climate_news.news.google_news import GoogleNewsProvider
from app.climate_news.news.http import HttpClient
from app.database import SessionLocal


def _context(args) -> MunicipalityContext:
    with SessionLocal() as db:
        return resolve_municipality(db, args.municipio, args.uf, args.codigo_ibge)


def _context_from_run(run_id: uuid.UUID) -> MunicipalityContext:
    with SessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if run is None:
            raise SystemExit(f"Execução não encontrada: {run_id}")
        try:
            return resolve_municipality(db, run.municipality, run.uf, run.codigo_ibge)
        except LookupError:
            return MunicipalityContext(name=run.municipality, uf=run.uf, codigo_ibge=run.codigo_ibge)


def _orchestrator(args, with_news: bool) -> Orchestrator:
    accumulation = None if getattr(args, "no_accumulation", False) else AccumulationConfig()
    researcher = fact_checker = None
    if with_news:
        search_client = HttpClient(min_interval=1.0, host_intervals={"news.google.com": 1.5})
        researcher = NewsResearcherAgent(
            GoogleNewsProvider(search_client, max_results=args.max_candidates),
            max_candidates=args.max_candidates,
            main_only=getattr(args, "principais", None) is not None,
        )
        # cliente HTTP próprio: o Fact-Checker não reutiliza nada do pesquisador
        fact_checker = FactCheckerAgent(HttpClient(min_interval=1.0))
    return Orchestrator(SessionLocal, researcher, fact_checker, accumulation)


def cmd_detect(args) -> uuid.UUID:
    config = DetectionConfig(
        z_threshold=args.threshold,
        seasonal=args.seasonal,
        initial_train_years=args.initial_train_years,
    )
    if args.csv:
        if not args.municipio:
            raise SystemExit("--municipio é obrigatório com --csv")
        series, quality = load_series_from_csv(
            args.csv, args.date_col, args.value_col, args.era5_12h, args.filter_col, args.filter_value
        )
        try:
            context = _context(args)
        except (LookupError, ValueError):
            context = MunicipalityContext(name=args.municipio, uf=args.uf)
        source = f"csv:{args.csv}"
    else:
        context = _context(args)
        with SessionLocal() as db:
            series, quality = load_daily_series(db, context.codigo_ibge, args.start, args.end)
        source = "database:registro_climatico (ERA5-Land, 12 h → diário)"
    with SessionLocal() as db:
        enso = load_enso(db)
    outcome = _orchestrator(args, with_news=False).run_detection(context, series, quality, config, enso, source)
    s = outcome.summary
    print(f"detecção {outcome.run_id} ({context.label()}): modelo {s['selected_spec']['order']} "
          f"sazonal={s['selected_spec']['seasonal']}, período pontuado {s['scored_period'][0]}..{s['scored_period'][1]}")
    print(f"  anomalias: {s['anomalies_by_detector']} | status: {s['anomalies_by_status']}")
    print(f"  datas candidatas à investigação: {len(s['candidate_dates_for_investigation'])}")
    return outcome.run_id


# ---------------------------------------------------------------------------
# Detecção nacional (todos os municípios), em processos paralelos
# ---------------------------------------------------------------------------

_ENSO: dict | None = None


def _init_worker() -> None:
    # cada processo abre as próprias conexões; BLAS com 1 thread evita disputa de CPU
    import os

    from app.database import engine

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    engine.dispose(close=False)


def _detect_one(codigo: int) -> tuple[int, str, int, float, str]:
    import time
    import warnings

    warnings.filterwarnings("ignore")
    global _ENSO
    inicio = time.perf_counter()
    try:
        with SessionLocal() as db:
            if _ENSO is None:
                _ENSO = load_enso(db)
            context = resolve_municipality(db, codigo_ibge=codigo)
            series, quality = load_daily_series(db, codigo)
        outcome = Orchestrator(SessionLocal, accumulation=AccumulationConfig()).run_detection(
            context, series, quality, DetectionConfig(), _ENSO,
            "database:precipitacao_diaria (ERA5-Land, 12 h → diário)",
        )
        return codigo, "ok", outcome.anomalies, time.perf_counter() - inicio, ""
    except Exception as error:  # noqa: BLE001 — registrado; a execução nacional continua
        return codigo, "erro", 0, time.perf_counter() - inicio, f"{type(error).__name__}: {error}"


def cmd_detect_all(args) -> None:
    import time
    from concurrent.futures import ProcessPoolExecutor, as_completed

    from sqlalchemy import select

    from app.climate_news import ALGORITHM_VERSION
    from app.models.municipio_details import MunicipioDetails

    with SessionLocal() as db:
        todos = [int(c) for c in db.scalars(select(MunicipioDetails.codigo_ibge).order_by(MunicipioDetails.codigo_ibge))]
        if args.uf:
            todos = [int(c) for c in db.scalars(select(MunicipioDetails.codigo_ibge).where(MunicipioDetails.uf.in_([u.upper() for u in args.uf])))]
        feitos = set(db.scalars(
            select(PipelineRun.codigo_ibge).where(
                PipelineRun.run_type == "detection", PipelineRun.status == "completed",
                PipelineRun.algorithm_version == ALGORITHM_VERSION,
            )
        ))
    pendentes = [c for c in todos if c not in feitos]
    if args.limit:
        pendentes = pendentes[: args.limit]
    print(f"detecção nacional: {len(todos)} municípios, {len(todos) - len(pendentes)} já concluídos, "
          f"{len(pendentes)} a processar com {args.workers} processos", flush=True)
    inicio, feitos_agora, erros, anomalias = time.perf_counter(), 0, 0, 0
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker) as pool:
        futuros = [pool.submit(_detect_one, c) for c in pendentes]
        for futuro in as_completed(futuros):
            codigo, status, n, segundos, erro = futuro.result()
            feitos_agora += 1
            anomalias += n
            if status == "erro":
                erros += 1
                print(f"ERRO {codigo}: {erro}", flush=True)
            if feitos_agora % 25 == 0 or feitos_agora == len(pendentes):
                decorrido = time.perf_counter() - inicio
                restante = decorrido / feitos_agora * (len(pendentes) - feitos_agora)
                print(f"[{feitos_agora}/{len(pendentes)}] {anomalias} anomalias, {erros} erros, "
                      f"{decorrido / 60:.1f} min decorridos, ~{restante / 60:.0f} min restantes", flush=True)


def _proxima_deteccao_sem_investigacao(db, ja_tentadas: set) -> tuple | None:
    """Detecção concluída mais recente de um município ainda sem investigação
    concluída, em ordem de população (maiores primeiro)."""
    from sqlalchemy import text

    row = db.execute(
        text(
            """
            WITH ultima AS (
                SELECT DISTINCT ON (r.codigo_ibge) r.id, r.codigo_ibge
                FROM pipeline_run r
                WHERE r.run_type = 'detection' AND r.status = 'completed'
                ORDER BY r.codigo_ibge, r.finished_at DESC
            )
            SELECT u.id, inv.id AS investigacao, inv.status
            FROM ultima u
            JOIN municipio_details d ON d.codigo_ibge = u.codigo_ibge
            LEFT JOIN LATERAL (
                SELECT i.id, i.status FROM pipeline_run i
                WHERE i.run_type = 'investigation' AND i.parent_run_id = u.id
                ORDER BY i.started_at DESC LIMIT 1
            ) inv ON true
            WHERE (inv.id IS NULL OR inv.status <> 'completed') AND NOT (u.id = ANY(:tentadas))
            ORDER BY d.populacao DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"tentadas": list(ja_tentadas)},
    ).first()
    return tuple(row) if row else None


def cmd_investigate_all(args) -> None:
    """Investiga notícias de todos os municípios com detecção (retomável).

    Maiores municípios primeiro. Se o buscador recusar todas as consultas de uma
    investigação (bloqueio/limite), pausa ``--pausa-bloqueio`` minutos e retoma.
    Com ``--follow``, espera novas detecções enquanto a detecção nacional roda.
    """
    import time

    if args.principais and args.max_candidates == 15:
        # cada candidata custa ~2 requisições ao buscador (decodificar o link):
        # no modo "principais" basta uma folga de 2× sobre o número desejado
        args.max_candidates = 2 * args.principais
    config = InvestigationConfig(
        window_before=args.window_before, window_after=args.window_after, workers=args.workers,
        include_rejected=False, include_neighbors=not args.no_neighbors,
        max_verified=args.principais,
    )
    orchestrator = _orchestrator(args, with_news=True)
    tentadas: set = set()
    feitas = 0
    while True:
        with SessionLocal() as db:
            proxima = _proxima_deteccao_sem_investigacao(db, tentadas)
        if proxima is None:
            if args.follow:
                print("nenhuma detecção pendente; aguardando novas (5 min)", flush=True)
                time.sleep(300)
                tentadas.clear()
                continue
            break
        deteccao, investigacao, status = proxima
        context = _context_from_run(deteccao)
        inicio = time.perf_counter()
        try:
            if investigacao is not None:
                orchestrator.resume_investigation(investigacao, context)
                run_id = investigacao
            else:
                run_id = orchestrator.run_investigation(deteccao, context, config)
        except Exception as error:  # noqa: BLE001 — registra e segue para o próximo
            print(f"ERRO {context.label()}: {type(error).__name__}: {error}", flush=True)
            tentadas.add(deteccao)
            continue
        with SessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            resumo = run.summary
        feitas += 1
        print(
            f"[{feitas}] {context.label()}: {run.status}, {len(resumo.get('dates_investigated', []))} datas, "
            f"{resumo.get('news_verified', 0)} verificadas, {resumo.get('news_rejected', 0)} rejeitadas "
            f"({(time.perf_counter() - inicio) / 60:.1f} min)",
            flush=True,
        )
        if run.status != "completed":
            falhas = len(resumo.get("failed_dates", []))
            total = len(resumo.get("dates_investigated", [])) or 1
            if falhas / total >= 0.5:
                print(f"buscador recusando consultas ({falhas}/{total} datas falharam): pausa de {args.pausa_bloqueio} min", flush=True)
                time.sleep(args.pausa_bloqueio * 60)
            else:
                tentadas.add(deteccao)  # falhas pontuais: retoma numa próxima passada


def cmd_investigate(args, detection_run: uuid.UUID | None = None) -> uuid.UUID:
    detection_run = detection_run or args.detection_run
    context = _context_from_run(detection_run)
    config = InvestigationConfig(
        window_before=args.window_before,
        window_after=args.window_after,
        workers=args.workers,
        include_rejected=args.include_rejected,
        include_neighbors=not args.no_neighbors,
    )
    run_id = _orchestrator(args, with_news=True).run_investigation(detection_run, context, config, args.only_dates)
    _print_run(run_id)
    return run_id


def cmd_resume(args) -> None:
    context = _context_from_run(args.investigation_run)
    _orchestrator(args, with_news=True).resume_investigation(args.investigation_run, context)
    _print_run(args.investigation_run)


def cmd_revalidate(args) -> None:
    context = _context_from_run(args.investigation_run)
    _orchestrator(args, with_news=True).revalidate_investigation(args.investigation_run, context)
    _print_run(args.investigation_run)


def _print_run(run_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        s = run.summary
        print(f"investigação {run.id}: status {run.status}")
        for key in ("investigations_by_status", "news_found", "news_verified", "news_rejected", "news_pending", "queries"):
            print(f"  {key}: {s.get(key)}")
        print(f"  datas com notícias verificadas: {s.get('dates_with_verified_news')}")
        print(f"  datas sem resultados: {s.get('dates_without_results')}")
        if s.get("failed_dates"):
            print(f"  datas com falha: {s['failed_dates']}")


def cmd_show(args) -> None:
    with SessionLocal() as db:
        run = db.get(PipelineRun, args.run)
        if run is None:
            raise SystemExit("Execução não encontrada")
        data = {c.key: getattr(run, c.key) for c in PipelineRun.__table__.columns}
        print(json.dumps(data, default=str, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="climate_news", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def place(p):
        p.add_argument("--municipio")
        p.add_argument("--uf")
        p.add_argument("--codigo-ibge", type=int)

    def detection(p):
        p.add_argument("--start", type=date.fromisoformat)
        p.add_argument("--end", type=date.fromisoformat)
        p.add_argument("--threshold", type=float, default=3.0)
        p.add_argument("--seasonal", choices=["auto", "fourier", "none"], default="auto")
        p.add_argument("--initial-train-years", type=int, default=2)
        p.add_argument("--no-accumulation", action="store_true", help="desliga o detector suplementar de acumulados")
        p.add_argument("--csv")
        p.add_argument("--date-col", default="date")
        p.add_argument("--value-col", default="precipitation_mm")
        p.add_argument("--era5-12h", action="store_true")
        p.add_argument("--filter-col")
        p.add_argument("--filter-value")

    def investigation(p):
        p.add_argument("--window-before", type=int, default=3)
        p.add_argument("--window-after", type=int, default=7)
        p.add_argument("--workers", type=int, default=3)
        p.add_argument("--max-candidates", type=int, default=15)
        p.add_argument("--include-rejected", action="store_true")
        p.add_argument("--no-neighbors", action="store_true")
        p.add_argument("--only-dates", type=date.fromisoformat, nargs="+")

    p = sub.add_parser("detect", help="detecção + revisão científica")
    place(p)
    detection(p)
    p = sub.add_parser("detect-all", help="detecção em todos os municípios (retomável; pula os já concluídos)")
    p.add_argument("--workers", type=int, default=7)
    p.add_argument("--uf", nargs="+", help="restringe a estas UFs")
    p.add_argument("--limit", type=int, help="processa no máximo N municípios (teste)")
    p = sub.add_parser("investigate-all", help="investiga notícias de todos os municípios com detecção (retomável)")
    investigation(p)
    p.add_argument("--follow", action="store_true", help="continua aguardando novas detecções")
    p.add_argument("--principais", type=int, default=3,
                   help="só as N principais notícias por data: consulta principal e para após N aprovadas (padrão 3)")
    p.add_argument("--pausa-bloqueio", type=int, default=15, help="minutos de pausa se o buscador bloquear")
    p = sub.add_parser("investigate", help="investiga notícias das anomalias de uma detecção")
    p.add_argument("--detection-run", type=uuid.UUID, required=True)
    investigation(p)
    p = sub.add_parser("run", help="detecção + investigação")
    place(p)
    detection(p)
    investigation(p)
    p = sub.add_parser("resume", help="reprocessa investigações pendentes/falhas")
    p.add_argument("--investigation-run", type=uuid.UUID, required=True)
    p.add_argument("--max-candidates", type=int, default=15)
    p = sub.add_parser("revalidate", help="reverifica com o Fact-Checker as notícias de uma investigação (sem nova busca)")
    p.add_argument("--investigation-run", type=uuid.UUID, required=True)
    p.add_argument("--max-candidates", type=int, default=15)
    p = sub.add_parser("show", help="mostra a trilha de auditoria de uma execução")
    p.add_argument("--run", type=uuid.UUID, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = build_parser().parse_args(argv)
    if args.command == "detect":
        cmd_detect(args)
    elif args.command == "detect-all":
        cmd_detect_all(args)
    elif args.command == "investigate-all":
        cmd_investigate_all(args)
    elif args.command == "investigate":
        cmd_investigate(args)
    elif args.command == "run":
        cmd_investigate(args, cmd_detect(args))
    elif args.command == "resume":
        cmd_resume(args)
    elif args.command == "revalidate":
        cmd_revalidate(args)
    elif args.command == "show":
        cmd_show(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
