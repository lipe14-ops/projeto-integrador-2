export const ANO_INICIO = 2015
export const ANO_FIM = 2025
export const TOTAL_MESES = (ANO_FIM - ANO_INICIO + 1) * 12
export const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
export const ANOS = Array.from({ length: ANO_FIM - ANO_INICIO + 1 }, (_, i) => ANO_INICIO + i)

export interface Municipio {
  id: string
  nome: string
  uf: string
  ibge: string
  regiao: string
  lat: number
  lon: number
  temp: number // média do período (°C)
  chuva: number // média mensal acumulada (mm)
  umid: number // média do período (%)
  estado?: string
  populacao?: number | null
  anoPopulacao?: number | null
  bioma?: string | null
  areaKm2?: number | null
}

export const MUNICIPIOS: Municipio[] = [
  { id: 'rio-verde', nome: 'Rio Verde', uf: 'GO', ibge: '5218805', regiao: 'Centro-Oeste', lat: -17.72, lon: -51.04, temp: 24.1, chuva: 127, umid: 62 },
  { id: 'goiania', nome: 'Goiânia', uf: 'GO', ibge: '5208707', regiao: 'Centro-Oeste', lat: -16.68, lon: -49.25, temp: 24.3, chuva: 135, umid: 63 },
  { id: 'anapolis', nome: 'Anápolis', uf: 'GO', ibge: '5201108', regiao: 'Centro-Oeste', lat: -16.33, lon: -48.95, temp: 23.2, chuva: 140, umid: 66 },
  { id: 'jatai', nome: 'Jataí', uf: 'GO', ibge: '5211909', regiao: 'Centro-Oeste', lat: -17.88, lon: -51.72, temp: 23.8, chuva: 128, umid: 61 },
  { id: 'catalao', nome: 'Catalão', uf: 'GO', ibge: '5205109', regiao: 'Centro-Oeste', lat: -18.17, lon: -47.94, temp: 22.9, chuva: 124, umid: 62 },
  { id: 'itumbiara', nome: 'Itumbiara', uf: 'GO', ibge: '5211503', regiao: 'Centro-Oeste', lat: -18.41, lon: -49.22, temp: 25.0, chuva: 120, umid: 60 },
  { id: 'mineiros', nome: 'Mineiros', uf: 'GO', ibge: '5213103', regiao: 'Centro-Oeste', lat: -17.57, lon: -52.55, temp: 24.0, chuva: 124, umid: 60 },
  { id: 'caldas-novas', nome: 'Caldas Novas', uf: 'GO', ibge: '5204508', regiao: 'Centro-Oeste', lat: -17.74, lon: -48.63, temp: 24.3, chuva: 132, umid: 63 },
  { id: 'formosa', nome: 'Formosa', uf: 'GO', ibge: '5208004', regiao: 'Centro-Oeste', lat: -15.54, lon: -47.34, temp: 23.0, chuva: 118, umid: 59 },
  { id: 'luziania', nome: 'Luziânia', uf: 'GO', ibge: '5212501', regiao: 'Centro-Oeste', lat: -16.25, lon: -47.95, temp: 22.8, chuva: 130, umid: 63 },
]

export const MUNICIPIO_PADRAO = MUNICIPIOS[0]

export const rotuloMunicipio = (m: Municipio) => `${m.nome} — ${m.uf}`

export const normalizar = (s: string) =>
  s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[–—-]/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()

export function buscarMunicipio(texto: string): Municipio | undefined {
  const t = normalizar(texto)
  if (!t) return undefined
  return MUNICIPIOS.find((m) => normalizar(rotuloMunicipio(m)) === t) ?? MUNICIPIOS.find((m) => normalizar(m.nome) === t)
}

export const rotuloMes = (i: number) => `${MESES[i % 12]}/${String(ANO_INICIO + Math.floor(i / 12)).slice(2)}`

// ---------- El Niño / La Niña (aproximação do ONI, NOAA/CPC) ----------
export type TipoEnso = 'el-nino' | 'la-nina'
export interface EpisodioEnso {
  tipo: TipoEnso
  inicio: number // índice de mês (inclusivo), 0 = jan/2010
  fim: number // índice de mês (exclusivo)
}
const ep = (tipo: TipoEnso, a: number, m1: number, b: number, m2: number): EpisodioEnso => ({
  tipo,
  inicio: (a - ANO_INICIO) * 12 + (m1 - 1),
  fim: (b - ANO_INICIO) * 12 + m2,
})
export const EPISODIOS_ENSO: EpisodioEnso[] = [
  ep('el-nino', 2010, 1, 2010, 4),
  ep('la-nina', 2010, 7, 2011, 4),
  ep('la-nina', 2011, 8, 2012, 3),
  ep('el-nino', 2014, 10, 2016, 5),
  ep('la-nina', 2016, 8, 2016, 12),
  ep('la-nina', 2017, 10, 2018, 3),
  ep('el-nino', 2018, 10, 2019, 6),
  ep('la-nina', 2020, 8, 2021, 5),
  ep('la-nina', 2021, 8, 2023, 2),
  ep('el-nino', 2023, 5, 2024, 5),
  ep('la-nina', 2024, 10, 2025, 3),
]

