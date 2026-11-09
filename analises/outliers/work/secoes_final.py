"""Seções 12–15 e resumo. Os números citados vêm da execução do notebook
(sementes fixas; reexecutar reproduz os mesmos valores)."""
from pathlib import Path

MD_DISCUSSAO = r"""
## 12. Discussão científica

Os números citados nesta seção vêm das células acima e se reproduzem com
`SEED = 42`.

**Os métodos discordam mais do que concordam.** Com orçamentos parecidos, o
percentual de instantes sinalizados no teste foi de 1,66% (ARIMA+Z), 1,13%
(IF) e 1,44% (Hampel). Mesmo assim, dos 1.081 instantes sinalizados por
pelo menos um método, **75%** foram marcados por um único método, e só 64
(5,9%) pelos três. O índice de Jaccard ficou entre 0,10 e 0,26. Essa
divergência é esperada, porque cada método responde a uma pergunta
diferente:

- **ARIMA+Z** sinaliza **quebras da dinâmica**: o valor que o passado recente não previa. Por construção, o alerta se concentra no primeiro instante da mudança. Nas flags de temperatura predominam sinais negativos (resfriamento brusco, como passagens de frente fria ou chuva convectiva), e nas de umidade, saltos positivos na maioria dos municípios (Porto Alegre é a exceção).
- **Isolation Forest** sinaliza **estados conjuntos raros**. Nesses dados, o atributo dominante dos alertas foi a variação de 24 h da precipitação em Goiânia, Porto Alegre e Feira de Santana. Em Manaus, foram as anomalias de umidade e temperatura. O IF atua, portanto, como detector de "dias de chuva forte após tempo seco" ou de "estiagem quente e seca", conforme o clima local.
- **Hampel** sinaliza **desvios da vizinhança imediata**. Fazer a mediana por horário reduziu à metade a escala robusta em Feira de Santana (σ mediano de 0,76 contra 1,69 °C na temperatura), o que confirma a necessidade de tratar o ciclo diurno. O método não modela a persistência: um episódio de vários dias acaba "absorvido" pela mediana, e o filtro deixa de sinalizar no meio do evento.

**A concordância aponta eventos reais, não erros.** Nos 64 instantes
sinalizados pelos três métodos, 58 têm anomalia de temperatura **negativa**.
A combinação típica é queda de 6 a 10 °C em relação à componente sazonal, com
salto de umidade. Por exemplo, em Goiânia, em 03/10/2017 às 12 UTC, havia
18,4 °C contra 27,3 °C esperados, com 21,7 mm de chuva. É a assinatura de
eventos sinóticos, e não de falha de dados. Isso ilustra o ponto central
deste trabalho: **concordância entre métodos não prova erro de medição**,
pois os três compartilham o mesmo viés de considerar raro o que é
meteorologicamente raro.

**Distribuição temporal.** Em todos os métodos, a primavera (SON) concentra
a maior parcela dos alertas: 43,6% no ARIMA+Z, 49,6% no IF e 30,6% no Hampel.
É a estação de transição, com frentes frias ainda ativas no Sul e o início da
estação chuvosa no Centro-Oeste. Em Manaus, ARIMA+Z e IF sinalizam muito mais
instantes em **2015** (23 e 24) do que nos anos seguintes, e voltam a subir
em **2023–2024**. Esses períodos coincidem temporalmente com os episódios de
El Niño de 2015–16 e 2023–24 e com as secas amazônicas associadas. Já o
Hampel sinalizou só 1 instante em 2015, provavelmente porque um evento persistente de semanas
desloca a própria mediana local. Essa associação é **descritiva**, e um
teste formal exigiria cruzar os alertas com o índice ONI (tabela
`enso_mensal` do projeto).

**Enchentes no RS (abr–mai/2024).** Entre 26/04 e 13/05/2024, a célula
ERA5-Land de Porto Alegre acumulou 320 mm. Só o Hampel aplicado à
precipitação sinalizou os acumulados de 12 h desse período, enquanto o IF
sinalizou um instante (11/05). O ARIMA+Z, por não classificar a
precipitação, não teve alertas nesses dias. O caso mostra (i) a atenuação
de extremos na reanálise e (ii) que um evento extremo **persistente** não
corresponde necessariamente a valores pontuais extremos. Detectar esse
tipo de evento pede indicadores acumulados, e não detectores de outliers
pontuais.

**Sensibilidade aos parâmetros.** No ARIMA+Z, passar de $|Z|>2{,}5$ para
$|Z|>4$ reduz a taxa no treino de 2,17% para 0,24%. No IF, a taxa fora da
amostra superou o $c$ nominal em todos os casos (com $c=0{,}05$, 7,5% na
validação, configuração A). Isso indica deslocamento da distribuição em
relação a 2015–2021, e não erro do método. No Hampel, a variante causal
sinaliza de duas a 2,6 vezes mais que a centrada, porque reage com atraso
às mudanças de regime.

**Experimento sintético** (única situação com verdade conhecida, picos de
±5σ no teste):

| Método (configuração principal) | recall 5σ | recall 3σ | observação |
|---|---|---|---|
| ARIMA+Z ($\lvert Z\rvert>3$) | 0,86 | 0,54 | precisão ≥ 0,43 (limite inferior) |
| Hampel centrado (k=15 d, 3,5) | 0,63 (T) / 0,46 (UR) | 0,26 / 0,21 | precisão incremental 0,96 (T) / 0,925 (UR) |
| IF temporal ($c=0{,}01$) | 0,16 (T) / 0,15 (UR) | — | chega a 0,76 / 0,63 com $c=0{,}05$ |
| IF, anomalia **condicional** (T alta + UR alta) | ≤ 0,22 | — | marginalmente normal |

Picos isolados são o cenário mais favorável ao ARIMA, porque o choque produz
um resíduo grande e imediato, e o mais desfavorável ao IF com $c$ pequeno. O
desempenho fraco do IF no cenário condicional é um resultado negativo
relevante: a vantagem teórica do método multivariado não apareceu nesses
dados com essa engenharia de atributos.

**Custo computacional.** O IF levou 4,5 s e o Hampel 1,9 s para a grade
inteira de 24 configurações. O ARIMA+Z levou 69,5 s, dominados pela busca de
ordens. O tempo é complementar e não decide entre os métodos.

**Qual método para qual série.**
- **Temperatura e umidade, picos e quebras de dinâmica:** ARIMA+Z.
- **Controle de qualidade retrospectivo, barato e robusto:** Hampel centrado por horário.
- **Triagem de estados conjuntos raros:** IF, desde que se aceite a dependência de $c$ e das entradas.
- **Precipitação:** nenhum dos três é adequado sem adaptação. O ARIMA+Z gera flags quase só positivas, e no Hampel o piso de escala domina (Porto Alegre teve 384 alertas de precipitação contra 44 de temperatura). O indicado é um modelo de duas partes (ocorrência + intensidade) ou limiares por percentis climatológicos.

**Outlier estatístico × erro × evento extremo.** Os únicos problemas de
qualidade *de fato* encontrados foram de **extração**, e nenhum veio dos
algoritmos:
- Células oceânicas (Salvador e mais nove municípios costeiros ou lacustres) sem nenhum dado.
- A lacuna sistemática de precipitação no dia 1º às 00 UTC.

Ambos foram identificados na análise exploratória estrutural. Os alertas
dos três métodos, quando inspecionados, são compatíveis com fenômenos
meteorológicos e devem ser tratados como **outliers estatísticos candidatos
a eventos**, não como erros.
"""

