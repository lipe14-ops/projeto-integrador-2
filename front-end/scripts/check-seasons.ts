// Verificação do módulo de estações (sem dependências):
//   node scripts/check-seasons.ts
// Referências: instantes publicados (UTC) de equinócios/solstícios.
import assert from 'node:assert/strict'
import {
  dataCivilBrasilia,
  estacaoNaData,
  instanteAstronomico,
  intervalosEstacoes,
  partesDoPeriodo,
} from '../src/data/seasons.ts'

const referencias: [number, 0 | 1 | 2 | 3, string][] = [
  [2023, 3, '2023-12-22T03:27Z'],
  [2024, 0, '2024-03-20T03:06Z'],
  [2024, 1, '2024-06-20T20:51Z'],
  [2024, 2, '2024-09-22T12:44Z'],
  [2024, 3, '2024-12-21T09:21Z'],
  [2025, 0, '2025-03-20T09:01Z'],
  [2025, 1, '2025-06-21T02:42Z'],
  [2015, 0, '2015-03-20T22:45Z'],
]
for (const [ano, evento, esperado] of referencias) {
  const erroMin = Math.abs(instanteAstronomico(ano, evento).getTime() - Date.parse(esperado)) / 60000
  assert.ok(erroMin < 3, `${ano}/${evento}: erro de ${erroMin.toFixed(1)} min`)
}

// conversão para data civil de Brasília: solstício de 22/12/2023 03:27 UTC = 22/12 00:27 BRT
assert.deepEqual(dataCivilBrasilia(instanteAstronomico(2023, 3)), { ano: 2023, mes: 12, dia: 22 })
// equinócio de 20/03/2024 03:06 UTC = 20/03 00:06 BRT; 2015-03-20 22:45 UTC = 20/03 19:45 BRT
assert.deepEqual(dataCivilBrasilia(instanteAstronomico(2024, 0)), { ano: 2024, mes: 3, dia: 20 })

// virada do ano: verão 2023/24 de 22/12/2023 a 19/03/2024
const verao = estacaoNaData('astronomica', { ano: 2024, mes: 1, dia: 15 })
assert.equal(verao.estacao, 'verao')
assert.equal(verao.rotulo, 'Verão 2023/24')
assert.deepEqual(verao.inicio, { ano: 2023, mes: 12, dia: 22 })
assert.deepEqual(verao.fim, { ano: 2024, mes: 3, dia: 19 })
assert.equal(estacaoNaData('astronomica', { ano: 2024, mes: 3, dia: 20 }).estacao, 'outono')
assert.equal(estacaoNaData('astronomica', { ano: 2024, mes: 6, dia: 20 }).estacao, 'inverno')
assert.equal(estacaoNaData('astronomica', { ano: 2024, mes: 9, dia: 21 }).estacao, 'inverno')
assert.equal(estacaoNaData('astronomica', { ano: 2024, mes: 9, dia: 22 }).estacao, 'primavera')

// intervalos contíguos, sem lacunas nem sobreposição, cobrindo exatamente o período
const periodo = intervalosEstacoes('astronomica', { ano: 2015, mes: 1, dia: 1 }, { ano: 2026, mes: 1, dia: 1 })
assert.equal(periodo[0].estacao, 'verao')
assert.deepEqual(periodo[0].inicioVisivel, { ano: 2015, mes: 1, dia: 1 })
assert.equal(periodo[0].rotulo, 'Verão 2014/15')
assert.deepEqual(periodo.at(-1)!.fimVisivel, { ano: 2025, mes: 12, dia: 31 })
for (let i = 1; i < periodo.length; i++) {
  const anterior = Date.UTC(periodo[i - 1].fimVisivel.ano, periodo[i - 1].fimVisivel.mes - 1, periodo[i - 1].fimVisivel.dia)
  const atual = Date.UTC(periodo[i].inicioVisivel.ano, periodo[i].inicioVisivel.mes - 1, periodo[i].inicioVisivel.dia)
  assert.equal(atual - anterior, 86_400_000, `lacuna entre ${periodo[i - 1].rotulo} e ${periodo[i].rotulo}`)
}
const ordem = ['verao', 'outono', 'inverno', 'primavera']
periodo.forEach((p, i) => assert.equal(p.estacao, ordem[i % 4]))
assert.equal(periodo.length, 45) // 11 anos × 4 + verão final 2025/26

// meteorológicas: DJF/MAM/JJA/SON
const djf = estacaoNaData('meteorologica', { ano: 2024, mes: 2, dia: 29 })
assert.equal(djf.rotulo, 'Verão 2023/24')
assert.deepEqual(djf.inicio, { ano: 2023, mes: 12, dia: 1 })
assert.deepEqual(djf.fim, { ano: 2024, mes: 2, dia: 29 })
assert.equal(estacaoNaData('meteorologica', { ano: 2024, mes: 3, dia: 1 }).estacao, 'outono')

// mês que atravessa duas estações: março/2024 = 19 dias de verão + 12 de outono
const marco = partesDoPeriodo('astronomica', { ano: 2024, mes: 3, dia: 1 }, { ano: 2024, mes: 4, dia: 1 })
assert.deepEqual(marco.map((p) => [p.intervalo.estacao, p.dias]), [['verao', 19], ['outono', 12]])

for (let ano = 2015; ano <= 2025; ano++) {
  const linha = [0, 1, 2, 3].map((e) => {
    const d = dataCivilBrasilia(instanteAstronomico(ano, e as 0 | 1 | 2 | 3))
    return `${String(d.dia).padStart(2, '0')}/${String(d.mes).padStart(2, '0')}`
  })
  console.log(ano, 'outono', linha[0], 'inverno', linha[1], 'primavera', linha[2], 'verão', linha[3])
}
console.log('check-seasons: todas as verificações passaram')
