"""Método 2: Isolation Forest multivariado (temperatura, umidade, precipitação).

Decisões metodológicas (resumo; detalhes nos comentários de cada função):

* Sazonalidade: em vez de alimentar a floresta com sen/cos do dia do ano,
  usamos ANOMALIAS sazonais de temperatura e umidade estimadas só no treino
  (`ajustar_sazonalidade`, ciclo anual + diurno + interação). Motivo: as
  divisões do Isolation Forest são paralelas aos eixos; para isolar "28 °C
  é quente para julho, mas normal para janeiro" com sen/cos como atributos
  a árvore precisaria de várias divisões combinadas, e sen/cos têm
  distribuição quase uniforme (não ajudam a isolar nada sozinhos). Com a
  anomalia, um valor atípico para a época/horário vira um valor extremo num
  único eixo, que é exatamente o que o IF isola bem.
* Precipitação: log1p(mm) sem dessazonalizar. A distribuição é assimétrica
  com ~12 % de zeros exatos; log1p mantém o zero em zero, comprime a cauda e
  evita que poucos eventos de chuva extrema dominem as divisões. Não se
  subtrai ciclo sazonal porque a média sazonal de uma variável inflada de
  zeros produziria "anomalias negativas" artificiais em todos os dias secos.
* Configuração A ("estatica"): [anom_temperatura, anom_umidade, log1p_precip].
  Configuração B ("temporal"): A + diferenças em defasagem 2 (mesmo horário
  do dia anterior, evitando o salto diurno 00↔12 UTC) das três variáveis.
  As diferenças usam só o passado, logo não há vazamento do futuro.
  A e B diferem nas ENTRADAS; o algoritmo e os hiperparâmetros são iguais.
* NaN: a precipitação é ausente no dia 1º às 00 UTC (reinício do acumulado).
  Não imputamos zero nem preenchemos: linhas com qualquer atributo NaN
  ficam fora do ajuste e recebem escore NaN e outlier=False ("não
  classificado"). Em B, a observação 24 h depois de um reinício também fica
  sem diferença de precipitação e, portanto, não classificada.
* Escala: RobustScaler (mediana/IQR) ajustado só no treino. O IF é
  praticamente invariante a transformações monótonas por atributo (cada
  divisão escolhe um limiar uniforme entre o mínimo e o máximo do atributo
  no subamostra), então a escala NÃO muda o escore; ela serve para (i)
  tornar comparáveis os desvios usados na heurística de "variável
  dominante" e (ii) manter o pipeline idêntico a métodos sensíveis à escala.
  Robusto em vez de padrão porque média/desvio do treino são distorcidos
  justamente pelos outliers que queremos detectar.
* Escore: `score_samples` devolve valores mais negativos para pontos mais
  anômalos; usamos escore = -score_samples (maior = mais anômalo).
* Limiar: `contamination` é hipótese, não verdade. O limiar é o quantil
  (1 - c) do escore NO TREINO; a taxa de alertas em validação/teste é então
  um resultado fora da amostra, não imposta.
"""
import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from common import *  # noqa: F401,F403  (no notebook, common já está definido)

CONTAMINACOES = [0.01, 0.03, 0.05]
IF_PARAMS = {"n_estimators": 300, "max_samples": 256, "max_features": 1.0}
CONFIGS = ("estatica", "temporal")


# ---------------------------------------------------------------------------
# Atributos
# ---------------------------------------------------------------------------
def construir_atributos(serie, mascara_treino, config="estatica"):
    """Matriz de atributos do IF para uma série de 12 h de um município.

    Componentes sazonais estimados só com o treino; diferenças só com o
    passado. Retorna DataFrame (index = datetime) possivelmente com NaN.
    """
    X = pd.DataFrame(index=serie.index)
    for v in ("temperatura", "umidade"):
        _, anom = ajustar_sazonalidade(serie[v], mascara_treino)
        X[f"anom_{v}"] = anom
    # Reinício do acumulado: ausência de medição, mantém NaN (não zero).
    prec = serie["precipitacao"].where(~serie["precip_reset"])
    X["log1p_precipitacao"] = np.log1p(prec.clip(lower=0))
    if config == "temporal":
        base = list(X.columns)
        for c in base:
            # diff(2) = valor atual − mesmo horário 24 h antes (só passado).
            X[f"d24h_{c}"] = X[c].diff(2)
    elif config != "estatica":
        raise ValueError(f"config desconhecida: {config}")
    return X


