"""Seções 7–11: os três métodos, comparação e visualizações."""

MD_ARIMA = r"""
## 7. Implementação: resíduos de ARIMA + Z-score

**Procedimento.** Para cada município e variável (temperatura e umidade):

1. Calcula-se a anomalia sazonal com coeficientes estimados no treino.
2. Testa-se a estacionariedade (ADF e KPSS) nas anomalias de treino e decide-se $d$ por série.
3. As ordens $p, q \in \{0,\dots,3\}$ são escolhidas por **BIC** no treino.
4. Calculam-se os **resíduos de previsão de um passo à frente** com os parâmetros congelados (`res.apply(refit=False)`). Cada resíduo em $t$ usa apenas $y_{0..t-1}$, então validação e teste são genuinamente fora da amostra.
5. Calcula-se $Z$ com média e desvio dos resíduos de **treino**. Uma variante robusta usa mediana e $1{,}4826\cdot$MAD.
6. Sinaliza-se $|Z|>3$ e analisa-se a sensibilidade para limiares de 2,5, 3, 3,5 e 4.

A **precipitação** é testada em log1p apenas como diagnóstico e **excluída**
das classificações. O motivo está na docstring do módulo: os resíduos são
assimétricos e heterocedásticos, e as flags são quase só positivas.
"""

COD_ARIMA_RUN = r"""
try:  # SARIMAX com matrizes pequenas fica mais lento com muitas threads BLAS
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
except ImportError:
    pass

t_ajuste = 0.0
modelos_arima, tab_modelos, resumo_arima, sint_arima, precip_diag = {}, [], [], [], []
for c, s in series.items():
    tr = mascara_split(s.index, "treino")
    for var, transf in [("temperatura", None), ("umidade", None), ("precipitacao", "log1p")]:
        t0 = time.perf_counter()
        mod = ajustar_modelo_serie(s[var], tr, transf)
        if not transf:
            t_ajuste += time.perf_counter() - t0
        p, d, q = mod["ordem"]
        tab_modelos.append({"município": CODIGOS[c], "variável": var, "transf.": transf or "—",
                            "ordem (BIC)": f"({p},{d},{q})", **mod["estacionariedade"], **mod["diagnostico"]})
        if transf:
            z, flag = detectar(mod, limiar=3.0)
            precip_diag.append({"município": CODIGOS[c], "% flags |Z|>3": round(100 * flag.mean(), 2),
                                "flags positivas": int((flag & (z > 0)).sum()),
                                "flags negativas": int((flag & (z < 0)).sum()),
                                "assimetria resíduos": round(mod["diagnostico"]["assimetria"], 2)})
            continue
        modelos_arima[(c, var)] = mod
        for tz in TIPOS_Z:
            for lim in LIMIARES:
                resumo_arima.extend(resumo_flags(s, var, mod, tz, lim))
        sint_arima.extend(experimento_sintetico_arima(s, var, mod))
TEMPO = {"ARIMA+Z": t_ajuste}
print(f"ARIMA (seleção de ordem + resíduos, temperatura e umidade): {t_ajuste:.1f} s")

tab_modelos = pd.DataFrame(tab_modelos)
cols = [c for c in ["município", "variável", "transf.", "ordem (BIC)", "d", "adf_p", "kpss_p",
                    "lb_p_lag10", "lb_p_lag30", "lb2_p_lag30", "acf_max_1_30"] if c in tab_modelos]
tab_modelos[cols].round(4)
"""

MD_ARIMA_DIAG = r"""
**Diagnóstico.** O ADF rejeita a raiz unitária em todas as séries de
anomalia, então $d=0$. Em várias séries o KPSS também rejeita a
estacionariedade, um conflito comum em amostras grandes e persistentes
($n\approx 5\,100$). O Ljung–Box costuma rejeitar a ausência de
autocorrelação residual porque, com esse $n$, o teste tem poder para detectar
autocorrelações muito pequenas; o tamanho efetivo aparece em `acf_max_1_30`.
O Ljung–Box nos resíduos ao quadrado (`lb2`) indica **heterocedasticidade**
sazonal, o que torna um limiar $|Z|$ constante mais permissivo na estação de
maior variância. Essa é uma limitação reconhecida do método.
"""

COD_ARIMA_RESUMO = r"""
resumo_arima = pd.DataFrame(resumo_arima)
print("Precipitação (log1p) — apenas diagnóstico:")
display(pd.DataFrame(precip_diag))

print("% sinalizado por split (Z clássico), média sobre municípios e variáveis:")
sens_arima = (resumo_arima.groupby(["tipo_z", "limiar", "split"])["pct"].mean()
              .unstack("split")[list(SPLITS)].round(2))
display(sens_arima)

print("Z clássico, |Z|>3, por município e variável:")
resumo_arima[(resumo_arima.tipo_z == "classico") & (resumo_arima.limiar == 3.0)].pivot_table(
    index=["municipio", "variavel"], columns="split", values=["pct", "n_pos", "n_neg"]).round(2)
"""

