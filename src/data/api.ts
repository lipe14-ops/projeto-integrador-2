import type { Municipio, SerieClima } from './climate'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

type MunicipioApi = {
  codigo_ibge: number
  latitude: number | null
  longitude: number | null
  details: { municipio: string; uf: string; regiao: string | null } | null
}
type ClimaApi = {
  registros: { datetime: string; temperatura: number | null; precipitacao: number | null; umidade: number | null }[]
  enso: { year: number; month: number; enso_index: number | null }[]
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`A API respondeu ${response.status}: ${detail || response.statusText}`)
  }
  return response.json() as Promise<T>
}

export async function carregarMunicipios(): Promise<Municipio[]> {
  const pageSize = 1000
  const todas: MunicipioApi[] = []
  for (let offset = 0; ; offset += pageSize) {
    const pagina = await get<MunicipioApi[]>(`/municipios?limit=${pageSize}&offset=${offset}`)
    todas.push(...pagina)
    if (pagina.length < pageSize) break
  }
  return todas.filter((m) => m.details).map((m) => ({
    id: String(m.codigo_ibge), ibge: String(m.codigo_ibge), nome: m.details!.municipio,
    uf: m.details!.uf, regiao: m.details!.regiao ?? '—', lat: m.latitude ?? 0, lon: m.longitude ?? 0,
    temp: 0, chuva: 0, umid: 0,
  }))
}

export async function carregarClima(municipio: Municipio, de: number, ate: number): Promise<{ serie: SerieClima; enso: ClimaApi['enso'] }> {
  const inicio = `${de}-01-01`
  const fim = `${ate}-12-31`
  const { registros, enso } = await get<ClimaApi>(`/municipios/${municipio.ibge}/clima?inicio=${inicio}&fim=${fim}`)
  if (registros.length === 0) throw new Error(`Não há registros climáticos para ${municipio.nome} no período ${de}–${ate}.`)
  const buckets = Array.from({ length: 11 * 12 }, () => ({ temp: 0, tempN: 0, umid: 0, umidN: 0, chuva: 0, chuvaN: 0 }))
  for (const row of registros) {
    const d = new Date(row.datetime)
    const index = (d.getUTCFullYear() - 2015) * 12 + d.getUTCMonth()
    const b = buckets[index]
    if (!b) continue
    if (row.temperatura != null) { b.temp += row.temperatura; b.tempN++ }
    if (row.umidade != null) { b.umid += row.umidade; b.umidN++ }
    if (row.precipitacao != null) { b.chuva += row.precipitacao; b.chuvaN++ }
  }
  return { serie: {
    temp: buckets.map((b) => b.tempN ? +(b.temp / b.tempN).toFixed(2) : 0),
    umid: buckets.map((b) => b.umidN ? +(b.umid / b.umidN).toFixed(2) : 0),
    chuva: buckets.map((b) => +b.chuva.toFixed(1)),
  }, enso }
}
