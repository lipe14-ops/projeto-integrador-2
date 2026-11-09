"""Método 3 — Filtro de Hampel (mediana móvel + MAD).

Para cada instante t, com janela W_t de observações vizinhas:
    m_t     = mediana(W_t)
    MAD_t   = mediana(|x_i − m_t|, i ∈ W_t)
    σ_t     = max(1,4826·MAD_t, σ_min)        (piso explícito p/ MAD = 0)
    R_t     = |x_t − m_t| / σ_t               (escore)
    outlier = R_t > limiar

Decisões de projeto (justificadas no relatório / notebook):
* Ciclo diurno: o filtro roda SEPARADAMENTE nas subséries das 00 e das
  12 UTC (cada uma diária). Uma janela mista 00/12 UTC tem distribuição
  bimodal (salto diurno), o que infla o MAD e reduz a sensibilidade;
  `comparar_modo_diurno` quantifica esse efeito.
* Janela em dias: meia-janela k dias ⇒ 2k+1 observações por subsérie
  (k dias antes e k depois, no mesmo horário).
* Duas variantes: "centrada" (usa o futuro — controle de qualidade
  retrospectivo) e "causal" (2k+1 observações passadas, incluindo t —
  operacional, sem olhar adiante).
* min_periods: janelas com menos de `frac_min`·(2k+1) valores válidos
  ficam sem classificação (escore NaN, outlier False).
* Precipitação: aplicada em log1p(mm) e com piso σ_min estimado no
  treino; mesmo assim o método é pouco adequado (variável intermitente,
  assimétrica, mediana 0 em estiagens) — ver relatório.
* Nada é substituído: a série original é preservada; o método devolve
  colunas de classificação.
"""
import time

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from common import *  # noqa: F401,F403  (carregar_dados, SPLITS, ...)

ALGORITMO = "Hampel"
MEIAS_JANELAS_DIAS = [3, 7, 15]
LIMIARES = [2.5, 3.0, 3.5, 4.0]
VARIANTES = ["centrada", "causal"]
FRAC_MIN = 0.6          # fração mínima de valores válidos na janela
K_MAD = 1.4826          # MAD → σ sob normalidade
LIMITES_FISICOS = {"temperatura": None, "umidade": (0.0, 100.0)}


# ---------------------------------------------------------------------------
# Núcleo vetorizado
# ---------------------------------------------------------------------------
def _janelas(x, meia_janela, variante):
    """Matriz (n, 2k+1) com as janelas de cada posição, preenchida com NaN
    nas bordas. Centrada: [t−k, t+k]; causal: [t−2k, t]."""
    w = 2 * meia_janela + 1
    if variante == "centrada":
        pad_esq, pad_dir = meia_janela, meia_janela
    elif variante == "causal":
        pad_esq, pad_dir = w - 1, 0
    else:
        raise ValueError(f"Variante desconhecida: {variante}")
    xp = np.concatenate([np.full(pad_esq, np.nan), x, np.full(pad_dir, np.nan)])
    return sliding_window_view(xp, w)


def hampel_vetor(x, meia_janela, variante="centrada", frac_min=FRAC_MIN,
                 sigma_min=0.0):
    """Hampel numa série regular 1D (np.ndarray, NaN = ausente).

    Devolve dict com mediana, sigma (já com piso), escore R_t e n_validos.
    Escore NaN quando x_t é NaN ou a janela tem poucos valores válidos.
    """
    x = np.asarray(x, dtype=float)
    J = _janelas(x, meia_janela, variante)
    n_validos = np.sum(~np.isnan(J), axis=1)
    min_periods = int(np.ceil(frac_min * J.shape[1]))
    ok = (n_validos >= min_periods) & ~np.isnan(x)
    med = np.full(len(x), np.nan)
    mad = np.full(len(x), np.nan)
    if ok.any():
        Jok = J[ok]
        med[ok] = np.nanmedian(Jok, axis=1)
        mad[ok] = np.nanmedian(np.abs(Jok - med[ok, None]), axis=1)
    sigma = np.maximum(K_MAD * mad, sigma_min)
    with np.errstate(divide="ignore", invalid="ignore"):
        escore = np.abs(x - med) / sigma
    # MAD = 0 sem piso (sigma_min = 0): desvio nulo → 0; desvio > 0 → inf.
    escore[ok & (sigma == 0) & (x == med)] = 0.0
    escore[~ok] = np.nan
    return {"mediana": med, "sigma": sigma, "mad": mad,
            "escore": escore, "n_validos": n_validos}