COD_ARIMA_SINT = r"""
sint_arima = pd.DataFrame(sint_arima)
(sint_arima.groupby(["magnitude", "tipo_z", "limiar"])[["recall", "precisao", "precisao_tolerante"]]
 .mean().round(3))
"""

MD_ARIMA_SINT = r"""
No experimento sintético, a precisão conta como falso positivo todo alerta
não injetado, inclusive anomalias reais do período de teste. Por isso ela é
um **limite inferior**. A `precisao_tolerante` também desconsidera o
alerta imediatamente seguinte a um pico injetado, porque o pico contamina a
previsão de um passo.
"""

COD_ARIMA_FIG = r"""
c, var = 2910800, "temperatura"
mod = modelos_arima[(c, var)]
z, flag = detectar(mod, limiar=3.0)
s = series[c]
jan = slice("2022-09-15", "2022-12-15")

fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
ax[0].plot(s.loc[jan, var], lw=0.8, color="gray", label="observado")
ax[0].plot(mod["sazonal"].loc[jan], lw=1.2, color="k", ls="--", label="sazonal (treino)")
f = flag.loc[jan]
ax[0].scatter(s.loc[jan].index[f], s.loc[jan, var][f], color=CORES["ARIMA+Z"], zorder=3, label="|Z| > 3")
ax[0].set_ylabel("temperatura (°C)"); ax[0].legend()
ax[1].plot(z.loc[jan], lw=0.8, color=CORES["ARIMA+Z"])
for h in (-3, 3): ax[1].axhline(h, color="r", ls=":", lw=1)
ax[1].set_ylabel("Z do resíduo"); ax[1].set_xlabel("data (UTC)")
fig.suptitle(f"ARIMA{mod['ordem']} + Z — {CODIGOS[c]}, validação (set–dez 2022)")
plt.tight_layout(); plt.show()
"""

MD_IFOREST = r"""
## 8. Implementação: Isolation Forest multivariado

**Atributos.**
- Configuração **A (estática):** anomalias sazonais de temperatura e umidade, mais $\log(1+P)$.
- Configuração **B (temporal):** A mais as diferenças de 24 h, ou seja, o mesmo horário do dia anterior, usando só o passado.

As duas configurações diferem **apenas nas entradas**. O timestamp bruto não é
usado. A sazonalidade entra pela anomalia, que transforma "atípico para a
estação e o horário" em um valor extremo num único eixo, o que combina com
as partições paralelas aos eixos do IF.

**Ajuste e limiar.**
- `RobustScaler` e IF (300 árvores, `max_samples=256`, `random_state=42`) são ajustados **só no treino**.
- O escore é $-$`score_samples`, de modo que um valor maior indica uma observação mais anômala.
- `contamination` é tratado como hipótese: o limiar é o quantil $1-c$ do escore **no treino**, com $c \in \{0{,}01; 0{,}03; 0{,}05\}$. A taxa observada em validação e teste é, portanto, um resultado fora da amostra.

**Faltantes.** Linhas com qualquer atributo ausente ficam como *não
classificadas*, sem imputação.

Diferentemente dos outros dois métodos, o IF usa a **precipitação** como
entrada. Isso é uma diferença de escopo, e não um mérito do algoritmo.
"""

COD_IFOREST_RUN = r"""
t0 = time.perf_counter()
res_if, modelos_if, alertas_if, sint_if = [], {}, [], []
for c, s in series.items():
    r, mods, al = rodar_municipio(s)
    res_if.append(r); modelos_if[c] = mods
    alertas_if.append(al.assign(municipio=s.attrs["municipio"]))
TEMPO["IsolationForest"] = time.perf_counter() - t0
for c, s in series.items():
    sint_if.append(experimento_sintetico_if(s, modelos_if[c])[0])
print(f"Isolation Forest (ajuste + escore): {TEMPO['IsolationForest']:.1f} s")

res_if = pd.concat(res_if, ignore_index=True)
alertas_if = pd.concat(alertas_if).rename_axis("datetime").reset_index()
taxas_if = taxas_por_split(res_if)
print("Taxa de alertas fora do treino (média dos municípios):")
display(taxas_if.pivot_table(index=["config", "contamination"], columns="split",
                             values="taxa_alertas")[list(SPLITS)].round(4))
print("Sobreposição A × B (Jaccard):")
sobreposicao_ab(res_if).pivot(index="municipio", columns="contamination", values="jaccard").round(2)
"""

