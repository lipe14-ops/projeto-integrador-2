# Projeto Integrador 2

O tema escolhido foi el ninõ e o projeto escolhido foi uma plataforma de relatório de historico climático

# Passo a passo: executar o backend completo

Execute os comandos a seguir a partir da raiz do projeto. É necessário ter
Python 3.12 ou superior, `uv` e Docker instalados.

## 1. Instalar as dependências

```sh
uv sync
```

## 2. Iniciar o banco de dados

O backend usa PostgreSQL com PostGIS. O comando abaixo cria ou inicia o
container local:

```sh
docker compose up -d postgis
```

Por padrão, o banco fica disponível em `localhost:5432`, com banco `geodata`
e usuário e senha `postgres`. Para alterar esses valores, crie um arquivo
`.env` na raiz, por exemplo:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/geodata
```

Se as variáveis do Compose forem alteradas, mantenha a `DATABASE_URL` de
acordo com elas.

## 3. Criar as tabelas

```sh
uv run alembic upgrade head
```

## 4. Gerar os arquivos dos municípios

Baixe e prepare a malha municipal, os dados complementares e o arquivo
Parquet usado pelo upload:

```sh
uv run python -m scripts.get_municipios
```

## 5. Enviar os municípios para o banco

Para testar com dois municípios:

```sh
uv run python -m scripts.upload_municipios --limit 2
```

Depois faça a carga completa:

```sh
uv run python -m scripts.upload_municipios
```

## 6. Baixar os dados climáticos

Para baixar os arquivos ERA5-Land, configure as credenciais do CDS conforme a
documentação do `cdsapi` e execute:

```sh
uv run python -m scripts.get_climate
```

Os arquivos são salvos em `data/era5_land`. Arquivos que já existem são
ignorados, permitindo retomar o download.

## 7. Enviar o clima para o banco

```sh
uv run python -m scripts.upload_climate
```

O upload processa um mês por vez. Para carregar somente um período:

```sh
uv run python -m scripts.upload_climate \
	--start-date 2015-01-01 \
	--end-date 2015-12-31
```

Para carregar ou atualizar somente a série ENSO:

```sh
uv run python -m scripts.get_climate --enso-only
uv run python -m scripts.upload_climate --enso-only
```

## 8. Iniciar a API

```sh
uv run uvicorn app.main:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`. Verifique se o backend
está respondendo:

```sh
curl http://127.0.0.1:8000/health
```

A resposta esperada é:

```json
{"status":"ok"}
```

A documentação interativa fica em
`http://127.0.0.1:8000/docs`.

## Execução automática pela pipeline

Depois de instalar as dependências e iniciar o PostGIS, a pipeline executa as
etapas do projeto na ordem correta:

```sh
uv run codigo pipeline
```

Para visualizar os comandos sem executá-los:

```sh
uv run codigo pipeline --dry-run
```

Use `uv run codigo list` para consultar os comandos disponíveis.

# Banco de dados

O projeto usa PostgreSQL com PostGIS. O Compose fornece uma instância local em
`localhost:5432`, com banco `geodata` e credenciais de desenvolvimento
`postgres`/`postgres`. Para usar outros valores, defina `DATABASE_URL` no
ambiente ou em um arquivo `.env`.

Os dados do PostGIS ficam em `data/postgis`, dentro de `/home`, para não ocupar
o filesystem raiz. Em instalações que ainda usam o volume Docker antigo
`codigo_postgis_data`, libere algum espaço na raiz e migre os dados uma única
vez antes de iniciar o serviço com esta configuração:

```sh
sudo docker compose stop postgis
mkdir -p data/postgis
sudo docker run --rm --entrypoint sh \
	-v codigo_postgis_data:/source:ro \
	-v "$PWD/data/postgis:/target" \
	postgis/postgis:17-3.5 \
	-c 'cp -a /source/. /target/'
sudo docker compose up -d postgis
```

O volume antigo é mantido como cópia; não use `docker compose down -v` durante
essa migração.

```sh
uv sync
docker compose up -d postgis
uv run alembic upgrade head
uv run python -m scripts.upload_municipios --limit 2
uv run python -m scripts.upload_municipios
```

O primeiro comando de carga testa dois registros; o segundo importa o arquivo
com lotes de 32 linhas. Cada lote é confirmado separadamente e pode ser
reexecutado com segurança. Use `--batch-size` para ajustar o tamanho dos lotes.

## Carga climática ERA5-Land

```sh
uv run alembic upgrade head
uv run python -m scripts.upload_climate
```

O carregador processa um GRIB mensal e um frame temporal por vez, grava uma
observação por município às 00:00 e 12:00 UTC e confirma cada mês em uma
transação. Para retomar a partir de uma data após interrupção:

```sh
uv run python -m scripts.upload_climate --start-date 2023-09-01
```

`umidade` é umidade relativa em porcentagem, calculada de temperatura e ponto
de orvalho; `temperatura` é Celsius; `precipitacao` é o acumulado do intervalo
de 12 horas em milímetros. O município é associado à célula ERA5 mais próxima
do seu centróide; coordenadas não são duplicadas na tabela climática.

