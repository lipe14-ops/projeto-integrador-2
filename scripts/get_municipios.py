from pathlib import Path
import zipfile
from io import BytesIO

import requests
import pandas as pd
import geopandas as gpd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

MUNICIPIOS_DIR = Path(
    "./data/BR_Municipios_2025"
)

URL_MUNICIPIOS = (
    "https://geoftp.ibge.gov.br/"
    "organizacao_do_territorio/"
    "malhas_territoriais/"
    "malhas_municipais/"
    "municipio_2025/"
    "Brasil/"
    "BR_Municipios_2025.zip"
)

MUNICIPIOS_ZIP = Path(
    "./data/BR_Municipios_2025.zip"
)

MUNICIPIOS_DIR = Path(
    "./data/BR_Municipios_2025"
)

ARQUIVO_PARQUET = Path(
    "./data/municipios.parquet"
)

ARQUIVO_GPKG = Path(
    "./data/municipios.gpkg"
)

GEOMORFOLOGIA_DIR = Path(
    "./data/geomorfologia"
)

GEOMORFOLOGIA_ZIP = Path(
    "./data/geom_area.zip"
)

URL_GEOMORFOLOGIA = (
    "https://geoftp.ibge.gov.br/"
    "informacoes_ambientais/"
    "geomorfologia/"
    "vetores/"
    "escala_250_mil/"
    "versao_2025/"
    "geom_area.zip"
)

ANO_POPULACAO = 2026


# ============================================================
# URLs IBGE
# ============================================================

# Divisão Territorial Brasileira 2025
URL_DTB = (
    "https://geoftp.ibge.gov.br/"
    "organizacao_do_territorio/"
    "divisao_territorial/"
)

# Bioma predominante por município 2024
URL_BIOMA = (
    "https://geoftp.ibge.gov.br/"
    "informacoes_ambientais/"
    "estudos_ambientais/"
    "biomas/"
    "documentos/"
    "Bioma_Predominante_por_Municipio_2024.csv"
)


# ============================================================
# DOWNLOAD
# ============================================================

def download(url):

    print(f"Download: {url}")

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    return response.content


# ============================================================
# LOCALIZAR SHAPEFILE
# ============================================================

def encontrar_shapefile():

    arquivos = list(
        MUNICIPIOS_DIR.rglob("*.shp")
    )

    if not arquivos:

        raise FileNotFoundError(
            f"Nenhum shapefile encontrado em "
            f"{MUNICIPIOS_DIR}"
        )

    return arquivos[0]


# ============================================================
# LER MUNICÍPIOS
# ============================================================

def baixar_municipios():

    print()
    print("=" * 80)
    print("DOWNLOAD DA MALHA MUNICIPAL 2025")
    print("=" * 80)

    MUNICIPIOS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # Verificar se já existe
    # ========================================================

    shp_files = list(
        MUNICIPIOS_DIR.rglob("*.shp")
    )

    if shp_files:

        print(
            f"Shapefile já existe:"
            f"\n{shp_files[0]}"
        )

        return shp_files[0]

    # ========================================================
    # Download
    # ========================================================

    print(
        "\nBaixando:"
    )

    print(
        URL_MUNICIPIOS
    )

    response = requests.get(
        URL_MUNICIPIOS,
        stream=True,
        timeout=300
    )

    response.raise_for_status()

    total = int(
        response.headers.get(
            "content-length",
            0
        )
    )

    baixado = 0

    with open(
        MUNICIPIOS_ZIP,
        "wb"
    ) as arquivo:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if not chunk:
                continue

            arquivo.write(
                chunk
            )

            baixado += len(chunk)

            if total:

                percentual = (
                    baixado / total
                ) * 100

                mb = (
                    baixado
                    / 1024
                    / 1024
                )

                total_mb = (
                    total
                    / 1024
                    / 1024
                )

                print(
                    f"\rDownload: "
                    f"{percentual:6.2f}% "
                    f"({mb:.1f}/{total_mb:.1f} MB)",
                    end=""
                )

    print()

    # ========================================================
    # Extrair
    # ========================================================

    print(
        "\nExtraindo..."
    )

    with zipfile.ZipFile(
        MUNICIPIOS_ZIP,
        "r"
    ) as zip_ref:

        zip_ref.extractall(
            MUNICIPIOS_DIR
        )

    print(
        f"Extraído para:"
        f"\n{MUNICIPIOS_DIR}"
    )

    # ========================================================
    # Localizar SHP
    # ========================================================

    shp_files = list(
        MUNICIPIOS_DIR.rglob("*.shp")
    )

    if not shp_files:

        raise FileNotFoundError(
            "Download concluído, mas "
            "nenhum .shp foi encontrado."
        )

    print(
        f"\nShapefile:"
        f"\n{shp_files[0]}"
    )

    return shp_files[0]


