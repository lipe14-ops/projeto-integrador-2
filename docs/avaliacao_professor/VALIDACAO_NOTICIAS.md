# Validação da verificação automática de notícias

Pergunta do professor: **"qual a confiabilidade da verificação automatizada?"**

Resposta curta: hoje temos três medidas, cada uma com alcance diferente.

1. **Conformidade com a especificação** (benchmark sintético, 67 casos rotulados
   antes da execução): precisão 0,724, revocação 0,913, F1 0,808, taxa de falso
   positivo 0,182. Os erros se concentram em um ponto: o critério temático
   aceita a notícia quando a manchete contém uma palavra de chuva, sem
   verificar se ela **relata a ocorrência** de chuva (estiagem, previsão,
   alerta, política pública e "casa cheia" passam).
2. **Estatísticas do pipeline real** (31 237 vínculos anomalia × notícia): 16,6%
   verificados, 62,0% rejeitados, 21,4% pendentes.
3. **Acurácia no mundo real: ainda não medida.** Não existe padrão-ouro. Deixamos
   pronta uma amostra estratificada de 150 vínculos reais para dois anotadores
   humanos, além do cálculo de precisão, revocação e kappa de Cohen. Até essa
   anotação ser feita, **nenhum número deste documento é uma estimativa da
   acurácia real**.

A validação também encontrou **dois bugs reais** no extrator de metadados.
Ambos foram corrigidos, com teste de regressão (§3.3).

---

## 1. Arquitetura da verificação

```
Google News RSS ──► News Researcher ──► candidatas "discovered"
  (busca por município, Defesa Civil e vizinhos;     │  (URL, manchete, fonte e data ALEGADAS)
   janela de publicação [D−3, D+7])                  ▼
                                         Fact-Checker (cliente HTTP próprio)
                                         reacessa a página, reextrai título/fonte/data,
                                         aplica os critérios 1–10 na ordem, e a
                                         primeira falha decide
                                                     │
                     verified / rejected / pending_verification + evidências (JSON)
                                                     ▼
                         anomaly_news (decisão por vínculo) + news_article (status global)
                         + news_verification_attempt (histórico)
```

- Quem busca não valida. O News Researcher só produz candidatas
  (`news_researcher.py:1-12`). A aprovação depende do Fact-Checker, e isso é
  garantido duas vezes: no código (`repository.py:102`, `_guard_verified`) e no
  banco (`models.py:155`, `CHECK ck_news_verified_requires_fact_checker`).
- A decisão é por **vínculo** (anomalia × notícia): a mesma matéria pode ser
  aprovada para uma anomalia e rejeitada para outra (`repository.py:146-185`).

## 2. Auditoria dos critérios implementados

Referências de linha no estado atual do código. `fact_checker.py` não foi
alterado.

| # | Critério | Implementação | Decisão em caso de falha |
|---|---|---|---|
| 1 | **URL é matéria específica** | `fact_checker.py:199-203` → `text.py:140` (`non_article_reason`): agregadores (`text.py:48`), página inicial, busca, tag e listagem (`text.py:42`), caminho curto demais | `rejected` |
| 2 | **Existência/acessibilidade** | `fact_checker.py:205-218`: 404/410 → rejeita; rede, timeout, 403, 429, 5xx → pendente; redirecionamento para não-matéria → rejeita; sem título ou HTML ilegível → pendente | `rejected` / `pending` |
| 3 | **Manchete confere com a página** | `fact_checker.py:220-229`: sobreposição de tokens ≥ 0,6 (`text.py:158`) com `<title>`/`og:title` ou `<h1>` | `rejected` |
| 4 | **Fonte identificada + nível** | `fact_checker.py:231-236`; `source_tier` em `fact_checker.py:56-63` (oficial, agência, veículo reconhecido, regional/outro) | nunca falha |
| 5 | **Data de publicação na página** | `fact_checker.py:238-254`; extração em `extract.py:83-160` (meta → JSON-LD → `<time>` → data visível). A divergência com a data do buscador fica registrada, mas não decide | `pending` se ausente |
| 6 | **Tema (chuva)** | `fact_checker.py:256-275`: termo forte na manchete (`text.py:13`, `STRONG_THEME`) **ou** ≥ 3 termos fortes no corpo **e** data de evento identificada; remove usos não meteorológicos ("marco temporal", "chuva de gols"; `text.py:24`) | `rejected` |
| 7 | **Geografia** | `fact_checker.py:277-297`: nome do município com maiúsculas, sem acento, mascarando nomes que colidem (`text.py:95`); homônimo em outra UF exige o estado (`text.py:82`); se o nome colide com outro e não está na manchete, exige estado ou vizinho; vizinho (ST_Touches) → `regional` | `rejected` |
| 8 | **Tempo** | `fact_checker.py:299-328`: publicação em [D−3, D+7] (data local BRT); manchete com outro ano → retrospectiva; pistas de retrospectiva (`text.py:30`); data do evento estimada no texto (`text.py:191`) precisa cair em [D−2, D+3] ou no período do acumulado com a mesma tolerância (`fact_checker.py:80`, `orchestrator.py:90`) | `rejected` |
| 9 | **Duplicatas** | `fact_checker.py:159-175, 330-338`: mesmo canonical → `same_article`; mesma manchete e mesma data → `republication`. Não rejeita, só marca | nunca falha |
| 10 | **Confiabilidade** | `fact_checker.py:340-348`: `high`, `medium` ou `low` a partir do nível da fonte e do método da data | nunca falha |
| — | **Evidência insuficiente → pendente** | critérios 2 e 5; `pending` nunca é tratado como aprovado | — |