Para baixar o ONI do NOAA sem ler o shapefile nem baixar novamente o ERA5, gere o
CSV mensal e carregue-o no banco:

```sh
uv run alembic upgrade head
uv run python scripts/get_climate.py --enso-only
uv run python -m scripts.upload_climate --enso-only
```

Os dados são atualizados pela chave ano/mês na tabela `enso_mensal`, sem flags
booleanas ou duplicação. `GET /municipios/{codigo_ibge}/clima` retorna a lista
mensal `enso` separada das observações horárias; cada item contém `year`,
`month` e `enso_index`, o valor numérico do ONI.

# Executar a API

Com as dependências instaladas e o banco iniciado e migrado, execute na raiz do
projeto:

```sh
uv run uvicorn app.main:app --reload
```

A API fica disponível em `http://127.0.0.1:8000`. A documentação interativa dos
endpoints fica em `http://127.0.0.1:8000/docs`.

# Pipeline e CLI

Com o PostGIS iniciado e as dependências instaladas, a CLI pode executar todas
as etapas em sequência. A pipeline gera os dados municipais, aplica as
migrações, carrega os municípios, baixa o ERA5-Land e carrega os dados
climáticos:

```sh
uv run codigo pipeline
```

Para executar somente etapas específicas, use os nomes listados em
`uv run codigo list`. A ordem definida pela pipeline é mantida:

```sh
uv run codigo pipeline --only municipios migrar-banco enviar-municipios
uv run codigo pipeline --dry-run
```

Também é possível executar qualquer script individual e encaminhar opções para
ele:

```sh
uv run codigo run enviar-municipios -- --limit 2
uv run codigo run carregar-clima -- --start-date 2015-01-01 --end-date 2015-01-31
uv run codigo run consultar-municipios -- --uf RS
uv run codigo run consultar-clima -- --municipio Porto Alegre --uf RS --variaveis
```

## EDA climática municipal interativa (Marimo)

O notebook [analises/eda_climatica_municipal.py](analises/eda_climatica_municipal.py)
explora a série ERA5-Land carregada em `registro_climatico`, a dimensão
municipal do PostGIS e o ONI mensal. Ele documenta o Shapefile IBGE 2025
(`data/BR_Municipios_2025`) e o catálogo `data/municipios.parquet`. A associação
municipal é feita pelo código IBGE, não pelo nome.

Com as dependências do projeto instaladas e o PostGIS iniciado/migrado:

```sh
uv run marimo edit analises/eda_climatica_municipal.py
```

`pyproject.toml` é a configuração de dependências equivalente a
`requirements.txt`; inclui Marimo, Pandas, NumPy, Plotly, GeoPandas, PyArrow,
SQLAlchemy e o driver PostgreSQL. O notebook não abre os GRIB: usa os dados já
carregados no banco. A consulta inicial é mensal; para evitar varreduras
acidentais da tabela climática (cerca de 8 GiB com índices), a série temporal
por intervalo de anos só roda ao clicar em **Carregar série agregada**. O
coroplético interativo busca geometrias simplificadas no PostGIS para a UF
escolhida; o mapa geral usa pontos de centróides e densidade por célula de 1°.

### Estrutura e métodos observados

- `registro_climatico`: chave `(codigo_ibge, datetime)`, índices pela chave e
  pela data; temperatura em °C, umidade relativa em %, precipitação em mm por
  intervalo de 12 horas; frequência nominal de duas observações diárias UTC.
- `municipio` e `municipio_details`: código IBGE, coordenadas, geometria
  PostGIS, nome, UF, estado e região. O Shapefile 2025 usa `CD_MUN` e CRS
  EPSG:4674; o banco declara geometrias em EPSG:4326.
- `enso_mensal` e `data/era5_land/registro_era5_enso.csv`: ONI mensal.
- Estatísticas: média, mediana, desvio-padrão, variância, quartis, IQR,
  coeficiente de variação, assimetria, curtose, P05/P95 e outliers relativos
  pelo limite de 1,5×IQR. Correlações Pearson/Spearman são calculadas sobre
  município-mês completo; inclinação linear é exploratória e não corrige
  autocorrelação.

### Limitações

- O total exato da tabela toda não é calculado ao abrir o notebook porque isso
  exige varrer bilhões de bytes; tamanho em disco e período são exibidos, e as
  contagens exatas ficam restritas aos períodos consultados.
- As taxas de faltantes são aproximações baseadas em duas observações por dia;
  interprete-as junto da cobertura municipal e do período.
- Os valores representam a célula ERA5-Land mais próxima do centróide, não
  medições independentes dentro de cada polígono. A malha não aumenta a
  resolução espacial da fonte climática.
- Outliers IQR são relativos ao recorte. A frequência de 12 horas não sustenta
  automaticamente definições oficiais de ondas de calor ou secas. Tendências
  de longo prazo exigem climatologia de referência e testes com sazonalidade e
  autocorrelação.
- A associação com ONI usa meses coincidentes; correlação descritiva não
  implica causalidade.