def hampel_serie(y, meia_janela_dias, variante="centrada", por_horario=True,
                 frac_min=FRAC_MIN, sigma_min=0.0):
    """Hampel numa pd.Series de 12 h.

    por_horario=True: roda separadamente nas subséries 00 e 12 UTC
    (k dias ⇒ 2k+1 obs daquele horário). por_horario=False: janela mista
    de 2·(2k)+1 observações de 12 h cobrindo os mesmos ±k dias.
    """
    saida = pd.DataFrame(index=y.index,
                         columns=["mediana", "sigma", "mad", "escore"],
                         dtype=float)
    if por_horario:
        for h in np.unique(y.index.hour):
            m = y.index.hour == h
            r = hampel_vetor(y[m].to_numpy(), meia_janela_dias, variante,
                             frac_min, sigma_min)
            for c in saida.columns:
                saida.loc[m, c] = r[c]
    else:
        r = hampel_vetor(y.to_numpy(), 2 * meia_janela_dias, variante,
                         frac_min, sigma_min)
        for c in saida.columns:
            saida[c] = r[c]
    return saida


# ---------------------------------------------------------------------------
# Transformação e piso de escala por variável
# ---------------------------------------------------------------------------
def transformar(variavel, y):
    """Precipitação em log1p(mm): reduz a assimetria e evita que a escala
    seja dominada por poucos eventos intensos."""
    return np.log1p(y) if variavel == "precipitacao" else y


def estimar_sigma_min(variavel, y_t, mascara_treino, meia_janela_dias,
                      variante, quantil=0.01):
    """Piso σ_min estimado SÓ no treino: quantil `quantil` (1 %) dos σ_t > 0.

    Temperatura/umidade: MAD = 0 não ocorre (valores contínuos de
    reanálise); o piso de 1 % só evita escalas degeneradas em trechos
    anormalmente calmos, sem dessensibilizar o filtro no resto da série.
    Precipitação: em estiagens mediana = MAD = 0 e qualquer garoa teria
    R = ∞; o piso também é limitado por baixo por log1p(1 mm), i.e. uma
    escala de 1 mm/12 h (limiar usual de "dia de chuva").
    """
    r = hampel_serie(y_t.where(mascara_treino), meia_janela_dias, variante)
    s = r["sigma"].to_numpy()
    s = s[np.isfinite(s) & (s > 0)]
    piso = float(np.quantile(s, quantil)) if len(s) else 0.0
    if variavel == "precipitacao":
        piso = max(piso, float(np.log1p(1.0)))
    return piso


def classificar_hampel(serie, variavel, meia_janela_dias, limiar, variante,
                       mascara_treino=None, y=None):
    """Escore e flag de uma variável/configuração. `y` permite passar uma
    série modificada (ex.: com anomalias injetadas) mantendo o piso
    estimado na série original de treino."""
    if mascara_treino is None:
        mascara_treino = mascara_split(serie.index, "treino")
    y_orig = serie[variavel]
    y = y_orig if y is None else y
    sigma_min = estimar_sigma_min(variavel, transformar(variavel, y_orig),
                                  mascara_treino, meia_janela_dias, variante)
    r = hampel_serie(transformar(variavel, y), meia_janela_dias, variante,
                     sigma_min=sigma_min)
    escore = r["escore"].to_numpy()
    outlier = np.nan_to_num(escore, nan=0.0) > limiar
    return escore, outlier, sigma_min, r


