# Evolução da área de análise — debate multiagente e decisões

Escopo: `front-end/` (React + Vite + Recharts). Sem bibliotecas novas. Identidade
visual preservada (tokens de `src/index.css`: fundo `--bg #f4f7f5`, tinta
`--ink #0f2f2d`, destaque `--teal #0b6b63`, séries `--rust #c0562b` /
`--blue #1769a8` / `--green #2f7d5b`, ENSO `--el-nino` / `--la-nina`, fontes
Space Grotesk / Hanken Grotesk / JetBrains Mono).

Componentes envolvidos: `pages/HomePage.tsx` (estado, carregamento),
`components/AnalysisSection.tsx` (monta os três gráficos e a comparação),
`components/TimeSeriesChart.tsx` (gráfico Recharts), `components/SummaryCards.tsx`,
`data/api.ts` (conversão da API mensal), `data/climate.ts` (agregação),
`index.css` (layout). Novo: `data/seasons.ts` + `scripts/check-seasons.ts`.

## 1. Diagnóstico da interface atual (Rodada 1)

Observado no código e na página em execução (dados mensais de
`/municipios/{id}/clima/mensal`, 2015–2025):

| # | Agente | Problema | Evidência |
|---|---|---|---|
| D1 | Web Designer | Gráficos com dimensões diferentes: temperatura ocupa a linha inteira (420 px); chuva e umidade dividem a linha (400 px). Áreas de plotagem desalinhadas impedem comparar o mesmo mês entre variáveis. | `AnalysisSection.tsx` (`charts__wide`, `altura` 420/400), `.charts` em grade de 2 colunas |
| D2 | Web Designer | Faixas ENSO em altura total com opacidade 0,72 já são o elemento de fundo dominante; qualquer camada sazonal de fundo competiria com elas (La Niña azul ≈ "inverno frio"). | `TimeSeriesChart.tsx`, `ReferenceArea fillOpacity={0.72}` |
| D3 | UX/UI | Cada gráfico tem seu próprio Brush: para ver o mesmo intervalo nos três, o usuário precisa arrastar três controles. | Brush independente em cada gráfico |
| D4 | UX/UI | Estado de carregamento mostra 3 esqueletos lado a lado, mas o resultado final tem outro arranjo → salto de layout. | `.loading-charts` com 3 colunas |
| D5 | Usuário | "Precipitação acumulada — chuva total no período" sugere total do período inteiro; cada barra é o total do **mês**. | subtítulo do gráfico |
| D6 | Usuário | Não há como saber em que estação está um mês sem fazer conta; "o verão foi mais chuvoso?" exige memória do calendário. | — |
| D7 | Cientista de Dados | **Meses sem dado viram zero** na conversão (`?? 0`): uma lacuna aparece como 0 °C, 0 % ou 0 mm, e entra nas médias dos cartões-resumo. | `data/api.ts`, `carregarClima` |
| D8 | Cientista de Dados | **"Comparar municípios" usa séries sintéticas**: a lista vem de 10 municípios fixos de Goiás (`MUNICIPIOS`) e `serieDoMunicipio` gera dados aleatórios calibrados, porque o cache real é indexado pelo código IBGE e a busca usa `id` (`'rio-verde'`). O usuário vê dados inventados como se fossem reais. | `data/climate.ts` `serieDoMunicipio`, `AnalysisSection.tsx` |
| D9 | Climatologista | Estações não aparecem; ao introduzi-las, há risco de apresentar estações astronômicas como se fossem "estações climáticas" (o Centro-Oeste tem estação chuvosa out–abr, que não coincide com verão astronômico). | — |
| D10 | Meteorologista | Dados mensais: a fronteira astronômica cai em 20–23 do mês, dentro de um ponto mensal. Uma faixa com bordas exatas sobre pontos mensais pode sugerir que o valor do mês pertence a uma só estação. | granularidade da API |
| D11 | Cientista da Computação | Eixo X categórico (rótulo por mês) impede posicionar faixas em datas reais — só em meses inteiros. | `XAxis dataKey="rotulo"` |

## 2. Propostas (Rodada 2)

