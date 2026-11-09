# Anomalias de precipitação × notícias — instalação e execução

Sistema multiagente que detecta anomalias de precipitação (ARIMA + Z-Score),
revisa cada uma cientificamente, procura notícias reais em torno de cada data,
verifica cada notícia de forma independente e expõe o resultado em
`GET /api/climate/news`.

- Arquitetura, diagrama de agentes e modelo de dados: [ARQUITETURA.md](ARQUITETURA.md)
- Resultados reais e validação: [RELATORIO_VALIDACAO.md](RELATORIO_VALIDACAO.md)

## 1. Instalação

Pré-requisitos: os mesmos do backend ([guia do backend](../execucao-backend.md)). São Python ≥ 3.12,
`uv` e PostgreSQL/PostGIS com `registro_climatico` carregado.

```sh
uv sync                    # inclui statsmodels, httpx e pytest (grupo dev)
uv run alembic upgrade head  # cria pipeline_run, precipitation_anomaly, news_* (revisão 9f764edda274)
```

É preciso acesso à internet para a investigação (news.google.com e os sites
das notícias). A detecção funciona sem rede.

## 2. Execução

### Pipeline completo (detecção + investigação)

```sh
uv run python -m app.climate_news.cli run --municipio "Porto Alegre" --uf RS
```

Opções principais:

| Opção | Padrão | Efeito |
|---|---|---|
| `--start/--end AAAA-MM-DD` | série inteira | recorte da série |
| `--threshold` | 3.0 | limiar de \|Z\| |
| `--seasonal auto\|fourier\|none` | auto | sazonalidade decidida por BIC, fixa ou desligada |
| `--initial-train-years` | 2 | anos usados só como treino (não pontuados) |
| `--no-accumulation` | — | desliga o detector suplementar de acumulados |
| `--window-before/--window-after` | 3 / 7 | janela de publicação, em dias em torno da anomalia |
| `--workers` | 3 | investigações em paralelo |
| `--max-candidates` | 15 | candidatas por data, somando todas as consultas |
| `--include-rejected` | — | investiga também anomalias rejeitadas pela revisão científica |
| `--no-neighbors` | — | não consulta municípios vizinhos |
| `--only-dates D1 D2…` | — | investiga só essas datas (útil em testes) |

### Etapas separadas

```sh
uv run python -m app.climate_news.cli detect --municipio "Rio Verde" --uf GO
uv run python -m app.climate_news.cli investigate --detection-run <uuid>
uv run python -m app.climate_news.cli resume --investigation-run <uuid>   # reprocessa pendentes/falhas
uv run python -m app.climate_news.cli revalidate --investigation-run <uuid>  # reverifica as notícias já encontradas (sem nova busca)
uv run python -m app.climate_news.cli show --run <uuid>                   # trilha de auditoria em JSON
```

Também está disponível na CLI do projeto como `uv run codigo run anomalias-noticias -- run --municipio ...`.

### Escala nacional (todos os municípios)

```sh
uv run alembic upgrade head   # cria precipitacao_diaria (série diária em ordem de município)
uv run python -m app.climate_news.cli detect-all --workers 6          # ~6 h para 5.573 municípios
uv run python -m app.climate_news.cli investigate-all --follow --principais 3
```

- `detect-all`: processos paralelos. É retomável, pula os municípios já
  detectados com a versão atual do algoritmo e registra erros sem parar a
  execução. A visão `precipitacao_diaria` dá a mesma série do caminho antigo
  (verificado em Porto Alegre: índice, valores e ausentes iguais) e lê um
  município em ~1,4 s, contra ~150 s na tabela bruta.
- `investigate-all`: municípios mais populosos primeiro. Com `--principais N`,
  roda só a consulta principal (município + termos de evento), decodifica
  2N candidatas e para após N notícias aprovadas por data. Se a maioria das
  datas falhar (bloqueio do buscador), pausa `--pausa-bloqueio` minutos e
  retoma. Com `--follow`, espera as detecções que ainda estão rodando.