# ---------------------------------------------------------------------------
# Isolados × persistentes
# ---------------------------------------------------------------------------
def rotular_eventos(outlier, index, tolerancia_h=24):
    """Agrupa flags separadas por ≤ tolerancia_h (24 h, porque cada
    subsérie horária tem passo de 24 h) em eventos. Devolve (id_evento,
    tamanho_evento) por observação; 0 para não-outliers."""
    outlier = np.asarray(outlier, dtype=bool)
    ids = np.zeros(len(outlier), dtype=int)
    tam = np.zeros(len(outlier), dtype=int)
    pos = np.flatnonzero(outlier)
    if len(pos) == 0:
        return ids, tam
    t = (index[pos] - index[0]) / pd.Timedelta(hours=1)  # horas, independe da resolução
    novo = np.r_[True, np.diff(np.asarray(t, dtype=float)) > tolerancia_h]
    ev = np.cumsum(novo)
    ids[pos] = ev
    cont = np.bincount(ev)
    tam[pos] = cont[ev]
    return ids, tam


# ---------------------------------------------------------------------------
# Experimento sintético
# ---------------------------------------------------------------------------
def metricas_injecao(outlier, outlier_limpo, rotulos, mascara):
    """Recall e precisão avaliados só no que a injeção alterou.

    TP = injetadas detectadas. FP = flags novas (ausentes na série limpa)
    em pontos não injetados — efeito colateral da injeção. Flags que já
    existiam na série original não são contadas (não há rótulo para elas).
    `precisao_bruta` conta todas as flags não injetadas como FP.
    """
    o, o0, r = (np.asarray(a, bool) & mascara for a in
                (outlier, outlier_limpo, rotulos))
    tp = int((o & r).sum())
    fp_novo = int((o & ~r & ~o0).sum())
    fp_bruto = int((o & ~r).sum())
    n = int(r.sum())
    return {"n_injetadas": n, "tp": tp, "fp_novos": fp_novo,
            "fp_brutos": fp_bruto,
            "recall": tp / n if n else np.nan,
            "precisao": tp / (tp + fp_novo) if tp + fp_novo else np.nan,
            "precisao_bruta": tp / (tp + fp_bruto) if tp + fp_bruto else np.nan}


def experimento_sintetico(serie, variavel, split, configs, magnitudes=(3, 5, 8),
                          n=20, seed=SEED):
    mask = mascara_split(serie.index, split)
    linhas = []
    limpo = {c: classificar_hampel(serie, variavel, *c)[1] for c in configs}
    for mag in magnitudes:
        y_mod, rot = injetar_anomalias(serie[variavel], mask, n=n,
                                       magnitude=mag, seed=seed,
                                       limites=LIMITES_FISICOS[variavel])
        for (k, lim, var) in configs:
            o0 = limpo[(k, lim, var)]
            _, o1, _, _ = classificar_hampel(serie, variavel, k, lim, var, y=y_mod)
            m = metricas_injecao(o1, o0, rot.to_numpy(), mask)
            linhas.append({"municipio": serie.attrs["municipio"],
                           "variavel": variavel, "split": split,
                           "magnitude": mag, "meia_janela_dias": k,
                           "limiar": lim, "variante": var, **m})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Justificativa do tratamento diurno
# ---------------------------------------------------------------------------
def comparar_modo_diurno(serie, variavel, meia_janela_dias=7, limiar=3.0):
    """σ_t mediano e taxa de flags: janela por horário × janela mista."""
    y = transformar(variavel, serie[variavel])
    out = []
    for por_h in (True, False):
        r = hampel_serie(y, meia_janela_dias, "centrada", por_horario=por_h)
        e = r["escore"]
        out.append({"municipio": serie.attrs["municipio"], "variavel": variavel,
                    "modo": "por_horario" if por_h else "misto",
                    "sigma_mediano": float(np.nanmedian(r["sigma"])),
                    "pct_mad_zero": float(np.nanmean(r["mad"] == 0) * 100),
                    "taxa_flags_pct": float((e > limiar).mean() * 100)})
    return out