| # | Agente | Proposta | Benefício | Risco | Prioridade proposta |
|---|---|---|---|---|---|
| P1 | Web Designer | Três gráficos empilhados, 100% da largura, mesma altura definida em CSS (360 px; 300 px ≤ 1100 px; 260 px ≤ 640 px), eixo Y com largura fixa (56 px) para alinhar as áreas de plotagem. | Comparação vertical do mesmo mês; consistência | Página mais longa (≈ +1 tela) | Alta |
| P2 | Cientista da Computação | Eixo X numérico (índice de mês fracionário) para que as faixas sazonais comecem no dia real (ex.: 20/03 = mês + 19/31). | Fronteiras corretas, não "trimestres" | Brush/ticks precisam ser revalidados | Alta |
| P3 | Climatologista | Módulo `seasons.ts` com método configurável: **astronômico** (padrão pedido; equinócios/solstícios pelo algoritmo de Meeus convertidos para data de Brasília) e **meteorológico** (DJF/MAM/JJA/SON). Texto curto dizendo que nenhum dos dois é a estação chuvosa/seca da região. | Rigor; evita confusão astronômico × climatológico | Mais um controle | Alta |
| P4 | Web Designer | Faixas sazonais de fundo, tons dessaturados derivados da paleta (areia, terroso, azul-acinzentado, verde-sálvia), opacidade baixa. ENSO sai do fundo e vira **faixa estreita no topo** da área de plotagem, numa margem reservada acima do maior valor. | Duas camadas de fundo não competem; dados nunca cobertos | Mudança visual no ENSO | Alta |
| P5 | UX/UI | Informação sazonal **dentro do tooltip existente** (nome, início, fim, ano/anos; quando o mês cruza duas estações, as duas com nº de dias). | Um toque no celular entrega valor + estação; acessível sem hover | Tooltip mais alto | Alta |
| P6 | UX/UI | `syncId` comum: cursor e Brush sincronizados entre os três gráficos. | Zoom único; compara o mesmo mês | Nenhum relevante | Média |
| P7 | Cientista de Dados | Meses sem dado como lacuna (linha interrompida, barra ausente, "sem dado" no tooltip) e excluídos das médias. | Representação fiel | — | Alta |
| P8 | Cientista de Dados | Comparação com **dados reais** da API (municípios da mesma UF), com estados de carregamento e erro. | Elimina dados fabricados | Uma requisição extra (≈ tempo do 1º carregamento) | Alta |
| P9 | Usuário | Legenda das estações com **texto** (não só cor) em todos os gráficos; subtítulo da chuva "total de cada mês". | Leitura sem conhecimento prévio | — | Média |
| P10 | Web Designer | Letra inicial da estação (V/O/I/P) dentro de cada faixa. | Redundância sem cor | Poluição com 44 faixas em 11 anos | Baixa |
| P11 | UX/UI | Esqueleto de carregamento empilhado como o layout final. | Sem salto de layout | — | Média |

## 3. Debate crítico (Rodada 3)

- **Opacidade das faixas (Web Designer × Cientista de Dados).** O designer propôs
  opacidade 0,5 para as estações ficarem "visíveis à primeira vista". O cientista
  de dados objetou que, com barras azuis de chuva e linha verde de umidade, o
  fundo esverdeado da primavera e o azul do inverno reduzem o contraste da própria
  série. Acordo: tons claros já dessaturados com opacidade 0,45 sobre branco
  (equivalente visual de ~10% de cor), grade acima das faixas, séries a 100%.
  A estação é "descoberta" pelo tooltip e pela legenda, não precisa gritar.
- **Granularidade mensal × fronteiras exatas (Meteorologista × Climatologista).**
  O meteorologista sugeriu arredondar as estações para meses inteiros, porque o
  dado é mensal. O climatologista recusou: arredondar transformaria o método
  astronômico no meteorológico, que já existe como opção. Decisão: faixas nas
  datas reais **e** tooltip explicitando que o mês de março, por exemplo, tem
  19 dias de verão e 12 de outono — o valor mensal não é atribuído a uma estação só.
