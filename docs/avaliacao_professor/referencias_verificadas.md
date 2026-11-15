# Referências verificadas — Clima Brasil

Levantamento bibliográfico para responder a duas perguntas do professor:
(A) existem trabalhos científicos que usam ARIMA + Z-score aplicado aos resíduos?
(B) qual a diferença entre "anomalia estatística", "evento meteorológico extremo", "evento climático extremo" e "evento de alto impacto"?

**Como verificamos.** Cada DOI foi conferido na API do Crossref (`https://api.crossref.org/works/<DOI>`): título, periódico, ano, volume e páginas. Os resumos foram lidos na OpenAlex, na Semantic Scholar, na página da editora ou no texto completo, conforme indicado na tabela final. Documentos sem DOI (IPCC, OMM) foram conferidos no PDF oficial baixado. As notas descrevem só o que lemos. Quando um detalhe vem de fonte secundária, isso está dito na nota.

Verificação feita em 14/11/2026. Referências no estilo ABNT NBR 6023.

---

## A. Resíduos de modelos ARIMA/AR + limiar padronizado (Z-score ou intervalo de predição)

**Equivalência usada na classificação.** Um intervalo de predição de um passo, ŷ_t|t−1 ± c·σ̂, com σ̂ estimado pelo desvio-padrão dos resíduos, sinaliza exatamente os mesmos pontos que |Z_t| > c, onde Z_t = e_t/σ̂ e e_t = y_t − ŷ_t|t−1. Hyndman e Athanasopoulos (2021, seção 5.5) dão essa forma explicitamente. Por isso, trabalhos que sinalizam "observação fora do intervalo de predição" entram aqui como limiar k·σ sobre o erro de previsão.

Cada trabalho recebe uma de três classificações:
- **[Z/k·σ]**: aplica Z ou limiar k·σ (ou intervalo de predição) sobre resíduos ou erros de previsão.
- **[outro critério]**: usa ARIMA/AR, mas decide por outro critério.
- **[fundamentação]**: fundamentação geral.

### A.1 Trabalhos que aplicam limiar padronizado sobre erros de previsão / resíduos

1. HILL, D. J.; MINSKER, B. S. Anomaly detection in streaming environmental sensor data: a data-driven modeling approach. **Environmental Modelling & Software**, v. 25, n. 9, p. 1014–1022, 2010. DOI: https://doi.org/10.1016/j.envsoft.2009.08.010.
   **[Z/k·σ — dado meteorológico]**
   - (a) Ajusta modelos autorregressivos univariados orientados a dados, de quatro tipos: ingênuo, de agrupamento, perceptron e rede neural. Segundo o resumo, "the method is based on an autoregressive data-driven model of the data stream and its corresponding prediction interval".
   - (b) e (c) Classifica como anômala a observação que cai fora do intervalo de predição (IP) da previsão de um passo.
   - Aplicação: dados de velocidade do vento de sensores em Corpus Christi (Texas, EUA). O melhor resultado foi o perceptron multicamadas com substituição dos pontos anômalos.
   - Ressalva: o resumo não traz a fórmula exata do IP. Não pudemos ler o texto completo, que é fechado.
   - Lido em: resumo na página Illinois Experts e descrição na revisão de Blázquez-García et al. (2021).

2. YU, Y.; ZHU, Y.; LI, S.; WAN, D. Time series outlier detection based on sliding window prediction. **Mathematical Problems in Engineering**, v. 2014, artigo 879736, 2014. DOI: https://doi.org/10.1155/2014/879736.
   **[Z/k·σ — dado hidrológico]**
   - (a) Ajusta um modelo de previsão sobre uma janela deslizante do histórico.
   - (b) e (c) Considera *outlier* a observação fora de um "prediction confidence interval (PCI)", calculado a partir do valor previsto e de um coeficiente de confiança.
   - Aplicação: séries hidrológicas reais.
   - Ressalva: o resumo não diz qual é o modelo de previsão. Uma fonte secundária (MDPI *Water*, 2021) o descreve como autorregressivo. Não conseguimos baixar o texto completo para confirmar se é AR ou ARIMA.

3. HYNDMAN, R. J.; ATHANASOPOULOS, G. **Forecasting: principles and practice**. 3. ed. [S. l.]: OTexts, 2021. Disponível em: https://otexts.com/fpp3/. Acesso em: 14 nov. 2026.
   **[fundamentação do Z/k·σ]**
   - A seção 5.5 ("Distributional forecasts and prediction intervals") define o IP como ŷ ± c·σ̂_h. Para h = 1, σ̂ é estimado pelo desvio-padrão dos resíduos (Eq. 5.1). A Tabela 5.1 dá os multiplicadores: 1,96 para 95% e 2,58 para 99%.
   - O texto avisa que esses multiplicadores supõem resíduos normais e não correlacionados. Sem normalidade, o IP "may be inaccurate".
   - É o livro-texto de referência para a equivalência IP ↔ |Z| > c.