MD_LIMITACOES = r"""
## 13. Limitações

- **Sem rótulos de verdade:** não se calculam acurácia, precisão, recall ou F1 nos dados reais. As métricas do experimento sintético valem só para picos artificiais, e a precisão ali é um limite inferior, porque anomalias reais do teste contam como falsos positivos.
- **Reanálise, não estação:** o ERA5-Land suaviza extremos locais e não contém falhas de sensor. O centróide municipal pode cair numa célula pouco representativa ou oceânica.
- **Frequência de 12 h:** as observações das 00 e 12 UTC (21 h e 9 h local) não captam máximas e mínimas diárias. A precipitação é um acumulado e não tem resolução sub-diária.
- **ARIMA:** heterocedasticidade sazonal (Ljung–Box nos resíduos² com $p\approx 0$) torna um limiar $\lvert Z\rvert$ constante desigual entre estações. A sazonalidade não tem termo de tendência, então o aquecimento pode deslocar validação e teste.
- **Isolation Forest:** a proporção sinalizada depende de $c$ e do conjunto de atributos (Jaccard A×B de 0,16 a 0,49). A "variável dominante" é uma heurística.
- **Hampel:** a janela fixa absorve eventos persistentes. Na precipitação, o piso de escala domina a decisão.
- **Comparação:** os métodos não usam as mesmas variáveis (o IF inclui a precipitação), e o critério "temperatura OU umidade" dos univariados é uma escolha de agregação.
- **Amostra:** quatro municípios (um por UF) e uma única realização da injeção sintética por configuração no Hampel. Generalizar para as 1.224 séries do arquivo completo exige reexecução.
"""