# ---------------------------------------------------------------------------
# Ajuste e escore
# ---------------------------------------------------------------------------
def ajustar_iforest(X, mascara_treino, seed=SEED):
    """Ajusta RobustScaler + IsolationForest só nas linhas completas do treino."""
    ok_treino = mascara_treino & X.notna().all(axis=1).to_numpy()
    scaler = RobustScaler().fit(X[ok_treino].to_numpy())
    # `contamination` do sklearn não é usado: o limiar é definido por nós.
    modelo = IsolationForest(random_state=seed, n_jobs=-1, **IF_PARAMS)
    modelo.fit(scaler.transform(X[ok_treino].to_numpy()))
    return scaler, modelo


def pontuar(X, scaler, modelo):
    """Escore positivo (maior = mais anômalo) e z robusto por atributo.

    Linhas com NaN ficam com escore NaN (não classificadas).
    """
    ok = X.notna().all(axis=1).to_numpy()
    escore = np.full(len(X), np.nan)
    Z = np.full(X.shape, np.nan)
    if ok.any():
        Xs = scaler.transform(X[ok].to_numpy())
        escore[ok] = -modelo.score_samples(Xs)
        # (x − mediana)/IQR · 1,349 ≈ z de uma normal (IQR = 1,349 σ).
        Z[ok] = Xs * 1.349
    return pd.Series(escore, index=X.index, name="escore"), pd.DataFrame(
        Z, index=X.index, columns=X.columns
    )


def limiares_treino(escore, mascara_treino, contaminacoes=CONTAMINACOES):
    """Limiar = quantil (1 − c) do escore no treino, para cada c."""
    s = escore[mascara_treino].dropna()
    return {c: float(np.quantile(s, 1 - c)) for c in contaminacoes}


def variavel_dominante(Z):
    """Heurística interpretativa: atributo com maior |z robusto|.

    NÃO é uma atribuição causal do IF (o escore depende de todas as árvores
    e interações); apenas indica qual atributo está mais longe do centro.
    """
    absZ = Z.abs()
    ok = absZ.notna().all(axis=1)
    dom = pd.Series(pd.NA, index=Z.index, dtype="object")
    dom[ok] = absZ[ok].idxmax(axis=1)
    zmax = pd.Series(np.nan, index=Z.index)
    zmax[ok] = absZ[ok].max(axis=1)
    return dom, zmax


# ---------------------------------------------------------------------------
# Pipeline por município
# ---------------------------------------------------------------------------
def rodar_municipio(serie, configs=CONFIGS, contaminacoes=CONTAMINACOES):
    """Ajusta A e B para um município; devolve resultados e artefatos."""
    m_treino = mascara_split(serie.index, "treino")
    saidas, modelos, alertas = [], {}, []
    for cfg in configs:
        X = construir_atributos(serie, m_treino, cfg)
        scaler, modelo = ajustar_iforest(X, m_treino)
        escore, Z = pontuar(X, scaler, modelo)
        lim = limiares_treino(escore, m_treino, contaminacoes)
        dom, zmax = variavel_dominante(Z)
        modelos[cfg] = (scaler, modelo, lim)
        for c, t in lim.items():
            flag = (escore > t).fillna(False).to_numpy()
            params = {"config": cfg, "contamination": c, "limiar": round(t, 6),
                      "atributos": list(X.columns), "seed": SEED, **IF_PARAMS}
            saidas.append(resultado_padrao(serie, "multivariada",
                                           "IsolationForest", params, escore, flag))
            det = serie.loc[flag, VARIAVEIS].copy()
            det["escore"] = escore[flag]
            det["var_dominante"] = dom[flag]
            det["z_dominante"] = zmax[flag]
            det["config"], det["contamination"] = cfg, c
            alertas.append(det)
    return pd.concat(saidas, ignore_index=True), modelos, pd.concat(alertas)


def taxas_por_split(res):
    """Taxa de alertas por split entre observações classificadas (escore não NaN)."""
    p = res["parametros"].map(json.loads)
    res = res.assign(config=p.map(lambda d: d["config"]),
                     contamination=p.map(lambda d: d["contamination"]),
                     classificada=res["escore"].notna())
    idx = pd.DatetimeIndex(res["datetime"])
    linhas = []
    for nome in SPLITS:
        t = (res[mascara_split(idx, nome)]
             .groupby(["municipio", "config", "contamination"])
             .agg(n_obs=("outlier", "size"), n_classificadas=("classificada", "sum"),
                  n_alertas=("outlier", "sum"))
             .reset_index())
        t["n_nao_classificadas"] = t["n_obs"] - t["n_classificadas"]
        t["taxa_alertas"] = t["n_alertas"] / t["n_classificadas"]
        t["split"] = nome
        linhas.append(t)
    return pd.concat(linhas, ignore_index=True)


