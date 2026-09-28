from pathlib import Path
import argparse

import geopandas as gpd
import numpy as np
import xarray as xr
from shapely.vectorized import contains


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_ERA5 = Path("./data/era5_land")
PASTA_SHAPEFILE = Path("./data/BR_Municipios_2025")


# ============================================================
# UTILITÁRIOS
# ============================================================

def encontrar_coluna(gdf, possibilidades):
    for coluna in possibilidades:
        if coluna in gdf.columns:
            return coluna
    return None


# ============================================================
# CARREGAR ERA5 (OTIMIZADO COM DASK / CHUNKS)
# ============================================================

def carregar_dataset():
    arquivos = sorted(PASTA_ERA5.glob("*.grib"))

    print(f"{len(arquivos)} arquivos GRIB encontrados.")

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo .grib encontrado em: {PASTA_ERA5.resolve()}"
        )

    # Usa chunks para leitura lazy via Dask (evita estouro de RAM)
    datasets = [
        xr.open_dataset(arq, engine="cfgrib", chunks={"time": 24})
        for arq in arquivos
    ]

    if len(datasets) == 1:
        ds = datasets[0]
    else:
        ds = xr.concat(datasets, dim="time")

    print(f"\nTempos: {len(ds.time):,} | Lats: {len(ds.latitude):,} | Lons: {len(ds.longitude):,}")
    return ds


# ============================================================
# CARREGAR SHAPEFILE
# ============================================================

def carregar_shapefile():
    shp_files = list(PASTA_SHAPEFILE.rglob("*.shp"))

    if not shp_files:
        raise FileNotFoundError(
            f"Nenhum Shapefile encontrado em: {PASTA_SHAPEFILE.resolve()}"
        )

    shp = shp_files[0]
    print(f"\nShapefile: {shp}")
    gdf = gpd.read_file(shp)
    print(f"Polígonos encontrados: {len(gdf):,}")
    return gdf


# ============================================================
# ENCONTRAR MUNICÍPIO
# ============================================================

def encontrar_municipio(gdf, municipio=None, uf=None):
    col_municipio = encontrar_coluna(gdf, ["NM_MUN", "NM_MUNICIP", "NM_MUNICIPIO"])
    col_uf = encontrar_coluna(gdf, ["SIGLA_UF", "SG_UF", "UF"])

    if col_municipio is None:
        raise ValueError("Não foi encontrada a coluna do nome do município.")

    resultado = gdf.copy()

    if municipio:
        resultado = resultado[
            resultado[col_municipio].astype(str).str.contains(municipio, case=False, na=False)
        ]

    if uf:
        if col_uf is None:
            raise ValueError("A coluna da UF não foi encontrada no shapefile.")
        resultado = resultado[
            resultado[col_uf].astype(str).str.upper().eq(uf.upper())
        ]

    if resultado.empty:
        raise ValueError("Nenhum município encontrado.")

    if len(resultado) > 1:
        print("\nMais de um município encontrado:")
        for _, row in resultado.iterrows():
            nome = row[col_municipio]
            uf_nome = row[col_uf] if col_uf else ""
            print(f"  {nome} - {uf_nome}")
        raise ValueError("Especifique melhor o município usando --municipio e --uf.")

    return resultado.iloc[0]


# ============================================================
# FILTRO ESPACIAL (OTIMIZADO COM SHAPELY.VECTORIZED)
# ============================================================

