"""Linha de comando da análise espacial e sazonal.

    uv run python -m app.climate_news.analysis.cli snapshot-chuva
    uv run python -m app.climate_news.analysis.cli snapshot-termica --workers 4
    uv run python -m app.climate_news.analysis.cli snapshot-malha
    uv run python -m app.climate_news.analysis.cli avaliar-metodo --por-regiao 30
    uv run python -m app.climate_news.analysis.cli relatorio

``relatorio`` lê o snapshot e grava tabelas CSV, figuras e o resumo numérico
em ``docs/avaliacao_professor/resultados/``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.climate_news.analysis.snapshot import DEFAULT_DIR, build_precipitation_snapshot, build_thermal_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Análise espacial e sazonal (Clima Brasil)")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="pasta do snapshot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("snapshot-chuva", help="extrai anomalias de chuva e exposição do banco")
    thermal = sub.add_parser("snapshot-termica", help="detecta anomalias de temperatura e umidade (nacional)")
    thermal.add_argument("--workers", type=int, default=4)
    thermal.add_argument("--codigos", type=int, nargs="*", help="só estes municípios (teste)")
    sub.add_parser("reclassificar-termica", help="recalcula as classes térmicas com a cauda do mesmo sentido")
    sub.add_parser("snapshot-malha", help="exporta a malha municipal simplificada (GeoParquet) para os mapas")
    method = sub.add_parser("avaliar-metodo", help="reexecuta o ARIMA+Z numa amostra e mede calibração/sazonalidade")
    method.add_argument("--por-regiao", type=int, default=30)
    method.add_argument("--workers", type=int, default=4)
    method.add_argument("--simulacoes", type=int, default=20)
    report = sub.add_parser("relatorio", help="gera tabelas, figuras e números do relatório")
    report.add_argument("--out", type=Path, default=Path("docs/avaliacao_professor/resultados"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.command in {"snapshot-chuva", "snapshot-termica"}:
        from app.database import engine

        if args.command == "snapshot-chuva":
            result = build_precipitation_snapshot(engine, args.dir)
        else:
            result = build_thermal_snapshot(engine, args.dir, workers=args.workers, codes=args.codigos)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str)[:4000])
        return 0

    if args.command == "reclassificar-termica":
        from app.climate_news.analysis.snapshot import reclassify_thermal

        print(json.dumps(reclassify_thermal(args.dir), ensure_ascii=False, indent=2))
        return 0

    if args.command == "snapshot-malha":
        from app.climate_news.analysis.snapshot import build_geometry_snapshot
        from app.database import engine

        print(json.dumps(build_geometry_snapshot(engine, args.dir), ensure_ascii=False, indent=2))
        return 0

    if args.command == "avaliar-metodo":
        import pandas as pd

        from app.climate_news.analysis.method_eval import null_simulation, run_method_evaluation, sample_municipalities
        from app.database import engine

        municipalities = pd.read_parquet(args.dir / "municipios.parquet")
        codes = sample_municipalities(municipalities, args.por_regiao)
        result = run_method_evaluation(engine, codes, workers=args.workers)
        result.to_parquet(args.dir / "metodo_avaliacao.parquet", index=False)
        null = null_simulation(args.simulacoes)
        null.to_parquet(args.dir / "metodo_simulacao_nula.parquet", index=False)
        errors = int(result["error"].notna().sum()) if "error" in result else 0
        print(json.dumps({"municipios": len(codes), "erros": errors, "simulacoes": len(null)}, indent=2))
        return 0

    from app.climate_news.analysis.report import build_report

    summary = build_report(args.dir, args.out)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