### Lacunas encontradas na auditoria

- **Não há checagem de polaridade nem de variável.** O critério 6 procura
  palavras como "chuva", "cheia" ou "vendaval", mas não verifica se o texto relata
  **ocorrência** de chuva. "Falta de chuva", "chuva só deve voltar", "previsão de
  chuva", "alerta de tempestade", "projeto contra enchentes" e "casa cheia"
  passam. A variável da anomalia não chega ao Fact-Checker: `VerificationContext`
  não tem esse campo. Na prática, toda anomalia investigada é de chuva positiva
  (`orchestrator.py:257`), mas a matéria pode tratar de calor, seca ou vento.
- **A magnitude não é comparada.** O volume observado (mm) não é confrontado com
  o que a matéria relata.
- **A credibilidade da fonte só é registrada.** `source_tier` e `reliability` não
  influenciam a decisão. Uma página de blog com data visível é aprovada com
  `reliability = low`. Isso é coerente com a especificação, mas a confiabilidade
  precisa ser exibida ou filtrada na interface.
- **O local é inferido por menção, não pelo local do evento.** Qualquer menção
  ao município (por exemplo, "a 260 km de Porto Alegre") ou a um vizinho
  ("BR-116 em direção a Canoas") conta.
- **A deduplicação vale só para a execução.** O registro de canonical e de
  impressões digitais fica na memória da instância do `FactCheckerAgent`
  (`fact_checker.py:135-137`), que é recriada a cada execução. Cópias publicadas
  em execuções (municípios) diferentes não são detectadas.
- **Não há agrupamento explícito por evento.** O "evento" é a anomalia. Uma
  mesma matéria pode sustentar várias anomalias próximas (ARIMA e acumulado,
  dias seguidos). Nos dados reais, 1 111 notícias verificadas estão ligadas a
  mais de uma anomalia.
- **Modo "principais".** 226 das 228 execuções reais usaram `max_verified = 3` e
  6 candidatas por tarefa (`orchestrator.py:58, 349`). Em 632 tarefas, a
  verificação parou antes de examinar todas as candidatas. Por isso a revocação
  real não pode ser medida sobre "todas as notícias existentes", só sobre as
  candidatas efetivamente examinadas.
- **Documentação desatualizada.** `docs/anomalias_noticias/ARQUITETURA.md` (§5,
  item 6) diz "ao menos 2 termos distintos no texto". O código exige 3 termos
  fortes **e** uma data de evento identificada quando a manchete não tem termo de
  chuva (`fact_checker.py:267-274`).

## 3. Estratégia de validação

| Camada | O que mede | O que **não** mede |
|---|---|---|
| Testes unitários (`tests/test_news.py`, 34 testes) | regressões pontuais | desempenho agregado |
| **Benchmark sintético rotulado** (`tests/news_validation/`) | conformidade do Fact-Checker real com a especificação escrita, em cenários difíceis escolhidos de propósito | acurácia no mundo real (os casos não são uma amostra da população) |
| **Estatísticas do pipeline real** (`scripts/amostra_validacao_noticias.py estatisticas`) | volume, distribuição das decisões, motivos, fontes, duplicatas | se as decisões estão certas |
| **Anotação humana de amostra real** (`... amostra` + `... metricas`) | precisão, revocação e taxas de erro reais, e concordância entre anotadores (κ) | ainda não executada: os rótulos humanos estão vazios |
| Reacesso de URLs verificadas (`... acessibilidade`) | se as evidências continuam acessíveis | se o conteúdo ainda confirma o evento |

### 3.1 Especificação de referência (definições operacionais)

O vínculo anomalia D × notícia deve ser **`verified`** somente se **todos** os
critérios abaixo valerem (texto integral em `tests/news_validation/cases.py`):

