# Respostas às observações da avaliação — Clima Brasil

Filipe Nascimento Soares e Guilherme Marinheiro de Oliveira — 14/11/2026

Cada resposta indica onde estão o método, os números e o código. Os números
vêm de execuções reprodutíveis (`docs/avaliacao_professor/resultados/` e
`RELATORIO_FINAL.md`, seção 9). Nenhum foi digitado à mão.

> **Correção feita durante a revisão.** Uma revisão independente da análise
> encontrou uma falha no carregamento dos dados: falta o registro das 00 UTC do
> dia 1º de todos os meses, e por isso o **último dia de cada mês fica sem
> total diário**. Isso gerava acumulados extrapolados na virada do mês e
> alertas do ARIMA inflados no dia 1º. Os 34.801 eventos calculados sobre dado
> incompleto foram **excluídos** das análises (classe `dado_incompleto`), e a
> exposição passou a contar só os dias cujo dia anterior também é válido. Os
> números abaixo já estão corrigidos. A correção na origem (recarregar os dados
> e refazer a detecção nacional) está pendente.

---

## 1. "Existem trabalhos que usam ARIMA + Z-score sobre os resíduos?"

**Sim para o princípio, não para a nossa aplicação específica.**

- **O princípio está estabelecido.** Marcar uma observação cujo erro de
  previsão de um passo passa de *c* desvios-padrão é o mesmo que verificar se
  ela cai fora do intervalo de predição ŷ ± c·σ̂. Hyndman e Athanasopoulos
  (2021, §5.5) apresentam essa equivalência.
  - Base estatística: Fox (1972), Tsay (1988) e Chen e Liu (1993).
  - **Leigh et al. (2019)**, *Science of the Total Environment*, é o trabalho
    mais próximo do nosso: ARIMA com previsão de um passo à frente, desvio-padrão
    dos resíduos do treino e anomalia quando o valor sai do intervalo de 99%
    (equivale a |Z| > 2,6 sobre o resíduo), em dados de rios (turbidez,
    condutividade e nível). Acurácia acima de 0,80, e os autores recomendam
    combinar métodos, como fazemos com ARIMA, percentis e acumulados.
  - Outras aplicações em dados ambientais: Hill e Minsker (2010), com modelo
    AR e intervalo de predição para dados de vento; Yu et al. (2014), com
    séries hidrológicas.
  - Revisão: Blázquez-García et al. (2021) formalizam a regra
    |x_t − x̂_t| > τ e citam esses trabalhos.
- **A aplicação à chuva diária não foi encontrada.** Não localizamos trabalho
  revisado por pares que aplique ARIMA + Z sobre resíduos para **precipitação
  diária**, nem com reanálise, nem no Brasil. Os trabalhos com chuva diária,
  como Durre et al. (2010), fazem controle de qualidade com outros testes.
- **Conclusão:** usamos o método validado por Leigh et al. (2019) em dados
  ambientais e o adaptamos à chuva diária. Essa adaptação é nossa e foi
  avaliada com dados reais (abaixo).

**O que medimos ao reexecutar o detector numa amostra estratificada de 100
municípios** (protocolo em `RELATORIO_FINAL.md`, §2.2; só dias cujo dia
anterior é válido):

- **Cauda pesada.** A taxa mediana de alertas Z > 3 é **0,78%**, contra
  0,135% numa distribuição normal (P10–P90 entre municípios: 0,26%–1,94%).
  Para Z > 4 a diferença é ainda maior: 0,065% contra 0,003%.
- **Simulação nula.** Em 20 séries sintéticas de chuva **sem nenhum evento**
  (com ciclo sazonal), a taxa de Z > 3 vai de 0% a 1,28%, com mediana de
  0,40%. Ela depende da forma da distribuição gama: 0,85% com forma 0,5,
  0,37% com 0,7 e 0,11% com 1,0. Logo, parte dos alertas reais é esperada
  só pela assimetria e pelos zeros da chuva.
- **Heterocedasticidade sazonal.** A variância do resíduo muda com a estação
  em **98%** dos municípios (teste de Brown–Forsythe). A mediana da razão
  entre o maior e o menor desvio-padrão sazonal é 1,92. Com σ único, os
  alertas se concentram nas estações mais variáveis.
- **Não substitui um detector de extremos.** Só **22%** dos alertas são dias
  ≥ P99 dos dias chuvosos locais, e o ARIMA marca **38%** dos dias ≥ P99.
- **Na chuva, o ARIMA vira uma linha de base.** O modelo escolhido por BIC é
  quase sempre de ordem baixa e sem sazonalidade. Funciona como uma linha de
  base quase constante em escala log: em Porto Alegre, Z > 3 equivale a cerca
  de 35–45 mm/dia.

**Recomendações:**
- modelar a variância sazonal da chuva, como já fazemos no novo detector de
  temperatura e umidade;
