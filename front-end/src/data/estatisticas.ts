// Estatísticas gerais (/api/estatisticas): panorama climático nacional.
// Todas as agregações vêm prontas do servidor (média ponderada pela área
// municipal sobre a visão mensal clima_mensal); o navegador só desenha.
import type { Estacao } from './seasons'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'
const BASE = API_BASE === '/api' ? '/api/estatisticas' : `${API_BASE}/api/estatisticas`

export type Regiao = 'Norte' | 'Nordeste' | 'Centro-Oeste' | 'Sudeste' | 'Sul'
export type FaseEnso = 'el_nino' | 'la_nina' | 'neutro'
export type VariavelClima = 'temperatura' | 'umidade' | 'precipitacao'

export const REGIOES: Regiao[] = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
export const FASES: FaseEnso[] = ['el_nino', 'la_nina', 'neutro']
export const NOME_FASE: Record<FaseEnso, string> = { el_nino: 'El Niño', la_nina: 'La Niña', neutro: 'Neutro' }
export const VARIAVEIS: VariavelClima[] = ['temperatura', 'precipitacao', 'umidade']
export const NOME_VARIAVEL: Record<VariavelClima, string> = {
  temperatura: 'Temperatura', precipitacao: 'Precipitação', umidade: 'Umidade relativa',
}
export const UNIDADE: Record<VariavelClima, string> = { temperatura: '°C', precipitacao: 'mm/mês', umidade: '%' }

export interface Recorte {
  inicio: number
  fim: number
  regiao: Regiao | null
  estacao: Estacao | null
  enso: FaseEnso | null
}

export const RECORTE_PADRAO: Recorte = { inicio: 2015, fim: 2025, regiao: null, estacao: null, enso: null }

export interface Indicador {
  valor: number | null
  unidade: string
  metodo: string
  media_simples_municipios: number | null
  referencia_2015_2025: number | null
  diferenca: number | null
  anual_equivalente?: number | null
}

export interface ExtremoMensal {
  valor: number
  unidade: string
  codigo_ibge: number
  municipio: string
  uf: string
  ano: number
  mes: number
}

export interface Resumo {
  meses: number
  meses_referencia: number
  municipios_com_dados: number
  municipios_cadastrados: number
  indicadores: Record<VariavelClima, Indicador>
  extremos_mensais: {
    temperatura_max: ExtremoMensal | null
    temperatura_min: ExtremoMensal | null
    precipitacao_max: ExtremoMensal | null
    umidade_min: ExtremoMensal | null
    metodo: string
  }
  metodo: { ponderacao: string; comparacao: string }
}

export interface PontoMensal {
  ano: number
  mes: number
  temperatura: number | null
  umidade: number | null
  precipitacao: number | null
  oni: number | null
  fase: FaseEnso | null
  estacao: Estacao
}

export interface Serie {
  mensal: PontoMensal[]
  anual: {
    ano: number; meses: number; temperatura: number | null; umidade: number | null
    precipitacao_mensal: number | null; precipitacao_total: number | null
  }[]
  ciclo_mensal: { mes: number; temperatura: number | null; umidade: number | null; precipitacao: number | null }[]
  nota_total_anual: string
}

export interface ResumoEstacao {
  estacao: Estacao
  anos: number
  temperatura: { media: number; min: number; max: number; ano_min: number; ano_max: number }
  umidade: { media: number; min: number; max: number; ano_min: number; ano_max: number }
  precipitacao_total: { media: number; min: number; max: number; ano_min: number; ano_max: number }
}

export interface Sazonal {
  por_ano: { ano: number; estacao: Estacao; temperatura: number | null; umidade: number | null; precipitacao_total: number | null }[]
  resumo: ResumoEstacao[]
  nota: string
}

export interface Regioes {
  regioes: ({ regiao: Regiao; municipios: number; area_km2: number | null } & Record<VariavelClima, number | null>)[]
  brasil: Record<VariavelClima, number | null>
  ciclo_mensal: ({ regiao: Regiao; mes: number } & Record<VariavelClima, number | null>)[]
}

