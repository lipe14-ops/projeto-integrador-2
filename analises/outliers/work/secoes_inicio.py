"""Seções 1–6 do notebook: objetivo, teoria, dados, EDA e pré-processamento."""

MD_TITULO = r"""
# Detecção e classificação de outliers em séries temporais climáticas: comparação entre resíduos de ARIMA, Isolation Forest e filtro de Hampel

**Projeto Integrador — plataforma de histórico climático e El Niño**

## 1. Título e objetivo

Este notebook compara três perspectivas complementares de anomalia em séries
meteorológicas de 12 em 12 horas (ERA5-Land, 2015–2025) para quatro municípios
brasileiros de climas contrastantes:

| Método | Perspectiva | Escopo |
|---|---|---|
| Resíduos de ARIMA + Z-score | desvio em relação ao comportamento temporal previsto | univariado |
| Isolation Forest | combinação atípica entre variáveis | multivariado |
| Filtro de Hampel (mediana móvel + MAD) | desvio local robusto | univariado |

O objetivo **não é contar outliers**, mas entender *quais* observações cada
método sinaliza, *por que* as classificações divergem, como dependem dos
parâmetros e quais limitações existem quando não há rótulos de verdade.

Ao longo do texto distinguem-se três conceitos:

1. **Outlier estatístico** — observação incomum em relação a um modelo ou referência.
2. **Possível erro de medição** — valor potencialmente causado por sensor, comunicação, calibração ou processamento.
3. **Evento climático extremo** — ocorrência meteorológica real, rara ou intensa.

Uma observação sinalizada é tratada como **candidata** a outlier; ela não é
automaticamente um erro.

**Execução:** `Ambiente de execução → Executar tudo`. Na primeira célula de
dados, se o CSV não estiver no ambiente, o Colab abre um diálogo de upload
(arquivo `clima_4_municipios.csv`, ~3 MB).
"""

COD_SETUP = r"""
# Dependências: no Colab todas já vêm instaladas; o pip só garante versões mínimas.
import importlib.util, subprocess, sys
for pacote, modulo in [("statsmodels>=0.14", "statsmodels"), ("scikit-learn>=1.3", "sklearn")]:
    if importlib.util.find_spec(modulo) is None:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pacote], check=True)

import json
import platform
import time
import warnings

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
import statsmodels

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 30)
plt.rcParams.update({
    "figure.figsize": (12, 4), "figure.dpi": 110, "axes.grid": True,
    "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False,
})
CORES = {"ARIMA+Z": "#1f77b4", "IsolationForest": "#d62728", "Hampel": "#2ca02c"}

versoes = {
    "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
    "matplotlib": matplotlib.__version__, "statsmodels": statsmodels.__version__,
    "scikit-learn": sklearn.__version__, "scipy": scipy.__version__,
}
print(json.dumps(versoes, indent=2))
"""

MD_INTRO = r"""
## 2. Introdução científica

Séries meteorológicas reúnem dois tipos de valor incomum que precisam ser
separados: falhas de instrumento ou de processamento, que devem ser
corrigidas, e eventos extremos reais (ondas de calor, frentes frias,
tempestades), que são justamente o que interessa estudar. Rotinas
automáticas de controle de qualidade combinam testes de limites físicos,
consistência temporal e consistência entre variáveis (DURRE *et al.*, 2010).
Pela literatura de detecção de anomalias, a definição de "anômalo" depende
do modelo de referência adotado (CHANDOLA; BANERJEE; KUMAR, 2009;
BLÁZQUEZ-GARCÍA *et al.*, 2021).

Os dados usados aqui vêm de **reanálise** (ERA5-Land; MUÑOZ-SABATER *et al.*,
2021), e não de estações. Isso tem duas consequências: (i) não existem falhas
de sensor no sentido estrito, mas existem artefatos de processamento (de
assimilação, de interpolação e do nosso próprio carregamento); (ii) a
reanálise suaviza extremos locais, então eventos reais tendem a aparecer
atenuados. Os três métodos foram escolhidos por representarem perspectivas
distintas:

- **Modelagem temporal** (ARIMA): o que é inesperado *dado o passado*.
- **Detecção multivariada** (Isolation Forest): o que é raro *na combinação* de variáveis.
- **Estatística robusta local** (Hampel): o que destoa *da vizinhança imediata*.
"""

