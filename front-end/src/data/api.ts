import { ANO_FIM, ANO_INICIO, type Municipio, type SerieClima } from './climate'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

type MunicipioApi = {
  codigo_ibge: number
  latitude: number | null
  longitude: number | null
  details: {
    municipio: string; uf: string; estado: string; regiao: string | null
    populacao: number | null; ano_populacao: number | null; bioma: string | null; area_km2: number | null
    mesorregiao: string | null; microrregiao: string | null; geomorfologia: string | null
    regiao_geomorfologica: string | null; dominio_geomorfologico: string | null
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
    bioma: d.bioma, areaKm2: d.area_km2, mesorregiao: d.mesorregiao, microrregiao: d.microrregiao,
    geomorfologia: d.geomorfologia, regiaoGeomorfologica: d.regiao_geomorfologica,
    dominioGeomorfologico: d.dominio_geomorfologico,
  }
}

export async function carregarMunicipios(): Promise<Municipio[]> {
  // ~5.570 municípios: as 6 páginas são pedidas em paralelo (antes, em sequência:
  // ~3 s no primeiro acesso); se a última vier cheia, segue paginando.
  const pageSize = 1000
  const paralelas = 6
  const todos: MunicipioApi[] = []
  let offset = 0
  for (;;) {
    const paginas = await Promise.all(
      Array.from({ length: paralelas }, (_, i) => get<MunicipioApi[]>(`/municipios?limit=${pageSize}&offset=${offset + i * pageSize}`)),
    )
    paginas.forEach((pagina) => todos.push(...pagina))
    if (paginas[paralelas - 1].length < pageSize) break
    offset += paralelas * pageSize
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

/**
 * Série mensal completa (2015–2025) do município.
 *
 * A série tem sempre os 132 meses e os componentes recortam o período
 * escolhido; por isso a consulta é feita uma única vez por município e trocar
 * o período não gera nova requisição.
 */
export async function carregarClima(codigoIbge: string, signal?: AbortSignal): Promise<{ serie: SerieClima; enso: ClimaApi['enso'] }> {
  const cacheado = cacheClima.get(codigoIbge)
  if (cacheado) return cacheado
  const { registros, enso } = await get<ClimaApi>(`/municipios/${codigoIbge}/clima/mensal?inicio=${ANO_INICIO}-01-01&fim=${ANO_FIM}-12-31`, signal)
  if (!registros.length) throw new Error('Não há dados climáticos para este município.')
  // Meses sem registro (ou com variável nula) ficam NaN: são lacunas, nunca zero.
  const meses = Array.from({ length: (ANO_FIM - ANO_INICIO + 1) * 12 }, () => ({ temperatura: NaN, umidade: NaN, precipitacao: NaN }))
  for (const item of registros) {
    const data = new Date(item.datetime)
    const mes = (data.getUTCFullYear() - ANO_INICIO) * 12 + data.getUTCMonth()
    const bucket = meses[mes]
    if (!bucket) continue
    bucket.temperatura = item.temperatura ?? NaN
    bucket.umidade = item.umidade ?? NaN
    bucket.precipitacao = item.precipitacao ?? NaN
  }
  const arredonda = (v: number, casas: number) => (Number.isFinite(v) ? +v.toFixed(casas) : NaN)
  const resultado = {
    serie: {
      temp: meses.map((m) => arredonda(m.temperatura, 2)),
      umid: meses.map((m) => arredonda(m.umidade, 2)),
      chuva: meses.map((m) => arredonda(m.precipitacao, 1)),
    },
    enso,
  }
  cacheClima.set(codigoIbge, resultado)
  return resultado
}

// ---------------------------------------------------------------------------
// Anomalias de chuva e notícias verificadas (/api/climate, via proxy em /climate)
// ---------------------------------------------------------------------------

export interface AnomaliaChuva {
  id: string
  data: string // AAAA-MM-DD
  detector: 'arima_zscore' | 'accumulation_percentile'
  observadoMm: number
  previstoMm: number | null
  dias: number // 1 para o ARIMA; 3 ou 5 para acumulados
  status: 'detected' | 'scientifically_reviewed' | 'rejected'
  avaliacaoClima: string | null
  avaliacaoTempo: string | null
  picoDiarioMm: number | null
  noticiasVerificadas: number
  noticiasPesquisadas: boolean // a busca de notícias já foi feita para esta anomalia
  faseEnso: FaseEnso | null
  oni: number | null
}

export type FaseEnso = 'el_nino' | 'la_nina' | 'neutral'

export interface NoticiaVerificada {
  id: string
  url: string
  manchete: string
  fonte: string | null
  publicadaEm: string | null
  confiabilidade: string | null
  relevancia: string
  datasAnomalia: string[]
}

type AnomaliasApi = {
  total: number
  anomalies: {
    id: string; anomaly_date: string; detector: AnomaliaChuva['detector']; observed_mm: number; predicted_mm: number | null
    direction: string; status: AnomaliaChuva['status']; verified_news: number; news_investigated: boolean; accumulation_days: number | null
    climate_assessment: string | null; weather_assessment: string | null; peak_daily_mm: number | null
    enso_phase: FaseEnso | null; oni: number | null
  }[]
}
type NoticiasApi = {
  total: number
  pages: number
  news: {
    id: string; url: string; headline: string; source: string | null; published_at: string | null; reliability: string | null
    relevance_status: string; related_anomalies: { anomaly_date: string }[]
  }[]
}

const cacheAnomalias = new Map<string, AnomaliaChuva[]>()
const cacheNoticias = new Map<string, NoticiaVerificada[]>()
// /api/climate é o caminho público; pelo proxy do Vite (que remove /api) ele vira /climate
const CLIMATE = API_BASE === '/api' ? '/climate' : '/api/climate'

/** Anomalias positivas de chuva (inclusive as descartadas, para transparência). */
export async function carregarAnomalias(codigoIbge: string, signal?: AbortSignal): Promise<AnomaliaChuva[]> {
  const cacheado = cacheAnomalias.get(codigoIbge)
  if (cacheado) return cacheado
  const { anomalies } = await get<AnomaliasApi>(
    `${CLIMATE}/anomalies?start_date=${ANO_INICIO}-01-01&end_date=${ANO_FIM}-12-31&codigo_ibge=${codigoIbge}&limit=500`, signal)
  const lista = anomalies.filter((a) => a.direction === 'positive').map((a) => ({
    id: a.id, data: a.anomaly_date, detector: a.detector, observadoMm: a.observed_mm, previstoMm: a.predicted_mm,
    dias: a.accumulation_days ?? 1, status: a.status, avaliacaoClima: a.climate_assessment,
    avaliacaoTempo: a.weather_assessment, picoDiarioMm: a.peak_daily_mm, noticiasVerificadas: a.verified_news,
    noticiasPesquisadas: a.news_investigated,
    faseEnso: a.enso_phase, oni: a.oni,
  }))
  cacheAnomalias.set(codigoIbge, lista)
  return lista
}

/** Notícias verificadas pelo Fact-Checker, ligadas a anomalias do município. */
export async function carregarNoticias(codigoIbge: string, signal?: AbortSignal): Promise<NoticiaVerificada[]> {
  const cacheado = cacheNoticias.get(codigoIbge)
  if (cacheado) return cacheado
  const lista: NoticiaVerificada[] = []
  for (let page = 1; page <= 20; page++) {
    const resposta = await get<NoticiasApi>(
      `${CLIMATE}/news?start_date=${ANO_INICIO}-01-01&end_date=${ANO_FIM}-12-31&codigo_ibge=${codigoIbge}&limit=100&page=${page}&sort_by=anomaly_date&order=asc`, signal)
    lista.push(...resposta.news.map((n) => ({
      id: n.id, url: n.url, manchete: n.headline, fonte: n.source, publicadaEm: n.published_at,
      confiabilidade: n.reliability, relevancia: n.relevance_status,
      datasAnomalia: n.related_anomalies.map((a) => a.anomaly_date),
    })))
    if (page >= resposta.pages) break
  }
  cacheNoticias.set(codigoIbge, lista)
  return lista
}

// ---------------------------------------------------------------------------
// Aba Notícias: busca paginada no servidor
// ---------------------------------------------------------------------------

export interface MunicipioAnalisado {
  codigoIbge: string
  nome: string
  uf: string | null
  eventos: number
  noticias: number
  primeiraData: string | null
  ultimaData: string | null
  latitude: number | null
  longitude: number | null
}

/** Municípios analisados; com filtros, as contagens seguem o período e a fonte. */
export async function carregarMunicipiosAnalisados(
  signal?: AbortSignal,
  filtros?: { anoDe: number; anoAte: number; fonte: string },
): Promise<MunicipioAnalisado[]> {
  const params = new URLSearchParams()
  if (filtros) {
    params.set('start_date', `${filtros.anoDe}-01-01`)
    params.set('end_date', `${filtros.anoAte}-12-31`)
    if (filtros.fonte.trim().length >= 2) params.set('source', filtros.fonte.trim())
  }
  const lista = await get<{
    codigo_ibge: number | null; municipality: string; uf: string | null; anomalies: number; verified_news: number
    first_date: string | null; last_date: string | null; latitude: number | null; longitude: number | null
  }[]>(`${CLIMATE}/municipalities${params.size ? `?${params}` : ''}`, signal)
  return lista.map((m) => ({
    codigoIbge: String(m.codigo_ibge ?? ''), nome: m.municipality, uf: m.uf, eventos: m.anomalies,
    noticias: m.verified_news, primeiraData: m.first_date, ultimaData: m.last_date,
    latitude: m.latitude, longitude: m.longitude,
  }))
}

export interface EventoRelacionado {
  data: string
  dataEvento: string | null
  municipio: string
  uf: string | null
  detector: AnomaliaChuva['detector']
  observadoMm: number
  dias: number
  relevancia: string
  faseEnso: FaseEnso | null
  oni: number | null
}

export interface NoticiaDaLista {
  id: string
  url: string
  manchete: string
  fonte: string | null
  publicadaEm: string | null
  confiabilidade: string | null
  relevancia: string
  eventos: EventoRelacionado[]
}

export interface FiltrosNoticias {
  codigoIbge: string // '' = todos
  anoDe: number
  anoAte: number
  fonte: string
  ordem: 'evento_desc' | 'evento_asc' | 'publicacao_desc'
  pagina: number
  porPagina: number
}

export interface PaginaNoticias {
  total: number
  paginas: number
  noticias: NoticiaDaLista[]
}

type NoticiasDetalhadasApi = {
  total: number
  pages: number
  news: (Omit<NoticiasApi['news'][number], 'related_anomalies'> & {
    related_anomalies: {
      anomaly_date: string; event_date: string | null; municipality: string; uf: string | null
      detector: AnomaliaChuva['detector']; observed_mm: number; accumulation_days: number | null; relevance_status: string
      enso_phase: FaseEnso | null; oni: number | null
    }[]
  })[]
}

export async function buscarNoticias(f: FiltrosNoticias, signal?: AbortSignal): Promise<PaginaNoticias> {
  const [sortBy, order] = f.ordem === 'publicacao_desc' ? ['published_at', 'desc'] : ['anomaly_date', f.ordem === 'evento_asc' ? 'asc' : 'desc']
  const params = new URLSearchParams({
    start_date: `${f.anoDe}-01-01`, end_date: `${f.anoAte}-12-31`, sort_by: sortBy, order,
    page: String(f.pagina), limit: String(f.porPagina),
  })
  if (f.codigoIbge) params.set('codigo_ibge', f.codigoIbge)
  if (f.fonte.trim().length >= 2) params.set('source', f.fonte.trim())
  const resposta = await get<NoticiasDetalhadasApi>(`${CLIMATE}/news?${params}`, signal)
  return {
    total: resposta.total,
    paginas: resposta.pages,
    noticias: resposta.news.map((n) => ({
      id: n.id, url: n.url, manchete: n.headline, fonte: n.source, publicadaEm: n.published_at,
      confiabilidade: n.reliability, relevancia: n.relevance_status,
      eventos: n.related_anomalies.map((a) => ({
        data: a.anomaly_date, dataEvento: a.event_date, municipio: a.municipality, uf: a.uf, detector: a.detector,
        observadoMm: a.observed_mm, dias: a.accumulation_days ?? 1, relevancia: a.relevance_status,
        faseEnso: a.enso_phase, oni: a.oni,
      })),
    })),
  }
}