export interface LinhaEnso {
  escopo: 'Brasil' | Regiao
  estacao: Estacao | 'todas'
  fase: FaseEnso
  meses: number
  temperatura: number | null
  umidade: number | null
  precipitacao: number | null
  precipitacao_pct: number | null
}

export interface Enso {
  linhas: LinhaEnso[]
  meses_por_fase: Record<FaseEnso, number>
  metodo: string
}

export interface MapaClima {
  variavel: VariavelClima
  unidade: string
  metodo: string
  quebras: number[]
  resumo: { com_valor: number; mediana: number | null; min: number | null; max: number | null }
  valores: { codigo_ibge: number; valor: number | null; meses: number }[]
}

export interface Abrangencia {
  municipios_com_dados: number
  municipios_cadastrados: number
  periodo: { inicio: number; fim: number }
  meses: number
  regioes: number
  ufs: number
  variaveis: string[]
  resolucao_temporal: string
  resolucao_espacial: string
  fonte: string
}

export type LinhaUf = { uf: string; regiao: Regiao; municipios: number } & Record<VariavelClima, number | null>

export type ClasseAnomalia = 'todas' | 'estatisticas' | 'extremos'
type PorClasse = Record<ClasseAnomalia, number> & Record<`taxa_${ClasseAnomalia}`, number | null> & { dias: number }

export interface VariavelAnomalia {
  variavel: 'precipitacao' | 'temperatura_alta' | 'temperatura_baixa' | 'umidade_alta' | 'umidade_baixa'
  rotulo: string
  familia: VariavelClima
  dias_validos: number
  totais: Record<ClasseAnomalia, { eventos: number; taxa: number | null }>
  por_ano: (PorClasse & { ano: number })[]
  por_estacao: (PorClasse & { estacao: Estacao })[]
  por_regiao: (PorClasse & { regiao: Regiao })[]
  ranking: { codigo_ibge: number; municipio: string; uf: string; regiao: Regiao; eventos: number; dias: number; taxa: number }[]
}

export interface Anomalias {
  recorte: Recorte
  inicio_pontuado: number
  classes: Record<ClasseAnomalia, string>
  min_eventos_ranking: number
  variaveis: VariavelAnomalia[]
  definicao: string
  atualizado_em: Record<string, string | null>
}

function query(r: Partial<Recorte> & Record<string, string | number | null | undefined>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(r)) if (v !== null && v !== undefined) p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

const cache = new Map<string, Promise<unknown>>()

async function obter<T>(caminho: string, signal?: AbortSignal): Promise<T> {
  const url = `${BASE}${caminho}`
  let promessa = cache.get(url) as Promise<T> | undefined
  if (!promessa) {
    promessa = fetch(url).then(async (r) => {
      if (!r.ok) {
        const corpo = await r.json().catch(() => null) as { detail?: unknown } | null
        throw new Error(typeof corpo?.detail === 'string' ? corpo.detail : `Erro ${r.status} ao consultar ${caminho}`)
      }
      return r.json() as Promise<T>
    })
    promessa.catch(() => cache.delete(url))
    cache.set(url, promessa)
  }
  // a requisição em si é compartilhada (cache); o abort só descarta a resposta deste chamador
  if (!signal) return promessa
  return new Promise<T>((resolve, reject) => {
    const abortar = () => reject(new DOMException('Abortado', 'AbortError'))
    if (signal.aborted) return abortar()
    signal.addEventListener('abort', abortar, { once: true })
    promessa!.then(resolve, reject).finally(() => signal.removeEventListener('abort', abortar))
  })
}

const q = (r: Recorte) => query({ inicio: r.inicio, fim: r.fim, regiao: r.regiao, estacao: r.estacao, enso: r.enso })