MD_TEORIA = r"""
## 3. Fundamentação teórica

### 3.1 Resíduos de ARIMA + Z-score

Um modelo ARIMA$(p,d,q)$ descreve $y_t$ (após $d$ diferenças) como combinação
linear de $p$ valores passados e $q$ erros passados (BOX *et al.*, 2015). O
erro de previsão de um passo à frente,
$e_t = y_t - \hat y_{t\mid t-1}$, é uma medida natural de surpresa. A
literatura clássica de outliers em séries temporais (FOX, 1972; TSAY, 1988;
CHEN; LIU, 1993) mostra que um choque isolado aparece como um resíduo grande.
Padroniza-se

$$Z_t = \frac{e_t - \bar e_{\text{treino}}}{s_{e,\text{treino}}}$$

e sinaliza-se $|Z_t| > c$. A média e o desvio vêm **só do treino**, para não
haver vazamento. A estacionariedade é avaliada com ADF (DICKEY; FULLER, 1979)
e KPSS (KWIATKOWSKI *et al.*, 1992), e a adequação do modelo com Ljung–Box
(LJUNG; BOX, 1978).

### 3.2 Isolation Forest

O Isolation Forest (LIU; TING; ZHOU, 2008, 2012) constrói árvores com
partições aleatórias. Pontos raros são isolados com poucas partições, e o
escore $s(x)=2^{-E[h(x)]/c(n)}$ cresce à medida que a profundidade média
$E[h(x)]$ diminui. O método não supõe distribuição e capta combinações
atípicas entre variáveis. Por outro lado, não modela a ordem temporal, e a
proporção sinalizada depende do parâmetro `contamination`, que é uma
**hipótese** e não um fato conhecido.

### 3.3 Filtro de Hampel

Para uma janela centrada em $t$, o filtro calcula a mediana local $m_t$ e o
desvio absoluto mediano $\mathrm{MAD}_t=\operatorname{mediana}(|x_i-m_t|)$.
Com $\sigma_t\approx 1{,}4826\,\mathrm{MAD}_t$, consistente com o desvio-padrão
sob normalidade (ROUSSEEUW; CROUX, 1993; LEYS *et al.*, 2013), o desvio
robusto é

$$R_t = \frac{|x_t - m_t|}{1{,}4826\cdot \mathrm{MAD}_t},$$

e $x_t$ é candidato a outlier quando $R_t>c$ (HAMPEL, 1974; PEARSON, 2002;
PEARSON *et al.*, 2016). Mediana e MAD têm ponto de ruptura de 50%, portanto o
próprio outlier quase não contamina a referência. A limitação é que o filtro
só "enxerga" a janela.
"""

MD_DADOS = r"""
## 4. Descrição dos dados

**Fonte.** ERA5-Land (ECMWF/Copernicus), resolução de ~9 km, extraída da
célula de grade mais próxima do **centróide** de cada município. A extração
foi feita no banco PostGIS do projeto com a consulta abaixo (`COPY` em
streaming). O CSV completo tem as UFs BA, GO, RS e AM: 1.224 municípios e
9,8 milhões de linhas.

```sql
COPY (
  SELECT r.datetime, d.codigo_ibge, d.municipio, d.uf,
         r.temperatura, r.umidade, r.precipitacao
  FROM registro_climatico r
  JOIN municipio_details d USING (codigo_ibge)
  WHERE d.uf = ANY('{BA,GO,RS,AM}')
  ORDER BY r.datetime, d.uf, d.municipio
) TO STDOUT WITH (FORMAT csv, HEADER true);
```

**Recorte analisado.** Um município por UF, com climas distintos:
Manaus/AM (equatorial úmido), Feira de Santana/BA (semiárido de transição),
Goiânia/GO (tropical com estação seca) e Porto Alegre/RS (subtropical).
**Salvador foi descartado** porque todas as suas observações são nulas: a
célula ERA5-Land mais próxima do centróide é oceânica, e o ERA5-Land só
cobre terra. O mesmo acontece em outros nove municípios costeiros ou
lacustres do arquivo completo. Esse é um problema real de qualidade da
extração.

| Variável | Unidade | Definição |
|---|---|---|
| `temperatura` | °C | temperatura do ar a 2 m |
| `umidade` | % | umidade relativa, calculada a partir da temperatura e do ponto de orvalho |
| `precipitacao` | mm/12 h | acumulado do intervalo de 12 h |

Radiação solar, vento e pressão **não estão disponíveis** no banco e não são
usados.
"""