MD_IFOREST_TAXAS = r"""
**Leitura.** No treino, a taxa coincide com $c$ por construção. Em validação
e teste ela é maior, o que indica um **deslocamento** da distribuição dos
anos recentes em relação a 2015–2021, como anos mais quentes ou o El Niño
2023–24. O índice de Jaccard entre A e B mostra quanto a escolha das entradas
muda *quais* pontos são sinalizados.
"""

COD_IFOREST_SINT = r"""
sint_if = pd.concat(sint_if, ignore_index=True)
(sint_if.groupby(["cenario", "config", "contamination"])
 [["recall", "precisao_ingenua", "precisao_incremental"]].mean().round(3).unstack("config"))
"""

MD_IFOREST_SINT = r"""
O cenário `multivariada_T_UR` testa o caso que motiva o uso de um método
multivariado: umidade marginalmente comum, mas alta numa manhã muito quente
da estação seca. O recall baixo mostra que, **nesses dados**, o IF tem
dificuldade com anomalias puramente condicionais, porque as anomalias
marginais são só moderadamente correlacionadas.

Duas medidas de precisão são reportadas:
- **Ingênua:** conta qualquer alerta não injetado como falso positivo.
- **Incremental:** conta apenas os alertas novos causados pela injeção.
"""

COD_IFOREST_DOM = r"""
print("Variável dominante nos alertas (config temporal, c=0,01) — heurística, não atribuição causal:")
display(alertas_if[(alertas_if.config == "temporal") & (alertas_if.contamination == 0.01)]
        .groupby("municipio")["var_dominante"].value_counts().unstack(fill_value=0))
print("Alertas de maior escore:")
(alertas_if[(alertas_if.config == "temporal") & (alertas_if.contamination == 0.01)]
 .sort_values("escore", ascending=False).groupby("municipio").head(3)
 [["municipio", "datetime", *VARIAVEIS, "escore", "var_dominante", "z_dominante"]]
 .round({v: 2 for v in [*VARIAVEIS, "escore", "z_dominante"]}))
"""

MD_HAMPEL = r"""
## 9. Implementação: filtro de Hampel

**Decisões.**
- **Ciclo diurno:** o filtro roda separadamente nas subséries das 00 e das 12 UTC. Uma meia-janela de $k$ dias corresponde a $2k+1$ observações do mesmo horário. A janela mista (00 e 12 UTC juntas) é bimodal e infla o MAD; o efeito é quantificado abaixo.
- **Variantes:** *centrada*, com $[t-k, t+k]$, para controle de qualidade retrospectivo; e *causal*, com $[t-2k, t]$, que usa só o passado e serve para uso operacional.
- **Poucos dados:** janelas com menos de 60% de valores válidos ficam sem classificação.
- **MAD = 0:** usa-se $\sigma_t=\max(1{,}4826\cdot\mathrm{MAD}_t,\ \sigma_{\min})$, com $\sigma_{\min}$ estimado no treino. Para a precipitação, o filtro é aplicado em $\log(1+P)$ com piso $\geq \log(1+1\,\text{mm})$.
- **Preservação dos dados:** nenhum valor é substituído.
- **Grade de sensibilidade:** $k\in\{3,7,15\}$ dias × limiar $\in\{2{,}5; 3; 3{,}5; 4\}$.
- **Escolha da configuração padrão, na validação:** maior recall em injeções de $5\sigma$, entre as configurações cuja taxa real de alertas na validação seja $\leq 1\%$. Esse teto funciona como orçamento de revisão manual.
"""

COD_HAMPEL_DIURNO = r"""
diurno = pd.DataFrame([d for s in series.values() for v in VARIAVEIS for d in comparar_modo_diurno(s, v)])
diurno.pivot_table(index=["municipio", "variavel"], columns="modo",
                   values=["sigma_mediano", "taxa_flags_pct"]).round(3)
"""

COD_HAMPEL_RUN = r"""
t0 = time.perf_counter()
GRADE = [(k, lim, var) for var in VARIANTES for k in MEIAS_JANELAS_DIAS for lim in LIMIARES]
sens_h, hampel_escores = [], {}
for c, s in series.items():
    for v in VARIAVEIS:
        for var in VARIANTES:
            for k in MEIAS_JANELAS_DIAS:
                escore, _, smin, r = classificar_hampel(s, v, k, LIMIARES[0], var)
                hampel_escores[(c, v, var, k)] = (escore, smin, r)
                for lim in LIMIARES:
                    flag = np.nan_to_num(escore, nan=0.0) > lim
                    for nome in SPLITS:
                        m = mascara_split(s.index, nome)
                        n_ok = int(np.isfinite(escore[m]).sum())
                        sens_h.append({"municipio": s.attrs["municipio"], "variavel": v, "variante": var,
                                       "meia_janela_dias": k, "limiar": lim, "split": nome,
                                       "n_flags": int(flag[m].sum()),
                                       "taxa_pct": 100 * flag[m].sum() / max(n_ok, 1)})
TEMPO["Hampel"] = time.perf_counter() - t0
print(f"Hampel (grade completa, 3 variáveis × 24 configs × 4 municípios): {TEMPO['Hampel']:.1f} s")
sens_h = pd.DataFrame(sens_h)
print("Taxa de alertas (%) no TESTE, média dos municípios:")
(sens_h[sens_h.split == "teste"].groupby(["variavel", "variante", "meia_janela_dias", "limiar"])
 ["taxa_pct"].mean().unstack("limiar").round(2))
"""

