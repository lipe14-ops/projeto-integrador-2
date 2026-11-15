# Anomalia estatística × evento extremo × evento de impacto (Tarefa B)

As definições abaixo estão implementadas em
`app/climate_news/analysis/classification.py` e são as que a API
`/api/analysis/definicoes` devolve. As referências estão em
[`referencias_verificadas.md`](referencias_verificadas.md), seção B.

## 1. Princípio: eixos independentes, nunca sinônimos

Cada evento detectado é descrito em **quatro eixos separados**. Um eixo não
implica outro:

| Eixo | Pergunta | Referência de comparação | Fonte da definição |
|---|---|---|---|
| **1. Anomalia estatística** | O valor surpreendeu o modelo? | previsão de um passo do modelo (ARIMA na chuva; Fourier + AR em temperatura e umidade) | IPCC (2022, Annex II): *anomaly* = desvio em relação a uma referência |
| **2. Extremo meteorológico** | O valor é **raro para este lugar nesta época do ano**? | percentis da climatologia local dos anos anteriores | IPCC (2022): *extreme weather event* = tão raro quanto P10/P90 ou mais; OMM-1310 (2023): magnitude, duração e extensão, independente do impacto; ETCCDI (Zhang et al., 2011) |
| **3. Intensidade absoluta** | O volume pode causar dano em qualquer lugar? | limiar físico fixo: ≥ 50 mm/dia ou ≥ 100 mm/5 dias | OMM-1310, opção de "limiar fixo associado a impacto" |
| **4. Impacto documentado** | Houve ocorrência registrada? | notícia verificada na página original | SREX (Seneviratne et al., 2012); OMM-1150 (2015) |

O **evento climático extremo** (escala de estação ou mais, como uma seca
prolongada ou uma estação chuvosa anômala) **não** é detectado: os detectores
são diários. Com 11 anos de dados, um percentil de totais sazonais teria cerca
de 10 valores por município, o que não basta para estimá-lo. Isso fica
registrado como limitação.

## 2. Definições operacionais (o que o código faz)

### Chuva

| Classe (mutuamente exclusiva) | Regra | Extremo? | Conta nos mapas? |
|---|---|---|---|
| `dado_incompleto` | dia anterior ausente (previsão de dois passos) ou janela do acumulado com dia ausente (soma extrapolada) | não | **não** |
| `artefato_provavel` | detector disparou, mas o Cientista de Dados apontou traço (< 1 mm) ou base próxima de zero | não | **não** |
| `anomalia_negativa` | Z < −3 (choveu bem menos que o previsto) | não | não |
| `anomalia_estatistica` | Z > 3, mas o volume está abaixo do P95 dos dias chuvosos e do P95 da época | **não** | sim |
| `extremo_sazonal` | ≥ P95 dos dias chuvosos da mesma época (±15 dias) nos anos anteriores, ou ≥ P99 de todos os dias da época na estação seca (com ≥ 10 mm) | sim | sim |
| `extremo_local` | ≥ P95 dos dias chuvosos (≥ 1 mm) do município nos anos anteriores (nível `p99` se ≥ P99) | sim | sim |
| `extremo_acumulado` | soma de 3 ou 5 dias ≥ P99 das somas de mesma duração dos anos anteriores (nível `recorde` se supera o máximo anterior) | sim | sim |

### Temperatura e umidade

| Classe | Regra |
|---|---|
| `anomalia_estatistica` | \|Z\| > 3 no resíduo do AR, com o valor entre P10 e P90 da mesma época (±15 dias) nos anos anteriores. É uma mudança brusca, não um valor raro. |
| `extremo_local` | valor ≥ P90 (anomalia positiva) ou ≤ P10 (negativa) da mesma época nos anos anteriores, sempre na **mesma cauda** do sinal do Z. Limiar análogo ao dos índices TX90p/TN10p do ETCCDI, com referência curta no primeiro ano (cerca de 60 dias). Nível `p99` se ≥ P99 ou ≤ P1. |

**Regra conservadora.** Sem veredito climatológico, a anomalia fica como
`anomalia_estatistica`. O sistema nunca chama algo de extremo sem evidência
de raridade local.