- Custo estimado sem `--principais`: ~27 requisições ao Google por data, ou
  ~80 dias para ~170 mil datas. Com `--principais 3`: ~7 por data. Mesmo assim
  são semanas de execução contínua, e o buscador pode limitar o acesso.

### Detector como script independente (CSV, sem banco)

```sh
# série diária: colunas date, precipitation_mm
uv run python -m app.climate_news.detection.arima_zscore --csv chuva.csv \
    --out-csv anomalias.csv --out-json relatorio.json

# acumulados ERA5 de 12 h (como no export do banco), filtrando um município
uv run python -m app.climate_news.detection.arima_zscore \
    --csv analises/outliers/clima_4_municipios.csv --era5-12h \
    --date-col datetime --value-col precipitacao \
    --filter-col municipio --filter-value "Porto Alegre"
```

Uso como biblioteca (DataFrame):

```python
from app.climate_news.detection.preparation import prepare_daily_series
from app.climate_news.detection.arima_zscore import DetectionConfig, detect_anomalies

series, quality = prepare_daily_series(df, date_col="date", value_col="precipitation_mm")
result = detect_anomalies(series, DetectionConfig(z_threshold=3.0), quality)
result.anomalies_frame()
```

## 3. API

Com a API no ar (`uv run uvicorn app.main:app`), a documentação Swagger fica em
`http://127.0.0.1:8000/docs`, seção *Anomalias climáticas e notícias*.

| Endpoint | Descrição |
|---|---|
| `GET /api/climate/news` | notícias por **data da anomalia** |
| `GET /api/climate/anomalies` | anomalias no período, com o número de notícias verificadas |
| `GET /api/climate/municipalities` | municípios com análise, contagens (filtráveis por período e fonte) e coordenadas |
| `GET /api/climate/runs/{id}` | trilha de auditoria de uma execução |

Os mesmos endpoints respondem em `/climate/...`, para o proxy do Vite (que
remove o prefixo `/api`).

Parâmetros de `/api/climate/news`: `start_date`, `end_date` (obrigatórios,
aplicados a `anomaly_date`), `municipality`, `uf`, `codigo_ibge`, `source`
(trecho do nome ou do domínio), `verification_status` (padrão `verified`),
`sort_by` (`anomaly_date` | `published_at`), `order` (`asc` | `desc`), `page`
e `limit` (1–100).

Erros: `422` para data inválida ou `start_date > end_date`; `404` para
município inexistente.

Exemplos reais da base local estão em [RELATORIO_VALIDACAO.md](RELATORIO_VALIDACAO.md#exemplos-de-requisição-e-resposta).

## 4. Testes

```sh
uv run pytest            # 61 testes
uv run pytest -m "not db"  # só os que não usam banco
```

Os testes de banco criam e recriam `<banco>_test` no mesmo servidor
(`TEST_DATABASE_URL` sobrescreve). O banco principal não é tocado. Nenhum teste
acessa a internet: buscador e páginas são simulados.

| Arquivo | Cenários |
|---|---|
| `tests/test_detection.py` | sem anomalias, picos isolados, evento prolongado, sazonalidade, ausentes, muitos dias secos, dados inconsistentes, agregação ERA5, **ausência de vazamento de dados futuros** |
| `tests/test_news.py` | regressões da auditoria manual ("Marco Temporal", outro evento na janela, retrospectiva, menção sem evento datado), notícia real e relacionada, URL inexistente, manchete incompatível, data errada ou ausente, outro município, vizinho, duplicada, publicada depois da janela, retrospectiva, fora do tema, página inicial/busca, nenhuma notícia, erro de busca, homônimos |
| `tests/test_orchestrator.py` | revalidação (matéria saiu do ar → rebaixada), fluxo completo, data com falha → execução `failed` e `resume`, revalidação sem duplicar, `CHECK` do banco, anomalias rejeitadas preservadas |
| `tests/test_api.py` | intervalo válido, sem notícias, início > fim, data inválida, município inexistente, paginação, várias notícias por anomalia, notícia ligada a várias anomalias, filtro por data da anomalia, rejeitadas nunca como verificadas, filtros combinados e ordenação, OpenAPI |
