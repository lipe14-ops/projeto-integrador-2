import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", auto_download=["html"])


@app.cell
def _():
    import json
    import os
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import geopandas as gpd
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text

    return (
        Path,
        create_engine,
        go,
        gpd,
        json,
        load_dotenv,
        mo,
        np,
        os,
        pd,
        px,
        text,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # EDA climática municipal — ERA5-Land / PostGIS

    Exploração da série climática por município, estado e região, com auditoria,
    estatística descritiva, gráficos interativos e mapas. A base observada no
    projeto contém temperatura (°C), umidade relativa (%) e precipitação (mm
    por intervalo de 12 h), às 00:00 e 12:00 UTC. Os agregados respeitam essas
    unidades: médias para temperatura/umidade e soma para precipitação.

    **Desempenho:** os GRIB (mais de 6 GiB) nunca são carregados aqui. O
    PostgreSQL agrega no servidor; a consulta inicial cobre um mês e a consulta
    temporal mais longa só roda ao clicar no botão. Os mapas de pontos usam
    centróides; o coroplético simplifica geometrias no PostGIS e exige selecionar
    uma UF. Uma tendência dentro deste produto ERA5-Land é descritiva, não prova
    mudança climática.
    """)
    return


@app.cell
def _(Path, gpd, mo, pd):
    _raiz = Path(__file__).resolve().parents[1]
    _pasta = _raiz / "data" / "era5_land"
    _arquivos = sorted(_pasta.glob("era5_land_????_??.grib"))
    _inventario = []
    for _arquivo in _arquivos:
        _ano_mes = _arquivo.stem.removeprefix("era5_land_").replace("_", "-")
        _inventario.append({
            "mês": _ano_mes,
            "arquivo": _arquivo.name,
            "tamanho_MiB": round(_arquivo.stat().st_size / 1024**2, 1),
        })
    inventario = pd.DataFrame(_inventario)
    _enso_path = _pasta / "registro_era5_enso.csv"
    if _enso_path.is_file():
        enso_df = pd.read_csv(_enso_path)
        _oni_col = "oni" if "oni" in enso_df.columns else "enso_index"
        if _oni_col in enso_df and {"year", "month"}.issubset(enso_df.columns):
            enso_df = enso_df.rename(columns={_oni_col: "oni"})
            enso_df["data"] = pd.to_datetime(
                dict(year=enso_df["year"], month=enso_df["month"], day=1),
                errors="coerce",
            )
            enso_df["oni"] = pd.to_numeric(enso_df["oni"], errors="coerce")
            enso_df = enso_df.dropna(subset=["data"]).sort_values("data")
    else:
        enso_df = pd.DataFrame(columns=["year", "month", "oni", "data"])

    _shp = _raiz / "data" / "BR_Municipios_2025" / "BR_Municipios_2025.shp"
    malha_ids = []
    _crs_malha = "ausente"
    if _shp.is_file():
        try:
            _atributos_malha = gpd.read_file(_shp, columns=["CD_MUN"], ignore_geometry=True)
            malha_ids = pd.to_numeric(_atributos_malha["CD_MUN"], errors="coerce").dropna().astype("int64").tolist()
            _crs_malha = str(gpd.read_file(_shp, rows=1).crs)
        except Exception as _erro:
            _crs_malha = f"erro de leitura: {type(_erro).__name__}"
    _parquet = _raiz / "data" / "municipios.parquet"
    _parquet_info = "ausente"
    if _parquet.is_file():
        try:
            import pyarrow.parquet as _pq
            _meta = _pq.ParquetFile(_parquet).metadata
            _parquet_info = f"{_meta.num_rows:,} linhas; {_meta.num_row_groups} grupo"
        except Exception as _erro:
            _parquet_info = f"não foi possível ler o metadado ({type(_erro).__name__})"
    _arquivo_mib = sum(x["tamanho_MiB"] for x in _inventario)
    _saida_fontes = mo.vstack([
        mo.md(
            f"**GRIB mensal:** {len(_inventario)} arquivos, {_arquivo_mib / 1024:.2f} GiB · "
            f"**ONI:** {len(enso_df):,} meses · **malha:** "
            f"{'Shapefile IBGE 2025 encontrado (' + _crs_malha + ')' if _shp.is_file() else 'Shapefile ausente'} · "
            f"**Parquet municipal:** {_parquet_info}"
        ),
        mo.ui.table(inventario, page_size=10),
        mo.md(
            "A malha disponível usa `CD_MUN` (código IBGE), nomes e siglas de UF. "
            "O Parquet contém `codigo_ibge`, dimensões "
            "municipais e geometria WKB. O notebook usa o PostGIS como fonte "
            "geográfica para evitar carregar a malha inteira na memória."
        ),
    ])
    _saida_fontes
    return enso_df, inventario, malha_ids


@app.cell
def _(Path, create_engine, load_dotenv, os, text):
    _raiz = Path(__file__).resolve().parents[1]
    load_dotenv(_raiz / ".env")
    _url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/geodata",
    )
    _engine = create_engine(
        _url, connect_args={"connect_timeout": 3}, pool_pre_ping=True,
    )

    def conectar():
        return _engine.connect()

    conectado = False
    erro_conexao = ""
    perfil = {}
    ufs = []
    meses_banco = []
    codigos_db = []
    try:
        with conectar() as _conn:
            _conn.execute(text("SELECT 1"))
            _dim = _conn.execute(text("""
                SELECT COUNT(*) AS municipios,
                       COUNT(*) FILTER (WHERE m.geometry IS NOT NULL) AS geometrias,
                       COUNT(*) FILTER (WHERE m.latitude IS NOT NULL AND m.longitude IS NOT NULL) AS coordenadas,
                       COUNT(*) FILTER (WHERE d.codigo_ibge IS NULL) AS sem_detalhes
                FROM municipio m LEFT JOIN municipio_details d USING (codigo_ibge)
            """)).mappings().one()
            _datas = _conn.execute(text("""
                SELECT min(datetime) AS inicio, max(datetime) AS fim
                FROM registro_climatico
            """)).mappings().one()
            _tamanho = _conn.execute(text("""
                SELECT pg_total_relation_size('registro_climatico') AS bytes,
                       (SELECT COUNT(*) FROM enso_mensal) AS meses_enso
            """)).mappings().one()
            ufs = list(_conn.execute(text(
                "SELECT DISTINCT uf FROM municipio_details ORDER BY uf"
            )).scalars())
            codigos_db = list(_conn.execute(text(
                "SELECT codigo_ibge FROM municipio ORDER BY codigo_ibge"
            )).scalars())
        perfil = {**dict(_dim), **dict(_datas), **dict(_tamanho)}
        conectado = True
    except Exception as _erro:
        erro_conexao = f"{type(_erro).__name__}: {_erro}"
    return (
        codigos_db,
        conectado,
        conectar,
        erro_conexao,
        meses_banco,
        perfil,
        ufs,
    )


@app.cell
def _(conectado, erro_conexao, mo, pd, perfil):
    if conectado:
        _periodo = (
            f"{pd.Timestamp(perfil['inicio']).date()} a {pd.Timestamp(perfil['fim']).date()}"
            if perfil["inicio"] is not None else "sem observações"
        )
        _saida_perfil = mo.vstack([
            mo.md(
                f"## Perfil e estrutura\n\nPostgreSQL conectado. **Período:** {_periodo}. "
                f"**Municípios na dimensão:** {perfil['municipios']:,}; "
                f"**variáveis climáticas analisadas:** 3; "
                f"**geometrias:** {perfil['geometrias']:,}; "
                f"**coordenadas:** {perfil['coordenadas']:,}; "
                f"**sem dimensão complementar:** {perfil['sem_detalhes']:,}. "
                f"**Tamanho da tabela climática com índices:** {perfil['bytes'] / 1024**3:.2f} GiB. "
                f"**ONI no banco:** {perfil['meses_enso']:,} meses."
            ),
            mo.md(
                "Esquema climático observado: chave primária `(codigo_ibge, datetime)` "
                "(portanto combinações duplicadas são impedidas pelo banco); colunas "
                "numéricas `temperatura`, `umidade`, `precipitacao`. A tabela tem índice "
                "por data. Frequência nominal da carga: 00:00 e 12:00 UTC. O banco está "
                "com aproximadamente 8 GiB indexados; totais globais exatos exigiriam "
                "varrer toda a tabela, então o perfil evita essa leitura pesada."
            ),
        ])
    else:
        _saida_perfil = mo.md(f"## Perfil e estrutura\n\nPostgreSQL indisponível: `{erro_conexao[:500]}`")
    _saida_perfil
    return


@app.cell
def _(codigos_db, conectado, malha_ids, mo):
    if conectado and malha_ids:
        _malha_set, _db_set = set(malha_ids), set(codigos_db)
        _faltam_db = sorted(_malha_set - _db_set)
        _faltam_malha = sorted(_db_set - _malha_set)
        _saida_integridade_geo = mo.md(
            f"**Integridade dos códigos geográficos:** {len(_malha_set):,} códigos únicos na malha "
            f"e {len(_db_set):,} na dimensão municipal; {len(_malha_set & _db_set):,} coincidem. "
            f"Sem correspondência no banco: {len(_faltam_db):,}; sem correspondência na malha: {len(_faltam_malha):,}. "
            "O relacionamento dos registros climáticos com municípios é protegido por chave estrangeira."
        )
    elif not conectado:
        _saida_integridade_geo = mo.md("A comparação de códigos com o PostGIS requer conexão com o banco.")
    else:
        _saida_integridade_geo = mo.md("A malha municipal não foi carregada; correspondência espacial não avaliada.")
    _saida_integridade_geo
    return


@app.cell
def _(inventario, meses_banco, mo, ufs):
    _meses = meses_banco or (inventario["mês"].tolist() if not inventario.empty else [])
    _anos = sorted({int(m[:4]) for m in _meses})
    _mes_padrao = _meses[-1] if _meses else ""
    mes = mo.ui.dropdown(
        options=_meses or ["sem dados"], value=_mes_padrao or "sem dados",
        label="Mês da auditoria e do mapa",
    )
    uf = mo.ui.dropdown(options=["Todas", *ufs], value="Todas", label="UF")
    variavel = mo.ui.dropdown(
        options={
            "Temperatura média (°C)": "temperatura",
            "Umidade relativa média (%)": "umidade",
            "Precipitação acumulada (mm)": "precipitacao",
        }, value="Temperatura média (°C)", label="Variável",
    )
    municipio_codigo = mo.ui.text(
        value="", label="Código IBGE (opcional, para série municipal)",
        placeholder="ex.: 5300108",
    )
    cobertura_minima = mo.ui.slider(
        start=0, stop=100, step=5, value=80,
        label="Cobertura mínima para ranking (%)",
    )
    if _anos:
        _ano_inicial = mo.ui.dropdown(
            options=_anos, value=_anos[-1], label="Ano inicial da série"
        )
        _ano_final = mo.ui.dropdown(
            options=_anos, value=_anos[-1], label="Ano final da série"
        )
    else:
        _ano_inicial = mo.ui.dropdown(options=[2025], value=2025, label="Ano inicial")
        _ano_final = mo.ui.dropdown(options=[2025], value=2025, label="Ano final")
    executar_serie = mo.ui.run_button(label="Carregar série agregada", kind="success")
    _saida_controles = mo.vstack([
        mo.md("## Filtros"),
        mo.hstack([mes, uf, variavel]),
        mo.hstack([_ano_inicial, _ano_final, municipio_codigo, executar_serie]),
        cobertura_minima,
        mo.md(
            "A auditoria mensal é leve e automática. O histórico usa uma consulta "
            "agregada no servidor, retorna no máximo uma linha por município/mês e "
            "só começa ao clicar. A consulta tem limite de 120 segundos no servidor; "
            "o padrão é um único ano recente e o período pode ser ampliado quando necessário."
        ),
    ])
    _saida_controles
    return (
        cobertura_minima,
        executar_serie,
        mes,
        municipio_codigo,
        uf,
        variavel,
    )


@app.cell
def _(conectado, conectar, mes, pd, text, uf):
    _cols = [
        "codigo_ibge", "municipio", "uf", "estado", "regiao", "latitude", "longitude",
        "registros", "temperatura_n", "umidade_n", "precipitacao_n",
        "temperatura_fora_limite", "umidade_fora_limite", "precipitacao_fora_limite",
        "temperatura", "umidade", "precipitacao",
    ]
    mensal_df = pd.DataFrame(columns=_cols)
    mensal_status = "Banco indisponível."
    if conectado and mes.value != "sem dados":
        _periodo = pd.Period(mes.value, freq="M")
        _inicio = _periodo.start_time.to_pydatetime()
        _fim = (_periodo + 1).start_time.to_pydatetime()
        _consulta = text("""
            WITH c AS (
                SELECT codigo_ibge, COUNT(*) AS registros,
                       COUNT(temperatura) AS temperatura_n,
                       COUNT(umidade) AS umidade_n,
                       COUNT(precipitacao) AS precipitacao_n,
                       COUNT(*) FILTER (WHERE temperatura IS NOT NULL AND (temperatura < -90 OR temperatura > 65)) AS temperatura_fora_limite,
                       COUNT(*) FILTER (WHERE umidade IS NOT NULL AND (umidade < 0 OR umidade > 100)) AS umidade_fora_limite,
                       COUNT(*) FILTER (WHERE precipitacao < 0) AS precipitacao_fora_limite,
                       AVG(temperatura) AS temperatura,
                       AVG(umidade) AS umidade,
                       SUM(precipitacao) AS precipitacao
                FROM registro_climatico
                WHERE datetime >= :inicio AND datetime < :fim
                GROUP BY codigo_ibge
            )
            SELECT m.codigo_ibge, d.municipio, d.uf, d.estado, d.regiao,
                   m.latitude, m.longitude,
                   COALESCE(c.registros,0) AS registros,
                   COALESCE(c.temperatura_n,0) AS temperatura_n,
                   COALESCE(c.umidade_n,0) AS umidade_n,
                   COALESCE(c.precipitacao_n,0) AS precipitacao_n,
                   COALESCE(c.temperatura_fora_limite,0) AS temperatura_fora_limite,
                   COALESCE(c.umidade_fora_limite,0) AS umidade_fora_limite,
                   COALESCE(c.precipitacao_fora_limite,0) AS precipitacao_fora_limite,
                   c.temperatura, c.umidade, c.precipitacao
            FROM municipio m
            LEFT JOIN municipio_details d USING (codigo_ibge)
            LEFT JOIN c USING (codigo_ibge)
            WHERE (CAST(:uf AS text) IS NULL OR d.uf = :uf)
              AND m.latitude IS NOT NULL AND m.longitude IS NOT NULL
            ORDER BY m.codigo_ibge
        """)
        try:
            with conectar() as _conn:
                _linhas = _conn.execute(_consulta, {
                    "inicio": _inicio, "fim": _fim,
                    "uf": None if uf.value == "Todas" else uf.value,
                }).mappings().all()
            mensal_df = pd.DataFrame(_linhas, columns=_cols)
            mensal_status = f"{len(mensal_df):,} municípios com coordenadas; {mes.value}."
        except Exception as _erro:
            mensal_status = f"Falha na consulta mensal ({type(_erro).__name__}): {_erro}"
    return mensal_df, mensal_status


@app.cell
def _(mensal_df, mensal_status, mes, mo, pd):
    if mensal_df.empty:
        _saida_auditoria = mo.md(f"## Auditoria mensal\n\n{mensal_status}\n\nSem linhas para auditar.")
    else:
        _dias = pd.Period(mes.value, freq="M").days_in_month
        _esperado = _dias * 2
        _variaveis = {
            "temperatura": ("temperatura_n", "temperatura_fora_limite", -90, 65),
            "umidade": ("umidade_n", "umidade_fora_limite", 0, 100),
            "precipitacao": ("precipitacao_n", "precipitacao_fora_limite", 0, None),
        }
        _linhas = []
        for _nome, (_ncol, _invalid_col, _min, _max) in _variaveis.items():
            _validos = int(mensal_df[_ncol].sum())
            _possiveis = len(mensal_df) * _esperado
            _fora = int(((mensal_df[_nome] < _min) | (mensal_df[_nome] > _max)).fillna(False).sum()) if _max is not None else int((mensal_df[_nome] < _min).fillna(False).sum())
            _linhas.append({
                "variável": _nome,
                "valores ausentes estimados*": max(_possiveis - _validos, 0),
                "% ausente*": round(100 * max(_possiveis - _validos, 0) / _possiveis, 2) if _possiveis else 0,
                "municípios sem nenhum valor": int((mensal_df[_ncol] == 0).sum()),
                "observações fora do limite físico básico": int(mensal_df[_invalid_col].sum()),
                "agregados municipais fora do limite": _fora,
            })
        _faltantes = pd.DataFrame(_linhas)
        _cobertura = (mensal_df["registros"].clip(upper=_esperado) / _esperado * 100).mean()
        _sem_registro = int((mensal_df["registros"] == 0).sum())
        _total_registros = int(mensal_df["registros"].sum())
        _saida_auditoria = mo.vstack([
            mo.md(
                f"## Auditoria mensal\n\n**{mensal_status}** Cobertura média das duas observações/dia: "
                f"{_cobertura:.1f}%; municípios sem observações: {_sem_registro:,}. "
                f"Registros climáticos no recorte: {_total_registros:,}. "
                "A expectativa por variável é uma aproximação da frequência de carga."
            ),
            mo.md("* Ausência estimada como frequência nominal (2 observações/dia) menos valores não nulos; meses/municípios parcialmente carregados podem afetar o denominador."),
            mo.ui.table(_faltantes, page_size=3),
            mo.md("A chave primária municipal-data impede duplicatas exatas. Os limites assinalam apenas valores impossíveis/incompatíveis em agregados, sem remover observações. Temperatura abaixo de −90 °C/acima de 65 °C, umidade fora de 0–100% e precipitação negativa são sinalizadas para inspeção."),
        ])
    _saida_auditoria
    return


@app.cell
def _(conectar, go, json, mensal_df, mes, mo, px, text, uf, variavel):
    if mensal_df.empty:
        _saida_espacial = mo.md("## Análise espacial\nSem dados para mapear neste recorte.")
    else:
        _campo = variavel.value
        _rotulos = {
            "temperatura": "Temperatura média (°C)",
            "umidade": "Umidade relativa média (%)",
            "precipitacao": "Precipitação acumulada mensal (mm)",
        }
        _pontos = mensal_df.dropna(subset=[_campo, "latitude", "longitude"])
        _mapa_pontos = px.scatter_geo(
            _pontos, lat="latitude", lon="longitude", color=_campo,
            hover_name="municipio", hover_data=["uf", "regiao", "codigo_ibge", "registros"],
            color_continuous_scale="Turbo", projection="mercator", scope="south america",
            title=f"{_rotulos[_campo]} por centróide municipal — {mes.value}",
        )
        _mapa_pontos.update_geos(
            center={"lat": -14, "lon": -52}, lataxis_range=[-35, 7], lonaxis_range=[-76, -32],
            showcountries=True, showland=True, landcolor="#f1f5f9",
        )
        _mapa_pontos.update_layout(height=600, margin={"l": 0, "r": 0, "t": 50, "b": 0})
        _grade = mensal_df.dropna(subset=["latitude", "longitude"]).copy()
        _grade["lat_cell"] = _grade["latitude"].astype(float).apply(lambda x: int(x // 1))
        _grade["lon_cell"] = _grade["longitude"].astype(float).apply(lambda x: int(x // 1))
        _grade = _grade.groupby(["lat_cell", "lon_cell"], as_index=False).agg(
            municipios=("codigo_ibge", "nunique"),
            latitude=("latitude", "mean"), longitude=("longitude", "mean"),
        )
        _mapa_densidade = px.scatter_geo(
            _grade, lat="latitude", lon="longitude", size="municipios", color="municipios",
            hover_data=["municipios"], color_continuous_scale="Viridis",
            projection="mercator", scope="south america", size_max=24,
            title="Pontos municipais por célula de 1° × 1° (densidade de localização)",
        )
        _mapa_densidade.update_geos(
            center={"lat": -14, "lon": -52}, lataxis_range=[-35, 7], lonaxis_range=[-76, -32],
            showcountries=True, showland=True, landcolor="#f1f5f9",
        )
        _mapa_densidade.update_layout(height=500, margin={"l": 0, "r": 0, "t": 50, "b": 0})
        _coropleto = mo.md("Selecione uma UF diferente de ‘Todas’ para consultar as geometrias simplificadas e montar o mapa coroplético.")
        if uf.value != "Todas":
            try:
                with conectar() as _conn:
                    _geom = _conn.execute(text("""
                        SELECT m.codigo_ibge::text AS codigo_ibge,
                               ST_AsGeoJSON(ST_SimplifyPreserveTopology(m.geometry, 0.01), 5) AS geom
                        FROM municipio m JOIN municipio_details d USING (codigo_ibge)
                        WHERE d.uf = :uf AND m.geometry IS NOT NULL
                    """), {"uf": uf.value}).mappings().all()
                _features = []
                for _row in _geom:
                    _features.append({
                        "type": "Feature",
                        "properties": {"codigo_ibge": str(_row["codigo_ibge"])},
                        "geometry": json.loads(_row["geom"]),
                    })
                _gj = {"type": "FeatureCollection", "features": _features}
                _valores = mensal_df.set_index("codigo_ibge")[_campo]
                _loc = [str(x) for x in mensal_df["codigo_ibge"]]
                _z = [float(x) if x == x else None for x in mensal_df[_campo]]
                _cor = go.Figure(go.Choropleth(
                    geojson=_gj, featureidkey="properties.codigo_ibge", locations=_loc,
                    z=_z, colorscale="Turbo", colorbar_title=_rotulos[_campo],
                    customdata=mensal_df[["municipio", "uf", "registros"]].to_numpy(),
                    hovertemplate="%{customdata[0]} (%{customdata[1]})<br>Valor: %{z:.2f}<br>Registros: %{customdata[2]}<extra></extra>",
                    marker_line_width=0.15,
                ))
                _cor.update_geos(fitbounds="locations", visible=False)
                _cor.update_layout(
                    title=f"{_rotulos[_campo]} por município — {uf.value}, {mes.value}",
                    height=650, margin={"l": 0, "r": 0, "t": 50, "b": 0},
                )
                _coropleto = _cor
            except Exception as _erro:
                _coropleto = mo.md(f"Falha ao criar coroplético: `{type(_erro).__name__}: {_erro}`")
        _saida_espacial = mo.vstack([
            mo.md("## Análise espacial municipal\nO ponto representa o centróide cadastrado, não a área inteira do município. Valores nulos são omitidos do mapa e permanecem identificáveis na auditoria."),
            _mapa_pontos,
            mo.md("A grade de 1° agrega os pontos de municípios por área aproximada; cada grau corresponde a cerca de 111 km norte–sul e varia no sentido leste–oeste."),
            _mapa_densidade,
            _coropleto,
        ])
    _saida_espacial
    return


@app.cell
def _(mensal_df, mo, np, pd, px, variavel):
    if mensal_df.empty:
        _saida_descritiva = mo.md("## Distribuições\nSem dados para calcular estatísticas.")
    else:
        _nomes = ["temperatura", "umidade", "precipitacao"]
        _linhas = []
        for _col in _nomes:
            _s = pd.to_numeric(mensal_df[_col], errors="coerce").dropna()
            if _s.empty:
                continue
            _q1, _q3 = _s.quantile([0.25, 0.75])
            _iqr = _q3 - _q1
            _linhas.append({
                "variável": _col, "n municípios": len(_s), "média": _s.mean(),
                "mediana": _s.median(), "desvio-padrão": _s.std(),
                "variância": _s.var(), "mínimo": _s.min(), "Q1": _q1,
                "Q3": _q3, "máximo": _s.max(), "IQR": _iqr,
                "CV (%)": 100 * _s.std() / abs(_s.mean()) if _s.mean() else np.nan,
                "assimetria": _s.skew(), "curtose": _s.kurt(),
                "P05": _s.quantile(.05), "P95": _s.quantile(.95),
                "outliers IQR": int(((_s < _q1 - 1.5*_iqr) | (_s > _q3 + 1.5*_iqr)).sum()),
            })
        _stats = pd.DataFrame(_linhas).round(3)
        _long = mensal_df.melt(
            id_vars=["codigo_ibge", "municipio", "uf", "regiao"],
            value_vars=_nomes, var_name="variável", value_name="valor",
        ).dropna(subset=["valor"])
        _box = px.box(
            _long, x="variável", y="valor", color="variável",
            facet_col="variável", facet_col_wrap=1, points="outliers",
            hover_data=["municipio", "uf", "codigo_ibge"],
            title="Distribuição dos agregados mensais entre municípios",
        )
        _hist = px.histogram(
            _long, x="valor", facet_col="variável", facet_col_wrap=1,
            marginal="rug", nbins=40, title="Histogramas por variável",
        )
        _regiao = mensal_df.groupby("regiao", dropna=False).agg(
            municipios=("codigo_ibge", "nunique"),
            temperatura_media=("temperatura", "mean"),
            umidade_media=("umidade", "mean"),
            precipitacao_media=("precipitacao", "mean"),
        ).reset_index().round(2)
        _box_regional = px.box(
            mensal_df.dropna(subset=[variavel.value]),
            x="regiao", y=variavel.value, color="regiao", points="outliers",
            hover_data=["municipio", "uf", "codigo_ibge"],
            title=f"{variavel.value}: distribuição municipal por região",
        )
        _saida_descritiva = mo.vstack([
            mo.md("## Estatística descritiva e comparação regional\nUm valor por município no mês selecionado. A precipitação é a soma dos intervalos de 12 h disponíveis; temperatura e umidade são médias. Outliers IQR são relativos a este recorte e não significam erro automaticamente."),
            mo.ui.table(_stats, page_size=3), _box, _hist,
            _box_regional,
            mo.md("Médias regionais simples dos agregados municipais; não ponderadas por área, população ou cobertura."),
            mo.ui.table(_regiao, page_size=10),
        ])
    _saida_descritiva
    return


@app.cell
def _(conectar, executar_serie, municipio_codigo, pd, text, uf):
    serie_df = pd.DataFrame()
    serie_n_municipios = 0
    serie_status = "Clique em ‘Carregar série agregada’ para executar a consulta temporal."
    if executar_serie.value:
        _ano_ini, _ano_fim = int(_ano_inicial.value), int(_ano_final.value)
        if _ano_ini > _ano_fim:
            serie_status = "Ano inicial posterior ao ano final. Ajuste os filtros."
        else:
            _codigo_txt = municipio_codigo.value.strip()
            try:
                _codigo = int(_codigo_txt) if _codigo_txt else None
                with conectar() as _conn:
                    serie_n_municipios = _conn.execute(text("""
                        SELECT COUNT(*) FROM municipio_details
                        WHERE (CAST(:uf AS text) IS NULL OR uf = :uf)
                          AND (CAST(:codigo AS bigint) IS NULL OR codigo_ibge = :codigo)
                    """), {
                        "uf": None if uf.value == "Todas" else uf.value,
                        "codigo": _codigo,
                    }).scalar_one()
                _q = text("""
                    SELECT date_trunc('month', r.datetime)::date AS mes,
                           d.codigo_ibge, d.municipio, d.uf, d.regiao,
                           AVG(r.temperatura) AS temperatura,
                           AVG(r.umidade) AS umidade,
                           SUM(r.precipitacao) AS precipitacao,
                           COUNT(*) AS registros,
                           COUNT(r.temperatura) AS temperatura_n,
                           COUNT(r.umidade) AS umidade_n,
                           COUNT(r.precipitacao) AS precipitacao_n,
                           COUNT(*) FILTER (WHERE r.temperatura IS NOT NULL AND (r.temperatura < -90 OR r.temperatura > 65)) AS temperatura_fora_limite,
                           COUNT(*) FILTER (WHERE r.umidade IS NOT NULL AND (r.umidade < 0 OR r.umidade > 100)) AS umidade_fora_limite,
                           COUNT(*) FILTER (WHERE r.precipitacao < 0) AS precipitacao_fora_limite
                    FROM registro_climatico r
                    JOIN municipio_details d USING (codigo_ibge)
                    WHERE r.datetime >= make_timestamptz(:ano_ini,1,1,0,0,0,'UTC')
                      AND r.datetime < make_timestamptz(:ano_fim + 1,1,1,0,0,0,'UTC')
                      AND (CAST(:codigo AS bigint) IS NULL OR r.codigo_ibge = :codigo)
                      AND (CAST(:uf AS text) IS NULL OR d.uf = :uf)
                    GROUP BY 1,2,3,4,5
                    ORDER BY 1,2
                """)
                with conectar() as _conn:
                    with _conn.begin():
                        _conn.execute(text("SET LOCAL statement_timeout = '120000ms'"))
                        _conn.execute(text("SET LOCAL work_mem = '32MB'"))
                        serie_df = pd.read_sql_query(_q, _conn, params={
                            "ano_ini": _ano_ini, "ano_fim": _ano_fim, "codigo": _codigo,
                            "uf": None if uf.value == "Todas" else uf.value,
                        })
                serie_df["mes"] = pd.to_datetime(serie_df["mes"])
                serie_status = f"{len(serie_df):,} município-mês agregados, { _ano_ini }–{ _ano_fim }."
                if _codigo is not None and serie_df.empty:
                    serie_status += " Código sem observações no período."
            except Exception as _erro:
                serie_status = f"Consulta temporal falhou ({type(_erro).__name__}): {_erro}"
    return serie_df, serie_n_municipios, serie_status


@app.cell
def _(enso_df, mo, pd, px, serie_df, serie_n_municipios, serie_status):
    if serie_df.empty:
        _saida_temporal = mo.md(f"## Evolução temporal\n\n{serie_status}")
    else:
        _mensal = serie_df.groupby("mes", as_index=False).agg(
            temperatura=("temperatura", "mean"), umidade=("umidade", "mean"),
            precipitacao=("precipitacao", "mean"), municipios=("codigo_ibge", "nunique"),
            observacoes=("registros", "sum"),
            temperatura_n=("temperatura_n", "sum"),
            umidade_n=("umidade_n", "sum"),
            precipitacao_n=("precipitacao_n", "sum"),
        )
        _calendario_completo = pd.date_range(
            _mensal["mes"].min(), _mensal["mes"].max(), freq="MS"
        )
        _mensal = _mensal.set_index("mes").reindex(_calendario_completo)
        _mensal.index.name = "mes"
        _mensal = _mensal.reset_index()
        for _col in ["municipios", "observacoes", "temperatura_n", "umidade_n", "precipitacao_n"]:
            _mensal[_col] = _mensal[_col].fillna(0)
        _mensal["mês observado"] = _mensal["observacoes"] > 0
        _mensal["dias"] = _mensal["mes"].dt.days_in_month
        _mensal["esperadas"] = serie_n_municipios * 2 * _mensal["dias"]
        for _var in ["temperatura", "umidade", "precipitacao"]:
            _mensal[f"{_var}_faltantes_pct"] = (
                100 * (1 - _mensal[f"{_var}_n"] / _mensal["esperadas"])
            ).clip(0, 100)
        _long = _mensal.melt(
            id_vars=["mes", "municipios", "observacoes"],
            value_vars=["temperatura", "umidade", "precipitacao"],
            var_name="variável", value_name="valor",
        )
        _fig = px.line(
            _long, x="mes", y="valor", color="variável", markers=True,
            facet_row="variável",
            title="Médias dos agregados municipais por mês",
            hover_data=["municipios", "observacoes"],
        )
        _fig.update_xaxes(rangeslider_visible=True)
        _fig.update_yaxes(matches=None)
        _calendario = pd.date_range(_mensal["mes"].min(), _mensal["mes"].max(), freq="MS")
        _faltam_meses = _calendario.difference(serie_df["mes"].drop_duplicates())
        _faltantes_long = _mensal.melt(
            id_vars=["mes"],
            value_vars=["temperatura_faltantes_pct", "umidade_faltantes_pct", "precipitacao_faltantes_pct"],
            var_name="variável", value_name="faltantes (%)",
        )
        _fig_faltantes = px.line(
            _faltantes_long, x="mes", y="faltantes (%)", color="variável", markers=True,
            title="Percentual ausente por mês (frequência nominal 2/dia)",
        )
        _mensal["mês do ano"] = _mensal["mes"].dt.month
        _sazonal = _mensal.groupby("mês do ano", as_index=False).agg(
            temperatura=("temperatura", "mean"), umidade=("umidade", "mean"),
            precipitacao=("precipitacao", "mean"),
            meses_observados=("mês observado", "sum"),
        )
        _saz_long = _sazonal.melt(
            id_vars=["mês do ano", "meses_observados"],
            value_vars=["temperatura", "umidade", "precipitacao"],
            var_name="variável", value_name="valor",
        )
        _fig_saz = px.line(
            _saz_long, x="mês do ano", y="valor", color="variável", markers=True,
            facet_row="variável",
            title="Ciclo sazonal médio no período carregado",
            hover_data=["meses_observados"],
        )
        _fig_saz.update_yaxes(matches=None)
        _anual = _mensal.assign(ano=_mensal["mes"].dt.year).groupby("ano", as_index=False).agg(
            temperatura=("temperatura", "mean"), umidade=("umidade", "mean"),
            precipitacao=("precipitacao", "mean"),
            meses_observados=("mês observado", "sum"),
        )
        _fig_anual = px.line(
            _anual.melt(id_vars=["ano", "meses_observados"],
                        value_vars=["temperatura", "umidade", "precipitacao"],
                        var_name="variável", value_name="valor"),
            x="ano", y="valor", color="variável", markers=True,
            facet_row="variável",
            hover_data=["meses_observados"], title="Resumo anual (média dos agregados mensais)",
        )
        _fig_anual.update_yaxes(matches=None)
        _trend_rows = []
        for _v in ["temperatura", "umidade", "precipitacao"]:
            _s = _anual.dropna(subset=[_v])
            _slope = float("nan")
            if len(_s) >= 3:
                _x = _s["ano"].to_numpy() - _s["ano"].min()
                _m, _b = __import__("numpy").polyfit(_x, _s[_v].to_numpy(), 1)
                _slope = float(_m)
            _trend_rows.append({"variável": _v, "slope anual (descritivo)": _slope, "anos": len(_s)})
        _trends = pd.DataFrame(_trend_rows).round(4)
        _state = serie_df.groupby(["uf", "mes"], as_index=False).agg(
            temperatura=("temperatura", "mean"), umidade=("umidade", "mean"),
            precipitacao=("precipitacao", "mean"), municipios=("codigo_ibge", "nunique"),
        )
        _state_fig = px.line(
            _state, x="mes", y="temperatura", color="uf", hover_data=["municipios"],
            title="Temperatura mensal por estado",
        )
        _region = serie_df.groupby(["regiao", "mes"], as_index=False).agg(
            temperatura=("temperatura", "mean"), municipios=("codigo_ibge", "nunique"),
        )
        _region_fig = px.line(
            _region, x="mes", y="temperatura", color="regiao",
            hover_data=["municipios"], title="Temperatura mensal por região",
        )
        if not enso_df.empty and "oni" in enso_df:
            _enso = enso_df[["data", "oni"]].dropna().rename(columns={"data": "mes"})
            _pair = _mensal.merge(_enso, on="mes", how="inner")
            _corr = pd.DataFrame([
                {"par": _v + " × ONI", "Pearson": _pair[_v].corr(_pair["oni"]), "meses pareados": len(_pair)}
                for _v in ["temperatura", "umidade", "precipitacao"]
            ]).round(3)
            _fig_enso = px.scatter(
                _pair, x="oni", y="temperatura", color="umidade", hover_data=["mes"],
                title="Temperatura mensal e ONI (associação descritiva)",
            )
            _enso_output = mo.vstack([mo.ui.table(_corr, page_size=3), _fig_enso])
        else:
            _enso_output = mo.md("Série ONI não disponível para pareamento.")
        if _mensal["mes"].dt.year.nunique() >= 2:
            for _v in ["temperatura", "umidade", "precipitacao"]:
                _mensal[f"{_v}_anomalia"] = _mensal[_v] - _mensal.groupby(
                    _mensal["mes"].dt.month
                )[_v].transform("mean")
            _anom_long = _mensal.melt(
                id_vars=["mes"],
                value_vars=["temperatura_anomalia", "umidade_anomalia", "precipitacao_anomalia"],
                var_name="variável", value_name="desvio",
            )
            _fig_anomalia = px.line(
                _anom_long, x="mes", y="desvio", color="variável", markers=True,
                facet_row="variável",
                title="Desvio da média do mesmo mês do ano no período selecionado",
            )
            _fig_anomalia.update_yaxes(matches=None)
        else:
            _fig_anomalia = mo.md(
                "Anomalias relativas ao mesmo mês exigem pelo menos dois anos; aumente o período selecionado."
            )
        _saida_temporal = mo.vstack([
            mo.md(
                f"## Evolução temporal\n\n**{serie_status}** Estatísticas mensais são médias simples "
                "entre município-mês disponíveis; precipitação é soma por município-mês e depois média municipal. "
                "A ausência de um município em algum mês não é preenchida por interpolação."
            ),
            mo.md(
                f"Lacunas mensais sem qualquer registro agregado neste filtro: "
                f"{len(_faltam_meses)}" + (f" ({', '.join(x.strftime('%Y-%m') for x in _faltam_meses[:12])})" if len(_faltam_meses) else ".")
            ),
            _fig, _fig_faltantes, _fig_saz, _fig_anual, _state_fig, _region_fig, _fig_anomalia,
            mo.md("Anomalias são desvios à média do mesmo mês do ano calculada dentro do período selecionado, não uma climatologia de referência. Inclinação linear usa resumos anuais, só é estimada com pelo menos 3 anos e não corrige autocorrelação; é exploratória, não evidência conclusiva de tendência climática."),
            mo.ui.table(_trends, page_size=3),
            mo.md("Correlação com ONI usa meses pareados e é descritiva; mistura sazonalidade e diferenças regionais, não implica causalidade."),
            _enso_output,
        ])
    _saida_temporal
    return


@app.cell
def _(mo, pd, px, serie_df):
    if serie_df.empty:
        _saida_qualidade = mo.md("## Variabilidade, extremos e correlações\nCarregue uma série para calcular estes diagnósticos.")
    else:
        _linhas = []
        for _var in ["temperatura", "umidade", "precipitacao"]:
            _x = serie_df[_var].dropna()
            _q1, _q3 = _x.quantile([.25, .75])
            _lim_inf, _lim_sup = _q1 - 1.5*(_q3-_q1), _q3 + 1.5*(_q3-_q1)
            _linhas.append({
                "variável": _var, "município-mês válidos": len(_x),
                "extremos relativos (1,5 IQR)": int(((_x < _lim_inf) | (_x > _lim_sup)).sum()),
                "observações fora de limite básico": int(serie_df[f"{_var}_fora_limite"].sum()),
            })
        _diag = pd.DataFrame(_linhas)
        _complete = serie_df[["temperatura", "umidade", "precipitacao"]].dropna()
        _pearson = _complete.corr(method="pearson").round(3)
        _spearman = _complete.corr(method="spearman").round(3)
        _heat_p = px.imshow(_pearson, text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="Correlação de Pearson")
        _heat_s = px.imshow(_spearman, text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="Correlação de Spearman")
        _scatter = px.scatter_matrix(
            _complete.sample(min(len(_complete), 5000), random_state=42),
            dimensions=["temperatura", "umidade", "precipitacao"],
            title="Relações entre agregados município-mês (amostra máx. 5.000)",
        )
        _saida_qualidade = mo.vstack([
            mo.md("## Variabilidade, extremos relativos e relações entre variáveis\nExtremos usam 1,5×IQR dentro do período consultado e devem ser inspecionados; não são eventos climatológicos oficiais. Correlações usam linhas com as três variáveis disponíveis e podem refletir sazonalidade, geografia e cobertura desigual."),
            mo.ui.table(_diag, page_size=3), _heat_p, _heat_s, _scatter,
        ])
    _saida_qualidade
    return


@app.cell
def _(cobertura_minima, mensal_df, mes, mo, pd, variavel):
    if mensal_df.empty:
        _saida_sintese = mo.md("## Síntese\nSem dados no recorte selecionado.")
    else:
        _v = variavel.value
        _s = mensal_df[_v].dropna()
        _pior = mensal_df[_v].idxmin() if not _s.empty else None
        _melhor = mensal_df[_v].idxmax() if not _s.empty else None
        _txt = (
            f"## Síntese do mês selecionado\n\n{len(mensal_df):,} municípios com coordenadas no recorte; "
            f"{len(_s):,} com {_v} válido."
        )
        if not _s.empty:
            _txt += (
                f" Média municipal {_s.mean():.2f}, mediana {_s.median():.2f}, "
                f"intervalo observado {_s.min():.2f}–{_s.max():.2f}. "
                f"Menor valor: {mensal_df.loc[_pior, 'municipio']} ({mensal_df.loc[_pior, 'uf']}); "
                f"maior: {mensal_df.loc[_melhor, 'municipio']} ({mensal_df.loc[_melhor, 'uf']})."
            )
        _txt += " A síntese descreve somente o recorte; dados municipais incompletos e a grade ERA5-Land (~9 km) limitam comparações locais."
        _dias = pd.Period(mes.value, freq="M").days_in_month
        _esperado = _dias * 2
        _ranking = mensal_df.copy()
        _ranking["cobertura_pct"] = (
            _ranking[f"{_v}_n"].clip(upper=_esperado) / _esperado * 100
        )
        _ranking = _ranking[
            (_ranking["cobertura_pct"] >= cobertura_minima.value)
            & _ranking[_v].notna()
        ].sort_values(_v)
        _ranking = pd.concat([_ranking.head(10), _ranking.tail(10)]).drop_duplicates("codigo_ibge")
        _ranking["cobertura_pct"] = _ranking["cobertura_pct"].round(1)
        _saida_sintese = mo.vstack([
            mo.md(_txt + f"\n\nRanking abaixo: cobertura mínima de {cobertura_minima.value}% aplicada."),
            mo.ui.table(
                _ranking[["codigo_ibge", "municipio", "uf", _v, "registros", "cobertura_pct"]],
                page_size=20,
            ),
        ])
    _saida_sintese
    return


if __name__ == "__main__":
    app.run()
