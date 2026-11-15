// Análise espacial e sazonal (/api/analysis): mapa coroplético nacional,
// distribuição sazonal por município/região e definições operacionais.
//
// Pelo proxy do Vite (que remove /api), /api/analysis vira /analysis — mesmo
// arranjo de /api/climate em api.ts.
import type { FeatureCollection, Geometry } from 'geojson'
import type { Estacao } from './seasons'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'
const ANALYSIS = API_BASE === '/api' ? '/api/analysis' : `${API_BASE}/api/analysis`

export type Variavel = 'precipitacao' | 'temperatura_alta' | 'temperatura_baixa' | 'umidade_alta' | 'umidade_baixa'
export type ClasseEvento = 'todas' | 'estatisticas' | 'extremos' | 'impacto'
export type Metrica =
  | 'taxa' | 'contagem' | 'intensidade' | 'participacao' | 'outono_inverno'
  | 'concentracao' | 'estacao_dominante' | 'razao_enso'
export type FaseEnsoAnalise = 'el_nino' | 'la_nina' | 'neutro'
export type FaseComparacao = 'el_nino' | 'la_nina'
export type Escala = 'sequential' | 'diverging' | 'categorical'
export type StatusValor = 'ok' | 'insuficiente' | 'sem_eventos' | 'sem_dados'
export type Padrao = `predominio_${Estacao}` | 'sem_predominio' | 'insuficiente'

export interface FiltrosAnalise {
  variable: Variavel
  event_class: ClasseEvento
  start_year: number
  end_year: number
  season: Estacao | null
  enso_phase: FaseEnsoAnalise | null
}

export interface DefinicaoMetrica {
  label: string
  unit: string
  scale: Escala
  definition: string
}

export interface DefinicaoClasse {
  label: string
  definition: string
  is_extreme: boolean
  counted: boolean
}

export interface Definicoes {
  analysis_version: string
  seasons: Record<Estacao, string>
  enso_phases: Record<FaseEnsoAnalise, string>
  enso_rule: string
  variables: Record<Variavel, { label: string; unit: string; available: boolean }>
  class_filters: Record<ClasseEvento, string>
  precipitation_classes: Record<string, DefinicaoClasse>
  thermal_classes: Record<string, DefinicaoClasse>
  metrics: Record<Metrica, DefinicaoMetrica>
  min_events: number
  snapshot: Record<string, string | null>
}

export interface ValorMunicipio {
  codigo_ibge: number
  value: number | null
  category: Padrao | null
  n: number
  days: number
  status: StatusValor
}

export interface Coropletico extends DefinicaoMetrica {
  metric: Metrica
  filters: FiltrosAnalise & { compare_phase?: FaseComparacao }
  variable_label: string
  period: { start_year: number; end_year: number }
  breaks: number[]
  summary: {
    municipalities_with_data: number
    insufficient: number
    without_detection: number
    total_events: number
    median: number | null
  }
  values: ValorMunicipio[]
}

export interface LinhaSazonal {
  season: Estacao
  n: number
  days: number
  rate_per_1000: number | null
  share_norm: number | null
}

export interface LinhaEnso {
  season: Estacao
  enso_phase: FaseEnsoAnalise
  n: number
  days: number
  rate_per_1000: number | null
  ratio_vs_neutral: number | null
  ratio_ci_low: number | null
  ratio_ci_high: number | null
}

export interface AnaliseMunicipio {
  codigo_ibge: number
  nome: string
  uf: string
  regiao: string
  filters: FiltrosAnalise
  has_detection: boolean
  seasons: (LinhaSazonal & { share_abs: number | null })[]
  summary: {
    n_events: number
    days: number
    concentration: number | null
    dominant_season: Estacao | null
    chi2_pvalue: number | null
    chi2_qvalue: number | null
    autumn_winter_share: number | null
    pattern: Padrao
  } | null
  comparison: { estado: LinhaSazonal[]; regiao: LinhaSazonal[]; brasil: LinhaSazonal[] }
  enso: LinhaEnso[]
  events_by_year: Record<string, number>
}

export interface Regioes {
  filters: FiltrosAnalise
  pooled: (LinhaSazonal & { regiao: string })[]
  patterns: { regiao: string; pattern: Padrao; municipalities: number; share: number }[]
  median_concentration: Record<string, number | null>
  moran_autumn_winter: { I: number | null; expected: number | null; p_value: number | null; n: number; permutations?: number } | null
}

export type Geometrias = FeatureCollection<Geometry, { codigo_ibge: number }>

