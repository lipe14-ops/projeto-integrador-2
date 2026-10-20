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
    import xarray as xr
    from shapely.geometry import Point, shape
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text

    return (
        Path,
        Point,
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
        shape,
        text,
        xr,
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

    **Desempenho:** o PostgreSQL agrega as séries no servidor; a consulta inicial
    cobre um mês e a série temporal é controlada pelos anos abaixo. Para mapas
    municipais, somente o GRIB do mês selecionado é consultado. O mapa geral usa
    centróides; os mapas municipais usam os centros internos da grade e podem
    exibir a interpolação contínua. O coroplético simplifica geometrias no PostGIS
    e exige selecionar uma UF. Uma tendência dentro deste produto ERA5-Land é
    descritiva, não prova mudança climática.
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
def _(Path, gpd, inventario, mo, np, xr):
    _raiz_cobertura = Path(__file__).resolve().parents[1]
    _shp_cobertura = _raiz_cobertura / "data" / "BR_Municipios_2025" / "BR_Municipios_2025.shp"
    if inventario.empty or not _shp_cobertura.is_file():
        _saida_cobertura_grade = mo.md(
            "## Cobertura espacial da grade ERA5-Land\n\nA análise requer a malha IBGE 2025 e ao menos um GRIB local."
        )
    else:
        try:
            import shapely as _shapely

            _municipios_grade = gpd.read_file(_shp_cobertura).to_crs("EPSG:4326")
            _municipios_grade = _municipios_grade.loc[
                ~_municipios_grade["CD_MUN"].astype(str).isin(["4300001", "4300002"])
            ].copy()
            _arquivo_grade = _raiz_cobertura / "data" / "era5_land" / inventario.iloc[0]["arquivo"]
            with xr.open_dataset(
                _arquivo_grade, engine="cfgrib", backend_kwargs={"indexpath": ""}
            ) as _ds_grade:
                _lon_grade, _lat_grade = np.meshgrid(
                    _ds_grade.longitude.values, _ds_grade.latitude.values
                )
            _contagens_grade = []
            for _geom in _municipios_grade.geometry:
                if _geom is None or _geom.is_empty:
                    _contagens_grade.append(0)
                    continue
                _minx, _miny, _maxx, _maxy = _geom.bounds
                _candidato_grade = (
                    (_lon_grade >= _minx) & (_lon_grade <= _maxx)
                    & (_lat_grade >= _miny) & (_lat_grade <= _maxy)
                )
                _contagens_grade.append(int(np.count_nonzero(
                    _shapely.intersects_xy(
                        _geom, _lon_grade[_candidato_grade], _lat_grade[_candidato_grade]
                    )
                )))
            _municipios_grade["pontos internos"] = _contagens_grade
            _sem_pontos_grade = _municipios_grade.loc[
                _municipios_grade["pontos internos"] == 0,
                ["CD_MUN", "NM_MUN", "SIGLA_UF", "pontos internos"],
            ].rename(columns={
                "CD_MUN": "código IBGE", "NM_MUN": "município", "SIGLA_UF": "UF",
            }).sort_values(["UF", "município"])
            _resumo_uf_grade = (
                _sem_pontos_grade.groupby("UF", as_index=False)
                .size().rename(columns={"size": "municípios sem ponto"})
                .sort_values("municípios sem ponto", ascending=False)
            )
            _saida_cobertura_grade = mo.vstack([
                mo.md(
                    f"## Cobertura espacial da grade ERA5-Land\n\n"
                    f"Na malha IBGE 2025, **{len(_sem_pontos_grade):,} de "
                    f"{len(_municipios_grade):,} municípios não têm nenhum centro da grade "
                    "(~9 km) dentro do polígono. A contagem usa os centros da grade do GRIB "
                    "local; como a grade espacial é comum aos meses, foi lido apenas o arquivo "
                    f"{_arquivo_grade.name}. Municípios pequenos podem não conter um centro, "
                    "mesmo estando cobertos por células ERA5-Land vizinhas."
                ),
                mo.ui.table(_resumo_uf_grade, page_size=10),
                mo.ui.table(_sem_pontos_grade, page_size=20),
            ])
        except Exception as _erro_cobertura:
            _saida_cobertura_grade = mo.md(
                "## Cobertura espacial da grade ERA5-Land\n\n"
                f"Não foi possível calcular a cobertura ({type(_erro_cobertura).__name__}: {_erro_cobertura})."
            )
    _saida_cobertura_grade
    return


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
    municipios_db = []
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
            meses_banco = list(_conn.execute(text(
                """SELECT DISTINCT to_char(date_trunc('month', datetime), 'YYYY-MM')
                   FROM registro_climatico ORDER BY 1"""
            )).scalars())
            codigos_db = list(_conn.execute(text(
                "SELECT codigo_ibge FROM municipio ORDER BY codigo_ibge"
            )).scalars())
            municipios_db = list(_conn.execute(text(
                "SELECT codigo_ibge, municipio, uf FROM municipio_details ORDER BY municipio, uf"
            )).mappings())
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
        municipios_db,
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
def _(inventario, meses_banco, mo, municipios_db, ufs):
    _meses = meses_banco or (inventario["mês"].tolist() if not inventario.empty else [])
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
    _opcoes_municipios = {"Selecione um município": ""}
    _opcoes_municipios.update({
        f"{m['municipio']} ({m['uf']}) — {m['codigo_ibge']}": str(m["codigo_ibge"])
        for m in municipios_db
    })
    municipio_codigo = mo.ui.dropdown(
        options=_opcoes_municipios, value="Selecione um município", label="Município",
    )
    modo_mapa = mo.ui.radio(
        options={"Pontos": "pontos", "Superfície contínua": "superficie"},
        value="Pontos", label="Mapa municipal",
    )
    cobertura_minima = mo.ui.slider(
        start=0, stop=100, step=5, value=80,
        label="Cobertura mínima para ranking (%)",
    )
    _saida_controles = mo.vstack([
        mo.md("## Filtros"),
        mo.hstack([mes, uf, variavel]),
        municipio_codigo,
        modo_mapa,
        cobertura_minima,
    ])
    _saida_controles
    return cobertura_minima, mes, modo_mapa, municipio_codigo, uf, variavel


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
        _rotulos_box = {
            "temperatura": "Temperatura (°C)",
            "umidade": "Umidade relativa (%)",
            "precipitacao": "Precipitação (mm)",
        }
        _boxplots = []
        for _coluna_box in _nomes:
            _dados_box = mensal_df.dropna(subset=[_coluna_box])
            _grafico_box = px.box(
                _dados_box, y=_coluna_box, points="outliers",
                hover_data=["municipio", "uf", "codigo_ibge"],
                title=_rotulos_box[_coluna_box],
            )
            _grafico_box.update_layout(
                showlegend=False, height=350,
                margin={"l": 35, "r": 10, "t": 55, "b": 35},
                yaxis_title=_rotulos_box[_coluna_box],
            )
            _boxplots.append(_grafico_box)
        _box = mo.hstack(_boxplots, widths="equal")
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
def _(inventario, meses_banco, mo):
    _meses_serie = meses_banco or (
        inventario["mês"].tolist() if not inventario.empty else []
    )
    _anos_serie = sorted({int(_m[:4]) for _m in _meses_serie})
    if _anos_serie:
        ano_inicial = mo.ui.dropdown(
            options=_anos_serie, value=_anos_serie[-1], label="Ano inicial"
        )
        ano_final = mo.ui.dropdown(
            options=_anos_serie, value=_anos_serie[-1], label="Ano final"
        )
    else:
        ano_inicial = mo.ui.dropdown(options=[2025], value=2025, label="Ano inicial")
        ano_final = mo.ui.dropdown(options=[2025], value=2025, label="Ano final")
    executar_serie = mo.ui.run_button(
        label="Carregar série agregada", kind="success"
    )
    mo.vstack([
        mo.md(
            "### Gerar série temporal\n\n"
            "Defina o período e clique para consultar os agregados mensais por UF. "
            "A seleção de município nos filtros carrega automaticamente a série "
            "municipal para os gráficos e o perfil. A consulta retorna uma linha por "
            "município/mês e tem limite de 120 segundos."
        ),
        mo.hstack([ano_inicial, ano_final, executar_serie]),
    ])
    return ano_final, ano_inicial, executar_serie


@app.cell
def _(
    ano_final,
    ano_inicial,
    conectar,
    executar_serie,
    municipio_codigo,
    pd,
    text,
    uf,
):
    serie_df = pd.DataFrame()
    serie_n_municipios = 0
    serie_status = "Selecione um município ou clique em ‘Carregar série agregada’ para executar a consulta temporal."
    if executar_serie.value or municipio_codigo.value:
        _ano_ini, _ano_fim = int(ano_inicial.value), int(ano_final.value)
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
def _(
    Path,
    Point,
    conectar,
    enso_df,
    go,
    json,
    mes,
    mo,
    modo_mapa,
    municipio_codigo,
    np,
    pd,
    px,
    serie_df,
    shape,
    text,
    xr,
):
    _codigo_txt = municipio_codigo.value.strip()
    _variaveis = {
        "temperatura": ("Temperatura média (°C)", "°C"),
        "umidade": ("Umidade relativa média (%)", "%"),
        "precipitacao": ("Precipitação acumulada (mm/mês)", "mm/mês"),
    }
    if not _codigo_txt:
        _saida_distribuicao = mo.md(
            "## Distribuição contínua municipal\n\nSelecione um município e carregue a série para visualizar o perfil e a distribuição."
        )
    elif serie_df.empty:
        _saida_distribuicao = mo.md(
            "## Distribuição contínua municipal\n\nCarregue a série para gerar a distribuição do município selecionado."
        )
    else:
        _municipio_df = serie_df[
            serie_df["codigo_ibge"].astype(str) == _codigo_txt
        ]
        _disponiveis = {
            _coluna: _municipio_df[_coluna].dropna().to_numpy(dtype=float)
            for _coluna in _variaveis
        }
        _area = None
        try:
            with conectar() as _conn:
                _info = _conn.execute(text("""
                    SELECT d.municipio, d.uf, d.estado, d.regiao, d.mesorregiao,
                           d.microrregiao, d.populacao, d.ano_populacao, d.area_km2,
                           d.bioma, d.geomorfologia, d.regiao_geomorfologica,
                           d.dominio_geomorfologico
                    FROM municipio_details d
                    WHERE d.codigo_ibge = :codigo
                """), {"codigo": int(_codigo_txt)}).mappings().one_or_none()
            if _info is None:
                _info_md = "Município não encontrado na dimensão complementar."
            else:
                _area = float(_info["area_km2"]) if _info["area_km2"] is not None else None
                _pop = int(_info["populacao"]) if _info["populacao"] is not None else None
                _dens_pop = _pop / _area if _pop is not None and _area and _area > 0 else None
                _n_observacoes = int(_municipio_df["registros"].sum())
                _formatado = lambda _v: f"{_v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                _pop_formatada = f"{_pop:,}".replace(",", ".") if _pop is not None else "não informada"
                _ano_pop = f" (ano {_info['ano_populacao']})" if _info["ano_populacao"] else ""
                _regiao_geo = f" ({_info['regiao_geomorfologica']})" if _info["regiao_geomorfologica"] else ""
                _dominio_geo = f" — {_info['dominio_geomorfologico']}" if _info["dominio_geomorfologico"] else ""
                _info_md = (
                    f"### {_info['municipio']} ({_info['uf']})\n\n"
                    f"**Código IBGE:** {_codigo_txt} · **Estado:** {_info['estado']} · "
                    f"**Região:** {_info['regiao'] or 'não informado'}  \n"
                    f"**Área:** {_formatado(_area) + ' km²' if _area is not None else 'não informada'} · "
                    f"**População:** {_pop_formatada}{_ano_pop} · "
                    f"**Densidade populacional:** {_formatado(_dens_pop) + ' hab./km²' if _dens_pop is not None else 'indisponível'}  \n"
                    f"**Mesorregião:** {_info['mesorregiao'] or 'não informada'} · "
                    f"**Microrregião:** {_info['microrregiao'] or 'não informada'}  \n"
                    f"**Bioma:** {_info['bioma'] or 'não informado'} · "
                    f"**Geomorfologia:** {_info['geomorfologia'] or 'não informada'}"
                    f"{_regiao_geo}{_dominio_geo}  \n"
                    f"**Observações climáticas no período carregado:** {_n_observacoes:,}."
                )
        except Exception as _erro_info:
            _info_md = f"Não foi possível carregar o perfil municipal ({type(_erro_info).__name__})."
        if not any(len(_v) for _v in _disponiveis.values()):
            _saida_distribuicao = mo.md(
                f"## Perfil municipal e distribuição mensal\n\n{_info_md}\n\nNão há dados mensais válidos para este município no período carregado."
            )
        else:
            _graficos_distribuicao = []
            for _coluna, (_rotulo, _unidade) in _variaveis.items():
                _valores = _disponiveis[_coluna]
                _grafico = go.Figure()
                if len(_valores):
                    _grafico.add_trace(go.Box(
                        y=_valores,
                        name="Agregados mensais",
                        boxpoints="outliers",
                        customdata=_municipio_df.loc[
                            _municipio_df[_coluna].notna(), "mes"
                        ].dt.strftime("%Y-%m").to_numpy(),
                        hovertemplate=(
                            "%{y:.2f} " + _unidade + "<br>Mês: %{customdata}"
                            "<extra></extra>"
                        ),
                    ))
                else:
                    _grafico.add_annotation(
                        text="Sem dados mensais", x=0.5, y=0.5, xref="paper", yref="paper",
                        showarrow=False,
                    )
                _grafico.update_layout(
                    title=_rotulo,
                    yaxis_title=_unidade,
                    showlegend=False,
                    height=350,
                    margin={"l": 45, "r": 15, "t": 55, "b": 35},
                )
                _graficos_distribuicao.append(_grafico)
            _saida_distribuicao = mo.vstack([
                mo.md(_info_md),
                mo.md(
                    "## Distribuição mensal municipal\n\n"
                    "Os três box plots resumem temperatura, umidade e precipitação mensal. "
                    "A precipitação está em mm/mês; cada variável mantém sua unidade original."
                ),
                mo.hstack(_graficos_distribuicao, widths="equal"),
            ])
            if enso_df.empty or not {"data", "oni"}.issubset(enso_df.columns):
                _saida_enso_municipal = mo.md(
                    "## Relação com o ONI (El Niño–La Niña)\n\nA série mensal do ONI não está disponível para pareamento."
                )
            else:
                _enso_mensal = enso_df[["data", "oni"]].dropna().rename(columns={"data": "mes"})
                _pareado_enso = _municipio_df[["mes", *_variaveis.keys()]].merge(
                    _enso_mensal, on="mes", how="inner"
                )
                _linhas_enso = []
                _graficos_enso = []
                for _coluna, (_rotulo, _unidade) in _variaveis.items():
                    _dados_enso = _pareado_enso.dropna(subset=["oni", _coluna])
                    _r = (
                        _dados_enso["oni"].corr(_dados_enso[_coluna])
                        if len(_dados_enso) >= 2 else float("nan")
                    )
                    _linhas_enso.append({
                        "Variável": _rotulo,
                        "Pearson com ONI": _r,
                        "Meses pareados": len(_dados_enso),
                    })
                    _grafico_enso = px.scatter(
                        _dados_enso,
                        x="oni",
                        y=_coluna,
                        hover_data={"mes": True, "oni": ":.2f", _coluna: ":.2f"},
                        labels={"oni": "ONI (°C)", _coluna: f"{_rotulo} ({_unidade})"},
                        title=f"ONI × {_rotulo.lower()}",
                    )
                    _grafico_enso.update_layout(
                        height=350,
                        showlegend=False,
                        margin={"l": 45, "r": 15, "t": 55, "b": 40},
                    )
                    _graficos_enso.append(_grafico_enso)
                _saida_enso_municipal = mo.vstack([
                    mo.md(
                        "## Relação dos agregados mensais com o ONI\n\n"
                        "Cada ponto representa um mês pareado do município selecionado. "
                        "A correlação de Pearson resume associação linear; não indica causalidade."
                    ),
                    mo.ui.table(pd.DataFrame(_linhas_enso).round(3), page_size=3),
                    mo.hstack(_graficos_enso, widths="equal"),
                ])
            _saida_distribuicao = mo.vstack([_saida_distribuicao, _saida_enso_municipal])
            try:
                with conectar() as _conn:
                    _geojson = _conn.execute(text("""
                        SELECT ST_AsGeoJSON(m.geometry, 6)
                        FROM municipio m
                        WHERE m.codigo_ibge = :codigo AND m.geometry IS NOT NULL
                    """), {"codigo": int(_codigo_txt)}).scalar_one_or_none()
                _arquivo_grib = (
                    Path(__file__).resolve().parents[1]
                    / "data" / "era5_land" / f"era5_land_{mes.value.replace('-', '_')}.grib"
                )
                if _geojson is None:
                    _saida_mapa = mo.md(
                        "## Mapas climáticos\n\nO município selecionado não possui geometria cadastrada."
                    )
                elif not _arquivo_grib.is_file():
                    _saida_mapa = mo.md(
                        f"## Mapas climáticos\n\nO GRIB de {mes.value} não está disponível em `{_arquivo_grib.relative_to(Path(__file__).resolve().parents[1])}`. "
                        "O banco guarda apenas a série no centróide municipal; para mapear células internas, é necessário o GRIB original do mês."
                    )
                else:
                    _poligono = shape(json.loads(_geojson))
                    _min_lon, _min_lat, _max_lon, _max_lat = _poligono.bounds
                    _dados_grade = None
                    with xr.open_dataset(
                        _arquivo_grib,
                        engine="cfgrib",
                        chunks={"time": 1},
                        backend_kwargs={"indexpath": ""},
                    ) as _dataset:
                        _latitudes = np.asarray(_dataset.latitude.values)
                        _longitudes = np.asarray(_dataset.longitude.values)
                        _idx_lat = np.flatnonzero(
                            (_latitudes >= _min_lat) & (_latitudes <= _max_lat)
                        )
                        _idx_lon = np.flatnonzero(
                            (_longitudes >= _min_lon) & (_longitudes <= _max_lon)
                        )
                        if len(_idx_lat) and len(_idx_lon):
                            _lon_grid, _lat_grid = np.meshgrid(
                                _longitudes[_idx_lon], _latitudes[_idx_lat]
                            )
                            _mascara = np.asarray([
                                _poligono.covers(Point(float(_lon), float(_lat)))
                                for _lat, _lon in zip(
                                    _lat_grid.ravel(), _lon_grid.ravel(), strict=True
                                )
                            ]).reshape(_lat_grid.shape)
                        else:
                            _mascara = np.zeros((len(_idx_lat), len(_idx_lon)), dtype=bool)
                        if _mascara.any():
                            _lat_pontos = _lat_grid[_mascara]
                            _lon_pontos = _lon_grid[_mascara]
                            _n_pontos = len(_lat_pontos)
                            _soma_temp = np.zeros(_n_pontos)
                            _n_temp = np.zeros(_n_pontos)
                            _soma_umidade = np.zeros(_n_pontos)
                            _n_umidade = np.zeros(_n_pontos)
                            _soma_precip = np.zeros(_n_pontos)
                            _n_precip = np.zeros(_n_pontos)
                            _passos_horas = _dataset.step.values.astype(
                                "timedelta64[h]"
                            ).astype(np.int64)
                            _indice_passo_12 = int(np.flatnonzero(_passos_horas == 12)[0])
                            _dataset_area = _dataset.isel(
                                latitude=_idx_lat, longitude=_idx_lon
                            )
                            for _indice_tempo in range(_dataset.sizes["time"]):
                                _frame = _dataset_area.isel(time=_indice_tempo).compute()
                                for _indice_passo, _horas in enumerate(_passos_horas):
                                    _valid_time = pd.Timestamp(
                                        _frame["valid_time"].values[_indice_passo]
                                    )
                                    if (_valid_time.year, _valid_time.month) != tuple(
                                        map(int, mes.value.split("-"))
                                    ):
                                        continue
                                    _temp = _frame["t2m"].values[_indice_passo][_mascara] - 273.15
                                    _dew = _frame["d2m"].values[_indice_passo][_mascara] - 273.15
                                    _rh = np.clip(100 * np.exp(
                                        17.625 * _dew / (243.04 + _dew)
                                        - 17.625 * _temp / (243.04 + _temp)
                                    ), 0, 100)
                                    _ok_temp = np.isfinite(_temp)
                                    _ok_rh = np.isfinite(_rh)
                                    _soma_temp += np.where(_ok_temp, _temp, 0)
                                    _n_temp += _ok_temp
                                    _soma_umidade += np.where(_ok_rh, _rh, 0)
                                    _n_umidade += _ok_rh
                                    _precip = _frame["tp"].values[_indice_passo][_mascara]
                                    if _horas == 24:
                                        _precip = _precip - _frame["tp"].values[_indice_passo_12][_mascara]
                                    _precip = np.maximum(_precip, 0) * 1000
                                    _ok_precip = np.isfinite(_precip)
                                    _soma_precip += np.where(_ok_precip, _precip, 0)
                                    _n_precip += _ok_precip
                            _dados_grade = {
                                "temperatura": np.divide(
                                    _soma_temp, _n_temp,
                                    out=np.full(_n_pontos, np.nan), where=_n_temp > 0,
                                ),
                                "umidade": np.divide(
                                    _soma_umidade, _n_umidade,
                                    out=np.full(_n_pontos, np.nan), where=_n_umidade > 0,
                                ),
                                "precipitacao": _soma_precip,
                                "lat": _lat_pontos,
                                "lon": _lon_pontos,
                            }
                    _n_pontos_grade = (
                        len(_dados_grade["lat"]) if _dados_grade is not None else 0
                    )
                    _densidade_grade = (
                        _n_pontos_grade / _area
                        if _area is not None and _area > 0 else None
                    )
                    _densidade_grade_txt = (
                        f"{_densidade_grade:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        if _densidade_grade is not None else "indisponível"
                    )
                    _texto_densidade = (
                        f"Densidade espacial: {_n_pontos_grade} pontos internos / "
                        f"{_area:,.2f} km² = {_densidade_grade_txt} pontos/km². "
                        if _area is not None and _area > 0 else
                        f"Densidade espacial: {_n_pontos_grade} pontos internos; área municipal indisponível. "
                    )
                    if _dados_grade is None:
                        _saida_mapa = mo.md(
                            "## Mapas climáticos\n\nA grade ERA5-Land não possui centros de célula dentro do limite deste município. "
                            + _texto_densidade
                        )
                    else:
                        _partes = list(_poligono.geoms) if hasattr(_poligono, "geoms") else [_poligono]
                        _mapas_variaveis = []
                        for _coluna, (_rotulo, _unidade) in _variaveis.items():
                            _valores_ponto = _dados_grade[_coluna]
                            _validos = np.isfinite(_valores_ponto)
                            _mapa_variavel = go.Figure()
                            for _parte in _partes:
                                _borda_lon, _borda_lat = _parte.exterior.xy
                                if modo_mapa.value == "superficie":
                                    _mapa_variavel.add_trace(go.Scatter(
                                        x=list(_borda_lon), y=list(_borda_lat),
                                        mode="lines", line={"color": "#202020", "width": 1},
                                        showlegend=False, hoverinfo="skip",
                                    ))
                                else:
                                    _mapa_variavel.add_trace(go.Scattergeo(
                                        lon=list(_borda_lon), lat=list(_borda_lat),
                                        mode="lines", line={"color": "#202020", "width": 1},
                                        showlegend=False, hoverinfo="skip",
                                    ))
                            if _validos.any():
                                if modo_mapa.value == "superficie":
                                    _lon_eixo = np.linspace(_min_lon, _max_lon, 120)
                                    _lat_eixo = np.linspace(_min_lat, _max_lat, 120)
                                    _lon_interpolado, _lat_interpolado = np.meshgrid(
                                        _lon_eixo, _lat_eixo
                                    )
                                    _dentro_municipio = np.asarray([
                                        _poligono.covers(Point(float(_lon), float(_lat)))
                                        for _lat, _lon in zip(
                                            _lat_interpolado.ravel(),
                                            _lon_interpolado.ravel(), strict=True,
                                        )
                                    ])
                                    _escala_lon = np.cos(np.deg2rad(float(np.mean(_dados_grade["lat"])) ))
                                    _pontos_xy = np.column_stack([
                                        _dados_grade["lon"][_validos] * _escala_lon,
                                        _dados_grade["lat"][_validos],
                                    ])
                                    _alvos_xy = np.column_stack([
                                        _lon_interpolado.ravel() * _escala_lon,
                                        _lat_interpolado.ravel(),
                                    ])
                                    _z_superficie = np.empty(len(_alvos_xy))
                                    for _inicio_bloco in range(0, len(_alvos_xy), 256):
                                        _fim_bloco = min(_inicio_bloco + 256, len(_alvos_xy))
                                        _alvos_bloco = _alvos_xy[_inicio_bloco:_fim_bloco]
                                        _dist2 = np.sum(
                                            (_alvos_bloco[:, None, :] - _pontos_xy[None, :, :]) ** 2,
                                            axis=2,
                                        )
                                        _pesos = 1 / np.maximum(_dist2, 1e-12)
                                        _z_superficie[_inicio_bloco:_fim_bloco] = (
                                            _pesos @ _valores_ponto[_validos]
                                        ) / _pesos.sum(axis=1)
                                    _z_superficie[~_dentro_municipio] = np.nan
                                    _mapa_variavel.add_trace(go.Heatmap(
                                        x=_lon_eixo, y=_lat_eixo,
                                        z=_z_superficie.reshape(_lat_interpolado.shape),
                                        colorscale="Turbo", colorbar={"title": _unidade},
                                        hovertemplate=(
                                            f"{_rotulo}: %{{z:.2f}} {_unidade}<br>"
                                            "Lon: %{x:.3f}<br>Lat: %{y:.3f}<extra></extra>"
                                        ),
                                    ))
                                else:
                                    _mapa_variavel.add_trace(go.Scattergeo(
                                        lon=_dados_grade["lon"][_validos],
                                        lat=_dados_grade["lat"][_validos],
                                        mode="markers",
                                        marker={
                                            "size": 10,
                                            "color": _valores_ponto[_validos],
                                            "colorscale": "Turbo",
                                            "showscale": True,
                                            "colorbar": {"title": _unidade},
                                            "line": {"width": 0.3, "color": "#333"},
                                        },
                                        customdata=np.column_stack([
                                            _dados_grade["lat"][_validos],
                                            _dados_grade["lon"][_validos],
                                        ]),
                                        hovertemplate=(
                                            f"{_rotulo}: %{{marker.color:.2f}} {_unidade}<br>"
                                            "Lat: %{customdata[0]:.3f}<br>Lon: %{customdata[1]:.3f}<extra></extra>"
                                        ),
                                        showlegend=False,
                                    ))
                            _sem_dado = ~_validos
                            if _sem_dado.any() and modo_mapa.value == "pontos":
                                _mapa_variavel.add_trace(go.Scattergeo(
                                    lon=_dados_grade["lon"][_sem_dado],
                                    lat=_dados_grade["lat"][_sem_dado],
                                    mode="markers",
                                    marker={
                                        "size": 10,
                                        "color": "#777777",
                                        "symbol": "circle-open",
                                        "line": {"width": 1.5, "color": "#777777"},
                                    },
                                    hovertemplate=(
                                        f"{_rotulo}: sem dado válido<br>"
                                        "Lat: %{lat:.3f}<br>Lon: %{lon:.3f}<extra></extra>"
                                    ),
                                    showlegend=False,
                                ))
                            if modo_mapa.value == "superficie":
                                _mapa_variavel.update_xaxes(
                                    range=[_min_lon, _max_lon], title="Longitude"
                                )
                                _mapa_variavel.update_yaxes(
                                    range=[_min_lat, _max_lat], title="Latitude",
                                    scaleanchor="x", scaleratio=1,
                                )
                            else:
                                _mapa_variavel.update_geos(fitbounds="locations", visible=False)
                            _mapa_variavel.update_layout(
                                title=f"{_rotulo} — {mes.value}", height=360,
                                margin={"l": 0, "r": 0, "t": 55, "b": 0},
                            )
                            _mapas_variaveis.append(_mapa_variavel)
                        _saida_mapa = mo.vstack([
                            mo.md(
                                "## Mapa climático municipal\n\n"
                                f"Mapas do mês {mes.value} com {len(_dados_grade['lat'])} centros de célula que caem dentro do polígono municipal. "
                                f"Modo: {'superfície contínua interpolada por distância inversa' if modo_mapa.value == 'superficie' else 'pontos observados na grade'}. "
                                "Todos os centros internos são desenhados; células sem valor válido aparecem vazadas em cinza. "
                                + _texto_densidade
                                + "O valor em cada ponto é agregado no mês; temperatura e umidade são médias, precipitação é o acumulado mensal. "
                                + "A resolução espacial corresponde à grade ERA5-Land (~9 km), não a estações locais."
                            ),
                            mo.hstack(_mapas_variaveis, widths="equal"),
                        ])
            except Exception as _erro_mapa:
                _saida_mapa = mo.md(
                    f"## Mapas climáticos\n\nFalha ao montar os mapas: `{type(_erro_mapa).__name__}: {_erro_mapa}`"
                )
            _saida_distribuicao = mo.vstack([_saida_distribuicao, _saida_mapa])
    _saida_distribuicao
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
