import argparse
import csv
import math
import re
from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import xarray as xr
from sqlalchemy import text

from app.database import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "era5_land"
FILE_PATTERN = re.compile(r"era5_land_(\d{4})_(\d{2})\.grib$")
COPY_SQL = """
COPY registro_climatico
    (codigo_ibge, datetime, umidade, temperatura, precipitacao)
FROM STDIN
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Carrega ERA5-Land no PostgreSQL em transacoes mensais."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Pasta com os GRIBs (padrao: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        help="Data inicial UTC inclusiva (AAAA-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        help="Data final UTC inclusiva (AAAA-MM-DD)",
    )
    parser.add_argument(
        "--enso-only",
        action="store_true",
        help="Atualiza somente os dados ENSO do CSV, sem processar arquivos GRIB",
    )
    args = parser.parse_args()
    if args.start_date and args.end_date and args.start_date > args.end_date:
        parser.error("--start-date nao pode ser posterior a --end-date")
    return args


def load_municipalities():
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT codigo_ibge, latitude, longitude
                FROM municipio
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY codigo_ibge
                """
            )
        ).all()

    if not rows:
        raise RuntimeError("Nenhum municipio com latitude/longitude no banco.")

    codes = np.asarray([row.codigo_ibge for row in rows], dtype=np.int64)
    latitudes = np.asarray([float(row.latitude) for row in rows], dtype=np.float64)
    longitudes = np.asarray([float(row.longitude) for row in rows], dtype=np.float64)
    return codes, latitudes, longitudes


def nearest_indices(grid_coordinates, targets):
    order = np.argsort(grid_coordinates)
    sorted_coordinates = grid_coordinates[order]
    insertion = np.searchsorted(sorted_coordinates, targets)
    upper = np.clip(insertion, 0, len(sorted_coordinates) - 1)
    lower = np.clip(insertion - 1, 0, len(sorted_coordinates) - 1)
    choose_upper = (
        np.abs(sorted_coordinates[upper] - targets)
        < np.abs(sorted_coordinates[lower] - targets)
    )
    return order[np.where(choose_upper, upper, lower)]


def to_utc_datetime(value):
    seconds = int(np.datetime64(value, "s").astype(np.int64))
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def finite_values(values):
    result = np.asarray(values, dtype=np.float64)
    result = result.copy()
    result[(~np.isfinite(result)) | (np.abs(result) > 1e20)] = np.nan
    return result


def db_float(value):
    number = float(value)
    return number if math.isfinite(number) else None


def read_enso_csv(path):
    required_columns = {"year", "month", "oni"}
    records_by_month = {}

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns - set(reader.fieldnames or ())
        if missing_columns:
            raise ValueError(
                f"Colunas ENSO ausentes em {path}: {', '.join(sorted(missing_columns))}"
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                year = int(row["year"])
                month = int(row["month"])
                if not 1 <= month <= 12:
                    raise ValueError("mês fora do intervalo 1-12")
                oni_value = row["oni"].strip()
                records_by_month[(year, month)] = {
                    "year": year,
                    "month": month,
                    "enso_index": db_float(oni_value) if oni_value else None,
                }
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Registro ENSO inválido na linha {line_number} de {path}: {error}"
                ) from error

    return [records_by_month[key] for key in sorted(records_by_month)]


def load_enso_data(data_dir):
    path = data_dir / "registro_era5_enso.csv"
    if not path.is_file():
        print(f"CSV ENSO não encontrado; carga ENSO ignorada: {path}")
        return 0

    records = read_enso_csv(path)
    if not records:
        raise ValueError(f"Nenhum registro ENSO encontrado em {path}")

    statement = text(
        """
        INSERT INTO enso_mensal (year, month, enso_index)
        VALUES (:year, :month, :enso_index)
        ON CONFLICT (year, month) DO UPDATE SET
            enso_index = EXCLUDED.enso_index
        """
    )
    with engine.begin() as connection:
        connection.execute(statement, records)

    print(f"ENSO: {len(records):,} registros mensais inseridos/atualizados.")
    return len(records)


def relative_humidity(temperature_kelvin, dewpoint_kelvin):
    temperature_celsius = temperature_kelvin - 273.15
    dewpoint_celsius = dewpoint_kelvin - 273.15
    vapor_ratio = (
        17.625 * dewpoint_celsius / (243.04 + dewpoint_celsius)
        - 17.625 * temperature_celsius / (243.04 + temperature_celsius)
    )
    return np.clip(100.0 * np.exp(vapor_ratio), 0.0, 100.0)


def next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


def month_overlaps_dates(year, month, start_date, end_date):
    month_start = date(year, month, 1)
    next_year, next_month_number = next_month(year, month)
    month_end = date(next_year, next_month_number, 1) - timedelta(days=1)
    return not (
        (start_date is not None and month_end < start_date)
        or (end_date is not None and month_start > end_date)
    )