COD_HAMPEL_ESCOLHA = r"""
sint_h = pd.concat([experimento_sintetico_hampel(s, v, sp, GRADE)
                    for s in series.values() for v in ["temperatura", "umidade"]
                    for sp in ["validacao", "teste"]], ignore_index=True)
agg_h = (sint_h.groupby(["split", "variavel", "variante", "meia_janela_dias", "limiar", "magnitude"])
         [["tp", "fp_novos", "n_injetadas"]].sum().reset_index())
agg_h["recall"] = agg_h.tp / agg_h.n_injetadas
agg_h["precisao"] = agg_h.tp / (agg_h.tp + agg_h.fp_novos)

CFG = ["variante", "meia_janela_dias", "limiar"]
ORCAMENTO_PCT = 1.0
taxa_val = (sens_h[(sens_h.split == "validacao") & sens_h.variavel.isin(["temperatura", "umidade"])]
            .groupby(CFG)["taxa_pct"].mean().rename("taxa_real_val_pct"))
cand = (agg_h[(agg_h.split == "validacao") & (agg_h.magnitude == 5)]
        .groupby(CFG)["recall"].mean().to_frame().join(taxa_val).reset_index())
cand["no_orcamento"] = cand.taxa_real_val_pct <= ORCAMENTO_PCT
# Dentro do orçamento: maior recall; se nenhuma cabe (variante causal), a de menor taxa real.
escolha_h = (cand.assign(ordem=np.where(cand.no_orcamento, -cand.recall, cand.taxa_real_val_pct))
             .sort_values(["no_orcamento", "ordem"], ascending=[False, True])
             .groupby("variante").head(1).drop(columns="ordem"))
print("Configuração escolhida na VALIDAÇÃO:")
display(escolha_h.round(3))
print("Desempenho no TESTE (sintético) da configuração escolhida:")
(agg_h[agg_h.split == "teste"].merge(escolha_h[CFG])
 .pivot_table(index=["variavel", "variante"], columns="magnitude", values=["recall", "precisao"]).round(3))
"""

COD_HAMPEL_EVENTOS = r"""
cfg_c = escolha_h[escolha_h.variante == "centrada"].iloc[0]
K_H, LIM_H = int(cfg_c.meia_janela_dias), float(cfg_c.limiar)
res_h, ev_h = [], []
for c, s in series.items():
    for v in VARIAVEIS:
        for var in VARIANTES:
            cf = escolha_h[escolha_h.variante == var].iloc[0]
            k, lim = int(cf.meia_janela_dias), float(cf.limiar)
            escore, smin, r = hampel_escores[(c, v, var, k)]
            flag = np.nan_to_num(escore, nan=0.0) > lim
            out = resultado_padrao(s, v, ALGORITMO_H, {"variante": var, "meia_janela_dias": k, "limiar": lim,
                                                     "sigma_min": round(smin, 6), "por_horario": True}, escore, flag)
            out["variante"] = var
            out["valor"] = s[v].to_numpy()
            med = r["mediana"].to_numpy()
            out["mediana_local"] = np.expm1(med) if v == "precipitacao" else med
            _, out["tamanho_evento"] = rotular_eventos(flag, s.index)
            res_h.append(out)
res_h = pd.concat(res_h, ignore_index=True)
fl = res_h[res_h.outlier]
print("Isolados × persistentes (agrupando alertas separados por ≤ 24 h), período completo:")
display(fl[fl.variante == "centrada"].groupby(["municipio", "variavel"]).size().unstack(fill_value=0)
        .rename_axis(columns="alertas Hampel centrado (período completo)"))
(fl.assign(tipo=np.where(fl.tamanho_evento == 1, "isolada", "persistente"))
 .groupby(["variavel", "variante", "tipo"]).size().unstack("tipo", fill_value=0))
"""