COD_DADOS = r"""
ARQUIVO = "clima_4_municipios.csv"

from pathlib import Path
if not Path(ARQUIVO).exists():
    try:
        from google.colab import files  # type: ignore
        print("Envie o arquivo", ARQUIVO)
        enviados = files.upload()
        ARQUIVO = next(iter(enviados))
    except ImportError:
        raise FileNotFoundError(f"{ARQUIVO} não encontrado no diretório atual")

df = carregar_dados(ARQUIVO)
print(df.shape)
df.head()
"""

MD_EDA = r"""
## 5. Análise exploratória
"""

COD_EDA_ESTRUTURA = r"""
print("Tipos:\n", df.dtypes, "\n")
print("Período:", df["datetime"].min(), "→", df["datetime"].max())
print("Duplicatas (município, datetime):", df.duplicated(["codigo_ibge", "datetime"]).sum())

passos = df.groupby("codigo_ibge")["datetime"].diff().dropna().value_counts()
print("Intervalos entre observações consecutivas:\n", passos, "\n")

resumo = (df.groupby(["uf", "municipio"])[VARIAVEIS]
            .agg(["count", "mean", "std", "min", "median", "max"]).round(2).T)
resumo
"""

COD_EDA_FALTANTES = r"""
faltantes = df[VARIAVEIS].isna().groupby([df["uf"], df["municipio"]]).sum()
display(faltantes)

nan_p = df[df["precipitacao"].isna()]
print("Precipitação ausente — dia do mês e hora UTC:")
print(nan_p["datetime"].dt.strftime("dia %d, %H UTC").value_counts().head())
print("\nFração de precipitação exatamente zero:",
      round((df["precipitacao"] == 0).mean(), 4),
      "| valores negativos:", int((df["precipitacao"] < 0).sum()),
      "| umidade fora de [0, 100]:", int((~df["umidade"].between(0, 100)).sum()))
"""

MD_EDA_FALTANTES = r"""
**Leitura.** Temperatura e umidade estão completas. Já a precipitação falta
sempre no **dia 1º às 00 UTC**, 132 vezes por município (11 anos × 12 meses).
O padrão sistemático indica um artefato do carregamento: o acumulado do
ERA5-Land é reiniciado na virada do mês, e o primeiro intervalo de cada
arquivo mensal não tem valor anterior para diferenciar. Esses valores são
**ausência de medição**, e não zero. Ficam como `NaN` e marcados na coluna
`precip_reset`.
"""

COD_EDA_SERIES = r"""
fig, eixos = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
for var, ax in zip(VARIAVEIS, eixos):
    for (uf, mun), g in df.groupby(["uf", "municipio"]):
        mensal = g.set_index("datetime")[var].resample("MS")
        mensal = mensal.sum(min_count=1) if var == "precipitacao" else mensal.mean()
        ax.plot(mensal.index, mensal, lw=1.2, label=f"{mun}/{uf}")
    rotulo = "acumulado mensal (mm)" if var == "precipitacao" else f"média mensal ({UNIDADES[var]})"
    ax.set_ylabel(f"{var}\n{rotulo}")
eixos[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.3))
eixos[-1].set_xlabel("data")
fig.suptitle("Séries mensais agregadas, 2015–2025", y=1.02)
plt.tight_layout(); plt.show()
"""

COD_EDA_CICLOS = r"""
aux = df.assign(mes=df["datetime"].dt.month, hora=df["datetime"].dt.hour.map({0: "00 UTC", 12: "12 UTC"}))
fig, eixos = plt.subplots(1, 3, figsize=(14, 4))
for var, ax in zip(VARIAVEIS, eixos):
    for (mun, hora), g in aux.groupby(["municipio", "hora"]):
        clim = g.groupby("mes")[var].mean()
        ax.plot(clim.index, clim, ls="-" if hora == "12 UTC" else "--", lw=1.3,
                label=f"{mun} {hora}")
    ax.set_title(var); ax.set_xlabel("mês"); ax.set_ylabel(UNIDADES[var]); ax.set_xticks(range(1, 13))
eixos[0].legend(fontsize=7, ncol=2)
fig.suptitle("Climatologia mensal por horário (linha cheia 12 UTC, tracejada 00 UTC)")
plt.tight_layout(); plt.show()
"""

MD_EDA_CICLOS = r"""
**Leitura.** Há dois ciclos fortes: o **anual** (mais marcado em Porto Alegre
na temperatura e em Goiânia na umidade, por causa da estação seca) e o
**diurno**, já que 00 UTC corresponde a 21 h local e 12 UTC a 9 h local. O
salto entre 00 e 12 UTC é maior que boa parte da variação dia a dia. Por
isso, todos os métodos têm de tratar a sazonalidade, ou vão "descobrir" o
ciclo diário como anomalia. A precipitação é inflada de zeros e muito
assimétrica, o que viola as hipóteses gaussianas do ARIMA e do Z-score.
"""