3b. LEIGH, C.; ALSIBAI, O.; HYNDMAN, R. J.; KANDANAARACHCHI, S.; KING, O. C.; McGREE, J. M.; NEELAMRAJU, C.; STRAUSS, J.; TALAGALA, P. D.; TURNER, R. D. R.; MENGERSEN, K.; PETERSON, E. E. A framework for automated anomaly detection in high frequency water-quality data from in situ sensors. **Science of the Total Environment**, v. 664, p. 885–898, 2019. DOI: https://doi.org/10.1016/j.scitotenv.2019.02.085.
   **[Z/k·σ — dado ambiental, ARIMA]** — **referência principal para o método do projeto.**
   - (a) Ajusta ARIMA (e regressão com erros ARIMA) a séries de turbidez, condutividade e **nível de rio** de rios que deságuam na Grande Barreira de Corais.
   - (b) e (c) Calcula a previsão de **um passo à frente** e marca como anomalia a observação fora do intervalo x̃ ± t(α/2, T−k)·s, com *s* = raiz da média dos quadrados dos **resíduos do ARIMA no treino** e IP de 99%. Equivale a |resíduo/s| > ≈2,6, isto é, um Z-score sobre o resíduo.
   - Resultados: acurácia > 0,80 e taxa de erro < 0,20 nos métodos de regressão; ARIMA com PPV de 0,93 na condutividade (sítio PR); picos isolados e mudanças de nível, as anomalias prioritárias, foram em sua maioria classificados corretamente.
   - Conclusão literal do resumo: "a combination of methods will provide optimal performance in terms of correct anomaly detection, whilst minimizing false detection rates".
   - Verificado: Crossref (metadados) e texto completo do pré-print arXiv:1810.13076, seção 2.4 e resultados, lidos em 14/11/2026.

4. ILCHUK, N.; VERES, O. Anomaly detection in cyber-physical systems: a SWaT data-based mathematical modeling approach. **Vìsnik Nacìonal'nogo universitetu "L'vìvs'ka politehnìka". Serìâ Ìnformacìjnì sistemi ta merežì**, v. 19, p. 76–87, 2026. DOI: https://doi.org/10.23939/sisn2026.19.076.
   **[resíduos de ARIMA — dado industrial]**
   - ARIMA(3,0,5) marca resíduos de previsão grandes num sensor de nível de água (base SWaT); compara com um Z-score em janela deslizante sobre os dados brutos. Pelo resumo (Crossref), o Z-score **não** é aplicado sobre os resíduos, e o limiar do ARIMA não é informado. Uso: exemplo recente do princípio.

### A.2 Base estatística clássica: detecção de outliers em séries ARIMA

4. FOX, A. J. Outliers in time series. **Journal of the Royal Statistical Society: Series B (Methodological)**, v. 34, n. 3, p. 350–363, 1972. DOI: https://doi.org/10.1111/j.2517-6161.1972.tb00912.x.
   **[fundamentação]**
   - Propõe dois modelos de *outlier* em séries temporais (os que depois ficaram conhecidos como aditivo e inovacional).
   - Deriva critérios de razão de verossimilhança e compara o poder desses testes com a abordagem usada até então.
   - É a origem formal de testar observações contra um modelo de série temporal. O resumo não fala em Z-score.

5. TSAY, R. S. Outliers, level shifts, and variance changes in time series. **Journal of Forecasting**, v. 7, n. 1, p. 1–20, 1988. DOI: https://doi.org/10.1002/for.3980070102.
   **[fundamentação — resíduos]**
   - Detecta *outliers*, mudanças de nível e mudanças de variância em séries univariadas.
   - Segundo o resumo, usa "only the least squares techniques and residual variance ratios".
   - Aplicado a três conjuntos de dados reais.
   - Trabalha sobre resíduos do modelo. O resumo não detalha o valor crítico usado.

6. CHEN, C.; LIU, L.-M. Joint estimation of model parameters and outlier effects in time series. **Journal of the American Statistical Association**, v. 88, n. 421, p. 284–297, 1993. DOI: https://doi.org/10.1080/01621459.1993.10594321.
   **[fundamentação — ARIMA + estatística de teste]**
   - Procedimento iterativo que detecta quatro tipos de *outlier* e estima em conjunto os parâmetros do modelo e os efeitos dos *outliers*.
   - Estuda por simulação o comportamento amostral das estatísticas de teste e discute os efeitos espúrio e de mascaramento.
   - É o método de base do pacote R `tsoutliers`.
   - Ressalva: a estatística padronizada comparada a um valor crítico vem do conhecimento do método, não do resumo lido.

### A.3 Revisões gerais (fundamentação)

7. BLÁZQUEZ-GARCÍA, A.; CONDE, A.; MORI, U.; LOZANO, J. A. A review on outlier/anomaly detection in time series data. **ACM Computing Surveys**, v. 54, n. 3, p. 1–33, 2021. DOI: https://doi.org/10.1145/3444690.
   **[fundamentação]**
   - Revisão com taxonomia de detecção não supervisionada de *outliers* em séries temporais. Lemos o texto completo no arXiv (2002.04236).
   - A seção sobre *outliers* pontuais formaliza a regra |x_t − x̂_t| > τ para modelos de predição, que usam só o passado.
   - Cita como exemplos Hill e Minsker (2010), com modelo AR, e Zhang et al. (2012), com ARIMA. Diz que ambos obtêm intervalos de confiança das previsões e, portanto, "implicitly define the value of τ".
   - Também cita trabalhos que aplicam testes de hipótese sobre os resíduos de ARIMA/ARX (Akouemo; Povinelli, 2014, 2016, 2017).

