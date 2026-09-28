import argparse
import geopandas as gpd
import cdsapi
import os
import calendar
import pandas as pd
import requests
from io import StringIO

parser = argparse.ArgumentParser()
parser.add_argument(
    "--enso-only",
    action="store_true",
    help="Baixa e grava somente a série ENSO, sem ler shapefile ou baixar ERA5",
)
args = parser.parse_args()

# ============================================================
# 1. Ler shapefile dos municípios
# ============================================================

area = None
if not args.enso_only:
    shapefile = "./data/BR_Municipios_2025/BR_Municipios_2025.shp"
    gdf = gpd.read_file(shapefile)
    print("CRS original:", gdf.crs)
    if gdf.crs is None:
        raise ValueError(
            "O shapefile não possui CRS definido. "
            "Defina o CRS correto antes de continuar."
        )

    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    print("CRS utilizado no ERA5:", gdf_wgs84.crs)
    minx, miny, maxx, maxy = gdf_wgs84.total_bounds
    area = [maxy, minx, miny, maxx]
    print("\nÁrea para o ERA5:")
    print(area)


# ============================================================
# 5. Função para carregar ENSO do NOAA
#
# Utiliza a série histórica do ONI.
#
# O ONI é mantido como valor numérico contínuo.
# ============================================================

def carregar_enso_noaa():

    url = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

    print("\n" + "=" * 60)
    print("BAIXANDO DADOS ENSO DO NOAA")
    print("=" * 60)

    try:

        response = requests.get(
            url,
            timeout=30
        )

        response.raise_for_status()

    except Exception as e:

        raise RuntimeError(
            "Não foi possível acessar os dados ENSO do NOAA. "
            f"Erro: {e}"
        )

    # --------------------------------------------------------
    # Ler o arquivo ASCII tabular do NOAA
    # --------------------------------------------------------
    try:
        enso = pd.read_csv(StringIO(response.text), sep=r"\s+")
    except Exception as e:
        raise RuntimeError(
            f"Não foi possível interpretar o arquivo ENSO do NOAA. Erro: {e}"
        )

    required_columns = {"SEAS", "YR", "ANOM"}
    missing_columns = required_columns - set(enso.columns)
    if missing_columns:
        raise RuntimeError(
            "Colunas ausentes no arquivo ENSO do NOAA: "
            f"{', '.join(sorted(missing_columns))}"
        )

    enso["YR"] = pd.to_numeric(enso["YR"], errors="coerce")
    enso["ANOM"] = pd.to_numeric(enso["ANOM"], errors="coerce")
    enso = enso.dropna(subset=["YR", "ANOM"])
    print(f"Série ENSO encontrada com {len(enso)} estações.")

    # --------------------------------------------------------
    # Estações trimestrais do ONI
    #
    # Usamos o mês central de cada estação:
    #
    # DJF -> Janeiro
    # JFM -> Fevereiro
    # FMA -> Março
    # MAM -> Abril
    # AMJ -> Maio
    # MJJ -> Junho
    # JJA -> Julho
    # JAS -> Agosto
    # ASO -> Setembro
    # SON -> Outubro
    # OND -> Novembro
    # NDJ -> Dezembro
    # --------------------------------------------------------

    seasons = {
        "DJF": 1,
        "JFM": 2,
        "FMA": 3,
        "MAM": 4,
        "AMJ": 5,
        "MJJ": 6,
        "JJA": 7,
        "JAS": 8,
        "ASO": 9,
        "SON": 10,
        "OND": 11,
        "NDJ": 12,
    }

    registros = []

    # --------------------------------------------------------
    # Transformar tabela NOAA em formato mensal
    # --------------------------------------------------------

    for row in enso.itertuples(index=False):
        season = str(row.SEAS).strip()
        if season not in seasons:
            continue
        registros.append(
            {
                "year": int(row.YR),
                "month": seasons[season],
                "oni": float(row.ANOM),
            }
        )

    # --------------------------------------------------------
    # DataFrame final
    # --------------------------------------------------------

    enso_df = pd.DataFrame(
        registros
    )

    # --------------------------------------------------------
    # Manter somente período do projeto
    # --------------------------------------------------------

    enso_df = enso_df[
        (enso_df["year"] >= 2015) &
        (enso_df["year"] <= 2025)
    ].copy()

    # --------------------------------------------------------
    # Ordenar
    # --------------------------------------------------------

    enso_df = enso_df.sort_values(
        ["year", "month"]
    ).reset_index(drop=True)

    print(
        "\nPeríodo ENSO carregado:"
    )

    if not enso_df.empty:

        print(
            f"{enso_df['year'].min()} "
            f"até "
            f"{enso_df['year'].max()}"
        )

    print(
        f"Total de registros: "
        f"{len(enso_df)}"
    )

    # --------------------------------------------------------
    # Mostrar resumo
    # --------------------------------------------------------

    print("\nResumo ENSO:")

    print(
        enso_df[
            [
                "year",
                "month",
                "oni"
            ]
        ].head(12)
    )

    return enso_df