MD_PREP = r"""
## 6. Pré-processamento

As escolhas a seguir valem para os três métodos:

1. **Série regular de 12 h** por município (`asfreq`), com lacunas como `NaN` explícito e **nenhuma interpolação**. Interpolar criaria valores suaves que mascaram ou fabricam anomalias.
2. **Valores extremos não são removidos** antes da detecção, porque são exatamente o objeto de estudo.
3. Os **zeros de precipitação são mantidos** como zero observado, e os `NaN` do reset mensal ficam como ausência de medição.
4. **Divisão cronológica:** treino 2015–2021 (estimação de parâmetros), validação 2022–2023 (escolha de configurações) e teste 2024–2025 (avaliação final). Não há embaralhamento.
5. **Sazonalidade:** regressão harmônica (3 harmônicos anuais × horário 00/12 UTC) ajustada **só no treino**. Gera a componente sazonal e a anomalia $y_t - \hat s_t$ para toda a série.
6. **Anomalias sintéticas:** picos de $\pm 5\,\sigma_{\text{robusto}}$ injetados no período de teste, numa cópia da série. A série original é preservada e as posições ficam registradas. É o único cenário em que existe verdade conhecida.

O código abaixo é o módulo comum usado por todos os métodos.
"""

COD_PREP_SERIES = r"""
CODIGOS = {1302603: "Manaus/AM", 2910800: "Feira de Santana/BA", 5208707: "Goiânia/GO", 4314902: "Porto Alegre/RS"}
series = {c: preparar_serie(df, c) for c in CODIGOS}

linhas = []
for c, s in series.items():
    for nome in SPLITS:
        m = mascara_split(s.index, nome)
        linhas.append({"município": CODIGOS[c], "split": nome, "n": int(m.sum()),
                       "início": s.index[m].min().date(), "fim": s.index[m].max().date(),
                       "precip NaN": int(s.loc[m, "precipitacao"].isna().sum())})
pd.DataFrame(linhas).pivot(index="município", columns="split", values="n")
"""

COD_PREP_SAZONAL = r"""
s = series[4314902]
treino = mascara_split(s.index, "treino")
saz, anom = ajustar_sazonalidade(s["temperatura"], treino)
janela = slice("2023-01-01", "2023-03-31")

fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
ax[0].plot(s.loc[janela, "temperatura"], lw=0.8, label="observado")
ax[0].plot(saz.loc[janela], lw=1.5, label="componente sazonal (ajustada no treino)")
ax[0].set_ylabel("temperatura (°C)"); ax[0].legend()
ax[1].plot(anom.loc[janela], lw=0.8, color="k")
ax[1].axhline(0, color="gray", lw=0.8)
ax[1].set_ylabel("anomalia (°C)"); ax[1].set_xlabel("data")
fig.suptitle("Porto Alegre — decomposição sazonal (validação, jan–mar 2023)")
plt.tight_layout(); plt.show()

for c, s in series.items():
    tr = mascara_split(s.index, "treino")
    r2 = {v: 1 - ajustar_sazonalidade(s[v], tr)[1][tr].var() / s.loc[tr, v].var() for v in ["temperatura", "umidade"]}
    print(f"{CODIGOS[c]:22s} R² sazonal (treino): " + ", ".join(f"{k}={v:.2f}" for k, v in r2.items()))
"""


def secoes_inicio(codigo_modulo):
    return [
        ("md", MD_TITULO),
        ("code", COD_SETUP),
        ("md", MD_INTRO),
        ("md", MD_TEORIA),
        ("md", MD_DADOS),
        ("md", "### Módulo comum\n\nFunções de carga, regularização, divisão temporal, "
               "sazonalidade, injeção sintética e formato padrão de saída."),
        ("code", codigo_modulo("common.py")),
        ("code", COD_DADOS),
        ("md", MD_EDA),
        ("code", COD_EDA_ESTRUTURA),
        ("code", COD_EDA_FALTANTES),
        ("md", MD_EDA_FALTANTES),
        ("code", COD_EDA_SERIES),
        ("code", COD_EDA_CICLOS),
        ("md", MD_EDA_CICLOS),
        ("md", MD_PREP),
        ("code", COD_PREP_SERIES),
        ("code", COD_PREP_SAZONAL),
    ]