- **ENSO no topo (Web Designer × Usuário).** O usuário avaliou que a faixa ENSO
  fina "parece menos importante". Contra-argumento do designer e do climatologista:
  com estações no fundo, manter ENSO em altura total geraria quatro tons
  sobrepostos (El Niño + verão, La Niña + inverno) e confusão de leitura. Mantida
  a faixa no topo, mais saturada que antes (a área é menor), com rótulo na legenda
  e no tooltip — nenhuma informação foi removida.
- **Controle de método (UX/UI × Product Lead).** O UX questionou se um usuário
  leigo precisa escolher método. O Product Lead manteve o controle porque o
  requisito pede método configurável e porque a opção "Ocultar" atende quem quer
  só os dados; o padrão (astronômicas) não exige ação. O controle fica uma única
  vez acima dos gráficos (não repetido em cada um) com uma frase explicativa.
- **Letras V/O/I/P nas faixas (Web Designer × Usuário).** Com 11 anos há 45
  faixas de ~20 px: as letras viram ruído. Decisão: letras só quando o período
  exibido tem até 36 meses; acima disso a legenda textual e o tooltip bastam.
- **Gráficos empilhados deixam a página longa (Usuário × Web Designer).** Aceito
  pelo ganho de comparação: com o eixo X idêntico e alinhado, o mesmo mês fica na
  mesma coordenada horizontal nos três gráficos, e o cursor sincronizado mostra o
  mês nos três ao mesmo tempo.
- **Comparação só com municípios da mesma UF (Cientista de Dados × UX).** Listar
  5.570 municípios num `<select>` é inviável; a lista da UF do município
  selecionado cobre o uso típico (comparar vizinhos). Limitação documentada.

## 4. Decisões do Product Lead (Rodada 4)

**Prioridade alta** — impedem uso correto ou violam o requisito:
1. P8 Comparação com dados reais — exibir dados fabricados como reais compromete a finalidade científica.
2. P7 Lacunas como lacunas — zero falso distorce gráficos e médias.
3. P1 Três gráficos empilhados com dimensões idênticas — requisito obrigatório.
4. P2 + P3 Estações por datas reais, método configurável, documentado.
5. P4 + P5 Faixas discretas + ENSO no topo + estação no tooltip (acesso por toque).

**Prioridade média** — clareza e eficiência:
6. P6 Cursor e zoom sincronizados.
7. P9 Legenda textual das estações e subtítulo correto da chuva.
8. P11 Esqueleto de carregamento empilhado.

**Prioridade baixa** — complementar:
9. P10 Letras nas faixas apenas para períodos curtos.

Critério de aceitação adicional: nenhuma regressão de build; nenhum erro de lint
novo (o projeto já tinha 16 erros e 1 aviso de lint em `Icons.tsx` e
`HomePage.tsx`, fora deste escopo).

## 5. Implementação e validação (Rodada 5)

### Implementado

- **Três gráficos empilhados com dimensões idênticas** — `.charts` em coluna
  única; altura definida uma vez por `--chart-height` (360 px; 300 px até
  1100 px; 260 px até 640 px); eixo Y com largura fixa de 56 px; mesmo cabeçalho
  (título + subtítulo com unidade), mesma legenda e mesmo comportamento
  (tooltip, Brush, download CSV). Escalas Y continuam próprias de cada variável,
  com passos legíveis (1, 2, 5, 10…) e margem superior reservada à faixa ENSO.
- **Estações do ano** (`src/data/seasons.ts`) — método configurável
  (Astronômicas, padrão; Meteorológicas; Ocultar). Astronômicas pelo algoritmo
  de Meeus (erro < 3 min frente aos instantes publicados) convertidas para a
  data civil de `America/Sao_Paulo`, inclusive o antigo horário de verão. Verão
  atravessa a virada do ano e é rotulado "Verão 2023/24". Faixas desenhadas nas
  datas reais (eixo X numérico em meses fracionários) e recortadas ao período
  consultado e ao zoom.
- **Interação** — o tooltip existente passou a mostrar a estação (nome, data
  inicial, data final, ano/anos); se o mês cruza duas estações, mostra as duas
  com o número de dias. Funciona com mouse e com toque (um toque basta). Só o
  gráfico tocado/apontado abre o tooltip; os outros dois mostram o cursor
  sincronizado (antes, no celular, três tooltips cobriam os dados).
  Cursor e zoom (Brush) sincronizados via `syncId`.