# ============================================================
# 6. Carregar ENSO
#
# Isso acontece uma única vez por execução.
# ============================================================

enso_df = carregar_enso_noaa()

if args.enso_only:
    output_dir = "./data/era5_land"
    os.makedirs(output_dir, exist_ok=True)
    registro_file = os.path.join(output_dir, "registro_era5_enso.csv")
    enso_df.to_csv(registro_file, index=False)
    print(f"CSV ENSO salvo em: {registro_file}")
    raise SystemExit(0)


# ============================================================
# 7. Criar dicionário para acesso rápido
#
# Chave:
#
# (ano, mês)
#
# Exemplo:
#
# (2019, 7)
#
# ============================================================

enso_dict = {
    (int(row["year"]), int(row["month"])): row["oni"]
    for _, row in enso_df.iterrows()
}


# ============================================================
# 8. Configuração do CDS
# ============================================================

print("\n" + "=" * 60)
print("CONFIGURANDO CDS")
print("=" * 60)

client = cdsapi.Client()

dataset = "reanalysis-era5-land"

output_dir = "./data/era5_land"

# Criar diretório caso não exista
os.makedirs(
    output_dir,
    exist_ok=True
)

print(
    "\nDiretório de saída:"
)

print(output_dir)


# ============================================================
# 9. Arquivo de registro ENSO
# ============================================================

registro_file = os.path.join(
    output_dir,
    "registro_era5_enso.csv"
)

print(
    "\nArquivo de registro ENSO:"
)

print(registro_file)


# ============================================================
# 10. Carregar registro existente
#
# Se o CSV já existir, ele será utilizado como base.
# O registro de cada mês será posteriormente substituído
# pelos dados ENSO mais recentes.
# ============================================================

if os.path.isfile(registro_file):

    print(
        "\n[REGISTRO] CSV existente encontrado."
    )

    try:

        registro_df = pd.read_csv(
            registro_file
        )

        print(
            f"[REGISTRO] "
            f"{len(registro_df)} registros carregados."
        )

    except Exception as e:

        print(
            "[AVISO] Não foi possível ler o CSV existente."
        )

        print(
            f"Erro: {e}"
        )

        print(
            "[REGISTRO] Criando um novo registro."
        )

        registro_df = pd.DataFrame(
            columns=[
                "year",
                "month",
                "arquivo",
                "oni"
            ]
        )

else:

    print(
        "\n[REGISTRO] CSV ainda não existe."
    )

    registro_df = pd.DataFrame(
        columns=[
            "year",
            "month",
            "arquivo",
            "oni"
        ]
    )

registro_df = registro_df.drop(
    columns=["el_nino", "la_nina"],
    errors="ignore",
)


# ============================================================
# 11. Garantir tipos das colunas existentes
# ============================================================

if not registro_df.empty:

    registro_df["year"] = pd.to_numeric(
        registro_df["year"],
        errors="coerce"
    )

    registro_df["month"] = pd.to_numeric(
        registro_df["month"],
        errors="coerce"
    )

    registro_df = registro_df.dropna(
        subset=[
            "year",
            "month"
        ]
    )

    registro_df["year"] = (
        registro_df["year"]
        .astype(int)
    )

    registro_df["month"] = (
        registro_df["month"]
        .astype(int)
    )


# ============================================================
# 12. Download ERA5
#
# Período:
#
# 2015 até 2025
# ============================================================