- **E1 (existência).** A URL é de uma matéria específica, responde com HTTP 2xx e
  não redireciona para uma página que não é matéria.
- **E2 (identidade).** A manchete do buscador corresponde ao título da página.
- **E3 (janela de publicação).** A data de publicação está **na página**, e a data
  local (BRT) cai em [D−3, D+7].
- **E4 (tema/variável).** A matéria relata a **ocorrência** de precipitação ou
  de seus impactos hidrológicos diretos: chuva, temporal com chuva, alagamento,
  enchente, inundação, enxurrada, deslizamento por chuva ou granizo. Não contam
  previsão, alerta, política pública ou prevenção, estiagem, calor, frio, vento
  sem chuva nem usos figurados.
- **E5 (geografia).** O evento ocorreu no município-alvo (`relevant`) ou em um
  município limítrofe (`regional`). Menção incidental, nome de outro município
  que contém o nome do alvo e rio homônimo não contam. Para município homônimo,
  o estado precisa aparecer no texto.
- **E6 (mesmo evento).** A data do evento, quando o texto a indica, cai em
  [D−2, D+3] (ou no período do acumulado, com a mesma tolerância), e a matéria
  não é retrospectiva.

Deve ser **`rejected`** quando algum critério falha de forma conclusiva, e
**`pending_verification`** quando não é possível avaliar: rede, timeout,
403/429/5xx, página sem data ou sem título. Uma republicação continua
`verified`, mas deve vir marcada como duplicata.

### 3.2 Benchmark sintético

**Os dados são sintéticos.** Páginas, manchetes, veículos e URLs foram escritos à
mão (domínios com sufixo `-ficticio`). Os municípios e os contextos (vizinhos,
nomes que colidem, homônimos) são os reais, resolvidos com
`data_source.resolve_municipality`. As anomalias são fictícias: D = 01/05/2024
para Porto Alegre/RS, Rio Verde/GO e Bom Jesus/RS, mais uma anomalia de
acumulado em 04/05/2024 com período de 27/04 a 05/05.

**Procedimento.** O rótulo de cada caso foi decidido a partir da especificação
**antes** da primeira execução. Depois, o `FactCheckerAgent` real rodou com um
HTTP simulado (`BenchmarkHttpClient`, que também simula redirecionamento e
timeout). Nenhum rótulo foi alterado depois da execução. As divergências estão
em `KNOWN_LIMITATIONS` (`tests/news_validation/test_benchmark.py`) como
`xfail(strict=True)`: se o sistema passar a acertar um desses casos, o teste
falha e a limitação tem de ser revista.

**Métrica.** A predição positiva é `verified`. `rejected` e `pending` contam
como predições negativas, e `pending` é informado à parte. Os casos
"ambíguos" têm referência negativa: rejeitar ou deixar pendente são ambos
aceitáveis.

Comando: `uv run python -m tests.news_validation.benchmark docs/avaliacao_professor/execucoes/benchmark_fact_checker.log`

#### Resultado (após as correções da §3.3)

| | Previsto `verified` | Previsto não verificado |
|---|---|---|
| **Deveria verificar (23)** | TP = 21 | FN = 2 |
| **Não deveria verificar (44)** | FP = 8 | TN = 36 |

| Métrica | Valor |
|---|---|
| Precisão | **0,724** (21/29) |
| Revocação | **0,913** (21/23) |
| F1 | **0,808** |
| Taxa de falso positivo | **0,182** (8/44) |
| Taxa de falso negativo | **0,087** (2/23) |
| Acurácia | 0,851 (57/67) |
| Pendentes | 6, todos em casos que deveriam ficar pendentes (0 entre os positivos) |
| Conformidade completa (status + relevância + duplicata) | 0,851 |

Por categoria: positivos 21/23, negativos 28/35, pendentes 6/6, ambíguos 2/3.

**Antes da correção do JSON-LD**, o caso P05 (data só no JSON-LD) ficava
`pending`. Os números eram: TP 20, FN 3, precisão 0,714, revocação 0,870,
F1 0,784, taxa de falso negativo 0,130.

Estes números medem **conformidade com a especificação em casos escolhidos para
serem difíceis**. Eles não são estimativa de precisão ou revocação na população
real: a proporção de casos difíceis aqui é muito maior que a real, e por isso não
calculamos intervalo de confiança.

#### Casos de teste

