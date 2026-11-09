"""Método 1: resíduos de ARIMA + Z-score.

Ideia: depois de remover o ciclo anual + diurno (ajustar_sazonalidade,
estimado só no treino), a anomalia ainda tem forte dependência temporal
(um dia quente tende a ser seguido de outro). Um ARIMA captura essa
dependência; o erro de previsão um passo à frente é a parte "inesperada"
da observação. Padronizamos esse erro com média/desvio do TREINO e
marcamos |Z| > limiar.

Garantias contra vazamento:
  * sazonalidade, ordem (p,d,q), parâmetros do ARIMA e estatísticas do Z
    são estimados apenas no treino (2015–2021);
  * validação/teste recebem os parâmetros congelados via `res.apply`
    (filtro de Kalman sem reestimação), de modo que cada resíduo em
    t usa somente y[0..t-1] → previsão genuinamente fora da amostra.

NaN: o filtro de Kalman do statsmodels (SARIMAX) trata observações
ausentes nativamente (passo de previsão sem atualização). Não há
imputação; o resíduo nesses instantes é NaN e a observação não é
avaliada (outlier=False, escore=NaN).

Precipitação: testada com log1p (mesmo pipeline), mas EXCLUÍDA dos
resultados do método. Diagnóstico (arima_precipitacao_log1p_diag.csv):
resíduos assimétricos à direita (assimetria 0,6–1,6), fortemente
heterocedásticos (Ljung-Box em resíduos² com p ≈ 0: variância alta na
estação chuvosa, quase nula na seca), MAD muito menor que o desvio
(o Z robusto explodiria) e flags quase só positivas — o piso em zero
impede "surpresas" negativas, então o Z simétrico vira apenas um
detector de "choveu mais que o previsto", sem significado de outlier.
Um modelo de duas partes (ocorrência + intensidade) seria o adequado.
"""
import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import acf, adfuller, kpss

from common import *  # noqa: F401,F403  (no notebook: células anteriores)

ALGORITMO = "ARIMA+Z"
LIMIARES = [2.5, 3.0, 3.5, 4.0]
TIPOS_Z = ["classico", "robusto"]  # média/desvio vs mediana/1,4826·MAD
VARIAVEIS_ARIMA = ["temperatura", "umidade"]
LIMITES_FISICOS = {"temperatura": None, "umidade": (0.0, 100.0)}
P_MAX, Q_MAX = 3, 3
BURN_IN = 10  # primeiras previsões dependem da inicialização do filtro


# ---------------------------------------------------------------------------
# 1. Estacionariedade
# ---------------------------------------------------------------------------
def testar_estacionariedade(x, alfa=0.05):
    """ADF (H0: raiz unitária) e KPSS (H0: estacionária) na anomalia de treino.

    Regra de decisão para d:
      * ADF rejeita H0 → d = 0 (mesmo que o KPSS rejeite: com n ≈ 5 000 o
        KPSS acusa até persistência fraca/memória longa; o conflito é
        registrado em `conflito`);
      * ADF não rejeita → d = 1.
    """
    x = pd.Series(x).dropna().to_numpy()
    with warnings.catch_warnings():
        # avisos de p-valor fora da tabela (KPSS) e de mudança de API (ADF)
        warnings.simplefilter("ignore")
        adf_stat, adf_p, *_ = adfuller(x, autolag="AIC")
        kpss_stat, kpss_p, *_ = kpss(x, regression="c", nlags="auto")
    adf_rej = adf_p < alfa
    kpss_rej = kpss_p < alfa
    d = 0 if adf_rej else 1
    return {
        "adf_estat": adf_stat, "adf_p": adf_p,
        "kpss_estat": kpss_stat, "kpss_p": kpss_p,
        "d": d, "conflito": bool(adf_rej and kpss_rej),
    }


# ---------------------------------------------------------------------------
# 2. Seleção da ordem (grade limitada, só treino)
# ---------------------------------------------------------------------------
def _ajustar(x, ordem):
    # d=0: anomalia de treino tem média ~0 por construção (MQO) → sem constante.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = SARIMAX(x, order=ordem, trend="n",
                      enforce_stationarity=True, enforce_invertibility=True)
        return mod.fit(disp=False, maxiter=200)


