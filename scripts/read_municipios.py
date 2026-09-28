from pathlib import Path
import argparse

import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_PARQUET = Path(
    "./data/municipios.parquet"
)


# ============================================================
# CARREGAR DADOS
# ============================================================

def carregar_dados():

    if not ARQUIVO_PARQUET.exists():

        raise FileNotFoundError(
            f"Parquet não encontrado: "
            f"{ARQUIVO_PARQUET.resolve()}"
        )

    print(
        f"Lendo: {ARQUIVO_PARQUET}"
    )

    df = pd.read_parquet(
        ARQUIVO_PARQUET
    )

    print(
        f"Municípios encontrados: "
        f"{len(df):,}"
    )

    print(
        f"Colunas: "
        f"{len(df.columns)}"
    )

    return df


# ============================================================
# FILTROS
# ============================================================

def filtrar_dados(
    df,
    args
):

    resultado = df.copy()

    # --------------------------------------------------------
    # Código IBGE
    # --------------------------------------------------------

    if args.codigo:

        resultado = resultado[
            resultado["codigo_ibge"]
            .astype(str)
            .str.startswith(
                args.codigo
            )
        ]

    # --------------------------------------------------------
    # UF
    # --------------------------------------------------------

    if args.uf:

        resultado = resultado[
            resultado["uf"]
            .astype(str)
            .str.upper()
            .eq(
                args.uf.upper()
            )
        ]

    # --------------------------------------------------------
    # Estado
    # --------------------------------------------------------

    if args.estado:

        resultado = resultado[
            resultado["estado"]
            .astype(str)
            .str.contains(
                args.estado,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # Município
    # --------------------------------------------------------

    if args.municipio:

        resultado = resultado[
            resultado["municipio"]
            .astype(str)
            .str.contains(
                args.municipio,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # Região
    # --------------------------------------------------------

    if args.regiao:

        resultado = resultado[
            resultado["regiao"]
            .astype(str)
            .str.contains(
                args.regiao,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # Mesorregião
    # --------------------------------------------------------

    if args.mesorregiao:

        resultado = resultado[
            resultado["mesorregiao"]
            .astype(str)
            .str.contains(
                args.mesorregiao,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # Microrregião
    # --------------------------------------------------------

    if args.microrregiao:

        resultado = resultado[
            resultado["microrregiao"]
            .astype(str)
            .str.contains(
                args.microrregiao,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # Bioma
    # --------------------------------------------------------

    if args.bioma:

        resultado = resultado[
            resultado["bioma"]
            .astype(str)
            .str.contains(
                args.bioma,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # Geomorfologia
    # --------------------------------------------------------

    if args.geomorfologia:

        resultado = resultado[
            resultado["geomorfologia"]
            .astype(str)
            .str.contains(
                args.geomorfologia,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------------
    # População mínima
    # --------------------------------------------------------

    if args.populacao_min is not None:

        resultado = resultado[
            resultado["populacao"]
            >= args.populacao_min
        ]

    # --------------------------------------------------------
    # População máxima
    # --------------------------------------------------------

    if args.populacao_max is not None:

        resultado = resultado[
            resultado["populacao"]
            <= args.populacao_max
        ]

    # --------------------------------------------------------
    # Área mínima
    # --------------------------------------------------------

    if args.area_min is not None:

        resultado = resultado[
            resultado["area_km2"]
            >= args.area_min
        ]

    # --------------------------------------------------------
    # Área máxima
    # --------------------------------------------------------

    if args.area_max is not None:

        resultado = resultado[
            resultado["area_km2"]
            <= args.area_max
        ]

    # --------------------------------------------------------
    # Limite
    # --------------------------------------------------------

    if args.limit:

        resultado = resultado.head(
            args.limit
        )

    return resultado


# ============================================================
# EXIBIR
# ============================================================

def mostrar_resultado(df):

    print()
    print("=" * 140)
    print("RESULTADO")
    print("=" * 140)

    if df.empty:

        print(
            "Nenhum município encontrado."
        )

        return

    exibicao = df.copy()

    # --------------------------------------------------------
    # Formatação
    # --------------------------------------------------------

    if "populacao" in exibicao.columns:

        exibicao["populacao"] = (
            exibicao["populacao"]
            .apply(
                lambda x:
                    f"{int(x):,}"
                    if pd.notna(x)
                    else "-"
            )
        )

    if "area_km2" in exibicao.columns:

        exibicao["area_km2"] = (
            exibicao["area_km2"]
            .apply(
                lambda x:
                    f"{x:,.2f}"
                    if pd.notna(x)
                    else "-"
            )
        )

    if "latitude" in exibicao.columns:

        exibicao["latitude"] = (
            exibicao["latitude"]
            .apply(
                lambda x:
                    f"{x:.6f}"
                    if pd.notna(x)
                    else "-"
            )
        )

    if "longitude" in exibicao.columns:

        exibicao["longitude"] = (
            exibicao["longitude"]
            .apply(
                lambda x:
                    f"{x:.6f}"
                    if pd.notna(x)
                    else "-"
            )
        )

    print(
        exibicao.to_string(
            index=False
        )
    )

    print()
    print(
        "-" * 140
    )

    print(
        f"Total exibido: "
        f"{len(df):,}"
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Consulta municípios do "
            "Parquet do IBGE."
        )
    )

    # --------------------------------------------------------
    # Localização
    # --------------------------------------------------------

    parser.add_argument(
        "--uf",
        help="Filtra pela UF. Ex: GO, SP, MG"
    )

    parser.add_argument(
        "--estado",
        help="Filtra pelo nome do estado."
    )

    parser.add_argument(
        "--municipio",
        help=(
            "Filtra pelo nome do município. "
            "Aceita parte do nome."
        )
    )

    parser.add_argument(
        "--codigo",
        help="Filtra pelo código IBGE."
    )

    # --------------------------------------------------------
    # Divisão territorial
    # --------------------------------------------------------

    parser.add_argument(
        "--regiao",
        help="Filtra pela região."
    )

    parser.add_argument(
        "--mesorregiao",
        help="Filtra pela mesorregião."
    )

    parser.add_argument(
        "--microrregiao",
        help="Filtra pela microrregião."
    )

    # --------------------------------------------------------
    # Características
    # --------------------------------------------------------

    parser.add_argument(
        "--bioma",
        help="Filtra pelo bioma."
    )

    parser.add_argument(
        "--geomorfologia",
        help="Filtra pela geomorfologia."
    )

    # --------------------------------------------------------
    # População
    # --------------------------------------------------------

    parser.add_argument(
        "--populacao-min",
        type=int,
        help="População mínima."
    )

    parser.add_argument(
        "--populacao-max",
        type=int,
        help="População máxima."
    )

    # --------------------------------------------------------
    # Área
    # --------------------------------------------------------

    parser.add_argument(
        "--area-min",
        type=float,
        help="Área mínima em km²."
    )

    parser.add_argument(
        "--area-max",
        type=float,
        help="Área máxima em km²."
    )

    # --------------------------------------------------------
    # Limite
    # --------------------------------------------------------

    parser.add_argument(
        "--limit",
        type=int,
        help="Limita a quantidade de resultados."
    )

    args = parser.parse_args()

    # ========================================================
    # EXECUÇÃO
    # ========================================================

    df = carregar_dados()

    resultado = filtrar_dados(
        df,
        args
    )

    mostrar_resultado(
        resultado
    )


if __name__ == "__main__":

    main()