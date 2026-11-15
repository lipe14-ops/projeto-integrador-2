# Clima Brasil — resposta às observações da avaliação

Relatório consolidado de 14/11/2026. Todos os números vêm de
`resultados/resumo.json`, gerado pelos comandos da seção 10. Nenhum foi
digitado à mão.

Versão curta para o professor: [`RESPOSTAS_PROFESSOR.md`](RESPOSTAS_PROFESSOR.md).

Documentos de apoio:

| Documento | Tarefa |
|---|---|
| [`referencias_verificadas.md`](referencias_verificadas.md) | A, B: 33 itens, com DOI conferido no Crossref quando existe; documentos sem DOI conferidos no PDF oficial |
| [`DEFINICOES_ANOMALIA_EXTREMO.md`](DEFINICOES_ANOMALIA_EXTREMO.md) | B |
| [`VALIDACAO_NOTICIAS.md`](VALIDACAO_NOTICIAS.md) | C |
| [`RESIDUO_DE_CHUVA.md`](RESIDUO_DE_CHUVA.md) | E |
| [`resultados/`](resultados/) (`resumo.json`, `tabelas/`, `figuras/`) | D, F e números da A |
| página **Mapa nacional** + API `/api/analysis` | D, F |

---

## 1. Diagnóstico

**Preservado sem alteração:**
- ingestão do ERA5-Land, malha do IBGE e ONI;
- detector ARIMA + Z de chuva diária e detector de acumulados de 3 e 5 dias ≥ P99, com revisão por regras;
- busca e verificação de notícias;
- página Explorar;
- anomalias e decisões sobre notícias já gravadas no banco.

**Problemas encontrados:**

| # | Problema | Tratamento |
|---|---|---|
| 1 | **Falta o registro das 00 UTC do dia 1º em todos os meses.** O último dia de cada mês fica sem total diário (uma só metade). Efeitos: o dia nunca é pontuado; acumulados que o incluem são extrapolados por k/(k−1), gerando excesso de eventos no dia 31 e nos dias 2 e 4; alertas ARIMA no dia 1º dobram (a previsão vira de dois passos). Isso atinge o pico da enchente de POA (30/04/2024). | Na análise: 34.801 eventos calculados sobre dado incompleto foram excluídos (classe `dado_incompleto`), e a exposição conta só dias cujo dia anterior é válido (3.071 por município). **Correção na origem pendente:** recarregar os dados e refazer a detecção. |
| 2 | Temperatura e umidade só tinham análise em 4 municípios. | Novo detector nacional (`analysis/thermal.py`). |
| 3 | "Anomalia" e "evento extremo" usados como sinônimos. | Classificação em eixos independentes (seção 3). |
| 4 | O "resíduo" fica na escala log, e `predicted_mm` era apresentado como "esperado". | `RESIDUO_DE_CHUVA.md`; textos da API e da interface corrigidos. |
| 5 | O detector de chuva usa σ único, mas a variância do resíduo muda com a estação. | Medido na seção 2.3. |
| 6 | O JSON-LD das notícias nunca era lido, e páginas XHTML derrubavam o parser. | Corrigido em `news/extract.py`, com testes de regressão. |
| 7 | O teste temático das notícias aceita seca, previsão ou projeto de lei como "chuva". | Documentado, com `xfail` estrito (seção 5). |
| 8 | Não havia mapa nacional nem comparação sazonal. | API `/api/analysis` + página Mapa nacional. |

---

## 2. Tarefa A — ARIMA + Z-score

### 2.1 Literatura

Veja `referencias_verificadas.md`, seção A, que indica o grau de verificação
de cada item.

**O princípio é documentado.** Marcar como anômalo o erro de previsão de um
passo acima de c·σ equivale a ficar fora do intervalo de predição.
- Equivalência: Hyndman e Athanasopoulos (2021, §5.5).
- Base estatística: Fox (1972); Tsay (1988); Chen e Liu (1993).
- Aplicação ambiental mais próxima do projeto: **Leigh et al. (2019)**, com
  ARIMA, previsão de um passo, desvio-padrão dos resíduos do treino e
  intervalo de 99% (|Z| > ≈2,6) em dados de rios; recomenda combinar métodos.
- Outra aplicação ambiental: Hill e Minsker (2010), com dados de vento, AR e
  intervalo de predição.
- Revisão: Blázquez-García et al. (2021).
- Yu et al. (2014) também usam intervalo de predição em hidrologia, mas o tipo
  de modelo não foi confirmado.