# ---------------------------------------------------------------------------
# Execução completa
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    CAMINHO = os.environ.get("CLIMA_CSV", "../clima_4_municipios.csv")
    t0_total = time.perf_counter()
    df = carregar_dados(CAMINHO)
    municipios = df["codigo_ibge"].unique()
    series = {c: preparar_serie(df, c) for c in municipios}

    # 1) Justificativa do modo diurno ----------------------------------------
    diurno = pd.DataFrame([d for s in series.values() for v in VARIAVEIS
                           for d in comparar_modo_diurno(s, v)])
    diurno.to_csv("hampel_modo_diurno.csv", index=False)
    print("\n== Janela por horário × mista (k=7 d, limiar 3) ==")
    print(diurno.round(3).to_string(index=False))

    # 2) Grade completa: escores e flags reais --------------------------------
    resultados, tempos, pisos = [], [], []
    for c, s in series.items():
        for v in VARIAVEIS:
            t0 = time.perf_counter()
            for var in VARIANTES:
                for k in MEIAS_JANELAS_DIAS:
                    escore, _, smin, r = classificar_hampel(s, v, k, LIMIARES[0], var)
                    pisos.append({"municipio": s.attrs["municipio"], "variavel": v,
                                  "variante": var, "meia_janela_dias": k,
                                  "sigma_min": smin,
                                  "pct_sigma_no_piso": float(np.nanmean(
                                      r["sigma"] <= smin) * 100)})
                    for lim in LIMIARES:
                        outlier = np.nan_to_num(escore, nan=0.0) > lim
                        res = resultado_padrao(
                            s, v, ALGORITMO,
                            {"meia_janela_dias": k, "janela_obs": 2 * k + 1,
                             "limiar": lim, "variante": var,
                             "por_horario": True, "frac_min": FRAC_MIN,
                             "sigma_min": round(smin, 6),
                             "transformacao": "log1p" if v == "precipitacao" else "nenhuma"},
                            escore, outlier)
                        res["meia_janela_dias"], res["limiar"], res["variante"] = k, lim, var
                        res["valor"] = s[v].to_numpy()
                        med = r["mediana"].to_numpy()
                        # mediana em unidades originais; sigma na escala
                        # do escore (log1p para precipitação).
                        res["mediana_local"] = np.expm1(med) if v == "precipitacao" else med
                        res["sigma_local"] = r["sigma"].to_numpy()
                        _, tam = rotular_eventos(outlier, s.index)
                        res["tamanho_evento"] = tam
                        resultados.append(res)
            tempos.append({"municipio": s.attrs["municipio"], "variavel": v,
                           "segundos_24_configs": time.perf_counter() - t0})
    res = pd.concat(resultados, ignore_index=True)
    split = np.select(
        [mascara_split(pd.DatetimeIndex(res["datetime"]), n) for n in SPLITS],
        list(SPLITS), default="fora")
    res["split"] = split
    res.to_csv("resultados_hampel.csv.gz", index=False)
    pd.DataFrame(pisos).to_csv("hampel_sigma_min.csv", index=False)
    pd.DataFrame(tempos).to_csv("hampel_tempos.csv", index=False)

    # 3) Sensibilidade: contagens de flags ------------------------------------
    chaves = ["variavel", "variante", "meia_janela_dias", "limiar"]
    g = res.groupby(["municipio", *chaves, "split"])
    sens = g.agg(n_obs=("outlier", "size"),
                 n_classificadas=("escore", lambda e: e.notna().sum()),
                 n_flags=("outlier", "sum")).reset_index()
    sens["taxa_pct"] = 100 * sens["n_flags"] / sens["n_classificadas"]
    sens.to_csv("hampel_sensibilidade.csv", index=False)
    print("\n== Taxa de flags (%) no teste, média dos 4 municípios ==")
    piv = (sens[sens.split == "teste"]
           .groupby(chaves)["taxa_pct"].mean().unstack("limiar").round(2))
    print(piv.to_string())

    # 4) Isolados × persistentes (todo o período) -----------------------------
    fl = res[res["outlier"]]
    # Contagem de observações sinalizadas por tipo e número de eventos
    # (grupos de flags separados por ≤ 24 h) persistentes.
    iso = (fl.assign(tipo=np.where(fl["tamanho_evento"] == 1, "obs_isoladas",
                                   "obs_persistentes"))
             .groupby([*chaves, "tipo"]).size().unstack("tipo", fill_value=0)
             .reset_index())
    n_ev = (fl[fl["tamanho_evento"] > 1]
            .assign(ev=lambda d: d.groupby(["municipio", *chaves])["tamanho_evento"]
                    .transform(lambda t: rotular_eventos(np.ones(len(t), bool),
                                                         pd.DatetimeIndex(d.loc[t.index, "datetime"]))[0]))
            .groupby([*chaves])
            .apply(lambda d: d.groupby(["municipio", "ev"]).ngroups)
            .rename("eventos_persistentes").reset_index())
    iso = iso.merge(n_ev, how="left").fillna({"eventos_persistentes": 0})
    iso.to_csv("hampel_isolados_persistentes.csv", index=False)

    # 5) Experimento sintético: escolha na validação, relatório no teste ------
    configs = [(k, l, var) for var in VARIANTES for k in MEIAS_JANELAS_DIAS
               for l in LIMIARES]
    sint = []
    for s in series.values():
        for v in ["temperatura", "umidade"]:
            for sp in ["validacao", "teste"]:
                sint.append(experimento_sintetico(s, v, sp, configs))
    sint = pd.concat(sint, ignore_index=True)
    sint.to_csv("hampel_sintetico.csv", index=False)
    agg = (sint.groupby(["split", "variavel", "variante", "meia_janela_dias",
                         "limiar", "magnitude"])[["tp", "fp_novos", "n_injetadas"]]
               .sum().reset_index())
    agg["recall"] = agg.tp / agg.n_injetadas
    agg["precisao"] = agg.tp / (agg.tp + agg.fp_novos)
    agg["f1"] = 2 * agg.recall * agg.precisao / (agg.recall + agg.precisao)
    # Escolha do padrão por variante, só com a validação: maior recall médio
    # (temperatura+umidade, magnitude 5σ) entre as configurações cuja taxa
    # real de flags na validação (temp+umid, média dos municípios) é ≤ 1 %
    # — orçamento de revisão manual. Não usamos F1 com `precisao` porque
    # ela ignora as flags pré-existentes e favorece limiares baixos demais.
    ORCAMENTO_PCT = 1.0
    val = agg[(agg.split == "validacao") & (agg.magnitude == 5)]
    cfg = ["variante", "meia_janela_dias", "limiar"]
    taxa_val = (sens[(sens.split == "validacao") & sens.variavel.isin(["temperatura", "umidade"])]
                .groupby(cfg)["taxa_pct"].mean().rename("taxa_real_val_pct"))
    cand = val.groupby(cfg)[["recall", "f1"]].mean().join(taxa_val).reset_index()
    cand.to_csv("hampel_candidatos_validacao.csv", index=False)
    # Variante sem configuração dentro do orçamento (ocorre com a causal):
    # usa a de menor taxa real na validação.
    cand["no_orcamento"] = cand.taxa_real_val_pct <= ORCAMENTO_PCT
    escolha = (cand.assign(ordem=np.where(cand.no_orcamento, -cand.recall,
                                          cand.taxa_real_val_pct))
               .sort_values(["no_orcamento", "ordem"], ascending=[False, True])
               .groupby("variante").head(1).drop(columns="ordem"))
    escolha.to_csv("hampel_config_escolhida.csv", index=False)
    print(f"\n== Configuração escolhida na validação (recall 5σ, taxa real ≤ {ORCAMENTO_PCT}%) ==")
    print(escolha.round(3).to_string(index=False))
    sel = agg.merge(escolha[["variante", "meia_janela_dias", "limiar"]])
    sel = sel[sel.split == "teste"]
    sel.to_csv("hampel_sintetico_teste_escolhida.csv", index=False)
    print("\n== Teste (config escolhida) ==")
    print(sel.round(3).to_string(index=False))

    print("\n== Tempo por município/variável (24 configs) ==")
    print(pd.DataFrame(tempos).round(3).to_string(index=False))
    print(f"\nTempo total: {time.perf_counter() - t0_total:.1f} s")