8. CHANDOLA, V.; BANERJEE, A.; KUMAR, V. Anomaly detection: a survey. **ACM Computing Surveys**, v. 41, n. 3, artigo 15, p. 1–58, 2009. DOI: https://doi.org/10.1145/1541880.1541882.
   **[fundamentação]**
   - Revisão geral de detecção de anomalias, organizada por categoria de técnica, com as hipóteses de cada uma, uma técnica básica de referência, vantagens, desvantagens e custo computacional.
   - Útil para enquadrar o método do projeto como detecção estatística paramétrica.

### A.4 Trabalhos com ARIMA ou modelo, mas outro critério de decisão

9. ZHOU, Y.; QIN, R.; XU, H.; SADIQ, S.; YU, Y. A data quality control method for seafloor observatories: the application of observed time series data in the East China Sea. **Sensors**, v. 18, n. 8, artigo 2628, 2018. DOI: https://doi.org/10.3390/s18082628.
   **[outro critério]**
   - (a) Ajusta ARIMA em janela deslizante, com limpeza dos dados de entrada, para controle de qualidade de dados oceanográficos de observatório submarino (pH e CTD).
   - (b) e (c) Marca como suspeito o ponto cujo **erro relativo** entre previsto e observado passa de um limiar fixo (0,065% para o pH). Não é um limiar k·σ.
   - Os autores comparam com os métodos clássicos de 2 e 3 desvios-padrão e relatam que o ARIMA equilibra melhor precisão e *recall*.
   - Atenção: Blázquez-García et al. (2021) descrevem este trabalho como baseado em "prediction interval", mas o texto completo (PMC6111880) mostra erro relativo.

10. ZHANG, Y.; HAMM, N. A. S.; MERATNIA, N.; STEIN, A.; VAN DE VOORT, M.; HAVINGA, P. J. M. Statistics-based outlier detection for wireless sensor networks. **International Journal of Geographical Information Science**, v. 26, n. 8, p. 1373–1392, 2012. DOI: https://doi.org/10.1080/13658816.2012.654493.
    **[provável Z/k·σ, não confirmado]**
    - Segundo o resumo, a metodologia combina análise de séries temporais e geoestatística. Foi aplicada a dados reais de rede de sensores nos Alpes suíços.
    - O uso de ARIMA com intervalo de confiança vem só da revisão de Blázquez-García et al. (2021). O resumo não o menciona.

11. AKOUEMO, H. N.; POVINELLI, R. J. Probabilistic anomaly detection in natural gas time series data. **International Journal of Forecasting**, v. 32, n. 3, p. 948–956, 2016. DOI: https://doi.org/10.1016/j.ijforecast.2015.06.001.
    **[outro critério]**
    - Segundo o resumo (lido via registros RePEc e bibliotecários), usa regressão linear com entradas meteorológicas para sinalizar anomalias de consumo de gás.
    - Depois filtra falsos positivos e classifica as anomalias com um classificador bayesiano de máxima verossimilhança.
    - Fornece a verossimilhança de cada ponto ser anômalo.

12. DURRE, I.; MENNE, M. J.; GLEASON, B. E.; HOUSTON, T. G.; VOSE, R. S. Comprehensive automated quality assurance of daily surface observations. **Journal of Applied Meteorology and Climatology**, v. 49, n. 8, p. 1615–1633, 2010. DOI: https://doi.org/10.1175/2010JAMC2375.1.
    **[outro critério — meteorologia, precipitação diária]**
    - Descreve os 19 testes automáticos de controle de qualidade do GHCN-Daily para temperatura, **precipitação diária**, neve e profundidade de neve.
    - Entre eles há testes de *outliers* climatológicos e de inconsistência temporal e espacial. Os limiares foram calibrados por revisão manual para minimizar falsos positivos (1–2%).
    - Não usa ARIMA. É a referência operacional mais próxima para detectar valores diários de chuva fora do padrão local, com a preocupação explícita de **não** marcar eventos meteorológicos reais como erro.

**Conclusão da seção A.** A literatura sustenta o princípio. Detectar anomalias por um limiar de c desvios-padrão sobre o erro de previsão de um passo de um modelo AR/ARIMA, ou pelo intervalo de predição equivalente, é prática documentada:
- em estatística de séries temporais: Fox, 1972; Tsay, 1988; Chen; Liu, 1993;
- em livros-texto: Hyndman; Athanasopoulos, 2021;
- em dados ambientais: Hill; Minsker, 2010 (vento); Yu et al., 2014 (hidrologia).

O trabalho mais próximo do método do projeto é **Leigh et al. (2019)**, que aplica exatamente o limiar padronizado sobre o resíduo de previsão de um passo do ARIMA em dados ambientais de rios. **Não encontramos** nenhum trabalho revisado por pares que aplique ARIMA + Z-score sobre resíduos para detectar anomalias de **precipitação diária**, nem com dados de reanálise, nem no Brasil. Os trabalhos com precipitação diária (Durre et al., 2010) usam outros testes. Essa aplicação deve ser apresentada como **adaptação experimental** de um método estabelecido.