def process_file(
    path,
    year,
    month,
    codes,
    municipality_latitudes,
    municipality_longitudes,
    start_date,
    end_date,
):
    started = perf_counter()
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    next_year, next_month_number = next_month(year, month)
    month_end = datetime(next_year, next_month_number, 1, tzinfo=timezone.utc)

    delete_start = month_start
    delete_end = month_end
    if start_date is not None:
        delete_start = max(
            delete_start,
            datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        )
    if end_date is not None:
        delete_end = min(
            delete_end,
            datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
        )

    inserted = 0
    connection = engine.raw_connection()
    try:
        with xr.open_dataset(
            path,
            engine="cfgrib",
            chunks={"time": 1},
            backend_kwargs={"indexpath": ""},
        ) as dataset:
            required_variables = {"t2m", "d2m", "tp"}
            missing = required_variables - set(dataset.data_vars)
            if missing:
                raise ValueError(
                    f"Variaveis ausentes em {path.name}: {', '.join(sorted(missing))}"
                )

            step_hours = dataset.step.values.astype("timedelta64[h]").astype(np.int64)
            step_indices = {int(hours): index for index, hours in enumerate(step_hours)}
            if 12 not in step_indices or 24 not in step_indices:
                raise ValueError(
                    f"Passos ERA5 inesperados em {path.name}: {step_hours.tolist()}"
                )

            latitude_indices = nearest_indices(
                dataset.latitude.values,
                municipality_latitudes,
            )
            longitude_indices = nearest_indices(
                dataset.longitude.values,
                municipality_longitudes,
            )
            precipitation_12h_index = step_indices[12]

            cursor = connection.cursor()
            try:
                cursor.execute(
                    "DELETE FROM registro_climatico "
                    "WHERE datetime >= %s AND datetime < %s",
                    (delete_start, delete_end),
                )

                with cursor.copy(COPY_SQL) as copy:
                    for time_index in range(dataset.sizes["time"]):
                        frame = dataset.isel(time=time_index).compute()
                        temperature_grid = frame["t2m"].values
                        dewpoint_grid = frame["d2m"].values
                        precipitation_grid = frame["tp"].values

                        for step_index, hours in enumerate(step_hours):
                            valid_time = to_utc_datetime(
                                frame["valid_time"].values[step_index]
                            )
                            if valid_time.year != year or valid_time.month != month:
                                continue
                            if start_date is not None and valid_time.date() < start_date:
                                continue
                            if end_date is not None and valid_time.date() > end_date:
                                continue

                            temperature = finite_values(
                                temperature_grid[
                                    step_index,
                                    latitude_indices,
                                    longitude_indices,
                                ]
                            )
                            dewpoint = finite_values(
                                dewpoint_grid[
                                    step_index,
                                    latitude_indices,
                                    longitude_indices,
                                ]
                            )
                            humidity = finite_values(
                                relative_humidity(temperature, dewpoint)
                            )

                            precipitation = finite_values(
                                precipitation_grid[
                                    step_index,
                                    latitude_indices,
                                    longitude_indices,
                                ]
                            )
                            if hours == 24:
                                precipitation -= finite_values(
                                    precipitation_grid[
                                        precipitation_12h_index,
                                        latitude_indices,
                                        longitude_indices,
                                    ]
                                )
                            precipitation = finite_values(
                                np.maximum(precipitation, 0.0) * 1000.0
                            )

                            for code, humid, temp, rain in zip(
                                codes,
                                humidity,
                                temperature,
                                precipitation,
                                strict=True,
                            ):
                                copy.write_row(
                                    (
                                        int(code),
                                        valid_time,
                                        db_float(humid),
                                        db_float(temp - 273.15),
                                        db_float(rain),
                                    )
                                )
                            inserted += len(codes)

                if inserted == 0:
                    raise RuntimeError(f"Nenhum horario valido em {path.name}.")
                connection.commit()
            finally:
                cursor.close()
    except Exception as error:
        connection.rollback()
        raise RuntimeError(
            f"Falha ao processar {path.name}; a transacao do mes foi revertida."
        ) from error
    finally:
        connection.close()

    elapsed = perf_counter() - started
    print(f"{path.name}: {inserted:,} registros em {elapsed:.1f}s")
    return inserted


def main():
    args = parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    if args.enso_only:
        if load_enso_data(data_dir) == 0:
            raise FileNotFoundError(
                f"CSV ENSO não encontrado em {data_dir / 'registro_era5_enso.csv'}"
            )
        return

    enso_count = load_enso_data(data_dir)
    paths = sorted(data_dir.glob("*.grib"))
    if not paths:
        if enso_count:
            print("Nenhum GRIB encontrado; apenas os dados ENSO foram atualizados.")
            return
        raise FileNotFoundError(f"Nenhum GRIB encontrado em {data_dir}")

    codes, latitudes, longitudes = load_municipalities()
    selected_files = []
    for path in paths:
        match = FILE_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        year, month = map(int, match.groups())
        if month_overlaps_dates(year, month, args.start_date, args.end_date):
            selected_files.append((path, year, month))

    if not selected_files:
        if enso_count:
            print("Nenhum GRIB corresponde ao período; dados ENSO foram atualizados.")
            return
        raise FileNotFoundError("Nenhum GRIB corresponde ao periodo solicitado.")

    print(
        f"Municipios: {len(codes):,} | arquivos: {len(selected_files)} | "
        "frequencia: 00:00 e 12:00 UTC"
    )
    print(
        "Unidades gravadas: umidade relativa (%), temperatura (C), "
        "precipitacao por intervalo de 12h (mm)."
    )

    total_inserted = 0
    for index, (path, year, month) in enumerate(selected_files, start=1):
        print(f"[{index}/{len(selected_files)}] Processando {path.name}...")
        total_inserted += process_file(
            path,
            year,
            month,
            codes,
            latitudes,
            longitudes,
            args.start_date,
            args.end_date,
        )

    print(f"Concluido: {total_inserted:,} registros climáticos gravados.")


if __name__ == "__main__":
    main()