| ID | Categoria | Cenário | Esperado | Sistema | Conforme |
|---|---|---|---|---|---|
| P01 | positivo | matéria típica: chuva alaga bairros do município-alvo, publicada D+1 | verified | verified (relevant) | sim |
| P02 | positivo | evento em município limítrofe (Canoas) → regional | verified | verified (regional) | sim |
| P03 | positivo | fonte oficial (Defesa Civil, .gov.br) | verified | verified (relevant) | sim |
| P04 | positivo | veículo regional pequeno, data só em elemento visível (confiabilidade baixa) | verified | verified (relevant) | sim |
| P05 | positivo | data de publicação só no JSON-LD | verified | verified (relevant) | sim (falhava antes da correção) |
| P06 | positivo | data de publicação só em `<time datetime>` | verified | verified (relevant) | sim |
| P07 | positivo | anomalia de acumulado: evento datado dentro do período acumulado | verified | verified (relevant) | sim |
| P08 | positivo | publicada antes da anomalia, dentro da janela (D−1) | verified | verified (relevant) | sim |
| P09 | positivo | publicada em D+6 relatando o evento datado de D | verified | verified (relevant) | sim |
| P10 | positivo | outro município (Rio Verde/GO) com nomes que colidem mascarados | verified | verified (relevant) | sim |
| P11 | positivo | município homônimo com o estado no texto (Bom Jesus/RS, "Serra gaúcha") | verified | verified (relevant) | sim |
| P12 | positivo | manchete truncada pelo buscador ("...") | verified | verified (relevant) | sim |
| P13 | positivo | URL com parâmetros de rastreamento (utm_*) | verified | verified (relevant) | sim |
| P14 | positivo | ciclone extratropical com chuva forte | verified | verified (relevant) | sim |
| P15 | positivo | manchete sem termo de chuva; corpo relata evento datado com vários termos | verified | verified (relevant) | sim |
| P16 | positivo | fuso horário: 2024-05-09T01:00Z = 08/05 22h BRT (último dia da janela) | verified | verified (relevant) | sim |
| P17 | positivo | número de 4 dígitos que parece ano na manchete ("2000 casas") | verified | rejected | **não** |
| P18 | positivo | mesmo evento, veículo A (não é duplicata de B) | verified | verified (relevant) | sim |
| P19 | positivo | mesmo evento, veículo B, manchete diferente → independente (não duplicata) | verified | verified (relevant) | sim |
| P20 | positivo | cópia sindicada (mesma manchete e data em outro veículo) → verified + republication | verified | verified (relevant, republication) | sim |
| P21 | positivo | versão AMP da mesma matéria (mesmo canonical) → verified + same_article | verified | verified (relevant, same_article) | sim |
| P22 | positivo | chuva de granizo (precipitação) | verified | verified (relevant) | sim |
| P23 | positivo | manchete em CAIXA ALTA; corpo cita o município normalmente | verified | rejected | **não** |
| N01 | negativo | HTTP 404 (página inexistente) | rejected | rejected | sim |
| N02 | negativo | HTTP 410 (removida) | rejected | rejected | sim |
| N03 | negativo | página inicial do veículo | rejected | rejected | sim |
| N04 | negativo | link do agregador (Google News), não a matéria | rejected | rejected | sim |
| N05 | negativo | página de tag/listagem | rejected | rejected | sim |
| N06 | negativo | página de busca do veículo | rejected | rejected | sim |
| N07 | negativo | URL de matéria que redireciona para a página inicial | rejected | rejected | sim |
| N08 | negativo | manchete alegada não corresponde ao conteúdo da página | rejected | rejected | sim |
| N09 | negativo | cidade certa, data errada (publicada 20/06, fora da janela) | rejected | rejected | sim |
| N10 | negativo | cidade certa, publicada antes da janela (26/04) | rejected | rejected | sim |
| N11 | negativo | fuso horário: 2024-04-28T02:00Z = 27/04 23h BRT (fora da janela) | rejected | rejected | sim |
| N12 | negativo | buscador alega 02/05/2024, página diz 02/05/2023 (ano anterior) | rejected | rejected | sim |
| N13 | negativo | publicada na janela, mas relata outro evento (08/05, fora de 29/04..04/05) | rejected | rejected | sim |
| N14 | negativo | outro município sem relação (Goiânia) | rejected | rejected | sim |
| N15 | negativo | homônimo em outra UF: Bom Jesus (PI) para anomalia de Bom Jesus/RS | rejected | rejected | sim |
| N16 | negativo | município de nome que contém o alvo (Porto Alegre do Norte/MT) | rejected | rejected | sim |
| N17 | negativo | município de nome que contém o alvo (Lucas do Rio Verde/MT) | rejected | rejected | sim |
| N18 | negativo | rio homônimo ("rio Verde") em outra cidade | rejected | rejected | sim |
| N19 | negativo | estiagem com "chuva" na manchete ("falta de chuva") | rejected | verified | **não** |
| N20 | negativo | estiagem sem termo de chuva na manchete | rejected | rejected | sim |
| N21 | negativo | onda de calor; "chuva" aparece só como previsão de retorno | rejected | verified | **não** |
| N22 | negativo | onda de calor sem termo de chuva (outra variável) | rejected | rejected | sim |
| N23 | negativo | frio/geada (outra variável) | rejected | rejected | sim |
| N24 | negativo | incêndio (fora do tema) | rejected | rejected | sim |
| N25 | negativo | previsão (não relata ocorrência) | rejected | rejected | sim (motivo acidental, ver §4) |
| N26 | negativo | alerta meteorológico (não relata ocorrência) | rejected | verified | **não** |
| N27 | negativo | política pública/prevenção com "enchentes" na manchete | rejected | verified | **não** |
| N28 | negativo | uso figurado de "cheia" ("casa cheia") | rejected | verified | **não** |
| N29 | negativo | uso figurado de "chuva" ("chuva de gols") | rejected | rejected | sim |
| N30 | negativo | "marco temporal" (não meteorológico) | rejected | rejected | sim |
| N31 | negativo | prevenção/serviço, chuva só como contexto | rejected | rejected | sim |
| N32 | negativo | retrospectiva de aniversário ("um ano após") | rejected | rejected | sim |
| N33 | negativo | retrospectiva de evento histórico (ano na manchete) | rejected | rejected | sim |
| N34 | negativo | menção incidental ao alvo (distância); evento em Pelotas | rejected | verified | **não** |
| N35 | negativo | menção incidental a vizinho (rota para Canoas); evento em Caxias do Sul | rejected | verified (regional) | **não** |
| PD01 | pendente | timeout/falha de rede | pending | pending | sim |
| PD02 | pendente | HTTP 503 (servidor indisponível) | pending | pending | sim |
| PD03 | pendente | HTTP 403 (bloqueio/paywall) | pending | pending | sim |
| PD04 | pendente | HTTP 429 (limite de requisições) | pending | pending | sim |
| PD05 | pendente | página sem data de publicação | pending | pending | sim |
| PD06 | pendente | página sem título identificável | pending | pending | sim |
| A01 | ambíguo | matéria estadual sem citar o município nem vizinhos | rejected ou pending | rejected | sim |
| A02 | ambíguo | homônimo sem o estado no texto (qual Bom Jesus?) | rejected ou pending | rejected | sim |
| A03 | ambíguo | vendaval sem chuva (vento é outra variável) | rejected ou pending | verified | **não** |