- **ENSO** — mantido, agora como faixa estreita acima dos dados (não compete
  com o fundo sazonal nem cobre valores); continua na legenda e no tooltip.
- **Acessibilidade** — legenda das estações com texto; letras V/O/I/P nas
  faixas quando o período tem até 36 meses; controle de método como
  `radiogroup` com descrição associada; `aria-label` de cada gráfico com
  variável, unidade, período e presença das estações.
- **Correções de dados** — meses sem dado viram lacunas (`NaN` → linha
  interrompida, "sem dado" no tooltip, excluídos das médias e "—" nos cartões);
  a comparação agora carrega **dados reais** da API para municípios da mesma UF,
  com estados de carregamento e erro (antes exibia séries sintéticas).
- **Carregamento** — esqueleto empilhado igual ao layout final.

### Arquivos modificados

- `front-end/src/components/TimeSeriesChart.tsx` — eixo numérico, faixas sazonais, ENSO no topo, tooltip com estação, sincronização, lacunas, altura por CSS.
- `front-end/src/components/AnalysisSection.tsx` — layout empilhado, controle de método, comparação real, tooltip por gráfico.
- `front-end/src/data/seasons.ts` (novo) — cálculo das estações.
- `front-end/src/data/api.ts` — meses ausentes como `NaN`.
- `front-end/src/data/climate.ts` — `mediaValida`; agregação e médias ignoram lacunas.
- `front-end/src/components/SummaryCards.tsx` — "—" quando não há valor.
- `front-end/src/pages/HomePage.tsx` — repassa a lista de municípios.
- `front-end/src/index.css` — layout dos gráficos, barra de estações, legenda, tooltip, esqueleto, responsivo.
- `front-end/scripts/check-seasons.ts` (novo) — verificação do módulo de estações.
- `front-end/scripts/visual-check.mjs` (novo) — verificação visual/layout via Chrome DevTools Protocol, sem dependências.
- `docs/frontend/capturas/` — capturas e `relatorio.json` da última execução.

### Testes realizados

| Verificação | Resultado |
|---|---|
| `node scripts/check-seasons.ts` | passou — 8 instantes de referência 2015–2025 com erro < 3 min; datas civis de Brasília; virada do ano; 45 intervalos contíguos sem lacunas em 2015–2025; DJF/MAM/JJA/SON; março/2024 = 19 dias de verão + 12 de outono |
| `npm run build` (`tsc -b && vite build`) | passou (aviso pré-existente de bundle > 500 kB) |
| `npm run lint` | 16 erros e 1 aviso — **os mesmos da linha de base** (`Icons.tsx`, `HomePage.tsx`); nenhum novo |
| `scripts/visual-check.mjs` (Chromium headless, Porto Alegre/RS) | desktop 1440 px e celular 390 px: os 3 gráficos com área idêntica (desktop 1187×324, plotagem 1122×265; celular 330×234, plotagem 265×175), mesma posição horizontal da plotagem, sem rolagem horizontal, legenda das 4 estações nos 3 gráficos, 45 faixas sazonais em 2015–2025, tooltip por mouse e por toque com estação e datas, alternância para método meteorológico |

### Reavaliação do agente Usuário (Porto Alegre/RS)

1. **Selecionar um município** — sem mudança (filtros e mapa preservados); o
   cabeçalho da análise agora mostra município **e período** ("PORTO ALEGRE — RS · 2023–2024").
2. **Escolher um intervalo** — idem; o zoom em qualquer gráfico amplia os três,
   o que antes exigia três arrastes.
3. **Período mais chuvoso** — com os gráficos empilhados e alinhados, a barra
   mais alta de 2023–2024 (set/2023, ~410 mm) é encontrada de imediato; o fundo
   mostra que fica na passagem inverno → primavera, e o tooltip informa os dias
   de cada estação naquele mês.
4. **Comparar estações** — as faixas tornam visíveis, sem conta mental, o mínimo
   de temperatura no inverno e a umidade mais alta no outono/inverno. Ressalva do
   usuário: "astronômica" e "meteorológica" ainda são termos técnicos; a frase
   explicativa sob o controle resolve, mas exige leitura.
