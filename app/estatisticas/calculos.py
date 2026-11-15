"""Cálculos das estatísticas gerais (funções puras sobre DataFrames).

Entrada: uma linha por município × mês (visão materializada ``clima_mensal``),
com as colunas

    codigo_ibge, year, month, temperatura, umidade, precipitacao,
    regiao, uf, area_km2, enso_phase, oni

Convenções (todas explicitadas na API, em ``METODO``):

- **Temperatura e umidade mensais**: média das leituras do ERA5-Land às 00 e
  12 UTC (21 h e 9 h de Brasília) de todos os dias do mês. Não é a média de
  24 horas nem a máxima/mínima diária.
- **Precipitação mensal**: soma dos acumulados de 12 h do mês (mm).
- **Agregação espacial** (Brasil, região, UF): média **ponderada pela área**
  dos municípios (IBGE). Aproxima a média sobre o território; a média simples
  de municípios daria peso excessivo às regiões com municípios pequenos
  (Sul, Sudeste e litoral do Nordeste).
- **Agregação temporal**: primeiro a média de cada município no recorte, depois
  a média ponderada entre municípios. Precipitação é dada em mm/mês (média
  dos totais mensais), comparável entre recortes de tamanhos diferentes.
- **Estações**: meteorológicas do Hemisfério Sul (DJF, MAM, JJA, SON). O verão
  de dezembro/AAAA conta no ano AAAA+1 (``season_year``).
- **ENSO**: fase do mês pela regra de episódio do NOAA/CPC (``enso_episodes``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VARIAVEIS = ("temperatura", "umidade", "precipitacao")
UNIDADES = {"temperatura": "°C", "umidade": "%", "precipitacao": "mm/mês"}
REGIOES = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")
ESTACOES = ("verao", "outono", "inverno", "primavera")
FASES = ("el_nino", "la_nina", "neutro")
ANO_INICIO, ANO_FIM = 2015, 2025
_ESTACAO_DO_MES = {12: "verao", 1: "verao", 2: "verao", 3: "outono", 4: "outono", 5: "outono",
                   6: "inverno", 7: "inverno", 8: "inverno", 9: "primavera", 10: "primavera", 11: "primavera"}
MESES_DA_ESTACAO = {e: [m for m, s in _ESTACAO_DO_MES.items() if s == e] for e in ESTACOES}

METODO = {
    "temperatura": "Média das leituras das 00 e 12 UTC (21 h e 9 h de Brasília) do ERA5-Land, por mês e "
    "município; depois média no recorte e média ponderada pela área municipal.",
    "umidade": "Umidade relativa calculada da temperatura e do ponto de orvalho (Magnus), média das leituras "
    "das 00 e 12 UTC; mesma agregação da temperatura.",
    "precipitacao": "Soma dos acumulados de 12 h de cada mês (mm); média dos totais mensais no recorte "
    "(mm/mês) e média ponderada pela área municipal.",
    "ponderacao": "Médias do Brasil, das regiões e das UFs ponderadas pela área de cada município (IBGE), "
    "aproximando a média sobre o território.",
    "extremos_mensais": "Maior e menor valor mensal de um município no recorte (médias mensais, não leituras "
    "isoladas). Não são recordes diários.",
    "comparacao": "Diferença entre o recorte e o período completo 2015–2025 com os mesmos filtros de região, "
    "estação e fase ENSO.",
    "enso": "Anomalia = valor do mês − média do mesmo mês do calendário no município (2015–2025). Remove o "
    "ciclo sazonal antes de comparar as fases. Associação estatística, não prova de causa.",
}


@dataclass(frozen=True)
class Recorte:
    inicio: int = ANO_INICIO
    fim: int = ANO_FIM
    regiao: str | None = None
    estacao: str | None = None
    enso: str | None = None

    def validar(self) -> None:
        if not (ANO_INICIO <= self.inicio <= ANO_FIM and ANO_INICIO <= self.fim <= ANO_FIM):
            raise ValueError(f"anos devem estar entre {ANO_INICIO} e {ANO_FIM}")
        if self.inicio > self.fim:
            raise ValueError("ano inicial maior que o final")
        if self.regiao is not None and self.regiao not in REGIOES:
            raise ValueError(f"região inválida: {self.regiao}")
        if self.estacao is not None and self.estacao not in ESTACOES:
            raise ValueError(f"estação inválida: {self.estacao}")
        if self.enso is not None and self.enso not in FASES:
            raise ValueError(f"fase ENSO inválida: {self.enso}")

    @property
    def periodo_completo(self) -> bool:
        return self.inicio == ANO_INICIO and self.fim == ANO_FIM


REGIAO_DA_UF = {
    **dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}


def preparar(mensal: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta estação e ano da estação; completa a região pela UF (municípios novos sem
    cadastro de região) e descarta linhas sem dado climático (áreas de lagoa, ilhas sem grade)."""
    df = mensal.copy()
    df["regiao"] = df["regiao"].fillna(df["uf"].map(REGIAO_DA_UF))
    tem_dado = df[list(VARIAVEIS)].notna().any(axis=1)
    df = df[df["regiao"].isin(REGIOES) & tem_dado].copy()
    df["estacao"] = df["month"].map(_ESTACAO_DO_MES)
    df["season_year"] = df["year"] + (df["month"] == 12).astype(int)
    df["area_km2"] = df["area_km2"].astype(float)
    return df.reset_index(drop=True)


