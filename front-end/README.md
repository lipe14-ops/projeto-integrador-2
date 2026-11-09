# Front-end — Clima Brasil

Aplicação React, TypeScript e Vite para explorar os dados climáticos municipais retornados pela API do projeto.

## Executar

Primeiro, inicie o back-end seguindo as instruções do [guia do backend](../docs/execucao-backend.md). Depois, nesta pasta:

```sh
npm install
npm run dev
```

O servidor Vite encaminha as chamadas iniciadas em `/api` para `http://127.0.0.1:8000`. Para usar outra URL da API, defina `VITE_API_URL` no ambiente do Vite.

## Estrutura

- `src/pages`: páginas da aplicação.
- `src/components`: interface, gráficos, cartão municipal e mapa.
- `src/data/api.ts`: consultas aos endpoints de municípios e clima.
- `src/data/climate.ts`: tipos, agregações e formatação das séries.

## Verificar e gerar a versão de produção

```sh
npm run build
npm run preview
```
