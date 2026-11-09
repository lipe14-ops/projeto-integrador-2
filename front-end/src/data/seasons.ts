// Estações do ano no hemisfério sul — cálculo a partir das datas reais.
//
// Métodos disponíveis (configuráveis na interface):
// - 'astronomica': as estações começam no instante dos equinócios e solstícios,
//   calculados pelo algoritmo de Jean Meeus (Astronomical Algorithms, cap. 27,
//   precisão de ~1 minuto entre 1000 e 3000) e convertidos para a data civil de
//   America/Sao_Paulo (inclusive o horário de verão histórico). Em 2024, por
//   exemplo, o outono começou em 20/03 e o verão seguinte em 21/12.
// - 'meteorologica': convenção climatológica por trimestres completos
//   (DJF verão, MAM outono, JJA inverno, SON primavera), usada em estatísticas
//   sazonais por coincidir com meses inteiros.
//
// Nenhuma das duas é uma "estação climática" universal: o regime de chuvas de
// cada região (estação chuvosa/seca) não coincide necessariamente com elas.
// Este módulo não importa nada e pode ser verificado por
// `node scripts/check-seasons.ts`.

export type MetodoEstacao = 'astronomica' | 'meteorologica'
export type Estacao = 'verao' | 'outono' | 'inverno' | 'primavera'

export interface DataCivil {
  ano: number
  mes: number // 1–12
  dia: number
}

export interface IntervaloEstacao {
  estacao: Estacao
  nome: string // "Verão"
  rotulo: string // "Verão 2023/24" ou "Outono 2024"
  inicio: DataCivil // primeiro dia da estação (real, não recortado)
  fim: DataCivil // último dia da estação (inclusivo, real)
  inicioVisivel: DataCivil // recortado ao período consultado
  fimVisivel: DataCivil // inclusivo, recortado
}

export const NOMES_ESTACAO: Record<Estacao, string> = {
  verao: 'Verão',
  outono: 'Outono',
  inverno: 'Inverno',
  primavera: 'Primavera',
}

export const ORDEM_ESTACOES: Estacao[] = ['verao', 'outono', 'inverno', 'primavera']

export const DESCRICAO_METODO: Record<MetodoEstacao, string> = {
  astronomica: 'Pelo calendário: cada estação começa no dia oficial de cada ano, por volta de 20–23 de março, junho, setembro e dezembro (estações astronômicas).',
  meteorologica: 'Em trimestres: verão dez–fev, outono mar–mai, inverno jun–ago, primavera set–nov, sempre com meses inteiros (estações meteorológicas).',
}

// ---------------------------------------------------------------------------
// Datas civis como número de dias (UTC) para aritmética simples
// ---------------------------------------------------------------------------
const DIA_MS = 86_400_000

export const diaNumero = (d: DataCivil) => Math.round(Date.UTC(d.ano, d.mes - 1, d.dia) / DIA_MS)

export function dataDoNumero(n: number): DataCivil {
  const dt = new Date(n * DIA_MS)
  return { ano: dt.getUTCFullYear(), mes: dt.getUTCMonth() + 1, dia: dt.getUTCDate() }
}

export const diasNoMes = (ano: number, mes: number) => new Date(Date.UTC(ano, mes, 0)).getUTCDate()

export const formatarData = (d: DataCivil) =>
  `${String(d.dia).padStart(2, '0')}/${String(d.mes).padStart(2, '0')}/${d.ano}`

// ---------------------------------------------------------------------------
// Equinócios e solstícios (Meeus, cap. 27)
// ---------------------------------------------------------------------------
// [A, B, C] dos 24 termos periódicos
const TERMOS: [number, number, number][] = [
  [485, 324.96, 1934.136], [203, 337.23, 32964.467], [199, 342.08, 20.186], [182, 27.85, 445267.112],
  [156, 73.14, 45036.886], [136, 171.52, 22518.443], [77, 222.54, 65928.934], [74, 296.72, 3034.906],
  [70, 243.58, 9037.513], [58, 119.81, 33718.147], [52, 297.17, 150.678], [50, 21.02, 2281.226],
  [45, 247.54, 29929.562], [44, 325.15, 31555.956], [29, 60.93, 4443.417], [18, 155.12, 67555.328],
  [17, 288.79, 4562.452], [16, 198.04, 62894.029], [14, 199.76, 31436.921], [12, 95.39, 14577.848],
  [12, 287.11, 31931.756], [12, 320.81, 34777.259], [9, 227.73, 1222.114], [8, 15.45, 16859.074],
]

// JDE0 médio (anos 1000–3000) para: equinócio de março, solstício de junho,
// equinócio de setembro, solstício de dezembro
const COEFICIENTES: [number, number, number, number, number][] = [
  [2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057],
  [2451716.56767, 365241.62603, 0.00325, 0.00888, -0.0003],
  [2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078],
  [2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032],
]

const rad = (graus: number) => (graus * Math.PI) / 180