- tratar os extremos por percentis locais ou pela teoria de valores extremos
  (Coles, 2001);
- relatar sempre a taxa empírica de alertas.

Referências completas e verificadas: `referencias_verificadas.md`.

---

## 2. "Qual a diferença entre anomalia e evento extremo?"

São **eixos diferentes**, e a plataforma não usa mais os termos como
sinônimos. Código: `analysis/classification.py`. Documento:
`DEFINICOES_ANOMALIA_EXTREMO.md`.

| Eixo | Pergunta | Critério no projeto | Base |
|---|---|---|---|
| Anomalia estatística | O valor surpreendeu o modelo? | \|Z\| > 3 no erro de previsão | IPCC (2022): desvio em relação a uma referência |
| Evento meteorológico extremo | É raro **para o lugar e a época**? | ≥ P95/P99 da climatologia local dos anos anteriores; acumulado de 3 ou 5 dias ≥ P99 | IPCC (2022); OMM-1310 (2023); ETCCDI |
| Evento climático extremo | O padrão anômalo persiste por uma estação ou mais? | **não detectado**: 11 anos é pouco | IPCC (2022) |
| Evento de impacto | Houve dano? | notícia verificada (indício, não prova) | SREX (2012); OMM-1150 |

**Números reais (chuva):**
- das **181.226** anomalias do ARIMA contadas, **38,1% são apenas
  estatísticas**: o volume é comum para o lugar e a época;
- 61,9% são extremos locais ou sazonais;
- 15,5% têm intensidade alta (≥ 50 mm/dia ou ≥ 100 mm em 5 dias).

**Por que um extremo pode não ser anomalia.** Uma chuva persistente, sem pico
isolado, não dispara o Z diário. Ela só aparece no detector de acumulados.

---

## 3. "Qual a confiabilidade da verificação automática das notícias?"

Agora ela é **mensurável**. Documento: `VALIDACAO_NOTICIAS.md`.

- **Benchmark de 67 casos sintéticos**, com rótulos definidos antes da
  execução: positivos, negativos, pendentes e ambíguos.

  | Métrica | Valor |
  |---|---|
  | Precisão | **0,72** |
  | Revocação | **0,91** |
  | F1 | **0,81** |
  | Falsos positivos | 18% |
  | Falsos negativos | 9% |

- **Erros encontrados** (mantidos como testes de limitação conhecida):
  matérias sobre seca, previsões e alertas tratados como chuva ocorrida,
  projeto de lei "contra enchentes" e menção de passagem à cidade. O
  verificador aceita qualquer palavra de chuva na manchete e não recebe a
  variável da anomalia.
- **Dois bugs reais corrigidos**, com testes de regressão: o JSON-LD das
  páginas nunca era lido, e páginas XHTML derrubavam o leitor.
- **Pipeline real:**
  - 9.522 anomalias investigadas;
  - 31.237 vínculos entre anomalia e notícia: 16,6% verificados, 62,0%
    rejeitados e 21,4% pendentes;
  - 50 de 50 URLs verificadas ainda respondem.
- **Limitação:** o benchmark mede conformidade com a especificação, não a
  acurácia real. Para isso há uma **amostra real de 150 vínculos**, cega e
  estratificada, pronta para dois anotadores, com cálculo de kappa. **Ela
  ainda não foi anotada.**
- **As notícias acompanham a força do evento.** Nas 9.520 anomalias
  investigadas, a proporção com notícia confirmada cresce com a chuva: 17% abaixo
  de 20 mm, 24% entre 20 e 40 mm e 32% entre 40 e 60 mm. Nos acumulados extremos
  (3 a 5 dias ≥ P99), chega a 37%. Nos eventos de intensidade alta, é 37%,
  contra 26% nos demais. Ressalvas:
  - entre os eventos diários, as notícias não separam "extremo para o local"
    (26%) de "só anomalia" (27%);
  - falta medir quantas notícias o sistema acharia em dias comuns (grupo de
    controle). Sem isso, não dá para afirmar que as notícias melhoram o acerto
    da detecção.
- **Princípio:** notícia indica impacto, mas não confirma o fenômeno
  meteorológico.

---

## 4. Mapa coroplético

Implementado na página **Mapa nacional** da plataforma (API `/api/analysis`).

- **Malha:** polígonos municipais reais do IBGE, ligados pelo código IBGE.
- **Métricas:**
  - frequência por 1.000 dias válidos, que é comparável entre municípios;
  - contagem, com aviso de que não é comparável;
  - intensidade;
  - participação de cada estação e de outono + inverno;
  - estação predominante, por teste qui-quadrado com correção FDR;
  - razão El Niño/neutro e La Niña/neutro.
- **Filtros:** variável, classe (anomalia, extremo ou impacto), período,
  estação e fase ENSO.
- **Legenda:** traz unidade, definição e período. Municípios com menos de 20
  eventos ficam **hachurados** e os sem dados ficam **pontilhados**, nunca
  pintados como zero.