**A aplicação à chuva diária não foi encontrada.** Não há trabalho revisado
por pares que aplique ARIMA + Z sobre resíduos de **precipitação diária**.
Durre et al. (2010) tratam de controle de qualidade de chuva diária, com
outros testes.

**Conclusão:** é uma **adaptação experimental** de um princípio
estabelecido.

### 2.2 Protocolo de avaliação

Código: `analysis/method_eval.py`.

**Amostra e regras:**
- O detector de produção foi reexecutado sem alteração em uma amostra
  aleatória estratificada: 20 municípios por região, mais POA, semente 42.
- 101 sorteados; 1 sem dados; **100 avaliados**.
- Só foram usados dias pontuados fora da amostra cujo dia anterior é válido.

**Medidas:**
1. Taxa de alertas para k = 2,5; 3; 3,5 e 4.
2. Teste de Brown–Forsythe entre as estações.
3. Alertas com σ único (atual) e com Z repadronizado pela média e pelo DP da
   mesma estação nos anos anteriores.
4. Sobreposição com os dias ≥ P95/P99 dos dias chuvosos (≥ 1 mm) dos anos
   anteriores, usando limiares do tipo R95p/R99p, aplicados ao dia.
5. Simulação nula com **dados sintéticos**: 20 séries com ocorrência de
   Bernoulli e intensidade gama, com ciclo sazonal e sem nenhum evento
   inserido.

### 2.3 Resultados

| Medida | Resultado |
|---|---|
| Taxa de Z > 3 (mediana entre municípios) | **0,78%**, contra 0,135% na normal; P10–P90 de 0,26%–1,94% |
| Taxa de Z > 4 | 0,065%, contra 0,003% |
| DP de Z / assimetria (medianas) | 1,008 / +0,86 |
| Simulação nula, Z > 3 | mediana de 0,40% (0%–1,28%); por forma da gama: 0,85% (0,5), 0,37% (0,7), 0,11% (1,0) |
| Modelos com termos de Fourier escolhidos pelo BIC | 16% |
| Brown–Forsythe com p < 0,05 | **98%** dos municípios; razão DP máx./mín. entre estações: 1,92 |
| Alertas com σ único (participação normalizada) | verão 31,4 · outono 27,9 · inverno 9,9 · primavera 30,9 |
| Alertas com σ sazonal | verão 11,5 · outono 20,1 · inverno 44,7 · primavera 23,7 |
| **Dias ≥ P99 locais (referência independente do modelo)** | **verão 44,8 · outono 28,3 · inverno 7,8 · primavera 19,1** |
| Alertas que são ≥ P95 / ≥ P99 | 54,1% / 21,8% |
| Dias ≥ P99 marcados pelo ARIMA | 38,3% (Jaccard mediano de 0,15) |

**Interpretação:**

- **Z > 3 não equivale a 0,135%.**
  - As caudas reais são muito mais pesadas que a normal.
  - Mesmo sem eventos, a forma da chuva (zeros, assimetria e ciclo sazonal não
    modelado) já produz alertas. A quantidade depende da forma da
    distribuição: com gama de forma 1, fica abaixo do nominal.
- **Na chuva, o ARIMA é quase uma linha de base constante em escala log.** Em
  POA, Z > 3 corresponde a cerca de 35–45 mm/dia.
- **Com σ único, a distribuição sazonal dos alertas se parece com a dos dias
  ≥ P99 climatológicos.** Os dois concentram eventos no verão e quase nada no
  inverno.
  - O σ sazonal mede outra coisa: "surpreendente para a estação". Na estação
    seca, o DP é pequeno e qualquer chuva moderada se destaca.
  - A estação dominante muda em 87,6% dos municípios ao trocar o σ. Esse valor
    não tem linha de base de ruído: com cerca de 30 alertas por município, a
    estação dominante já é instável.
  - Por isso, as conclusões sazonais (seção 7) se apoiam na referência
    climatológica, e não só nos alertas.
- **O ARIMA + Z capta "dias acima do típico", não "extremos".** Só 22% dos
  alertas são ≥ P99.

### 2.4 Temperatura e umidade

Código: `analysis/thermal.py`.

**Modelo:**
- climatologia de Fourier (K = 3) para a média;
- **variância sazonal** modelada por Fourier (K = 2);
- AR(p), p ≤ 3, escolhido por BIC;
- reajuste anual com janela expansiva;
- Z sobre o erro de um passo.