/** Instante (UTC, aproximação TT≈UT, diferença ~1 min) do evento 0..3 do ano. */
export function instanteAstronomico(ano: number, evento: 0 | 1 | 2 | 3): Date {
  const y = (ano - 2000) / 1000
  const [a, b, c, d, e] = COEFICIENTES[evento]
  const jde0 = a + b * y + c * y ** 2 + d * y ** 3 + e * y ** 4
  const t = (jde0 - 2451545.0) / 36525
  const w = rad(35999.373 * t - 2.47)
  const deltaLambda = 1 + 0.0334 * Math.cos(w) + 0.0007 * Math.cos(2 * w)
  const s = TERMOS.reduce((soma, [A, B, C]) => soma + A * Math.cos(rad(B + C * t)), 0)
  const jde = jde0 + (0.00001 * s) / deltaLambda
  return new Date((jde - 2440587.5) * DIA_MS)
}

const formatoBrasilia = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Sao_Paulo',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

export function dataCivilBrasilia(instante: Date): DataCivil {
  const partes = Object.fromEntries(formatoBrasilia.formatToParts(instante).map((p) => [p.type, p.value]))
  return { ano: Number(partes.year), mes: Number(partes.month), dia: Number(partes.day) }
}

// ---------------------------------------------------------------------------
// Inícios de estação de um ano
// ---------------------------------------------------------------------------
interface InicioEstacao {
  estacao: Estacao
  dia: number // diaNumero do primeiro dia
}

const cacheInicios = new Map<string, InicioEstacao[]>()

/** Inícios de estação que caem no ano civil ``ano`` (ordem cronológica). */
function iniciosDoAno(metodo: MetodoEstacao, ano: number): InicioEstacao[] {
  const chave = `${metodo}-${ano}`
  const salvo = cacheInicios.get(chave)
  if (salvo) return salvo
  // hemisfério sul: equinócio de março → outono; solstício de junho → inverno;
  // equinócio de setembro → primavera; solstício de dezembro → verão
  const sequencia: Estacao[] = ['outono', 'inverno', 'primavera', 'verao']
  const inicios: InicioEstacao[] =
    metodo === 'astronomica'
      ? sequencia.map((estacao, i) => ({
          estacao,
          dia: diaNumero(dataCivilBrasilia(instanteAstronomico(ano, i as 0 | 1 | 2 | 3))),
        }))
      : sequencia.map((estacao, i) => ({ estacao, dia: diaNumero({ ano, mes: 3 + 3 * i, dia: 1 }) }))
  cacheInicios.set(chave, inicios)
  return inicios
}

function rotular(estacao: Estacao, inicio: DataCivil, fim: DataCivil): string {
  const nome = NOMES_ESTACAO[estacao]
  if (inicio.ano === fim.ano) return `${nome} ${inicio.ano}`
  return `${nome} ${inicio.ano}/${String(fim.ano).slice(2)}`
}

/**
 * Estações que intersectam o período [inicio, fimExclusivo).
 * O verão atravessa a virada do ano e recebe os dois anos no rótulo.
 */
export function intervalosEstacoes(metodo: MetodoEstacao, inicio: DataCivil, fimExclusivo: DataCivil): IntervaloEstacao[] {
  const a = diaNumero(inicio)
  const b = diaNumero(fimExclusivo)
  if (b <= a) return []
  const inicios: InicioEstacao[] = []
  for (let ano = inicio.ano - 1; ano <= fimExclusivo.ano + 1; ano++) inicios.push(...iniciosDoAno(metodo, ano))
  const resultado: IntervaloEstacao[] = []
  for (let i = 0; i < inicios.length - 1; i++) {
    const atual = inicios[i]
    const proximo = inicios[i + 1].dia // exclusivo
    if (proximo <= a || atual.dia >= b) continue
    const real0 = dataDoNumero(atual.dia)
    const real1 = dataDoNumero(proximo - 1)
    resultado.push({
      estacao: atual.estacao,
      nome: NOMES_ESTACAO[atual.estacao],
      rotulo: rotular(atual.estacao, real0, real1),
      inicio: real0,
      fim: real1,
      inicioVisivel: dataDoNumero(Math.max(a, atual.dia)),
      fimVisivel: dataDoNumero(Math.min(b, proximo) - 1),
    })
  }
  return resultado
}

/** Estação de uma data. */
export function estacaoNaData(metodo: MetodoEstacao, data: DataCivil): IntervaloEstacao {
  const proximoDia = dataDoNumero(diaNumero(data) + 1)
  return intervalosEstacoes(metodo, data, proximoDia)[0]
}

/** Quantos dias de cada estação há em um período (ex.: um mês). */
export function partesDoPeriodo(
  metodo: MetodoEstacao,
  inicio: DataCivil,
  fimExclusivo: DataCivil,
): { intervalo: IntervaloEstacao; dias: number }[] {
  return intervalosEstacoes(metodo, inicio, fimExclusivo).map((intervalo) => ({
    intervalo,
    dias: diaNumero(intervalo.fimVisivel) - diaNumero(intervalo.inicioVisivel) + 1,
  }))
}