def sobreposicao_ab(res):
    """Jaccard e interseção entre alertas de A e B (mesmo município e c)."""
    p = res["parametros"].map(json.loads)
    res = res.assign(config=p.map(lambda d: d["config"]),
                     contamination=p.map(lambda d: d["contamination"]))
    linhas = []
    for (mun, c), d in res[res["outlier"]].groupby(["municipio", "contamination"]):
        a = set(d.loc[d["config"] == "estatica", "datetime"])
        b = set(d.loc[d["config"] == "temporal", "datetime"])
        uniao = a | b
        linhas.append({"municipio": mun, "contamination": c, "n_A": len(a),
                       "n_B": len(b), "n_A_e_B": len(a & b),
                       "jaccard": len(a & b) / len(uniao) if uniao else np.nan})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Experimento sintético
# ---------------------------------------------------------------------------
def injetar_multivariada(serie, mascara, n=20, seed=SEED):
    """Anomalia só conjunta: tarde (12 UTC) quente com umidade alta.

    Sorteia observações das 12 UTC no período `mascara` cuja anomalia de
    temperatura está acima do percentil 75 do treino (tarde quente) e troca
    a umidade pelo percentil 95 da umidade do TREINO no mesmo mês e horário.
    Cada valor isolado é plausível para a época (temperatura não é alterada;
    a umidade é um valor observado com frequência de 5 % no mês), mas a
    combinação quente + muito úmido contraria a correlação negativa T × UR.
    Devolve (serie_modificada, rotulos_bool).
    """
    rng = np.random.default_rng(seed)
    m_treino = mascara_split(serie.index, "treino")
    _, anom_t = ajustar_sazonalidade(serie["temperatura"], m_treino)
    p75 = anom_t[m_treino].quantile(0.75)
    idx = serie.index
    cand = np.flatnonzero(mascara & (idx.hour == 12) & (anom_t > p75).to_numpy()
                          & serie["umidade"].notna().to_numpy())
    pos = rng.choice(cand, size=min(n, len(cand)), replace=False)
    treino = serie.loc[m_treino & (idx.hour == 12), "umidade"]
    p95_mes = treino.groupby(treino.index.month).quantile(0.95)
    s = serie.copy()
    alvo = idx[pos]
    s.loc[alvo, "umidade"] = np.maximum(
        p95_mes.reindex(alvo.month).to_numpy(), serie.loc[alvo, "umidade"].to_numpy())
    rot = pd.Series(False, index=idx, name="injetada")
    rot.iloc[pos] = True
    return s, rot


def _z_marginal(serie, variavel, rotulos):
    """|z| robusto univariado da anomalia sazonal nos pontos injetados."""
    m_treino = mascara_split(serie.index, "treino")
    _, a = ajustar_sazonalidade(serie[variavel], m_treino)
    med = a[m_treino].median()
    mad = 1.4826 * (a[m_treino] - med).abs().median()
    return ((a[rotulos] - med) / mad).abs()


def experimento_sintetico(serie, modelos, n=20, magnitude=5.0, n_rep=5):
    """Recall/precisão nos pontos injetados no TESTE, com modelos já ajustados.

    Os modelos (scaler, IF, limiares) do treino NÃO são reajustados: a
    injeção ocorre só no teste e a sazonalidade é estimada só no treino,
    então os atributos de treino não mudam.
    * recall = injetados sinalizados / injetados classificados;
    * precisao_ingenua = injetados sinalizados / todos os alertas no teste
      (penaliza outliers reais, logo é limite inferior);
    * precisao_incremental = injetados sinalizados / (injetados sinalizados +
      alertas NOVOS em pontos não injetados vs. a série limpa) — mede só os
      falsos alarmes causados pela injeção (ex.: diferença 24 h depois).
    """
    m_teste = mascara_split(serie.index, "teste")
    m_treino = mascara_split(serie.index, "treino")
    linhas, zmarg = [], []
    for rep in range(n_rep):
        sd = SEED + rep
        cenarios = {}
        for v, lim in (("temperatura", None), ("umidade", (0, 100))):
            ymod, rot = injetar_anomalias(serie[v], m_teste, n=n, magnitude=magnitude,
                                          seed=sd, limites=lim)
            s = serie.copy()
            s[v] = ymod
            cenarios[v] = (s, rot)
        s, rot = injetar_multivariada(serie, m_teste, n=n, seed=sd)
        cenarios["multivariada_T_UR"] = (s, rot)
        zm = _z_marginal(s, "umidade", rot)
        zmarg.append(zm)
        for cfg, (scaler, modelo, lims) in modelos.items():
            esc_limpo, _ = pontuar(construir_atributos(serie, m_treino, cfg), scaler, modelo)
            for cen, (s, rot) in cenarios.items():
                esc, _ = pontuar(construir_atributos(s, m_treino, cfg), scaler, modelo)
                for c, t in lims.items():
                    f = (esc > t) & m_teste
                    f0 = (esc_limpo > t) & m_teste
                    inj = rot & esc.notna()
                    tp = int((f & inj).sum())
                    novos_fp = int((f & ~rot & ~f0).sum())
                    linhas.append({
                        "municipio": serie.attrs["municipio"], "config": cfg,
                        "cenario": cen, "contamination": c, "rep": rep,
                        "n_injetados": int(inj.sum()), "tp": tp,
                        "recall": tp / max(int(inj.sum()), 1),
                        "precisao_ingenua": tp / max(int(f.sum()), 1),
                        "precisao_incremental": tp / max(tp + novos_fp, 1),
                    })
    return pd.DataFrame(linhas), pd.concat(zmarg)