def aplicar(df: pd.DataFrame, r: Recorte, *, anos=True, regiao=True, estacao=True, enso=True) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if anos:
        mask &= df["year"].between(r.inicio, r.fim)
    if regiao and r.regiao:
        mask &= df["regiao"] == r.regiao
    if estacao and r.estacao:
        mask &= df["estacao"] == r.estacao
    if enso and r.enso:
        mask &= df["enso_phase"] == r.enso
    return df[mask]


def media_ponderada(valores: pd.Series, pesos: pd.Series) -> float | None:
    ok = valores.notna() & pesos.notna() & (pesos > 0)
    if not ok.any():
        return None
    return float(np.average(valores[ok], weights=pesos[ok]))


def medias_municipais(df: pd.DataFrame) -> pd.DataFrame:
    """Média de cada variável por município no recorte (+ área, região, UF e nº de meses)."""
    if df.empty:
        return pd.DataFrame(columns=["codigo_ibge", *VARIAVEIS, "area_km2", "regiao", "uf", "meses"])
    g = df.groupby("codigo_ibge")
    out = g[list(VARIAVEIS)].mean()
    out["meses"] = g["temperatura"].count()
    out[["area_km2", "regiao", "uf"]] = g[["area_km2", "regiao", "uf"]].first()
    return out.reset_index()