MD_CONCLUSAO = r"""
## 14. Conclusão

Os três métodos oferecem perspectivas **complementares, e não
intercambiáveis**, de anomalia em séries climáticas:
- **ARIMA+Z:** quebras da dinâmica temporal, com a maior sensibilidade a picos sintéticos.
- **Isolation Forest:** estados conjuntos raros, dominados pela precipitação nesses dados.
- **Hampel:** desvios locais robustos, muito barato, mas cego a eventos persistentes.

Com orçamentos de alerta semelhantes, três quartos dos instantes sinalizados
foram vistos por um único método. Os poucos casos consensuais correspondem a
eventos sinóticos plausíveis, sobretudo resfriamentos bruscos com aumento de
umidade, e não a erros. Na prática, isso sugere usar os métodos **em
conjunto e com papéis distintos**:
1. **Triagem estrutural** (limites físicos, lacunas e duplicatas), que é onde os erros reais foram encontrados.
2. **Hampel** para controle de qualidade retrospectivo.
3. **ARIMA+Z** para monitoramento operacional de quebras.
4. **IF** como triagem exploratória de condições conjuntas.

O passo seguinte natural é cruzar os alertas com o ONI para testar
formalmente a associação com o ENSO, tema do projeto.
"""

COD_RESUMO_NUMEROS = r"""
# Números usados no resumo, recalculados aqui para conferência.
uniao = F[METODOS].any(axis=1)
so_um = F[METODOS].sum(axis=1).eq(1) & uniao
print(f"Instantes analisados: {len(F):,}")
print("% sinalizado no teste:", {m: round(float(100 * F.loc[F.split == 'teste', m].mean()), 2) for m in METODOS})
print(f"Sinalizados por ≥1 método: {uniao.sum()} | por um único: {so_um.sum()} ({100 * so_um.sum() / uniao.sum():.0f}%) "
      f"| pelos três: {F[METODOS].all(axis=1).sum()}")
print("Jaccard:", {f"{a}×{b}": round(float(jac.loc[a, b]), 3) for a, b in combinations(METODOS, 2)})
print("Recall sintético 5σ:", TABELA["recall sintético 5σ"].to_dict())
"""

MD_REFS_CAB = r"""
## 15. Referências bibliográficas

Todas as referências foram conferidas em 24/10/2026 na API Crossref
(`api.crossref.org/works/<DOI>`), no site do JMLR ou no site da OTexts.
"""