COD_HAMPEL_FIG = r"""
c = 4314902
s = series[c]
jan = slice("2024-04-01", "2024-06-15")
fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
for a, v in zip(ax, ["precipitacao", "temperatura"]):
    d = res_h[(res_h.codigo_ibge == c) & (res_h.variavel == v) & (res_h.variante == "centrada")].set_index("datetime").loc[jan]
    a.plot(d.index, d.valor, lw=0.8, color="gray", label="observado")
    a.plot(d.index, d.mediana_local, lw=1.2, color="k", ls="--", label="mediana local")
    a.scatter(d.index[d.outlier], d.valor[d.outlier], color=CORES["Hampel"], zorder=3, label=f"R > {LIM_H}")
    a.set_ylabel(f"{v} ({UNIDADES[v]})")
ax[0].legend(); ax[1].set_xlabel("data (UTC)")
fig.suptitle(f"Hampel centrado (k={K_H} d, por horário) — Porto Alegre, abr–jun 2024 (enchentes no RS)")
plt.tight_layout(); plt.show()

d = s.loc["2024-04-26":"2024-05-13", "precipitacao"]
print(f"Precipitação acumulada 26/04–13/05/2024: {d.sum():.0f} mm ({d.isna().sum()} valor ausente)")
"""

MD_COMPARA = r"""
## 10. Comparação dos resultados

Para uma comparação justa, cada método é fixado numa configuração principal
com **orçamento de alertas semelhante, em torno de 1%**:

| Método | Configuração principal | Variáveis |
|---|---|---|
| ARIMA+Z | Z clássico, $\lvert Z\rvert>3$ | temperatura, umidade (univariado) |
| Isolation Forest | config. B (temporal), $c=0{,}01$ | temperatura, umidade, precipitação (multivariado) |
| Hampel | centrado, $k$ e limiar escolhidos na validação | temperatura, umidade (univariado) |

A unidade de comparação é o par **(município, instante)**. Um método
univariado sinaliza o instante se sinalizar temperatura **ou** umidade. A
precipitação do Hampel é reportada à parte, porque ARIMA não a classifica e
o IF a usa só como entrada conjunta.
"""

COD_COMPARA_FLAGS = r"""
def flags_instante(df_res, nome):
    return (df_res.groupby(["codigo_ibge", "datetime"])["outlier"].any().rename(nome))

arima_pr = pd.concat([resultado_padrao(series[c], v, "ARIMA+Z", {"tipo_z": "classico", "limiar": 3.0},
                                       detectar(m, limiar=3.0)[0].abs(), detectar(m, limiar=3.0)[1])
                      for (c, v), m in modelos_arima.items()], ignore_index=True)
p_if = res_if["parametros"].map(json.loads)
if_pr = res_if[(p_if.map(lambda d: d["config"]) == "temporal") & (p_if.map(lambda d: d["contamination"]) == 0.01)]
hampel_pr = res_h[(res_h.variante == "centrada") & res_h.variavel.isin(["temperatura", "umidade"])]

F = pd.concat([flags_instante(arima_pr, "ARIMA+Z"), flags_instante(if_pr, "IsolationForest"),
               flags_instante(hampel_pr, "Hampel")], axis=1).fillna(False).astype(bool)
F = F.reset_index()
F["municipio"] = F.codigo_ibge.map(CODIGOS)
idx = pd.DatetimeIndex(F.datetime)
F["split"] = np.select([mascara_split(idx, n) for n in SPLITS], list(SPLITS), default="?")
METODOS = ["ARIMA+Z", "IsolationForest", "Hampel"]

tab = F.groupby("split")[METODOS].agg(["sum", "mean"]).loc[list(SPLITS)]
tab.columns = [f"{m} {'n' if a == 'sum' else '%'}" for m, a in tab.columns]
for col in [c for c in tab if c.endswith("%")]: tab[col] = (100 * tab[col]).round(2)
print("Instantes sinalizados por método (4 municípios):")
display(tab)
F.groupby("municipio")[METODOS].sum()
"""

COD_COMPARA_INTER = r"""
from itertools import combinations
combo = F[METODOS].apply(lambda r: " ∩ ".join(m for m in METODOS if r[m]) or "nenhum", axis=1)
inter = combo[combo != "nenhum"].value_counts()
print("Padrões de concordância (instantes sinalizados por pelo menos um método):")
display(inter.to_frame("n").assign(pct=lambda d: (100 * d.n / d.n.sum()).round(1)))

jac = pd.DataFrame(index=METODOS, columns=METODOS, dtype=float)
for a in METODOS:
    for b in METODOS:
        u = (F[a] | F[b]).sum()
        jac.loc[a, b] = (F[a] & F[b]).sum() / u if u else np.nan
print("Índice de Jaccard entre métodos:")
jac.round(3)
"""