---

## A.2 Limitações documentadas

13. WILKS, D. S. **Statistical methods in the atmospheric sciences**. 4. ed. Amsterdam: Elsevier, 2019. ISBN 978-0-12-815823-4. DOI: https://doi.org/10.1016/C2017-0-03921-6.
    - Livro-texto de referência em estatística atmosférica. O Crossref confirma a 4ª edição (ISBN 9780128158234; capítulo "Preface to the Fourth Edition", DOI 10.1016/B978-0-12-815823-4.09991-0).
    - Uso no projeto: fundamentar que a precipitação diária é assimétrica, limitada em zero e com muitos dias secos. Por isso costuma ser modelada por distribuições não gaussianas (por exemplo, a gama) e por modelos de ocorrência e intensidade, e não por resíduos normais.
    - Ressalva: não conferimos o número exato do capítulo. Citar o capítulo de distribuições paramétricas após consultar o livro.

14. COLES, S. **An introduction to statistical modeling of extreme values**. London: Springer, 2001. (Springer Series in Statistics). DOI: https://doi.org/10.1007/978-1-4471-3675-0.
    - Referência padrão de teoria de valores extremos (GEV, GPD/*peaks-over-threshold*, níveis de retorno).
    - Fundamenta a crítica de que um limiar Z > 3 sob hipótese gaussiana não representa bem a cauda da precipitação. A alternativa para caudas é ajustar a distribuição de excessos acima de um limiar alto.
    - A OMM-1310 (seção B) também cita a GEV para limiares de precipitação extrema.

15. Também documentam limitações:
    - Hyndman e Athanasopoulos (2021, seção 5.5): IPs com multiplicadores normais exigem resíduos normais e não correlacionados.
    - Zhou et al. (2018): os métodos de 2 e 3 desvios-padrão erram muito em precisão ou em *recall*.
    - Durre et al. (2010): limiares precisam ser calibrados para não marcar eventos reais como erro.

**Implicações para o projeto.** Estas são inferências nossas, apoiadas nas referências acima:
- A transformação log1p reduz, mas não elimina, a assimetria e o excesso de zeros.
- A variância dos resíduos muda com a estação (heteroscedasticidade sazonal). Um σ único calculado no treino tende a gerar mais alarmes na estação chuvosa.
- A taxa nominal de 0,13% para Z > 3 não vale sem normalidade.
- Recomendação: relatar a taxa empírica de alertas e comparar com o limiar por percentil (P99), que o projeto já usa no detector suplementar.

---

## B. Definições de anomalia, extremo e impacto

16. IPCC. Annex II: Glossary. *In*: PÖRTNER, H.-O. et al. (ed.). **Climate change 2022: impacts, adaptation and vulnerability**. Contribution of Working Group II to the Sixth Assessment Report of the IPCC. Cambridge: Cambridge University Press, 2022. p. 2897–2930. DOI: https://doi.org/10.1017/9781009325844.029. PDF verificado: https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_Annex-II.pdf.
    Definições, em citação literal:
    - **Anomaly** (p. 2900): "The deviation of a variable from its value averaged over a reference period."
    - **Extreme weather event** (p. 2908): "An event that is rare at a particular place and time of year. Definitions of 'rare' vary, but an extreme weather event would normally be as rare as or rarer than the 10th or 90th percentile of a probability density function estimated from observations."
    - **Climate extreme (extreme weather or climate event)** (p. 2902): "The occurrence of a value of a weather or climate variable above (or below) a threshold value near the upper (or lower) ends of the range of observed values of the variable." Continua: "When a pattern of extreme weather persists for some time, such as a season, it may be classified as an extreme climate event […]".
    - **Compound weather/climate events** (p. 2904): "[…] refer to the combination of multiple drivers and/or hazards that contributes to societal and/or environmental risk (Zscheischler et al., 2018)."
    - O glossário do AR5 (IPCC, 2014, Synthesis Report, Annex II) traz a mesma definição de *extreme weather event*, conferida em https://www.ipcc.ch/site/assets/uploads/2019/01/SYRAR5-Glossary_en.pdf.

17. SENEVIRATNE, S. I. et al. Changes in climate extremes and their impacts on the natural physical environment. *In*: FIELD, C. B. et al. (ed.). **Managing the risks of extreme events and disasters to advance climate change adaptation**. A Special Report of Working Groups I and II of the IPCC (SREX). Cambridge: Cambridge University Press, 2012. p. 109–230. DOI: https://doi.org/10.1017/CBO9781139177245.006.
    - O sumário executivo (p. 111) e a seção 3.1.2 (p. 116) distinguem o extremo **estatístico** do **impacto**. Em citação literal: "weather or climate events, even if not extreme in a statistical sense, can still lead to extreme conditions or impacts […]" e "Conversely, not all extremes necessarily lead to serious impacts."
    - Também afirmam que alguns extremos (secas, cheias) resultam da **acumulação** de eventos individualmente não extremos. Isso justifica conceitualmente o detector de acumulados de 3 e 5 dias.
    - Os limiares típicos citados são probabilidades abaixo de 10%, 5% ou 1% num período de referência.

18. SENEVIRATNE, S. I. et al. Weather and climate extreme events in a changing climate. *In*: MASSON-DELMOTTE, V. et al. (ed.). **Climate change 2021: the physical science basis**. Contribution of Working Group I to the Sixth Assessment Report of the IPCC. Cambridge: Cambridge University Press, 2021. p. 1513–1766. DOI: https://doi.org/10.1017/9781009157896.013.
    - Capítulo 11 do AR6 WG1: avaliação mais recente sobre extremos, incluindo precipitação intensa e eventos compostos.
    - O Crossref confirma título, livro e páginas. Usamos a referência para contexto e não extraímos citações literais dela.

19. WORLD METEOROLOGICAL ORGANIZATION. **Guidelines on the definition and characterization of extreme weather and climate events**. Geneva: WMO, 2023. (WMO-No. 1310). ISBN 978-92-63-11310-8. PDF verificado: https://digitallibrary.un.org/record/4012890/files/Guidelines.pdf.
    - Segundo a p. 3, a definição de extremo deve ser **independente do impacto** ("Its definition should be impact-independent"). O evento é caracterizado por **magnitude** (afastamento de uma linha de base ou limiar), **duração** e **extensão**. A informação de impacto não entra na definição, mas deve ser registrada no monitoramento.
    - Para precipitação (p. 7), um evento é extremo por (1) passar de um limiar fixo associado a impacto ou (2) ser raro, por percentil (P90, P95, P99) ou período de retorno, inclusive via GEV.
    - Definição proposta: "a marked and unusual precipitation event occurring during a period of hours to a longer period of several days, with total precipitation largely exceeding local average conditions of that period."
    - O limiar P99 de acumulados de vários dias do projeto se encaixa diretamente nessa definição.

20. WORLD METEOROLOGICAL ORGANIZATION. **WMO guidelines on multi-hazard impact-based forecast and warning services**. Geneva: WMO, 2015. (WMO-No. 1150).
    - Existência verificada pela carta-circular oficial da OMM de 12 jun. 2015: https://extranet.wmo.int/edistrib_exped/grp_tc_caem/grp_prs/_en/2015/2015_06/2015-06-12-PR-6852-WDS-PWS-WMO-No-1150_en.pdf.
    - O documento apresenta a mudança de previsões centradas no fenômeno para serviços centrados no **impacto**. A circular motiva isso pela distância entre prever bem um evento severo e compreender seus impactos potenciais.
    - Serve de referência para o conceito de evento de **alto impacto**, que se define pelas consequências e não pela raridade estatística.

21. ZHANG, X.; ALEXANDER, L.; HEGERL, G. C.; JONES, P.; KLEIN TANK, A.; PETERSON, T. C.; TREWIN, B.; ZWIERS, F. W. Indices for monitoring changes in extremes based on daily temperature and precipitation data. **WIREs Climate Change**, v. 2, n. 6, p. 851–870, 2011. DOI: https://doi.org/10.1002/wcc.147.
    - Revisa os índices de extremos do ETCCDI, calculados a partir de dados diários de temperatura e precipitação (por exemplo, R95p, R99p, Rx1day, Rx5day).
    - Explica a passagem de limiares físicos absolutos para limiares **relativos** (percentis locais) e as dificuldades de gerar índices em grade, já que a média espacial amortece extremos.
    - Este último ponto também vale para reanálises como o ERA5-Land.

22. STEPHENSON, D. B. Definition, diagnosis, and origin of extreme weather and climate events. *In*: DIAZ, H. F.; MURNANE, R. J. (ed.). **Climate extremes and society**. Cambridge: Cambridge University Press, 2008. p. 11–23. DOI: https://doi.org/10.1017/CBO9780511535840.004.
    - Capítulo conceitual sobre como definir e diagnosticar extremos. Lemos apenas o parágrafo de abertura disponível.
    - Os editores do livro (Diaz; Murnane) vêm do nosso conhecimento e não aparecem nos metadados do Crossref. Conferir antes de usar.

23. ZSCHEISCHLER, J.; WESTRA, S.; VAN DEN HURK, B. J. J. M.; SENEVIRATNE, S. I.; WARD, P. J.; PITMAN, A.; AGHAKOUCHAK, A.; BRESCH, D. N.; LEONARD, M.; WAHL, T.; ZHANG, X. Future climate risk from compound events. **Nature Climate Change**, v. 8, n. 6, p. 469–477, 2018. DOI: https://doi.org/10.1038/s41558-018-0156-3.
    - Metadados confirmados no Crossref (11 autores). O resumo é fechado e não foi lido.
    - O IPCC (2022, Annex II, p. 2904) cita este artigo como fonte da definição de eventos compostos: combinação de múltiplos fatores e/ou ameaças que contribui para risco social ou ambiental.

**Síntese das diferenças conceituais** (nossa, baseada nas fontes 16–23):

| Termo | Critério | O que o projeto detecta |
|---|---|---|
| Anomalia estatística | Desvio em relação a uma referência: média de um período (IPCC) ou, no nosso caso, previsão de um modelo. Não implica raridade extrema nem impacto. | Z > 3 sobre o resíduo de previsão do ARIMA: é **anomalia estatística condicional** ao modelo. |
| Evento meteorológico extremo | Raridade em escala de tempo meteorológica (horas a dias), para o local e a época do ano: tipicamente além de P90/P10 (IPCC) ou P95/P99 (OMM-1310). Independente do impacto (OMM). | Acumulados de 3 e 5 dias acima do P99 local se aproximam desta definição. |
| Evento climático extremo | Padrão extremo que persiste (estação ou mais) ou cujo total ou média é extremo, como seca ou estação muito chuvosa (IPCC). | Não é detectado diretamente: exigiria agregação mensal ou sazonal. |
| Evento de alto impacto | Definido pelas consequências (danos, mortes, interrupções), que dependem de exposição e vulnerabilidade. Pode ser causado por evento não extremo, e nem todo extremo gera impacto (SREX; OMM-1150). Eventos compostos são um caso particular (Zscheischler et al., 2018). | Não é detectado sem dados de impacto. O cruzamento com notícias de desastres, já feito no Explorar, é um passo nessa direção. |

---

## C. Sazonalidade e ENSO no Brasil

24. GRIMM, A. M.; TEDESCHI, R. G. ENSO and extreme rainfall events in South America. **Journal of Climate**, v. 22, n. 7, p. 1589–1609, 2009. DOI: https://doi.org/10.1175/2008JCLI2429.1.
    - Analisa, mês a mês ao longo do ciclo ENSO, a frequência de eventos extremos de chuva na América do Sul com dados diários de estações.
    - Define extremo como **média de 3 dias acima do percentil 90**, um critério próximo ao do nosso detector de acumulados.
    - Encontra sinais significativos de El Niño e La Niña na frequência de extremos em extensas regiões, mais extensos que os sinais nos totais mensais. A precipitação diária é mais sensível ao ENSO justamente na cauda.

25. GRIMM, A. M. The El Niño impact on the summer monsoon in Brazil: regional processes versus remote influences. **Journal of Climate**, v. 16, n. 2, p. 263–280, 2003. DOI: https://doi.org/10.1175/1520-0442(2003)016<0263:TENIOT>2.0.CO;2.
    - Analisa com resolução mensal o efeito do El Niño sobre a monção de verão no Brasil, usando uma rede densa de estações.
    - Mostra que anomalias importantes se cancelam na média sazonal e que o sinal muda dentro da estação.
    - No início do verão, o padrão é de anomalias negativas no norte e no centro-leste e positivas no sul. Em janeiro há reforço da chuva no centro-leste.

26. GRIMM, A. M. Interannual climate variability in South America: impacts on seasonal precipitation, extreme events, and possible effects of climate change. **Stochastic Environmental Research and Risk Assessment**, v. 25, n. 4, p. 537–554, 2011. DOI: https://doi.org/10.1007/s00477-010-0420-1.
    - Revisa os principais modos de variabilidade interanual da precipitação sazonal na América do Sul.
    - Mostra que a influência do ENSO sobre os extremos é forte em todas as estações e, em geral, maior que sobre os totais sazonais.
    - O resumo foi lido de forma indireta (registros ADS e peeref), porque o Springer exige login.
    - Nota: o Crossref registra a publicação online em 2010. Volume e fascículo são de 2011.

27. GRIMM, A. M.; FERRAZ, S. E. T.; GOMES, J. Precipitation anomalies in southern Brazil associated with El Niño and La Niña events. **Journal of Climate**, v. 11, n. 11, p. 2863–2880, 1998. DOI: https://doi.org/10.1175/1520-0442(1998)011<2863:PAISBA>2.0.CO;2.
    - Referência para o sinal do ENSO no Sul do Brasil.
    - Só os metadados foram confirmados no Crossref. O resumo não foi lido.

28. REBOITA, M. S.; GAN, M. A.; ROCHA, R. P.; AMBRIZZI, T. Regimes de precipitação na América do Sul: uma revisão bibliográfica. **Revista Brasileira de Meteorologia**, v. 25, n. 2, p. 185–204, 2010. DOI: https://doi.org/10.1590/S0102-77862010000200004.
    - Revisão dos sistemas atmosféricos que produzem precipitação em cada setor da América do Sul (ZCAS, ZCIT, frentes, CCM, entre outros).
    - Base para explicar a distribuição regional e sazonal das anomalias detectadas.

29. CAVALCANTI, I. F. A.; FERREIRA, N. J.; SILVA, M. G. A. J.; SILVA DIAS, M. A. F. (org.). **Tempo e clima no Brasil**. São Paulo: Oficina de Textos, 2009.
    - Registro confirmado no Repositório USP (https://repositorio.usp.br/item/001833489): título, autores, editora e ano.
    - O ISBN 978-85-86238-92-5 aparece apenas em citação secundária e **não foi verificado**.
    - A ordem e o papel de cada autor ou organizador devem ser conferidos na ficha catalográfica do livro.

30. MUÑOZ-SABATER, J. et al. ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. **Earth System Science Data**, v. 13, n. 9, p. 4349–4383, 2021. DOI: https://doi.org/10.5194/essd-13-4349-2021.
    - Descreve o ERA5-Land: componente terrestre do ERA5 com resolução de 9 km e saída horária, forçado pela meteorologia do ERA5 reduzida de escala.
    - Mostra ganho sobretudo em umidade do solo e vazão.
    - Importante para o projeto: a precipitação do ERA5-Land **vem da forçante do ERA5**. Não é um produto independente de precipitação.

31. HERSBACH, H. et al. The ERA5 global reanalysis. **Quarterly Journal of the Royal Meteorological Society**, v. 146, n. 730, p. 1999–2049, 2020. DOI: https://doi.org/10.1002/qj.3803.
    - Descreve o ERA5 (IFS Cy41r2, 31 km, horário, com estimativa de incerteza por ensemble).
    - Para precipitação, a correlação média global com o GPCP mensal sobe de 67% para 77% em relação ao ERA-Interim.

32. BROWN, J. R. C.; WOODS, R.; DA ROCHA, H. R.; ROBERTI, D. R.; ROSOLEM, R. Evaluation of high-resolution meteorological data products using flux tower observations across Brazil. **Hydrology and Earth System Sciences**, v. 30, n. 1, p. 141–162, 2026. DOI: https://doi.org/10.5194/hess-30-141-2026.
    - Compara ERA5-Land, GLDAS 2.0/2.1, MSWEP 2.2 e uma base brasileira interpolada (BNMD) com 11 torres de fluxo no Brasil (1999–2010).
    - Para **precipitação**, o MSWEP é o melhor na escala diária e o BNMD na mensal.
    - O ERA5-Land é o melhor nas demais variáveis.
    - Indica que a chuva diária do ERA5-Land não é o produto mais preciso no Brasil.

33. SILVA, F. D. S. et al. Intercomparison of different sources of precipitation data in the Brazilian Legal Amazon. **Climate**, v. 11, n. 12, artigo 241, 2023. DOI: https://doi.org/10.3390/cli11120241.
    - Avalia nove bases de precipitação na Amazônia Legal: grade de Xavier, CPC, GPCC, CRU, CHIRPS, IMERG, CMORPH, PERSIANN-CDR e ERA5-Land.
    - Todas reproduzem o ciclo anual, com viés predominantemente negativo.
    - O ERA5-Land fica entre as melhores nas escalas mensal, sazonal e anual.
    - Não avalia extremos diários.

**Lacuna.** Não localizamos, com resumo lido, um estudo revisado por pares que avalie especificamente os **extremos diários** de precipitação do ERA5-Land contra pluviômetros em todo o Brasil.
- A busca devolveu indícios de subestimação de extremos pelo ERA5 no Sul do Brasil, mas em uma dissertação (UFRJ) que não verificamos.
- Recomendação: tratar a capacidade do ERA5-Land de representar picos de chuva como limitação declarada do projeto.

---

## Referências não verificadas ou verificadas só em parte (não usar sem conferir)

| Referência | Situação |
|---|---|
| WORLD METEOROLOGICAL ORGANIZATION. *WMO guidelines on the calculation of climate normals*. Geneva: WMO, 2017. (WMO-No. 1203). | Citada por várias fontes secundárias (registro library.wmo.int/records/item/55797). A página da OMM só funciona com JavaScript e o PDF espelhado na NCEI/NOAA deu 404. **Não verificada.** Para definir anomalia, usar o glossário do IPCC (ref. 16). |
| HILL, D. J. Automated Bayesian quality control of streaming rain gauge data. *Environmental Modelling & Software*, v. 40, p. 289–301, 2013. DOI 10.1016/j.envsoft.2012.10.006. | DOI e metadados confirmados no Crossref. **Resumo não lido**, porque o acesso é fechado. Potencialmente relevante (controle de qualidade de pluviômetros), mas o conteúdo não foi verificado. |
| HILL, D. J.; MINSKER, B. S.; AMIR, E. Real-time Bayesian anomaly detection in streaming environmental data. *Water Resources Research*, v. 45, n. 4, 2009. DOI 10.1029/2008WR006956. | DOI e resumo verificados: redes bayesianas dinâmicas em oito séries meteorológicas de Corpus Christi; detectou falha de sensor e uma tempestade. Fica fora da lista principal porque não usa ARIMA nem limiar k·σ, e sim intervalo de credibilidade bayesiano. |
| CAVALCANTI et al. (2009): ISBN 978-85-86238-92-5 | ISBN só em citação secundária. |
| Dissertação UFRJ sobre ERA5 × INMET/ANA (pantheon.ufrj.br) | Não aberta nem verificada. |

---

## Tabela de verificação

| chave | verificada | URL usada | observação |
|---|---|---|---|
| HillMinsker2010 | sim | api.crossref.org/works/10.1016/j.envsoft.2009.08.010; experts.illinois.edu | Resumo lido (AR + intervalo de predição; vento) |
| Yu2014 | sim | api.crossref.org/works/10.1155/2014/879736; api.semanticscholar.org | Resumo lido; modelo exato (AR?) não confirmado |
| HyndmanAthanasopoulos2021 | sim | otexts.com/fpp3/prediction-intervals.html | Seção 5.5 lida |
| Fox1972 | sim | api.crossref.org/works/10.1111/j.2517-6161.1972.tb00912.x; OpenAlex | Resumo lido |
| Tsay1988 | sim | api.crossref.org/works/10.1002/for.3980070102; OpenAlex | Resumo lido |
| ChenLiu1993 | sim | api.crossref.org/works/10.1080/01621459.1993.10594321; OpenAlex | Resumo lido |
| BlazquezGarcia2021 | sim | api.crossref.org/works/10.1145/3444690; arxiv.org/pdf/2002.04236 | Texto completo (arXiv) lido na seção relevante |
| Chandola2009 | sim | api.crossref.org/works/10.1145/1541880.1541882; OpenAlex | Resumo lido |
| Zhou2018 | sim | api.crossref.org/works/10.3390/s18082628; pmc.ncbi.nlm.nih.gov/articles/PMC6111880 | Texto completo: erro relativo, não k·σ |
| Zhang2012 | sim (metadados e resumo) | api.crossref.org/works/10.1080/13658816.2012.654493; OpenAlex | Uso de ARIMA só via revisão |
| AkouemoPovinelli2016 | sim | api.crossref.org/works/10.1016/j.ijforecast.2015.06.001; ideas.repec.org | Resumo via RePEc (indireto) |
| Durre2010 | sim | api.crossref.org/works/10.1175/2010JAMC2375.1; OpenAlex | Resumo lido |
| Wilks2019 | sim | api.crossref.org/works/10.1016/C2017-0-03921-6 | 4ª ed., ISBN 9780128158234; capítulo não conferido |
| Coles2001 | sim | api.crossref.org/works/10.1007/978-1-4471-3675-0 | Metadados |
| IPCC2022_AnnexII | sim | ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_Annex-II.pdf | Citações literais conferidas no PDF, com páginas |
| IPCC2014_SYR_Glossary | sim | ipcc.ch/site/assets/uploads/2019/01/SYRAR5-Glossary_en.pdf | Definição de *extreme weather event* conferida |
| Seneviratne2012_SREX | sim | api.crossref.org/works/10.1017/CBO9781139177245.006; ipcc.ch/site/assets/uploads/2018/03/SREX-Chap3_FINAL-1.pdf | Citações conferidas (p. 111 e 116) |
| Seneviratne2021_AR6ch11 | sim (metadados) | api.crossref.org/works/10.1017/9781009157896.013 | p. 1513–1766; texto não lido |
| WMO1310_2023 | sim | digitallibrary.un.org/record/4012890/files/Guidelines.pdf | PDF lido; ISBN 978-92-63-11310-8 |
| WMO1150_2015 | sim (existência) | extranet.wmo.int/…/2015-06-12-PR-6852-WDS-PWS-WMO-No-1150_en.pdf | Carta-circular oficial; guia não lido |
| WMO1203_2017 | **não** | library.wmo.int/records/item/55797 (página só em JS); espelho NCEI deu 404 | Ver lista de não verificadas |
| Zhang2011_ETCCDI | sim | api.crossref.org/works/10.1002/wcc.147; OpenAlex | Resumo lido |
| Stephenson2008 | sim | api.crossref.org/works/10.1017/CBO9780511535840.004; OpenAlex | Só o parágrafo de abertura; editores não confirmados |
| Zscheischler2018 | sim (metadados) | api.crossref.org/works/10.1038/s41558-018-0156-3 | Resumo fechado; definição via glossário IPCC |
| GrimmTedeschi2009 | sim | api.crossref.org/works/10.1175/2008JCLI2429.1; OpenAlex | Resumo lido |
| Grimm2003 | sim | api.crossref.org (consulta bibliográfica); OpenAlex | Resumo lido |
| Grimm2011 | sim | api.crossref.org/works/10.1007/s00477-010-0420-1 | Resumo indireto (ADS/peeref) |
| GrimmFerrazGomes1998 | sim (metadados) | api.crossref.org (consulta bibliográfica) | Resumo não lido |
| Reboita2010 | sim | api.crossref.org (DOI 10.1590/S0102-77862010000200004); OpenAlex | Resumo lido |
| Cavalcanti2009 | parcial | repositorio.usp.br/item/001833489 | Título, autores, editora e ano ok; ISBN não verificado |
| MunozSabater2021 | sim | api.crossref.org/works/10.5194/essd-13-4349-2021; OpenAlex | Resumo lido |
| Hersbach2020 | sim | api.crossref.org/works/10.1002/qj.3803; OpenAlex | Resumo lido |
| Brown2026_HESS | sim | api.crossref.org/works/10.5194/hess-30-141-2026; OpenAlex | Resumo lido |
| Silva2023_Climate | sim | api.crossref.org/works/10.3390/cli11120241; OpenAlex | Resumo lido |
| Hill2013_raingauge | parcial | api.crossref.org (DOI 10.1016/j.envsoft.2012.10.006) | Só metadados; fora da lista principal |
| HillMinskerAmir2009 | sim | api.crossref.org (DOI 10.1029/2008WR006956); OpenAlex | Resumo lido; não usa k·σ |
