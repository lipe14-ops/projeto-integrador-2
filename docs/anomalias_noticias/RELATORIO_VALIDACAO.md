# Relatório de validação científica e técnica

Execuções reais em 08/11/2026 sobre a base local (ERA5-Land, 2015–2025, 12 h →
diário). Os identificadores das execuções servem para auditoria em
`GET /api/climate/runs/{id}` ou `cli show --run`.

| Município | Detecção | Investigação |
|---|---|---|
| Porto Alegre/RS | `ccbdd15c-e0b2-4eec-b863-87a0d83775e6` | `64f5cc22-a2a5-4da2-93cb-065749107d67` |
| Rio Verde/GO | `f54cfda2-6f43-4ed9-a239-149ad9948cc0` | (ver §4) |

## 1. Dados (Cientista de Dados)

| | Porto Alegre | Rio Verde |
|---|---|---|
| dias (01/01/2015–30/12/2025) | 4017 | 4017 |
| dias ausentes | 131 (3,3%) | 131 (3,3%) |
| dias com chuva zero | 6,6% | 10,0% |
| negativos / implausíveis / duplicatas | 0 / 0 / 0 | 0 / 0 / 0 |

Todos os dias ausentes têm a mesma origem: o último dia de cada mês fica
incompleto porque a observação de 00 UTC do dia 1º não foi carregada (falha de
carga já registrada na análise exploratória). Esses dias ficam como NaN e não
são preenchidos com zero; o filtro de Kalman os trata como falta de
observação.

## 2. Modelo e diagnósticos

| | Porto Alegre | Rio Verde |
|---|---|---|
| ADF p / KPSS p (treino 2015–2016) | 0,000 / 0,073 → d = 0 | 0,015 / 0,100 → d = 0 |
| modelo escolhido por BIC | ARIMA(0,0,1), sem Fourier | ARIMA(2,0,1), sem Fourier |
| BIC sem / com Fourier (melhor ordem) | 2056,5 / 2086,2 | 1530,0 / 1539,4 |
| período pontuado (fora da amostra) | 2017–2025, 3179 dias | 2017–2025, 3179 dias |
| média / desvio de Z | −0,01 / 1,01 | −0,01 / 1,00 |
| assimetria / curtose em excesso de Z | 1,13 / 0,54 | 0,65 / 1,34 |
| Ljung-Box p (lag 1 / 7 / 30) | 0,53 / 0,59 / 0,05 | 0,84 / 0,38 / 0,02 |
| taxa Z > 3 (esperado sob normalidade: 0,135%) | 0,53% (3,96×) | 0,79% (5,83×) |
| estabilidade dos parâmetros (9 reajustes) | ma.L1 entre 0,332 e 0,381 | ar.L1 entre 1,427 e 1,475; ma.L1 entre −0,919 e −0,905 |
| ajustes de máxima verossimilhança | 26 | 26 |

O que esses números mostram:

- **Calibração.** Z tem média ≈ 0 e desvio ≈ 1 fora da amostra, ou seja, os
  resíduos de referência (passado) descrevem bem o futuro. Os parâmetros
  variam pouco entre reajustes anuais, então o modelo é estável.
- **Autocorrelação.** Não há autocorrelação residual nos lags 1 e 7. No lag 30
  há um sinal fraco (p = 0,02 em Rio Verde), compatível com variações
  intrassazonais que o ARMA de baixa ordem não captura.
- **Não normalidade.** Os resíduos têm assimetria positiva (chuva). Por isso
  |Z| > 3 aparece 4 a 6 vezes mais do que sob normalidade: o limiar 3 funciona
  como critério operacional, não como probabilidade de 0,135%.
- **SARIMA e sazonalidade.** SARIMA com período 365 é inviável (estado de
  centenas de dimensões). A alternativa, regressão de Fourier com erros ARMA,
  foi avaliada por BIC e **perdeu nos dois municípios**. Em Rio Verde o AR(2) é
  quase integrado (ar1 ≈ 1,45, ar2 ≈ −0,46): o nível sazonal é acompanhado
  como uma componente que varia devagar, e os 6 parâmetros extras de Fourier
  não compensam a penalidade do BIC. O critério fica configurável
  (`--seasonal fourier`).
- **Sem vazamento.** Para cada bloco anual, o treino termina antes do início
  do bloco. O teste `test_no_future_information_leaks_into_past_scores` mostra
  que truncar a série no meio de um ano não altera nenhum Z anterior.

## 3. Revisão científica das anomalias (Climatologista e Meteorologista)

### Porto Alegre — 35 anomalias (17 ARIMA + 18 de acumulado), nenhuma rejeitada

| Ano | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| anomalias | 4 | 1 | 1 | 5 | 2 | 3 | **10** | 5 | 4 |

- 2023 concentra 10 anomalias, **todas** em meses com ONI ≥ 0,5 (El Niño). É coerente com
  a teleconexão conhecida (El Niño favorece chuva acima da média no Sul), mas é
  **contexto, não atribuição causal**: 9 anos não bastam para inferência.
- O ARIMA marcou dias de 24 a 146 mm (máximo em 04/09/2023, ciclone
  extratropical). Duas anomalias do ARIMA (14/07/2022, 23,9 mm; 21/03/2024,
  32,5 mm) ficaram como `within_normal_variability` para o Climatologista e
  `plausible_significant_event` para o Meteorologista. Com pareceres
  divergentes, foram mantidas para investigação, com a ressalva registrada.
- **Limitação estrutural do ARIMA (achado principal).** A enchente de
  abril/maio de 2024 teve chuva de 20 a 36 mm por dia durante cerca de 10 dias
  em Porto Alegre, nenhum dia extremo isoladamente, e o ARIMA passa a prever a
  persistência. O detector **não marcou** os dias de 26/04 a 05/05/2024.
  O detector suplementar de acumulados os capturou: **02/05/2024** (5 dias,
  103 mm ≥ P99) e **12/05/2024**. Também capturou 05/09/2023 (162,9 mm em
  5 dias, **recorde** da série), 16/06/2023 e 18/11/2023.
- Meteorologista: 18 eventos `plausible_extreme_event` e 17
  `plausible_significant_event`. As hipóteses de mecanismo (frente,
  ciclone extratropical, CCM) ficam registradas como **não confirmadas**.

### Rio Verde — 41 anomalias (27 ARIMA + 14 de acumulado), 15 rejeitadas

Rio Verde (Cerrado) tem estação seca marcada. **13 das 27 anomalias do ARIMA
são chuvas moderadas (7,7 a 19 mm) nas transições de estação**: 9 em
setembro/outubro (primeiras chuvas depois da estiagem) e 4 em abril/maio (fim
da estação chuvosa). São estatisticamente surpreendentes depois de dias secos,
mas habituais no local e sem significância meteorológica. Climatologista e Meteorologista as rejeitaram,
fazendo a separação pedida entre anomalia estatística e evento extremo. Outras
2 foram rejeitadas pelo Cientista de Dados como artefato (traço < 1 mm com
Z < −3).

Na primeira execução (`dc50cfc8…`), as chuvas de junho de 2021 e 2022 (14 e
11 mm, em plena estação seca) também foram rejeitadas. O percentil sazonal
entre dias chuvosos não existia por falta de amostra e o veredito caía em
`within_normal_variability`. A regra foi corrigida: o percentil passou a usar
todos os dias da época (teste
`test_dry_season_rain_is_unusual_for_season_not_normal`). Na execução atual
elas aparecem como `unusual_for_season`. As duas execuções continuam no banco
para auditoria.

<!-- SEÇÃO DE NOTÍCIAS: preenchida após a investigação -->
