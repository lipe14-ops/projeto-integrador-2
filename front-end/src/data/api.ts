import type { Municipio, SerieClima } from './climate'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

type MunicipioApi = {
  codigo_ibge: number
  latitude: number | null
  longitude: number | null
  details: {
    municipio: string; uf: string; estado: string; regiao: string | null
    populacao: number | null; ano_populacao: number | null; bioma: string | null; area_km2: number | null
  } | null
}
type ClimaApi = {
  registros: { datetime: string; temperatura: number | null; precipitacao: number | null; umidade: number | null }[]
  enso: { year: number; month: number; enso_index: number | null }[]
}
const cacheDetalhes = new Map<string, Municipio>()
const cacheClima = new Map<string, { serie: SerieClima; enso: ClimaApi['enso'] }>()

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { signal })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`Erro ${response.status} ao consultar a API${body ? `: ${body}` : ''}`)
  }
  return response.json() as Promise<T>
}

function converterMunicipio(item: MunicipioApi): Municipio {
  const d = item.details
  if (!d) throw new Error(`A API não retornou os detalhes do município ${item.codigo_ibge}.`)
  return {
    id: String(item.codigo_ibge), ibge: String(item.codigo_ibge), nome: d.municipio, uf: d.uf,
    estado: d.estado, regiao: d.regiao ?? '—', lat: item.latitude ?? 0, lon: item.longitude ?? 0,
    temp: 0, chuva: 0, umid: 0, populacao: d.populacao, anoPopulacao: d.ano_populacao,
    bioma: d.bioma, areaKm2: d.area_km2,
  }
}

export async function carregarMunicipios(): Promise<Municipio[]> {
  const pageSize = 1000
  const todos: MunicipioApi[] = []
  for (let offset = 0; ; offset += pageSize) {
    const page = await get<MunicipioApi[]>(`/municipios?limit=${pageSize}&offset=${offset}`)
    todos.push(...page)
    if (page.length < pageSize) break
  }
  return todos.filter((item) => item.details).map((item) => {
    const municipio = converterMunicipio(item)
    cacheDetalhes.set(municipio.ibge, municipio)
    return municipio
  })
}

export async function carregarMunicipio(codigoIbge: string, signal?: AbortSignal): Promise<Municipio> {
  const cacheado = cacheDetalhes.get(codigoIbge)
  if (cacheado) return cacheado
  const municipio = converterMunicipio(await get<MunicipioApi>(`/municipios/${codigoIbge}`, signal))
  cacheDetalhes.set(codigoIbge, municipio)
  return municipio
}

export async function carregarClima(codigoIbge: string, de: number, ate: number, signal?: AbortSignal): Promise<{ serie: SerieClima; enso: ClimaApi['enso'] }> {
  const chave = `${codigoIbge}:${de}:${ate}`
  const cacheado = cacheClima.get(chave)
  if (cacheado) return cacheado
  const { registros, enso } = await get<ClimaApi>(`/municipios/${codigoIbge}/clima/mensal?inicio=${de}-01-01&fim=${ate}-12-31`, signal)
  if (!registros.length) throw new Error(`Não há dados climáticos para o município ${codigoIbge} entre ${de} e ${ate}.`)
  const meses = Array.from({ length: 11 * 12 }, () => ({ temperatura: 0, nTemperatura: 0, umidade: 0, nUmidade: 0, precipitacao: 0 }))
  for (const item of registros) {
    const data = new Date(item.datetime)
    const mes = (data.getUTCFullYear() - 2015) * 12 + data.getUTCMonth()
    const bucket = meses[mes]
    if (!bucket) continue
    bucket.temperatura = item.temperatura ?? 0
    bucket.nTemperatura = item.temperatura == null ? 0 : 1
    bucket.umidade = item.umidade ?? 0
    bucket.nUmidade = item.umidade == null ? 0 : 1
    bucket.precipitacao = item.precipitacao ?? 0
  }
  const resultado = {
    serie: {
      temp: meses.map((m) => m.nTemperatura ? +(m.temperatura / m.nTemperatura).toFixed(2) : 0),
      umid: meses.map((m) => m.nUmidade ? +(m.umidade / m.nUmidade).toFixed(2) : 0),
      chuva: meses.map((m) => +m.precipitacao.toFixed(1)),
    },
    enso,
  }
  cacheClima.set(chave, resultado)
  return resultado
}
