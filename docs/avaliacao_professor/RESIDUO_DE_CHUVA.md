# O que é o "resíduo de chuva" no Clima Brasil (Tarefa E)

Auditoria feita no código de produção
(`app/climate_news/detection/arima_zscore.py`, linhas 334–392) e nos registros
gravados em `precipitation_anomaly`.

## 1. Resposta curta

No projeto, "resíduo de chuva" é o **erro de previsão de um passo do modelo
ARIMA, calculado na escala logarítmica** `ln(1 + chuva)`. Das quatro opções
listadas na avaliação, é a (2), "resíduo de uma previsão ARIMA". Também é a (1),
porque o ARIMA é um modelo estatístico aplicado à precipitação. **Não** é a
diferença em milímetros entre a chuva observada e a "esperada" (opção 3),
embora o banco guarde essa diferença numa segunda coluna, `residual_mm`.

O Z-score é calculado sobre o resíduo em log. A coluna em mm serve só para
descrever o evento.

## 2. Definição matemática

Para o município *m* e o dia *t*:

| Símbolo | Nome no código | Significado | Unidade |
|---|---|---|---|
| P_t | `observed_mm` | precipitação observada (ERA5-Land, soma de 00–12 e 12–24 UTC) | mm/dia |
| y_t = ln(1 + P_t) | `y` | chuva transformada; reduz a assimetria e aceita zero | adimensional |
| ŷ_{t\|t−1} | `prediction_t` | previsão de um passo do ARIMA(p,d,q) (com ou sem termos de Fourier), feita só com dias anteriores a *t* e parâmetros estimados só com anos anteriores ao ano de *t* | adimensional |
| **e_t = y_t − ŷ_{t\|t−1}** | **`residual`** | **resíduo = erro de previsão de um passo** | adimensional (log) |
| μ_e, σ_e | `residual_mean`, `residual_std` | média e desvio-padrão dos resíduos do **período de treino** do bloco anual (sem os 30 primeiros dias) | adimensional |
| Z_t = (e_t − μ_e)/σ_e | `z_score` | resíduo padronizado | desvios-padrão |
| P̂_t = exp(ŷ_{t\|t−1}) − 1 | `predicted_mm` | previsão levada de volta para mm | mm/dia |
| P_t − P̂_t | `residual_mm` | diferença em mm, **apenas descritiva** | mm/dia |

O dia é anomalia estatística positiva quando Z_t > 3.

Três cuidados de interpretação:

1. **"Previsão" e "valor esperado" não são a mesma coisa aqui.** Como o
   modelo prevê a média de ln(1 + P), o valor P̂_t = exp(ŷ) − 1 se aproxima de
   um valor **típico** (tipo mediana), e não da média condicional da chuva. A
   média em mm seria maior, por causa da desigualdade de Jensen. Por isso a
   interface não deve chamar P̂_t de "chuva esperada" sem qualificação.
2. **O mesmo excesso em mm pode dar resíduos muito diferentes.** O resíduo é
   uma razão em escala log, e e_t = ln[(1 + P_t)/(1 + P̂_t)]. Um excesso de
   30 mm sobre uma previsão de 1 mm pesa muito mais que 30 mm sobre uma
   previsão de 10 mm (veja o exemplo 2).
3. **Erro de previsão × resíduo do ajuste.** O valor usado é o erro **fora da
   amostra**: o dia *t* não participou da estimação dos parâmetros. O resíduo
   "dentro da amostra" (`fitted.resid`) só é usado para estimar μ_e e σ_e no
   período de treino.

## 3. Exemplos numéricos

### Exemplo 1 — DADOS FICTÍCIOS (didáticos)

Suponha μ_e = 0 e σ_e = 1,0. Os números são inventados para mostrar a conta e
não vêm de nenhum município.

| Caso | P_t observada | P̂_t prevista | ŷ = ln(1+P̂) | y = ln(1+P) | resíduo e_t | Z | `residual_mm` |
|---|---|---|---|---|---|---|---|
| A | 40 mm | 1 mm | 0,693 | 3,714 | **3,02** | **3,02 → anomalia** | 39 mm |
| B | 40 mm | 10 mm | 2,398 | 3,714 | **1,32** | 1,32 → normal | 30 mm |
| C | 5 mm | 0 mm | 0,000 | 1,792 | **1,79** | 1,79 → normal | 5 mm |