**Resultados:**
- DP de Z mediano de 1,04.
- Taxas medianas por variável:

  | Variável | Z > 3 | Z < −3 |
  |---|---|---|
  | Temperatura | 0,15% | 1,00% (cauda fria: frentes frias) |
  | Umidade | 0,64% | 0,49% |

- 38 municípios sem dados (76 séries, temperatura e umidade).
- Testes confirmam que não há vazamento de informação futura.

---

## 3. Tarefa B — Anomalia × extremo

Documento completo: `DEFINICOES_ANOMALIA_EXTREMO.md`.

**Quatro eixos independentes:**
1. anomalia estatística (Z do modelo);
2. extremo meteorológico (percentil local da época, segundo IPCC, OMM-1310 e ETCCDI);
3. intensidade absoluta (≥ 50 mm/dia ou ≥ 100 mm/5 dias);
4. impacto documentado (notícia verificada).

O evento climático extremo (escala sazonal) não é detectado.

**Chuva:**
- 181.226 anomalias ARIMA contadas;
- **38,1% apenas estatísticas**;
- 61,9% extremas (P95/P99 local ou da época);
- 15,5% com intensidade alta.

**Notícias:** só foram buscadas para 9.522 anomalias de 227 municípios.
Entre elas, 24,2% das ARIMA e 36,8% dos acumulados têm notícia verificada
(`VALIDACAO_NOTICIAS.md`). A proporção sobre o total nacional não é
informativa, porque a maior parte não foi investigada.

**Temperatura e umidade:** o extremo exige o percentil da **mesma cauda** do
sinal do Z.
- 290 anomalias que estavam na cauda oposta foram reclassificadas como
  "apenas estatísticas".
- A referência do primeiro ano pontuado é curta (cerca de 60 dias). O limiar
  é **análogo** ao TX90p/TN10p, não idêntico.

**Exemplos de divergência entre os conceitos:**
- *Anomalia sem extremo:* POA, 14/07/2022, 23,9 mm, Z = 3,00. Ficou abaixo
  dos percentis locais, mas tem notícia (impacto sem extremo).
- *Extremo sem anomalia diária:* chuva persistente que só o detector de
  acumulados capta (SREX descreve esse mecanismo).
  - O exemplo intuitivo seria o início de maio de 2024 em POA, mas ele **não
    pode ser usado**: o dia de pico, 30/04, está entre os dias ausentes, e o
    acumulado até 02/05 foi excluído por ter dado incompleto.
  - Além disso, a cheia do Guaíba resultou da chuva nas bacias a montante,
    não na célula de POA.

---

## 4. Tarefa D — Mapa coroplético

**Implementação:**
- API: `/api/analysis/{coropletico, municipios/{ibge}, regioes, ranking, definicoes, geometrias}`.
- Página: **Mapa nacional**, com polígonos reais do IBGE ligados pelo código IBGE.
- Geometria simplificada em 0,01°: a malha passa de 505 MB para 3,8 MB.

**Métricas**, cada uma com unidade e definição na legenda:
- frequência por 1.000 dias válidos;
- contagem, com aviso de que não é comparável entre municípios;
- \|Z\| mediano;
- participação de uma estação;
- outono + inverno;
- concentração (1 − H/ln 4);
- estação de maior taxa após teste;
- razão de frequência ENSO/neutro (exploratória).

**Filtros:** variável, classe, período, estação e fase ENSO. Os filtros que
uma métrica ignora são informados em `ignored_filters`.

**Regras de representação:**
- Dias anômalos separados por até 1 dia sem anomalia formam um evento. Um
  acumulado ocupa a janela inteira, então o dia ARIMA da mesma tempestade não
  conta duas vezes.
- Municípios com menos de 20 eventos ficam hachurados.
- Municípios sem dados válidos ficam em cinza ou pontilhados. Nunca aparecem
  como zero.
- Paletas validadas para daltonismo.

**Verificação:**
- testes de consistência mapa × contagem e de filtros (`tests/test_analysis_api.py`);
- `npm run build` e `npm run lint` sem erros;
- capturas em navegador *headless*.

---

## 5. Tarefa C — Verificação das notícias

Documento completo: `VALIDACAO_NOTICIAS.md`.

**Benchmark de 67 casos sintéticos**, com rótulos fixados antes da execução:

| Métrica | Valor |
|---|---|
| Precisão | 0,724 |
| Revocação | 0,913 |
| F1 | 0,808 |
| Falsos positivos | 18,2% |
| Falsos negativos | 8,7% |

O benchmark mede conformidade com a especificação, não a acurácia real.

**8 falsos positivos documentados:**
- matérias sobre seca;
- onda de calor;
- alerta do Inmet;
- projeto de lei;
- "casa cheia";
- vendaval;
- duas menções de passagem a cidades.

Causa principal: o teste temático aceita qualquer termo de chuva na manchete
e não recebe a variável da anomalia.

**Pipeline real:**
- 31.237 vínculos: 16,6% verificados, 62,0% rejeitados, 21,4% pendentes;
- 82,7% das pendências são por falta de data;
- 50 de 50 URLs verificadas continuam acessíveis.

**Pendente:** a anotação humana da amostra cega de 150 vínculos.

---

## 6. Tarefa E — Resíduo de chuva

Documento completo: `RESIDUO_DE_CHUVA.md`.

**Definição:**
- e_t = ln(1 + P_t) − ŷ_{t|t−1} é o erro de previsão de um passo em escala log;
- Z = (e_t − μ_e)/σ_e;
- `predicted_mm` = exp(ŷ) − 1 é uma previsão típica, não a média;
- `residual_mm` é apenas descritivo.

**Exemplo real (POA, 23/05/2024):**

| Grandeza | Valor |
|---|---|
| Chuva observada | 38,66 mm |
| Previsão típica | 0,85 mm |
| e | 3,063 |
| Z | 3,03 |

Esse dia vem depois do pico da enchente.

**Exemplo fictício:** 40 mm com previsão de 1 mm dão Z = 3,02. Com previsão
de 10 mm, dão Z = 1,32.

---

## 7. Tarefa F — Distribuição sazonal em todos os municípios

### 7.1 Método

Código: `analysis/seasonal.py`.

- **Estações:** DJF, MAM, JJA e SON.
- **Frequência:** eventos por dia válido, normalizada entre as quatro estações
  (25% = sem preferência).
- **Teste:** qui-quadrado por município contra a exposição, com FDR de
  Benjamini–Hochberg e pelo menos 20 eventos.
  - "Predomínio de X" significa que a uniformidade foi rejeitada **e** que X
    é a estação de maior taxa. A rejeição pode vir também de uma estação com
    poucos eventos.
- **Cobertura:** os 5.535 municípios com dados têm exatamente a mesma janela
  (3.071 dias válidos de chuva). Os 38 restantes aparecem como "sem dados".
- **Poder estatístico:** é baixo.
  - Com o perfil agregado do Sul (w = 0,23), o qui-quadrado a 5% tem poder de
    12% com 20 eventos e de 14% com 26, antes do FDR.
  - Logo, **"sem predomínio significativo" não significa "estações iguais"**.
  - Comparar a proporção de municípios significativos entre regiões mistura
    efeito com tamanho de amostra: a mediana é de 20 eventos no Sul e de 49 no
    Nordeste.
  - Por isso a resposta usa sobretudo as **participações** (estimativas de
    efeito).
- **A "chuva" junta os dois detectores**, ARIMA (Z > 3) e acumulados ≥ P99,
  desagrupados juntos.

### 7.2 Resposta: o predomínio de outono/inverno em POA é regional, nacional ou local?

Chuva, todas as anomalias válidas, 2017–2025:

| | Verão | Outono | Inverno | Primavera | Outono + inverno |
|---|---|---|---|---|---|
| **Porto Alegre** (29 eventos) | 7,0% | 27,4% | 27,4% | 38,2% | **54,8%** (p = 0,12; q = 0,16) |
| Mediana dos municípios do RS | | | | | 56,2% |
| Sul (agregado) | 18,7% | 24,7% | 25,3% | 31,3% | 50,0% |
| Nordeste (agregado) | 35,6% | **37,7%** | 10,7% | 15,9% | 48,4% |
| **Brasil (agregado)** | **35,5%** | 28,4% | 10,3% | 25,7% | 38,7% |
| Brasil, dias ≥ P99 (amostra de 100, independente do modelo) | **44,8%** | 28,3% | 7,8% | 19,1% | 36,1% |

1. **Em POA, a inclinação para outono/inverno é pequena.**
   - Outono + inverno somam 54,8%, contra 50% sem preferência. O teste não
     distingue isso da uniformidade, e o poder é baixo.
   - O traço mais marcado é o **verão com poucos eventos** (7%). A estação de
     maior taxa é a primavera.
   - Com eventos que têm notícia: 53,9%.
   - Com extremos: 51,5%.