COD_COMPARA_TEMPO = r"""
mensal = F.set_index("datetime").groupby("municipio")[METODOS].resample("QS").sum()
fig, eixos = plt.subplots(4, 1, figsize=(13, 10), sharex=True)
for ax, mun in zip(eixos, CODIGOS.values()):
    d = mensal.loc[mun]
    for m in METODOS:
        ax.plot(d.index, d[m], lw=1.4, color=CORES[m], label=m)
    ax.set_ylabel("alertas por\ntrimestre"); ax.set_title(mun, loc="left", fontsize=10)
    for nome, (ini, fim) in SPLITS.items():
        ax.axvline(pd.Timestamp(ini, tz="UTC"), color="gray", lw=0.6, ls=":")
eixos[0].legend(ncol=3); eixos[-1].set_xlabel("trimestre")
fig.suptitle("Distribuição temporal dos alertas (linhas pontilhadas: início de treino, validação e teste)")
plt.tight_layout(); plt.show()

print("Alertas por estação do ano (todos os métodos, % do total de cada método):")
F["mes"] = idx.month
est = F["mes"].map({12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                    6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"})
(F.groupby(est)[METODOS].sum() / F[METODOS].sum() * 100).round(1)
"""

COD_COMPARA_TEMPO_EXEC = r"""
tempos = pd.Series(TEMPO, name="segundos").round(1).to_frame()
tempos["observação"] = ["grade de 16 ordens (p,q) por série + resíduos, 8 séries",
                        "2 configs × 3 contaminações, 4 municípios",
                        "3 variáveis × 24 configs × 4 municípios"]
tempos
"""

COD_CASOS = r"""
print("Casos representativos: instantes sinalizados pelos TRÊS métodos (maiores |anomalia| de temperatura)")
tres = F[F[METODOS].all(axis=1)][["codigo_ibge", "datetime", "municipio"]]
linhas = []
for _, r in tres.iterrows():
    s = series[r.codigo_ibge]
    m_t = modelos_arima[(r.codigo_ibge, "temperatura")]
    m_u = modelos_arima[(r.codigo_ibge, "umidade")]
    linhas.append({"município": r.municipio, "datetime": r.datetime,
                   "T (°C)": s.at[r.datetime, "temperatura"], "T sazonal": m_t["sazonal"][r.datetime],
                   "UR (%)": s.at[r.datetime, "umidade"], "UR sazonal": m_u["sazonal"][r.datetime],
                   "P (mm/12 h)": s.at[r.datetime, "precipitacao"]})
casos = pd.DataFrame(linhas)
casos["ΔT"] = casos["T (°C)"] - casos["T sazonal"]
display(casos.reindex(casos["ΔT"].abs().sort_values(ascending=False).index).head(12)
        .round({c: 1 for c in ["T (°C)", "T sazonal", "UR (%)", "UR sazonal", "P (mm/12 h)", "ΔT"]}))
print("Sinal da anomalia de temperatura nos casos concordantes:",
      (casos["ΔT"] < 0).sum(), "negativas,", (casos["ΔT"] > 0).sum(), "positivas")

print("\nManaus — instantes sinalizados por ano:")
F[F.codigo_ibge == 1302603].groupby(pd.DatetimeIndex(F.loc[F.codigo_ibge == 1302603, "datetime"]).year)[METODOS].sum().T
"""

MD_VIS = r"""
## 11. Visualizações
"""

COD_VIS_TRES = r"""
def flags_variavel(df_res, c, v):
    d = df_res[(df_res.codigo_ibge == c) & (df_res.variavel == v)].set_index("datetime")["outlier"]
    return d[d].index

def painel_eventos(c, jan, titulo):
    s = series[c].loc[jan]
    fig, ax = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
    # IF é multivariado: o alerta é do instante, desenhado como faixa em todos os painéis.
    t_if = flags_instante(if_pr[if_pr.codigo_ibge == c], "IF")
    t_if = t_if[t_if].index.get_level_values("datetime")
    t_if = t_if[(t_if >= s.index[0]) & (t_if <= s.index[-1])]
    for a, v in zip(ax, VARIAVEIS):
        a.plot(s.index, s[v], lw=0.8, color="gray")
        for k, t in enumerate(t_if):
            a.axvline(t, color=CORES["IsolationForest"], alpha=0.35, lw=3,
                      label="IsolationForest (instante)" if k == 0 and v == "temperatura" else None)
        if v != "precipitacao":
            ta = flags_variavel(arima_pr, c, v).intersection(s.index)
            a.scatter(ta, s.loc[ta, v], s=55, marker="^", color=CORES["ARIMA+Z"], zorder=4, label="ARIMA+Z")
        th = flags_variavel(res_h[res_h.variante == "centrada"], c, v).intersection(s.index)
        a.scatter(th, s.loc[th, v], s=40, marker="v", color=CORES["Hampel"], zorder=5,
                  label="Hampel" + (" (precipitação, à parte)" if v == "precipitacao" else ""))
        a.set_ylabel(f"{v} ({UNIDADES[v]})")
        a.legend(loc="upper left", fontsize=8, ncol=3)
    ax[-1].set_xlabel("data (UTC)")
    fig.suptitle(titulo); plt.tight_layout(); plt.show()

painel_eventos(4314902, slice("2024-04-10", "2024-06-10"), "Três métodos no mesmo período — Porto Alegre, abr–jun 2024 (enchentes no RS)")
painel_eventos(1302603, slice("2023-08-15", "2023-11-30"), "Três métodos no mesmo período — Manaus, ago–nov 2023 (seca amazônica)")
painel_eventos(2910800, slice("2022-10-01", "2022-12-15"), "Três métodos no mesmo período — Feira de Santana, out–dez 2022")
"""

