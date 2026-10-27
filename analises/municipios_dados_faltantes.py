import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import geopandas as gpd
    from pathlib import Path

    return Path, gpd, mo, pd


@app.cell
def _(mo):
    mo.md(r"""
    # Dados faltantes nos municípios

    Esta análise usa `data/municipios.parquet`, a base de municípios do
    projeto. Valores ausentes incluem nulos e, em campos textuais, strings
    vazias ou compostas apenas por espaços. Geometrias nulas ou vazias
    também são contabilizadas como faltantes.

    A base contém atributos descritivos, coordenadas e geometria. Use o
    seletor para comparar o Brasil inteiro com uma UF específica.
    """)
    return


@app.cell
def _(Path, gpd, mo):
    _caminho_base = Path(__file__).resolve().parents[1] / "data" / "municipios.parquet"
    if not _caminho_base.exists():
        raise FileNotFoundError(f"Base não encontrada: {_caminho_base}")

    municipios = gpd.read_parquet(_caminho_base)

    _ufs = sorted(municipios["uf"].dropna().astype(str).unique()) if "uf" in municipios else []
    seletor_uf = mo.ui.dropdown(
        options=["Brasil", *_ufs], value="Brasil", label="Unidade da Federação"
    )
    mo.vstack([mo.md(f"**Arquivo:** `{_caminho_base.relative_to(Path(__file__).resolve().parents[1])}` · **Linhas:** {municipios.shape[0]:,} · **Colunas:** {municipios.shape[1]}"), seletor_uf])
    return municipios, seletor_uf


@app.cell
def _(pd):
    _campos = [
        "codigo_ibge", "municipio", "uf", "estado", "regiao", "mesorregiao",
        "microrregiao", "populacao", "ano_populacao", "bioma", "geomorfologia",
        "regiao_geomorfologica", "dominio_geomorfologico", "area_km2", "latitude",
        "longitude", "geometry",
    ]
    _descricoes = {
        "codigo_ibge": "Código IBGE", "municipio": "Município", "uf": "UF",
        "estado": "Estado", "regiao": "Região", "mesorregiao": "Mesorregião",
        "microrregiao": "Microrregião", "populacao": "População",
        "ano_populacao": "Ano da população", "bioma": "Bioma",
        "geomorfologia": "Geomorfologia", "regiao_geomorfologica": "Região geomorfológica",
        "dominio_geomorfologico": "Domínio geomorfológico", "area_km2": "Área (km²)",
        "latitude": "Latitude", "longitude": "Longitude", "geometry": "Geometria",
    }

    def resumir_faltantes(_dados):
        _colunas = [ _coluna for _coluna in _campos if _coluna in _dados.columns ]
        _linhas = []
        for _coluna in _colunas:
            _serie = _dados[_coluna]
            _faltantes = int(_serie.isna().sum())
            if _coluna == "geometry":
                _faltantes += int(_serie.map(lambda _valor: bool(getattr(_valor, "is_empty", False))).sum())
            elif pd.api.types.is_string_dtype(_serie.dtype) or _serie.dtype == object:
                _faltantes += int(_serie.map(lambda _valor: isinstance(_valor, str) and not _valor.strip()).sum())
            _total = len(_dados)
            _linhas.append({
                "Campo": _descricoes.get(_coluna, _coluna),
                "Coluna": _coluna,
                "Faltantes": _faltantes,
                "Presentes": _total - _faltantes,
                "% faltantes": round(100 * _faltantes / _total, 2) if _total else 0.0,
            })
        return pd.DataFrame(_linhas).sort_values(
            ["Faltantes", "Coluna"], ascending=[False, True]
        ).reset_index(drop=True)

    return (resumir_faltantes,)


@app.cell
def _(mo, municipios, resumir_faltantes, seletor_uf):
    dados_filtrados = (
        municipios
        if seletor_uf.value == "Brasil" or "uf" not in municipios.columns
        else municipios[municipios["uf"].astype(str) == seletor_uf.value]
    )
    _resumo = resumir_faltantes(dados_filtrados)
    _total = len(dados_filtrados)
    _campos_com_faltas = int((_resumo["Faltantes"] > 0).sum())
    _faltas_totais = int(_resumo["Faltantes"].sum())
    _metricas = mo.hstack([
        mo.stat(label="Municípios analisados", value=f"{_total:,}"),
        mo.stat(label="Campos com faltantes", value=f"{_campos_com_faltas} / {len(_resumo)}"),
        mo.stat(label="Valores faltantes", value=f"{_faltas_totais:,}"),
    ])
    _colunas_disponiveis = _resumo["Coluna"].tolist()
    seletor_campos = mo.ui.multiselect(
        options=_colunas_disponiveis,
        value=_colunas_disponiveis,
        label="Filtrar registros por campos faltantes",
    )
    mo.vstack([
        _metricas,
        mo.md("## Faltantes por campo"),
        mo.ui.table(_resumo, page_size=20),
        mo.md("## Registros com dados faltantes"),
        mo.md(
            "Uma linha aparece quando falta ao menos um dos campos selecionados. "
            "A coluna `campos_faltantes` indica quais valores estão ausentes."
        ),
        seletor_campos,
    ])
    return dados_filtrados, seletor_campos


@app.cell
def _(dados_filtrados, mo, pd, seletor_campos):
    _limite = 500

    def _eh_faltante(_valor, _coluna):
        if pd.isna(_valor):
            return True
        if _coluna == "geometry":
            return bool(getattr(_valor, "is_empty", False))
        return isinstance(_valor, str) and not _valor.strip()

    _mascara_registros = pd.Series(False, index=dados_filtrados.index)
    for _coluna in seletor_campos.value:
        _mascara_registros = _mascara_registros | dados_filtrados[_coluna].map(
            lambda _valor: _eh_faltante(_valor, _coluna)
        )

    _registros_faltantes = dados_filtrados.loc[_mascara_registros].copy()
    _registros_faltantes["campos_faltantes"] = [
        ", ".join(
            _coluna
            for _coluna in seletor_campos.value
            if _eh_faltante(_linha[_coluna], _coluna)
        )
        for _, _linha in _registros_faltantes.iterrows()
    ]
    _registros_faltantes = _registros_faltantes.drop(columns=["geometry"], errors="ignore")
    _total_registros_faltantes = len(_registros_faltantes)
    _registros_exibidos = _registros_faltantes.head(_limite).reset_index(drop=True)
    _texto_registros = (
        f"Exibindo {_len:,} de {_total_registros_faltantes:,} registros encontrados. "
        "A coluna `campos_faltantes` informa quais dados estão ausentes. Geometria foi omitida da tabela."
        if (_len := len(_registros_exibidos))
        else "Nenhum registro faltante encontrado para os campos selecionados."
    )

    mo.vstack([mo.md(_texto_registros), mo.ui.table(_registros_exibidos, page_size=50)])
    return


if __name__ == "__main__":
    app.run()