Os casos A e B têm a **mesma chuva observada** e diferem por 9 mm de excesso.
Mesmo assim, só A é anomalia, porque o que conta é a razão (1 + P)/(1 + P̂),
não a diferença em mm.

### Exemplo 2 — DADO REAL (Porto Alegre, 23/05/2024)

Fonte: tabela `precipitation_anomaly`, última detecção concluída. O bloco de
2024 foi treinado com 2015–2023, com μ_e = −0,0034 e σ_e = 1,0122. O modelo
escolhido por BIC foi ARIMA(0,0,1) **sem** termos sazonais.

| Grandeza | Valor |
|---|---|
| Chuva observada P_t | 38,66 mm |
| Previsão P̂_t | 0,85 mm |
| y_t = ln(1 + 38,66) | 3,680 |
| ŷ_t = ln(1 + 0,85) | 0,615 |
| Resíduo e_t | 3,063 |
| Z = (3,063 + 0,0034)/1,0122 | **3,03** |
| `residual_mm` = 38,66 − 0,85 | 37,8 mm |

O dia tem notícias verificadas e cai no mês das enchentes de 2024 no RS, mas
**depois** do pico (29/04–05/05). Duas ressalvas:
- a cheia do Guaíba resultou da chuva acumulada nas bacias a montante, não
  da chuva na célula ERA5-Land de Porto Alegre;
- o dia mais chuvoso do pico, 30/04/2024, **não tem dado completo**. O ERA5-Land
  carregado no projeto não tem o registro das 00 UTC do dia 1º de cada mês,
  então o último dia de cada mês fica ausente (ver `RELATORIO_FINAL.md`,
  seção 1).

**O que o exemplo revela sobre o método.** Para a chuva diária de Porto
Alegre, o ARIMA escolhido é praticamente uma linha de base constante: a
previsão em todos os 17 alertas ARIMA de POA ficou entre 0,26 e 2,9 mm. A
chuva diária tem pouca persistência de um dia para o outro, então o modelo
prevê "um dia típico, quase seco". Com σ_e ≈ 1, a regra Z > 3 equivale, na
prática, a um limiar fixo de cerca de **35–45 mm/dia** em POA. Nos dados, o
menor alerta ARIMA foi de 23,9 mm (com previsão de 0,26 mm) e a maioria ficou
acima de 35 mm.

Ou seja, para a chuva o "resíduo" mede sobretudo **quão acima de um dia
típico** foi a chuva, em escala log. Mede pouco a "surpresa em relação aos
dias anteriores". Isso é diferente do que acontece com temperatura e umidade,
séries muito persistentes, em que o AR prevê bem o dia seguinte.

## 4. Nomenclatura proposta

| Hoje | Problema | Proposta (interface e documentação) |
|---|---|---|
| "resíduo de chuva" | sugere uma quantidade de chuva em mm | **"erro de previsão (escala log)"**; em texto para leigos: "o quanto a chuva superou a previsão do modelo" |
| `residual_mm` / "diferença para o esperado" | parece ser a base do Z, mas não é | **"excesso sobre a previsão típica (mm)"**, sempre com o aviso de que o Z vem da escala log |
| "esperado: cerca de X mm" (lista de eventos no Explorar) | P̂ não é a média esperada | **"previsão típica do modelo: X mm"** |
| "anomalia" (genérico) | confundido com evento extremo | "anomalia estatística (Z > 3)", separada de "extremo para o local" (ver `DEFINICOES_ANOMALIA_EXTREMO.md`) |

Implementado nesta entrega:
- descrição dos campos na API (`app/climate_news/schemas.py`);
- texto da lista de eventos (`front-end/src/data/eventos.ts`);
- este documento.

Os nomes das colunas no banco (`residual`, `residual_mm`) **não** foram
alterados, para preservar a compatibilidade com as APIs e o histórico de
execuções.