COD_VIS_ESCORES = r"""
c, jan = 1302603, slice("2023-06-01", "2024-03-31")
d = F[F.codigo_ibge == c].set_index("datetime")
norm = {}
a = arima_pr[arima_pr.codigo_ibge == c].groupby("datetime")["escore"].max() / 3.0
norm["ARIMA+Z"] = a
i = if_pr[if_pr.codigo_ibge == c].set_index("datetime")
norm["IsolationForest"] = i["escore"] / json.loads(i["parametros"].iloc[0])["limiar"]
h = hampel_pr[hampel_pr.codigo_ibge == c].groupby("datetime")["escore"].max() / LIM_H
norm["Hampel"] = h

fig, ax = plt.subplots(figsize=(13, 4.5))
for m in METODOS:
    ax.plot(norm[m].loc[jan].index, norm[m].loc[jan], lw=0.7, color=CORES[m], label=m, alpha=0.85)
ax.axhline(1, color="k", ls="--", lw=1, label="limiar (escore / limiar = 1)")
ax.set_ylabel("escore normalizado pelo limiar"); ax.set_xlabel("data (UTC)")
ax.set_title(f"Escores de anomalia ao longo do tempo — {CODIGOS[c]}, jun/2023–mar/2024")
ax.legend(ncol=4); plt.tight_layout(); plt.show()
print("Correlação de Spearman entre escores normalizados (todos os instantes de Manaus):")
pd.DataFrame(norm).corr(method="spearman").round(2)
"""

COD_VIS_BARRAS = r"""
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
cont = F.groupby("municipio")[METODOS].sum()
cont.plot.bar(ax=ax[0], color=[CORES[m] for m in METODOS], rot=0)
ax[0].set_ylabel("instantes sinalizados (2015–2025)"); ax[0].set_xlabel("")
ax[0].set_title("Observações sinalizadas por método")
inter.sort_values().plot.barh(ax=ax[1], color="#555")
ax[1].set_xlabel("instantes"); ax[1].set_title("Concordância e divergência entre métodos")
plt.tight_layout(); plt.show()
"""

COD_VIS_SINT = r"""
c, var = 5208707, "temperatura"
s = series[c]
m_teste = mascara_split(s.index, "teste")
y_mod, rot = injetar_anomalias(s[var], m_teste, n=20, magnitude=5.0, seed=SEED)
z, f_ar = detectar(modelos_arima[(c, var)], y_mod, 3.0)
_, f_h, _, _ = classificar_hampel(s, var, K_H, LIM_H, "centrada", y=y_mod)
jan = slice("2024-01-01", "2024-12-31")
fig, ax = plt.subplots(figsize=(13, 4.5))
ax.plot(y_mod.loc[jan], lw=0.6, color="#bbb", label="série com injeção")
ax.plot(s.loc[jan, var], lw=0.6, color="k", label="série original")
t = rot.loc[jan].index[rot.loc[jan]]
ax.scatter(t, y_mod.loc[t], s=110, facecolor="none", edgecolor="k", lw=1.2, label="injetada (verdade)")
fa = pd.Series(f_ar.to_numpy() & rot.to_numpy(), index=s.index).loc[jan]
fh = pd.Series(f_h & rot.to_numpy(), index=s.index).loc[jan]
off = 0.9  # deslocamento vertical (°C) só para os marcadores não se sobreporem
ax.scatter(fa.index[fa], y_mod.loc[fa.index[fa]] + off, s=45, marker="v", color=CORES["ARIMA+Z"], label="detectada ARIMA+Z")
ax.scatter(fh.index[fh], y_mod.loc[fh.index[fh]] - off, s=45, marker="^", color=CORES["Hampel"], label="detectada Hampel")
ax.set_ylabel("temperatura (°C)"); ax.set_xlabel("data (UTC)")
ax.set_title(f"Anomalias sintéticas (±5σ) — {CODIGOS[c]}, 2024 ({int(rot.loc[jan].sum())} das 20 injeções do teste)\n"
             f"detectadas no teste inteiro (2024–2025): ARIMA+Z {int((f_ar & rot).sum())}/20, Hampel {int((f_h & rot.to_numpy()).sum())}/20")
ax.legend(ncol=3, fontsize=8); plt.tight_layout(); plt.show()
"""