2. **É um traço do Rio Grande do Sul e do Sul, não nacional.**
   - POA fica perto da mediana gaúcha (56,2%).
   - No agregado do Sul, as estações têm participações próximas: o verão é
     menor (18,7%) e a primavera, maior (31,3%).
3. **No Brasil, o padrão é o oposto.** Entre os 4.872 municípios com pelo
   menos 20 eventos:

   | Padrão | Municípios |
   |---|---|
   | Predomínio de **verão** | **37,3%** |
   | Sem predomínio detectável | 30,9% |
   | Predomínio de outono | 18,5% |
   | Predomínio de primavera | 12,4% |
   | Predomínio de inverno | **0,9%** |

   - O verão predomina no Sudeste (49%) e no Centro-Oeste (54%).
   - O outono predomina no **Nordeste** (47% dos municípios).
   - A referência climatológica independente do modelo confirma: no Brasil,
     os dias ≥ P99 ficam 45% no verão e 8% no inverno.
4. **Coerência com a literatura.** O padrão é compatível com os regimes de
   chuva descritos por Reboita et al. (2010). A atribuição a sistemas
   específicos não foi testada.
5. **Estrutura espacial.** O I de Moran da participação de outono + inverno é
   0,94, com p de permutação de 0,005 (o mínimo com 199 permutações). Isso é
   esperado em parte, porque vizinhos compartilham células do ERA5-Land e
   sistemas sinóticos. Não é evidência independente por município.

### 7.3 Outras variáveis

Medianas de outono + inverno entre os municípios com pelo menos 20 eventos:

| Variável | Brasil (n) | Sul (n) | POA | Leitura |
|---|---|---|---|---|
| Umidade abaixo do esperado | 67,3% (2.032) | 70,2% (785); 93,6% acima de 50% | **75,7%** (25 eventos; q = 0,053) | Em POA, o padrão de outono/inverno é mais forte no **ar seco**. No Sudeste, só 311 de 1.660 municípios têm eventos suficientes, o que não permite generalizar. |
| Umidade acima do esperado | 55,5% (2.913) | 71,1% (281) | 2 eventos | — |
| Temperatura abaixo do esperado | 47,3% (5.115) | 40,3% (1.171) | 19 eventos | 89% sem predomínio: com a variância sazonal corrigida, frentes frias não se concentram artificialmente no inverno. |
| Temperatura acima do esperado | 107 municípios elegíveis | — | 4 eventos | Rara demais para comparar. |

### 7.4 ENSO (apenas exploratório)

Arquivos: `tabelas/enso_regiao_estacao.csv` e `figuras/enso_razao_precipitacao.png`.

**No agregado nacional, a razão de frequência de chuva fica acima de 1 nas
duas fases e em todas as estações.**

| Estação | El Niño | La Niña |
|---|---|---|
| Inverno | 1,51 | 1,76 |
| Outono | 1,25 | 1,02 |
| Primavera | 1,14 | 1,26 |
| Verão | 1,29 | 1,10 |

Por região, o sinal varia. Não interpretamos isso como efeito do ENSO, por
três motivos:
- houve só 27 meses de El Niño, 30 de La Niña e 51 neutros, ou seja, 2 a 3
  episódios por fase;
- a fase quase coincide com o ano (2022 foi todo La Niña; 2025, todo neutro),
  então a variabilidade entre anos se confunde com a fase;
- os IC 95% supõem eventos independentes entre municípios. Na prática, eles
  são estreitos demais.

---

## 8. Revisão independente: achados e tratamento

Um revisor independente (agente separado, sem acesso às nossas conclusões)
conferiu números, código e textos. Os números das seções 2, 3, 5 e 7
conferiram com o `resumo.json` e com recálculos. O revisor também confirmou
que o BH, o IC da razão de taxas e a ausência de vazamento no detector
térmico estão corretos.