/** Erro da API com o status HTTP e a mensagem (`detail`) do FastAPI. */
export class ErroAnalise extends Error {
  status: number
  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.status = status
  }
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${ANALYSIS}${path}`, { signal })
  if (!response.ok) {
    let detalhe: string
    try {
      const corpo = await response.json() as { detail?: unknown }
      detalhe = typeof corpo.detail === 'string' ? corpo.detail : JSON.stringify(corpo.detail ?? corpo)
    } catch {
      detalhe = response.statusText
    }
    const prefixo = response.status === 503
      ? 'Dados da análise indisponíveis'
      : response.status === 422 ? 'Filtro inválido' : `Erro ${response.status}`
    throw new ErroAnalise(response.status, `${prefixo}: ${detalhe}`)
  }
  return response.json() as Promise<T>
}

function paramsFiltros(f: FiltrosAnalise): URLSearchParams {
  const p = new URLSearchParams({
    variable: f.variable, event_class: f.event_class,
    start_year: String(f.start_year), end_year: String(f.end_year),
  })
  if (f.season) p.set('season', f.season)
  if (f.enso_phase) p.set('enso_phase', f.enso_phase)
  return p
}

let promessaDefinicoes: Promise<Definicoes> | null = null
export function carregarDefinicoes(): Promise<Definicoes> {
  promessaDefinicoes ??= get<Definicoes>('/definicoes').catch((e: unknown) => {
    promessaDefinicoes = null
    throw e
  })
  return promessaDefinicoes
}

// a malha nacional (~1 MB comprimido) é baixada uma vez por sessão
let promessaGeometrias: Promise<Geometrias> | null = null
export function carregarGeometrias(): Promise<Geometrias> {
  promessaGeometrias ??= get<Geometrias>('/geometrias').catch((e: unknown) => {
    promessaGeometrias = null
    throw e
  })
  return promessaGeometrias
}

const cacheCoropletico = new Map<string, Coropletico>()
export async function carregarCoropletico(
  metrica: Metrica, filtros: FiltrosAnalise, comparar: FaseComparacao, signal?: AbortSignal,
): Promise<Coropletico> {
  const p = paramsFiltros(filtros)
  p.set('metric', metrica)
  if (metrica === 'razao_enso') p.set('compare_phase', comparar)
  const chave = p.toString()
  const cacheado = cacheCoropletico.get(chave)
  if (cacheado) return cacheado
  const resposta = await get<Coropletico>(`/coropletico?${chave}`, signal)
  cacheCoropletico.set(chave, resposta)
  return resposta
}

export function carregarAnaliseMunicipio(codigo: string, filtros: FiltrosAnalise, signal?: AbortSignal): Promise<AnaliseMunicipio> {
  return get<AnaliseMunicipio>(`/municipios/${codigo}?${paramsFiltros(filtros)}`, signal)
}

export function carregarRegioes(filtros: FiltrosAnalise, signal?: AbortSignal): Promise<Regioes> {
  return get<Regioes>(`/regioes?${paramsFiltros(filtros)}`, signal)
}

export function ehAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError'
}

// ---- notícias × intensidade e visão geral --------------------------------

export interface Proporcao {
  n: number
  with_news: number
  pct: number | null
  ci_low: number | null
  ci_high: number | null
}

export interface NoticiasIntensidade {
  investigated_events: number
  investigated_municipalities: number
  overall: Proporcao
  by_intensity_daily: (Proporcao & { label: string })[]
  by_class: (Proporcao & { event_class: string; label: string })[]
  by_high_intensity: { alta: Proporcao; demais: Proporcao }
  definitions: Record<string, string>
  caveats: string[]
}

export interface VisaoGeral {
  climate_records: number | null
  municipalities: number
  municipalities_with_data: number | null
  period: { start: number; end: number; scored_start: number }
  rain_events: number
  thermal_anomalies: number
  variables: string[]
}

let promessaNoticias: Promise<NoticiasIntensidade> | null = null
export function carregarNoticiasIntensidade(): Promise<NoticiasIntensidade> {
  promessaNoticias ??= get<NoticiasIntensidade>('/noticias-intensidade').catch((e) => {
    promessaNoticias = null
    throw e
  })
  return promessaNoticias
}

let promessaVisao: Promise<VisaoGeral> | null = null
export function carregarVisaoGeral(): Promise<VisaoGeral> {
  promessaVisao ??= get<VisaoGeral>('/visao-geral').catch((e) => {
    promessaVisao = null
    throw e
  })
  return promessaVisao
}