MD_RESUMO = r"""
## Resumo acadêmico (proposta)

**Detecção de outliers em séries climáticas de reanálise: comparação entre resíduos de ARIMA, Isolation Forest e filtro de Hampel**

**Contextualização e objetivo.** Séries meteorológicas misturam erros de
dados e eventos extremos legítimos, e os dois podem aparecer como valores
atípicos. Este trabalho compara três perspectivas complementares de
anomalia: modelagem temporal, detecção multivariada e estatística robusta
local. O objetivo é caracterizar quais observações cada uma identifica e por
que divergem, em vez de apenas contar outliers.

**Metodologia.** Foram usadas séries de 12 h (00 e 12 UTC) de temperatura,
umidade relativa e precipitação do ERA5-Land, de 2015 a 2025, na célula mais
próxima do centróide de Manaus/AM, Feira de Santana/BA, Goiânia/GO e Porto
Alegre/RS (32.144 instantes). Os métodos foram:
- **ARIMA + Z-score:** resíduos de previsão de um passo sobre anomalias sazonais, com ordens escolhidas por BIC.
- **Isolation Forest:** sobre anomalias sazonais, $\log(1+P)$ e diferenças de 24 h.
- **Filtro de Hampel:** mediana e MAD móveis calculados separadamente por horário.

Todos os parâmetros foram estimados apenas em 2015–2021, e as configurações
escolhidas em 2022–2023 e avaliadas em 2024–2025. Sem rótulos reais, a
avaliação combinou concordância entre métodos, sensibilidade a parâmetros,
inspeção meteorológica de casos e um experimento com picos sintéticos de
±5σ.

**Resultados experimentais.** Com orçamentos semelhantes, os métodos
sinalizaram 1,66% (ARIMA+Z), 1,13% (Isolation Forest) e 1,44% (Hampel) dos
instantes do teste. Dos 1.081 instantes sinalizados por algum método, 75%
foram marcados por um único método e 5,9% pelos três (Jaccard entre 0,10 e
0,26). Os casos consensuais são, em 58 de 64 vezes, resfriamentos bruscos
acompanhados de aumento de umidade, compatíveis com eventos sinóticos. A
primavera concentrou 31% a 50% dos alertas, e em Manaus os alertas se
concentraram em 2015 e 2023–2024. Nos picos sintéticos, o recall foi de
0,86 para ARIMA+Z, de 0,46 a 0,63 para Hampel e de 0,15 a 0,16 para o
Isolation Forest com contaminação de 1%. O Isolation Forest não recuperou
anomalias puramente condicionais (recall ≤ 0,22), e nenhum método se mostrou
adequado à precipitação. Os únicos problemas reais de qualidade foram de
extração: células oceânicas sem dados e uma lacuna mensal sistemática de
precipitação, ambos encontrados por verificação estrutural.

**Conclusão.** Os métodos são complementares, e não intercambiáveis. O
ARIMA+Z capta quebras de dinâmica, o Isolation Forest capta estados
conjuntos raros e o Hampel capta desvios locais. Ser marcado como anômalo,
mesmo pelos três métodos, não implica erro de medição: em dados de
reanálise, os alertas correspondem majoritariamente a eventos meteorológicos
plausíveis.

**Palavras-chave:** detecção de anomalias; séries temporais climáticas; ARIMA; Isolation Forest; filtro de Hampel; ERA5-Land.
"""


def secoes_final():
    refs = (Path(__file__).parent / "referencias.md").read_text()
    lista = refs.split("## (a) Lista de referências (ABNT NBR 6023)")[1].split("## (b)")[0].strip()
    return [
        ("md", MD_DISCUSSAO),
        ("md", MD_LIMITACOES),
        ("md", MD_CONCLUSAO),
        ("md", MD_REFS_CAB + "\n" + lista),
        ("md", MD_RESUMO),
        ("md", "Conferência dos números citados no resumo:"),
        ("code", COD_RESUMO_NUMEROS),
    ]