def filtrar_por_poligono(ds, poligono):
    print("\n" + "=" * 100)
    print("FILTRO ESPACIAL")
    print("=" * 100)

    if poligono.crs is None:
        raise ValueError("O polígono não possui CRS.")

    poligono = poligono.to_crs("EPSG:4326")

    try:
        geometria = poligono.geometry.union_all()
    except AttributeError:
        geometria = poligono.geometry.unary_union

    minx, miny, maxx, maxy = geometria.bounds

    print(f"\nBounding box:\n  Longitude: {minx:.6f} → {maxx:.6f}\n  Latitude : {miny:.6f} → {maxy:.6f}")

    latitudes = ds.latitude.values
    longitudes = ds.longitude.values

    # O ERA5 costuma ter latitude decrescente (ex: 90 a -90). Trata ambos os casos:
    lat_min, lat_max = min(miny, maxy), max(miny, maxy)
    lon_min, lon_max = min(minx, maxx), max(minx, maxx)

    lat_mask = (latitudes >= lat_min) & (latitudes <= lat_max)
    lon_mask = (longitudes >= lon_min) & (longitudes <= lon_max)

    lat_indices = np.where(lat_mask)[0]
    lon_indices = np.where(lon_mask)[0]

    if len(lat_indices) == 0 or len(lon_indices) == 0:
        raise ValueError("O polígono não possui nenhum ponto da grade ERA5.")

    # 1. Recorta primeiro o dataset apenas pelo bounding box (Redução drástica de RAM)
    ds_sub = ds.isel(latitude=lat_indices, longitude=lon_indices)

    latitudes_box = ds_sub.latitude.values
    longitudes_box = ds_sub.longitude.values

    lon_grid, lat_grid = np.meshgrid(longitudes_box, latitudes_box)

    print(f"\nTestando {lon_grid.size:,} pontos do Bounding Box...")

    # 2. Teste vetorial em C extremamente rápido (shapely.vectorized)
    mask = contains(geometria, lon_grid, lat_grid)

    quantidade = int(mask.sum())
    print(f"Pontos dentro do polígono: {quantidade:,}")

    if quantidade == 0:
        # Se for um município pequeno demais para a grade ERA5 (~10km), escolhe o ponto mais próximo
        print("Aviso: Nenhum centroide de grade dentro do polígono. Selecionando o ponto ERA5 mais próximo do centro...")
        centro = geometria.centroid
        ds_sub = ds.sel(latitude=centro.y, longitude=centro.x, method="nearest")
        return ds_sub

    # 3. Mascarar o dataset recortado
    mask_xr = xr.DataArray(
        mask,
        dims=["latitude", "longitude"],
        coords={"latitude": latitudes_box, "longitude": longitudes_box}
    )

    # Aplica a máscara e remove bordas totalmente Nulas
    ds_filtrado = ds_sub.where(mask_xr, drop=True)

    print(f"\nGrade ERA5 após filtro:\n  Latitude : {len(ds_filtrado.latitude):,}\n  Longitude: {len(ds_filtrado.longitude):,}")

    return ds_filtrado


# ============================================================
# DEMAIS FUNÇÕES DE FILTRO E EXIBIÇÃO
# ============================================================

def filtrar_localizacao(ds, latitude=None, longitude=None):
    if latitude is None and longitude is None:
        return ds

    print("\n" + "=" * 100)
    print("FILTRO POR COORDENADA")
    print("=" * 100)

    if latitude is not None:
        ds = ds.sel(latitude=latitude, method="nearest")
        print(f"Latitude solicitada: {latitude} | Selecionada: {float(ds.latitude.values):.4f}")

    if longitude is not None:
        ds = ds.sel(longitude=longitude, method="nearest")
        print(f"Longitude solicitada: {longitude} | Selecionada: {float(ds.longitude.values):.4f}")

    return ds


def filtrar_data(ds, inicio=None, fim=None):
    if inicio is None and fim is None:
        return ds

    print("\n" + "=" * 100)
    print("FILTRO TEMPORAL")
    print("=" * 100)

    inicio = inicio or str(ds.time.values[0])
    fim = fim or str(ds.time.values[-1])

    print(f"Início: {inicio} | Fim: {fim}")

    ds = ds.sel(time=slice(inicio, fim))

    if len(ds.time) == 0:
        raise ValueError("Nenhum registro encontrado no período informado.")

    print(f"Registros encontrados: {len(ds.time):,}")
    return ds


def mostrar_variaveis(ds):
    print("\n" + "=" * 100)
    print("VARIÁVEIS")
    print("=" * 100)

    for nome in ds.data_vars:
        var = ds[nome]
        unidade = var.attrs.get("units", "")
        desc = var.attrs.get("long_name", "")
        print(f"\n{nome}\n  Dimensões: {var.dims}\n  Shape: {var.shape}")
        if unidade: print(f"  Unidade: {unidade}")
        if desc: print(f"  Descrição: {desc}")


def mostrar_dataset(ds):
    print("\n" + "=" * 100 + "\nDATASET\n" + "=" * 100)
    print(ds)