def agregar_espacial(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Média ponderada pela área entre municípios, por grupo de ``chaves`` (linhas mês × município)."""
    cols = list(VARIAVEIS)
    tmp = df[chaves + cols + ["area_km2"]].copy()
    for c in cols:
        valido = tmp[c].notna()
        tmp[f"_w_{c}"] = tmp["area_km2"].where(valido, 0.0)
        tmp[f"_wx_{c}"] = (tmp[c] * tmp["area_km2"]).where(valido, 0.0)
    g = tmp.groupby(chaves)
    soma = g[[f"_w_{c}" for c in cols] + [f"_wx_{c}" for c in cols]].sum()
    out = pd.DataFrame(index=soma.index)
    for c in cols:
        out[c] = (soma[f"_wx_{c}"] / soma[f"_w_{c}"].where(soma[f"_w_{c}"] > 0)).astype(float)
    out["municipios"] = g["temperatura"].count()
    return out.reset_index()


def _num(v, casas=3):
    if v is None or (isinstance(v, float) and not np.isfinite(v)) or pd.isna(v):
        return None
    return round(float(v), casas)


# ---------------------------------------------------------------- resumo
def resumo(df: pd.DataFrame, r: Recorte, nomes: dict[int, tuple[str, str]], total_cadastrados: int) -> dict:
    sub = aplicar(df, r)
    mun = medias_municipais(sub)
    sub_ref = aplicar(df, Recorte(ANO_INICIO, ANO_FIM, r.regiao, r.estacao, r.enso))
    base = medias_municipais(sub_ref)
    meses_ref = int(sub_ref[["year", "month"]].drop_duplicates().shape[0])
    meses = int(sub[["year", "month"]].drop_duplicates().shape[0])
    # se o recorte já contém todos os meses da referência, a comparação é vazia (diferença nula por construção)
    comparavel = not r.periodo_completo and meses < meses_ref
    indicadores = {}
    for v in VARIAVEIS:
        valor = media_ponderada(mun[v], mun["area_km2"]) if not mun.empty else None
        ref = media_ponderada(base[v], base["area_km2"]) if not base.empty else None
        indicadores[v] = {
            "valor": _num(valor, 2),
            "unidade": UNIDADES[v],
            "metodo": METODO[v],
            "media_simples_municipios": _num(mun[v].mean(), 2) if not mun.empty else None,
            "referencia_2015_2025": _num(ref, 2) if comparavel else None,
            "diferenca": None if (not comparavel or valor is None or ref is None) else _num(valor - ref, 2),
        }
    sem_filtro_tempo = r.estacao is None and r.enso is None
    if indicadores["precipitacao"]["valor"] is not None and sem_filtro_tempo:
        indicadores["precipitacao"]["anual_equivalente"] = _num(indicadores["precipitacao"]["valor"] * 12, 0)

    def extremo(col: str, maior: bool):
        s = sub.dropna(subset=[col])
        if s.empty:
            return None
        linha = s.loc[s[col].idxmax() if maior else s[col].idxmin()]
        nome, uf = nomes.get(int(linha.codigo_ibge), (str(int(linha.codigo_ibge)), ""))
        return {"valor": _num(linha[col], 2), "unidade": "mm" if col == "precipitacao" else UNIDADES[col],
                "codigo_ibge": int(linha.codigo_ibge), "municipio": nome, "uf": uf,
                "ano": int(linha.year), "mes": int(linha.month)}

    return {
        "recorte": r.__dict__,
        "meses": meses,
        "meses_referencia": meses_ref,
        "municipios_com_dados": int(mun["temperatura"].notna().sum()) if not mun.empty else 0,
        "municipios_cadastrados": total_cadastrados,
        "indicadores": indicadores,
        "extremos_mensais": {
            "temperatura_max": extremo("temperatura", True),
            "temperatura_min": extremo("temperatura", False),
            "precipitacao_max": extremo("precipitacao", True),
            "umidade_min": extremo("umidade", False),
            "metodo": METODO["extremos_mensais"],
        },
        "metodo": {"ponderacao": METODO["ponderacao"], "comparacao": METODO["comparacao"]},
    }


# ---------------------------------------------------------------- séries
def serie(df: pd.DataFrame, r: Recorte, enso_mensal: pd.DataFrame) -> dict:
    """Série mensal (todas as fases/estações), anual e ciclo mensal médio, no recorte."""
    base = aplicar(df, r, estacao=False, enso=False)
    mensal = agregar_espacial(base, ["year", "month"]).merge(
        enso_mensal[["year", "month", "oni", "enso_phase"]], on=["year", "month"], how="left")
    filtrado = aplicar(df, r)
    mensal_f = agregar_espacial(filtrado, ["year", "month"]) if not filtrado.empty else pd.DataFrame()
    anual = []
    meses_esperados = 3 if r.estacao else 12
    if not mensal_f.empty:
        for ano, g in mensal_f.groupby("year"):
            completo = r.enso is None and len(g) == meses_esperados
            anual.append({
                "ano": int(ano), "meses": int(len(g)),
                "temperatura": _num(g["temperatura"].mean()), "umidade": _num(g["umidade"].mean()),
                "precipitacao_mensal": _num(g["precipitacao"].mean()),
                # total do ano (ou da estação no ano) só com todos os meses do recorte
                "precipitacao_total": _num(g["precipitacao"].sum(), 1) if completo else None,
            })
    ciclo = agregar_espacial(aplicar(df, r, estacao=False), ["month"]) if not base.empty else pd.DataFrame()
    return {
        "recorte": r.__dict__,
        "mensal": [
            {"ano": int(x.year), "mes": int(x.month), "temperatura": _num(x.temperatura), "umidade": _num(x.umidade),
             "precipitacao": _num(x.precipitacao), "oni": _num(x.oni, 2),
             "fase": None if pd.isna(x.enso_phase) else x.enso_phase,
             "estacao": _ESTACAO_DO_MES[int(x.month)]}
            for x in mensal.itertuples()
        ],
        "anual": anual,
        "ciclo_mensal": [
            {"mes": int(x.month), "temperatura": _num(x.temperatura), "umidade": _num(x.umidade),
             "precipitacao": _num(x.precipitacao)}
            for x in (ciclo.itertuples() if not ciclo.empty else [])
        ],
        "nota_total_anual": "Total anual de chuva só para anos com todos os meses do recorte e sem filtro ENSO; "
        "com filtro de estação, é o total da estação no ano.",
    }


def sazonal(df: pd.DataFrame, r: Recorte) -> dict:
    """Valores por estação e ano (só estações com os 3 meses no período), e resumo por estação."""
    sub = df[df["season_year"].between(r.inicio, r.fim)]
    sub = aplicar(sub, r, anos=False, estacao=False)
    if sub.empty:
        return {"recorte": r.__dict__, "por_ano": [], "resumo": []}
    m = agregar_espacial(sub, ["season_year", "estacao", "year", "month"])
    linhas = []
    for (ano, est), g in m.groupby(["season_year", "estacao"]):
        if len(g) != 3:  # verão de 2015 (sem dez/2014) e o de 2026 ficam de fora
            continue
        linhas.append({"ano": int(ano), "estacao": est, "temperatura": _num(g["temperatura"].mean()),
                       "umidade": _num(g["umidade"].mean()), "precipitacao_total": _num(g["precipitacao"].sum(), 1)})
    tab = pd.DataFrame(linhas)
    resumo_est = []
    for est in ESTACOES:
        g = tab[tab["estacao"] == est] if not tab.empty else tab
        if g.empty:
            continue
        item = {"estacao": est, "anos": int(len(g))}
        for c in ("temperatura", "umidade", "precipitacao_total"):
            item[c] = {"media": _num(g[c].mean()), "min": _num(g[c].min()), "max": _num(g[c].max()),
                       "ano_min": int(g.loc[g[c].idxmin(), "ano"]), "ano_max": int(g.loc[g[c].idxmax(), "ano"])}
        resumo_est.append(item)
    return {"recorte": r.__dict__, "por_ano": linhas, "resumo": resumo_est,
            "nota": "Estações meteorológicas (DJF, MAM, JJA, SON); o verão leva o ano de janeiro. Só estações "
            "com os três meses no período. Chuva: total da estação (mm)."}


def regioes(df: pd.DataFrame, r: Recorte) -> dict:
    sub = aplicar(df, r, regiao=False)
    mun = medias_municipais(sub)
    linhas = []
    for reg in REGIOES:
        g = mun[mun["regiao"] == reg]
        linhas.append({"regiao": reg, "municipios": int(g["temperatura"].notna().sum()),
                       "area_km2": _num(g["area_km2"].sum(), 0),
                       **{v: _num(media_ponderada(g[v], g["area_km2"]), 2) if not g.empty else None for v in VARIAVEIS}})
    ciclo = agregar_espacial(aplicar(df, r, regiao=False, estacao=False), ["regiao", "month"])
    return {
        "recorte": r.__dict__,
        "regioes": linhas,
        "brasil": {v: _num(media_ponderada(mun[v], mun["area_km2"]), 2) if not mun.empty else None for v in VARIAVEIS},
        "ciclo_mensal": [
            {"regiao": x.regiao, "mes": int(x.month), "temperatura": _num(x.temperatura), "umidade": _num(x.umidade),
             "precipitacao": _num(x.precipitacao)}
            for x in ciclo.itertuples()
        ],
    }


def anomalias_climatologicas(df: pd.DataFrame) -> pd.DataFrame:
    """Anomalia de cada município × mês em relação à média do mesmo mês do calendário (2015–2025)."""
    clim = df.groupby(["codigo_ibge", "month"])[list(VARIAVEIS)].transform("mean")
    out = df.copy()
    for v in VARIAVEIS:
        out[f"anom_{v}"] = df[v] - clim[v]
        out[f"clim_{v}"] = clim[v]
    return out


def enso(anom: pd.DataFrame, r: Recorte) -> dict:
    """Anomalia média por fase ENSO × estação, para o Brasil e as regiões (sem filtro de fase)."""
    sub = aplicar(anom, r, regiao=False, enso=False)
    linhas = []
    for escopo in ("Brasil", *REGIOES):
        g0 = sub if escopo == "Brasil" else sub[sub["regiao"] == escopo]
        for est in (None, *ESTACOES):
            g1 = g0 if est is None else g0[g0["estacao"] == est]
            for fase in FASES:
                g = g1[g1["enso_phase"] == fase]
                item = {"escopo": escopo, "estacao": est or "todas", "fase": fase,
                        "meses": int(g[["year", "month"]].drop_duplicates().shape[0])}
                for v in VARIAVEIS:
                    a = media_ponderada(g[f"anom_{v}"], g["area_km2"]) if not g.empty else None
                    item[v] = _num(a)
                    if v == "precipitacao":
                        c = media_ponderada(g[f"clim_{v}"], g["area_km2"]) if not g.empty else None
                        item["precipitacao_pct"] = _num(100 * a / c, 1) if (a is not None and c) else None
                linhas.append(item)
    meses_fase = (sub[["year", "month", "enso_phase"]].drop_duplicates()["enso_phase"].value_counts().to_dict()
                  if not sub.empty else {})
    return {"recorte": {**r.__dict__, "enso": None}, "linhas": linhas,
            "meses_por_fase": {f: int(meses_fase.get(f, 0)) for f in FASES},
            "metodo": METODO["enso"]}


def quebras_quantis(valores: pd.Series, classes: int = 7) -> list[float]:
    v = valores.dropna()
    if v.nunique() < 2:
        return []
    q = np.quantile(v, np.linspace(0, 1, classes + 1)[1:-1])
    amplitude = float(v.max() - v.min())
    casas = 0 if amplitude >= 50 else 1 if amplitude >= 5 else 2
    return sorted({round(float(x), casas) for x in q})


def mapa(df: pd.DataFrame, r: Recorte, variavel: str) -> dict:
    if variavel not in VARIAVEIS:
        raise ValueError(f"variável inválida: {variavel}")
    mun = medias_municipais(aplicar(df, r, regiao=False))
    valores = mun[["codigo_ibge", variavel, "meses"]].rename(columns={variavel: "valor"})
    return {
        "variavel": variavel, "unidade": UNIDADES[variavel], "metodo": METODO[variavel],
        "recorte": {**r.__dict__, "regiao": None},
        "quebras": quebras_quantis(valores["valor"]),
        "resumo": {"com_valor": int(valores["valor"].notna().sum()),
                   "mediana": _num(valores["valor"].median(), 2),
                   "min": _num(valores["valor"].min(), 2), "max": _num(valores["valor"].max(), 2)},
        "valores": [{"codigo_ibge": int(x.codigo_ibge), "valor": _num(x.valor, 2), "meses": int(x.meses)}
                    for x in valores.itertuples()],
    }


def por_uf(df: pd.DataFrame) -> list[dict]:
    mun = medias_municipais(df)
    out = []
    for uf, g in mun.groupby("uf"):
        out.append({"uf": uf, "regiao": g["regiao"].iloc[0], "municipios": int(g["temperatura"].notna().sum()),
                    **{v: _num(media_ponderada(g[v], g["area_km2"]), 2) for v in VARIAVEIS}})
    return out
