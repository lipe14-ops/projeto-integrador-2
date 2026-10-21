# Clima Brasil

Dashboard web de análise climática municipal (Projeto Integrador · Ciência da Computação).
React 19 + TypeScript + Vite, **sem bibliotecas de gráfico ou mapa**: os gráficos e o mapa são SVG próprio.

## Como rodar

```bash
npm install
npm run dev      # desenvolvimento
npm run build    # typecheck + build de produção
```

## Estrutura

```
src/
  App.tsx                      # shell + navegação (Explorar / Sobre)
  index.css                    # tokens de design e estilos
  components/
    Header/Header.tsx
    SearchFilters.tsx          # busca com autocomplete, período, Aplicar/Limpar
    MunicipioMap.tsx           # mapa SVG com zoom, arraste e seleção
    MunicipioCard.tsx          # "Município selecionado"
    SummaryCards.tsx           # temperatura, precipitação, umidade
    AnalysisSection.tsx        # Mensal/Anual, janelas, comparação, 3 gráficos
    TimeSeriesChart.tsx        # linha/barras, faixas El Niño/La Niña, brush, tooltip, CSV
    Methodology.tsx            # metodologia + FAQ (accordions)
  data/
    climate.ts                 # municípios, episódios ENSO, séries de exemplo, agregação
    goias.ts                   # contorno + malha esquemática de Goiás
  pages/HomePage.tsx, Sobre.tsx
```

## Dados de demonstração

- As séries (2010–2025) são **sintéticas**, calibradas para que Rio Verde — GO tenha média de
  24,1 °C, 127 mm/mês e 62 %. Não são valores observados.
- Os episódios de El Niño/La Niña são uma aproximação do ONI (NOAA/CPC).
- O mapa é esquemático (contorno simplificado de Goiás + células de municípios).

### Ligando dados reais

1. Em `src/data/climate.ts`, troque `serieDoMunicipio(m)` por uma chamada à sua API/arquivos
   (ERA5-Land agregado por município). O formato esperado é `{ temp[], chuva[], umid[] }`
   com um valor por mês, de jan/2010 a dez/2025.
2. Em `src/data/goias.ts`, substitua `CELULAS` por polígonos do GeoJSON de malhas municipais do IBGE
   (o componente `MunicipioMap` só precisa de `{ id, d }` por município).
3. Adicione os demais municípios à lista `MUNICIPIOS` (ou carregue-a da API).

## Interações

- Busca de município (teclado: ↑ ↓ Enter Esc), anos inicial/final, **Aplicar filtros** / **Limpar**.
- Clique nos municípios cadastrados do mapa; botões +/− e arraste para navegar.
- Mensal/Anual, 12 meses / 5 anos / 10 anos / Personalizado, **Comparar municípios**.
- Em cada gráfico: tooltip ao passar o mouse, **Baixar** (CSV) e barra inferior para ampliar
  (arraste as alças ou a seleção; as alças também respondem às setas do teclado).