COD_TABELA_FINAL = r"""
def media(df, filtro, col="recall"):
    return round(float(df.query(filtro)[col].mean()), 2)

linhas = {
    "ARIMA+Z": {
        "escopo": "univariado (T, UR)",
        "% sinalizado teste": round(100 * F.loc[F.split == "teste", "ARIMA+Z"].mean(), 2),
        "recall sintético 5σ": media(sint_arima, "magnitude == 5 and tipo_z == 'classico' and limiar == 3"),
        "recall sintético 3σ": media(sint_arima, "magnitude == 3 and tipo_z == 'classico' and limiar == 3"),
        "tempo (s)": round(TEMPO["ARIMA+Z"], 1),
        "detecta melhor": "quebras da dinâmica (frentes frias, chuvas súbitas)",
        "limitação": "heterocedasticidade sazonal; precipitação inadequada",
    },
    "IsolationForest": {
        "escopo": "multivariado (T, UR, P)",
        "% sinalizado teste": round(100 * F.loc[F.split == "teste", "IsolationForest"].mean(), 2),
        "recall sintético 5σ": media(sint_if, "cenario != 'multivariada_T_UR' and config == 'temporal' and contamination == 0.01"),
        "recall sintético 3σ": "n/d",
        "tempo (s)": round(TEMPO["IsolationForest"], 1),
        "detecta melhor": "estados combinados raros (seca extrema, chuva forte)",
        "limitação": "sem ordem temporal; depende de c e das entradas",
    },
    "Hampel": {
        "escopo": "univariado (T, UR; P à parte)",
        "% sinalizado teste": round(100 * F.loc[F.split == "teste", "Hampel"].mean(), 2),
        "recall sintético 5σ": media(agg_h.merge(escolha_h[CFG]), "split == 'teste' and magnitude == 5 and variante == 'centrada'"),
        "recall sintético 3σ": media(agg_h.merge(escolha_h[CFG]), "split == 'teste' and magnitude == 3 and variante == 'centrada'"),
        "tempo (s)": round(TEMPO["Hampel"], 1),
        "detecta melhor": "picos locais isolados",
        "limitação": "janela fixa; MAD=0 em séries intermitentes",
    },
}
TABELA = pd.DataFrame(linhas).T
TABELA
"""


def secoes_metodos(codigo_modulo):
    arima = codigo_modulo("metodo_arima.py").replace(
        "def experimento_sintetico(", "def experimento_sintetico_arima(")
    iforest = codigo_modulo("metodo_iforest.py").replace(
        "def experimento_sintetico(", "def experimento_sintetico_if(")
    hampel = (codigo_modulo("metodo_hampel.py")
              .replace("def experimento_sintetico(", "def experimento_sintetico_hampel(")
              .replace('ALGORITMO = "Hampel"', 'ALGORITMO_H = "Hampel"')
              .replace("LIMIARES = [2.5, 3.0, 3.5, 4.0]", "# LIMIARES: mesmos do ARIMA (2,5; 3; 3,5; 4)")
              .replace('LIMITES_FISICOS = {"temperatura": None, "umidade": (0.0, 100.0)}',
                       "# LIMITES_FISICOS: mesmos do ARIMA"))
    return [
        ("md", MD_ARIMA),
        ("code", arima),
        ("code", COD_ARIMA_RUN),
        ("md", MD_ARIMA_DIAG),
        ("code", COD_ARIMA_RESUMO),
        ("code", COD_ARIMA_SINT),
        ("md", MD_ARIMA_SINT),
        ("code", COD_ARIMA_FIG),
        ("md", MD_IFOREST),
        ("code", iforest),
        ("code", COD_IFOREST_RUN),
        ("md", MD_IFOREST_TAXAS),
        ("code", COD_IFOREST_SINT),
        ("md", MD_IFOREST_SINT),
        ("code", COD_IFOREST_DOM),
        ("md", MD_HAMPEL),
        ("code", hampel),
        ("code", COD_HAMPEL_DIURNO),
        ("code", COD_HAMPEL_RUN),
        ("code", COD_HAMPEL_ESCOLHA),
        ("code", COD_HAMPEL_EVENTOS),
        ("code", COD_HAMPEL_FIG),
        ("md", MD_COMPARA),
        ("code", COD_COMPARA_FLAGS),
        ("code", COD_COMPARA_INTER),
        ("code", COD_COMPARA_TEMPO),
        ("code", COD_COMPARA_TEMPO_EXEC),
        ("code", COD_CASOS),
        ("md", MD_VIS),
        ("code", COD_VIS_TRES),
        ("code", COD_VIS_ESCORES),
        ("code", COD_VIS_BARRAS),
        ("code", COD_VIS_SINT),
        ("md", "### Tabela comparativa"),
        ("code", COD_TABELA_FINAL),
    ]