def selecionar_ordem(x_treino, d, criterio="bic"):
    """Grade p, q ∈ 0..3 com d fixo; retorna (melhor_res, tabela)."""
    linhas, melhor, melhor_val = [], None, np.inf
    for p in range(P_MAX + 1):
        for q in range(Q_MAX + 1):
            if p == 0 and q == 0 and d == 0:
                continue  # ruído branco: não modela nada
            try:
                res = _ajustar(x_treino, (p, d, q))
            except Exception as e:  # pragma: no cover
                linhas.append({"p": p, "d": d, "q": q, "aic": np.nan,
                               "bic": np.nan, "erro": str(e)})
                continue
            convergiu = bool(res.mle_retvals.get("converged", True))
            linhas.append({"p": p, "d": d, "q": q, "aic": res.aic,
                           "bic": res.bic, "convergiu": convergiu})
            val = getattr(res, criterio)
            if convergiu and val < melhor_val:
                melhor, melhor_val = res, val
    return melhor, pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 3. Resíduos fora da amostra e Z-score
# ---------------------------------------------------------------------------
def residuos_um_passo(res_treino, x_completo, burn_in=BURN_IN):
    """Erros de previsão um passo à frente na série inteira, sem reestimar.

    `apply` reaplica o filtro de Kalman com os parâmetros do treino desde o
    início; em t o erro é y_t − E[y_t | y_0..y_{t−1}].
    """
    res_full = res_treino.apply(np.asarray(x_completo, dtype=float), refit=False)
    e = pd.Series(np.asarray(res_full.resid, dtype=float), index=x_completo.index,
                  name="residuo")
    e[np.asarray(pd.isna(x_completo))] = np.nan
    e.iloc[:burn_in] = np.nan
    return e


def estatisticas_z(e_treino):
    e = e_treino.dropna()
    med = float(np.median(e))
    return {
        "classico": (float(e.mean()), float(e.std(ddof=1))),
        "robusto": (med, float(1.4826 * np.median(np.abs(e - med)))),
    }


def escore_z(e, centro_escala):
    centro, escala = centro_escala
    return (e - centro) / escala


# ---------------------------------------------------------------------------
# 4. Diagnóstico dos resíduos (treino)
# ---------------------------------------------------------------------------
def diagnostico_residuos(e_treino, n_param, lags=(10, 30, 60)):
    """Ljung-Box nos resíduos e nos resíduos² (heterocedasticidade).

    Defasagens em passos de 12 h (10 = 5 dias, 30 = 15 dias, 60 = 1 mês);
    gl corrigidos por p+q. Com n ≈ 5 000 o teste rejeita autocorrelações minúsculas; por isso
    reportamos também o maior |ACF| em 1..30 vs a banda ±1,96/√n.
    """
    e = e_treino.dropna()
    lb = acorr_ljungbox(e, lags=list(lags), model_df=n_param)
    lb2 = acorr_ljungbox(e ** 2, lags=list(lags))
    r = acf(e, nlags=30, fft=True)[1:]
    out = {f"lb_p_lag{l}": float(lb.loc[l, "lb_pvalue"]) for l in lags}
    out.update({f"lb2_p_lag{l}": float(lb2.loc[l, "lb_pvalue"]) for l in lags})
    out["acf_max_abs_1a30"] = float(np.max(np.abs(r)))
    out["acf_lag_max"] = int(np.argmax(np.abs(r)) + 1)
    out["banda_95"] = float(1.96 / np.sqrt(len(e)))
    out["assimetria"] = float(stats.skew(e))
    out["curtose_exc"] = float(stats.kurtosis(e))
    return out


# ---------------------------------------------------------------------------
# 5. Pipeline por série
# ---------------------------------------------------------------------------
def ajustar_modelo_serie(y, mascara_treino, transformacao=None):
    """Sazonalidade + estacionariedade + grade ARIMA, tudo no treino."""
    if transformacao == "log1p":
        y = np.log1p(y)
    sazonal, anom = ajustar_sazonalidade(y, mascara_treino)
    x_tr = anom[mascara_treino]
    est = testar_estacionariedade(x_tr)
    res, grade = selecionar_ordem(x_tr, est["d"])
    e = residuos_um_passo(res, anom)
    z_stats = estatisticas_z(e[mascara_treino])
    p, d, q = res.model.order
    diag = diagnostico_residuos(e[mascara_treino], n_param=p + q)
    return {"sazonal": sazonal, "anomalia": anom, "res": res, "grade": grade,
            "estacionariedade": est, "residuo": e, "z_stats": z_stats,
            "diagnostico": diag, "ordem": (p, d, q),
            "transformacao": transformacao}


def detectar(modelo, y_novo=None, limiar=3.0, tipo_z="classico"):
    """Z e flags para a série (ou uma versão modificada, ex. sintética).

    Para `y_novo`, sazonalidade/ARIMA/estatísticas Z continuam as do treino.
    """
    if y_novo is None:
        e = modelo["residuo"]
    else:
        y_t = np.log1p(y_novo) if modelo["transformacao"] == "log1p" else y_novo
        e = residuos_um_passo(modelo["res"], y_t - modelo["sazonal"])
    z = escore_z(e, modelo["z_stats"][tipo_z])
    flag = (z.abs() > limiar).fillna(False).astype(bool)
    return z, flag