def encontrar_shapefile():

    shp_files = list(
        MUNICIPIOS_DIR.rglob("*.shp")
    )

    if shp_files:

        return shp_files[0]

    # Se não existe, baixa automaticamente
    return baixar_municipios()


def carregar_municipios():

    shp = encontrar_shapefile()

    print()
    print("=" * 80)
    print("MUNICÍPIOS")
    print("=" * 80)

    print(
        f"Arquivo: {shp}"
    )

    gdf = gpd.read_file(
        shp
    )

    print(
        f"Registros: {len(gdf):,}"
    )

    print(
        f"CRS: {gdf.crs}"
    )

    return gdf

# ============================================================
# IDENTIFICAR COLUNA
# ============================================================

def encontrar_coluna(
    df,
    nomes
):

    for nome in nomes:

        if nome in df.columns:

            return nome

    return None


# ============================================================
# PADRONIZAR MUNICÍPIOS
# ============================================================

def padronizar_municipios(gdf):

    codigo = encontrar_coluna(
        gdf,
        [
            "CD_MUN",
            "CD_GEOCMU",
            "CD_MUN_",
        ]
    )

    municipio = encontrar_coluna(
        gdf,
        [
            "NM_MUN",
            "NM_MUNICIP",
            "NM_MUNICIPIO",
        ]
    )

    uf = encontrar_coluna(
        gdf,
        [
            "SIGLA_UF",
            "SG_UF",
            "UF",
        ]
    )

    if codigo is None:

        raise ValueError(
            "Não encontrei o código IBGE."
        )

    if municipio is None:

        raise ValueError(
            "Não encontrei o nome do município."
        )

    renomear = {
        codigo: "codigo_ibge",
        municipio: "municipio",
    }

    if uf:

        renomear[uf] = "uf"

    gdf = gdf.rename(
        columns=renomear
    )

    # --------------------------------------------------------
    # Código IBGE
    # --------------------------------------------------------

    gdf["codigo_ibge"] = (
        gdf["codigo_ibge"]
        .astype(str)
        .str.replace(
            ".0",
            "",
            regex=False
        )
        .str.zfill(7)
    )

    # --------------------------------------------------------
    # CRS
    # --------------------------------------------------------

    if gdf.crs is None:

        gdf = gdf.set_crs(
            "EPSG:4674"
        )

    # --------------------------------------------------------
    # Área
    # --------------------------------------------------------

    gdf_metric = gdf.to_crs(
        "EPSG:5880"
    )

    gdf["area_km2"] = (
        gdf_metric
        .geometry
        .area
        / 1_000_000
    )

    # --------------------------------------------------------
    # Centroide
    # --------------------------------------------------------

    centroides = (
        gdf_metric
        .geometry
        .centroid
        .to_crs("EPSG:4326")
    )

    gdf["longitude"] = (
        centroides.x
    )

    gdf["latitude"] = (
        centroides.y
    )

    # --------------------------------------------------------
    # Polygon
    # --------------------------------------------------------

    # geometry = coluna geoespacial
    # polygon = cópia da geometria

    gdf["polygon"] = (
        gdf.geometry.copy()
    )

    return gdf