for year in range(
    2015,
    2026
):

    for month in range(
        1,
        13
    ):

        print("\n" + "=" * 60)

        print(
            f"PROCESSANDO "
            f"{year}-{month:02d}"
        )

        print("=" * 60)

        # ----------------------------------------------------
        # Número de dias do mês
        # ----------------------------------------------------

        days = [

            f"{day:02d}"

            for day in range(
                1,
                calendar.monthrange(
                    year,
                    month
                )[1] + 1
            )

        ]

        # ----------------------------------------------------
        # Nome do arquivo ERA5
        # ----------------------------------------------------

        filename = os.path.join(

            output_dir,

            f"era5_land_"
            f"{year}_"
            f"{month:02d}.grib"

        )

        # ====================================================
        # 13. Obter informações ENSO
        #
        # IMPORTANTE:
        #
        # Essa parte acontece SEMPRE.
        #
        # Mesmo que o GRIB já exista.
        # ====================================================

        oni = enso_dict.get((year, month))

        print(
            f"ONI       : {oni}"
        )


        # ====================================================
        # 14. Verificar se o GRIB já existe
        # ====================================================

        if os.path.isfile(filename):

            print(
                "\n[EXISTE] "
                "Arquivo ERA5 já existe:"
            )

            print(filename)

            print(
                "[PULANDO DOWNLOAD]"
            )

            print(
                "O arquivo GRIB não será "
                "baixado novamente."
            )

        else:

            # =================================================
            # 15. Montar requisição CDS
            # =================================================

            request = {

                "variable": [

                    "2m_temperature",

                    "2m_dewpoint_temperature",

                    "total_precipitation"

                ],

                "year": str(year),

                "month": f"{month:02d}",

                "day": days,

                "time": [

                    "00:00",

                    "12:00"

                ],

                "data_format": "grib",

                "download_format": "unarchived",

                "area": area

            }

            # =================================================
            # 16. Fazer download
            # =================================================

            print(
                "\n[DOWNLOAD]"
            )

            print(
                f"Ano/mês: "
                f"{year}-{month:02d}"
            )

            print(
                f"Área: "
                f"{area}"
            )

            print(
                f"Arquivo: "
                f"{filename}"
            )

            try:

                client.retrieve(

                    dataset,

                    request

                ).download(

                    filename

                )

                print(
                    f"\n[OK] "
                    f"ERA5 salvo:"
                )

                print(filename)

            except Exception as e:

                print(
                    "\n" + "!" * 60
                )

                print(
                    f"[ERRO] Falha ao baixar "
                    f"{year}-{month:02d}"
                )

                print(
                    f"Erro: {e}"
                )

                print(
                    "!" * 60
                )

                # --------------------------------------------
                # Remover arquivo parcial
                # --------------------------------------------

                if os.path.isfile(filename):

                    try:

                        os.remove(
                            filename
                        )

                        print(
                            "[OK] Arquivo incompleto "
                            "removido:"
                        )

                        print(
                            filename
                        )

                    except Exception as remove_error:

                        print(
                            "[ERRO] Não foi possível "
                            "remover o arquivo:"
                        )

                        print(
                            remove_error
                        )

                print(
                    "[INFO] "
                    "Mesmo com a falha no download, "
                    "o ENSO será atualizado."
                )


        # ====================================================
        # 17. Atualizar registro ENSO
        #
        # ESTA PARTE ACONTECE SEMPRE.
        #
        # Portanto:
        #
        # GRIB existe?
        #     -> não baixa
        #     -> atualiza ENSO
        #
        # GRIB não existe?
        #     -> baixa
        #     -> atualiza ENSO
        # ====================================================

        novo_registro = pd.DataFrame([

            {

                "year": year,

                "month": month,

                "arquivo": filename,

                "oni": oni

            }

        ])


        # ====================================================
        # 18. Remover registro anterior do mesmo ano/mês
        # ====================================================

        if not registro_df.empty:

            registro_df = registro_df[

                ~(

                    (registro_df["year"] == year)

                    &

                    (registro_df["month"] == month)

                )

            ]


        # ====================================================
        # 19. Adicionar registro ENSO atualizado
        # ====================================================

        registro_df = pd.concat(

            [

                registro_df,

                novo_registro

            ],

            ignore_index=True

        )


        # ====================================================
        # 20. Ordenar registros
        # ====================================================

        registro_df = registro_df.sort_values(

            [
                "year",
                "month"
            ]

        ).reset_index(

            drop=True

        )


        # ====================================================
        # 21. Salvar registro imediatamente
        #
        # Se o programa for interrompido no meio,
        # os meses já processados continuam registrados.
        # ====================================================

        registro_df.to_csv(

            registro_file,

            index=False

        )


        print(
            "\n[ENSO ATUALIZADO]"
        )

        print(
            f"{year}-{month:02d}"
        )

        print(
            f"ONI={oni}"
        )

        print(
            f"Registro: {registro_file}"
        )


# ============================================================
# 22. Finalização
# ============================================================

print("\n" + "=" * 60)

print(
    "PROCESSO FINALIZADO"
)

print("=" * 60)

print(
    "\nArquivos ERA5:"
)

print(
    output_dir
)

print(
    "\nRegistro ENSO:"
)

print(
    registro_file
)

print(
    "\nTotal de registros ENSO:"
)

print(
    len(registro_df)
)