### 3.3 Bugs encontrados e corrigidos

Os dois afetam só `app/climate_news/news/extract.py`. A correção é mínima e cada
um ganhou teste de regressão em `tests/test_news.py`.

1. **O JSON-LD nunca era lido.** `extract_metadata` removia todos os `<script>`
   **antes** de procurar `<script type="application/ld+json">`. Com isso, nunca
   se aproveitavam a data (`datePublished`), o veículo (`publisher`), a manchete
   nem o tipo de página vindos do JSON-LD. A evidência nos dados reais: nas ~29 mil
   decisões gravadas que chegaram a esses critérios (cerca de 24 mil com data
   lida), os métodos `json-ld:datePublished` e `json-ld publisher` aparecem
   **zero** vezes. Correção: ler o
   JSON-LD antes de remover os scripts. Teste:
   `test_json_ld_date_and_publisher_are_read`.
   - **Impacto medido** (`impacto-jsonld`, log `execucoes/impacto_correcao_jsonld.log`).
     Das 2 358 URLs distintas que ficaram pendentes por "data não encontrada",
     reacessamos 40 (semente fixa, 1 req/s). Em **8 das 40 (20%; IC 95% de
     Wilson ≈ 10%–35%)**, a data só é encontrada com a correção. Isso é uma
     estimativa por amostra pequena. As decisões gravadas no banco **não foram
     reprocessadas**: para isso é preciso rodar `cli revalidate` nas
     investigações.