- **Painel do município:** ao clicar, o município é comparado com o estado, a
  região e o Brasil.

---

## 5. "O que é o resíduo de chuva?"

Documento: `RESIDUO_DE_CHUVA.md`.

**É o erro de previsão de um passo do ARIMA, em escala logarítmica:**

e_t = ln(1 + P_obs) − ŷ_{t|t−1},   Z_t = (e_t − μ_e)/σ_e

- O resíduo **não** é a diferença em mm.
- A "previsão em mm", exp(ŷ) − 1, é um valor **típico** (do tipo mediana), e
  não a média esperada.
- **Exemplo fictício:** 40 mm com previsão de 1 mm dão Z = 3,02. Os mesmos
  40 mm com previsão de 10 mm dão Z = 1,32. O que conta é a **razão**, não a
  diferença.
- **Exemplo real** (Porto Alegre, 23/05/2024):

  | Grandeza | Valor |
  |---|---|
  | Observado | 38,66 mm |
  | Previsão típica | 0,85 mm |
  | Resíduo e_t | 3,063 |
  | Z | (3,063 + 0,0034)/1,0122 = **3,03** |

- **Nomenclatura corrigida** na interface e na API: "esperado" passou a
  "previsão típica do modelo".

---

## 6. "O caso de POA indica majoritariamente outono/inverno. Como isso se distribui nos outros municípios?"

Analisamos **todos os municípios com dados (5.535)**, com o mesmo período e a
mesma cobertura (3.071 dias válidos de chuva em cada um).

**Método:**
- **Normalização.** Usamos a frequência por dia válido de cada estação, porque
  as estações têm tamanhos diferentes. Sem preferência, cada estação teria
  25%.
- **Contagem de eventos.** Dias anômalos seguidos contam como um só evento.
- **Teste.** Qui-quadrado por município, com correção FDR, exigindo pelo menos
  20 eventos.

**Chuva, todas as anomalias válidas, 2017–2025:**

| | Verão | Outono | Inverno | Primavera | Outono + inverno |
|---|---|---|---|---|---|
| **Porto Alegre** (29 eventos) | 7,0% | 27,4% | 27,4% | 38,2% | **54,8%** (q = 0,16, não significativo) |
| Mediana dos municípios do RS | | | | | 56,2% |
| Região Sul (agregado) | 18,7% | 24,7% | 25,3% | 31,3% | 50,0% |
| Nordeste (agregado) | 35,6% | **37,7%** | 10,7% | 15,9% | 48,4% |
| **Brasil (agregado)** | **35,5%** | 28,4% | 10,3% | 25,7% | 38,7% |

**Resposta:**

1. **Em POA, o predomínio de outono/inverno é fraco.**
   - Outono + inverno somam 54,8%, pouco acima dos 50% esperados sem
     preferência.
   - O que mais distingue POA é o **verão com poucos eventos** (7%). A
     estação de maior frequência é a primavera.
   - O resultado se repete com os eventos que têm notícia: 53,9%.
2. **É um traço regional, do RS, e não nacional.**
   - POA fica perto da mediana gaúcha (56,2%).
   - No Sul, as quatro estações têm participações próximas, com menos eventos
     no verão.
3. **No Brasil, o padrão é o oposto.** Entre os 4.872 municípios com pelo
   menos 20 eventos:

   | Padrão | Municípios |
   |---|---|
   | Predomínio de **verão** (Sudeste e Centro-Oeste) | 37,3% |
   | Sem predomínio | 30,9% |
   | Predomínio de outono (concentrado no **Nordeste**, onde 47% dos municípios seguem esse padrão) | 18,5% |
   | Predomínio de inverno | **0,9%** |

4. **Temperatura e umidade.**
   - Na **umidade abaixo do esperado** (ar mais seco), o outono/inverno é forte
     em POA (**75,7%**, q = 0,053) e na maior parte do Sul (mediana de 70%).
   - Se a observação veio do notebook com temperatura e umidade, é nessa
     variável que o padrão se confirma.

**Cuidados de interpretação:**
- **"Não significativo" não quer dizer "uniforme".** Com cerca de 20–30
  eventos por município, o teste tem pouco poder estatístico: cerca de 14% para
  o perfil típico do Sul. Por isso comparamos as **participações**, e não só a
  significância.
- **A distribuição sazonal das anomalias depende do método** (seção 1).
  - Mesmo assim, uma referência independente do modelo confirma o quadro
    nacional: dias ≥ P99 da climatologia local, numa amostra de 100
    municípios, ficaram 44,8% no verão e 7,8% no inverno.
  - Para a chuva, a conclusão "regional, não nacional" se mantém.
- **ENSO:** a comparação entre El Niño, La Niña e fase neutra é **apenas
  exploratória**. Em 2017–2025 houve só 2 a 3 episódios por fase, e os
  eventos de municípios vizinhos não são independentes.
