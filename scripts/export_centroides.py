from pathlib import Path
import argparse
import time

import psycopg
from psycopg import sql

from app.database import DATABASE_URL


# ============================================================
# CONFIGURAÇÃO
# ============================================================

UFS_PADRAO = ["BA", "GO", "RS", "AM"]
ARQUIVO_PADRAO = Path("./data/clima_centroides_ba_go_rs_am.csv")

# registro_climatico guarda a célula ERA5-Land mais próxima do centróide de
# cada município. O filtro por UF é resolvido na tabela pequena
# (municipio_details) e aplicado via hash join sobre um seq scan paralelo da
# tabela climática, mais barato que milhares de buscas no índice para ~20%
# das linhas. O COPY formata o CSV no servidor e o arquivo é gravado em
# streaming, sem materializar as linhas no Python.
CONSULTA = """
COPY (
    SELECT
        r.datetime,
        d.codigo_ibge,
        d.municipio,
        d.uf,
        r.temperatura,
        r.umidade,
        r.precipitacao
    FROM registro_climatico AS r
    JOIN municipio_details AS d USING (codigo_ibge)
    WHERE d.uf = ANY({ufs})
    ORDER BY r.datetime, d.uf, d.municipio
) TO STDOUT WITH (FORMAT csv, HEADER true)
"""


# ============================================================
# EXPORTAÇÃO
# ============================================================

def exportar(ufs, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    consulta = sql.SQL(CONSULTA).format(ufs=sql.Literal(ufs))

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        # Datas em UTC; JIT não compensa para um plano simples de scan/sort e
        # work_mem maior mantém a ordenação em memória.
        cur.execute("SET LOCAL TimeZone = 'UTC'")
        cur.execute("SET LOCAL jit = off")
        cur.execute("SET LOCAL work_mem = '512MB'")

        with destino.open("wb") as arquivo, cur.copy(consulta) as copy:
            for bloco in copy:
                arquivo.write(bloco)


def main():
    parser = argparse.ArgumentParser(
        description="Exporta o clima dos centróides municipais para CSV."
    )
    parser.add_argument("--uf", nargs="+", default=UFS_PADRAO)
    parser.add_argument("--saida", type=Path, default=ARQUIVO_PADRAO)
    args = parser.parse_args()

    ufs = [uf.upper() for uf in args.uf]
    inicio = time.perf_counter()
    exportar(ufs, args.saida)

    tamanho = args.saida.stat().st_size / 1024**2
    print(
        f"{args.saida} ({tamanho:,.1f} MiB) gerado em "
        f"{time.perf_counter() - inicio:,.1f}s para UFs: {', '.join(ufs)}"
    )


if __name__ == "__main__":
    main()