2. **Páginas XHTML com `<?xml ... encoding="UTF-8"?>` falhavam.** O lxml recusa
   `str` que traz declaração de encoding ("Unicode strings with encoding
   declaration are not supported"), e a notícia ficava `pending`. Isso aconteceu
   em 4 vínculos reais. Correção: remover a declaração antes de interpretar o
   HTML. Teste: `test_xhtml_with_xml_encoding_declaration_is_parsed`.

## 4. O que o sistema erra (achados do benchmark)

Os rótulos destes casos **não foram alterados**. Cada um mostra uma situação em
que o sistema associa (ou deixa de associar) uma notícia a uma anomalia de forma
errada.

**Falsos positivos (notícia associada indevidamente à anomalia):**

| Caso | Por que passa | Critério responsável |
|---|---|---|
| N19 estiagem ("Falta de chuva castiga lavouras") | "chuva" na manchete basta; não há negação/polaridade | tema (`fact_checker.py:267`) |
| N21 onda de calor ("chuva só deve voltar na próxima semana") | idem; a variável (temperatura) não é conferida | tema |
| N26 alerta do Inmet | alerta/previsão não é distinguido de ocorrência | tema |
| N27 projeto de prevenção a enchentes | "enchentes" na manchete basta | tema |
| N28 "casa cheia" na Arena | "cheia" é termo forte sem contexto (`text.py:13`) | tema |
| A03 vendaval sem chuva | "vendava" é termo forte; vento ≠ precipitação | tema |
| N34 chuva em Pelotas, "a 260 km de Porto Alegre" | qualquer menção ao município conta | geografia (`fact_checker.py:280`) |
| N35 temporal em Caxias do Sul, "em direção a Canoas" | qualquer menção a vizinho vira `regional` | geografia (`fact_checker.py:281`) |

**Falsos negativos (notícia correta descartada):**

| Caso | Por que falha | Critério responsável |
|---|---|---|
| P17 "mais de 2000 casas" | número de 4 dígitos entre 1900 e 2099 é lido como ano → "retrospectiva" | tempo (`fact_checker.py:305`, `text.py:187`) |
| P23 manchete em CAIXA ALTA | a menção ao município diferencia maiúsculas; como Porto Alegre tem nomes que colidem, a menção que fica só no corpo exige estado ou vizinho | geografia (`fact_checker.py:286-289`) |

**Acerto por motivo acidental.** N25 (previsão para o fim de semana) foi
rejeitada porque "no sábado" foi interpretado como 27/04, uma data passada fora
da faixa do evento. O sistema não entendeu que se tratava de previsão. Com outra
redação, a mesma matéria seria aprovada, como em N26.

**Exposição nos dados reais.** Contamos as manchetes das 3 506 notícias
verificadas que contêm os padrões ligados a esses falsos positivos. Isso **não é
contagem de erros**: cada caso precisa de revisão humana.

| Padrão | Manchetes |
|---|---|
| previsão/alerta/aviso | 480 (13,7%) |
| política/projeto/obra | 46 (1,3%) |
| vendaval/ventania/rajada | 40 (1,1%) |
| frio/geada | 37 (1,1%) |
| calor/temperatura | 26 (0,7%) |
| estiagem/seca/falta de chuva | 17 (0,5%) |
| "casa/lua/agenda cheia" | 0 |

A categoria **previsão/alerta** tem a maior exposição e é a primeira candidata a
um critério novo, por exemplo exigir um verbo de ocorrência no passado ou
rejeitar quando a manchete só contém "previsão", "alerta" ou "prevê". Uma
mudança como essa altera o comportamento do sistema e **não foi feita aqui**.

## 5. Estatísticas do pipeline real

Comando: `uv run python -m scripts.amostra_validacao_noticias estatisticas`.
Log completo em `execucoes/estatisticas_noticias.log`. Banco consultado em
14–15/11/2026. Os números refletem as decisões **gravadas** (antes das correções
da §3.3).

| Item | Valor |
|---|---|
| Execuções de investigação | 228 (226 `completed`, 1 `failed`, 1 `processing`) |
| Municípios investigados | 227 |
| Anomalias investigadas (tarefas) | 9 522 (5 387 ARIMA+Z, 4 135 acumulado) |
| Tarefas sem nenhuma candidata | 1 711 (18,0%) |
| Candidatas examinadas (vínculos) | 31 237 |
| Vínculos `verified` | 5 189 (16,6%): 4 926 `relevant`, 263 `regional` |
| Vínculos `rejected` | 19 377 (62,0%) |
| Vínculos `pending_verification` | 6 671 (21,4%) |
| Notícias distintas (URL) | 17 317: 3 506 verificadas, 10 802 rejeitadas, 3 009 pendentes |
| Anomalias com ≥ 1 notícia verificada | ARIMA+Z: 1 302/5 387 (24,2%); acumulado: 1 523/4 135 (36,8%) |
| Eventos distintos com ≥ 1 notícia verificada | 2 735 pares (município, data); **2 508 episódios** (datas a até 1 dia agrupadas) em 202 municípios |
| Notícias verificadas ligadas a mais de uma anomalia | 1 111 |
| Duplicatas marcadas entre vínculos verificados | 9 `republication`, 0 `same_article` (o mesmo canonical é fundido na mesma linha de `news_article`) |
| Data do buscador diverge da página (> 2 dias) | 521 vínculos |

**Motivo da rejeição** (primeiro critério que falhou, n = 19 377): tema 61,9%;
publicação fora da janela 15,8%; geografia 12,2%; evento datado fora da faixa
6,0%; manchete divergente 1,5%; URL que não é matéria 1,4%; pista de
retrospectiva 0,7%; outro ano na manchete 0,3%; 404/410 0,1%.

**Motivo da pendência** (n = 6 671): data de publicação não encontrada 82,7%;
HTTP 403 8,5%; página sem título 3,8%; HTML vazio 2,1%; timeout/rede 0,9%;
5xx 1,5%; outros.

**Nível da fonte** (todos os vínculos em que foi avaliado): veículo reconhecido
13 754; regional/outro 12 881; oficial 2 536; agência 318. Entre os
**verificados**: reconhecido 2 885 (55,6%), regional/outro 1 960 (37,8%), oficial
210 (4,0%), agência 134 (2,6%). Confiabilidade dos verificados: `high` 3 100,
`medium` 1 978, `low` 111.

**Por região** (verificados/total de vínculos): Sul 26,4% (795/3 006), Sudeste
19,6% (2 138/10 897), Nordeste 14,5% (1 826/12 591), Centro-Oeste 9,9%
(160/1 617), Norte 8,6% (270/3 126). Episódios com notícia verificada: Sudeste
1 081, Nordeste 852, Sul 318, Norte 165, Centro-Oeste 92.

**Reacesso das evidências** (`acessibilidade`, log
`execucoes/acessibilidade_urls_verificadas.log`): de 50 URLs verificadas
sorteadas (semente 20261114, 1 req/s, timeout 10 s, User-Agent genérico),
**50/50 (100%) responderam HTTP 200** sem redirecionamento. Isso mostra só que a
URL responde. Não reconfirma o conteúdo. Com n = 50, o IC 95% de Wilson para a
proporção acessível vai de 92,9% a 100%.

## 6. Protocolo de anotação humana (padrão-ouro)

### 6.1 Amostra

`uv run python -m scripts.amostra_validacao_noticias amostra` (semente
`20261114`, 10 por estrato).

- **População:** os 31 237 vínculos anomalia × notícia (o hash SHA-256 das chaves
  está em `validacao_noticias/amostra_estratos.txt`; se o banco mudar, o hash
  muda).
- **Estratos:** decisão do sistema (verified, rejected, pending) × região (5),
  10 vínculos por estrato, **150 linhas**. A ordem é determinística e as linhas
  saem embaralhadas.
- **Peso amostral:** `peso_amostral = tamanho do estrato / tamanho da amostra
  do estrato`. Ele permite estimar as métricas na população.
- **Arquivos:**
  - `validacao_noticias/amostra_para_anotacao.csv`: completo, com a decisão e os
    motivos do sistema;
  - `validacao_noticias/amostra_para_anotacao_cega.csv`: **sem** a decisão do
    sistema. **Os anotadores devem usar a versão cega**, para não se ancorarem
    na decisão do sistema.

As colunas de rótulo (`rotulo_anotador_1`, `rotulo_anotador_2`,
`rotulo_adjudicado`, `observacao`) estão **vazias**. Nenhum rótulo foi preenchido
automaticamente.

### 6.2 Rótulos

Cada anotador abre a URL e responde, independentemente do outro: *"esta matéria
relata a ocorrência de chuva (ou de seus impactos diretos: alagamento, enchente,
deslizamento etc.) no município da anomalia ou em município vizinho, em datas
compatíveis com a anomalia (o dia ou o período do acumulado, com tolerância de
2 dias antes e 3 depois)?"*

| Rótulo | Quando usar |
|---|---|
| `confirma` | sim: E1–E6 da §3.1, julgados por uma pessoa |
| `nao_confirma` | não: outro lugar, outra data, outro tema (seca, calor, vento), previsão ou alerta sem ocorrência, retrospectiva, política pública, página que não é matéria |
| `indeterminado` | não dá para julgar: página fora do ar, paywall, texto insuficiente |

Em `observacao`, registre o motivo de `nao_confirma` ou `indeterminado` e
qualquer dúvida. Uma terceira pessoa adjudica as discordâncias em
`rotulo_adjudicado`.

**Importante:** `confirma` significa que **a notícia relata** o evento, e
**não** que o evento meteorológico está confirmado. Notícia não é medição.

### 6.3 Cálculo

`uv run python -m scripts.amostra_validacao_noticias metricas ARQUIVO_ANOTADO.csv [--amostra amostra_para_anotacao.csv]`
(o `--amostra` é necessário se o arquivo anotado for a versão cega).
Implementação em `app/climate_news/validation.py`, com testes em
`tests/test_validation_metrics.py`.

- **Rótulo de referência:** `rotulo_adjudicado`, se preenchido; senão, o rótulo
  comum aos dois anotadores. Linhas com discordância não adjudicada e linhas
  `indeterminado` são contadas, mas ficam fora das métricas.
- **Concordância:** κ de Cohen = (p_o − p_e)/(1 − p_e), calculado nas linhas
  com os dois rótulos. Interpretação usual (Landis e Koch): κ < 0,40 é fraca,
  0,41–0,60 moderada, 0,61–0,80 substancial e > 0,80 quase perfeita. Se κ < 0,6,
  a definição dos rótulos precisa ser revista antes de as métricas serem
  levadas a sério.
- **Métricas do sistema** (positivo = `verified`; verdade = `confirma`):
  precisão, revocação, F1, taxa de falso positivo (FP/(FP+TN)) e taxa de falso
  negativo (FN/(FN+TP)). Elas são calculadas sem peso (a amostra como está) e
  **ponderadas pelo peso amostral** (estimativa para a população). A precisão
  ganha intervalo de Wilson de 95%.
- **Leitura correta da revocação:** ela vale para as candidatas que o buscador
  trouxe e que o Fact-Checker examinou (§2, modo "principais"). Não é a
  revocação sobre "todas as notícias que existem".

## 7. Limitações

1. **O benchmark mede conformidade com a especificação, não acurácia real.** Os
   67 casos foram escolhidos para estressar o sistema, e a proporção de casos
   difíceis é muito maior que na população. Por isso precisão e revocação do
   benchmark não podem ser extrapoladas.
2. **Ainda não há padrão-ouro.** A acurácia real só existirá depois da anotação
   da §6. Com 50 vínculos verificados na amostra, o intervalo de 95% da precisão
   terá cerca de ±12 a 14 pontos percentuais (por exemplo, 35/50 → 56%–81%).
3. **Notícia não é confirmação meteorológica.** Uma notícia `verified` mostra
   que **houve cobertura jornalística** compatível com a anomalia, e não que a
   chuva extrema ocorreu ou que o volume do ERA5-Land está correto. A
   ausência de notícia também não indica ausência de evento.
4. **O viés de cobertura do Google News** favorece capitais e cidades grandes,
   além do Sul e do Sudeste. As taxas de verificação por região (Sul 26,4% contra
   Norte 8,6%) refletem, ao menos em parte, cobertura e indexação, e não só a
   qualidade do detector.
5. **A revocação real é limitada pela busca.** São no máximo 6 candidatas por
   tarefa, e a verificação para depois de 3 aprovadas. 18% das tarefas não
   tiveram nenhuma candidata. Notícias que o buscador não retorna nunca são
   avaliadas.
6. **As heurísticas são lexicais.** Tema e geografia dependem de palavras e
   menções (§4), e não de compreensão do texto: não há negação, polaridade,
   tempo verbal nem local do evento.
7. **As decisões gravadas são anteriores às correções da §3.3.** As estatísticas
   da §5 refletem o extrator com os dois bugs. Parte dos 5 517 pendentes por data
   ausente (estimativa de 20%, IC de 10% a 35%) poderia ser decidida após uma
   revalidação.
8. **As páginas mudam.** O reacesso mostra que as URLs continuam no ar, mas o
   conteúdo pode ter sido editado depois da verificação. A evidência gravada
   (`verification_evidence`) é a referência para auditoria.

## 8. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `app/climate_news/validation.py` | métricas (matriz, precisão, revocação, F1, taxas de erro, κ, Wilson, avaliação do CSV) |
| `tests/test_validation_metrics.py` | testes das métricas (valores de referência conhecidos) |
| `tests/news_validation/cases.py` | especificação + 67 casos sintéticos rotulados |
| `tests/news_validation/benchmark.py` | execução do Fact-Checker real e relatório |
| `tests/news_validation/test_benchmark.py` | testes por caso; limitações conhecidas como `xfail(strict=True)` |
| `scripts/amostra_validacao_noticias.py` | `amostra`, `estatisticas`, `metricas`, `acessibilidade`, `impacto-jsonld` |
| `validacao_noticias/amostra_para_anotacao*.csv`, `amostra_estratos.txt` | amostra real para anotação (rótulos vazios) |
| `execucoes/benchmark_fact_checker.log`, `estatisticas_noticias.log`, `acessibilidade_urls_verificadas.log`, `impacto_correcao_jsonld.log` | saídas das execuções |