# ============================================================
# ADICIONAR TERRITÓRIO
# ============================================================
def adicionar_territorio(gdf):

    print()
    print("=" * 80)
    print("TERRITÓRIO")
    print("=" * 80)

    url = (
        "https://servicodados.ibge.gov.br/"
        "api/v1/localidades/municipios"
    )

    print(
        "\nConsultando municípios no IBGE..."
    )

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    dados = response.json()

    print(
        f"Municípios retornados pela API: "
        f"{len(dados):,}"
    )

    resultados = []

    for municipio in dados:

        codigo = municipio.get(
            "id"
        )

        nome_municipio = municipio.get(
            "nome"
        )

        microrregiao = municipio.get(
            "microrregiao"
        ) or {}

        mesorregiao = (
            microrregiao.get(
                "mesorregiao"
            )
            or {}
        )

        regiao_imediata = (
            municipio.get(
                "regiao-imediata"
            )
            or {}
        )

        regiao_intermediaria = (
            regiao_imediata.get(
                "regiao-intermediaria"
            )
            or {}
        )

        # ----------------------------------------------------
        # UF
        # ----------------------------------------------------

        uf = (
            mesorregiao.get(
                "UF"
            )
            or {}
        )

        regiao = (
            uf.get(
                "regiao"
            )
            or {}
        )

        resultados.append(
            {
                "codigo_ibge": str(
                    codigo
                ).zfill(7),

                "codigo_uf": uf.get(
                    "id"
                ),

                "uf": uf.get(
                    "sigla"
                ),

                "estado": uf.get(
                    "nome"
                ),

                "regiao": regiao.get(
                    "nome"
                ),

                "mesorregiao": mesorregiao.get(
                    "nome"
                ),

                "microrregiao": microrregiao.get(
                    "nome"
                ),
            }
        )

    # ========================================================
    # DATAFRAME
    # ========================================================

    territorio = pd.DataFrame(
        resultados
    )

    territorio["codigo_ibge"] = (
        territorio["codigo_ibge"]
        .astype(str)
        .str.zfill(7)
    )

    # ========================================================
    # REMOVER DUPLICADOS
    # ========================================================

    territorio = (
        territorio
        .drop_duplicates(
            "codigo_ibge"
        )
    )

    # ========================================================
    # MERGE
    # ========================================================

    gdf = gdf.drop(
        columns=[
            "codigo_uf",
            "uf",
            "estado",
            "regiao",
            "mesorregiao",
            "microrregiao",
        ],
        errors="ignore"
    )

    gdf = gdf.merge(
        territorio,
        on="codigo_ibge",
        how="left"
    )

    # ========================================================
    # RESUMO
    # ========================================================

    print(
        f"Municípios no shapefile: "
        f"{len(gdf):,}"
    )

    print(
        f"Municípios encontrados: "
        f"{gdf['estado'].notna().sum():,}"
    )

    print(
        f"Sem território: "
        f"{gdf['estado'].isna().sum():,}"
    )

    return gdf


# ============================================================
# POPULAÇÃO
# ============================================================