# ---------------------------------------------------------------------------
# Execução completa
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    BASE = os.path.dirname(os.path.abspath(__file__))
    df = carregar_dados(os.path.join(BASE, "..", "clima_4_municipios.csv"))
    resultados, alertas, sinteticos, tempos, zmarg = [], [], [], [], {}
    for cod in sorted(df["codigo_ibge"].unique()):
        t0 = time.perf_counter()
        serie = preparar_serie(df, cod)
        res, modelos, al = rodar_municipio(serie)
        t_ajuste = time.perf_counter() - t0
        sint, zm = experimento_sintetico(serie, modelos)
        t_total = time.perf_counter() - t0
        mun = serie.attrs["municipio"]
        al["municipio"] = mun
        resultados.append(res)
        alertas.append(al)
        sinteticos.append(sint)
        zmarg[mun] = zm
        tempos.append({"municipio": mun, "seg_ajuste_e_escore": round(t_ajuste, 2),
                       "seg_total_com_sintetico": round(t_total, 2)})
        print(f"{mun}: ajuste+escore {t_ajuste:.1f}s, total {t_total:.1f}s")

    res = pd.concat(resultados, ignore_index=True)
    res.to_csv(os.path.join(BASE, "resultados_iforest.csv.gz"), index=False)

    taxas = taxas_por_split(res)
    taxas.to_csv(os.path.join(BASE, "iforest_taxas_por_split.csv"), index=False)
    sob = sobreposicao_ab(res)
    sob.to_csv(os.path.join(BASE, "iforest_sobreposicao_AB.csv"), index=False)
    al = pd.concat(alertas).rename_axis("datetime").reset_index()
    al.to_csv(os.path.join(BASE, "iforest_alertas_detalhados.csv"), index=False)
    sint = pd.concat(sinteticos, ignore_index=True)
    sint.to_csv(os.path.join(BASE, "iforest_sintetico_reps.csv"), index=False)
    resumo_sint = (sint.groupby(["cenario", "config", "contamination"])
                   [["recall", "precisao_ingenua", "precisao_incremental"]]
                   .mean().round(3).reset_index())
    resumo_sint.to_csv(os.path.join(BASE, "iforest_sintetico_resumo.csv"), index=False)
    pd.DataFrame(tempos).to_csv(os.path.join(BASE, "iforest_tempos.csv"), index=False)

    pd.set_option("display.width", 200)
    print("\nTaxa de alertas por split (média dos municípios):")
    print(taxas.pivot_table(index=["config", "contamination"], columns="split",
                            values="taxa_alertas").round(4))
    print("\nTaxa por município (teste):")
    print(taxas[taxas.split == "teste"].pivot_table(
        index="municipio", columns=["config", "contamination"],
        values="taxa_alertas").round(4))
    print("\nSobreposição A × B:\n", sob.round(3))
    print("\nSintético (média de 5 repetições × 4 municípios):\n", resumo_sint)
    print("\n|z| marginal da umidade nos pontos multivariados:")
    for m, z in zmarg.items():
        print(f"  {m}: mediana {z.median():.2f}, máx {z.max():.2f}")
    print("\nTop 5 alertas (config estatica, c=0.01) por município:")
    top = al[(al.config == "estatica") & (al.contamination == 0.01)]
    for m, d in top.groupby("municipio"):
        print(m)
        print(d.nlargest(5, "escore")[["datetime", *VARIAVEIS, "escore",
                                       "var_dominante", "z_dominante"]]
              .to_string(index=False))
    print("\nVariável dominante (estatica, c=0.03):")
    print(al[(al.config == "estatica") & (al.contamination == 0.03)]
          .groupby("municipio")["var_dominante"].value_counts().unstack(fill_value=0))