5. **Identificar anomalias** — El Niño/La Niña continuam visíveis (faixa no topo
   + tooltip). Ressalva: a plataforma ainda não marca anomalias de precipitação
   no gráfico (ver pendências).
6. **Informações complementares** — tooltip com valor, ENSO e estação num só
   toque; CSV por gráfico mantido.

Veredito do Usuário: **aprovado com ressalvas** (itens 4 e 5).

### Pendências e recomendações

- Marcar no gráfico de precipitação as anomalias detectadas pelo backend (ARIMA
  + Z-Score / acumulados) quando a API de anomalias estiver disponível no front.
- Comparação com municípios de outras UFs (exige um seletor com busca, como o
  dos filtros).
- Opção futura de "estação chuvosa/seca" regional (climatológica), distinta das
  estações astronômicas e meteorológicas.
- Endpoint `/clima/mensal` lento (~10–50 s por município); afeta o fluxo inteiro.
- Erros de lint pré-existentes em `Icons.tsx` (exports não-componentes) e `HomePage.tsx`.
- Não houve teste com leitor de tela real nem em navegadores além do Chromium.

---

## 6. Segunda rodada — melhorias a partir das pendências

Esta rodada partiu do veredito anterior do Usuário (**aprovado com ressalvas**:
item 4, termos técnicos; item 5, anomalias ausentes) e das pendências da
seção 5.

### Diagnóstico

| # | Problema | Evidência |
|---|---|---|
| R1 | Carregamento lento: o Usuário espera 10–80 s a cada município | `/clima/mensal` medido: Manaus **78 s** e outros municípios 16–27 s na primeira consulta; o plano usa a PK, então o custo é I/O aleatório (as ~8 mil linhas do município ficam espalhadas pela tabela de ~8 GB) |
| R2 | Trocar o período refaz a consulta lenta | o cache do cliente usava `município:anoDe:anoAte`, mas a série é sempre de 132 meses |
| R3 | Tarefa 5 ("identificar anomalias") **falhava** | o backend já detecta anomalias e verifica notícias (`/api/climate/*`), mas nada disso aparecia na tela |
| R4 | Termos "astronômicas/meteorológicas" | ressalva do Usuário no item 4 |
| R5 | Comparação só na mesma UF, num `<select>` com centenas de itens | pendência da seção 5 |
| R6 | 16 erros de lint (fábrica de ícones e `setState` dentro de efeito) | `npm run lint` |

### Debate

- **Visão materializada × `CLUSTER` (Cientista da Computação × Engenheiro).**
  `CLUSTER` na PK resolveria a localidade, mas reescreve 8 GB com bloqueio
  exclusivo. A visão `clima_mensal` (~735 mil linhas) é aditiva, construída em
  4 min, pode ser atualizada com `CONCURRENTLY` e devolve exatamente o mesmo
  resultado (diferença máxima de 1e−14 frente à agregação direta, em Porto
  Alegre). **Decisão:** visão + passo `atualizar-clima-mensal` na pipeline.
- **Onde mostrar as anomalias (Web Designer × Cientista de Dados × Usuário).**
  O designer quis evitar um quarto elemento de fundo nos gráficos: estações e
  ENSO já ocupam esse papel. O cientista de dados exigiu a data real do evento
  e não só o mês. **Decisão:** um marcador ▼ discreto na fronteira entre os
  dados e a faixa ENSO, que não cobre barras, posicionado no dia real, só no
  gráfico de **precipitação**. Os detalhes ficam num painel próprio, abaixo dos
  gráficos.