function ensoPorMes(): number[] {
  const out = new Array<number>(TOTAL_MESES).fill(0)
  for (const e of EPISODIOS_ENSO) for (let i = e.inicio; i < e.fim && i < TOTAL_MESES; i++) out[i] = e.tipo === 'el-nino' ? 1 : -1
  return out
}

// ---------- Séries mensais ----------
export interface SerieClima {
  temp: number[]
  chuva: number[]
  umid: number[]
}

function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const gauss = (r: () => number) => Math.sqrt(-2 * Math.log(r() || 1e-9)) * Math.cos(2 * Math.PI * r())
const hash = (s: string) => [...s].reduce((h, c) => (Math.imul(h, 31) + c.charCodeAt(0)) >>> 0, 7)
const media = (v: number[]) => v.reduce((a, b) => a + b, 0) / v.length

const PERFIL_TEMP = [0.0, 0.1, 0.0, -0.3, -0.9, -1.5, -1.6, -0.9, 0.6, 1.5, 1.1, 0.4]
const PERFIL_CHUVA = [1.15, 1.0, 1.05, 0.55, 0.15, 0.03, 0.02, 0.04, 0.25, 0.75, 1.1, 1.25]
const PERFIL_UMID = [78, 80, 79, 72, 62, 52, 47, 45, 50, 60, 72, 78]

const cache = new Map<string, SerieClima>()

export function registrarSerieReal(idMunicipio: string, serie: SerieClima) {
  cache.set(idMunicipio, serie)
}

export function serieDoMunicipio(m: Municipio): SerieClima {
  const hit = cache.get(m.id)
  if (hit) return hit
  const rnd = mulberry32(hash(m.id))
  const enso = ensoPorMes()
  const mediaPerfilChuva = media(PERFIL_CHUVA)
  const temp: number[] = []
  const chuva: number[] = []
  const umid: number[] = []
  for (let i = 0; i < TOTAL_MESES; i++) {
    const mo = i % 12
    temp.push(m.temp + 1.9 * PERFIL_TEMP[mo] + 0.45 * enso[i] + 0.04 * (i / 12) + gauss(rnd) * 0.45)
    const ruido = Math.exp(gauss(rnd) * 0.38 - 0.07)
    const c = (m.chuva / mediaPerfilChuva) * PERFIL_CHUVA[mo] * ruido * (1 - 0.12 * enso[i])
    chuva.push(c)
    umid.push(PERFIL_UMID[mo] + (c / (m.chuva / mediaPerfilChuva) - PERFIL_CHUVA[mo]) * 6 - 1.2 * enso[i] + gauss(rnd) * 2.6)
  }
  // calibra a média do período inteiro para os valores-alvo do município
  const dt = m.temp - media(temp)
  const du = m.umid - media(umid)
  let fc = m.chuva / media(chuva)
  let chuvaFinal = chuva
  for (let k = 0; k < 6; k++) {
    chuvaFinal = chuva.map((v) => Math.min(380, Math.max(0, v * fc)))
    fc *= m.chuva / media(chuvaFinal)
  }
  const serie: SerieClima = {
    temp: temp.map((v) => +(v + dt).toFixed(2)),
    chuva: chuvaFinal.map((v) => +v.toFixed(1)),
    umid: umid.map((v) => +Math.min(97, Math.max(30, v + du)).toFixed(1)),
  }
  cache.set(m.id, serie)
  return serie
}

// ---------- Janelas e agregação ----------
export type Granularidade = 'mensal' | 'anual'
export type Janela = '12m' | '5a' | '10a' | 'custom'

export interface Ponto {
  rotulo: string
  inicio: number // mês inicial (inclusivo)
  fim: number // mês final (exclusivo)
  valor: number
}

export function janelaEmMeses(janela: Janela, de: number, ate: number): [number, number] {
  const n = janela === '12m' ? 12 : janela === '5a' ? 60 : janela === '10a' ? 120 : Infinity
  return [Math.max(de, ate - n), ate]
}

export function agregar(valores: number[], ini: number, fim: number, gran: Granularidade, modo: 'media' | 'soma'): Ponto[] {
  if (gran === 'mensal') {
    return Array.from({ length: fim - ini }, (_, k) => ({ rotulo: rotuloMes(ini + k), inicio: ini + k, fim: ini + k + 1, valor: valores[ini + k] }))
  }
  const pontos: Ponto[] = []
  for (let a = Math.floor(ini / 12); a <= Math.floor((fim - 1) / 12); a++) {
    const i0 = Math.max(ini, a * 12)
    const i1 = Math.min(fim, a * 12 + 12)
    const fatia = valores.slice(i0, i1)
    pontos.push({
      rotulo: String(ANO_INICIO + a),
      inicio: i0,
      fim: i1,
      valor: modo === 'soma' ? fatia.reduce((x, y) => x + y, 0) : media(fatia),
    })
  }
  return pontos
}

export const mediaPeriodo = (v: number[], ini: number, fim: number) => media(v.slice(ini, fim))
export const mesInicialDoAno = (ano: number) => (ano - ANO_INICIO) * 12
export const mesFinalDoAno = (ano: number) => (ano - ANO_INICIO + 1) * 12