| Achado | Gravidade | Tratamento |
|---|---|---|
| Último dia do mês ausente → acumulados extrapolados e alertas do dia 1º inflados | crítico | Eventos excluídos e exposição corrigida (seção 1, item 1); correção na origem pendente |
| Contradição sobre a enchente de POA (Z = 3 "nunca" × 23/05 com Z = 3,03) | crítico | Exemplo removido e explicação corrigida (seção 3) |
| "Sul equilibrado / 90% sem predomínio" confundia ausência de evidência com evidência de ausência | crítico | Poder calculado (12–14%) e resposta baseada nas participações (seções 7.1 e 7.2) |
| Dupla contagem entre ARIMA e acumulados da mesma tempestade | importante | Desagrupamento pela janela do acumulado |
| σ sazonal sem recentragem; afirmação de "3 a 6×" na simulação nula | importante | Recentrado; texto da simulação corrigido (seção 2.3) |
| Denominador das notícias (todas as anomalias × investigadas) | importante | Corrigido (seção 3) |
| 290 anomalias térmicas na cauda oposta | menor | Classe exige a mesma cauda; reclassificadas |
| Citações além do verificado (Yu, Durre, Reboita; contagem de 35 refs) | importante | Texto ajustado ao que foi verificado; 33 itens |
| Legendas sobre o mapa; "sem dados" fundido com "< 20 eventos" | importante | Legendas fora do mapa e categorias separadas |
| ENSO "> 1 nas duas fases" vale para o Brasil, não para as regiões | menor | Texto corrigido (seção 7.4) |

**Limitações não resolvidas:**
- a taxa ARIMA pode refletir a intermitência da chuva (hipótese não testada);
- o filtro "extremos" inclui `extremo_sazonal`, então o teste de robustez é em
  parte circular;
- o qui-quadrado fica no limite com 20 eventos.

---

## 9. Recomendações

1. **Dados:** recarregar o registro das 00 UTC do dia 1º e refazer a detecção
   nacional. No detector de acumulados, não extrapolar janelas incompletas.
2. **Chuva:** usar variância sazonal ou POT/GPD por estação (Coles, 2001), ou
   um modelo de ocorrência × intensidade (Wilks, 2019). Relatar a taxa
   empírica de alertas.
3. **Notícias:** passar a variável da anomalia ao verificador; separar
   ocorrência de previsão, alerta e seca; exigir menção não incidental à
   cidade; fazer a anotação humana; rodar `cli revalidate`.
4. **ENSO:** usar uma série longa (ERA5 desde 1950).
5. **Validação externa:** comparar com pluviômetros do INMET e da ANA.

---

## 10. Implementação, testes e reprodutibilidade

**Arquivos novos:**
- `app/climate_news/analysis/`: `seasons`, `classification`, `thermal`, `seasonal`, `method_eval`, `snapshot`, `service`, `router`, `report`, `cli`;
- `app/climate_news/validation.py` e `scripts/amostra_validacao_noticias.py`;
- front-end: `pages/AnaliseEspacial.tsx`, `components/Analise/*`, `data/analise.ts`;
- testes: `tests/test_analysis*.py`, `tests/test_validation_metrics.py`, `tests/news_validation/*`;
- pôster: `docs/poster/`.

**Arquivos alterados:**
- `app/main.py`;
- `app/climate_news/schemas.py`;
- `app/climate_news/news/extract.py`;
- `tests/test_news.py`;
- `README.md`;
- front-end: `App.tsx`, `Header.tsx`, `api.ts`, `eventos.ts`, `EventosExtremos.tsx`.

**Banco:** sem migrações e sem dados alterados. A análise lê o snapshot
Parquet em `data/analise/`, com SHA-256 em `metadata.json`.

**Para reproduzir:**

```sh
uv run python -m app.climate_news.analysis.cli snapshot-chuva
uv run python -m app.climate_news.analysis.cli snapshot-termica --workers 4
uv run python -m app.climate_news.analysis.cli reclassificar-termica
uv run python -m app.climate_news.analysis.cli snapshot-malha
OMP_NUM_THREADS=1 uv run python -m app.climate_news.analysis.cli avaliar-metodo --por-regiao 20 --workers 6
uv run python -m app.climate_news.analysis.cli relatorio
uv run python docs/poster/preencher_numeros.py
uv run pytest -q
```

**Limitações:**
- ERA5-Land não é estação: a célula é de cerca de 9 km, os picos são
  suavizados e municípios vizinhos podem compartilhar a mesma célula;
- o período é curto (9 anos pontuados);
- os resultados sazonais da chuva dependem da definição de anomalia;
- não há padrão-ouro de notícias, e a cobertura é desigual (vínculos
  verificados: 26% no Sul, 9% no Norte);
- o evento climático extremo não é detectado;
- o ENSO é apenas exploratório;
- a falha de dado de fim de mês só foi contornada, não corrigida.