def resultados_serie(serie, variavel, modelo):
    """Formato padrão para todas as configurações (tipo_z × limiar)."""
    p, d, q = modelo["ordem"]
    blocos = []
    for tipo_z in TIPOS_Z:
        for lim in LIMIARES:
            z, flag = detectar(modelo, limiar=lim, tipo_z=tipo_z)
            params = {"ordem": [p, d, q], "tipo_z": tipo_z, "limiar": lim,
                      "transformacao": modelo["transformacao"] or "nenhuma"}
            # escore = |Z| (maior = mais anômalo), como nos demais métodos.
            blocos.append(resultado_padrao(serie, variavel, ALGORITMO, params,
                                           z.abs(), flag))
    return pd.concat(blocos, ignore_index=True)


def resumo_flags(serie, variavel, modelo, tipo_z, limiar):
    z, flag = detectar(modelo, limiar=limiar, tipo_z=tipo_z)
    linhas = []
    for nome in SPLITS:
        m = mascara_split(serie.index, nome)
        val = z[m].notna()
        n_ok = int(val.sum())
        n_pos = int((flag[m] & (z[m] > 0)).sum())
        n_neg = int((flag[m] & (z[m] < 0)).sum())
        # "eco": flag em t−1 também marcado (pico contamina a previsão t+1).
        eco = int((flag[m] & flag.shift(1, fill_value=False)[m]).sum())
        linhas.append({"municipio": serie.attrs["municipio"],
                       "variavel": variavel, "tipo_z": tipo_z, "limiar": limiar,
                       "split": nome, "n_avaliados": n_ok,
                       "n_outliers": n_pos + n_neg,
                       "pct": 100 * (n_pos + n_neg) / max(n_ok, 1),
                       "n_pos": n_pos, "n_neg": n_neg, "n_seguido_de_flag": eco})
    return linhas


# ---------------------------------------------------------------------------
# 6. Experimento sintético (somente no teste)
# ---------------------------------------------------------------------------
def experimento_sintetico(serie, variavel, modelo, magnitudes=(3.0, 5.0),
                          sementes=range(5), n=20):
    m_teste = mascara_split(serie.index, "teste")
    y = serie[variavel]
    linhas = []
    for mag in magnitudes:
        for s in sementes:
            y_mod, rot = injetar_anomalias(y, m_teste, n=n, magnitude=mag,
                                           seed=SEED + s,
                                           limites=LIMITES_FISICOS[variavel])
            for tipo_z in TIPOS_Z:
                for lim in LIMIARES:
                    z, flag = detectar(modelo, y_mod, lim, tipo_z)
                    f, r = flag[m_teste], rot[m_teste]
                    tp = int((f & r).sum())
                    fp = int((f & ~r).sum())
                    # Tolerante: flag logo após um ponto injetado (eco do
                    # resíduo de previsão) não conta como falso positivo.
                    eco = rot.shift(1, fill_value=False)[m_teste]
                    fp_tol = int((f & ~r & ~eco).sum())
                    linhas.append({
                        "municipio": serie.attrs["municipio"],
                        "variavel": variavel, "magnitude": mag, "semente": s,
                        "tipo_z": tipo_z, "limiar": lim, "n_injetadas": int(r.sum()),
                        "tp": tp, "fp": fp, "fp_tolerante": fp_tol,
                        "recall": tp / r.sum(),
                        "precisao": tp / (tp + fp) if tp + fp else np.nan,
                        "precisao_tolerante": tp / (tp + fp_tol) if tp + fp_tol else np.nan,
                    })
    return linhas


