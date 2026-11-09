"""Atualiza a visão materializada clima_mensal após uma carga climática."""

import time

from sqlalchemy import text

from app.database import engine


def main() -> int:
    inicio = time.perf_counter()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # CONCURRENTLY mantém a visão legível pela API durante a atualização
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY clima_mensal"))
        linhas = conn.execute(text("SELECT count(*) FROM clima_mensal")).scalar()
    print(f"clima_mensal atualizada: {linhas} linhas em {time.perf_counter() - inicio:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
