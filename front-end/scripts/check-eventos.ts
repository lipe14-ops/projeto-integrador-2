// Verificação do agrupamento de eventos de chuva (sem dependências):
//   node scripts/check-eventos.ts
import assert from 'node:assert/strict'
import { agruparEventos, descreverAnomalia, formatarPeriodo, rotuloAvaliacao } from '../src/data/eventos.ts'
import type { AnomaliaChuva, NoticiaVerificada } from '../src/data/api.ts'

const anomalia = (id: string, data: string, extra: Partial<AnomaliaChuva> = {}): AnomaliaChuva => ({
  id, data, detector: 'arima_zscore', observadoMm: 50, previstoMm: 2, dias: 1, status: 'scientifically_reviewed',
  avaliacaoClima: 'very_heavy_for_location', avaliacaoTempo: 'plausible_significant_event', picoDiarioMm: 50,
  noticiasVerificadas: 0, noticiasPesquisadas: true, faseEnso: null, oni: null, ...extra,
})
const noticia = (id: string, datas: string[], publicadaEm: string): NoticiaVerificada => ({
  id, url: `https://x.com/${id}`, manchete: id, fonte: 'X', publicadaEm, confiabilidade: 'high', relevancia: 'relevant', datasAnomalia: datas,
})

// Enchente de maio/2024 em POA: acumulado de 5 dias terminando em 02/05 + dia isolado 23/05
const eventos = agruparEventos(
  [
    anomalia('acc', '2024-05-02', { detector: 'accumulation_percentile', dias: 5, observadoMm: 103, avaliacaoClima: 'exceptional_accumulation', avaliacaoTempo: 'plausible_extreme_event' }),
    anomalia('dia', '2024-04-30', { observadoMm: 40 }), // dentro do período do acumulado (28/04–02/05)
    anomalia('isolado', '2024-05-23', { observadoMm: 39 }),
  ],
  [
    noticia('n1', ['2024-05-02'], '2024-05-03T10:00:00Z'),
    noticia('n2', ['2024-04-30', '2024-05-02'], '2024-05-01T10:00:00Z'), // ligada às duas anomalias: aparece uma vez
    noticia('n3', ['2024-05-23'], '2024-05-23T10:00:00Z'),
  ],
)
assert.equal(eventos.length, 2, 'detecções sobrepostas viram um evento só')
const [maio, isolado] = eventos
assert.equal(maio.inicio, '2024-04-28')
assert.equal(maio.fim, '2024-05-02')
assert.equal(maio.anomalias.length, 2)
assert.deepEqual(maio.noticias.map((n) => n.id), ['n2', 'n1'], 'notícias sem repetição, em ordem de publicação')
assert.equal(maio.avaliacao.texto, 'Acumulado excepcional', 'prevalece a avaliação mais alta')
assert.equal(maio.impacto?.nivel, 'alto')
assert.equal(maio.principal.id, 'acc')
assert.deepEqual(isolado.noticias.map((n) => n.id), ['n3'])
assert.equal(maio.pesquisado, true)
assert.equal(agruparEventos([anomalia('np', '2022-01-01', { noticiasPesquisadas: false })], [])[0].pesquisado, false)

// intervalo de até 2 dias ainda é o mesmo episódio; 3 dias separa
assert.equal(agruparEventos([anomalia('a', '2023-09-04'), anomalia('b', '2023-09-06')], []).length, 1)
assert.equal(agruparEventos([anomalia('a', '2023-09-04'), anomalia('b', '2023-09-08')], []).length, 2)

// textos
assert.equal(formatarPeriodo('2024-05-12', '2024-05-12'), '12 mai 2024')
assert.equal(formatarPeriodo('2024-04-28', '2024-05-02'), '28 abr – 2 mai 2024')
assert.equal(formatarPeriodo('2023-12-30', '2024-01-02'), '30 dez 2023 – 2 jan 2024')
assert.equal(descreverAnomalia(anomalia('x', '2023-09-04', { observadoMm: 145.8, previstoMm: 2.9 })), '146 mm em um dia (esperado: cerca de 3 mm)')
assert.equal(descreverAnomalia(anomalia('x', '2023-09-05', { detector: 'accumulation_percentile', dias: 5, observadoMm: 162.9 })), '163 mm acumulados em 5 dias')
assert.equal(rotuloAvaliacao(null).texto, 'Em avaliação')
assert.equal(rotuloAvaliacao('within_normal_variability').nivel, 'baixo')

console.log('check-eventos: todas as verificações passaram')