# ---------------------------------------------------------------------------
# Execução completa
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    # Muitas threads BLAS deixam os ajustes SARIMAX (matrizes pequenas)
    # ~2x mais lentos; limitamos a 1 thread quando threadpoolctl existe.
    try:
        from threadpoolctl import threadpool_limits
        threadpool_limits(1)
    except ImportError:
        pass

    BASE = os.path.dirname(os.path.abspath(__file__))
    df = carregar_dados(os.path.join(BASE, "..", "clima_4_municipios.csv"))
    t_total = time.perf_counter()

    resultados, modelos_tab, grades, resumo, sint, tempos = [], [], [], [], [], []
    precip_tab, top_eventos = [], []

    for cod in sorted(df["codigo_ibge"].unique()):
        serie = preparar_serie(df, cod)
        m_tr = mascara_split(serie.index, "treino")
        mun = serie.attrs["municipio"]

        alvos = [(v, None) for v in VARIAVEIS_ARIMA] + [("precipitacao", "log1p")]
        for var, transf in alvos:
            t0 = time.perf_counter()
            mod = ajustar_modelo_serie(serie[var], m_tr, transf)
            t_ajuste = time.perf_counter() - t0
            p, d, q = mod["ordem"]
            g = mod["grade"].assign(municipio=mun, variavel=var)
            grades.append(g)
            linha_mod = {"municipio": mun, "variavel": var,
                         "transformacao": transf or "nenhuma",
                         "ordem": f"({p},{d},{q})", "aic": mod["res"].aic,
                         "bic": mod["res"].bic,
                         "ordem_aic": "({p},{d},{q})".format(
                             **g.loc[g["aic"].idxmin(), ["p", "d", "q"]].astype(int)),
                         **mod["estacionariedade"], **mod["diagnostico"],
                         "z_media": mod["z_stats"]["classico"][0],
                         "z_desvio": mod["z_stats"]["classico"][1],
                         "z_mediana": mod["z_stats"]["robusto"][0],
                         "z_mad": mod["z_stats"]["robusto"][1]}

            if transf == "log1p":
                # Precipitação: apenas diagnóstico (ver relatório/README).
                z, flag = detectar(mod, limiar=3.0)
                x = serie[var]
                for nome in SPLITS:
                    m = mascara_split(serie.index, nome)
                    ok = z[m].notna()
                    precip_tab.append({
                        "municipio": mun, "split": nome, "ordem": f"({p},{d},{q})",
                        "pct_zeros": 100 * float((x[m] == 0).mean()),
                        "pct_flag_z3": 100 * float(flag[m].sum() / ok.sum()),
                        "n_flag_pos": int((flag[m] & (z[m] > 0)).sum()),
                        "n_flag_neg": int((flag[m] & (z[m] < 0)).sum()),
                        "assim_resid": linha_mod["assimetria"],
                        "curt_resid": linha_mod["curtose_exc"],
                        "lb_p_lag30": linha_mod["lb_p_lag30"],
                        "lb2_p_lag30": linha_mod["lb2_p_lag30"],
                    })
                modelos_tab.append(linha_mod)
                tempos.append({"municipio": mun, "variavel": var + "_log1p",
                               "seg_ajuste": t_ajuste, "seg_sintetico": np.nan})
                continue

            resultados.append(resultados_serie(serie, var, mod))
            for tz in TIPOS_Z:
                for lim in LIMIARES:
                    resumo.extend(resumo_flags(serie, var, mod, tz, lim))

            # Eventos mais extremos (|Z| clássico) para inspeção física.
            z, _ = detectar(mod, limiar=3.0)
            top = z.abs().nlargest(5).index
            for ts in top:
                top_eventos.append({"municipio": mun, "variavel": var,
                                    "datetime": ts, "valor": serie.at[ts, var],
                                    "sazonal": mod["sazonal"][ts],
                                    "residuo": mod["residuo"][ts], "z": z[ts]})

            t1 = time.perf_counter()
            sint.extend(experimento_sintetico(serie, var, mod))
            t_sint = time.perf_counter() - t1
            modelos_tab.append(linha_mod)
            tempos.append({"municipio": mun, "variavel": var,
                           "seg_ajuste": t_ajuste, "seg_sintetico": t_sint})
            print(f"{mun:18s} {var:12s} ARIMA{mod['ordem']}  "
                  f"ajuste {t_ajuste:5.1f}s  sintético {t_sint:5.1f}s")

    out = lambda nome: os.path.join(BASE, nome)  # noqa: E731
    pd.concat(resultados, ignore_index=True).to_csv(
        out("resultados_arima.csv.gz"), index=False)
    pd.DataFrame(modelos_tab).to_csv(out("arima_modelos.csv"), index=False)
    pd.concat(grades, ignore_index=True).to_csv(out("arima_grade_ordens.csv"), index=False)
    pd.DataFrame(resumo).to_csv(out("arima_resumo_flags.csv"), index=False)
    sint_df = pd.DataFrame(sint)
    sint_df.to_csv(out("arima_sintetico_detalhe.csv"), index=False)
    (sint_df.groupby(["municipio", "variavel", "magnitude", "tipo_z", "limiar"])
     [["recall", "precisao", "precisao_tolerante"]].mean().reset_index()
     .to_csv(out("arima_sintetico_resumo.csv"), index=False))
    pd.DataFrame(precip_tab).to_csv(out("arima_precipitacao_log1p_diag.csv"), index=False)
    pd.DataFrame(top_eventos).to_csv(out("arima_top_eventos.csv"), index=False)
    pd.DataFrame(tempos).to_csv(out("arima_tempos.csv"), index=False)
    print(f"Tempo total: {time.perf_counter() - t_total:.1f}s")