- **Uma ou duas anomalias por tempestade (Usuário × Climatologista).** Os dois
  detectores (dia isolado e acumulado de 3/5 dias) costumam disparar para a
  mesma chuva. O Usuário via isso como duplicação. O climatologista pediu que
  as duas medidas não se perdessem. **Decisão:** períodos que se tocam (até
  2 dias) viram **um evento**, e a frase mostra as duas medidas ("41 mm em um
  dia · 60 mm acumulados em 3 dias").
- **Linguagem (UX × Meteorologista).** O meteorologista aceitou trocar
  "plausible_extreme_event" por "Impacto potencial alto", desde que o critério
  apareça no `title` do selo e na seção "Como os eventos são identificados".
  Os selos levam texto e cor, nunca só cor, e um prefixo para leitor de tela
  ("Para o local:", "Impacto:").
- **Confiança nas notícias (Usuário × Cientista de Dados).** A auditoria manual
  mostrou ~85–90% de acerto da verificação automática depois das correções
  (72% antes). **Decisão:** exibir as notícias com o aviso "A verificação é
  automática e pode errar: confira a matéria antes de citá-la", e diferenciar
  "notícias ainda não pesquisadas" de "busca sem notícia confirmada". Antes, um
  município sem busca parecia não ter notícias.
- **"Ver no gráfico" (UX).** Na primeira versão o botão aparecia entre a frase
  e os selos e quebrava a ordem de leitura no celular (captura 09). Ele passou
  para o fim do item no DOM: no desktop fica posicionado no canto, no celular
  vem depois das notícias.

### Implementado

| Item | Mudança | Arquivos |
|---|---|---|
| R1 | visão `clima_mensal` e endpoint lendo dela; passo `atualizar-clima-mensal` | `alembic/versions/b7e2c4d91a05_*.py`, `app/repositories.py`, `scripts/refresh_clima_mensal.py`, `src/codigo/pipeline.py` |
| R1 | lista de municípios em 6 requisições paralelas (antes, sequenciais) | `src/data/api.ts` |
| R2 | série completa buscada uma vez por município; o período é recortado no cliente | `src/data/api.ts`, `src/pages/HomePage.tsx` |
| R3 | painel **Eventos de chuva extrema**: eventos do período (mais recentes primeiro), frase em linguagem simples, selos, notícias verificadas com fonte, data e link (abre em nova aba), estados de carregamento, erro, "sem análise" e "não pesquisado", e "Como os eventos são identificados" | `src/components/EventosExtremos.tsx`, `src/data/eventos.ts` (novo) |
| R3 | ▼ no gráfico de precipitação, legenda "Evento de chuva extrema", evento no tooltip do mês, destaque com linha-guia via "Ver no gráfico" | `src/components/TimeSeriesChart.tsx`, `src/components/AnalysisSection.tsx` |
| R3 | API: `news_investigated`, vereditos e pico diário em `/api/climate/anomalies` | `app/climate_news/router.py`, `schemas.py` |
| R4 | "Pelo calendário" / "Em trimestres" / "Ocultar", com o termo técnico entre parênteses na nota | `src/data/seasons.ts`, `AnalysisSection.tsx` |
| R5 | comparação com **qualquer** município, por busca (combobox acessível com teclado) | `src/components/BuscaMunicipio.tsx` (novo) |
| R6 | ícones como componentes de função; `HomePage` sem `setState` síncrono em efeito | `src/components/Icons.tsx`, `HomePage.tsx` |

### Medições

| Medida | Antes | Depois |
|---|---|---|
| `/clima/mensal`, município sem cache (5 municípios) | 16–78 s | **6–45 ms** |
| trocar o período | nova consulta (16–78 s sem cache) | **0 requisições** |
| lista de municípios no 1º acesso | 6 páginas em sequência (~3 s) | 6 páginas em paralelo (limitado pela página mais lenta, ~1,2 s) |
| comparar com outro município | 10–80 s | 0,9 s (headless, com carregamento) |
| lint | 16 erros, 1 aviso | **0** |

### Verificações

- `node scripts/check-eventos.ts`: agrupamento, notícias sem repetição,
  textos, "pesquisado".
- `node scripts/check-seasons.ts`: sem regressão.
- `npm run build` e `npm run lint`: sem erros.
- `uv run pytest`: 62 testes, incluindo os novos campos da API.
- `scripts/ux-check.mjs` (Chromium headless): tarefas do Usuário, capturas em
  `docs/frontend/capturas/melhorias/` e `relatorio.json`.

### Reavaliação do agente Usuário

1. **Selecionar município**: a análise aparece em ~2 s, contra até 80 s antes.
2. **Escolher período**: instantâneo, sem novo carregamento.
3. **Período mais chuvoso**: sem mudança, continua imediato.
4. **Comparar estações**: os rótulos "Pelo calendário / Em trimestres" foram
   entendidos sem a nota. **Resolvido.**
5. **Identificar anomalias**: em Porto Alegre 2024, o painel lista 5 eventos,
   todos com notícias, entre eles a enchente de 30/04–02/05 e a de 10–12/05.
   "Ver no gráfico" leva ao ▼ correspondente. **Resolvido.**
6. **Informações complementares**: as notícias abrem a matéria original; o
   selo explica o critério ao passar o cursor.

Veredito do Usuário: **aprovado**. Ressalva menor: algumas notícias aprovadas
são pouco ligadas ao evento (análises, matérias de esporte "sob chuva"). Elas
aparecem com o aviso de verificação automática.

### Pendências

- Eventos só existem para municípios já processados (Porto Alegre e Rio
  Verde). Para os demais, o painel explica isso. Processar mais municípios é
  tarefa de backend (`cli run`).
- Precisão da verificação automática (~85–90%): matérias analíticas ou
  esportivas ainda passam às vezes.
- O zoom não acompanha "Ver no gráfico"; hoje ele rola até o gráfico e
  destaca o marcador.
- Faltam testes com leitor de tela real e em navegadores além do Chromium.


---

## 7. Terceira rodada — aba Notícias, ENSO, mapa e cartão do município

| Pedido | Implementação | Verificação |
|---|---|---|
| Aba só de notícias | `pages/Noticias.tsx`: filtros (município, período do evento, fonte, ordenação), paginação no servidor (20 por página), estados de carregamento, erro, vazio e "limpar filtros"; a página fica montada ao trocar de aba | `scripts/news-check.mjs`: 158 notícias; Rio Verde, "G1" (29), página 2, 2024 por publicação e estado vazio; sem rolagem horizontal no celular |
| Etiqueta El Niño / La Niña | `TagEnso` na aba Notícias e no painel de eventos; fase pelo ONI do mês do evento (dado do Climatologista); texto e cor, com o valor do ONI e o aviso "contexto, não causa" | API: `enso_phase`/`oni` em `related_anomalies` e em `/anomalies` (testado) |
| Inverter ENSO e estações nos gráficos | ENSO virou faixa de fundo em toda a altura (opacidade 0,32); estações foram para a faixa superior (cores cheias, separadores, letras V/O/I/P em períodos curtos); legenda e rótulo do controle atualizados | capturas `melhorias/04` e `05` |
| Mapa com a localização das notícias | `MapaNoticias`: contorno dos estados (IBGE) num painel abaixo dos marcadores; círculos por município com raio proporcional ao número de notícias (com teto); clique filtra a lista; contagens seguem o período e a fonte | captura `noticias/06`; endpoint `/municipalities` com filtros (testado) |
| Linhas sem sentido no mapa | **Causa 1:** ao clicar num polígono, o Chrome dá foco ao `<path>` e desenha o contorno de foco como o retângulo envolvente do polígono (376×562 px, maior que o mapa), visto como linhas retas que seguem o zoom e o arraste. Removido em `.leaflet-interactive` (sem `tabindex`, então não afeta o teclado). **Causa 2:** a malha `qualidade=minima` vira segmentos retos com zoom no estado; trocada por `intermediaria` (MG: 1,8 MB, ~0,6 s). **Causa 3:** o renderizador SVG só tinha 10% de folga, o que expunha o recorte ao arrastar; agora tem `padding: 1` | `scripts/map-check-estado.mjs`: `document.activeElement` = `path.leaflet-interactive` com `outline: auto`; capturas `mapa/estado_4` (linha preta) × `corrigido_4` (sem linha) e `estado_3` × `intermediaria_3` |
| Informações restantes do município | `<details>` "Mais informações do município" no cartão: mesorregião, microrregião, densidade demográfica, domínio, região e unidade geomorfológica (com explicação no `title`), coordenadas da sede e fonte | captura `municipio/02` |

Pendência de dados: `regiao_geomorfologica` chega truncada da carga original
(ex.: "…da Bacia Se"). A correção é no `scripts/get_municipios.py`.