## 3. Por que uma anomalia não é necessariamente um extremo, e vice-versa

**Anomalia sem extremo.** O Z mede o afastamento em relação à *previsão*, não
à *climatologia*. Na estação seca de um município do Centro-Oeste, 15 mm
depois de semanas sem chuva podem dar Z > 3 e mesmo assim ser um volume
comum no ano. Na temperatura, uma frente fria que derruba 8 °C de um dia para
o outro gera Z muito negativo, mesmo que a temperatura final seja normal para
julho.

**Extremo sem anomalia.** Uma chuva **persistente**, que se acumula ao
longo de vários dias sem nenhum pico diário fora do comum, não dispara o Z
diário. Ela só aparece no detector de acumulados de 3 e 5 dias. O SREX
(Seneviratne et al., 2012) descreve esse mecanismo: extremos formados pela
acumulação de eventos que, isolados, não são extremos.

O exemplo intuitivo seria o início de maio de 2024 em Porto Alegre, mas ele
não pode ser usado. O dia de pico, 30/04, está entre os dias sem dado
completo: os dados do projeto não têm o registro das 00 UTC do dia 1º de cada
mês. Por isso o acumulado que termina em 02/05 foi excluído (`dado_incompleto`).
Além disso, a cheia do Guaíba resultou da chuva nas bacias a montante, não na
célula ERA5-Land da cidade.

**Impacto sem extremo.** Em Porto Alegre, 14/07/2022 teve 23,9 mm e Z = 3,00,
mas ficou abaixo dos percentis locais (`anomalia_estatistica`). Mesmo assim, há
2 notícias verificadas. O impacto depende de exposição e vulnerabilidade, não
só do volume de chuva.

**Extremo sem impacto documentado.** As notícias só foram buscadas para
9.522 anomalias de 227 municípios. Entre elas, 24,2% das anomalias ARIMA e
36,8% dos acumulados têm notícia verificada. A ausência de notícia não
significa ausência de impacto: a cobertura jornalística é desigual entre
municípios.

## 4. Quanto as classes diferem nos dados reais

Snapshot de 14/11/2026, última detecção de cada um dos 5.535 municípios com
dados (números de `resultados/resumo.json`):

| Medida | Valor |
|---|---|
| Anomalias ARIMA de chuva contadas (Z > 3, sem artefatos, sem as negativas e sem dado incompleto) | 181.226 |
| … apenas estatísticas (não extremas para o local) | **38,1%** |
| … extremas para o local ou a época (≥ P95) | 61,9% |
| … com intensidade absoluta alta (≥ 50 mm/dia ou ≥ 100 mm/5 dias) | 15,5% |
| Prováveis artefatos excluídos | 20.988 |
| Eventos calculados sobre dado incompleto, excluídos | 34.801 |

Mais de um terço das anomalias estatísticas de chuva **não** são extremos
climatológicos. Por isso os mapas e a API têm o filtro "classe do evento"
(`todas`, `estatisticas`, `extremos`, `impacto`), e os rótulos da interface
não usam "anomalia" e "evento extremo" como sinônimos.

## 5. Tabela comparativa (resumo para apresentação)

| Critério | Anomalia estatística | Evento meteorológico extremo | Evento climático extremo | Evento de impacto |
|---|---|---|---|---|
| Referência | previsão do modelo (passado recente) | climatologia local da mesma época | climatologia de totais sazonais ou anuais | danos registrados |
| Escala de tempo | dia | horas a dias | estação a anos | qualquer |
| Depende do lugar? | sim (modelo por município) | sim (percentil local) | sim | sim (exposição e vulnerabilidade) |
| Depende do impacto? | não | não (OMM-1310) | não | **sim, por definição** |
| No projeto | Z > 3 (ARIMA; Fourier + AR) | percentis P95/P99; acumulados ≥ P99 | **não detectado** (limitação) | notícia verificada (indício, não prova) |
| Coincidem quando | chuva intensa após dias secos, num lugar onde esse volume é raro | — | — | extremo + alta exposição |
| Divergem quando | mudança brusca dentro do normal; chuva persistente sem pico diário | evento lento, sem salto diário | estação inteira anômala sem dias extremos | dano com chuva moderada; extremo em área desabitada |