def mostrar_dados(ds, variavel=None, limit=20):
    print("\n" + "=" * 100 + "\nDADOS\n" + "=" * 100)
    if variavel:
        if variavel not in ds.data_vars:
            raise ValueError(f"Variável '{variavel}' não encontrada.")
        print(ds[variavel].isel(time=slice(0, limit)).compute())
    else:
        print("Use --variavel para visualizar uma variável específica.")


def mostrar_estatisticas(ds, variavel):
    if variavel not in ds.data_vars:
        raise ValueError(f"Variável '{variavel}' não encontrada.")

    da = ds[variavel]

    print("\n" + "=" * 100)
    print(f"ESTATÍSTICAS — {variavel}")
    print("=" * 100)

    # Executa o cálculo com compute() para carregar na RAM apenas o resultado resumido
    minimo, maximo, media, mediana = xr.compute(
        da.min(skipna=True),
        da.max(skipna=True),
        da.mean(skipna=True),
        da.median(skipna=True)
    )

    print(f"Mínimo : {float(minimo.values):.6f}")
    print(f"Máximo : {float(maximo.values):.6f}")
    print(f"Média  : {float(media.values):.6f}")
    print(f"Mediana: {float(mediana.values):.6f}")


def mostrar_resumo_temporal(ds, variavel):
    if variavel not in ds.data_vars:
        raise ValueError(f"Variável '{variavel}' não encontrada.")

    da = ds[variavel]
    dims_espaciais = [d for d in ["latitude", "longitude"] if d in da.dims]

    if dims_espaciais:
        serie = da.mean(dim=dims_espaciais, skipna=True)
    else:
        serie = da

    print("\n" + "=" * 100)
    print(f"SÉRIE TEMPORAL — {variavel}")
    print("=" * 100)
    print(serie.compute())


# ============================================================
# MAIN CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="CLI otimizada para explorar ERA5-Land.")
    parser.add_argument("--variavel", help="Nome da variável do ERA5.")
    parser.add_argument("--variaveis", action="store_true", help="Lista as variáveis.")
    parser.add_argument("--inicio", help="Data inicial (Ex: 2025-01-01)")
    parser.add_argument("--fim", help="Data final (Ex: 2025-01-31)")
    parser.add_argument("--latitude", type=float, help="Latitude.")
    parser.add_argument("--longitude", type=float, help="Longitude.")
    parser.add_argument("--municipio", help="Nome do município.")
    parser.add_argument("--uf", help="UF do município.")
    parser.add_argument("--shapefile", type=Path, help="Shapefile personalizado.")
    parser.add_argument("--stats", action="store_true", help="Estatísticas.")
    parser.add_argument("--serie", action="store_true", help="Série temporal.")
    parser.add_argument("--dataset", action="store_true", help="Resumo do dataset.")
    parser.add_argument("--limit", type=int, default=20, help="Limite de exibição.")

    args = parser.parse_args()

    ds = carregar_dataset()
    ds = filtrar_data(ds, inicio=args.inicio, fim=args.fim)

    if args.municipio:
        gdf = carregar_shapefile()
        mun = encontrar_municipio(gdf, municipio=args.municipio, uf=args.uf)
        poligono = gpd.GeoDataFrame([mun], geometry="geometry", crs=gdf.crs)
        ds = filtrar_por_poligono(ds, poligono)

    elif args.shapefile:
        if not args.shapefile.exists():
            raise FileNotFoundError(f"Shapefile não encontrado: {args.shapefile}")
        gdf = gpd.read_file(args.shapefile)
        ds = filtrar_por_poligono(ds, gdf)

    elif args.latitude is not None or args.longitude is not None:
        ds = filtrar_localizacao(ds, latitude=args.latitude, longitude=args.longitude)

    if args.variaveis:
        mostrar_variaveis(ds)

    if args.dataset:
        mostrar_dataset(ds)

    if args.stats:
        if not args.variavel:
            raise ValueError("--stats exige --variavel.")
        mostrar_estatisticas(ds, args.variavel)

    if args.serie:
        if not args.variavel:
            raise ValueError("--serie exige --variavel.")
        mostrar_resumo_temporal(ds, args.variavel)

    if args.variavel and not (args.stats or args.serie):
        mostrar_dados(ds, variavel=args.variavel, limit=args.limit)

    if not any([args.variavel, args.variaveis, args.dataset, args.stats, args.serie]):
        mostrar_dataset(ds)


if __name__ == "__main__":
    main()