export const carregarAbrangencia = (s?: AbortSignal) => obter<Abrangencia>('/abrangencia', s)
export const carregarResumo = (r: Recorte, s?: AbortSignal) => obter<Resumo>(`/resumo${q(r)}`, s)
export const carregarSerie = (r: Recorte, s?: AbortSignal) => obter<Serie>(`/serie${q(r)}`, s)
export const carregarSazonal = (r: Recorte, s?: AbortSignal) => obter<Sazonal>(`/sazonal${q(r)}`, s)
export const carregarRegioes = (r: Recorte, s?: AbortSignal) => obter<Regioes>(`/regioes${q(r)}`, s)
export const carregarEnso = (r: Recorte, s?: AbortSignal) => obter<Enso>(`/enso${q({ ...r, enso: null })}`, s)
export const carregarAnomalias = (r: Recorte, s?: AbortSignal) => obter<Anomalias>(`/anomalias${q(r)}`, s)
export const carregarUfs = (s?: AbortSignal) => obter<LinhaUf[]>('/ufs', s)
export const carregarMapaClima = (v: VariavelClima, r: Recorte, s?: AbortSignal) =>
  obter<MapaClima>(`/mapa${query({ variavel: v, inicio: r.inicio, fim: r.fim, estacao: r.estacao, enso: r.enso })}`, s)

export const ehAbort = (e: unknown) => e instanceof DOMException && e.name === 'AbortError'

// ---------------------------------------------------------------- formatação
const nf = (casas: number) => new Intl.NumberFormat('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
export const fmt = (v: number | null | undefined, casas = 1) => (v === null || v === undefined || !Number.isFinite(v) ? '—' : nf(casas).format(v))
export const fmtInt = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v.toLocaleString('pt-BR'))
export const fmtSinal = (v: number | null | undefined, casas = 1) =>
  v === null || v === undefined ? '—' : `${v > 0 ? '+' : v < 0 ? '−' : '±'}${nf(casas).format(Math.abs(v))}`
export const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
export const casasDe = (v: VariavelClima) => (v === 'precipitacao' ? 0 : 1)

// ---------------------------------------------------------------- cores
// Categóricas validadas (scripts/validate_palette.js do guia de visualização):
// regiões e classes passam em todas as verificações; as estações são as do mapa nacional.
export const COR_REGIAO: Record<Regiao, string> = {
  Norte: '#16a06a', Nordeste: '#e0a100', 'Centro-Oeste': '#b5562b', Sudeste: '#2a6fd6', Sul: '#c2449a',
}
export const COR_FASE: Record<FaseEnso, string> = { el_nino: '#c7522a', la_nina: '#2a6fd6', neutro: '#8f8f8a' }
export const COR_CLASSE = { estatisticas: '#2a6fd6', extremos: '#c0562b' } as const
export const COR_VARIAVEL: Record<VariavelClima, string> = { temperatura: '#c7522a', precipitacao: '#2a6fd6', umidade: '#16806a' }
/** Rampas sequenciais (claro → escuro), um matiz por variável. */
export const RAMPA: Record<VariavelClima, string[]> = {
  temperatura: ['#fdeccd', '#fbd29a', '#f6b066', '#ec8a44', '#d9632f', '#b53f24', '#86251a'],
  precipitacao: ['#dcebfb', '#b4d3f5', '#86b5ec', '#5594e0', '#2f74cc', '#1d57a3', '#103b73'],
  umidade: ['#dcf1eb', '#b3dfd3', '#83c8b7', '#53ad99', '#2e8f7b', '#18725f', '#0b5446'],
}

export type IdAnomalia = VariavelAnomalia['variavel']
export const ROTULO_ANOMALIA: Record<IdAnomalia, string> = {
  precipitacao: 'Chuva acima', temperatura_alta: 'Temp. acima', temperatura_baixa: 'Temp. abaixo',
  umidade_alta: 'Umidade acima', umidade_baixa: 'Umidade abaixo',
}
