import argparse
import math
from pathlib import Path
from time import perf_counter

import pyarrow.parquet as pq
from sqlalchemy import text

from app.database import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET = PROJECT_ROOT / "data" / "municipios.parquet"
DEFAULT_BATCH_SIZE = 32
STATE_BY_IBGE_PREFIX = {
    "43": ("RS", "Rio Grande do Sul"),
    "51": ("MT", "Mato Grosso"),
}

PARQUET_COLUMNS = (
    "codigo_ibge",
    "municipio",
    "uf",
    "estado",
    "regiao",
    "mesorregiao",
    "microrregiao",
    "populacao",
    "ano_populacao",
    "bioma",
    "geomorfologia",
    "regiao_geomorfologica",
    "dominio_geomorfologico",
    "area_km2",
    "latitude",
    "longitude",
    "geometry",
)

INSERT_MUNICIPIO = text(
    """
    INSERT INTO municipio (
        codigo_ibge, latitude, longitude, geometry
    ) VALUES (
        :codigo_ibge,
        :latitude,
        :longitude,
        ST_Transform(
            ST_SetSRID(ST_GeomFromWKB(:geometry), :source_srid),
            4326
        )
    )
    ON CONFLICT (codigo_ibge) DO UPDATE SET
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        geometry = EXCLUDED.geometry
    """
)

INSERT_DETAILS = text(
    """
    INSERT INTO municipio_details (
        codigo_ibge, municipio, uf, estado, regiao, mesorregiao,
        microrregiao, populacao, ano_populacao, bioma, geomorfologia,
        regiao_geomorfologica, dominio_geomorfologico, area_km2
    ) VALUES (
        :codigo_ibge, :municipio, :uf, :estado, :regiao, :mesorregiao,
        :microrregiao, :populacao, :ano_populacao, :bioma, :geomorfologia,
        :regiao_geomorfologica, :dominio_geomorfologico, :area_km2
    )
    ON CONFLICT (codigo_ibge) DO UPDATE SET
        municipio = EXCLUDED.municipio,
        uf = EXCLUDED.uf,
        estado = EXCLUDED.estado,
        regiao = EXCLUDED.regiao,
        mesorregiao = EXCLUDED.mesorregiao,
        microrregiao = EXCLUDED.microrregiao,
        populacao = EXCLUDED.populacao,
        ano_populacao = EXCLUDED.ano_populacao,
        bioma = EXCLUDED.bioma,
        geomorfologia = EXCLUDED.geomorfologia,
        regiao_geomorfologica = EXCLUDED.regiao_geomorfologica,
        dominio_geomorfologico = EXCLUDED.dominio_geomorfologico,
        area_km2 = EXCLUDED.area_km2
    """
)


def optional_int(value):
    if value is None:
        return None

    number = float(value)
    return int(number) if math.isfinite(number) else None


def optional_float(value):
    if value is None:
        return None

    number = float(value)
    return number if math.isfinite(number) else None


def required_text(value, column, code):
    if value is None or not value.strip():
        raise ValueError(
            f"Campo obrigatorio vazio: {column}, codigo_ibge={code}"
        )
    return value


def build_records(rows, source_srid):
    municipalities = []
    details = []

    for row in rows:
        code = int(row["codigo_ibge"])
        geometry = row["geometry"]
        if not isinstance(geometry, (bytes, bytearray, memoryview)) or not geometry:
            raise ValueError(f"Geometria WKB ausente: codigo_ibge={code}")
        fallback_uf, fallback_state = STATE_BY_IBGE_PREFIX.get(
            str(code)[:2],
            (None, None),
        )

        municipalities.append(
            {
                "codigo_ibge": code,
                "latitude": optional_float(row["latitude"]),
                "longitude": optional_float(row["longitude"]),
                "geometry": geometry,
                "source_srid": source_srid,
            }
        )
        details.append(
            {
                "codigo_ibge": code,
                "municipio": required_text(row["municipio"], "municipio", code),
                "uf": required_text(row["uf"] or fallback_uf, "uf", code),
                "estado": required_text(
                    row["estado"] or fallback_state,
                    "estado",
                    code,
                ),
                "regiao": row["regiao"],
                "mesorregiao": row["mesorregiao"],
                "microrregiao": row["microrregiao"],
                "populacao": optional_int(row["populacao"]),
                "ano_populacao": optional_int(row["ano_populacao"]),
                "bioma": row["bioma"],
                "geomorfologia": row["geomorfologia"],
                "regiao_geomorfologica": row["regiao_geomorfologica"],
                "dominio_geomorfologico": row["dominio_geomorfologico"],
                "area_km2": optional_float(row["area_km2"]),
            }
        )

    return municipalities, details


def parse_args():
    parser = argparse.ArgumentParser(
        description="Carrega municipios do Parquet para o PostgreSQL/PostGIS em lotes."
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=DEFAULT_PARQUET,
        help=f"Arquivo de entrada (padrao: {DEFAULT_PARQUET})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Linhas por transacao (padrao: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--source-srid",
        type=int,
        default=4674,
        help="SRID das geometrias no Parquet (padrao: EPSG:4674)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limita linhas para uma carga de teste",
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size precisa ser maior que zero")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit precisa ser maior que zero")

    return args


def main():
    args = parse_args()
    parquet_path = args.parquet.expanduser().resolve()
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Parquet nao encontrado: {parquet_path}")

    parquet_file = pq.ParquetFile(parquet_path)
    missing_columns = set(PARQUET_COLUMNS) - set(parquet_file.schema_arrow.names)
    if missing_columns:
        raise ValueError(
            "Colunas ausentes no Parquet: " + ", ".join(sorted(missing_columns))
        )

    total_rows = parquet_file.metadata.num_rows
    expected_rows = min(total_rows, args.limit or total_rows)
    print(
        f"Arquivo: {parquet_path}\n"
        f"Registros: {expected_rows:,} | lote: {args.batch_size} | "
        f"geometrias: EPSG:{args.source_srid} -> EPSG:4326"
    )

    processed = 0
    started = perf_counter()

    for batch in parquet_file.iter_batches(
        batch_size=args.batch_size,
        columns=list(PARQUET_COLUMNS),
        use_threads=False,
    ):
        rows = batch.to_pylist()
        if args.limit is not None:
            rows = rows[: expected_rows - processed]
        if not rows:
            break

        municipalities, details = build_records(rows, args.source_srid)
        try:
            with engine.begin() as connection:
                connection.execute(INSERT_MUNICIPIO, municipalities)
                connection.execute(INSERT_DETAILS, details)
        except Exception as error:
            codes = [record["codigo_ibge"] for record in municipalities]
            raise RuntimeError(
                f"Falha no lote com codigos {codes[0]} a {codes[-1]}; "
                "os lotes anteriores foram confirmados e podem ser retomados."
            ) from error

        processed += len(rows)
        percent = processed / expected_rows * 100 if expected_rows else 100
        print(
            f"\rImportados {processed:,}/{expected_rows:,} ({percent:.1f}%)",
            end="",
            flush=True,
        )

    elapsed = perf_counter() - started
    print(f"\nConcluido em {elapsed:.1f}s.")


if __name__ == "__main__":
    main()