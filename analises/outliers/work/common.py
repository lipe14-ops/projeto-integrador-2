"""Utilitários compartilhados pelos três métodos de detecção de outliers.

Este código será colado em células do notebook Colab; mantenha-o
autocontido (apenas pandas/numpy) e compatível com pandas >= 2.2.
"""
import json

import numpy as np
import pandas as pd

SEED = 42
VARIAVEIS = ["temperatura", "umidade", "precipitacao"]
UNIDADES = {"temperatura": "°C", "umidade": "%", "precipitacao": "mm/12 h"}
FREQ = "12h"

# Divisão cronológica: treino estima parâmetros, validação escolhe
# configurações, teste avalia o procedimento final.
SPLITS = {
    "treino": ("2015-01-01", "2021-12-31 23:59"),
    "validacao": ("2022-01-01", "2023-12-31 23:59"),
    "teste": ("2024-01-01", "2025-12-31 23:59"),
}


def carregar_dados(caminho):
    df = pd.read_csv(caminho)
    esperadas = {"datetime", "codigo_ibge", "municipio", "uf", *VARIAVEIS}
    faltando = esperadas - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes no CSV: {sorted(faltando)}")
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    return df.sort_values(["codigo_ibge", "datetime"]).reset_index(drop=True)


def preparar_serie(df, codigo_ibge):
    """Série regular de 12 h de um município, sem imputação.

    Lacunas viram NaN explícito (asfreq). A coluna `precip_reset` marca o
    dia 1º às 00 UTC, quando o acumulado ERA5-Land é reiniciado no
    carregamento e a precipitação não é registrada (ausência de medição,
    não zero).
    """
    sub = df[df["codigo_ibge"] == codigo_ibge]
    if sub.empty:
        raise ValueError(f"Município {codigo_ibge} não encontrado")
    if sub["datetime"].duplicated().any():
        raise ValueError("Timestamps duplicados")
    serie = sub.set_index("datetime")[VARIAVEIS].asfreq(FREQ)
    serie.attrs["codigo_ibge"] = int(codigo_ibge)
    serie.attrs["municipio"] = sub["municipio"].iloc[0]
    serie.attrs["uf"] = sub["uf"].iloc[0]
    idx = serie.index
    serie["precip_reset"] = (idx.day == 1) & (idx.hour == 0)
    return serie


def mascara_split(index, nome):
    inicio, fim = SPLITS[nome]
    return (index >= pd.Timestamp(inicio, tz="UTC")) & (
        index <= pd.Timestamp(fim, tz="UTC")
    )


def termos_sazonais(index, n_harmonicos=3):
    """Regressoras de Fourier anuais e indicador do horário (00/12 UTC)."""
    doy = index.day_of_year.to_numpy() - 1
    ang = 2 * np.pi * doy / 365.25
    cols = {"const": np.ones(len(index)), "h12": (index.hour == 12).astype(float)}
    for k in range(1, n_harmonicos + 1):
        cols[f"sin{k}"] = np.sin(k * ang)
        cols[f"cos{k}"] = np.cos(k * ang)
        # Interação horário × estação: amplitude diurna varia no ano.
        cols[f"h12_sin{k}"] = cols["h12"] * cols[f"sin{k}"]
        cols[f"h12_cos{k}"] = cols["h12"] * cols[f"cos{k}"]
    return pd.DataFrame(cols, index=index)


def ajustar_sazonalidade(y, mascara_treino, n_harmonicos=3):
    """Ciclo anual + diurno estimado por MQO só com o treino.

    Retorna (componente_sazonal, anomalia) para toda a série; nenhum dado
    de validação/teste entra na estimação.
    """
    X = termos_sazonais(y.index, n_harmonicos)
    ok = mascara_treino & y.notna().to_numpy()
    beta, *_ = np.linalg.lstsq(X[ok].to_numpy(), y[ok].to_numpy(), rcond=None)
    sazonal = pd.Series(X.to_numpy() @ beta, index=y.index, name="sazonal")
    return sazonal, (y - sazonal).rename("anomalia")


def injetar_anomalias(y, mascara, n=20, magnitude=5.0, seed=SEED, limites=None):
    """Injeta picos isolados de ±magnitude·σ_robusto em posições sorteadas.

    σ_robusto = 1,4826·MAD das diferenças em defasagem 2 (mesmo horário em
    dias consecutivos, evitando o salto diurno 00↔12 UTC) dentro da
    máscara. Preserva `y` e devolve (serie_modificada, rotulos_bool).
    `limites` (min, max) recorta valores fisicamente impossíveis.
    """
    rng = np.random.default_rng(seed)
    candidatos = np.flatnonzero(mascara & y.notna().to_numpy())
    pos = rng.choice(candidatos, size=min(n, len(candidatos)), replace=False)
    d = y[mascara].diff(2).dropna()
    sigma = 1.4826 * np.median(np.abs(d - d.median()))
    sinais = rng.choice([-1.0, 1.0], size=len(pos))
    y_mod = y.copy()
    y_mod.iloc[pos] = y.iloc[pos] + sinais * magnitude * sigma
    if limites is not None:
        y_mod = y_mod.clip(*limites)
    rotulos = pd.Series(False, index=y.index, name="injetada")
    rotulos.iloc[pos] = True
    return y_mod, rotulos


def resultado_padrao(serie, variavel, algoritmo, parametros, escore, outlier):
    """Formato longo comum a todos os métodos (uma linha por observação)."""
    return pd.DataFrame(
        {
            "datetime": serie.index,
            "codigo_ibge": serie.attrs["codigo_ibge"],
            "municipio": serie.attrs["municipio"],
            "uf": serie.attrs["uf"],
            "variavel": variavel,
            "algoritmo": algoritmo,
            "parametros": json.dumps(parametros, sort_keys=True),
            "escore": np.asarray(escore, dtype=float),
            "outlier": np.asarray(outlier, dtype=bool),
        }
    )