def buscar_populacao():

    print()
    print("=" * 80)
    print(
        f"POPULAÇÃO {ANO_POPULACAO}"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # API SIDRA / agregados
    #
    # Aqui usamos a tabela/agregado de estimativas
    # municipais.
    # --------------------------------------------------------

    url = (
        "https://servicodados.ibge.gov.br/"
        "api/v3/agregados/"
        "6579/"
        f"periodos/{ANO_POPULACAO}/"
        "variaveis/9324"
    )

    params = {
        "localidades": "N6[all]"
    }

    response = requests.get(
        url,
        params=params,
        timeout=120
    )

    response.raise_for_status()

    dados = response.json()

    registros = []

    for bloco in dados:

        for resultado in bloco.get(
            "resultados",
            []
        ):

            for serie in resultado.get(
                "series",
                []
            ):

                codigo = (
                    serie
                    .get("localidade", {})
                    .get("id")
                )

                valores = serie.get(
                    "serie",
                    {}
                )

                valor = valores.get(
                    str(ANO_POPULACAO)
                )

                if codigo and valor:

                    registros.append(
                        {
                            "codigo_ibge": str(
                                codigo
                            ).zfill(7),

                            "populacao": int(
                                float(valor)
                            ),

                            "ano_populacao":
                                ANO_POPULACAO,
                        }
                    )

    df = pd.DataFrame(
        registros
    )

    if df.empty:

        raise RuntimeError(
            "A API não retornou população."
        )

    df = df.drop_duplicates(
        "codigo_ibge"
    )

    print(
        f"Municípios com população: "
        f"{len(df):,}"
    )

    return df

# ============================================================
# GEOMORFOLOGIA
# ============================================================

def encontrar_coluna_geomorfologia(
    gdf,
    nomes
):

    for nome in nomes:

        if nome in gdf.columns:
            return nome

    # fallback: procura ignorando maiúsculas/minúsculas
    mapa = {
        str(col).upper(): col
        for col in gdf.columns
    }

    for nome in nomes:

        coluna = mapa.get(
            nome.upper()
        )

        if coluna:
            return coluna

    return None


def buscar_geomorfologia(municipios):

    print()
    print("=" * 80)
    print("GEOMORFOLOGIA IBGE")
    print("=" * 80)

    GEOMORFOLOGIA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # DOWNLOAD
    # ========================================================

    if not GEOMORFOLOGIA_ZIP.exists():

        print(
            "\nBaixando geomorfologia..."
        )

        response = requests.get(
            URL_GEOMORFOLOGIA,
            stream=True,
            timeout=300
        )

        response.raise_for_status()

        total = int(
            response.headers.get(
                "content-length",
                0
            )
        )

        baixado = 0

        with open(
            GEOMORFOLOGIA_ZIP,
            "wb"
        ) as arquivo:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                arquivo.write(chunk)

                baixado += len(chunk)

                if total:

                    percentual = (
                        baixado / total
                    ) * 100

                    print(
                        f"\rDownload: "
                        f"{percentual:6.2f}%",
                        end=""
                    )

        print()

    else:

        print(
            f"\nZIP já existe:"
            f"\n{GEOMORFOLOGIA_ZIP}"
        )

    # ========================================================
    # EXTRAIR
    # ========================================================

    shp_existentes = list(
        GEOMORFOLOGIA_DIR.rglob("*.shp")
    )

    if not shp_existentes:

        print(
            "\nExtraindo geomorfologia..."
        )

        with zipfile.ZipFile(
            GEOMORFOLOGIA_ZIP,
            "r"
        ) as zip_ref:

            zip_ref.extractall(
                GEOMORFOLOGIA_DIR
            )

    # ========================================================
    # LOCALIZAR SHAPEFILES
    # ========================================================

    shp_files = list(
        GEOMORFOLOGIA_DIR.rglob("*.shp")
    )

    if not shp_files:

        raise FileNotFoundError(
            "Nenhum shapefile encontrado "
            "na base de geomorfologia."
        )

    print(
        f"\nShapefiles encontrados: "
        f"{len(shp_files):,}"
    )

    # ========================================================
    # LER SHAPEFILES
    # ========================================================

    partes = []

    for shp in shp_files:

        print(
            f"Lendo: {shp.name}"
        )

        parte = gpd.read_file(
            shp
        )

        if not parte.empty:

            partes.append(
                parte
            )

    if not partes:

        raise RuntimeError(
            "Nenhum dado geomorfológico "
            "foi encontrado."
        )

    geom = gpd.GeoDataFrame(
        pd.concat(
            partes,
            ignore_index=True
        ),
        crs=partes[0].crs
    )

    # ========================================================
    # COLUNAS
    # ========================================================

    print()
    print(
        "Colunas da geomorfologia:"
    )

    print(
        geom.columns.tolist()
    )

    # ========================================================
    # IDENTIFICAR CAMPOS
    # ========================================================

    col_unidade = (
        encontrar_coluna_geomorfologia(
            geom,
            [
                "NM_UNIDADE",
                "NOME_UNIDADE",
                "UNIDADE",
            ]
        )
    )

    col_regiao = (
        encontrar_coluna_geomorfologia(
            geom,
            [
                "NM_REGIAO",
                "REGIAO",
            ]
        )
    )

    col_dominio = (
        encontrar_coluna_geomorfologia(
            geom,
            [
                "NM_DOMINIO",
                "DOMINIO",
            ]
        )
    )

    if col_unidade is None:

        raise ValueError(
            "Coluna de unidade geomorfológica "
            "não encontrada."
        )

    print(
        f"\nUnidade: {col_unidade}"
    )

    print(
        f"Região: {col_regiao}"
    )

    print(
        f"Domínio: {col_dominio}"
    )

    # ========================================================
    # CRS
    # ========================================================

    if geom.crs is None:

        raise ValueError(
            "A camada geomorfológica "
            "não possui CRS."
        )

    # ========================================================
    # PROJEÇÃO MÉTRICA
    # ========================================================

    print(
        "\nReprojetando dados..."
    )

    municipios_proj = (
        municipios
        .to_crs("EPSG:5880")
        .copy()
    )

    geom_proj = (
        geom
        .to_crs("EPSG:5880")
        .copy()
    )

    # ========================================================
    # MANTER SOMENTE ATRIBUTOS NECESSÁRIOS
    # ========================================================

    atributos = [
        col_unidade
    ]

    if col_regiao:
        atributos.append(
            col_regiao
        )

    if col_dominio:
        atributos.append(
            col_dominio
        )

    geom_proj = geom_proj[
        atributos + ["geometry"]
    ].copy()

    # Remover geometrias inválidas/vazias

    geom_proj = geom_proj[
        geom_proj.geometry.notna()
        & ~geom_proj.geometry.is_empty
    ].copy()

    municipios_proj = municipios_proj[
        municipios_proj.geometry.notna()
        & ~municipios_proj.geometry.is_empty
    ].copy()

    # ========================================================
    # JOIN ESPACIAL
    # ========================================================

    print()
    print(
        "Criando índice espacial..."
    )

    # Apenas para garantir a criação do índice

    _ = municipios_proj.sindex
    _ = geom_proj.sindex

    print(
        "Buscando candidatos..."
    )

    candidatos = gpd.sjoin(
        municipios_proj[
            [
                "codigo_ibge",
                "geometry",
            ]
        ],
        geom_proj,
        how="inner",
        predicate="intersects",
    )

    print(
        f"Candidatos encontrados: "
        f"{len(candidatos):,}"
    )

    # ========================================================
    # CALCULAR ÁREA DAS INTERSEÇÕES
    # ========================================================

    print()
    print(
        "Calculando áreas das interseções..."
    )

    resultados = []

    total = len(candidatos)

    for posicao, (idx_municipio, linha) in enumerate(
        candidatos.iterrows(),
        start=1
    ):

        if posicao % 1000 == 0:

            print(
                f"\rProcessando: "
                f"{posicao:,}/{total:,}",
                end=""
            )

        codigo = linha[
            "codigo_ibge"
        ]

        idx_geom = linha[
            "index_right"
        ]

        # ----------------------------------------------------
        # Geometria do município
        # ----------------------------------------------------

        geom_municipio = (
            municipios_proj.loc[
                municipios_proj["codigo_ibge"]
                == codigo,
                "geometry"
            ]
            .iloc[0]
        )

        # ----------------------------------------------------
        # Geometria geomorfológica
        # ----------------------------------------------------

        geom_geomorfologia = (
            geom_proj
            .loc[
                idx_geom,
                "geometry"
            ]
        )

        # ----------------------------------------------------
        # Interseção
        # ----------------------------------------------------

        try:

            intersecao = (
                geom_municipio
                .intersection(
                    geom_geomorfologia
                )
            )

        except Exception as erro:

            print(
                f"\n[AVISO] Não foi possível calcular "
                f"a geomorfologia do município "
                f"{codigo}: {erro}"
            )

            continue

        if intersecao.is_empty:
            continue

        # ----------------------------------------------------
        # Área
        # ----------------------------------------------------

        area_km2 = (
            intersecao.area
            / 1_000_000
        )

        registro = {

            "codigo_ibge":
                codigo,

            "geomorfologia":
                geom_proj.loc[
                    idx_geom,
                    col_unidade
                ],

            "_area_intersecao_km2":
                area_km2,
        }

        if col_regiao:

            registro[
                "regiao_geomorfologica"
            ] = geom_proj.loc[
                idx_geom,
                col_regiao
            ]

        if col_dominio:

            registro[
                "dominio_geomorfologico"
            ] = geom_proj.loc[
                idx_geom,
                col_dominio
            ]

        resultados.append(
            registro
        )

    print()

    # ========================================================
    # DATAFRAME DAS INTERSEÇÕES
    # ========================================================

    if not resultados:

        raise RuntimeError(
            "Nenhuma interseção geomorfológica "
            "foi encontrada."
        )

    intersecoes = pd.DataFrame(
        resultados
    )

    print(
        f"Interseções calculadas: "
        f"{len(intersecoes):,}"
    )

    # ========================================================
    # PEGAR GEOMORFOLOGIA PREDOMINANTE
    # ========================================================

    print(
        "\nIdentificando geomorfologia predominante..."
    )

    predominante = (
        intersecoes
        .sort_values(
            [
                "codigo_ibge",
                "_area_intersecao_km2",
            ],
            ascending=[
                True,
                False,
            ]
        )
        .drop_duplicates(
            "codigo_ibge"
        )
        .copy()
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    colunas = [
        "codigo_ibge",
        "geomorfologia",
    ]

    if (
        "regiao_geomorfologica"
        in predominante.columns
    ):

        colunas.append(
            "regiao_geomorfologica"
        )

    if (
        "dominio_geomorfologico"
        in predominante.columns
    ):

        colunas.append(
            "dominio_geomorfologico"
        )

    resultado = predominante[
        colunas
    ].copy()

    # ========================================================
    # MERGE COM MUNICÍPIOS
    # ========================================================

    municipios = municipios.merge(
        resultado,
        on="codigo_ibge",
        how="left"
    )

    # ========================================================
    # RESUMO
    # ========================================================

    classificados = (
        municipios[
            "geomorfologia"
        ]
        .notna()
        .sum()
    )

    print()
    print(
        "=" * 80
    )

    print(
        "GEOMORFOLOGIA CONCLUÍDA"
    )

    print(
        f"Municípios: "
        f"{len(municipios):,}"
    )

    print(
        f"Classificados: "
        f"{classificados:,}"
    )

    print(
        f"Sem classificação: "
        f"{len(municipios) - classificados:,}"
    )

    print(
        "=" * 80
    )

    return municipios

# ============================================================
# BIOMA
# ============================================================

def buscar_bioma():

    print()
    print("=" * 80)
    print("BIOMA")
    print("=" * 80)

    # --------------------------------------------------------
    # Primeiro tenta localizar o arquivo no FTP do IBGE.
    # --------------------------------------------------------

    urls = [

        URL_BIOMA,

        (
            "https://geoftp.ibge.gov.br/"
            "informacoes_ambientais/"
            "estudos_ambientais/"
            "biomas/documentos/"
            "Bioma_Predominante_por_Municipio_2024.csv"
        ),

    ]

    dados = None

    for url in urls:

        try:

            response = requests.get(
                url,
                timeout=60
            )

            if response.ok:

                dados = response.content

                print(
                    f"Arquivo encontrado: {url}"
                )

                break

        except requests.RequestException:

            pass

    if dados is None:

        raise RuntimeError(
            "Não foi possível baixar "
            "o arquivo de biomas do IBGE."
        )

    # --------------------------------------------------------
    # Detectar separador/encoding
    # --------------------------------------------------------

    df = None

    for encoding in [
        "utf-8",
        "latin1",
        "cp1252",
    ]:

        try:

            df = pd.read_csv(
                BytesIO(dados),
                sep=None,
                engine="python",
                encoding=encoding
            )

            break

        except (
            UnicodeDecodeError,
            pd.errors.ParserError
        ):

            continue

    if df is None:

        raise RuntimeError(
            "Não foi possível ler "
            "o arquivo de biomas."
        )

    print(
        "Colunas:",
        df.columns.tolist()
    )

    # --------------------------------------------------------
    # Encontrar código
    # --------------------------------------------------------

    codigo = encontrar_coluna(
        df,
        [
            "Geocódigo",
            "Geocodigo",
            "CD_MUN",
            "CD_GEOCMU",
            "codigo_ibge",
            "Código",
            "Codigo",
        ]
    )

    # --------------------------------------------------------
    # Encontrar bioma
    # --------------------------------------------------------

    bioma = encontrar_coluna(
        df,
        [
            "Bioma predominante",
            "Bioma predominante ",
            "BIOMA",
            "bioma",
            "Bioma",
        ]
    )

    if codigo is None:

        # fallback por nome
        for c in df.columns:

            if "geo" in str(c).lower():

                codigo = c
                break

    if bioma is None:

        for c in df.columns:

            if "bioma" in str(c).lower():

                bioma = c
                break

    if codigo is None:

        raise ValueError(
            "Código IBGE não encontrado "
            "no arquivo de bioma."
        )

    if bioma is None:

        raise ValueError(
            "Coluna de bioma não encontrada."
        )

    df = df.rename(
        columns={
            codigo: "codigo_ibge",
            bioma: "bioma",
        }
    )

    df["codigo_ibge"] = (
        df["codigo_ibge"]
        .astype(str)
        .str.replace(
            ".0",
            "",
            regex=False
        )
        .str.zfill(7)
    )

    df["bioma"] = (
        df["bioma"]
        .astype(str)
        .str.strip()
    )

    return df[
        [
            "codigo_ibge",
            "bioma",
        ]
    ].drop_duplicates(
        "codigo_ibge"
    )


# ============================================================
# MERGE
# ============================================================

def montar_dataframe():

    # --------------------------------------------------------
    # Shapefile
    # --------------------------------------------------------

    gdf = carregar_municipios()

    gdf = padronizar_municipios(
        gdf
    )

    # --------------------------------------------------------
    # Território
    # --------------------------------------------------------

    gdf = adicionar_territorio(
        gdf
    )

    # --------------------------------------------------------
    # População
    # --------------------------------------------------------

    populacao = buscar_populacao()

    gdf = gdf.merge(
        populacao,
        on="codigo_ibge",
        how="left"
    )

    # --------------------------------------------------------
    # Geomorfologia
    # --------------------------------------------------------

    gdf = buscar_geomorfologia(
        gdf
    )

    # --------------------------------------------------------
    # Bioma
    # --------------------------------------------------------

    bioma = buscar_bioma()

    gdf = gdf.merge(
        bioma,
        on="codigo_ibge",
        how="left"
    )

    # --------------------------------------------------------
    # Colunas finais
    # --------------------------------------------------------

    colunas = [
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
    ]

    # Se geomorfologia ainda não estiver
    # disponível, cria a coluna.
    if "geomorfologia" not in gdf.columns:

        gdf["geomorfologia"] = None

    gdf = gdf[
        colunas
    ]

    return gdf


# ============================================================
# SALVAR
# ============================================================
def salvar_dataframe(gdf):

    ARQUIVO_PARQUET.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    ARQUIVO_GPKG.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # 1. PARQUET
    # ========================================================
    #
    # Mantém geometry e polygon.
    # O GeoPandas consegue armazenar múltiplas geometrias
    # em Parquet.
    #

    gdf.to_parquet(
        ARQUIVO_PARQUET,
        index=False
    )

    print(
        f"\nParquet salvo:"
        f"\n{ARQUIVO_PARQUET}"
    )

    # ========================================================
    # 2. GEOPACKAGE
    # ========================================================
    #
    # GeoPackage aceita somente uma coluna geométrica.
    # Portanto, transformamos "polygon" em WKT.
    #

    gdf_gpkg = gdf.copy()

    if "polygon" in gdf_gpkg.columns:

        gdf_gpkg["polygon"] = (
            gdf_gpkg["polygon"]
            .apply(
                lambda geom:
                    geom.wkt
                    if geom is not None
                    else None
            )
        )

    # ========================================================
    # Remover arquivo anterior
    # ========================================================

    if ARQUIVO_GPKG.exists():

        ARQUIVO_GPKG.unlink()

    # ========================================================
    # Salvar
    # ========================================================

    gdf_gpkg.to_file(
        ARQUIVO_GPKG,
        layer="municipios",
        driver="GPKG",
        index=False
    )

    print(
        f"\nGeoPackage salvo:"
        f"\n{ARQUIVO_GPKG}"
    )

# ============================================================
# MAIN
# ============================================================

def main():

    gdf = montar_dataframe()

    salvar_dataframe(
        gdf
    )

    # --------------------------------------------------------
    # Resumo
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("DATAFRAME FINAL")
    print("=" * 100)

    print(
        f"Municípios: {len(gdf):,}"
    )

    print(
        f"Colunas: {len(gdf.columns)}"
    )

    print()

    print(
        gdf[
            [
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
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print()
    print("Colunas finais:")

    for coluna in gdf.columns:

        print(
            f"  - {coluna}"
        )


if __name__ == "__main__":

    main()
