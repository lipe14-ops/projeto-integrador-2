import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell
def _():
    import os
    import re
    from datetime import timezone
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text

    return (
        Path,
        create_engine,
        load_dotenv,
        mo,
        np,
        os,
        pd,
        px,
        re,
        text,
        timezone,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Análise exploratória dos dados climáticos

    Este notebook analisa as observações ERA5-Land carregadas em
    `registro_climatico`, relaciona-as com municípios e com o índice ENSO,
    e mostra distribuições, faltantes, outliers, séries temporais e mapas
    interativos.

    ## Uso de memória e limites

    Há 132 arquivos GRIB, com cerca de 6,5 GB no disco. O notebook **não os
    carrega na memória**: as estatísticas climáticas vêm de consultas
    agregadas a um único mês no PostgreSQL. A série histórica completa é
    opcional e só é consultada ao clicar no botão próprio. Os mapas usam
    coordenadas dos municípios e não carregam polígonos municipais.

    O banco precisa estar acessível pela variável `DATABASE_URL` (ou pelo
    endereço padrão do projeto). O arquivo GRIB original não é aberto aqui;
    sua decodificação depende da biblioteca nativa ecCodes.
    """)
    return


@app.cell
def _(Path, mo, pd, re):
    _raiz = Path(__file__).resolve().parents[1]
    _pasta_grib = _raiz / "data" / "era5_land"
    _arquivos_grib = sorted(
        _pasta_grib.glob("era5_land_????_??.grib"), key=lambda _p: _p.name
    )
    _inventario_linhas = []
    for _arquivo in _arquivos_grib:
        _correspondencia = re.fullmatch(r"era5_land_(\d{4})_(\d{2})\.grib", _arquivo.name)
        if _correspondencia:
            _ano, _mes = _correspondencia.groups()
            _inventario_linhas.append({
                "Mês": f"{_ano}-{_mes}",
                "Arquivo": _arquivo.name,
                "Tamanho (MiB)": round(_arquivo.stat().st_size / (1024 ** 2), 1),
            })
    inventario_grib = pd.DataFrame(_inventario_linhas)
    caminho_enso = _pasta_grib / "registro_era5_enso.csv"
    if caminho_enso.is_file():
        enso = pd.read_csv(caminho_enso)
        _coluna_oni = "oni" if "oni" in enso.columns else "enso_index"
        if _coluna_oni in enso.columns and {"year", "month"}.issubset(enso.columns):
            enso = enso.rename(columns={_coluna_oni: "oni"})
            enso["data"] = pd.to_datetime(
                dict(year=enso["year"], month=enso["month"], day=1), errors="coerce"
            )
            enso["oni"] = pd.to_numeric(enso["oni"], errors="coerce")
            enso = enso.dropna(subset=["data"]).sort_values("data").reset_index(drop=True)
    else:
        enso = pd.DataFrame(columns=["year", "month", "oni", "data"])

    _tamanho_total_mib = (
        sum(_arquivo.stat().st_size for _arquivo in _arquivos_grib) / (1024 ** 2)
    )
    mo.vstack([
        mo.md(
            f"**Arquivos GRIB encontrados:** {len(inventario_grib):,} · "
            f"**Volume em disco:** {_tamanho_total_mib / 1024:.2f} GiB · "
            f"**Índice ENSO:** {len(enso):,} meses"
        ),
        mo.ui.table(inventario_grib, page_size=12),
    ])
    return enso, inventario_grib


@app.cell
def _(Path, create_engine, load_dotenv, os, text):
    _raiz = Path(__file__).resolve().parents[1]
    load_dotenv(_raiz / ".env")
    _url_banco = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/geodata",
    )
    _engine = create_engine(
        _url_banco,
        connect_args={"connect_timeout": 3},
        pool_pre_ping=True,
    )

    def conectar_banco():
        return _engine.connect()

    database_ok = False
    database_error = ""
    ufs = []
    try:
        with conectar_banco() as _conexao:
            _conexao.execute(text("SELECT 1"))
            ufs = list(_conexao.execute(
                text("SELECT DISTINCT uf FROM municipio_details WHERE uf IS NOT NULL ORDER BY uf")
            ).scalars())
        database_ok = True
    except Exception as _erro:
        database_error = f"{type(_erro).__name__}: {_erro}"
    return conectar_banco, database_error, database_ok, ufs


@app.cell
def _(database_error, database_ok, mo):
    if database_ok:
        _saida_status = mo.md("✅ **PostgreSQL conectado.** A análise climática municipal está disponível.")
    else:
        _saida_status = mo.md(
            "⚠️ **PostgreSQL indisponível.** A parte municipal (mapas, boxplots e "
            "faltantes climáticos) será omitida até o banco estar acessível. "
            f"Detalhe: `{database_error[:500]}`"
        )
    _saida_status
    return


@app.cell
def _(inventario_grib, mo, ufs):
    _meses = inventario_grib["Mês"].tolist() if not inventario_grib.empty else ["Sem GRIB"]
    mes_escolhido = mo.ui.dropdown(
        options=_meses,
        value=_meses[-1],
        label="Mês para análise municipal",
    )
    uf_escolhida = mo.ui.dropdown(
        options=["Todas", *ufs], value="Todas", label="UF"
    )
    variavel_escolhida = mo.ui.dropdown(
        options={
            "Temperatura média (°C)": "temperatura",
            "Umidade relativa média (%)": "umidade",
            "Precipitação acumulada (mm)": "precipitacao",
        },
        value="Temperatura média (°C)",
        label="Variável para o mapa",
    )
    historico_button = mo.ui.run_button(
        label="Calcular série histórica mensal completa",
        kind="success",
    )
    mo.vstack([
        mo.hstack([mes_escolhido, uf_escolhida, variavel_escolhida]),
        mo.md(
            "A agregação mensal municipal lê no máximo o resultado agregado por "
            "município; a série histórica completa roda somente após clicar no botão."
        ),
        historico_button,
    ])
    return historico_button, mes_escolhido, uf_escolhida, variavel_escolhida


@app.cell
def _(
    conectar_banco,
    database_ok,
    mes_escolhido,
    pd,
    text,
    timezone,
    uf_escolhida,
):
    _colunas_clima = [
        "codigo_ibge", "municipio", "uf", "latitude", "longitude", "registros",
        "temperatura_validos", "umidade_validos", "precipitacao_validos",
        "temperatura", "umidade", "precipitacao",
    ]
    climate_df = pd.DataFrame(columns=_colunas_clima)
    climate_status = ""
    if database_ok and mes_escolhido.value != "Sem GRIB":
        _periodo = pd.Period(mes_escolhido.value, freq="M")
        _inicio = pd.Timestamp(_periodo.start_time, tz=timezone.utc).to_pydatetime()
        _fim = pd.Timestamp((_periodo + 1).start_time, tz=timezone.utc).to_pydatetime()
        _consulta = text(
            """
            WITH clima_mes AS (
                SELECT codigo_ibge,
                       COUNT(datetime)::integer AS registros,
                       COUNT(temperatura)::integer AS temperatura_validos,
                       COUNT(umidade)::integer AS umidade_validos,
                       COUNT(precipitacao)::integer AS precipitacao_validos,
                       AVG(temperatura) AS temperatura,
                       AVG(umidade) AS umidade,
                       SUM(precipitacao) AS precipitacao
                FROM registro_climatico
                WHERE datetime >= :inicio AND datetime < :fim
                GROUP BY codigo_ibge
            )
            SELECT m.codigo_ibge,
                   COALESCE(d.municipio, m.codigo_ibge::text) AS municipio,
                   d.uf, m.latitude, m.longitude,
                   COALESCE(c.registros, 0) AS registros,
                   COALESCE(c.temperatura_validos, 0) AS temperatura_validos,
                   COALESCE(c.umidade_validos, 0) AS umidade_validos,
                   COALESCE(c.precipitacao_validos, 0) AS precipitacao_validos,
                   c.temperatura, c.umidade, c.precipitacao
            FROM municipio AS m
            LEFT JOIN municipio_details AS d ON d.codigo_ibge = m.codigo_ibge
            LEFT JOIN clima_mes AS c ON c.codigo_ibge = m.codigo_ibge
            WHERE m.latitude IS NOT NULL AND m.longitude IS NOT NULL
              AND (CAST(:uf AS text) IS NULL OR d.uf = CAST(:uf AS text))
            ORDER BY m.codigo_ibge
            """
        )
        try:
            with conectar_banco() as _conexao:
                _resultados = _conexao.execute(
                    _consulta,
                    {"inicio": _inicio, "fim": _fim,
                     "uf": None if uf_escolhida.value == "Todas" else uf_escolhida.value},
                ).mappings().all()
            climate_df = pd.DataFrame(_resultados, columns=_colunas_clima)
            climate_status = (
                f"{len(climate_df):,} municípios com coordenadas consultados para "
                f"{mes_escolhido.value} (apenas médias e contagens mensais)."
            )
        except Exception as _erro:
            climate_status = f"Erro na consulta mensal: {type(_erro).__name__}: {_erro}"
    elif database_ok:
        climate_status = "Nenhum arquivo GRIB mensal foi encontrado para oferecer no seletor."
    else:
        climate_status = "Inicie/conecte o PostgreSQL para consultar os registros climáticos."
    return climate_df, climate_status


@app.cell
def _(climate_df, climate_status, mes_escolhido, mo, pd):
    if climate_df.empty:
        _saida_resumo = mo.vstack([
            mo.md(f"**Consulta mensal:** {climate_status}"),
            mo.md("Sem resultados municipais neste mês. Confira se o mês já foi enviado ao banco."),
        ])
    else:
        _esperado_por_municipio = (
            pd.Period(mes_escolhido.value, freq="M").days_in_month * 2
        )
        _municipios_sem_registro = int((climate_df["registros"] == 0).sum())
        _faltantes_linhas = []
        for _variavel, _coluna_validos in [
            ("temperatura", "temperatura_validos"),
            ("umidade", "umidade_validos"),
            ("precipitacao", "precipitacao_validos"),
        ]:
            _possiveis = len(climate_df) * _esperado_por_municipio
            _validos = int(climate_df[_coluna_validos].sum())
            _faltantes = max(_possiveis - _validos, 0)
            _faltantes_linhas.append({
                "Variável": _variavel,
                "Observações esperadas*": _possiveis,
                "Observações válidas": _validos,
                "Observações faltantes*": _faltantes,
                "% faltantes*": round(100 * _faltantes / _possiveis, 2) if _possiveis else 0,
            })
        _climate_missing = pd.DataFrame(_faltantes_linhas)
        _cobertura_media = (
            climate_df["registros"].clip(upper=_esperado_por_municipio).mean()
            / _esperado_por_municipio * 100
            if _esperado_por_municipio else 0
        )
        _saida_resumo = mo.vstack([
            mo.md(f"**Consulta mensal:** {climate_status}"),
            mo.md(
                f"**Municípios sem registros:** {_municipios_sem_registro:,} · "
                f"**Cobertura média do mês:** {_cobertura_media:.1f}% · "
                f"**Pontos municipais com coordenadas:** {len(climate_df):,}"
            ),
            mo.md(
                "\\* Espera-se 2 registros por dia, conforme a frequência de carga "
                "00:00 e 12:00 UTC do projeto. A taxa mede cobertura dessa expectativa."
            ),
            mo.ui.table(_climate_missing, page_size=3),
        ])
    _saida_resumo
    return


@app.cell
def _(climate_df, mes_escolhido, mo, px, variavel_escolhida):
    if climate_df.empty:
        _saida_mapa = mo.md("O mapa municipal aparecerá quando houver observações no mês e conexão com o banco.")
    else:
        _variavel = variavel_escolhida.value
        _nomes = {
            "temperatura": "Temperatura média (°C)",
            "umidade": "Umidade relativa média (%)",
            "precipitacao": "Precipitação acumulada no mês (mm)",
        }
        _para_mapa = climate_df.dropna(subset=[_variavel, "latitude", "longitude"])
        if _para_mapa.empty:
            _saida_mapa = mo.md(f"Não há valores válidos de {_nomes[_variavel]} nesse recorte.")
        else:
            _mapa_clima = px.scatter_geo(
                _para_mapa,
                lat="latitude",
                lon="longitude",
                color=_variavel,
                hover_name="municipio",
                hover_data={
                    "uf": True, "codigo_ibge": True, "registros": True,
                    "latitude": ":.3f", "longitude": ":.3f",
                },
                color_continuous_scale="Turbo",
                projection="mercator",
                scope="south america",
                title=f"{_nomes[_variavel]} por município — {mes_escolhido.value}",
            )
            _mapa_clima.update_geos(
                center={"lat": -14, "lon": -52},
                lataxis_range=[-35, 7], lonaxis_range=[-76, -32],
                showcountries=True, countrycolor="#64748b",
                showland=True, landcolor="#f1f5f9",
            )
            _mapa_clima.update_traces(marker={"size": 7, "opacity": 0.8})
            _mapa_clima.update_layout(height=650, margin={"l": 0, "r": 0, "t": 55, "b": 0})
            _saida_mapa = mo.vstack([
                mo.md("## Mapa interativo da variável climática\nPasse o cursor sobre um município; use zoom e arraste para explorar."),
                _mapa_clima,
            ])
    _saida_mapa
    return


@app.cell
def _(climate_df, mo, np, pd, px):
    if climate_df.empty:
        _saida_distribuicoes = mo.md("A distribuição e o mapa de densidade dependem dos resultados municipais.")
    else:
        _variaveis = [
            ("temperatura", "Temperatura média municipal (°C)"),
            ("umidade", "Umidade relativa média municipal (%)"),
            ("precipitacao", "Precipitação acumulada municipal (mm)"),
        ]
        _estatisticas = []
        for _coluna, _rotulo in _variaveis:
            _serie = climate_df[_coluna].dropna()
            _q1 = _serie.quantile(0.25)
            _q3 = _serie.quantile(0.75)
            _iqr = _q3 - _q1
            _estatisticas.append({
                "Variável": _rotulo,
                "Municípios válidos": len(_serie),
                "Média": _serie.mean(),
                "Mediana": _serie.median(),
                "Desvio-padrão": _serie.std(),
                "Mínimo": _serie.min(),
                "Q1": _q1,
                "Q3": _q3,
                "Máximo": _serie.max(),
                "Outliers (1,5×IQR)": int(((_serie < _q1 - 1.5 * _iqr) | (_serie > _q3 + 1.5 * _iqr)).sum()),
            })
        _tabela_estatisticas = pd.DataFrame(_estatisticas).round(2)
        _long = climate_df.melt(
            id_vars=["codigo_ibge", "municipio", "uf"],
            value_vars=[_coluna for _coluna, _ in _variaveis],
            var_name="variavel", value_name="valor",
        ).dropna(subset=["valor"])
        _long["variavel"] = _long["variavel"].map(dict(_variaveis))
        _boxplot = px.box(
            _long, x="variavel", y="valor", points="outliers", color="variavel",
            hover_data=["municipio", "uf", "codigo_ibge"],
            title="Distribuição entre municípios (um valor agregado por município)",
        )
        _boxplot.update_layout(showlegend=False, height=500, xaxis_title="", yaxis_title="Valor")

        _densidade = climate_df.dropna(subset=["latitude", "longitude"]).copy()
        _densidade["latitude_celula"] = np.floor(_densidade["latitude"]).astype(int)
        _densidade["longitude_celula"] = np.floor(_densidade["longitude"]).astype(int)
        _densidade = (
            _densidade.groupby(["latitude_celula", "longitude_celula"], as_index=False)
            .agg(municipios=("codigo_ibge", "nunique"),
                 latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        )
        _mapa_densidade = px.scatter_geo(
            _densidade, lat="latitude", lon="longitude", size="municipios",
            color="municipios", hover_data={"municipios": True},
            color_continuous_scale="Viridis", projection="mercator",
            scope="south america",
            title="Densidade de pontos municipais por célula de 1° × 1°",
            size_max=24,
        )
        _mapa_densidade.update_geos(
            center={"lat": -14, "lon": -52}, lataxis_range=[-35, 7],
            lonaxis_range=[-76, -32], showcountries=True, showland=True,
            landcolor="#f1f5f9",
        )
        _mapa_densidade.update_layout(height=600, margin={"l": 0, "r": 0, "t": 55, "b": 0})
        _saida_distribuicoes = mo.vstack([
            mo.md("## Boxplots e pontos por área"),
            mo.md(
                "A tabela e os boxplots comparam um agregado mensal por município; "
                "outliers usam a regra de 1,5×IQR. O mapa "
                "agrupa centroides em células de 1 grau; cada círculo mostra quantos "
                "municípios caem na célula (aproximadamente 111 km norte-sul, com "
                "largura leste-oeste variável por latitude)."
            ),
            mo.ui.table(_tabela_estatisticas, page_size=3),
            _boxplot,
            _mapa_densidade,
        ])
    _saida_distribuicoes
    return


@app.cell
def _(climate_df, mes_escolhido, mo, pd):
    if climate_df.empty:
        _saida_alertas = mo.md("A lista de municípios com baixa cobertura será exibida após a consulta mensal.")
    else:
        _dias = pd.Period(mes_escolhido.value, freq="M").days_in_month
        _esperado = _dias * 2
        _alertas = climate_df.copy()
        _alertas["cobertura_pct"] = (_alertas["registros"].clip(upper=_esperado) / _esperado * 100).round(1)
        for _nome, _validos in [
            ("temperatura", "temperatura_validos"),
            ("umidade", "umidade_validos"),
            ("precipitacao", "precipitacao_validos"),
        ]:
            _alertas[f"{_nome}_faltantes"] = (_esperado - _alertas[_validos]).clip(lower=0)
        _alertas = _alertas.sort_values(
            ["cobertura_pct", "registros", "codigo_ibge"], ascending=[True, True, True]
        )
        _colunas_alerta = [
            "codigo_ibge", "municipio", "uf", "registros", "cobertura_pct",
            "temperatura_faltantes", "umidade_faltantes", "precipitacao_faltantes",
        ]
        _saida_alertas = mo.vstack([
            mo.md("## Municípios com menor cobertura de registros"),
            mo.md("Até 100 municípios, ordenados pela menor cobertura de observações esperadas no mês."),
            mo.ui.table(_alertas[_colunas_alerta].head(100).reset_index(drop=True), page_size=20),
        ])
    _saida_alertas
    return


@app.cell
def _(enso, mo, pd, px):
    if enso.empty or "oni" not in enso:
        _saida_enso = mo.md("## ENSO\nO arquivo `registro_era5_enso.csv` não foi encontrado ou não tem colunas utilizáveis.")
    else:
        _serie_enso = enso.dropna(subset=["oni"]).copy()
        _q1, _q3 = _serie_enso["oni"].quantile([0.25, 0.75])
        _iqr = _q3 - _q1
        _limite_inferior, _limite_superior = _q1 - 1.5 * _iqr, _q3 + 1.5 * _iqr
        _outliers = _serie_enso[
            (_serie_enso["oni"] < _limite_inferior)
            | (_serie_enso["oni"] > _limite_superior)
        ]
        _estatisticas_enso = pd.DataFrame([{
            "Meses válidos": len(_serie_enso),
            "Meses faltantes": int(enso["oni"].isna().sum()),
            "Média": _serie_enso["oni"].mean(),
            "Mediana": _serie_enso["oni"].median(),
            "Desvio-padrão": _serie_enso["oni"].std(),
            "Mínimo": _serie_enso["oni"].min(),
            "Máximo": _serie_enso["oni"].max(),
            "Outliers (regra 1,5×IQR)": len(_outliers),
        }]).round(3)
        _grafico_enso = px.line(
            _serie_enso, x="data", y="oni", markers=True,
            title="Índice ONI por mês",
            labels={"data": "Mês", "oni": "ONI (°C)"},
        )
        _grafico_enso.add_hline(y=0, line_dash="dash", line_color="gray")
        _box_enso = px.box(
            _serie_enso, y="oni", points="all", title="Distribuição do índice ONI",
            labels={"oni": "ONI (°C)"},
        )
        _saida_enso = mo.vstack([
            mo.md("## Série e distribuição ENSO/ONI"),
            mo.md("O ONI é analisado na frequência mensal registrada no arquivo, sem interpolar meses ausentes."),
            mo.ui.table(_estatisticas_enso, page_size=1),
            _grafico_enso,
            _box_enso,
        ])
    _saida_enso
    return


@app.cell
def _(conectar_banco, enso, historico_button, mo, pd, px, text):
    if not historico_button.value:
        _saida_historico = mo.md("## Relação histórica clima–ENSO\nClique no botão acima para calcular os agregados mensais do período completo no PostgreSQL.")
    elif enso.empty or not {"data", "oni"}.issubset(enso.columns):
        _saida_historico = mo.md("O CSV ENSO não está disponível; não é possível calcular a relação clima–ENSO.")
    else:
        _consulta_historica = text(
            """
            SELECT date_trunc('month', datetime)::date AS mes,
                   AVG(temperatura) AS temperatura_media,
                   AVG(umidade) AS umidade_media,
                   SUM(precipitacao) / NULLIF(COUNT(DISTINCT codigo_ibge), 0)
                       AS precipitacao_media_municipal_mm,
                   COUNT(*)::bigint AS observacoes
            FROM registro_climatico
            GROUP BY date_trunc('month', datetime)::date
            ORDER BY mes
            """
        )
        try:
            with conectar_banco() as _conexao:
                with _conexao.begin():
                    _conexao.execute(text("SET LOCAL statement_timeout = '60000ms'"))
                    _conexao.execute(text("SET LOCAL work_mem = '32MB'"))
                    _historico = pd.read_sql_query(_consulta_historica, _conexao)
            _historico["mes"] = pd.to_datetime(_historico["mes"])
            _relacao = _historico.merge(
                enso[["data", "oni"]], left_on="mes", right_on="data", how="inner"
            ).dropna(subset=["oni", "temperatura_media", "umidade_media"])
            _correlacoes = pd.DataFrame([
                {"Par de variáveis": "Temperatura média × ONI", "Correlação de Pearson": _relacao["temperatura_media"].corr(_relacao["oni"]), "Meses pareados": len(_relacao)},
                {"Par de variáveis": "Umidade média × ONI", "Correlação de Pearson": _relacao["umidade_media"].corr(_relacao["oni"]), "Meses pareados": len(_relacao)},
                {"Par de variáveis": "Precipitação média municipal × ONI", "Correlação de Pearson": _relacao["precipitacao_media_municipal_mm"].corr(_relacao["oni"]), "Meses pareados": len(_relacao)},
            ]).round(3)
            _grafico_relacao = px.scatter(
                _relacao, x="oni", y="temperatura_media", color="umidade_media",
                hover_data=["mes", "observacoes"],
                labels={"oni": "ONI (°C)", "temperatura_media": "Temperatura média (°C)", "umidade_media": "Umidade média (%)"},
                title="Temperatura mensal e ONI (ponto = mês)",
                color_continuous_scale="Turbo",
            )
            _saida_historico = mo.vstack([
                mo.md("## Relação histórica clima–ENSO"),
                mo.md(
                    f"**Meses climáticos agregados:** {len(_historico):,} · "
                    f"**Meses com ONI pareado:** {len(_relacao):,}. Correlação é descritiva e não implica causalidade."
                ),
                mo.ui.table(_correlacoes, page_size=3),
                _grafico_relacao,
            ])
        except Exception as _erro:
            _saida_historico = mo.md(
                "Não foi possível executar a consulta histórica. Ela lê todo o "
                "período no servidor, mas retorna apenas uma linha por mês e tem "
                f"limite de 60 s. Erro: `{type(_erro).__name__}: {_erro}`"
            )
    _saida_historico
    return


if __name__ == "__main__":
    app.run()
